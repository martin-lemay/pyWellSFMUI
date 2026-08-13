"""Locate a Python 3.13+ interpreter on Windows.

Search order: py launcher, PATH, common Anaconda locations,
conda base environment.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path

_MIN_MINOR = 13


def _check_python_version(python_path: str) -> bool:
    """Return True if python_path is Python >= 3.13."""
    try:
        result = subprocess.run(
            [python_path, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    if result.returncode != 0:
        return False
    match = re.search(r"Python (\d+)\.(\d+)", result.stdout)
    if not match:
        return False
    major, minor = int(match.group(1)), int(match.group(2))
    return major == 3 and minor >= _MIN_MINOR


def _find_py_launcher_python() -> str | None:
    """Try the official Windows Python Launcher.

    Runs ``py -3.13 --version`` directly because ``py`` alone invokes
    the default Python, not the 3.13 one.
    """
    if shutil.which("py") is None:
        return None
    try:
        result = subprocess.run(
            ["py", "-3.13", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    match = re.search(r"Python (\d+)\.(\d+)", result.stdout)
    if not match:
        return None
    major, minor = int(match.group(1)), int(match.group(2))
    if major == 3 and minor >= _MIN_MINOR:
        return "py -3.13"
    return None


def _find_path_python() -> str | None:
    """Try python / python3 on PATH."""
    for name in ("python", "python3"):
        path = shutil.which(name)
        if path and _check_python_version(path):
            return path
    return None


def _find_anaconda_python() -> str | None:
    """Check common Anaconda / Miniconda install locations."""
    env_vars = ["USERPROFILE", "LOCALAPPDATA", "PROGRAMDATA"]
    subdirs = ["anaconda3", "miniconda3"]
    for var in env_vars:
        base = os.environ.get(var, "")
        if not base:
            continue
        for subdir in subdirs:
            candidate = Path(base) / subdir / "python.exe"
            if candidate.exists() and _check_python_version(str(candidate)):
                return str(candidate)
    return None


def _find_conda_base_python() -> str | None:
    """Use conda info --base to find the base environment."""
    if shutil.which("conda") is None:
        return None
    try:
        result = subprocess.run(
            ["conda", "info", "--base"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    base_path = result.stdout.strip()
    candidate = str(Path(base_path) / "python.exe")
    if _check_python_version(candidate):
        return candidate
    return None


def find_python() -> str | None:
    """Find a Python 3.13+ interpreter.

    Returns the path/command string, or None if not found.
    """
    for finder in (
        _find_py_launcher_python,
        _find_path_python,
        _find_anaconda_python,
        _find_conda_base_python,
    ):
        result = finder()
        if result is not None:
            return result
    return None
