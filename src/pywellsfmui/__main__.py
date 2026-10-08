"""Start the app with ``python -m pywellsfmui [panel serve options]``."""

import subprocess
import sys
from pathlib import Path


def main() -> int:
    """Serve the packaged app with Panel and open it in the browser."""
    app_py = Path(__file__).with_name("app.py")
    cmd = [sys.executable, "-m", "panel", "serve", str(app_py), "--show"]
    return subprocess.run([*cmd, *sys.argv[1:]]).returncode


if __name__ == "__main__":
    sys.exit(main())
