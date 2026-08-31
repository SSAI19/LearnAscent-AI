"""
Personalized Learning Path Generator (Feature 7) — now with two parallel
tracks: TECHNICAL and PROFESSIONAL (your call on the Phase 3 open question).

Merges everything Phase 1-2 built into an actual ordered, time-boxed
roadmap:
  1. Run skill-gap across ALL four O*NET rating categories and classify
     every gap into technical or professional via track_classifier.py
     (grounded in O*NET's own Content Model IDs where the data supports
     it — see that module).
  2. Pull tool gaps from Software Skills — always technical.
  3. Cross-reference against the curated skill graph so prerequisites
     land ahead of what depends on them.
  4. Pack EACH TRACK INDEPENDENTLY into its own weekly milestone list, so
     they can render as two separate paths (e.g. Mountain ridge = technical,
     a parallel base trail = professional) rather than one interleaved list.

TRACK TIME SPLIT IS A DESIGNED POLICY, NOT DATA:
Nothing in the spec or O*NET says how a learner's daily time should divide
between the two tracks. Default here is 70% technical / 30% professional
of `available_minutes_per_day`, each track packed against its own slice of
the weekly budget — tracks run in PARALLEL (same wall-clock weeks), so
overall duration is determined by whichever track needs more weeks, not
the sum of both. Documented here so it's tunable, not hidden.

TIME ESTIMATES ARE A DOCUMENTED HEURISTIC, NOT DATA — see HOURS_PER_GAP_LEVEL
and the TOOL_HOURS_* constants below; O*NET has no "hours to learn this"
field. Replace with real resource-duration data once Feature 8 exists.
"""

from dataclasses import dataclass, field

from backend.app.engines.skill_gap import analyze_skill_gap
from backend.app.engines.skill_graph import SKILL_GRAPH, get_prerequisite_chain
from backend.app.engines.track_classifier import classify_track
from backend.app.models.learner import LearnerProfile

RATING_SOURCES = ["essential_skills", "knowledge", "abilities", "transferable_skills"]

HOURS_PER_GAP_LEVEL = 4.0
PROFESSIONAL_HOURS_PER_GAP_LEVEL = 1.5   # soft/foundational skills build through practice and
                                          # ongoing work, not concentrated study time the way a
                                          # technical topic does — same curated-heuristic caveat
                                          # as HOURS_PER_GAP_LEVEL, just track-specific.
MIN_HOURS_PER_TOPIC = 2.0
MIN_HOURS_PER_TOPIC_PROFESSIONAL = 1.0
TOOL_HOURS_HIGH_PRIORITY = 15.0
TOOL_HOURS_MEDIUM_PRIORITY = 8.0
TOOL_HOURS_LOW_PRIORITY = 4.0
CAMPSITE_EVERY_N_WEEKS = 4
MIN_RELEVANT_IMPORTANCE = 3.0
MAX_TOPICS_PER_CATEGORY = 8

# Curated policy — see module docstring.
TECHNICAL_TIME_SHARE = 0.70
PROFESSIONAL_TIME_SHARE = 0.30


@dataclass
class RoadmapTopic:
    id: str
    label: str
    topic_type: str
    track: str              # "technical" | "professional"
    estimated_hours: float
    high_priority: bool
    graph_node_id: str | None = None
    detail: str = ""


@dataclass
class Milestone:
    week_number: int
    topics: list[RoadmapTopic] = field(default_factory=list)
    total_hours: float = 0.0
    is_campsite: bool = False


@dataclass
class TrackPlan:
    track: str
    milestones: list[Milestone] = field(default_factory=list)
    weeks_planned: int = 0
    total_hours: float = 0.0
    weekly_hour_budget: float = 0.0


@dataclass
class Roadmap:
    target_career_title: str
    technical: TrackPlan
    professional: TrackPlan
    weeks_planned: int = 0          # overall = max(technical.weeks, professional.weeks)
    total_topics: int = 0
    total_estimated_hours: float = 0.0
    fits_target_duration: bool = True
    overflow_weeks: int = 0


def _match_tool_to_graph_node(tool_name: str) -> str | None:
    tool_lower = tool_name.lower()
    for node_id, node in SKILL_GRAPH.items():
        if node.label.lower() in tool_lower or tool_lower in node.label.lower():
            return node_id
    return None


