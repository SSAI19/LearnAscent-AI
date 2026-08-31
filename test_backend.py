#!/usr/bin/env python3
"""
Test script to verify backend functionality without running a server.
"""

import sys
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Test imports
try:
    from backend.db import init_db, SessionLocal, User, LearnerProfile
    from backend.auth import hash_password, verify_password, create_access_token, verify_token
    from backend.app.ingestion.occupation_matcher import OccupationMatcher
    from backend.app.models.learner import LearnerProfile as LearnerDataClass
    from backend.app.engines.skill_gap import analyze_skill_gap
    from backend.app.engines.readiness import compute_readiness
    from backend.app.engines.roadmap import generate_roadmap
    print("✓ All imports successful")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)

# Test database initialization
try:
    init_db()
    print("✓ Database initialized")
except Exception as e:
    print(f"✗ Database init error: {e}")
    sys.exit(1)

# Test password hashing
try:
    pwd = "test123"  # Short password to avoid bcrypt 72-byte limit
    hashed = hash_password(pwd)
    assert verify_password(pwd, hashed), "Password verification failed"
    assert not verify_password("wrong", hashed), "Wrong password should fail"
    print("✓ Password hashing works")
except Exception as e:
    print(f"✗ Password hashing error: {e}")
    sys.exit(1)

# Test JWT tokens
try:
    token = create_access_token(user_id=1)
    user_id = verify_token(token)
    assert user_id == 1, f"Token verification returned {user_id} instead of 1"
    print("✓ JWT token generation and verification works")
except Exception as e:
    print(f"✗ JWT token error: {e}")
    sys.exit(1)

# Test occupation matcher
try:
    matcher = OccupationMatcher()
    matches = matcher.match("data scientist", top_k=3)
    assert len(matches) > 0, "No matches found for 'data scientist'"
    print(f"✓ Occupation matcher works (found {len(matches)} matches)")
    print(f"  Top match: {matches[0].code} - {matches[0].title}")
except Exception as e:
    print(f"✗ Occupation matcher error: {e}")
    sys.exit(1)

# Test engines with demo learner
try:
    occupations = json.loads((Path(__file__).parent / "backend" / "data" / "processed" / "occupations.json").read_text())
    learner = LearnerDataClass(
        user_id="test-1",
        target_career_code="15-2051.00",
        target_career_title="Data Scientists",
        experience_level="beginner",
        known_tools={"Python"},
    )
    occupation = occupations["15-2051.00"]
    
    # Test skill gap
    gap_results = analyze_skill_gap(learner, occupation, source="essential_skills")
    assert len(gap_results) > 0, "No skill gaps found"
    print(f"✓ Skill gap analysis works ({len(gap_results)} gaps)")
    
    # Test readiness
    readiness = compute_readiness(learner, gap_results)
    assert 0 <= readiness.readiness_score <= 100, f"Invalid readiness score: {readiness.readiness_score}"
    print(f"✓ Readiness calculation works (score: {readiness.readiness_score})")
    
    # Test roadmap
    roadmap = generate_roadmap(learner, occupation)
    assert len(roadmap.milestones) > 0, "No roadmap milestones generated"
    print(f"✓ Roadmap generation works ({len(roadmap.milestones)} milestones)")
except Exception as e:
    print(f"✗ Engine error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✓✓✓ All Phase A backend tests passed! ✓✓✓")
