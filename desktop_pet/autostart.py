"""Start the pet when you log in.

Windows: a value under HKCU\\...\\CurrentVersion\\Run.
macOS:   a LaunchAgent in ~/Library/LaunchAgents (applies from the next login).
Linux:   a .desktop file in ~/.config/autostart.
Nothing here needs admin rights, and turning it off removes what was added.
"""
import os
import sys
from pathlib import Path
from xml.sax.saxutils import escape

LABEL = "com.desktoppet.app"
WIN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
WIN_NAME = "DesktopPet"


def command(frozen=None, executable=None, main=None, exists=os.path.exists):
    """How to launch the app: the packaged app itself, or python + main.py."""
    frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    executable = executable or sys.executable
    if frozen:
        return [executable]
    main = main or str(Path(__file__).resolve().parent / "main.py")
    if executable.lower().endswith("python.exe"):           # Windows: no console window
        pythonw = executable[:-len("python.exe")] + "pythonw.exe"
        if exists(pythonw):
            return [pythonw, main[:-3] + ".pyw" if main.endswith(".py") else main]
    return [executable, main]


def mac_plist(cmd):
    args = "\n".join(f"        <string>{escape(a)}</string>" for a in cmd)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{LABEL}</string>
    <key>ProgramArguments</key>
    <array>
{args}
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
"""


def linux_desktop(cmd):
    exec_line = " ".join(f'"{a}"' for a in cmd)
    return f"""[Desktop Entry]
Type=Application
Name=Desktop Pet
Exec={exec_line}
X-GNOME-Autostart-enabled=true
"""


def entry_path(platform=None, home=None):
    platform = platform or sys.platform
    home = Path(home) if home else Path.home()
    if platform == "darwin":
        return home / "Library" / "LaunchAgents" / f"{LABEL}.plist"
    return home / ".config" / "autostart" / "desktop-pet.desktop"


def is_enabled(platform=None, home=None):
    platform = platform or sys.platform
    if platform == "win32":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, WIN_KEY) as k:
                winreg.QueryValueEx(k, WIN_NAME)
            return True
        except OSError:
            return False
    return entry_path(platform, home).exists()


def set_enabled(on, platform=None, home=None, cmd=None):
    platform = platform or sys.platform
    cmd = cmd or command()
    if platform == "win32":
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, WIN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            if on:
                winreg.SetValueEx(k, WIN_NAME, 0, winreg.REG_SZ, " ".join(f'"{a}"' for a in cmd))
            else:
                try:
                    winreg.DeleteValue(k, WIN_NAME)
                except OSError:
                    pass
        return
    path = entry_path(platform, home)
    if on:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(mac_plist(cmd) if platform == "darwin" else linux_desktop(cmd))
    elif path.exists():
        path.unlink()
