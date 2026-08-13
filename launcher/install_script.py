"""Install script for pyWellSFM desktop distribution.

Creates a venv, installs bundled wheels, and verifies the
installation. Compiled to install.exe via PyInstaller.
"""

import glob
import shutil
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

from launcher.find_python import find_python

if getattr(sys, "frozen", False):
    _INSTALL_DIR = Path(sys.executable).resolve().parent
else:
    _INSTALL_DIR = Path(__file__).resolve().parent
_VENV_DIR = _INSTALL_DIR / ".venv"
_WHEELS_DIR = _INSTALL_DIR / "wheels"


def _pause_and_exit(code: int = 1) -> NoReturn:
    """Pause for user to read output, then exit."""
    input("\nPress Enter to close...")
    sys.exit(code)


def _create_venv(python_cmd: str, venv_dir: Path) -> None:
    """Create a fresh venv, removing any existing one."""
    if venv_dir.exists():
        print(f"Removing existing installation at {venv_dir}...")
        shutil.rmtree(venv_dir)
    print(f"Creating virtual environment at {venv_dir}...")
    # Handle "py -3.13" (space-separated command)
    cmd = [*python_cmd.split(), "-m", "venv", str(venv_dir)]
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("ERROR: Failed to create virtual environment.")
        _pause_and_exit(1)


def _install_wheels(venv_dir: Path, wheels_dir: Path) -> None:
    """Install all .whl files from wheels_dir into the venv."""
    pip = str(venv_dir / "Scripts" / "pip.exe")
    wheel_files = glob.glob(str(wheels_dir / "*.whl"))
    if not wheel_files:
        print(f"ERROR: No .whl files found in {wheels_dir}")
        _pause_and_exit(1)
    print("Installing packages...")
    cmd = [pip, "install", "--find-links", str(wheels_dir)] + wheel_files
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(
            "\nERROR: Installation failed. An internet "
            "connection is required to download dependencies."
        )
        _pause_and_exit(1)


def _verify_install(venv_dir: Path) -> None:
    """Verify that pywellsfm and pywellsfmui can be imported."""
    python = str(venv_dir / "Scripts" / "python.exe")
    result = subprocess.run(
        [
            python,
            "-c",
            "import pywellsfm; import pywellsfmui",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("ERROR: Installation verification failed.")
        print(result.stderr)
        _pause_and_exit(1)


def main() -> None:
    """Run the installer."""
    print("=" * 50)
    print("  pyWellSFM Installer")
    print("=" * 50)
    print()

    # Find Python
    print("Searching for Python 3.13+...")
    python_cmd = find_python()
    if python_cmd is None:
        print(
            "ERROR: Could not find Python 3.13+.\n"
            "Checked: py launcher, PATH, Anaconda "
            "default locations.\n"
            "Please ensure Python 3.13 or later is "
            "installed."
        )
        _pause_and_exit(1)
    print(f"Found Python: {python_cmd}")
    print()

    # Create venv
    _create_venv(python_cmd, _VENV_DIR)
    print()

    # Install wheels
    _install_wheels(_VENV_DIR, _WHEELS_DIR)
    print()

    # Verify
    print("Verifying installation...")
    _verify_install(_VENV_DIR)
    print()

    print("=" * 50)
    print(
        "  Installation complete. Run pyWellSFM.exe to start the application."
    )
    print("=" * 50)
    _pause_and_exit(0)


if __name__ == "__main__":
    main()
