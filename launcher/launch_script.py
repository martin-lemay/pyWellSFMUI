"""Launch script for pyWellSFM desktop distribution.

Checks the venv, starts Panel server, and opens the
browser. Compiled to pyWellSFM.exe via PyInstaller.
"""

import configparser
import socket
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

if getattr(sys, "frozen", False):
    _INSTALL_DIR = Path(sys.executable).resolve().parent
else:
    _INSTALL_DIR = Path(__file__).resolve().parent
_VENV_DIR = _INSTALL_DIR / ".venv"
_CONFIG_FILE = _INSTALL_DIR / "config.ini"
_DEFAULT_PORT = 5006


def _pause_and_exit(code: int = 1) -> NoReturn:
    """Pause for user to read output, then exit."""
    input("\nPress Enter to close...")
    sys.exit(code)


def _check_venv(venv_dir: Path) -> None:
    """Verify the venv exists and has python.exe."""
    python = venv_dir / "Scripts" / "python.exe"
    if not python.exists():
        print("Installation not found. Please run install.exe first.")
        _pause_and_exit(1)


def _read_config(
    config_file: Path,
) -> dict[str, int]:
    """Read config.ini and return settings dict."""
    config = configparser.ConfigParser()
    config.read(str(config_file))
    port = config.getint("launcher", "port", fallback=_DEFAULT_PORT)
    return {"port": port}


def _is_port_in_use(port: int) -> bool:
    """Check if a TCP port is already bound."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex(("127.0.0.1", port)) == 0


def main() -> None:
    """Launch the pyWellSFM Panel server."""
    print("=" * 50)
    print("  pyWellSFM")
    print("=" * 50)
    print()

    # Check venv
    _check_venv(_VENV_DIR)

    # Read config
    config = _read_config(_CONFIG_FILE)
    port = config["port"]

    # Check port
    if _is_port_in_use(port):
        print(
            f"Port {port} is already in use. "
            "Close the other instance or change the "
            "port in config.ini."
        )
        _pause_and_exit(1)

    # Resolve app.py from installed package
    app_py = _VENV_DIR / "Lib" / "site-packages" / "pywellsfmui" / "app.py"
    if not app_py.exists():
        print("Installation appears corrupted. Please re-run install.exe.")
        _pause_and_exit(1)

    # Start Panel server
    panel_exe = str(_VENV_DIR / "Scripts" / "panel.exe")
    print(
        f"Server running at http://localhost:{port} "
        "- close this window to stop."
    )
    print()
    try:
        subprocess.run(
            [
                panel_exe,
                "serve",
                str(app_py),
                f"--port={port}",
                "--show",
            ]
        )
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    main()
