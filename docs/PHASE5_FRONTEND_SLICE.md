# Phase 5 — Frontend: a connected slice (Learner DNA + Mountain Journey + Live Adaptation)

## What was built
`frontend/index.html` + `app.js` — a single self-contained prototype (Three.js
DNA scene, SVG mountain journey, live adaptation demo) wired to REAL output
from the Phase 1-4 Python engines, not placeholder content. `frontend/
build_demo_data.py` converts the engines' JSON export into the flattened
shape the frontend consumes (`demo_data.js`), so there's a clean, re-runnable
path from "change the learner/occupation" to "see it in the UI."

Two backend changes came first, both from your Phase 3/4 open questions:
- **Two-track roadmap**: `roadmap.py` now packs technical and professional
  topics into independent, parallel weekly plans (`Roadmap.technical` /
  `.professional`), each with its own time budget (70/30 split of daily
  minutes — a documented policy, not data) and its own hour heuristic
  (professional topics cost less per gap-level, since they build through
  practice rather than concentrated study — also documented).
- **Track-aware adaptive engine**: `adaptive.py` now splices a recovery
  route into whichever track the assessed skill actually belongs to
  (via `track_classifier.py`, grounded in O*NET's own `2.A`/`2.B.3`/etc.
  Content Model IDs — confirmed against real element IDs before writing
  the classifier, not guessed).

## Verified by actually rendering it, not by inspection
This environment has Playwright with a working Chromium install. Rather
than ship HTML/JS I couldn't observe running, I rendered the page headless,
captured console/page errors, and screenshotted every section — including
clicking the live "Run assessment result" button and confirming the DOM
actually changed:
- 0 console/page errors.
- Technical track: 8 nodes before → 12 after (matches the engine's real
  4-step recovery insertion).
- Readiness stat counts 0 → 13 (matches `readiness_before`/`_after` from
  the engine, not an invented number).
- Recovery nodes render in coral on the technical ridge; the professional
  trail is confirmed untouched (still 20 nodes) — matching the Phase 4
  design goal that a track's recovery splice doesn't disturb the other.

## Bugs caught by that verification, fixed before shipping
- **Tooltip truncation cut mid-sentence** ("...typically needed at a
  proficiency level of · 23.4h" — the actual number was chopped by a
  fixed `[:140]` slice). Fixed with word-boundary truncation in a proper
  script (`build_demo_data.py`) instead of an inline one-liner, so it's
  reusable when the learner/occupation changes.
- Confirmed CDN failures in the sandbox's own test run (Three.js, Google
  Fonts) were the bash tool's network allowlist, not the app — verified by
  swapping in a locally-npm-installed Three.js for the test only; the
  shipped file still references the CDN, which a real browser reaches fine.

## Known simplifications, stated plainly
- The DNA's "gold energy" fraction is `0.15 + readiness/100 * 0.55` — a
  **display curve**, not altered data. A literal 1:1 mapping of a
  beginner's real readiness score (often single digits) would leave the
  DNA almost entirely dark, contradicting the spec's own "small amount of
  subtle gold energy visible at the start." The number in the stat card is
  the real, unscaled score; only the visual mapping is designed. Documented
  in `app.js` at the point it's applied.
- This is one learner/occupation pair (the demo persona) baked into a
  static JS file — there's no live backend serving different learners yet.
  That's Phase 6+ (API layer + database), not pretended to exist here.
- Skill Constellation, Campsite breakpoint interactions, and the AI mentor
  conversation are not built — the mentor here is a static message tied to
  one event, not a conversational agent (that needs a real AI provider key,
  per the original spec's own instruction not to fake API calls as
  succeeding).

## Not yet done
- Resource recommendation engine (Feature 8)
- API layer + database persistence (still O*NET reference data + one
  in-memory demo learner, no multi-user backend)
- AI provider integration (mentor conversations, resume/JD analysis,
  multilingual) — needs real provider keys to be more than a labeled stub
- Remaining frontend screens from the spec's 18-screen flow (only 3 of 18
  are built, deliberately, as the "connected slice" you asked for)
