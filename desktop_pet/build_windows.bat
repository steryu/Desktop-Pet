@echo off
rem Builds dist\DesktopPet.exe (a single file). Run from this folder on Windows.
python -m pip install -r requirements.txt pyinstaller || exit /b 1
python tools\make_icons.py || exit /b 1
python -m PyInstaller --noconfirm --clean desktop_pet.spec || exit /b 1
echo.
echo Done: dist\DesktopPet.exe
