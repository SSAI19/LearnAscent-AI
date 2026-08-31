# Phase 1 — O*NET Data Ingestion Pipeline

## What this phase delivers
- `backend/scripts/ingest_onet.py` — reads all 14 raw O*NET files, normalizes
  them, and writes:
  - `backend/data/processed/occupations.json` — 1,016 occupations, each with
    a full Career Requirement Profile (essential skills, software/tools,
    knowledge, abilities, transferable skills, training & experience, job
    zone, RIASEC interests, emerging tasks).
  - `backend/data/processed/onet.db` — the same data in queryable SQLite
    form, indexed by occupation code and by element name, for the engines
    in Phase 2 that need to query "which occupations need skill X" rather
    than "what does occupation Y need."
  - `occupation_search_index.json`, `education_categories.json`,
    `task_categories.json` — supporting lookups.
- `backend/app/ingestion/occupation_matcher.py` — resolves free-text career
  input ("I want to become a cybersecurity analyst") to ranked O*NET-SOC
  codes. This is the entry point for Feature 4 (Goal Reverse Engineering).

## Real structure, not assumptions
Every column referenced in the pipeline was confirmed by directly opening
the files before writing code against them (per the brief's own
instruction). Two things in particular were **not** what a naive read of
the spec would assume, and getting them wrong would have silently broken
downstream features:

1. **Software Skills**: `Element Name` is a broad category ("Development
   environment software"); the actual tool name ("Python", "GitHub",
   "Adobe Photoshop") is in `Workplace Example`. Using `Element Name` as
   the tool name — the more "obvious" column — would have made the
   resource-recommendation engine (Feature 8) recommend categories instead
   of real tools.
2. **Career Interest Types**: the `IH` (Interest High-Point) rows don't
   contain the RIASEC dimension name — `Element Name` is a rank label
   ("First/Second/Third Interest High-Point") and `Data Value` is a 1–6
   code pointing at the dimension. Decoded and verified against a real
   occupation (Software Developers: 1st→Investigative, 2nd→Conventional,
   matching its actual highest two RIASEC scores of 6.05 and 5.62).

## A real data-coverage gap worth flagging
O*NET-SOC titles are official occupation names, not industry slang —
"Information Security Analysts," not "cybersecurity"; there's no "UX
Designer" or "Cloud Architect" or "ML Engineer" as a literal title. O*NET
normally publishes an **Alternate Titles** crosswalk for exactly this, but
it wasn't among the 14 files provided. Rather than let common queries
silently return nothing, `occupation_matcher.py`:
- weights token overlap by inverse document frequency, so a rare word like
  "cybersecurity" or "architect" counts for more than a common title word
  like "specialist" or "machine" (this alone fixed "machine learning
  engineer" incorrectly matching "Sewing Machine Operators"), and
- applies a small **curated** alias list (clearly marked as curated, not
  O*NET data, in the source file) for the ~20 most common industry terms
  that don't literally appear in O*NET titles.

If you have access to O*NET's Alternate Titles file, dropping it into
`backend/data/raw/` and extending the ingestion script would replace the
curated list with real crosswalk data — worth doing before this goes past
prototype stage.

## Verified output (spot-checked, not just "ran without errors")
For O*NET-SOC 15-1252.00 (Software Developers):
- Job Zone 4 ("Considerable Preparation Needed," bachelor's degree typical)
- Top essential skills by importance: Critical Thinking, Reading
  Comprehension, Active Learning, Active Listening, Writing
- In-demand tools: AWS, Docker, Git, GitHub, JavaScript, HTML/CSS, Go, C++
- Hot technologies include AWS, Ansible, Apache Airflow, Amazon Redshift
- RIASEC high points: Investigative (1st), Conventional (2nd) — matches raw
  scores directly

SQLite and JSON outputs were cross-checked against each other and against
the raw Excel rows for this occupation; they match.

## Not yet done (Phase 2+)
- Skill-gap classifier, prerequisite skill graph, readiness scoring engine
- Database models for users/learners/progress (this phase is O*NET
  reference data only — no learner data model yet)
- API layer, frontend, AI provider integration
