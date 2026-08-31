"""
Learner profile routes: get, create, and update learner profiles.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

from backend.db import get_db, User, LearnerProfile, SkillRecord, ProjectRecord, AssessmentRecord
from backend.api.auth_routes import get_current_user

router = APIRouter(prefix="/api/learner", tags=["learner"])


# Request/Response models
class SkillRecordResponse(BaseModel):
    element: str
    level: float
    source: str
    last_updated: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ProjectRecordResponse(BaseModel):
    name: str
    skills_demonstrated: List[str]
    quality_score: Optional[float]
    
    class Config:
        from_attributes = True


class AssessmentRecordResponse(BaseModel):
    skill_element: str
    score: float
    weak_concepts: List[str]
    attempt_number: int
    
    class Config:
        from_attributes = True


class LearnerProfileResponse(BaseModel):
    id: int
    name: Optional[str]
    experience_level: str
    target_career_code: Optional[str]
    target_career_title: Optional[str]
    education_status: Optional[str]
    year_of_study: Optional[int]
    career_interests: List[str]
    previous_courses: List[str]
    experience_text: Optional[str] = None
    preferred_language: str
    available_minutes_per_day: int
    target_duration_weeks: int
    completed_milestones: int
    total_milestones: int
    assessment_status: str
    known_tools: List[str]
    has_completed_onboarding: bool
    created_at: datetime
    updated_at: datetime
    skills: List[SkillRecordResponse]
    projects: List[ProjectRecordResponse]
    assessments: List[AssessmentRecordResponse]
    
    class Config:
        from_attributes = True


class LearnerProfileCreateRequest(BaseModel):
    name: str
    experience_level: str = "beginner"
    target_career_code: str
    target_career_title: str
    education_status: Optional[str] = None
    year_of_study: Optional[int] = None
    career_interests: List[str] = []
    previous_courses: List[str] = []
    experience_text: Optional[str] = None
    preferred_language: str = "en"
    available_minutes_per_day: int = 30
    target_duration_weeks: int = 12
    known_tools: List[str] = []


class LearnerProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    experience_level: Optional[str] = None
    target_career_code: Optional[str] = None
    target_career_title: Optional[str] = None
    education_status: Optional[str] = None
    year_of_study: Optional[int] = None
    career_interests: Optional[List[str]] = None
    previous_courses: Optional[List[str]] = None
    experience_text: Optional[str] = None
    preferred_language: Optional[str] = None
    available_minutes_per_day: Optional[int] = None
    target_duration_weeks: Optional[int] = None
    known_tools: Optional[List[str]] = None


@router.get("", response_model=LearnerProfileResponse)
def get_learner_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get the current user's learner profile."""
    profile = db.query(LearnerProfile).filter(LearnerProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learner profile not found")
    return profile


@router.post("/profile", response_model=LearnerProfileResponse)
def create_learner_profile(
    req: LearnerProfileCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new learner profile for the current user."""
    # Check if profile already exists
    existing = db.query(LearnerProfile).filter(LearnerProfile.user_id == current_user.id).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Learner profile already exists")
    
    # Create new profile with EMPTY initial state (no fake data)
    profile = LearnerProfile(
        user_id=current_user.id,
        name=req.name,
        experience_level=req.experience_level,
        target_career_code=req.target_career_code,
        target_career_title=req.target_career_title,
        education_status=req.education_status,
        year_of_study=req.year_of_study,
        career_interests=req.career_interests,
        previous_courses=req.previous_courses,
        experience_text=req.experience_text,
        preferred_language=req.preferred_language,
        available_minutes_per_day=req.available_minutes_per_day,
        target_duration_weeks=req.target_duration_weeks,
        known_tools=req.known_tools,
        assessment_status="not_started",  # NEW LEARNER: no assessment yet
        completed_milestones=0,  # No fake progress
        total_milestones=0,
        has_completed_onboarding=True,
    )
    
    db.add(profile)
    db.commit()
    db.refresh(profile)
    
    return profile


@router.put("/profile", response_model=LearnerProfileResponse)
def update_learner_profile(
    req: LearnerProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update the current user's learner profile."""
    profile = db.query(LearnerProfile).filter(LearnerProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learner profile not found")
    
    # Update only provided fields
    if req.name is not None:
        profile.name = req.name
    if req.experience_level is not None:
        profile.experience_level = req.experience_level
    if req.target_career_code is not None:
        profile.target_career_code = req.target_career_code
    if req.target_career_title is not None:
        profile.target_career_title = req.target_career_title
    if req.education_status is not None:
        profile.education_status = req.education_status
    if req.year_of_study is not None:
        profile.year_of_study = req.year_of_study
    if req.career_interests is not None:
        profile.career_interests = req.career_interests
    if req.previous_courses is not None:
        profile.previous_courses = req.previous_courses
    if req.experience_text is not None:
        profile.experience_text = req.experience_text
    if req.preferred_language is not None:
        profile.preferred_language = req.preferred_language
    if req.available_minutes_per_day is not None:
        profile.available_minutes_per_day = req.available_minutes_per_day
    if req.target_duration_weeks is not None:
        profile.target_duration_weeks = req.target_duration_weeks
    if req.known_tools is not None:
        profile.known_tools = req.known_tools
    
    db.commit()
    db.refresh(profile)
    
    return profile


@router.post("/skills/{element}")
def add_or_update_skill(
    element: str,
    level: float,
    source: str = "self_reported",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add or update a skill for the learner."""
    profile = db.query(LearnerProfile).filter(LearnerProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learner profile not found")
    
    # Check if skill exists
    skill = db.query(SkillRecord).filter(
        SkillRecord.learner_profile_id == profile.id,
        SkillRecord.element == element
    ).first()
    
    if skill:
        skill.level = level
        skill.source = source
        skill.last_updated = datetime.utcnow()
    else:
        skill = SkillRecord(
            learner_profile_id=profile.id,
            element=element,
            level=level,
            source=source
        )
        db.add(skill)
    
    db.commit()
    db.refresh(skill)
    
    return SkillRecordResponse.from_orm(skill)
