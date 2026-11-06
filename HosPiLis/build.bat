@echo off
REM Builds dist\HosPiLis.exe  (run on Windows, from this folder)
cd /d "%~dp0"

where py >nul 2>nul && (set PY=py -3) || (set PY=python)

echo === Creating build environment ===
%PY% -m venv .venv || goto :error
call .venv\Scripts\activate.bat || goto :error
python -m pip install --upgrade pip || goto :error
pip install -r requirements.txt || goto :error

echo === Building HosPiLis.exe ===
pyinstaller --clean --noconfirm HosPiLis.spec || goto :error

echo.
echo Done:  %~dp0dist\HosPiLis.exe
pause
exit /b 0

:error
echo.
echo BUILD FAILED
pause
exit /b 1
