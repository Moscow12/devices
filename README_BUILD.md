# Building TS-LISA Executable

## For Windows

### Method 1: Using the batch file (Easiest)
1. Double-click `build_liscom.bat`
2. The script will install PyInstaller if needed
3. Executable will be created in `dist\TS-LISA.exe`

### Method 2: Manual build
```cmd
pip install pyinstaller pyserial requests
pyinstaller --onefile --noconsole --name "TS-LISA" --hidden-import=serial.tools.list_ports liscom.py
```

### Method 3: Using the spec file
```cmd
pip install pyinstaller pyserial requests
pyinstaller liscom.spec
```

## For Linux/Mac

### Using the shell script
```bash
chmod +x build_liscom.sh
./build_liscom.sh
```

### Manual build
```bash
pip3 install pyinstaller pyserial requests
pyinstaller --onefile --noconsole --name "TS-LISA" --hidden-import=serial.tools.list_ports liscom.py
```

## Output Location
- **Windows**: `dist\TS-LISA.exe`
- **Linux/Mac**: `dist/TS-LISA`

## Requirements
- Python 3.7+
- PyInstaller
- pyserial
- requests

## Notes
- `--onefile`: Creates a single executable file
- `--noconsole`: Hides the console window (GUI only)
- `--hidden-import=serial.tools.list_ports`: Includes serial port detection module
- The executable will be standalone and can run on systems without Python installed
