@echo off
title AICTE Scrutiny Backend Service
echo Starting AICTE Regulatory Scrutiny Backend (FastAPI)...
cd backend
set PYTHONPATH=.
python -m uvicorn app.main:app --reload --port 8000
pause
