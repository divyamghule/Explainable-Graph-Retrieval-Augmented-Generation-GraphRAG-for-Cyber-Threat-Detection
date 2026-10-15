@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    py -3 -m venv .venv
    if errorlevel 1 (
        echo Could not create .venv. Install Python 3.10+ and enable the py launcher.
        exit /b 1
    )
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if not exist ".env" (
    copy /Y ".env.example" ".env" >nul
    echo Created .env from .env.example.
    echo Edit .env with your Neo4j password and a newly generated Gemini API key, then run this file again.
    pause
    exit /b 0
)

start "GraphRAG detector" cmd /k ""%~dp0.venv\Scripts\python.exe" "%~dp0detector.py""
start "Website server" cmd /k ""%~dp0.venv\Scripts\python.exe" "%~dp0run.py""

set "CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" set "CHROME=%LocalAppData%\Google\Chrome\Application\chrome.exe"
if exist "%CHROME%" (
    start "" "%CHROME%" --new-window "http://127.0.0.1:8001"
    start "" "%CHROME%" --new-window "http://127.0.0.1:8001/security-dashboard"
) else (
    start "" "http://127.0.0.1:8001"
    start "" "http://127.0.0.1:8001/security-dashboard"
)

endlocal