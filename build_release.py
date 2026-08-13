"""Build a distributable zip for pyWellSFM desktop.

Usage: python build_release.py

Requires: build, pyinstaller
    pip install build pyinstaller
"""

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_PYWELLSFM_DIR = _ROOT.parent / "pyWellSFM"
_LAUNCHER_DIR = _ROOT / "launcher"
_TEMPLATES_DIR = _LAUNCHER_DIR / "templates"
_DIST_DIR = _ROOT / "dist"


def _get_version() -> str:
    """Read version from pywellsfmui.__init__."""
    init_file = _ROOT / "src" / "pywellsfmui" / "__init__.py"
    for line in init_file.read_text().splitlines():
        if line.startswith("__version__"):
            return line.split('"')[1]
    msg = "Could not find __version__ in __init__.py"
    raise RuntimeError(msg)


def _build_wheels() -> Path:
    """Build wheels for pyWellSFM and pyWellSFMUI.

    Returns the directory containing both .whl files.
    """
    wheels_dir = _DIST_DIR / "wheels"
    if wheels_dir.exists():
        shutil.rmtree(wheels_dir)
    wheels_dir.mkdir(parents=True)

    for project_dir in [_PYWELLSFM_DIR, _ROOT]:
        print(f"Building wheel for {project_dir.name}...")
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "build",
                "--wheel",
                "--outdir",
                str(wheels_dir),
                str(project_dir),
            ]
        )
        if result.returncode != 0:
            msg = f"Failed to build wheel for {project_dir.name}"
            raise RuntimeError(msg)

    return wheels_dir


def _build_exes() -> Path:
    """Build install.exe and pyWellSFM.exe via PyInstaller.

    Returns the directory containing both .exe files.
    """
    exes_dir = _DIST_DIR / "exes"
    if exes_dir.exists():
        shutil.rmtree(exes_dir)
    exes_dir.mkdir(parents=True)

    scripts = {
        "install": _LAUNCHER_DIR / "install_script.py",
        "pyWellSFM": _LAUNCHER_DIR / "launch_script.py",
    }

    for name, script in scripts.items():
        print(f"Building {name}.exe...")
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "PyInstaller",
                "--onefile",
                "--name",
                name,
                "--distpath",
                str(exes_dir),
                "--workpath",
                str(_DIST_DIR / "build_temp"),
                "--specpath",
                str(_DIST_DIR / "build_temp"),
                str(script),
            ]
        )
        if result.returncode != 0:
            msg = f"Failed to build {name}.exe"
            raise RuntimeError(msg)

    return exes_dir


def _assemble_zip(
    version: str,
    exes_dir: Path,
    wheels_dir: Path,
    templates_dir: Path,
    output_dir: Path,
) -> Path:
    """Assemble all artifacts into the final zip."""
    zip_name = f"pyWellSFM-v{version}"
    zip_path = output_dir / f"{zip_name}.zip"
    output_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Exes
        for exe in exes_dir.glob("*.exe"):
            zf.write(exe, f"{zip_name}/{exe.name}")

        # Wheels
        for whl in wheels_dir.glob("*.whl"):
            zf.write(whl, f"{zip_name}/wheels/{whl.name}")

        # Templates (config.ini, README.txt)
        for template in templates_dir.iterdir():
            if template.is_file():
                zf.write(
                    template,
                    f"{zip_name}/{template.name}",
                )

    return zip_path


def main() -> None:
    """Build the full release zip."""
    print("=" * 50)
    print("  pyWellSFM Release Builder")
    print("=" * 50)
    print()

    version = _get_version()
    print(f"Version: {version}")
    print()

    wheels_dir = _build_wheels()
    print()

    exes_dir = _build_exes()
    print()

    print("Assembling zip...")
    zip_path = _assemble_zip(
        version=version,
        exes_dir=exes_dir,
        wheels_dir=wheels_dir,
        templates_dir=_TEMPLATES_DIR,
        output_dir=_DIST_DIR,
    )
    print()

    print("=" * 50)
    print(f"  Release built: {zip_path}")
    print(f"  Size: {zip_path.stat().st_size / 1024:.0f} KB")
    print("=" * 50)


if __name__ == "__main__":
    main()
