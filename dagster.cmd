@echo off
REM Kaynnistaa Dagsterin kayttoliittyman osoitteeseen http://localhost:3000
REM Sulje ikkuna tai paina Ctrl+C lopettaaksesi.
cd /d "%~dp0"
set DAGSTER_HOME=%~dp0.dagster_home
if not exist "%DAGSTER_HOME%" mkdir "%DAGSTER_HOME%"
"%~dp0.venv\Scripts\python.exe" -m dagster dev -m orchestration.assets -p 3000
