"""
Smart Resource Recommendation engine (new feature).

Deterministic, no paid AI API required — this mirrors the same design
philosophy as skill_gap.py / readiness.py / roadmap.py: plain scoring
rules over real data, documented here rather than hidden in a model call.

Inputs used to build a recommendation set for one learner:
  - target career (O*NET occupation dict, same shape used elsewhere)
  - learner's current skills / known tools (LearnerProfile)
  - skill gaps (list[SkillGapResult] from the existing skill_gap engine —
    this module does not recompute gaps, it only ranks against them)
  - experience level (used for difficulty fit)
  - available learning time (used for a soft time-fit signal)
  - existing roadmap topic labels (optional secondary keyword signal, so
    recommendations stay aligned with the roadmap without re-deriving it)

Resource data comes from a local JSON catalogue
(backend/data/resources_catalogue.json) so the engine always works, even
with zero external services configured. YouTube Data API integration is
optional and purely additive:
  - the API key is read from the YOUTUBE_API_KEY environment variable and
    is never hardcoded
  - if the key is missing, or the request fails for any reason, the
    engine silently falls back to the curated catalogue — the app never
    breaks because an external API is unavailable or unconfigured.

Udemy is intentionally NOT integrated via any private/unsupported API.
Where a paid-course category is useful, the catalogue links to public,
stable Udemy/Coursera *search* pages rather than a specific fabricated
course URL, so nothing here can point at a course that doesn't exist.
"""

import json
import os
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from backend.app.models.learner import LearnerProfile
from backend.app.engines.skill_gap import SkillGapResult

CATALOGUE_PATH = Path(__file__).resolve().parents[2] / "data" / "resources_catalogue.json"

EXPERIENCE_DIFFICULTY_RANK = {"beginner": 0, "intermediate": 1, "advanced": 2}
DIFFICULTY_RANK = {"Beginner": 0, "Intermediate": 1, "Advanced": 2}

# Status -> base score. Mirrors skill_gap's own priority ordering
# (missing/developing-and-high-priority matter most) so recommendations
# and the skill-gap view never disagree about what matters most.
STATUS_BASE_SCORE = {"missing": 80.0, "developing": 60.0, "strong": 30.0, "mastered": 5.0}


@dataclass
class Recommendation:
    id: str
    title: str
    resource_type: str          # "course" | "video" | "project" | "free_resource"
    related_skill: str
    difficulty: str
    estimated_time_hours: float
    why_recommended: str
    url: Optional[str]
    source: str
    score: float = 0.0


def _load_catalogue() -> list[dict]:
    with open(CATALOGUE_PATH, encoding="utf-8") as f:
        return json.load(f)


def _normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()


def _skill_matches(resource_skills: list[str], target: str) -> bool:
    t = _normalize(target)
    if len(t) < 2:
        return False
    for s in resource_skills:
        ns = _normalize(s)
        # Exact normalized labels prevent short technology labels (notably
        # "C++" -> "c") from matching arbitrary words such as "Critical".
        if len(ns) >= 2 and ns == t:
            return True
    return False


def _why_text(skill: str, status: str, career_title: str) -> str:
    if status == "missing":
        return f"Recommended because {skill} is one of your identified skill gaps — you haven't started it yet for {career_title}."
    if status == "developing":
        return f"Recommended because {skill} is one of your identified skill gaps — you're developing it but not yet at the level {career_title} typically needs."
    if status == "strong":
        return f"Recommended to close the small remaining gap in {skill}."
    if status == "mastered":
        return f"Recommended to go further in {skill}, a skill you already show strength in."
    return f"Recommended because {skill} is relevant to your path toward {career_title}."


