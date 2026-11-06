# PyInstaller build spec for HosPi LIS -> dist\HosPiLis.exe
# Build on Windows with:  pyinstaller --clean HosPiLis.spec   (or just run build.bat)

a = Analysis(
    ['liscom.py'],
    pathex=[],
    binaries=[],
    # Bundled inside the exe so the window/taskbar icon works at runtime
    datas=[('hospi.ico', '.'), ('hospi.png', '.')],
    hiddenimports=['serial.tools.list_ports_windows'],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='HosPiLis',
    icon='hospi.ico',        # icon of the .exe file in Explorer / desktop shortcut
    console=False,           # GUI app: no black console window
    debug=False,
    strip=False,
    upx=False,               # UPX-packed exes are often flagged by antivirus
    runtime_tmpdir=None,
)
