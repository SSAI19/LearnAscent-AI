#!/usr/bin/env python3
"""
Start the LearnAscent AI backend server.
Usage: python run_server.py
"""

import uvicorn
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

if __name__ == "__main__":
    print("Starting LearnAscent AI Backend...")
    print("Server will be available at: http://127.0.0.1:8000")
    print("API Documentation: http://127.0.0.1:8000/docs")
    print("ReDoc Documentation: http://127.0.0.1:8000/redoc")
    print("")
    print("Press CTRL+C to stop the server")
    print("")
    
    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )
