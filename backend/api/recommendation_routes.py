"""
Smart Resource Recommendation routes (new feature).

Exposes POST /api/recommendations. Follows the exact same pattern as
engine_routes.py: pull the authenticated user's real LearnerProfile +
skills + assessments from the DB, convert to the in-memory dataclass,
run the (deterministic) engine, return a typed response.

No DEMO_DATA, no fake skills/readiness/progress — if the learner has no
profile or no target career set, this returns a 4xx rather than making
anything up.
"""

import json
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from backend.db import get_db, User, LearnerProfile
from backend.api.auth_routes import get_current_user
from backend.api.engine_routes import _learner_to_dataclass
from backend.app.engines.skill_gap import analyze_skill_gap
from backend.app.engines.roadmap import generate_roadmap, RATING_SOURCES
from backend.app.engines.recommendations import generate_recommendations

router = APIRouter(prefix="/api", tags=["recommendations"])

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"
with open(DATA_DIR / "occupations.json") as f:
    OCCUPATIONS = json.load(f)


class RecommendationItemResponse(BaseModel):
    id: str
    title: str
    resource_type: str   # course | video | project | free_resource
    related_skill: str
    difficulty: str
    estimated_time_hours: float
    why_recommended: str
    url: Optional[str] = None
    source: str


class RecommendationsResponse(BaseModel):
    target_career_title: str
    based_on_skill_gaps: List[str]
    recommended_for_you: List[RecommendationItemResponse]
    courses: List[RecommendationItemResponse]
    videos: List[RecommendationItemResponse]
    projects: List[RecommendationItemResponse]
    free_resources: List[RecommendationItemResponse]


def _to_response_item(r) -> RecommendationItemResponse:
    return RecommendationItemResponse(
        id=r.id,
        title=r.title,
        resource_type=r.resource_type,
        related_skill=r.related_skill,
        difficulty=r.difficulty,
        estimated_time_hours=r.estimated_time_hours,
        why_recommended=r.why_recommended,
        url=r.url,
        source=r.source,
    )


@router.post("/recommendations", response_model=RecommendationsResponse)
def get_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate personalized learning resource recommendations for the
    authenticated learner, using their real profile, skills, skill gaps,
    experience level, available time, and existing roadmap."""
    profile = db.query(LearnerProfile).filter(LearnerProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learner profile not found")
    if not profile.target_career_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No target career set")

    occupation = OCCUPATIONS.get(profile.target_career_code)
    if not occupation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Occupation not found in O*NET data")

    learner = _learner_to_dataclass(profile)

    # Real skill gaps for THIS learner against THEIR target occupation.
    gap_results = [
        gap for source in RATING_SOURCES
        for gap in analyze_skill_gap(learner, occupation, source=source)
    ]

    # Existing roadmap, used only as an extra keyword signal — not rebuilt.
    roadmap_topic_labels: List[str] = []
    try:
        roadmap = generate_roadmap(learner, occupation)
        for milestone in roadmap.technical.milestones + roadmap.professional.milestones:
            roadmap_topic_labels.extend(t.label for t in milestone.topics)
    except Exception:
        roadmap_topic_labels = []

    result = generate_recommendations(
        learner=learner,
        occupation=occupation,
        gap_results=gap_results,
        roadmap_topic_labels=roadmap_topic_labels,
    )

    high_priority_elements = [r.element for r in gap_results if r.status in ("missing", "developing")]

    return RecommendationsResponse(
        target_career_title=profile.target_career_title or occupation.get("title", ""),
        based_on_skill_gaps=high_priority_elements,
        recommended_for_you=[_to_response_item(r) for r in result["recommended_for_you"]],
        courses=[_to_response_item(r) for r in result["courses"]],
        videos=[_to_response_item(r) for r in result["videos"]],
        projects=[_to_response_item(r) for r in result["projects"]],
        free_resources=[_to_response_item(r) for r in result["free_resources"]],
    )
