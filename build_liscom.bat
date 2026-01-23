@echo off
echo Building TS-LISA executable for Windows...
echo.

REM Check if PyInstaller is installed
python -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    python -m pip install pyinstaller pyserial requests
) else (
    echo PyInstaller found.
)

echo.
echo Building executable...
pyinstaller --onefile --noconsole --name "TS-LISA" --hidden-import=serial.tools.list_ports liscom.py

echo.
echo Build complete!
echo Executable location: dist\TS-LISA.exe
echo.
pause
