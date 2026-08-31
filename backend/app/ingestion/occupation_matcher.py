"""
Occupation Matcher — entry point for Feature 4 (Goal Reverse Engineering).

Takes free-text the learner typed as their target career ("I want to be a
data scientist", "cybersecurity analyst", "become a UX designer") and
resolves it to one or more O*NET-SOC Codes, ranked by match confidence.

Approach: deterministic token-overlap + substring scoring over the
normalized title index built in Phase 1 (occupation_search_index.json).
No AI call needed for this step — it's fast, explainable, and doesn't
depend on any provider key. Reserve the AI layer for cases where this
scoring comes back empty/low-confidence and the learner's phrasing needs
real language understanding (e.g. "I want to build apps for a living").
"""

import json
import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "processed"

_STOPWORDS = {"a", "an", "the", "and", "or", "of", "for", "to", "in", "on", "at",
              "i", "want", "be", "become", "as", "my", "career", "job", "work",
              "working", "am", "is", "are"}

# CURATED (not O*NET data): O*NET-SOC titles are official occupation names
# ("Information Security Analysts") and don't cover how people actually
# phrase careers ("cybersecurity", "UX designer", "cloud architect",
# "ML engineer"). O*NET does publish an "Alternate Titles" crosswalk for
# this, but it wasn't among the files provided — this hand-built list fills
# that specific, narrow gap and is marked curated so it's never mistaken for
# O*NET-sourced data. Expand this list as real onboarding queries surface
# terms it misses.
CURATED_CAREER_ALIASES: dict[str, str] = {
    "cybersecurity": "information security",
    "cyber security": "information security",
    "infosec": "information security",
    "ux designer": "web and digital interface designer",
    "ui designer": "web and digital interface designer",
    "ux/ui designer": "web and digital interface designer",
    "product designer": "web and digital interface designer",
    "cloud architect": "computer network architect",
    "cloud engineer": "computer network architect",
    "ml engineer": "data scientist",
    "machine learning engineer": "data scientist machine learning",
    "ai engineer": "computer and information research scientist",
    "devops engineer": "software developer",
    "full stack developer": "software developer",
    "fullstack developer": "software developer",
    "backend developer": "software developer",
    "frontend developer": "web developer",
    "sre": "computer network architect",
    "site reliability engineer": "computer network architect",
    "qa engineer": "software quality assurance analyst",
    "data analyst": "data scientist",
    "product manager": "computer and information systems manager",
}


def _apply_curated_aliases(query: str) -> str:
    q = query.lower().strip()
    for alias, canonical in CURATED_CAREER_ALIASES.items():
        if alias in q:
            return canonical
    return query


def _normalize(text: str) -> str:
    t = unicodedata.normalize("NFKD", text).lower()
    t = "".join(ch for ch in t if ch.isalnum() or ch.isspace())
    return re.sub(r"\s+", " ", t).strip()


def _tokens(text: str) -> set[str]:
    return {w for w in _normalize(text).split() if w not in _STOPWORDS and len(w) > 1}


@dataclass
class OccupationMatch:
    code: str
    title: str
    score: float
    match_type: str  # "exact", "substring", "token_overlap"


class OccupationMatcher:
    def __init__(self):
        with open(DATA / "occupation_search_index.json") as f:
            self.index = json.load(f)
        self._title_tokens = [set(e["normalized_title"].split()) for e in self.index]
        # IDF weighting so common occupation-title words ("machine",
        # "specialist", "analyst") don't dominate a match the way a rare,
        # specific word ("cybersecurity", "architect") should.
        doc_count = Counter()
        for toks in self._title_tokens:
            doc_count.update(toks)
        n_docs = len(self.index)
        self._idf = {tok: math.log(n_docs / (1 + df)) + 1 for tok, df in doc_count.items()}

    def _weighted_overlap_score(self, query_tokens: set[str], title_tokens: set[str]) -> float:
        overlap = query_tokens & title_tokens
        if not overlap:
            return 0.0
        overlap_weight = sum(self._idf.get(t, 1.0) for t in overlap)
        union_weight = sum(self._idf.get(t, 1.0) for t in (query_tokens | title_tokens))
        return overlap_weight / union_weight if union_weight else 0.0

    def match(self, query: str, top_k: int = 5) -> list[OccupationMatch]:
        if not query or not query.strip():
            return []

        aliased_query = _apply_curated_aliases(query)
        norm_query = _normalize(aliased_query)
        query_tokens = _tokens(aliased_query)

        results: list[OccupationMatch] = []
        for entry, title_tokens in zip(self.index, self._title_tokens):
            title_norm = entry["normalized_title"]

            if title_norm == norm_query:
                results.append(OccupationMatch(entry["code"], entry["title"], 1.0, "exact"))
                continue

            if norm_query in title_norm or title_norm in norm_query:
                shorter = min(len(norm_query), len(title_norm))
                longer = max(len(norm_query), len(title_norm))
                score = 0.6 + 0.3 * (shorter / longer)
                results.append(OccupationMatch(entry["code"], entry["title"], score, "substring"))
                continue

            if not query_tokens or not title_tokens:
                continue
            score = self._weighted_overlap_score(query_tokens, title_tokens)
            if score > 0.12:
                results.append(OccupationMatch(entry["code"], entry["title"], score, "token_overlap"))

        results.sort(key=lambda m: -m.score)
        # de-duplicate by code (shouldn't happen, but keep it safe) and cap
        seen = set()
        deduped = []
        for m in results:
            if m.code not in seen:
                deduped.append(m)
                seen.add(m.code)
            if len(deduped) >= top_k:
                break
        return deduped


if __name__ == "__main__":
    matcher = OccupationMatcher()
    test_queries = [
        "cybersecurity analyst",
        "I want to become a data scientist",
        "full stack web developer",
        "UX designer",
        "machine learning engineer",
        "cloud architect",
    ]
    for q in test_queries:
        matches = matcher.match(q, top_k=3)
        print(f"\nQuery: {q!r}")
        for m in matches:
            print(f"  {m.score:.2f} [{m.match_type}] {m.code} — {m.title}")
