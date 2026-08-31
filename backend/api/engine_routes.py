"""
Engine integration routes: expose Phase 1-5 engines via API.

These routes call the existing deterministic engines and integrate them
with the database layer. The engines themselves are unchanged.
"""

import json
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from backend.db import get_db, User, LearnerProfile, AssessmentRecord, TaskCompletion
from backend.api.auth_routes import get_current_user
from backend.app.models.learner import LearnerProfile as LearnerDataClass, SkillRecord, AssessmentRecord as AssessmentDataClass
from backend.app.engines.skill_gap import analyze_skill_gap, SkillGapResult
from backend.app.engines.readiness import compute_readiness, ReadinessResult
from backend.app.engines.roadmap import generate_roadmap
from backend.app.engines.adaptive import apply_assessment_result
from backend.app.ingestion.occupation_matcher import OccupationMatcher

router = APIRouter(prefix="/api/engines", tags=["engines"])

# Load O*NET data
DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"
with open(DATA_DIR / "occupations.json") as f:
    OCCUPATIONS = json.load(f)

OCCUPATION_MATCHER = OccupationMatcher()


# Request/Response models
class SkillGapRequest(BaseModel):
    source: str = "essential_skills"  # essential_skills | knowledge | abilities | transferable_skills


class SkillGapItemResponse(BaseModel):
    element: str
    element_id: str
    importance: float
    required_level: float
    learner_level: float
    gap: float
    status: str
    high_priority: bool
    why_it_matters: str


class ReadinessComponentResponse(BaseModel):
    component: str
    weight: float
    raw_score_0_100: float
    weighted_contribution: float
    note: str


class ReadinessResponse(BaseModel):
    readiness_score: float
    breakdown: List[ReadinessComponentResponse]
    missing_evidence: List[str]
    next_action: str
    disclaimer: str


class RoadmapTopicResponse(BaseModel):
    id: str
    label: str
    topic_type: str
    track: str  # "technical" | "professional"
    estimated_hours: float
    high_priority: bool
    detail: str
    completed: bool = False  # real, persisted TaskCompletion state — see task_routes.py


class MilestoneResponse(BaseModel):
    week_number: int
    topics: List[RoadmapTopicResponse]
    total_hours: float
    is_campsite: bool


class TrackPlanResponse(BaseModel):
    track: str
    milestones: List[MilestoneResponse]
    weeks_planned: int
    total_hours: float
    weekly_hour_budget: float


class RoadmapResponse(BaseModel):
    target_career_title: str
    weeks_planned: int
    technical: TrackPlanResponse
    professional: TrackPlanResponse
    total_topics: int
    total_estimated_hours: float
    fits_target_duration: bool
    overflow_weeks: int


class AssessmentSubmitRequest(BaseModel):
    skill_element: str
    score: float  # 0-100
    weak_concepts: List[str] = []


class AssessmentAdaptationResponse(BaseModel):
    action: str  # accelerate | steady | recover
    track: str  # "technical" | "professional"
    skill_element: str
    score: float
    updated_learner_level: float
    message: str


def _learner_to_dataclass(profile: LearnerProfile) -> LearnerDataClass:
    """Convert DB learner profile to in-memory dataclass for engine processing."""
    skills_dict = {}
    for skill_record in profile.skills:
        skills_dict[skill_record.element] = SkillRecord(
            element=skill_record.element,
            level=skill_record.level,
            source=skill_record.source,
            last_updated=skill_record.last_updated.isoformat() if skill_record.last_updated else None
        )
    
    assessments_list = []
    for assessment_record in profile.assessments:
        assessments_list.append(AssessmentDataClass(
            skill_element=assessment_record.skill_element,
            score=assessment_record.score,
            weak_concepts=assessment_record.weak_concepts,
            attempt_number=assessment_record.attempt_number
        ))
    
    return LearnerDataClass(
        user_id=f"db-{profile.user_id}",
        target_career_code=profile.target_career_code or "unknown",
        target_career_title=profile.target_career_title or "Unknown",
        experience_level=profile.experience_level,
        skills=skills_dict,
        known_tools=set(profile.known_tools) if profile.known_tools else set(),
        projects=[],  # TODO: serialize ProjectRecord
        assessments=assessments_list,
        completed_milestones=profile.completed_milestones,
        total_milestones=profile.total_milestones,
        available_minutes_per_day=profile.available_minutes_per_day,
        target_duration_weeks=profile.target_duration_weeks,
        preferred_language=profile.preferred_language,
    )


