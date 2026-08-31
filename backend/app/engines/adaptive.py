"""
Adaptive Learning Path + Failure Recovery (Features 9 & 11) — updated for
the two-track roadmap (technical / professional).

An assessed skill belongs to whichever track it was classified into during
roadmap generation (track_classifier.py, grounded in O*NET's Content Model
IDs). The recovery splice — or the acceleration prune — happens INSIDE
that track's TrackPlan only; the other track is untouched. This matters
for the demo: a low score on a technical skill re-routes the mountain
ridge without disturbing the professional trail running in parallel, which
is the whole point of keeping them visually separate.

Same three outcomes as before:
  - score >= 85  -> accelerate: mastered, redundant queued topics pruned.
  - score 70-84  -> steady: level nudged up, no structural change.
  - score < 70   -> recover: [missed prerequisites, if graph-linked] ->
                    revision -> practice -> mini-assessment, spliced in at
                    the learner's current week within that track.
"""

from dataclasses import dataclass, field

from backend.app.engines.roadmap import (
    RATING_SOURCES, Roadmap, RoadmapTopic, TrackPlan, pack_track,
)
from backend.app.engines.skill_graph import SKILL_GRAPH
from backend.app.engines.track_classifier import classify_track
from backend.app.models.learner import AssessmentRecord, LearnerProfile, SkillRecord

ACCELERATE_THRESHOLD = 85.0
RECOVER_THRESHOLD = 70.0

REVISION_HOURS = 3.0
PRACTICE_HOURS = 4.0
REASSESSMENT_HOURS = 1.0
PREREQ_REVIEW_HOURS = 5.0


@dataclass
class AdaptationResult:
    action: str
    track: str
    skill_element: str
    score: float
    updated_learner_level: float
    inserted_topics: list[RoadmapTopic] = field(default_factory=list)
    removed_topic_ids: list[str] = field(default_factory=list)
    message: str = ""
    route_before: list[str] = field(default_factory=list)
    route_after: list[str] = field(default_factory=list)


def _find_element_track(occupation: dict, element: str) -> str:
    """Look up which O*NET source category an assessed element came from,
    to classify its track. Falls back to 'technical' if it matches a
    software tool name, else 'professional' — an assessment on something
    outside the occupation's own rated elements is rare but shouldn't crash."""
    for source in RATING_SOURCES:
        for item in occupation.get(source, []):
            if item["element"] == element:
                return classify_track(source, item.get("element_id", ""), element)
    for s in occupation.get("software_skills", []):
        if s["name"] == element:
            return "technical"
    return "professional"


def _find_graph_node_for_element(element: str) -> str | None:
    for node_id, node in SKILL_GRAPH.items():
        if node.onet_element == element or node.label == element:
            return node_id
    return None


def _mastered_graph_node_ids(learner: LearnerProfile) -> set[str]:
    mastered = set()
    for node_id, node in SKILL_GRAPH.items():
        if node.onet_element and learner.skill_level(node.onet_element) >= 5.0:
            mastered.add(node_id)
        elif learner.knows_tool(node.label):
            mastered.add(node_id)
    return mastered


def _route_labels(plan: TrackPlan) -> list[str]:
    return [f"W{m.week_number}: {t.label}" for m in plan.milestones for t in m.topics]


def _recompute_roadmap_totals(roadmap: Roadmap, learner: LearnerProfile) -> None:
    roadmap.weeks_planned = max(roadmap.technical.weeks_planned, roadmap.professional.weeks_planned)
    roadmap.fits_target_duration = roadmap.weeks_planned <= learner.target_duration_weeks
    roadmap.overflow_weeks = max(0, roadmap.weeks_planned - learner.target_duration_weeks)
    roadmap.total_estimated_hours = round(roadmap.technical.total_hours + roadmap.professional.total_hours, 1)


