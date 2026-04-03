@echo off
echo Starting AI Assistant...
docker start ollama openclaw
echo.
echo Waiting for models to load...
timeout /t 25 /nobreak > nul
echo.
echo Starting Job Finder in background...
start "Arpan Job Finder" /MIN cmd /c "cd /d C:\assistant && .\assist_enve\Scripts\activate && python job_finder.py"
echo.
echo Done!
echo  - Telegram bot is online
echo  - Job finder is running in background
echo  - Results will arrive on Telegram in 45-60 min
pause