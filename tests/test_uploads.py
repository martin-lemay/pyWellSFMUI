import json
from pathlib import Path

import pytest

from pywellsfmui.state.actions import Actions
from pywellsfmui.state.app_state import AppState
from pywellsfmui.state.io_manager import IOManager
from pywellsfmui.state.message_store import MessageStore
from pywellsfmui.state.uploads import load_uploaded_json

_EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


@pytest.fixture
def actions() -> Actions:
    """Return Actions wired to a fresh state."""
    return Actions(
        state=AppState(),
        io_manager=IOManager(),
        message_store=MessageStore(),
    )


def test_load_uploaded_json_accepts_inline_data() -> None:
    """Self-contained JSON is parsed as usual."""
    data = (_EXAMPLES / "simulation_simple.json").read_bytes()
    assert load_uploaded_json(data) == json.loads(data)


@pytest.mark.parametrize(
    "url", ["/etc/passwd", "C:/Windows/win.ini", "../../secret.csv", "a.csv"]
)
def test_load_uploaded_json_rejects_file_references(url: str) -> None:
    """Any nested url reference is rejected, absolute or relative."""
    payload = {"scenario": {"eustaticCurve": {"url": url}}}
    with pytest.raises(ValueError, match="self-contained") as exc:
        load_uploaded_json(json.dumps(payload).encode())
    assert url in str(exc.value)


def test_load_simulation_file_rejects_file_reference(
    actions: Actions,
) -> None:
    """A simulation upload pointing to server files is not loaded."""
    payload = json.loads(
        (_EXAMPLES / "simulation_simple.json").read_text(encoding="utf-8")
    )
    payload["scenario"]["eustaticCurve"] = {"url": "/etc/passwd"}
    with pytest.raises(ValueError, match="self-contained"):
        actions.load_simulation_file(json.dumps(payload).encode())
    assert actions._state.accumulation_model is None


def test_load_well_json_rejects_file_reference(actions: Actions) -> None:
    """A well upload pointing to server files is not loaded."""
    payload = {
        "format": "pyWellSFM.WellData",
        "version": "1.0",
        "well": {"url": "/etc/passwd"},
    }
    with pytest.raises(ValueError, match="self-contained"):
        actions.load_well_from_bytes(json.dumps(payload).encode(), "w.json")
    assert actions._state.wells == []
