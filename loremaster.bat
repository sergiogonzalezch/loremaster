@echo off
setlocal enabledelayedexpansion
pushd "%~dp0"

for /f "usebackq" %%a in (`powershell -NoProfile -Command "[char]27"`) do set "ESC=%%a"
set "C=%ESC%[96m"
set "Y=%ESC%[93m"
set "G=%ESC%[92m"
set "R=%ESC%[91m"
set "D=%ESC%[90m"
set "W=%ESC%[97m"
set "Z=%ESC%[0m"

:MENU
cls
echo.
echo  %C%  +==========================================+%Z%
echo  %C%  +%Z%       %W%LOREMASTER  --  DEV LAUNCHER%Z%        %C%+%Z%
echo  %C%  +==========================================+%Z%
echo.
echo  %Y%  LOCAL%Z%
echo   %G%  1%Z%  Dev SQLite        .\dev.ps1
echo   %G%  2%Z%  Dev PostgreSQL    .\dev.ps1 -Postgres
echo.
echo  %Y%  INFRA%Z%
echo   %G%  3%Z%  Levantar SQLite   make infra
echo   %G%  4%Z%  Levantar Postgres make infra-pg
echo   %G%  5%Z%  Bajar todo        make down
echo.
echo  %Y%  TESTS%Z%
echo   %G%  6%Z%  Ejecutar suite    cd backend ^&^& make test
echo.
echo  %Y%  PRODUCCION / DEMO%Z%
echo   %G%  7%Z%  Prod UP           make prod-up
echo   %G%  8%Z%  Prod DOWN         make prod-down
echo.
echo   %R%  9%Z%  Salir y cerrar servicios
echo.
choice /c 123456789 /n /m "  > "
set OPT=%errorlevel%
goto HANDLE_%OPT%

:HANDLE_1
cls
echo.
echo  %C%  Abriendo entorno Dev -- SQLite...%Z%
echo.
powershell -ExecutionPolicy Bypass -File ".\dev.ps1"
echo.
echo  %D%  Ventanas abiertas. Volviendo al menu...%Z%
timeout /t 2 /nobreak >nul
goto MENU

:HANDLE_2
cls
echo.
echo  %C%  Abriendo entorno Dev -- PostgreSQL...%Z%
echo.
powershell -ExecutionPolicy Bypass -File ".\dev.ps1" -Postgres
echo.
echo  %D%  Ventanas abiertas. Volviendo al menu...%Z%
timeout /t 2 /nobreak >nul
goto MENU

:HANDLE_3
cls
echo.
echo  %C%  Levantando infra SQLite (Qdrant + Redis)...%Z%
echo.
make infra
echo.
echo  %G%  Listo.%Z%
pause
goto MENU

:HANDLE_4
cls
echo.
echo  %C%  Levantando infra PostgreSQL...%Z%
echo.
make infra-pg
echo.
echo  %G%  Listo.%Z%
pause
goto MENU

:HANDLE_5
cls
echo.
echo  %C%  Bajando infraestructura...%Z%
echo.
make down
echo.
echo  %G%  Listo.%Z%
pause
goto MENU

:HANDLE_6
cls
echo.
echo  %C%  Ejecutando tests...%Z%
echo.
pushd backend
call make test
popd
echo.
pause
goto MENU

:HANDLE_7
cls
echo.
echo  %C%  Levantando produccion / demo...%Z%
echo.
make prod-up
echo.
echo  %G%  Listo.%Z%
pause
goto MENU

:HANDLE_8
cls
echo.
echo  %C%  Bajando produccion...%Z%
echo.
make prod-down
echo.
echo  %G%  Listo.%Z%
pause
goto MENU

:HANDLE_9
cls
echo.
echo  %C%  Cerrando backend, frontend e infraestructura...%Z%
echo.

echo  %D%  Cerrando backend...%Z%
if exist ".loremaster_backend_pid" (
    for /f %%a in (.loremaster_backend_pid) do taskkill /PID %%a /F /T >nul 2>&1
    del ".loremaster_backend_pid" >nul 2>&1
)
taskkill /F /FI "WINDOWTITLE eq loremaster-backend" >nul 2>&1
powershell -NoProfile -Command "for($i=0;$i -lt 5;$i++){$p=(netstat -ano|Select-String ':8000\s+\S+\s+LISTENING')|ForEach-Object{($_ -split '\s+')[-1]}|Select-Object -First 1; if(-not $p){break}; $pp=[int]$p; if($pp -le 4){break}; $r=(Get-CimInstance Win32_Process -Filter('ProcessId='+$pp) -Property ParentProcessId -EA SilentlyContinue).ParentProcessId; if($r -and $r -gt 4){Stop-Process -Id $r -Force -EA SilentlyContinue}; Stop-Process -Id $pp -Force -EA SilentlyContinue; Start-Sleep -Milliseconds 500}"

echo  %D%  Cerrando frontend (Vite en :5173)...%Z%
if exist ".loremaster_frontend_pid" (
    for /f %%a in (.loremaster_frontend_pid) do taskkill /PID %%a /F /T >nul 2>&1
    del ".loremaster_frontend_pid" >nul 2>&1
)
taskkill /F /FI "WINDOWTITLE eq loremaster-frontend" >nul 2>&1
powershell -NoProfile -Command "for($i=0;$i -lt 5;$i++){$p=(netstat -ano|Select-String ':5173\s+\S+\s+LISTENING')|ForEach-Object{($_ -split '\s+')[-1]}|Select-Object -First 1; if(-not $p){break}; $pp=[int]$p; if($pp -le 4){break}; $r=(Get-CimInstance Win32_Process -Filter('ProcessId='+$pp) -Property ParentProcessId -EA SilentlyContinue).ParentProcessId; if($r -and $r -gt 4){Stop-Process -Id $r -Force -EA SilentlyContinue}; Stop-Process -Id $pp -Force -EA SilentlyContinue; Start-Sleep -Milliseconds 500}"

echo  %D%  Bajando infraestructura Docker...%Z%
docker compose -f backend\docker-compose.yml down
docker stop postgres >nul 2>&1
docker rm   postgres >nul 2>&1

echo.
echo  %G%  Todo cerrado.%Z%
echo.
timeout /t 2 /nobreak >nul
popd
endlocal
exit /b 0
