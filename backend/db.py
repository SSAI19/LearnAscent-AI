"""
Database models and connection management for LearnAscent.

Maps the in-memory LearnerProfile dataclass to persistent SQLAlchemy ORM models.
"""

import os
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Boolean, ForeignKey, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./learnascent.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    """User account with secure password."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    learner_profile = relationship("LearnerProfile", back_populates="user", uselist=False)


class LearnerProfile(Base):
    """Core learner profile mapped from LearnerProfile dataclass."""
    __tablename__ = "learner_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    
    # Learner info
    name = Column(String, nullable=True)
    experience_level = Column(String, default="beginner")  # beginner | intermediate | advanced
    target_career_code = Column(String, nullable=True)  # O*NET-SOC code (e.g., "15-2051.00")
    target_career_title = Column(String, nullable=True)
    
    # Onboarding
    education_status = Column(String, nullable=True)  # current education/occupation status
    year_of_study = Column(Integer, nullable=True)
    career_interests = Column(JSON, default=list)  # list of interests
    previous_courses = Column(JSON, default=list)  # list of course names
    preferred_language = Column(String, default="en")

    # Free-text self-described experience (real learner narrative, not a
    # beginner/intermediate/professional bucket). Optional. Surfaced to the
    # personalization/mentor context — see api/mentor_routes.py.
    experience_text = Column(Text, nullable=True)
    
    # Learning preferences
    available_minutes_per_day = Column(Integer, default=30)
    target_duration_weeks = Column(Integer, default=12)
    
    # Progress
    completed_milestones = Column(Integer, default=0)
    total_milestones = Column(Integer, default=0)
    assessment_status = Column(String, default="not_started")  # not_started | in_progress | completed
    
    # Known tools (JSON list)
    known_tools = Column(JSON, default=list)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    has_completed_onboarding = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", back_populates="learner_profile")
    skills = relationship("SkillRecord", back_populates="learner_profile", cascade="all, delete-orphan")
    projects = relationship("ProjectRecord", back_populates="learner_profile", cascade="all, delete-orphan")
    assessments = relationship("AssessmentRecord", back_populates="learner_profile", cascade="all, delete-orphan")


class SkillRecord(Base):
    """A learner's skill level for a specific O*NET element."""
    __tablename__ = "skill_records"
    
    id = Column(Integer, primary_key=True, index=True)
    learner_profile_id = Column(Integer, ForeignKey("learner_profiles.id"), nullable=False, index=True)
    
    element = Column(String, nullable=False)  # O*NET element name (e.g., "Programming")
    level = Column(Float, default=0.0)  # 0-7 scale (O*NET scale)
    source = Column(String, default="self_reported")  # self_reported | assessment | project_verified
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    learner_profile = relationship("LearnerProfile", back_populates="skills")


class ProjectRecord(Base):
    """A learner's completed project."""
    __tablename__ = "project_records"
    
    id = Column(Integer, primary_key=True, index=True)
    learner_profile_id = Column(Integer, ForeignKey("learner_profiles.id"), nullable=False, index=True)
    
    name = Column(String, nullable=False)
    skills_demonstrated = Column(JSON, default=list)  # list of skill names
    quality_score = Column(Float, nullable=True)  # 0-100, from feature review
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    learner_profile = relationship("LearnerProfile", back_populates="projects")


class AssessmentRecord(Base):
    """A learner's assessment result."""
    __tablename__ = "assessment_records"
    
    id = Column(Integer, primary_key=True, index=True)
    learner_profile_id = Column(Integer, ForeignKey("learner_profiles.id"), nullable=False, index=True)
    
    skill_element = Column(String, nullable=False)  # O*NET element name
    score = Column(Float, nullable=False)  # 0-100
    weak_concepts = Column(JSON, default=list)  # list of weak concept names
    attempt_number = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    learner_profile = relationship("LearnerProfile", back_populates="assessments")


class TaskCompletion(Base):
    """A real, persisted record that a learner marked one roadmap topic
    (a "task") as complete. topic_id matches the deterministic
    RoadmapTopic.id produced by backend/app/engines/roadmap.py for the
    learner's current target career + skill state (e.g.
    "essential_skills:2.A.1.a", "tool:Python"). Nothing here is a fake
    checkbox — completion state is looked up from this table on every
    request and drives both the Mountain frontier and the readiness
    "milestones" component.
    """
    __tablename__ = "task_completions"

    id = Column(Integer, primary_key=True, index=True)
    learner_profile_id = Column(Integer, ForeignKey("learner_profiles.id"), nullable=False, index=True)

    topic_id = Column(String, nullable=False, index=True)
    track = Column(String, nullable=True)          # "technical" | "professional", snapshot at completion time
    week_number = Column(Integer, nullable=True)
    label = Column(String, nullable=True)
    topic_type = Column(String, nullable=True)
    estimated_hours = Column(Float, nullable=True)

    completed_at = Column(DateTime, default=datetime.utcnow)

    learner_profile = relationship("LearnerProfile")


def _run_light_migrations():
    """SQLite ADD COLUMN migration for existing databases created before
    experience_text existed. Base.metadata.create_all() only creates
    missing TABLES, not missing COLUMNS on tables that already exist — so
    without this, a pre-existing learner_profiles row would break every
    query. New tables (e.g. task_completions) still come from create_all()
    below; this only patches the one column added to an existing table."""
    if "sqlite" not in DATABASE_URL:
        return
    with engine.connect() as conn:
        cols = [row[1] for row in conn.exec_driver_sql("PRAGMA table_info(learner_profiles)").fetchall()]
        if cols and "experience_text" not in cols:
            conn.exec_driver_sql("ALTER TABLE learner_profiles ADD COLUMN experience_text TEXT")
            conn.commit()


def init_db():
    """Initialize database tables."""
    _run_light_migrations()
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency injection for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
