@echo off
rem Start the SET100 dashboard on Windows: double-click this file.
rem The first run creates the .venv folder and installs the packages (5-15 minutes).
rem Later runs start the dashboard at once. Close this window to stop the dashboard.
cd /d "%~dp0"

if exist ".venv\installed.txt" goto run
if exist ".venv\Scripts\python.exe" goto install

echo First run: setting up the dashboard. This happens only once.
echo Creating the Python environment in the .venv folder...
py -3.11 -m venv .venv >nul 2>&1
if not exist ".venv\Scripts\python.exe" python -m venv .venv
if not exist ".venv\Scripts\python.exe" goto nopython

:install
echo Installing the packages the dashboard needs.
echo This can take 5-15 minutes. Please wait and do not close this window...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto installfailed
echo ok> ".venv\installed.txt"
echo Setup finished.

:run
set "STOCKS_LANG=th"
echo.
echo Starting the dashboard. Your browser will open at http://localhost:8501
echo Keep this window open while you use the dashboard. Close it to stop the dashboard.
echo.
".venv\Scripts\python.exe" -m streamlit run app.py --server.address localhost --server.showEmailPrompt false
if errorlevel 1 goto runfailed
goto :eof

:nopython
echo.
echo ERROR: Python was not found.
echo Install Python 3.11 from https://www.python.org/downloads/windows/
echo and tick "Add python.exe to PATH" in the installer. Then double-click start.bat again.
pause
exit /b 1

:installfailed
echo.
echo ERROR: Installing the packages failed. See the messages above.
echo Check the internet connection, then double-click start.bat again.
echo The dashboard needs Python 3.11 or newer.
pause
exit /b 1

:runfailed
echo.
echo ERROR: The dashboard stopped with an error. See the messages above.
pause
exit /b 1
