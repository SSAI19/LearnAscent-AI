"""
LearnAscent AI Backend — FastAPI Application.

Main entry point for the backend API server.
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from backend.db import init_db
from backend.api import auth_routes, learner_routes, engine_routes, recommendation_routes, mentor_routes, task_routes

# Load environment variables
load_dotenv()

# Initialize database
init_db()

# Create FastAPI app
app = FastAPI(
    title="LearnAscent AI",
    description="Personalized learning platform powered by O*NET intelligence",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", "http://localhost:5500",
        "http://127.0.0.1:5500", "http://127.0.0.1:3000", "file://",
    ],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_routes.router)
app.include_router(learner_routes.router)
app.include_router(engine_routes.router)
app.include_router(recommendation_routes.router)
app.include_router(mentor_routes.router)
app.include_router(task_routes.router)


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "message": "LearnAscent AI Backend",
        "docs": "/docs",
        "endpoints": {
            "auth": "/api/auth/docs",
            "learner": "/api/learner/docs",
            "engines": "/api/engines/docs"
        }
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    
    # Run with: python -m uvicorn backend.main:app --reload
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