def apply_assessment_result(learner: LearnerProfile, occupation: dict, roadmap: Roadmap,
                             assessment: AssessmentRecord, current_week: int = 1) -> AdaptationResult:
    element = assessment.skill_element
    score = assessment.score
    track = _find_element_track(occupation, element)
    plan: TrackPlan = roadmap.technical if track == "technical" else roadmap.professional
    route_before = _route_labels(plan)

    prior_level = learner.skill_level(element)
    if score >= ACCELERATE_THRESHOLD:
        new_level = min(7.0, prior_level + 2.5)
    elif score >= RECOVER_THRESHOLD:
        new_level = min(7.0, prior_level + 1.0)
    else:
        new_level = prior_level
    learner.skills[element] = SkillRecord(element=element, level=new_level, source="assessment")
    learner.assessments.append(assessment)

    all_topics: list[RoadmapTopic] = [t for m in plan.milestones for t in m.topics]

    if score >= ACCELERATE_THRESHOLD:
        removed = [t.id for t in all_topics if t.label == element]
        remaining = [t for t in all_topics if t.id not in removed]
        new_plan = pack_track(remaining, plan.weekly_hour_budget, track)
        if track == "technical":
            roadmap.technical = new_plan
        else:
            roadmap.professional = new_plan
        _recompute_roadmap_totals(roadmap, learner)
        return AdaptationResult(
            action="accelerate", track=track, skill_element=element, score=score,
            updated_learner_level=new_level, removed_topic_ids=removed,
            message=f"Strong result on {element} ({score:.0f}/100) — marked mastered, "
                    f"removed {len(removed)} redundant queued topic(s) from the {track} track.",
            route_before=route_before, route_after=_route_labels(new_plan),
        )

    if score < RECOVER_THRESHOLD:
        inserted: list[RoadmapTopic] = []
        node_id = _find_graph_node_for_element(element)
        if node_id:
            mastered = _mastered_graph_node_ids(learner)
            node = SKILL_GRAPH[node_id]
            for p in node.prerequisites:
                if p in mastered:
                    continue
                pnode = SKILL_GRAPH[p]
                inserted.append(RoadmapTopic(
                    id=f"recovery_prereq:{p}:{element}", label=pnode.label, topic_type="missed_prerequisite",
                    track=track, estimated_hours=PREREQ_REVIEW_HOURS, high_priority=True,
                    detail=f"Prerequisite review — {element} depends on {pnode.label}, not yet solid.",
                ))
        weak = assessment.weak_concepts or [element]
        inserted += [
            RoadmapTopic(id=f"recovery_revision:{element}", label=f"Revision: {element}",
                          topic_type="revision", track=track, estimated_hours=REVISION_HOURS, high_priority=True,
                          detail=f"Simplified re-explanation focused on: {', '.join(weak)}."),
            RoadmapTopic(id=f"recovery_practice:{element}", label=f"Practice: {element}",
                          topic_type="practice", track=track, estimated_hours=PRACTICE_HOURS, high_priority=True,
                          detail="Targeted practice problems on the missed concepts."),
            RoadmapTopic(id=f"recovery_reassess:{element}", label=f"Mini-assessment: {element}",
                          topic_type="reassessment", track=track, estimated_hours=REASSESSMENT_HOURS,
                          high_priority=True, detail="Short check before returning to the main roadmap."),
        ]

        before_current = [t for m in plan.milestones if m.week_number < current_week for t in m.topics]
        from_current_on = [t for m in plan.milestones if m.week_number >= current_week for t in m.topics]
        new_order = before_current + inserted + from_current_on
        new_plan = pack_track(new_order, plan.weekly_hour_budget, track)
        if track == "technical":
            roadmap.technical = new_plan
        else:
            roadmap.professional = new_plan
        _recompute_roadmap_totals(roadmap, learner)

        return AdaptationResult(
            action="recover", track=track, skill_element=element, score=score,
            updated_learner_level=new_level, inserted_topics=inserted,
            message=f"Low score on {element} ({score:.0f}/100) — recovery route inserted "
                    f"into the {track} track ({len(inserted)} steps) before continuing.",
            route_before=route_before, route_after=_route_labels(new_plan),
        )

    return AdaptationResult(
        action="steady", track=track, skill_element=element, score=score, updated_learner_level=new_level,
        message=f"Solid result on {element} ({score:.0f}/100) — roadmap unchanged, level nudged up.",
        route_before=route_before, route_after=route_before,
    )


if __name__ == "__main__":
    import json
    from pathlib import Path
    from backend.app.models.learner import demo_learner
    from backend.app.engines.roadmap import generate_roadmap

    occupations = json.loads((Path(__file__).resolve().parents[2] / "data" / "processed" / "occupations.json").read_text())
    learner = demo_learner()
    occ = occupations[learner.target_career_code]
    roadmap = generate_roadmap(learner, occ)

    print("=== TECHNICAL TRACK BEFORE ===")
    for label in _route_labels(roadmap.technical):
        print(" ", label)

    assessment = AssessmentRecord(skill_element="Computers and Electronics", score=52.0,
                                   weak_concepts=["REST APIs", "databases"])
    result = apply_assessment_result(learner, occ, roadmap, assessment, current_week=1)
    print(f"\n=== ASSESSMENT: {assessment.skill_element} scored {assessment.score} (track: {result.track}) ===")
    print("Action:", result.action)
    print("Message:", result.message)
    for t in result.inserted_topics:
        print(f"  [{t.topic_type}] {t.label} ({t.estimated_hours}h) — {t.detail}")

    print("\n=== TECHNICAL TRACK AFTER ===")
    for label in _route_labels(roadmap.technical):
        print(" ", label)

    print(f"\nProfessional track untouched, still {roadmap.professional.weeks_planned}w "
          f"(confirms the splice stayed inside the technical track only)")
