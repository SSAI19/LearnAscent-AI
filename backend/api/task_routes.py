"""
Learning Tasks / Journey routes (new feature).

Exposes the learner's REAL personalized learning journey as a set of
completable tasks — no separate "task" data model is invented. Every task
here IS a RoadmapTopic produced live by the existing (unmodified)
`generate_roadmap` engine for the learner's current target career + skill
state. Completion state is the only new persisted concept
(`TaskCompletion`, see backend/db.py), and it is what actually drives:

  - GET  /api/engines/tasks            -> today's tasks + this week's tasks,
                                           each carrying real `completed`
                                           state
  - POST /api/engines/tasks/complete   -> mark one real topic complete
  - POST /api/engines/tasks/uncomplete -> undo that (fixes a mis-click,
                                           still real — no hidden state)

Marking a task complete/incomplete recomputes
LearnerProfile.completed_milestones / total_milestones from the live
roadmap (see engine_routes._sync_progress_counters), which is the exact
number the readiness engine's "milestones" component and the Mountain
Journey frontier (frontend/mountain.js) already read. Nothing else in the
existing architecture needed to change for the Mountain and Learner DNA to
reflect real progress — they already consumed that field, it just never
had real data written to it before now.
"""

import json
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from backend.db import get_db, User, LearnerProfile, TaskCompletion
from backend.api.auth_routes import get_current_user
from backend.api.engine_routes import (
    _learner_to_dataclass,
    _completed_topic_ids,
    _sync_progress_counters,
)
from backend.app.engines.roadmap import generate_roadmap

router = APIRouter(prefix="/api/engines/tasks", tags=["tasks"])

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"
with open(DATA_DIR / "occupations.json") as f:
    OCCUPATIONS = json.load(f)

# Keep "today" focused rather than an exhaustive list — a real daily study
# session, not the whole roadmap dumped on one page.
MAX_TODAY_TASKS = 4


class TaskItem(BaseModel):
    id: str
    label: str
    topic_type: str
    track: str
    week_number: int
    estimated_hours: float
    high_priority: bool
    detail: str
    completed: bool


class TasksResponse(BaseModel):
    today: List[TaskItem]
    this_week: List[TaskItem]
    week_number: Optional[int] = None
    completed_count: int
    total_count: int


class TaskActionRequest(BaseModel):
    topic_id: str


def _get_profile_or_404(current_user: User, db: Session) -> LearnerProfile:
    profile = db.query(LearnerProfile).filter(LearnerProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learner profile not found")
    if not profile.target_career_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No target career set")
    return profile


def _flatten_current_roadmap(profile: LearnerProfile, db: Session):
    """Regenerate the roadmap live (same engine call as everywhere else)
    and flatten it into one ordered list of real topics, annotated with
    real completed state. Ordering matches frontend/mountain.js: by week,
    technical before professional on ties."""
    occupation = OCCUPATIONS.get(profile.target_career_code)
    if not occupation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Occupation not found in O*NET data")

    learner = _learner_to_dataclass(profile)
    roadmap = generate_roadmap(learner, occupation)

    completed_ids = _completed_topic_ids(profile, db)

    flat = []
    for track_name, plan in (("technical", roadmap.technical), ("professional", roadmap.professional)):
        for milestone in plan.milestones:
            for t in milestone.topics:
                flat.append(TaskItem(
                    id=t.id, label=t.label, topic_type=t.topic_type, track=t.track,
                    week_number=milestone.week_number, estimated_hours=t.estimated_hours,
                    high_priority=t.high_priority, detail=t.detail,
                    completed=t.id in completed_ids,
                ))
    flat.sort(key=lambda x: (x.week_number, 0 if x.track == "technical" else 1, not x.high_priority))
    return flat, roadmap


@router.get("", response_model=TasksResponse)
def get_tasks(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return the learner's real daily + weekly tasks, derived live from
    their current roadmap, with real persisted completion state."""
    profile = _get_profile_or_404(current_user, db)
    flat, roadmap = _flatten_current_roadmap(profile, db)

    # Keep counters in sync even if the roadmap shifted (e.g. a skill
    # improved enough that a topic dropped out) since the learner is
    # actively viewing this page.
    _sync_progress_counters(profile, roadmap, db)
    db.commit()

    if not flat:
        return TasksResponse(today=[], this_week=[], week_number=None, completed_count=0, total_count=0)

    incomplete = [t for t in flat if not t.completed]
    # Current week = earliest week that still has an incomplete task; once
    # everything is done, fall back to the last week so the page still
    # shows something rather than going blank.
    current_week = incomplete[0].week_number if incomplete else flat[-1].week_number

    this_week = [t for t in flat if t.week_number == current_week]
    today = [t for t in this_week if not t.completed][:MAX_TODAY_TASKS]
    if not today:
        # Everything in the current week is already done — show it anyway
        # so "today" isn't an empty dead end.
        today = this_week[:MAX_TODAY_TASKS]

    return TasksResponse(
        today=today,
        this_week=this_week,
        week_number=current_week,
        completed_count=sum(1 for t in flat if t.completed),
        total_count=len(flat),
    )


@router.post("/complete", response_model=TasksResponse)
def complete_task(
    req: TaskActionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Persist real completion of one roadmap topic for this learner, then
    return the refreshed task list (so the UI updates from one round trip
    without a stale local checkbox)."""
    profile = _get_profile_or_404(current_user, db)
    flat, roadmap = _flatten_current_roadmap(profile, db)
    match = next((t for t in flat if t.id == req.topic_id), None)
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                             detail="That task is not part of your current roadmap")

    existing = db.query(TaskCompletion).filter(
        TaskCompletion.learner_profile_id == profile.id,
        TaskCompletion.topic_id == req.topic_id,
    ).first()
    if not existing:
        db.add(TaskCompletion(
            learner_profile_id=profile.id, topic_id=match.id, track=match.track,
            week_number=match.week_number, label=match.label, topic_type=match.topic_type,
            estimated_hours=match.estimated_hours,
        ))
        db.commit()

    _sync_progress_counters(profile, roadmap, db)
    db.commit()
    return get_tasks(current_user=current_user, db=db)


@router.post("/uncomplete", response_model=TasksResponse)
def uncomplete_task(
    req: TaskActionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Undo a completion (correcting a mis-click) — still real state, just
    removed rather than hidden."""
    profile = _get_profile_or_404(current_user, db)

    existing = db.query(TaskCompletion).filter(
        TaskCompletion.learner_profile_id == profile.id,
        TaskCompletion.topic_id == req.topic_id,
    ).first()
    if existing:
        db.delete(existing)
        db.commit()

    _, roadmap = _flatten_current_roadmap(profile, db)
    _sync_progress_counters(profile, roadmap, db)
    db.commit()
    return get_tasks(current_user=current_user, db=db)
