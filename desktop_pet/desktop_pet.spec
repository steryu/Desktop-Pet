# PyInstaller recipe. Build with build_windows.bat (-> dist/DesktopPet.exe)
# or ./build_mac.sh (-> dist/Desktop Pet.app). Run tools/make_icons.py first if assets/ is missing.
import sys
from pathlib import Path

here = Path(SPECPATH)
datas = [(str(here / "sprites"), "sprites")] if (here / "sprites").is_dir() else []

# big parts of Qt the pet never uses; leaving them out keeps the app much smaller
EXCLUDES = [
    "tkinter", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebChannel",
    "PySide6.QtQuick", "PySide6.QtQml", "PySide6.QtQuickWidgets", "PySide6.Qt3DCore",
    "PySide6.QtCharts", "PySide6.QtDataVisualization", "PySide6.QtGraphs", "PySide6.QtPdf",
    "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtBluetooth", "PySide6.QtNfc",
    "PySide6.QtSerialPort", "PySide6.QtPositioning", "PySide6.QtLocation", "PySide6.QtSensors",
    "PySide6.QtDesigner", "PySide6.QtHelp", "PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets",
]

a = Analysis(
    [str(here / "main.pyw")],
    pathex=[str(here)],
    datas=datas,
    hiddenimports=["store_window", "settings_window", "PySide6.QtMultimedia"],
    excludes=EXCLUDES,
)
pyz = PYZ(a.pure)

if sys.platform == "darwin":
    icon = str(here / "assets" / "icon.icns")
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="DesktopPet", console=False, icon=icon)
    coll = COLLECT(exe, a.binaries, a.datas, name="DesktopPet")
    app = BUNDLE(
        coll,
        name="Desktop Pet.app",
        icon=icon,
        bundle_identifier="com.desktoppet.app",
        info_plist={
            "LSUIElement": True,                 # no Dock icon: it lives in the menu bar
            "CFBundleShortVersionString": "1.0.0",
            "NSHighResolutionCapable": True,
        },
    )
else:
    icon = str(here / "assets" / "icon.ico")
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="DesktopPet", console=False, icon=icon)
