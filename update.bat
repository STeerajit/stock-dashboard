@echo off
rem Update the SET100 dashboard to the latest version: double-click this file.
rem Close the dashboard window first: Windows cannot replace packages that are in use.
cd /d "%~dp0"

rem Everything below is one block, so cmd reads it all before git pull can change this file.
(
    where git >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Git is not installed. Install it from https://git-scm.com/download/win
        pause
        exit /b 1
    )
    echo Downloading the latest version...
    git pull
    if errorlevel 1 (
        echo.
        echo ERROR: Downloading the update failed. See the messages above.
        pause
        exit /b 1
    )
    if not exist ".venv\Scripts\python.exe" (
        echo Done. Double-click start.bat to set up and start the dashboard.
        pause
        exit /b 0
    )
    echo Updating the packages...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo ERROR: Updating the packages failed. Close the dashboard window and try again.
        pause
        exit /b 1
    )
    echo.
    echo Update finished. Double-click start.bat to start the dashboard.
    pause
    exit /b 0
)
