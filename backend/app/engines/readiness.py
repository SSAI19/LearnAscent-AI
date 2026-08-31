"""
Skill Passport / Career Readiness engine (Feature 21).

Produces an EXPLAINABLE readiness score (0-100) from configurable weighted
components, plus what contributed to it, what evidence is missing, and the
single next highest-priority action — per the spec's explicit requirement
to show what contributed to the score and never claim it guarantees
employability.

Components (defaults sum to 1.0, all configurable):
  - skill_coverage   0.40  from skill-gap engine: weighted by importance,
                             not a flat % of skills mastered
  - assessment_perf  0.25  average of recent assessment scores (0 if none
                             taken yet — explicitly surfaced, not hidden)
  - project_evidence 0.20  verified project count vs. a small target,
                             capped so one project can't fully cover it
  - milestones       0.15  roadmap milestones completed / total

If a component has no data yet (e.g. no assessments taken), it scores 0 for
that component AND is listed under `missing_evidence` — a 0 from "not done
yet" must never be visually indistinguishable from a 0 from "did badly."
"""

from dataclasses import dataclass, field

from backend.app.engines.skill_gap import SkillGapResult
from backend.app.models.learner import LearnerProfile

DEFAULT_WEIGHTS = {
    "skill_coverage": 0.40,
    "assessment_performance": 0.25,
    "project_evidence": 0.20,
    "milestones": 0.15,
}
PROJECT_EVIDENCE_TARGET = 3  # projects at which this component maxes out


@dataclass
class ReadinessBreakdown:
    component: str
    weight: float
    raw_score_0_100: float
    weighted_contribution: float
    note: str


@dataclass
class ReadinessResult:
    readiness_score: float
    breakdown: list[ReadinessBreakdown] = field(default_factory=list)
    missing_evidence: list[str] = field(default_factory=list)
    next_action: str = ""
    disclaimer: str = ("This score reflects progress on this platform's roadmap and "
                        "assessments. It is an application-generated estimate, not a "
                        "guarantee of employability or hiring outcomes.")


def _skill_coverage_score(gap_results: list[SkillGapResult]) -> float:
    """Importance-weighted coverage: mastering a high-importance skill counts
    for more than mastering a low-importance one, matching how the gap
    engine already weights priority."""
    if not gap_results:
        return 0.0
    total_weight = sum(r.importance for r in gap_results) or 1.0
    earned = sum(r.importance for r in gap_results if r.status in ("mastered", "strong"))
    return round(100 * earned / total_weight, 1)


def _assessment_score(learner: LearnerProfile) -> tuple[float, str]:
    if not learner.assessments:
        return 0.0, "No assessments taken yet."
    avg = sum(a.score for a in learner.assessments) / len(learner.assessments)
    return round(avg, 1), f"Average of {len(learner.assessments)} assessment(s)."


def _project_evidence_score(learner: LearnerProfile) -> tuple[float, str]:
    verified = [p for p in learner.projects if p.quality_score is not None]
    if not verified:
        return 0.0, "No reviewed projects yet."
    count_score = min(len(verified), PROJECT_EVIDENCE_TARGET) / PROJECT_EVIDENCE_TARGET
    quality_avg = sum(p.quality_score for p in verified) / len(verified)
    combined = 100 * count_score * (quality_avg / 100)
    return round(combined, 1), f"{len(verified)} reviewed project(s), avg quality {quality_avg:.0f}/100."


def _milestone_score(learner: LearnerProfile) -> tuple[float, str]:
    if learner.total_milestones == 0:
        return 0.0, "Roadmap not generated yet."
    pct = 100 * learner.completed_milestones / learner.total_milestones
    return round(pct, 1), f"{learner.completed_milestones}/{learner.total_milestones} milestones complete."


def compute_readiness(learner: LearnerProfile, gap_results: list[SkillGapResult],
                       weights: dict | None = None) -> ReadinessResult:
    w = weights or DEFAULT_WEIGHTS
    breakdown: list[ReadinessBreakdown] = []
    missing_evidence: list[str] = []

    coverage = _skill_coverage_score(gap_results)
    breakdown.append(ReadinessBreakdown(
        "skill_coverage", w["skill_coverage"], coverage, round(coverage * w["skill_coverage"], 1),
        "Importance-weighted share of required skills at Strong/Mastered level."))

    assess_score, assess_note = _assessment_score(learner)
    breakdown.append(ReadinessBreakdown(
        "assessment_performance", w["assessment_performance"], assess_score,
        round(assess_score * w["assessment_performance"], 1), assess_note))
    if not learner.assessments:
        missing_evidence.append("No assessments completed — take one to verify skill levels.")

    proj_score, proj_note = _project_evidence_score(learner)
    breakdown.append(ReadinessBreakdown(
        "project_evidence", w["project_evidence"], proj_score,
        round(proj_score * w["project_evidence"], 1), proj_note))
    if proj_score == 0.0:
        missing_evidence.append("No reviewed projects — submit a project for skill verification.")

    milestone_score, milestone_note = _milestone_score(learner)
    breakdown.append(ReadinessBreakdown(
        "milestones", w["milestones"], milestone_score,
        round(milestone_score * w["milestones"], 1), milestone_note))
    if learner.total_milestones == 0:
        missing_evidence.append("No roadmap generated yet.")

    total = round(sum(b.weighted_contribution for b in breakdown), 1)

    high_priority = [r for r in gap_results if r.high_priority]
    if high_priority:
        next_action = f"Focus next on '{high_priority[0].element}' — high-priority gap for this career."
    elif missing_evidence:
        next_action = missing_evidence[0]
    else:
        next_action = "Keep progressing through the roadmap — no urgent gaps detected."

    return ReadinessResult(
        readiness_score=total, breakdown=breakdown,
        missing_evidence=missing_evidence, next_action=next_action,
    )


if __name__ == "__main__":
    import json
    from pathlib import Path
    from backend.app.models.learner import demo_learner
    from backend.app.engines.skill_gap import analyze_skill_gap

    data_path = Path(__file__).resolve().parents[2] / "data" / "processed" / "occupations.json"
    occupations = json.loads(data_path.read_text())

    learner = demo_learner()
    occ = occupations[learner.target_career_code]
    gap_results = analyze_skill_gap(learner, occ, source="essential_skills")

    result = compute_readiness(learner, gap_results)
    print(f"Career Readiness for {learner.user_id} -> {occ['title']}\n")
    print(f"Overall score: {result.readiness_score}/100\n")
    for b in result.breakdown:
        print(f"  {b.component:24s} raw={b.raw_score_0_100:5.1f}  weight={b.weight:.2f}  "
              f"contributes={b.weighted_contribution:5.1f}  ({b.note})")
    print("\nMissing evidence:")
    for m in result.missing_evidence:
        print(f"  - {m}")
    print(f"\nNext action: {result.next_action}")
    print(f"\nDisclaimer: {result.disclaimer}")
