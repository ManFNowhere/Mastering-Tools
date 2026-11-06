#!/usr/bin/env python3
"""
build.py — build SS-Mastering as a standalone desktop app

PyInstaller cannot cross-compile; each OS must build its own binary.
Run locally (requires .venv from run.py), or via GitHub Actions which
builds all three platforms in parallel using native cloud runners.

  Local:   python build.py
  CI:      triggered automatically by GitHub Actions on tag push

Outputs:
  macOS   → dist/SS-Mastering.app
  Windows → dist/SS-Mastering/SS-Mastering.exe
  Linux   → dist/SS-Mastering/SS-Mastering
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

# GitHub Actions sets CI=true; local builds use the .venv instead
CI_MODE  = os.environ.get("CI", "").lower() in ("true", "1")
VENV_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv")

HIDDEN_IMPORTS = [
    "scipy.signal",
    "scipy.ndimage",
    "scipy.stats",
    "scipy.stats._qmc",
    "sounddevice",
    "soundfile",
    "pyloudnorm",
    "pydub",
    "PIL",
    "PIL.Image",
    "PIL.ImageDraw",
    "PIL.ImageQt",
    "numpy",
    # Python 3.9: PyInstaller does not auto-collect importlib subpackages
    "importlib.resources",
    "importlib.metadata",
    "importlib.metadata._meta",
    "importlib.metadata.selectors",
]

DATA_FILES = [
    "lang.json",
    "logo.png",
    ICON_FILE,
    "assets",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_python():
    if CI_MODE:
        return sys.executable
    if platform.system() == "Windows":
        return os.path.join(VENV_DIR, "Scripts", "python.exe")
    return os.path.join(VENV_DIR, "bin", "python3")


def get_pip():
    if CI_MODE:
        return [sys.executable, "-m", "pip"]
    if platform.system() == "Windows":
        return [os.path.join(VENV_DIR, "Scripts", "pip.exe")]
    return [os.path.join(VENV_DIR, "bin", "pip3")]


def data_sep():
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
    print(f"  Mode     : {'CI (GitHub Actions)' if CI_MODE else 'Local (.venv)'}")
    print("=" * 60)

    if not CI_MODE and not os.path.exists(VENV_DIR):
        print("\n[ERROR] Virtual environment not found.")
        print("        Run  python run.py  first to set it up.")
        sys.exit(1)

    python = get_python()
    pip    = get_pip()

    # --- Install PyInstaller ---
    print("\n[1/4] Installing PyInstaller...")
    run([*pip, "install", "--quiet", "--upgrade", "pyinstaller"])

    # --- Clean ---
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
        "--distpath",    "dist",
        "--workpath",    "build",
        "--specpath",    ".",
    ]

    if os.path.exists(ICON_FILE):
        cmd += ["--icon", ICON_FILE]

    for f in DATA_FILES:
        if os.path.exists(f):
            dest = "." if os.path.isfile(f) else f
            cmd += ["--add-data", f"{f}{s}{dest}"]
        else:
            print(f"      [!] Skipping missing asset: {f}")

    for imp in HIDDEN_IMPORTS:
        cmd += ["--hidden-import", imp]

    # collect full importlib subpackage tree (needed on Python 3.9 + PyInstaller)
    cmd += ["--collect-submodules", "importlib"]

    if system == "Darwin":
        # collect-all PySide6 bundles Qt tools (Assistant, Designer) with
        # deeply nested symlinks that break macOS codesigning — exclude them
        for mod in [
            "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
            "PySide6.QtWebEngineQuick", "PySide6.Qt3DAnimation",
            "PySide6.Qt3DCore", "PySide6.Qt3DExtras", "PySide6.Qt3DInput",
            "PySide6.Qt3DLogic", "PySide6.Qt3DRender",
            "PySide6.QtDesigner", "PySide6.QtHelp",
        ]:
            cmd += ["--exclude-module", mod]

    cmd.append(ENTRY_POINT)
    run(cmd)

    # --- Report ---
    print("\n[4/4] Build complete!")
    print("-" * 60)

    if system == "Darwin":
        out = os.path.join("dist", f"{APP_NAME}.app")
        print(f"  App bundle : {out}")
        print(f"  Distribute : zip -r SS-Mastering-macos.zip dist/{APP_NAME}.app")
    elif system == "Windows":
        out = os.path.join("dist", APP_NAME, f"{APP_NAME}.exe")
        print(f"  Executable : {out}")
        print(f"  Distribute : zip dist\\{APP_NAME}\\ → SS-Mastering-windows.zip")
    else:
        out = os.path.join("dist", APP_NAME, APP_NAME)
        print(f"  Executable : {out}")
        print(f"  Distribute : tar -czf SS-Mastering-linux.tar.gz dist/{APP_NAME}/")

    print()
    print("  Distribute the entire dist/ folder, not just the executable.")
    print("-" * 60)


if __name__ == "__main__":
    main()