def _fetch_youtube_videos(query: str, api_key: str, max_results: int = 2) -> list[dict]:
    """
    Best-effort YouTube Data API v3 search. NEVER raises — any failure
    (missing key, network error, quota, bad response) just returns [] so
    the caller falls back to the curated catalogue.
    """
    try:
        params = urllib.parse.urlencode({
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": max_results,
            "key": api_key,
            "safeSearch": "strict",
            "relevanceLanguage": "en",
            "videoEmbeddable": "true",
        })
        url = f"https://www.googleapis.com/youtube/v3/search?{params}"
        with urllib.request.urlopen(url, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        out = []
        for item in data.get("items", []):
            vid = item.get("id", {}).get("videoId")
            snippet = item.get("snippet", {})
            if not vid:
                continue
            out.append({
                "title": snippet.get("title", "YouTube video"),
                "url": f"https://www.youtube.com/watch?v={vid}",
                "channel": snippet.get("channelTitle", "YouTube"),
            })
        return out
    except Exception:
        return []


def generate_recommendations(
    learner: LearnerProfile,
    occupation: dict,
    gap_results: list[SkillGapResult],
    roadmap_topic_labels: Optional[list[str]] = None,
    max_per_category: int = 6,
) -> dict:
    """
    Returns a dict with keys: recommended_for_you, courses, videos,
    projects, free_resources — each a list[Recommendation], ranked.

    Never returns identical output for different learners unless their
    profile, target career, and skill gaps are themselves identical —
    every score is derived from the arguments passed in, nothing here
    is a fixed/demo dataset.
    """
    catalogue = _load_catalogue()
    roadmap_topic_labels = roadmap_topic_labels or []
    career_title = occupation.get("title", "this career")

    gap_by_element = {r.element: r for r in gap_results}
    knowledge_focus = {item["element"] for item in occupation.get("knowledge", [])}
    transferable_focus = {item["element"] for item in occupation.get("transferable_skills", [])}

    def _occupation_focus_bonus(element: str) -> float:
        # Knowledge is the most occupation-specific O*NET category (Food
        # Production vs. Design vs. Computers and Electronics); transferable
        # skills remain useful, but should not displace it in the journey.
        if element in knowledge_focus:
            return 55.0
        if element in transferable_focus:
            return 20.0
        return 0.0
    # Highest-priority gaps first (skill_gap.py already sorts this way).
    priority_gaps = [r for r in gap_results if r.status in ("missing", "developing")]
    other_gaps = [r for r in gap_results if r.status not in ("missing", "developing")]

    exp_rank = EXPERIENCE_DIFFICULTY_RANK.get(learner.experience_level, 0)
    weekly_hours_budget = max(learner.available_minutes_per_day * 7 / 60.0, 1.0)

    scored: list[Recommendation] = []
    seen_ids: set[str] = set()
    matched_gap_elements: set[str] = set()

    def add(item: dict, related_skill: str, gap: Optional[SkillGapResult]):
        if item["id"] in seen_ids:
            return
        seen_ids.add(item["id"])

        difficulty = item.get("difficulty", "Beginner")
        diff_rank = DIFFICULTY_RANK.get(difficulty, 0)
        diff_fit_penalty = abs(diff_rank - exp_rank) * 8.0

        status = gap.status if gap else "relevant"
        gap_score = STATUS_BASE_SCORE.get(status, 15.0)
        if gap and gap.high_priority:
            gap_score += 25.0
        if gap:
            gap_score += gap.importance * 5.0
            # O*NET knowledge/cross-functional requirements distinguish one
            # occupation from another better than the universal Basic Skills
            # domain, so use them first when both are real learner gaps.
            gap_score += _occupation_focus_bonus(related_skill)

        hours = item.get("estimated_hours") or 5.0
        time_fit_bonus = -abs(hours - weekly_hours_budget) * 0.2

        total_score = gap_score - diff_fit_penalty + time_fit_bonus

        scored.append(Recommendation(
            id=item["id"],
            title=item["title"],
            resource_type=item["type"],
            related_skill=related_skill,
            difficulty=difficulty,
            estimated_time_hours=float(hours),
            why_recommended=_why_text(related_skill, status, career_title),
            url=item.get("url"),
            source=item.get("source", "Curated"),
            score=total_score,
        ))

    # 1) Match catalogue resources against the learner's real skill gaps,
    #    highest priority first — this is the primary ranking signal.
    for gap in priority_gaps + other_gaps:
        for item in catalogue:
            if _skill_matches(item.get("skills", []), gap.element):
                add(item, gap.element, gap)
                matched_gap_elements.add(gap.element)

    # 2) Existing roadmap topics as a secondary keyword signal, so
    #    recommendations stay aligned with the roadmap the learner is
    #    already on without rebuilding or re-deriving it.
    for label in roadmap_topic_labels:
        for item in catalogue:
            if _skill_matches(item.get("skills", []), label):
                add(item, label, gap_by_element.get(label))

    # 3) Practical, hands-on project matches for tools the learner already
    #    knows — helps them build a portfolio, not just close gaps.
    for tool in learner.known_tools:
        for item in catalogue:
            if item["type"] == "project" and _skill_matches(item.get("skills", []), tool):
                add(item, tool, None)

    # 4) Optional YouTube enrichment for the top priority gaps only.
    api_key = os.getenv("YOUTUBE_API_KEY")
    if api_key:
        for gap in priority_gaps[:3]:
            query = f"{gap.element} tutorial for {career_title}"
            for v in _fetch_youtube_videos(query, api_key, max_results=2):
                digits = re.sub(r"\W", "", v["url"])[-16:]
                rid = f"yt-{digits}"
                if rid in seen_ids:
                    continue
                seen_ids.add(rid)
                scored.append(Recommendation(
                    id=rid,
                    title=v["title"],
                    resource_type="video",
                    related_skill=gap.element,
                    difficulty="Beginner",
                    estimated_time_hours=0.5,
                    why_recommended=_why_text(gap.element, gap.status, career_title)
                        + f" (via YouTube — {v['channel']})",
                    url=v["url"],
                    source="YouTube",
                    score=STATUS_BASE_SCORE.get(gap.status, 15.0) + 25.0 + gap.importance * 5.0,
                ))

    # 5) Fill missing catalogue coverage from the actual O*NET gap.  Do not
    # fall back to arbitrary catalogue entries: that was how unrelated C++/R
    # material leaked into non-technical careers.
    for gap in priority_gaps:
        if gap.element not in matched_gap_elements:
            query = urllib.parse.quote_plus(f"{gap.element} {career_title}")
            scored.append(Recommendation(
                id=f"occupation-gap:{gap.element_id or _normalize(gap.element)}",
                title=f"Learn {gap.element} for {career_title}",
                resource_type="free_resource",
                related_skill=gap.element,
                difficulty="Beginner",
                estimated_time_hours=1.0,
                why_recommended=_why_text(gap.element, gap.status, career_title),
                url=f"https://www.youtube.com/results?search_query={query}",
                source="YouTube search",
                score=(STATUS_BASE_SCORE.get(gap.status, 15.0) + gap.importance * 5.0
                       + _occupation_focus_bonus(gap.element)),
            ))

    scored.sort(key=lambda r: -r.score)

    def top(resource_type: str, n: int) -> list[Recommendation]:
        return [r for r in scored if r.resource_type == resource_type][:n]

    return {
        "recommended_for_you": scored[:max_per_category],
        "courses": top("course", max_per_category),
        "videos": top("video", max_per_category),
        "projects": top("project", max_per_category),
        "free_resources": top("free_resource", max_per_category),
    }
