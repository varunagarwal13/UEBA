@echo off
echo Starting UEBA V2 Backend...
cd %~dp0backend
set PYTHONPATH=%~dp0
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