def _gather_skill_topics(learner: LearnerProfile, occupation: dict) -> list[RoadmapTopic]:
    topics: list[RoadmapTopic] = []
    seen_elements: set[str] = set()
    for source in RATING_SOURCES:
        results = analyze_skill_gap(learner, occupation, source=source)
        category_topics: list[RoadmapTopic] = []
        for r in results:
            if r.status == "mastered":
                continue
            if r.importance < MIN_RELEVANT_IMPORTANCE:
                continue
            if r.status == "strong" and not r.high_priority:
                continue
            if r.element in seen_elements:
                continue
            track = classify_track(source, r.element_id, r.element)
            per_level = HOURS_PER_GAP_LEVEL if track == "technical" else PROFESSIONAL_HOURS_PER_GAP_LEVEL
            min_hours = MIN_HOURS_PER_TOPIC if track == "technical" else MIN_HOURS_PER_TOPIC_PROFESSIONAL
            hours = max(min_hours, round(r.gap * per_level, 1))
            topic_type = "onet_skill" if source == "essential_skills" else f"onet_{source.split('_')[0]}"
            category_topics.append(RoadmapTopic(
                id=f"{source}:{r.element_id or r.element}", label=r.element, topic_type=topic_type,
                track=track, estimated_hours=hours, high_priority=r.high_priority, detail=r.why_it_matters,
            ))
        for t in category_topics[:MAX_TOPICS_PER_CATEGORY]:
            seen_elements.add(t.label)
            topics.append(t)
    return topics


def _gather_tool_topics(learner: LearnerProfile, occupation: dict, max_tools: int = 6) -> list[RoadmapTopic]:
    candidates = [s for s in occupation.get("software_skills", [])
                  if (s["hot_technology"] or s["in_demand"]) and not learner.knows_tool(s["name"])]
    # Some occupations have O*NET technology entries but none labelled Hot
    # Technology/In Demand.  Keep their actual occupation-specific tools in
    # the journey instead of replacing them with tools from another career.
    if not candidates:
        candidates = [s for s in occupation.get("software_skills", [])
                      if not learner.knows_tool(s["name"])]
    dedup: dict[str, dict] = {}
    for s in candidates:
        if s["name"] not in dedup:
            dedup[s["name"]] = s
    ranked = sorted(dedup.values(), key=lambda s: (-(s["hot_technology"] and s["in_demand"]),
                                                     -s["hot_technology"], -s["in_demand"]))[:max_tools]
    topics = []
    for s in ranked:
        if s["hot_technology"] and s["in_demand"]:
            hours, priority = TOOL_HOURS_HIGH_PRIORITY, True
        elif s["hot_technology"] or s["in_demand"]:
            hours, priority = TOOL_HOURS_MEDIUM_PRIORITY, True
        else:
            hours, priority = TOOL_HOURS_LOW_PRIORITY, False
        node_id = _match_tool_to_graph_node(s["name"])
        topics.append(RoadmapTopic(
            id=f"tool:{s['name']}", label=s["name"], topic_type="tool", track="technical",
            estimated_hours=hours, high_priority=priority, graph_node_id=node_id,
            detail=f"{'Hot technology. ' if s['hot_technology'] else ''}"
                   f"{'In demand. ' if s['in_demand'] else ''}Category: {s['category']}.",
        ))
    return topics


def expand_prerequisites(topics: list[RoadmapTopic], learner: LearnerProfile) -> list[RoadmapTopic]:
    """Public (used by adaptive.py too): insert not-yet-known prerequisite
    chains ahead of any topic linked to a skill-graph node."""
    mastered_tool_ids = {node_id for node_id, node in SKILL_GRAPH.items() if learner.knows_tool(node.label)}
    expanded: list[RoadmapTopic] = []
    seen_ids: set[str] = set()

    def add(topic: RoadmapTopic):
        if topic.id not in seen_ids:
            expanded.append(topic)
            seen_ids.add(topic.id)

    for topic in topics:
        if topic.graph_node_id:
            chain = get_prerequisite_chain(topic.graph_node_id)
            for node_id in chain[:-1]:
                if node_id in mastered_tool_ids:
                    continue
                node = SKILL_GRAPH[node_id]
                add(RoadmapTopic(
                    id=f"prereq:{node_id}", label=node.label, topic_type="prerequisite", track="technical",
                    estimated_hours=TOOL_HOURS_MEDIUM_PRIORITY, high_priority=True,
                    graph_node_id=node_id, detail=f"Curated prerequisite for {topic.label}.",
                ))
        add(topic)
    return expanded


