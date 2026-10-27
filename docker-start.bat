@echo off
title AICTE Scrutiny Platform - Docker Launch
echo ======================================================================
echo Starting AICTE Regulatory Scrutiny Platform via Docker Compose...
echo ======================================================================

docker compose up --build -d

echo.
echo ======================================================================
echo Containers started!
echo Frontend (AICTE Validation Portal): http://localhost:3000 or http://localhost:5173
echo Backend (FastAPI Swagger UI):      http://localhost:8000/docs
echo Backend Healthcheck:               http://localhost:8000/api/v1/health
echo ======================================================================
pause
