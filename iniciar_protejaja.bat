@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ==================================================
echo   ProtejaJA - Inicializador Automatico
echo ==================================================
echo.

set "PY_EXE="
set "PY_ARGS="

call :encontrar_python
if defined PY_EXE goto :python_pronto

echo [1/4] Python nao encontrado. Instalando Python 3.14...
where winget >nul 2>&1
if errorlevel 1 goto :baixar_oficial

echo       Tentando instalar via winget (Python 3.14)...
winget install -e --id Python.Python.3.14 --accept-package-agreements --accept-source-agreements --silent
call :atualizar_path
call :encontrar_python
if defined PY_EXE goto :python_pronto

:baixar_oficial
echo       Baixando instalador oficial do Python 3.14.0...
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.14.0/python-3.14.0-amd64.exe' -OutFile '%TEMP%\python-installer.exe' -UseBasicParsing"
if not exist "%TEMP%\python-installer.exe" goto :erro_python

echo       Instalando Python 3.14.0 silenciosamente (aguarde)...
"%TEMP%\python-installer.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
del "%TEMP%\python-installer.exe" >nul 2>&1

call :atualizar_path
call :encontrar_python
if defined PY_EXE goto :python_pronto

:erro_python
echo.
echo [ERRO] Nao foi possivel instalar ou localizar o Python automaticamente.
echo Baixe em https://www.python.org/downloads/ e marque "Add Python to PATH".
goto :fim_erro

:python_pronto
echo [2/4] Python detectado: "%PY_EXE%" %PY_ARGS%

set "RUN_PY=%PY_EXE%"
set "RUN_ARGS=%PY_ARGS%"

if exist ".venv\Scripts\python.exe" (
    set "RUN_PY=.venv\Scripts\python.exe"
    set "RUN_ARGS="
    goto :instalar_deps
)

echo       Criando ambiente virtual (.venv)...
"%PY_EXE%" %PY_ARGS% -m venv .venv >nul 2>&1
if exist ".venv\Scripts\python.exe" (
    set "RUN_PY=.venv\Scripts\python.exe"
    set "RUN_ARGS="
) else (
    echo       Aviso: usando Python do sistema diretamente.
)

:instalar_deps
echo [3/4] Instalando/verificando dependencias (requirements.txt)...
"%RUN_PY%" %RUN_ARGS% -m pip install -r requirements.txt
if errorlevel 1 (
    echo       Tentando instalar com --user...
    "%RUN_PY%" %RUN_ARGS% -m pip install --user -r requirements.txt
    if errorlevel 1 goto :erro_deps
)
goto :iniciar_servidor

:erro_deps
echo.
echo [ERRO] Falha ao instalar dependencias do requirements.txt.
goto :fim_erro

:iniciar_servidor
echo [4/4] Iniciando servidor ProtejaJA...
echo       Abrindo http://127.0.0.1:5000/home no navegador...
echo       (Para encerrar, pressione Ctrl+C ou feche esta janela)
echo.

start "" cmd /c "timeout /t 3 /nobreak >nul & start http://127.0.0.1:5000/home"
"%RUN_PY%" %RUN_ARGS% run.py
if errorlevel 1 goto :erro_servidor
goto :fim

:erro_servidor
echo.
echo [ERRO] O servidor foi encerrado com erro.

:fim_erro
echo.
pause
exit /b 1

:fim
pause
exit /b 0

:: ==========================================================
:: SUB-ROTINAS
:: ==========================================================

:encontrar_python
set "PY_EXE="
set "PY_ARGS="

for /f "delims=" %%I in ('python -c "import sys; print(sys.executable)" 2^>nul') do (
    if exist "%%I" (
        set "PY_EXE=%%I"
        exit /b 0
    )
)

for /f "delims=" %%I in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do (
    if exist "%%I" (
        set "PY_EXE=%%I"
        exit /b 0
    )
)

for %%V in (314 313 312 311 310) do (
    if exist "%LocalAppData%\Programs\Python\Python%%V\python.exe" (
        set "PY_EXE=%LocalAppData%\Programs\Python\Python%%V\python.exe"
        exit /b 0
    )
    if exist "%ProgramFiles%\Python%%V\python.exe" (
        set "PY_EXE=%ProgramFiles%\Python%%V\python.exe"
        exit /b 0
    )
    if exist "C:\Python%%V\python.exe" (
        set "PY_EXE=C:\Python%%V\python.exe"
        exit /b 0
    )
)
exit /b 1

:atualizar_path
for /f "delims=" %%P in ('powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')" 2^>nul') do set "PATH=%%P"
exit /b 0