def _completed_topic_ids(profile: LearnerProfile, db: Session) -> set:
    """Real, persisted completion state (backend/api/task_routes.py owns
    writes to this table). Used to annotate roadmap topics and to derive
    completed_milestones from actual learner action — never invented."""
    rows = db.query(TaskCompletion.topic_id).filter(
        TaskCompletion.learner_profile_id == profile.id
    ).all()
    return {r[0] for r in rows}


def _sync_progress_counters(profile: LearnerProfile, roadmap, db: Session) -> None:
    """Recompute total_milestones / completed_milestones from the CURRENT
    roadmap's real topic set and the learner's real TaskCompletion rows.
    A topic only counts as complete if it's both persisted as completed
    AND still present in the freshly-generated roadmap (e.g. a mastered
    skill's topic naturally drops out and stops counting — that's correct,
    not a bug). This feeds both the readiness "milestones" component and
    the Mountain frontier (frontend/mountain.js), so both always reflect
    the same real number."""
    all_topic_ids = {t.id for m in roadmap.technical.milestones for t in m.topics}
    all_topic_ids |= {t.id for m in roadmap.professional.milestones for t in m.topics}
    completed_ids = _completed_topic_ids(profile, db)
    profile.total_milestones = len(all_topic_ids)
    profile.completed_milestones = len(completed_ids & all_topic_ids)


