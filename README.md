# LearnAscent AI

Personalized learning platform powered by O*NET occupation data — merged/integrated
build combining the FastAPI + auth + SQLite backend with the two-track
(technical / professional) roadmap engine and the fuller Learner DNA visual.

## Run the backend

```
cd backend  # from project root, but run uvicorn from the project root itself:
cd ..
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

API docs: http://127.0.0.1:8000/docs

## Run the frontend

```
cd frontend
python3 -m http.server 5500
```

Open: http://127.0.0.1:5500/index.html

## First run

The app starts with an empty `learnascent.db` (SQLite) — sign up, then fill in
the onboarding form (name + target career + time budget) to create your real
learner profile. No demo/fake data is ever attached to a real account.
