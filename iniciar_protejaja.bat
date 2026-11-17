@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo ==================================================
echo   ProtejaJA - Inicializador Automatico
echo ==================================================
echo.

set "PY_CMD="

:: Verifica se python real esta instalado (ignora alias da Microsoft Store)
python -c "import sys" >nul 2>&1
if %errorlevel%==0 (
    set "PY_CMD=python"
) else (
    py -3 -c "import sys" >nul 2>&1
    if !errorlevel!==0 (
        set "PY_CMD=py -3"
    )
)

if defined PY_CMD goto :check_venv

echo [1/4] Python nao encontrado. Iniciando instalacao automatica...
where winget >nul 2>&1
if %errorlevel%==0 (
    echo       Instalando Python 3.12 via winget...
    winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements --silent
) else (
    echo       winget indisponivel. Baixando instalador oficial do Python 3.12...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe' -OutFile '$env:TEMP\python-installer.exe'"
    if exist "%TEMP%\python-installer.exe" (
        echo       Executando instalador silencioso...
        "%TEMP%\python-installer.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
        del "%TEMP%\python-installer.exe" >nul 2>&1
    )
)

:: Atualiza o PATH na sessao atual e tenta localizar o executavel instalado
for /f "delims=" %%P in ('powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')"') do set "PATH=%%P"

python -c "import sys" >nul 2>&1
if %errorlevel%==0 (
    set "PY_CMD=python"
) else if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
    set "PY_CMD=%LocalAppData%\Programs\Python\Python312\python.exe"
) else if exist "%ProgramFiles%\Python312\python.exe" (
    set "PY_CMD=%ProgramFiles%\Python312\python.exe"
)

if not defined PY_CMD (
    echo.
    echo [ERRO] Nao foi possivel instalar ou localizar o Python automaticamente.
    echo Instale manualmente em https://www.python.org/downloads/ marcando "Add Python to PATH".
    pause
    exit /b 1
)

:check_venv
echo [2/4] Python detectado: %PY_CMD%
if not exist ".venv\Scripts\python.exe" (
    echo       Criando ambiente virtual (.venv)...
    %PY_CMD% -m venv .venv
    if errorlevel 1 (
        echo [ERRO] Falha ao criar ambiente virtual.
        pause
        exit /b 1
    )
)

echo [3/4] Instalando/verificando dependencias (requirements.txt)...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERRO] Falha ao instalar dependencias.
    pause
    exit /b 1
)

echo [4/4] Iniciando servidor ProtejaJA e abrindo o navegador...
echo       Acesse: http://127.0.0.1:5000/home
echo       (Para encerrar o sistema, pressione Ctrl+C ou feche esta janela)
echo.

start "" /b cmd /c "timeout /t 3 /nobreak >nul & start http://127.0.0.1:5000/home"
".venv\Scripts\python.exe" run.py

pause
