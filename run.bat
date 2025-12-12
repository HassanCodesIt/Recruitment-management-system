@echo off
REM Quick Start Script for Recruitment Management System

echo Starting Recruitment Management System...
echo.

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Start Streamlit app
streamlit run app.py

pause
