"""
AI Learner Assistant / Mentor chat routes (new feature).

Exposes POST /api/mentor/chat.

Follows the exact same pattern as recommendation_routes.py and
engine_routes.py: pull the authenticated user's REAL LearnerProfile,
skills, assessments, skill gaps, roadmap and recommendations from the
DB + existing (unmodified) engines, then hand that as grounding
context to a language model. Nothing here is invented:

  - No DEMO_DATA is ever used for this endpoint.
  - If the learner has no profile, no target career, or the target
    occupation isn't in the O*NET data, the endpoint says so plainly
    (via `context_available: false` + an explanatory `reply`) instead
    of fabricating scores, skills, or recommendations.
  - The LLM is instructed (system prompt) to answer ONLY from the
    supplied context and to say "I don't have that information yet"
    rather than guess.

Model/API: uses the Anthropic Messages API if ANTHROPIC_API_KEY is set
in the environment (see backend/.env.example). If no key is
configured, falls back to a small deterministic responder that still
answers the required question types (what to learn today/next, why a
skill/resource matters, progress, missing skills) using ONLY the same
real context gathered below — so the assistant works out of the box
without requiring an API key, and never crosses into fabrication
either way.
"""

import json
import os
import urllib.request
import urllib.error
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.db import get_db, User, LearnerProfile
from backend.api.auth_routes import get_current_user
from backend.api.engine_routes import _learner_to_dataclass
from backend.app.engines.skill_gap import analyze_skill_gap
from backend.app.engines.readiness import compute_readiness
from backend.app.engines.roadmap import generate_roadmap
from backend.app.engines.recommendations import generate_recommendations

router = APIRouter(prefix="/api/mentor", tags=["mentor"])

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"
with open(DATA_DIR / "occupations.json") as f:
    OCCUPATIONS = json.load(f)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

MAX_HISTORY_TURNS = 10  # keep the prompt small; UI can keep more locally


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []


class ChatResponse(BaseModel):
    reply: str
    context_available: bool
    used_ai_model: bool


# --------------------------------------------------------------------------
# Context gathering — real data only, same pattern as recommendation_routes
# --------------------------------------------------------------------------

def _gather_context(current_user: User, db: Session):
    """Return (context: dict | None, reason: str | None).

    reason is one of: "no_profile" | "no_target_career" | "no_occupation_data"
    when context couldn't be built, explaining exactly why — never guessed.
    """
    profile = db.query(LearnerProfile).filter(LearnerProfile.user_id == current_user.id).first()
    if not profile:
        return None, "no_profile"
    if not profile.target_career_code:
        return None, "no_target_career"

    occupation = OCCUPATIONS.get(profile.target_career_code)
    if not occupation:
        return None, "no_occupation_data"

    learner = _learner_to_dataclass(profile)
    assessed = bool(profile.assessment_status and profile.assessment_status != "not_started")

    context = {
        "name": profile.name,
        "target_career_title": profile.target_career_title,
        "experience_level": profile.experience_level,
        "career_interests": profile.career_interests or [],
        "experience_text": profile.experience_text or "",
        "preferred_language": profile.preferred_language,
        "assessment_status": profile.assessment_status,
        "has_assessed": assessed,
        "completed_milestones": profile.completed_milestones,
        "total_milestones": profile.total_milestones,
        "known_skills": [
            {"element": s.element, "level": s.level, "source": s.source}
            for s in profile.skills
        ],
        "past_assessments": [
            {"skill_element": a.skill_element, "score": a.score, "weak_concepts": a.weak_concepts}
            for a in profile.assessments
        ],
        "skill_gaps": [],
        "readiness_score": None,
        "readiness_next_action": None,
        "roadmap_weeks_planned": None,
        "roadmap_topics": [],
        "recommendations": {},
    }

    # Skill gap / readiness / roadmap / recommendations all reuse the exact
    # same (unmodified) engine calls the rest of the app already uses.
    gap_results = []
    try:
        gap_results = analyze_skill_gap(learner, occupation, source="essential_skills")
        context["skill_gaps"] = [
            {
                "element": r.element,
                "learner_level": r.learner_level,
                "required_level": r.required_level,
                "gap": r.gap,
                "status": r.status,
                "high_priority": r.high_priority,
                "why_it_matters": r.why_it_matters,
            }
            for r in gap_results
        ]
    except Exception:
        pass

    try:
        readiness_result = compute_readiness(learner, gap_results)
        context["readiness_score"] = readiness_result.readiness_score
        context["readiness_next_action"] = readiness_result.next_action
    except Exception:
        pass

    roadmap_topic_labels: List[str] = []
    try:
        roadmap = generate_roadmap(learner, occupation)
        upcoming = []
        for milestone in roadmap.technical.milestones + roadmap.professional.milestones:
            for t in milestone.topics:
                upcoming.append({
                    "week": milestone.week_number,
                    "label": t.label,
                    "hours": t.estimated_hours,
                    "high_priority": t.high_priority,
                    "detail": t.detail,
                })
        upcoming.sort(key=lambda x: (x["week"], not x["high_priority"]))
        context["roadmap_weeks_planned"] = roadmap.weeks_planned
        context["roadmap_topics"] = upcoming[:20]  # cap for prompt size
        roadmap_topic_labels = [t["label"] for t in upcoming]
    except Exception:
        pass

    try:
        reco = generate_recommendations(
            learner=learner,
            occupation=occupation,
            gap_results=gap_results,
            roadmap_topic_labels=roadmap_topic_labels,
        )

        def _slim(items):
            return [
                {
                    "title": r.title,
                    "type": r.resource_type,
                    "related_skill": r.related_skill,
                    "difficulty": r.difficulty,
                    "why_recommended": r.why_recommended,
                }
                for r in items
            ]

        context["recommendations"] = {
            "recommended_for_you": _slim(reco.get("recommended_for_you", []))[:6],
            "courses": _slim(reco.get("courses", []))[:5],
            "videos": _slim(reco.get("videos", []))[:5],
            "projects": _slim(reco.get("projects", []))[:5],
            "free_resources": _slim(reco.get("free_resources", []))[:5],
        }
    except Exception:
        pass

    return context, None