@router.post("/skill-gap", response_model=List[SkillGapItemResponse])
def analyze_skill_gap_endpoint(
    req: SkillGapRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Analyze learner's skill gap relative to their target career."""
    profile = db.query(LearnerProfile).filter(LearnerProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learner profile not found")
    if not profile.target_career_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No target career set")
    
    # Get occupation data
    occupation = OCCUPATIONS.get(profile.target_career_code)
    if not occupation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Occupation not found in O*NET data")
    
    # Convert learner to dataclass
    learner = _learner_to_dataclass(profile)
    
    # Run engine
    results = analyze_skill_gap(learner, occupation, source=req.source)
    
    return [
        SkillGapItemResponse(
            element=r.element,
            element_id=r.element_id,
            importance=r.importance,
            required_level=r.required_level,
            learner_level=r.learner_level,
            gap=r.gap,
            status=r.status,
            high_priority=r.high_priority,
            why_it_matters=r.why_it_matters
        ) for r in results
    ]


@router.post("/readiness", response_model=ReadinessResponse)
def calculate_readiness_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Calculate learner's career readiness score."""
    profile = db.query(LearnerProfile).filter(LearnerProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learner profile not found")
    if not profile.target_career_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No target career set")
    
    # Get occupation data
    occupation = OCCUPATIONS.get(profile.target_career_code)
    if not occupation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Occupation not found in O*NET data")
    
    # Convert learner to dataclass
    learner = _learner_to_dataclass(profile)
    
    # Calculate skill gap first (needed for readiness)
    gap_results = analyze_skill_gap(learner, occupation, source="essential_skills")
    
    # Run engine
    result = compute_readiness(learner, gap_results)
    
    return ReadinessResponse(
        readiness_score=result.readiness_score,
        breakdown=[
            ReadinessComponentResponse(
                component=b.component,
                weight=b.weight,
                raw_score_0_100=b.raw_score_0_100,
                weighted_contribution=b.weighted_contribution,
                note=b.note
            ) for b in result.breakdown
        ],
        missing_evidence=result.missing_evidence,
        next_action=result.next_action,
        disclaimer=result.disclaimer
    )


@router.post("/roadmap", response_model=RoadmapResponse)
def generate_roadmap_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate personalized learning roadmap."""
    profile = db.query(LearnerProfile).filter(LearnerProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learner profile not found")
    if not profile.target_career_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No target career set")
    
    # Get occupation data
    occupation = OCCUPATIONS.get(profile.target_career_code)
    if not occupation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Occupation not found in O*NET data")
    
    # Convert learner to dataclass
    learner = _learner_to_dataclass(profile)
    
    # Run engine
    roadmap = generate_roadmap(learner, occupation)

    # Recompute real progress counters (total/completed topics) from this
    # fresh roadmap + the learner's persisted TaskCompletion rows.
    _sync_progress_counters(profile, roadmap, db)
    db.commit()

    completed_ids = _completed_topic_ids(profile, db)

    def _track_response(plan) -> TrackPlanResponse:
        return TrackPlanResponse(
            track=plan.track,
            milestones=[
                MilestoneResponse(
                    week_number=m.week_number,
                    topics=[
                        RoadmapTopicResponse(
                            id=t.id,
                            label=t.label,
                            topic_type=t.topic_type,
                            track=t.track,
                            estimated_hours=t.estimated_hours,
                            high_priority=t.high_priority,
                            detail=t.detail,
                            completed=t.id in completed_ids,
                        ) for t in m.topics
                    ],
                    total_hours=m.total_hours,
                    is_campsite=m.is_campsite
                ) for m in plan.milestones
            ],
            weeks_planned=plan.weeks_planned,
            total_hours=plan.total_hours,
            weekly_hour_budget=plan.weekly_hour_budget,
        )

    return RoadmapResponse(
        target_career_title=roadmap.target_career_title,
        weeks_planned=roadmap.weeks_planned,
        technical=_track_response(roadmap.technical),
        professional=_track_response(roadmap.professional),
        total_topics=roadmap.total_topics,
        total_estimated_hours=roadmap.total_estimated_hours,
        fits_target_duration=roadmap.fits_target_duration,
        overflow_weeks=roadmap.overflow_weeks,
    )


@router.post("/assessment", response_model=AssessmentAdaptationResponse)
def submit_assessment_endpoint(
    req: AssessmentSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit an assessment result and get adaptive roadmap changes."""
    profile = db.query(LearnerProfile).filter(LearnerProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learner profile not found")
    if not profile.target_career_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No target career set")
    
    # Get occupation data
    occupation = OCCUPATIONS.get(profile.target_career_code)
    if not occupation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Occupation not found in O*NET data")
    
    # Convert learner to dataclass
    learner = _learner_to_dataclass(profile)
    
    # Generate roadmap (needed for adaptation)
    roadmap = generate_roadmap(learner, occupation)
    
    # Create assessment dataclass
    assessment = AssessmentDataClass(
        skill_element=req.skill_element,
        score=req.score,
        weak_concepts=req.weak_concepts,
        attempt_number=1
    )
    
    # Run adaptation engine (track is auto-detected from which O*NET category
    # the assessed element belongs to — see track_classifier.py)
    adaptation = apply_assessment_result(learner, occupation, roadmap, assessment, current_week=1)
    
    # Save assessment to DB
    db_assessment = AssessmentRecord(
        learner_profile_id=profile.id,
        skill_element=req.skill_element,
        score=req.score,
        weak_concepts=req.weak_concepts,
        attempt_number=1
    )
    db.add(db_assessment)
    
    # Update learner's assessment status and real progress counters
    profile.assessment_status = "completed"
    _sync_progress_counters(profile, roadmap, db)
    db.commit()
    
    return AssessmentAdaptationResponse(
        action=adaptation.action,
        track=adaptation.track,
        skill_element=adaptation.skill_element,
        score=adaptation.score,
        updated_learner_level=adaptation.updated_learner_level,
        message=adaptation.message
    )


@router.get("/occupation-search")
def search_occupations(query: str):
    """Search for occupations by name."""
    matches = OCCUPATION_MATCHER.match(query, top_k=5)
    return [
        {
            "code": m.code,
            "title": m.title,
            "score": m.score,
            "match_type": m.match_type
        } for m in matches
    ]
