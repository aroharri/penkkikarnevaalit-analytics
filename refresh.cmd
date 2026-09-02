@echo off
REM Ajaa refresh.ps1 riippumatta PowerShellin suorituskaytannosta.
REM Voit joko kaksoisklikata tata tiedostoa tai ajaa sen terminaalista.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0refresh.ps1"
echo.
echo Paina mita tahansa nappainta sulkeaksesi.
pause >nul
