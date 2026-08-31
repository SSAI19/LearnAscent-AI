"""
Learner DNA — the profile every engine in this backend reads from.

This is intentionally a plain, serializable dataclass (not tied to a DB
driver yet) so Phase 2's engines can be built and tested against it before
Phase 2's DB models exist. Skill levels use O*NET's own 0-7 Level scale so
learner skills and occupation requirements are directly comparable without
a conversion step — that's the whole point of using O*NET data at all.
"""

from dataclasses import dataclass, field


@dataclass
class SkillRecord:
    element: str                 # must match an O*NET Element Name (Essential Skills / Knowledge / Abilities)
    level: float                 # 0-7, same scale as O*NET's LV
    source: str = "self_reported"  # "self_reported" | "assessment" | "project_verified"
    last_updated: str | None = None


@dataclass
class ProjectRecord:
    name: str
    skills_demonstrated: list[str] = field(default_factory=list)
    quality_score: float | None = None  # 0-100, from Feature 16 project review, if run


@dataclass
class AssessmentRecord:
    skill_element: str
    score: float          # 0-100
    weak_concepts: list[str] = field(default_factory=list)
    attempt_number: int = 1


@dataclass
class LearnerProfile:
    user_id: str
    target_career_code: str            # O*NET-SOC Code, from occupation_matcher
    target_career_title: str
    experience_level: str = "beginner"  # "beginner" | "intermediate" | "advanced"
    skills: dict[str, SkillRecord] = field(default_factory=dict)   # keyed by O*NET Element Name (0-7 level)
    known_tools: set[str] = field(default_factory=set)             # keyed by O*NET Software Skill name — binary,
                                                                     # since O*NET's Software Skills table has no
                                                                     # proficiency scale, only presence/hot/in-demand
    projects: list[ProjectRecord] = field(default_factory=list)
    assessments: list[AssessmentRecord] = field(default_factory=list)
    completed_milestones: int = 0
    total_milestones: int = 0
    available_minutes_per_day: int = 30
    target_duration_weeks: int = 12
    preferred_language: str = "en"

    def skill_level(self, element: str) -> float:
        rec = self.skills.get(element)
        return rec.level if rec else 0.0

    def knows_tool(self, tool_name: str) -> bool:
        return any(tool_name.lower() in t.lower() or t.lower() in tool_name.lower()
                    for t in self.known_tools)

    def demonstrated_skill_names(self) -> set[str]:
        """Skills backed by a project, not just self-reported."""
        return {rec.element for rec in self.skills.values() if rec.source == "project_verified"}


def demo_learner() -> LearnerProfile:
    """
    The Demo Mode persona from the spec: beginner, target an AI/software
    career, current skills = basic Python only. Used to exercise every
    engine end-to-end without needing a real onboarding flow yet.
    """
    return LearnerProfile(
        user_id="demo-learner-1",
        target_career_code="15-2051.00",   # Data Scientists — resolved via occupation_matcher
        target_career_title="Data Scientists",
        experience_level="beginner",
        skills={
            "Programming": SkillRecord(element="Programming", level=2.0, source="self_reported"),
            "Critical Thinking": SkillRecord(element="Critical Thinking", level=3.0, source="self_reported"),
            "Mathematics": SkillRecord(element="Mathematics", level=2.5, source="self_reported"),
        },
        known_tools={"Python"},
        projects=[],
        assessments=[],
        completed_milestones=0,
        total_milestones=0,
        available_minutes_per_day=30,
        target_duration_weeks=12,
        preferred_language="en",
    )
