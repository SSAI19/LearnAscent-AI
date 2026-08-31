# Phase 3 — Personalized Learning Path Generator (Feature 7)

## What was built
`backend/app/engines/roadmap.py` merges skill-gap analysis across ALL four
O*NET rating categories (not just one, fixing the Phase 2 limitation) with
Software Skills tool gaps and the curated prerequisite graph, then packs
the result into weekly milestones sized by the learner's stated available
time, with every 4th week marked as a campsite checkpoint (Feature 10).

`LearnerProfile` gained a `known_tools: set[str]` field, separate from
`skills`. This was a real gap, not a stylistic choice: O*NET's rating
tables (Essential Skills, Knowledge, Abilities, Transferable Skills) use a
0-7 proficiency scale, but Software Skills has no proficiency scale at
all — just presence/hot-technology/in-demand flags. Conflating "Python
level 4/7" with "knows Python: yes/no" would have been wrong in both
directions.

## A bug caught before shipping: the roadmap dumped irrelevant topics
First run produced a 131-week, 1,156-hour roadmap for a Data Scientist
target, including "Trunk Strength," "Static Strength," "Stamina," and
"Peripheral Vision." Root cause, confirmed against real data before
patching: O*NET rates every occupation on all ~166 elements across the
four tables, and most score at floor importance (1.0/5) for any given
job — Data Scientists' physical-ability importances top out around 2.25,
while the skills that actually matter (Critical Thinking, Mathematics,
Reading Comprehension) sit at 3.5-4.25. There's a real cliff around 3.0.
Fixed with two filters, both documented in the module as designed policy:
  - `MIN_RELEVANT_IMPORTANCE = 3.0` — below this, an element isn't
    material to the role, independent of whether the learner has it.
  - `MAX_TOPICS_PER_CATEGORY = 8` — keeps the path "prioritized" rather
    than exhaustive, matching the feature's own name.
This took total topics from 131 down to 28 for the same learner/occupation
pair, and removed every physically-irrelevant ability from the plan.

## Verified output (demo learner, target: Data Scientists, 30 min/day, 12wk goal)
- 28 topics total: 7 essential skills, several knowledge/ability/
  transferable-skill gaps, and 6 tool gaps (AWS, Hadoop, Spark, C++, Git,
  Azure) — all pulled from the occupation's actual hot-technology/
  in-demand software list, not invented.
- `fits_target_duration: False`, `overflow_weeks: 16` — at a 3.5h/week
  budget (30 min/day), 28 substantive topics genuinely don't fit in 12
  weeks. The engine reports this honestly rather than silently truncating
  the plan or pretending it fits — this matters given the spec's own
  instruction not to overstate what the platform can promise a learner.

## Open product question, not resolved here
Generic O*NET workplace skills (Reading Comprehension, Writing, Speaking)
currently sit in the roadmap alongside concrete technical topics (AWS,
Git) with the same treatment — "learn Reading Comprehension: 18.5 hours"
reads oddly for a student audience, even though the underlying gap
analysis is correct (self-reported skills didn't cover them, so they're
genuinely unassessed). Worth deciding in Phase 4/frontend: whether to
separate a "professional/soft skills" track visually from the technical
track, rather than interleaving them by raw priority score. Flagging now
rather than making that call unilaterally, since it changes how the
Mountain Journey's zones (Feature 6: base/forest/rocky/high-altitude/
summit) should map onto topic types.

## Not yet done
- Adaptive Learning Path / Failure Recovery (Features 9, 11) — the
  roadmap above is static; nothing yet re-routes it based on assessment
  performance
- Resource recommendation engine (Feature 8) — topics have no attached
  learning resources yet; time estimates are a documented heuristic, not
  derived from real resource durations
- Database persistence, API layer, frontend, AI provider integration
