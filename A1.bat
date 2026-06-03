@echo off
cd /d "%~dp0wpc_admin"
start "" http://localhost:8000
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
