#!/bin/sh
# Builds "dist/Desktop Pet.app". Run from this folder on macOS.
set -e
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt pyinstaller
.venv/bin/python tools/make_icons.py
.venv/bin/python -m PyInstaller --noconfirm --clean desktop_pet.spec
echo "Done: dist/Desktop Pet.app"
