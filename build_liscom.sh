#!/bin/bash
echo "Building TS-LISA executable..."
echo ""

# Check if PyInstaller is installed
if ! python3 -m pip show pyinstaller &> /dev/null; then
    echo "PyInstaller not found. Installing..."
    python3 -m pip install pyinstaller pyserial requests
else
    echo "PyInstaller found."
fi

echo ""
echo "Building executable..."
pyinstaller --onefile --noconsole --name "TS-LISA" --hidden-import=serial.tools.list_ports liscom.py

echo ""
echo "Build complete!"
echo "Executable location: dist/TS-LISA"
echo ""
