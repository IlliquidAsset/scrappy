@echo off
title Scrappy Installer and Runner



:: Check for Git
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Git is not installed. Attempting to install using winget...
    winget install --id Git.Git -e --source winget
    if %errorlevel% neq 0 (
        echo Failed to install Git. Please install Git manually from https://git-scm.com/.
        call :pause_script
    )
)

:: Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed. Attempting to install using winget...
    winget install --id Python.Python.3 -e --source winget
    if %errorlevel% neq 0 (
        echo Failed to install Python. Please install Python manually from https://www.python.org/.
        call :pause_script
    )
)

:: Set up Scrappy
cd %USERPROFILE%
if not exist "scrappy" (
    echo Scrappy folder not found. Cloning repository...
    git clone https://github.com/IlliquidAsset/scrappy
) else (
    echo Scrappy folder found. Pulling latest changes...
    cd scrappy
    git pull
    cd ..
)

:: Navigate to Scrappy folder
cd scrappy

:: Install dependencies
echo Installing required Python packages...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Error installing dependencies. Ensure pip is configured correctly and try again.
    call :pause_script
)

:: Launch Scrappy
echo Starting Scrappy...
python main.py

:: Pause to allow the user to see any output
pause
