@echo off
title Mini Hedge Fund - Daily Pipeline
cd /d %~dp0
echo ============================================
echo  Mini Hedge Fund - Daily Pipeline Runner
echo ============================================
echo.

call .venv\Scripts\activate

echo [1/5] Cleaning stale data...
del /q data\prices\*.parquet 2>nul
del /q data\prices\*.csv 2>nul
del /q data\features\*.parquet 2>nul
del /q data\signals\*.parquet 2>nul
del /q data\orders\*.parquet 2>nul
echo Done.

echo.
echo [2/5] Running ML Pipeline...
python scripts/run_all.py

echo.
echo Pipeline complete! Starting services...
echo.

echo [3/5] Starting FastAPI on port 8000...
start "FastAPI Backend" cmd /k ".venv\Scripts\activate && uvicorn api.main:app --host 0.0.0.0 --port 8000"

timeout /t 3 /nobreak >nul

echo [4/5] Starting Streamlit Dashboard on port 8501...
start "Streamlit Dashboard" cmd /k ".venv\Scripts\activate && streamlit run apps/apps.py --server.port 8501"

timeout /t 3 /nobreak >nul

echo [5/5] Starting React Frontend on port 5173...
start "React Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ============================================
echo  All services started!
echo  FastAPI:    http://localhost:8000/docs
echo  Streamlit:  http://localhost:8501
echo  React:      http://localhost:5173
echo ============================================
pause