NO_CONTEXT_MESSAGES = {
    "no_profile": (
        "I don't have a learner profile for you yet, so I can't answer that from "
        "real data. Please finish onboarding (set your name and target career) and "
        "I'll be able to help."
    ),
    "no_target_career": (
        "You haven't set a target career yet, so I don't have anything to base an "
        "answer on. Set a target career in your profile and ask me again."
    ),
    "no_occupation_data": (
        "I can't find O*NET data for your target career code, so I can't ground an "
        "answer in real data right now. Please try re-selecting your target career."
    ),
}


# --------------------------------------------------------------------------
# LLM call (Anthropic) — optional; falls back to deterministic responder
# --------------------------------------------------------------------------

SYSTEM_PROMPT_TEMPLATE = """You are the LearnAscent AI Learner Assistant, embedded in the LearnAscent \
platform. You help a learner understand their own progress toward a target career.

STRICT RULES:
- Only use the LEARNER CONTEXT JSON below. It is the learner's real, authenticated data \
(profile, skills, assessment results, skill gaps, roadmap, recommended resources).
- NEVER invent scores, skills, courses, gaps, or progress that are not in the context.
- If the context does not contain the information needed to answer, say so plainly and \
suggest what the learner should do (e.g. "take an assessment", "set a target career") \
instead of guessing.
- When asked why something was recommended or why a skill matters, explain using the \
`why_it_matters` / `why_recommended` fields and the skill-gap status already provided.
- `experience_text` is the learner's own free-text description of what they've already \
learned, built, worked on, or practiced. Use it (when non-empty) to tailor tone and pacing \
advice — e.g. don't suggest something they said they've already done.
- Be concise, encouraging, and specific. Reference the learner's actual target career, \
skill names, and numbers when relevant.
- Keep replies to a few short sentences or a short list — this is a chat panel, not a report.

LEARNER CONTEXT (JSON):
{context_json}
"""


