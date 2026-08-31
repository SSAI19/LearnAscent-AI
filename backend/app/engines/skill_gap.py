"""
Skill Gap Analysis engine (Feature 5).

Compares a learner's current skills against a target occupation's Career
Requirement Profile (from Phase 1) and classifies each required skill.

CLASSIFICATION RULE (deterministic, documented here because the spec names
five labels — Mastered / Strong / Developing / Missing / High-priority —
without specifying the numeric rule, so this is a designed policy, not
O*NET data):

  status is decided from the gap between the occupation's required LEVEL
  (O*NET Scale LV, 0-7) and the learner's current level on that skill:
    gap = required_level - learner_level
    - learner_level == 0                         -> "missing"
    - gap <= 0                                    -> "mastered"   (learner meets/exceeds requirement)
    - 0 < gap <= 1.0                              -> "strong"     (nearly there)
    - gap > 1.0                                   -> "developing"

  high_priority is a FLAG layered on top of status, not a sixth status
  value that overwrites it — a skill can be "missing" AND high-priority,
  or "developing" AND high-priority. It's true when:
    status in {"missing", "developing"} AND importance (O*NET IM, 1-5) >= 3.5
  Importance threshold of 3.5 is the same policy choice as above: O*NET
  importance scores for a given occupation's essential skills cluster
  mostly in the 3.0-4.5 range, so 3.5 marks "above-median importance for
  this occupation" rather than an absolute cutoff — documented so it can be
  tuned per-occupation later if the distribution warrants it.

Only skills present in the occupation's `essential_skills` list are scored
here — Knowledge/Abilities/Software feed the same shape but are kept as
separate calls so the UI can group them (Feature 5's "explain why skills
matter" wants skill vs. knowledge vs. tool to read differently).
"""

from dataclasses import dataclass

from backend.app.models.learner import LearnerProfile

HIGH_PRIORITY_IMPORTANCE_THRESHOLD = 3.5
STRONG_GAP_THRESHOLD = 1.0


@dataclass
class SkillGapResult:
    element: str
    element_id: str
    importance: float
    required_level: float
    learner_level: float
    gap: float
    status: str          # "mastered" | "strong" | "developing" | "missing"
    high_priority: bool
    why_it_matters: str


def _why_it_matters(element: str, importance: float, required_level: float) -> str:
    if importance >= 4.0:
        weight = "one of the most important skills"
    elif importance >= 3.0:
        weight = "an important skill"
    else:
        weight = "a supporting skill"
    return (f"{element} is {weight} for this career (importance {importance:.1f}/5), "
            f"typically needed at a proficiency level of {required_level:.1f}/7.")


def analyze_skill_gap(learner: LearnerProfile, occupation: dict,
                       source: str = "essential_skills") -> list[SkillGapResult]:
    """
    source: "essential_skills" | "knowledge" | "abilities" | "transferable_skills"
    — all four share the same {element, importance, level} shape from Phase 1.
    """
    items = occupation.get(source, [])
    results: list[SkillGapResult] = []

    for item in items:
        element = item["element"]
        importance = item.get("importance") or 0.0
        required_level = item.get("level") or 0.0
        learner_level = learner.skill_level(element)
        gap = required_level - learner_level

        if learner_level == 0:
            status = "missing"
        elif gap <= 0:
            status = "mastered"
        elif gap <= STRONG_GAP_THRESHOLD:
            status = "strong"
        else:
            status = "developing"

        high_priority = status in ("missing", "developing") and importance >= HIGH_PRIORITY_IMPORTANCE_THRESHOLD

        results.append(SkillGapResult(
            element=element,
            element_id=item.get("element_id", ""),
            importance=importance,
            required_level=required_level,
            learner_level=learner_level,
            gap=round(gap, 2),
            status=status,
            high_priority=high_priority,
            why_it_matters=_why_it_matters(element, importance, required_level),
        ))

    # highest-priority gaps first: high_priority, then by gap size, then by importance
    results.sort(key=lambda r: (not r.high_priority, -r.gap, -r.importance))
    return results


def summarize(results: list[SkillGapResult]) -> dict:
    total = len(results) or 1
    counts = {"mastered": 0, "strong": 0, "developing": 0, "missing": 0}
    for r in results:
        counts[r.status] += 1
    high_priority = [r.element for r in results if r.high_priority]
    coverage_pct = round(100 * (counts["mastered"] + counts["strong"]) / total, 1)
    return {
        "total_skills": total,
        "counts": counts,
        "coverage_pct": coverage_pct,
        "high_priority_skills": high_priority,
    }


if __name__ == "__main__":
    import json
    from pathlib import Path
    from backend.app.models.learner import demo_learner

    data_path = Path(__file__).resolve().parents[2] / "data" / "processed" / "occupations.json"
    occupations = json.loads(data_path.read_text())

    learner = demo_learner()
    occ = occupations[learner.target_career_code]

    results = analyze_skill_gap(learner, occ, source="essential_skills")
    print(f"Skill gap for {learner.user_id} -> {occ['title']} ({occ['code']})\n")
    for r in results:
        flag = " [HIGH PRIORITY]" if r.high_priority else ""
        print(f"  {r.status.upper():10s} {r.element:30s} learner={r.learner_level:.1f} "
              f"required={r.required_level:.1f} gap={r.gap:+.2f} imp={r.importance:.2f}{flag}")

    print("\nSummary:", json.dumps(summarize(results), indent=2))
