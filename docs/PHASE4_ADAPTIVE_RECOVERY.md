# Phase 4 — Adaptive Learning Path + Failure Recovery (Features 9, 11)

## What was built
`backend/app/engines/adaptive.py` takes one freshly-taken assessment and
decides what happens to the roadmap:
- **score ≥ 85 → accelerate**: skill marked mastered (level nudged up),
  any still-queued roadmap topics for that exact element are pruned as
  redundant.
- **score 70-84 → steady**: level nudged up proportionally, roadmap
  structure untouched — solid but not yet demo-worthy of restructuring.
- **score < 70 → recover**: builds the Feature 11 chain — [missed
  prerequisite review, if the curated skill graph links one] → revision →
  practice → mini-assessment — and splices it into the roadmap at the
  learner's current week, pushing everything after it back and
  re-numbering. Never surfaces as "you failed"; the route change is the
  entire message.

A failing score never regresses the learner's stored skill level below
where it already was — it's evidence of "not yet," not proof of negative
skill. This matches the spec's "never simply show 'You failed'" framing at
the data-model level as well as the UI-copy level.

## Verified end-to-end (demo learner, Data Scientists target)
Simulated a 52/100 assessment on "Computers and Electronics" — an O*NET
knowledge element that happens to link, via the curated graph, to the
`backend_apis` node (prerequisites: `python`, `sql`). The learner's
`known_tools` has Python but not SQL, so the engine correctly surfaced
**SQL** as the missing prerequisite and inserted it as the first recovery
step, before revision/practice/reassessment — without me hand-coding "SQL"
anywhere in the demo; it fell out of the graph traversal. Route before/
after was captured and printed to confirm the splice actually reorders
weeks (W1-4 became the recovery chain, everything else pushed to W5+)
rather than just appending at the end.

A second simulated assessment (92/100 on Reading Comprehension) correctly
triggered the accelerate branch and pruned the now-redundant topic.

## Known scope limits, stated plainly
- Missed-prerequisite detection only fires for O*NET elements that have a
  curated graph node with a matching `onet_element` link — most O*NET
  elements don't have one (the graph is a documented starter set from
  Phase 2, not exhaustive). Recovery degrades gracefully to
  revision+practice+reassessment without a prerequisite step in that case,
  rather than fabricating a prerequisite.
- "Learning speed" (mentioned in Feature 9's spec bullet list) isn't
  modeled yet — this phase reacts to a single assessment result, not a
  trend across several. Would need timestamped assessment history and a
  pace calculation; deferred rather than guessed at.
- User feedback (also in Feature 9's list) has no input path yet — no UI
  exists to collect it.

## Not yet done
- Resource recommendation engine (Feature 8)
- Frontend — nothing built yet has a UI. This is the natural next stopping
  point before moving to the immersive frontend, since Phases 1-4 now
  cover enough of the data/logic layer (occupation matching, skill gaps,
  prerequisite graph, roadmap generation, adaptive recovery) to give the
  Learner DNA and Mountain Journey screens real data to render, including
  a genuine "watch the route change" moment for the live-demo screen.
- Database persistence, API layer, AI provider integration (mentor,
  resume/JD analysis, multilingual) — still require real provider keys to
  be more than a labeled demo-mode stub.
