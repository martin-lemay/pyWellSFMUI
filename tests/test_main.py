import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pywellsfmui import __main__ as entry


def test_main_serves_installed_app(monkeypatch: pytest.MonkeyPatch) -> None:
    """Python -m pywellsfmui serves the packaged app.py with extra args."""
    run = MagicMock(return_value=MagicMock(returncode=0))
    monkeypatch.setattr(entry.subprocess, "run", run)
    monkeypatch.setattr(sys, "argv", ["pywellsfmui", "--port", "5007"])

    assert entry.main() == 0

    cmd = run.call_args.args[0]
    assert cmd[:4] == [sys.executable, "-m", "panel", "serve"]
    app_py = Path(cmd[4])
    assert app_py.name == "app.py" and app_py.exists()
    assert cmd[-2:] == ["--port", "5007"]
