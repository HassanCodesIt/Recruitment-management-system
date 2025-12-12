@echo off
REM Recruitment Management System - Quick Setup Script for Windows
REM Run this script to set up the entire system

echo ========================================
echo Recruitment Management System - Setup
echo ========================================
echo.

REM Check Python installation
echo [1/6] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.11+ from python.org
    pause
    exit /b 1
)
python --version
echo.

REM Check PostgreSQL
echo [2/6] Checking PostgreSQL...
psql --version >nul 2>&1
if errorlevel 1 (
    echo WARNING: PostgreSQL not found in PATH
    echo Please ensure PostgreSQL is installed and running
    echo.
) else (
    psql --version
    echo.
)

REM Create virtual environment
echo [3/6] Creating virtual environment...
if exist venv (
    echo Virtual environment already exists
) else (
    python -m venv venv
    echo Virtual environment created
)
echo.

REM Activate virtual environment and install dependencies
echo [4/6] Installing dependencies...
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
echo.

REM Download Spacy model
echo [5/6] Downloading Spacy model...
python -m spacy download en_core_web_sm
echo.

REM Check .env file
echo [6/6] Checking configuration...
if exist .env (
    echo .env file found
) else (
    echo WARNING: .env file not found
    echo Copying from .env.template...
    copy .env.template .env
    echo.
    echo IMPORTANT: Please edit .env file with your credentials:
    echo   - Database password
    echo   - Email credentials
    echo   - Groq API key
    echo.
)

echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Next steps:
echo   1. Edit .env file with your credentials (if not done)
echo   2. Ensure PostgreSQL is running
echo   3. Run: python init_database.py
echo   4. Run: streamlit run app.py
echo.
echo To activate the virtual environment later:
echo   venv\Scripts\activate.bat
echo.

pause
