"""
Converts backend/data/processed/frontend_demo.json (Phase 1-4 engine output)
into frontend/demo_data.js — a flattened, frontend-friendly shape, baked in
as a JS const so the prototype has no runtime fetch/CORS dependency.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "backend" / "data" / "processed" / "frontend_demo.json"
OUT = ROOT / "frontend" / "demo_data.js"

MAX_DETAIL_LEN = 150


def truncate(detail: str) -> str:
    if len(detail) <= MAX_DETAIL_LEN:
        return detail
    cut = detail[:MAX_DETAIL_LEN].rsplit(" ", 1)[0]
    return cut.rstrip(".,;: ") + "…"


def flatten(track: dict) -> list[dict]:
    topics = []
    for m in track["milestones"]:
        for t in m["topics"]:
            topics.append({
                "week": m["week_number"], "campsite": m["is_campsite"],
                "label": t["label"], "type": t["topic_type"],
                "hours": t["estimated_hours"], "priority": t["high_priority"],
                "detail": truncate(t["detail"]),
            })
    return topics


def main():
    d = json.loads(SRC.read_text())
    payload = {
        "learner": d["learner"],
        "occupation": {"title": d["occupation"]["title"], "code": d["occupation"]["code"],
                        "jobZone": d["occupation"]["job_zone"].get("name", "")},
        "readinessBefore": d["readiness_before"]["readiness_score"],
        "readinessAfter": d["readiness_after"]["readiness_score"],
        "nextAction": d["readiness_after"]["next_action"],
        "technicalBefore": flatten(d["roadmap_before"]["technical"]),
        "professionalBefore": flatten(d["roadmap_before"]["professional"]),
        "technicalAfter": flatten(d["roadmap_after"]["technical"]),
        "professionalAfter": flatten(d["roadmap_after"]["professional"]),
        "adaptation": d["adaptation_event"],
    }
    OUT.write_text("const DEMO_DATA = " + json.dumps(payload) + ";")
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
