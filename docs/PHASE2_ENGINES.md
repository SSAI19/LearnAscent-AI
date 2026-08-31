# Phase 2 — Deterministic Engines

No AI calls in this phase — everything here is explainable, rule-based, and
testable against real O*NET data with no API key required.

## What was built
- `backend/app/models/learner.py` — `LearnerProfile` data model. Skill
  levels use O*NET's own 0-7 Level scale on purpose, so learner skills and
  occupation requirements are directly comparable with no conversion step.
- `backend/app/engines/skill_gap.py` (Feature 5) — classifies each required
  skill as mastered/strong/developing/missing, with a `high_priority` flag
  layered on top (not a 6th mutually-exclusive status). The exact
  thresholds (gap ≤ 1.0 = "strong", importance ≥ 3.5 = high-priority
  eligible) are a **designed policy**, not O*NET data — documented in the
  file's docstring since the spec names the five labels but not the
  numeric rule.
- `backend/app/engines/skill_graph.py` (Feature 6) — curated prerequisite
  graph, separate from O*NET (which has no prerequisite relationships at
  all in the files provided). Every edge is marked `source="curated"`.
  Provides topological prerequisite chains and locked/available/mastered
  state computation for the Skill Constellation UI (Feature 11).
- `backend/app/engines/readiness.py` (Feature 21) — weighted, explainable
  readiness score (skill coverage 40%, assessment performance 25%, project
  evidence 20%, milestones 15%). A component with no data yet scores 0 AND
  is separately listed under `missing_evidence`, so "haven't done this yet"
  is never visually the same as "did badly." Carries the spec-required
  disclaimer that this isn't an employability guarantee.

## Verified, not just run
- Skill gap engine tested against the demo (beginner) learner: correctly
  shows 8/10 essential skills as "missing" and flags the 7 that are also
  high-importance — no false "mastered" on skills the learner never
  reported.
- Readiness engine tested at two points: the beginner (score 0, every
  component correctly attributed to "not done yet," not "failed") and a
  hand-built "progressed" learner with assessments/projects/milestones
  (score 64.2, breakdown and next-action both shift correctly as gaps
  close — confirms the score actually moves with real progress rather than
  being a static/broken calculation).

## Known limitation worth flagging now
The skill-gap engine currently only compares against ONE `source` category
per call (essential_skills, knowledge, abilities, or transferable_skills).
A learner's self-reported "Programming" skill correctly does NOT show up
against Data Scientists' essential_skills gap, because O*NET's Essential
Skills taxonomy is generic workplace skills (reading, critical thinking),
not domain tools — "Programming" lives under Knowledge/Software Skills.
The Personalized Learning Path Generator (next) needs to run the gap
engine across all four sources and merge results, or a learner's real
technical skills will be invisible to the roadmap.

## Not yet done
- Learning Path Generator (Feature 7) — merges skill-gap across all
  sources + skill graph ordering into an actual roadmap
- Adaptive Learning Path / Failure Recovery (Features 9, 11)
- Resource recommendation engine (Feature 8)
- Database persistence, API layer, frontend, AI provider integration
