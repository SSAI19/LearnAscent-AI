"""
Exports a single JSON payload the frontend prototype consumes statically.

This is explicitly DEMO-MODE: the real product would have a FastAPI layer
(not yet built — see docs) serving these engines live per-request. For
this prototype phase, we run the real pipeline once here and bake the
result into JSON so the frontend can be a self-contained file with no
backend process running alongside it. Every number in the export comes
from the actual engines (Phases 1-4) against real O*NET data — nothing in
this file invents roadmap content, only serializes what the engines produced.
"""

import json
from dataclasses import asdict
from pathlib import Path

from backend.app.engines.adaptive import apply_assessment_result
from backend.app.engines.readiness import compute_readiness
from backend.app.engines.roadmap import generate_roadmap
from backend.app.engines.skill_gap import analyze_skill_gap, summarize
from backend.app.models.learner import AssessmentRecord, demo_learner

OUT_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "frontend_demo.json"


def track_to_dict(plan) -> dict:
    return {
        "track": plan.track,
        "weeks_planned": plan.weeks_planned,
        "total_hours": plan.total_hours,
        "weekly_hour_budget": plan.weekly_hour_budget,
        "milestones": [
            {
                "week_number": m.week_number,
                "is_campsite": m.is_campsite,
                "total_hours": m.total_hours,
                "topics": [
                    {
                        "id": t.id, "label": t.label, "topic_type": t.topic_type,
                        "track": t.track, "estimated_hours": t.estimated_hours,
                        "high_priority": t.high_priority, "detail": t.detail,
                    } for t in m.topics
                ],
            } for m in plan.milestones
        ],
    }


def roadmap_to_dict(roadmap) -> dict:
    return {
        "target_career_title": roadmap.target_career_title,
        "weeks_planned": roadmap.weeks_planned,
        "total_topics": roadmap.total_topics,
        "total_estimated_hours": roadmap.total_estimated_hours,
        "fits_target_duration": roadmap.fits_target_duration,
        "overflow_weeks": roadmap.overflow_weeks,
        "technical": track_to_dict(roadmap.technical),
        "professional": track_to_dict(roadmap.professional),
    }


def main():
    occupations = json.loads((Path(__file__).resolve().parents[1] / "data" / "processed" / "occupations.json").read_text())
    learner = demo_learner()
    occ = occupations[learner.target_career_code]

    gap_essential = analyze_skill_gap(learner, occ, source="essential_skills")
    gap_summary = summarize(gap_essential)
    readiness_before = compute_readiness(learner, gap_essential)

    roadmap = generate_roadmap(learner, occ)
    roadmap_before = roadmap_to_dict(roadmap)

    # Live adaptation demo: low-score assessment on a technical, graph-linked
    # element, so the frontend can show the real SQL-prerequisite insertion.
    assessment = AssessmentRecord(skill_element="Computers and Electronics", score=52.0,
                                   weak_concepts=["REST APIs", "databases"])
    adaptation = apply_assessment_result(learner, occ, roadmap, assessment, current_week=1)
    roadmap_after = roadmap_to_dict(roadmap)

    readiness_after = compute_readiness(learner, analyze_skill_gap(learner, occ, source="essential_skills"))

    payload = {
        "learner": {
            "user_id": learner.user_id,
            "target_career_title": learner.target_career_title,
            "target_career_code": learner.target_career_code,
            "experience_level": learner.experience_level,
            "known_tools": sorted(learner.known_tools),
            "available_minutes_per_day": learner.available_minutes_per_day,
            "target_duration_weeks": learner.target_duration_weeks,
        },
        "occupation": {
            "code": occ["code"], "title": occ["title"],
            "job_zone": occ.get("job_zone", {}),
        },
        "skill_gap_summary": gap_summary,
        "readiness_before": asdict(readiness_before),
        "readiness_after": asdict(readiness_after),
        "roadmap_before": roadmap_before,
        "roadmap_after": roadmap_after,
        "adaptation_event": {
            "action": adaptation.action,
            "track": adaptation.track,
            "skill_element": adaptation.skill_element,
            "score": adaptation.score,
            "message": adaptation.message,
            "inserted_topics": [
                {"label": t.label, "topic_type": t.topic_type, "estimated_hours": t.estimated_hours,
                 "detail": t.detail} for t in adaptation.inserted_topics
            ],
            "route_before": adaptation.route_before,
            "route_after": adaptation.route_after,
        },
    }

    OUT_PATH.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {OUT_PATH} ({OUT_PATH.stat().st_size / 1024:.1f} KB)")
    print(f"Readiness before: {readiness_before.readiness_score} -> after: {readiness_after.readiness_score}")
    print(f"Technical track: {roadmap_before['technical']['weeks_planned']}w -> "
          f"{roadmap_after['technical']['weeks_planned']}w")


if __name__ == "__main__":
    main()