def pack_track(topics: list[RoadmapTopic], weekly_budget: float, track_name: str) -> TrackPlan:
    ordered = sorted(topics, key=lambda t: (not t.high_priority,))
    milestones: list[Milestone] = []
    week = 1
    current = Milestone(week_number=week)
    for topic in ordered:
        if current.total_hours + topic.estimated_hours > weekly_budget and current.topics:
            milestones.append(current)
            week += 1
            current = Milestone(week_number=week)
        current.topics.append(topic)
        current.total_hours = round(current.total_hours + topic.estimated_hours, 1)
    if current.topics:
        milestones.append(current)
    for m in milestones:
        m.is_campsite = (m.week_number % CAMPSITE_EVERY_N_WEEKS == 0)
    return TrackPlan(
        track=track_name, milestones=milestones, weeks_planned=len(milestones),
        total_hours=round(sum(t.estimated_hours for t in topics), 1), weekly_hour_budget=weekly_budget,
    )


def generate_roadmap(learner: LearnerProfile, occupation: dict) -> Roadmap:
    skill_topics = _gather_skill_topics(learner, occupation)
    tool_topics = _gather_tool_topics(learner, occupation)
    all_topics = expand_prerequisites(skill_topics + tool_topics, learner)

    technical_topics = [t for t in all_topics if t.track == "technical"]
    professional_topics = [t for t in all_topics if t.track == "professional"]

    daily_hours = learner.available_minutes_per_day / 60
    weekly_total = daily_hours * 7
    tech_budget = round(weekly_total * TECHNICAL_TIME_SHARE, 1)
    prof_budget = round(weekly_total * PROFESSIONAL_TIME_SHARE, 1)

    technical_plan = pack_track(technical_topics, tech_budget, "technical")
    professional_plan = pack_track(professional_topics, prof_budget, "professional")

    weeks_planned = max(technical_plan.weeks_planned, professional_plan.weeks_planned)
    fits = weeks_planned <= learner.target_duration_weeks
    overflow = max(0, weeks_planned - learner.target_duration_weeks)

    return Roadmap(
        target_career_title=learner.target_career_title,
        technical=technical_plan, professional=professional_plan,
        weeks_planned=weeks_planned, total_topics=len(all_topics),
        total_estimated_hours=round(technical_plan.total_hours + professional_plan.total_hours, 1),
        fits_target_duration=fits, overflow_weeks=overflow,
    )


def apply_roadmap_to_learner(learner: LearnerProfile, roadmap: Roadmap) -> None:
    learner.total_milestones = len(roadmap.technical.milestones) + len(roadmap.professional.milestones)
    learner.completed_milestones = 0


def _print_track(plan: TrackPlan):
    for m in plan.milestones:
        tag = " [CAMPSITE]" if m.is_campsite else ""
        print(f"  Week {m.week_number}{tag} — {m.total_hours}h")
        for t in m.topics:
            flag = " *" if t.high_priority else ""
            print(f"      [{t.topic_type:16s}] {t.label:32s} {t.estimated_hours:5.1f}h{flag}")


if __name__ == "__main__":
    import json
    from pathlib import Path
    from backend.app.models.learner import demo_learner

    occupations = json.loads((Path(__file__).resolve().parents[2] / "data" / "processed" / "occupations.json").read_text())
    learner = demo_learner()
    occ = occupations[learner.target_career_code]
    roadmap = generate_roadmap(learner, occ)

    print(f"Roadmap for {learner.user_id} -> {roadmap.target_career_title}")
    print(f"Total topics: {roadmap.total_topics}  |  Total est. hours: {roadmap.total_estimated_hours}")
    print(f"Weeks planned (parallel tracks): {roadmap.weeks_planned}  |  Target: {learner.target_duration_weeks}  "
          f"|  Fits: {roadmap.fits_target_duration}"
          f"{f' (overflow {roadmap.overflow_weeks}w)' if roadmap.overflow_weeks else ''}\n")

    print(f"=== TECHNICAL TRACK ({roadmap.technical.weeks_planned}w, "
          f"{roadmap.technical.total_hours}h, budget {roadmap.technical.weekly_hour_budget}h/wk) ===")
    _print_track(roadmap.technical)
    print(f"\n=== PROFESSIONAL TRACK ({roadmap.professional.weeks_planned}w, "
          f"{roadmap.professional.total_hours}h, budget {roadmap.professional.weekly_hour_budget}h/wk) ===")
    _print_track(roadmap.professional)
