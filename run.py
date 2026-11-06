#!/usr/bin/env python3
"""
run.py — setup and launch SS-Mastering

Automatically creates a virtual environment, installs all dependencies,
and starts the app. No manual setup required beyond having Python 3.9+.

Usage:
    python run.py
"""

import sys
import os
import subprocess
import platform

VENV_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv")
REQUIREMENTS = [
    "pydub",
    "numpy",
    "pyloudnorm",
    "soundfile",
    "sounddevice",
    "PySide6",
    "scipy",
    "Pillow",
]


def venv_python():
    if platform.system() == "Windows":
        return os.path.join(VENV_DIR, "Scripts", "python.exe")
    return os.path.join(VENV_DIR, "bin", "python3")


def venv_pip():
    if platform.system() == "Windows":
        return os.path.join(VENV_DIR, "Scripts", "pip.exe")
    return os.path.join(VENV_DIR, "bin", "pip3")


def run(cmd, **kwargs):
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        sys.exit(result.returncode)


def check_ffmpeg():
    try:
        return subprocess.run(
            ["ffmpeg", "-version"], capture_output=True
        ).returncode == 0
    except FileNotFoundError:
        return False


def main():
    root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(root)

    # --- Python version check ---
    if sys.version_info < (3, 9):
        print(f"[ERROR] Python 3.9+ is required. You have {sys.version.split()[0]}")
        print("        Download it from https://www.python.org/downloads/")
        sys.exit(1)

    # --- Create venv if needed ---
    if not os.path.exists(VENV_DIR):
        print("[*] Creating virtual environment...")
        run([sys.executable, "-m", "venv", VENV_DIR])
        print("[+] Virtual environment created.\n")
    else:
        print("[+] Virtual environment found.")

    python = venv_python()
    pip    = venv_pip()

    # --- Install / upgrade dependencies ---
    print("[*] Checking dependencies (first run may take a moment)...")
    run([pip, "install", "--quiet", "--upgrade", "pip"])
    run([pip, "install", "--quiet", "--upgrade"] + REQUIREMENTS)
    print("[+] All dependencies are ready.\n")

    # --- Check ffmpeg (optional, needed for MP3 export only) ---
    if not check_ffmpeg():
        print("[!] ffmpeg not found — MP3 export will be unavailable.")
        print("    To enable it:")
        if platform.system() == "Darwin":
            print("      brew install ffmpeg")
        elif platform.system() == "Linux":
            print("      sudo apt install ffmpeg   # Debian/Ubuntu")
            print("      sudo dnf install ffmpeg   # Fedora")
        else:
            print("      https://ffmpeg.org/download.html")
        print()

    # --- Launch app ---
    print("[*] Starting SS-Mastering...\n")
    subprocess.run([python, os.path.join(root, "main.py")])


if __name__ == "__main__":
    main()
