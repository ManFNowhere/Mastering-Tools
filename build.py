#!/usr/bin/env python3
"""
build.py — build SS-Mastering as a standalone desktop app

Packages the app into a self-contained executable using PyInstaller.
Run this on each target OS to produce a native build for that platform:
  - macOS  → dist/SS-Mastering.app
  - Windows → dist/SS-Mastering/SS-Mastering.exe
  - Linux   → dist/SS-Mastering/SS-Mastering

Prerequisites:
  - Run run.py at least once so the virtual environment (.venv) exists.

Usage:
    python build.py
"""

import sys
import os
import shutil
import platform
import subprocess

APP_NAME    = "SS-Mastering"
APP_VERSION = "2.0.0"
ENTRY_POINT = "main.py"
ICON_FILE   = "mastering_tool_icon.ico"

VENV_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv")

HIDDEN_IMPORTS = [
    "scipy.signal",
    "scipy.ndimage",
    "sounddevice",
    "soundfile",
    "pyloudnorm",
    "pydub",
    "PIL",
    "PIL.Image",
    "PIL.ImageDraw",
    "PIL.ImageQt",
    "numpy",
]

DATA_FILES = [
    "lang.json",
    "logo.png",
    ICON_FILE,
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def venv_python():
    if platform.system() == "Windows":
        return os.path.join(VENV_DIR, "Scripts", "python.exe")
    return os.path.join(VENV_DIR, "bin", "python3")


def venv_pip():
    if platform.system() == "Windows":
        return os.path.join(VENV_DIR, "Scripts", "pip.exe")
    return os.path.join(VENV_DIR, "bin", "pip3")


def data_sep():
    """PyInstaller --add-data separator differs by OS."""
    return ";" if platform.system() == "Windows" else ":"


def run(cmd, **kwargs):
    print(f"    $ {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        print(f"\n[ERROR] Build step failed (exit {result.returncode})")
        sys.exit(result.returncode)


def clean(path):
    if os.path.isdir(path):
        shutil.rmtree(path)
    elif os.path.isfile(path):
        os.remove(path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    root   = os.path.dirname(os.path.abspath(__file__))
    system = platform.system()
    arch   = platform.machine()
    os.chdir(root)

    print("=" * 60)
    print(f"  SS-Mastering — Build Script v{APP_VERSION}")
    print(f"  Platform : {system} ({arch})")
    print(f"  Python   : {sys.version.split()[0]}")
    print("=" * 60)

    # --- Require venv ---
    if not os.path.exists(VENV_DIR):
        print("\n[ERROR] Virtual environment not found.")
        print("        Run  python run.py  first to set it up.")
        sys.exit(1)

    python = venv_python()
    pip    = venv_pip()

    # --- Install PyInstaller into venv ---
    print("\n[1/4] Installing PyInstaller...")
    run([pip, "install", "--quiet", "--upgrade", "pyinstaller"])

    # --- Clean previous build artifacts ---
    print("\n[2/4] Cleaning previous build artifacts...")
    for path in ["build", "dist", f"{APP_NAME}.spec"]:
        clean(path)
    print("      Done.")

    # --- Assemble PyInstaller command ---
    print("\n[3/4] Running PyInstaller...")

    s = data_sep()
    cmd = [
        python, "-m", "PyInstaller",
        "--name",        APP_NAME,
        "--onedir",
        "--windowed",
        "--clean",
        "--noconfirm",
        "--icon",        ICON_FILE,
        "--distpath",    "dist",
        "--workpath",    "build",
        "--specpath",    ".",
    ]

    # Add data files (skip missing files gracefully)
    for f in DATA_FILES:
        if os.path.exists(f):
            cmd += ["--add-data", f"{f}{s}."]
        else:
            print(f"      [!] Skipping missing asset: {f}")

    # Hidden imports
    for imp in HIDDEN_IMPORTS:
        cmd += ["--hidden-import", imp]

    # macOS: also collect all PySide6 plugins to avoid missing module errors
    if system == "Darwin":
        cmd += ["--collect-all", "PySide6"]

    cmd.append(ENTRY_POINT)

    run(cmd)

    # --- Report ---
    print("\n[4/4] Build complete!")
    print("-" * 60)

    if system == "Darwin":
        out = os.path.join("dist", f"{APP_NAME}.app")
        print(f"  App bundle : {out}")
        print(f"  Run        : open \"{out}\"")
        print(f"  Distribute : zip the .app folder and share it")
    elif system == "Windows":
        out = os.path.join("dist", APP_NAME, f"{APP_NAME}.exe")
        print(f"  Executable : {out}")
        print(f"  Distribute : zip dist\\{APP_NAME}\\ and share it")
    else:  # Linux
        out = os.path.join("dist", APP_NAME, APP_NAME)
        print(f"  Executable : {out}")
        print(f"  Run        : ./{out}")
        print(f"  Distribute : tar -czf {APP_NAME}.tar.gz dist/{APP_NAME}/")

    print()
    print("  NOTE: Always distribute the entire dist/ folder,")
    print("        not just the executable file alone.")
    print("-" * 60)


if __name__ == "__main__":
    main()