def _call_anthropic(system_prompt: str, history: List[ChatMessage], message: str) -> Optional[str]:
    if not ANTHROPIC_API_KEY:
        return None

    messages = []
    for turn in history[-MAX_HISTORY_TURNS:]:
        role = "assistant" if turn.role == "assistant" else "user"
        messages.append({"role": role, "content": turn.content})
    messages.append({"role": "user", "content": message})

    payload = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": 600,
        "system": system_prompt,
        "messages": messages,
    }

    req = urllib.request.Request(
        ANTHROPIC_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "content-type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError):
        return None

    parts = data.get("content", [])
    text = "".join(p.get("text", "") for p in parts if p.get("type") == "text").strip()
    return text or None


# --------------------------------------------------------------------------
# Deterministic fallback — used only when no ANTHROPIC_API_KEY is set, or
# the API call fails. Built entirely from the same real `context` dict.
# --------------------------------------------------------------------------

def _fallback_reply(message: str, context: dict) -> str:
    q = message.lower()
    career = context.get("target_career_title") or "your target career"

    if not context.get("has_assessed"):
        if any(k in q for k in ["today", "next", "learn", "missing", "gap", "progress", "readiness"]):
            return (
                f"You haven't completed an assessment yet, so I don't have real skill-gap or "
                f"roadmap data to base this on. Take your assessment for {career} and I'll be "
                f"able to tell you exactly what to focus on next."
            )

    gaps = context.get("skill_gaps") or []
    high_priority_gaps = [g for g in gaps if g.get("high_priority")]
    missing = [g for g in gaps if g.get("status") == "missing"]
    developing = [g for g in gaps if g.get("status") == "developing"]

    if any(k in q for k in ["missing", "what skills am i missing", "gap"]):
        if not gaps:
            return "I don't have skill-gap data for you yet — complete an assessment first."
        if not missing and not developing:
            return f"Good news — based on your assessment, you have no major skill gaps left for {career} right now."
        names = [g["element"] for g in (missing or developing)][:5]
        return (
            f"Based on your real skill-gap analysis for {career}, the skills you're missing or "
            f"still developing are: {', '.join(names)}."
        )

    if any(k in q for k in ["today", "what should i learn"]):
        topics = context.get("roadmap_topics") or []
        if not topics:
            return "I don't have a roadmap topic for today yet — complete your assessment to generate one."
        t = topics[0]
        return f"Based on your roadmap, today's focus is **{t['label']}** (week {t['week']}, ~{t['hours']}h) — {t['detail']}"

    if "next" in q:
        topics = context.get("roadmap_topics") or []
        if not topics:
            return "I don't have roadmap data yet — complete your assessment first."
        names = [t["label"] for t in topics[:3]]
        return f"Coming up next on your roadmap: {', '.join(names)}."

    if "progress" in q or "how am i doing" in q or "readiness" in q:
        score = context.get("readiness_score")
        if score is None:
            return "I don't have a readiness score for you yet — complete an assessment to generate one."
        milestones = f"{context.get('completed_milestones', 0)}/{context.get('total_milestones', 0)} milestones completed"
        return f"Your real career readiness score is {round(score)}/100 for {career} ({milestones}). {context.get('readiness_next_action') or ''}".strip()

    if "why" in q and ("recommend" in q or "resource" in q or "course" in q):
        reco = context.get("recommendations") or {}
        featured = (reco.get("recommended_for_you") or [])
        if not featured:
            return "I don't have any resource recommendations for you yet — this unlocks after your assessment."
        item = featured[0]
        return f"\"{item['title']}\" was recommended because {item['why_recommended']}"

    if "why" in q and "important" in q or ("why" in q and "skill" in q):
        if not gaps:
            return "I don't have skill-gap data yet — complete an assessment first."
        top = sorted(gaps, key=lambda g: g.get("gap", 0), reverse=True)[0]
        return f"{top['element']} matters for {career}: {top['why_it_matters']}"

    # Generic fallback: summarize what we do know, using only real data.
    score = context.get("readiness_score")
    lines = [f"Here's what I know about your progress toward {career}:"]
    if score is not None:
        lines.append(f"- Readiness score: {round(score)}/100")
    if high_priority_gaps:
        lines.append(f"- Highest-priority skill gaps: {', '.join(g['element'] for g in high_priority_gaps[:3])}")
    topics = context.get("roadmap_topics") or []
    if topics:
        lines.append(f"- Next roadmap topic: {topics[0]['label']}")
    if len(lines) == 1:
        lines.append("Complete your assessment to unlock skill gaps, a roadmap, and recommendations.")
    lines.append("You can ask me things like \"what should I learn today\", \"why is this skill important\", or \"what skills am I missing\".")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Route
# --------------------------------------------------------------------------

@router.post("/chat", response_model=ChatResponse)
def chat(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Chat with the AI learner assistant, grounded in the authenticated
    learner's real profile/skills/assessment/roadmap/recommendation data.
    Never uses DEMO_DATA and never invents facts about the learner."""
    context, reason = _gather_context(current_user, db)

    if context is None:
        return ChatResponse(
            reply=NO_CONTEXT_MESSAGES.get(reason, "I don't have enough data about you yet to answer that."),
            context_available=False,
            used_ai_model=False,
        )

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(context_json=json.dumps(context, default=str))
    ai_reply = _call_anthropic(system_prompt, req.history, req.message)

    if ai_reply:
        return ChatResponse(reply=ai_reply, context_available=True, used_ai_model=True)

    return ChatResponse(
        reply=_fallback_reply(req.message, context),
        context_available=True,
        used_ai_model=False,
    )
