"""Tests for RealizationDataEditor component."""

from unittest.mock import MagicMock

import panel as pn
import pytest
from pywellsfm.model import Well
from pywellsfm.model.enums import SubsidenceType

from pywellsfmui.components.realization_data_editor import (
    RealizationDataEditor,
)
from pywellsfmui.state.actions import Actions
from pywellsfmui.state.app_state import AppState
from pywellsfmui.state.io_manager import IOManager
from pywellsfmui.state.message_store import MessageStore


@pytest.fixture
def state() -> AppState:
    """Return a fresh AppState."""
    return AppState()


@pytest.fixture
def actions(state: AppState) -> Actions:
    """Return Actions wired to the given state."""
    return Actions(
        state=state,
        io_manager=IOManager(),
        message_store=MessageStore(),
    )


@pytest.fixture
def editor(
    state: AppState,
    actions: Actions,
) -> RealizationDataEditor:
    """Return a RealizationDataEditor instance."""
    return RealizationDataEditor(state=state, actions=actions)


def _make_mock_well(name: str) -> MagicMock:
    """Create a mock Well with the given name."""
    well = MagicMock(spec=Well)
    well.name = name
    return well


def test_renders_panel(
    editor: RealizationDataEditor,
) -> None:
    """Test panel() returns a pn.Column."""
    panel = editor.panel()
    assert isinstance(panel, pn.Column)


def test_empty_state_shows_no_wells(
    editor: RealizationDataEditor,
) -> None:
    """Test status shows 'No wells' when empty."""
    html = editor._build_status_html()
    assert "No wells" in html


def test_wells_from_state_appear_in_list(
    editor: RealizationDataEditor,
    state: AppState,
) -> None:
    """Test wells populate _well_settings."""
    w = _make_mock_well("Well-1")
    state.wells = [w]
    assert len(editor._well_settings) == 1
    assert "Well-1" in editor._well_settings


def test_default_well_settings(
    editor: RealizationDataEditor,
    state: AppState,
) -> None:
    """Test freshly-added well gets defaults."""
    w = _make_mock_well("Well-1")
    state.wells = [w]
    ws = editor._well_settings["Well-1"]
    assert ws.bathymetry == 0.0
    assert ws.subsidence_type == SubsidenceType.CUMULATIVE
    assert ws.subsidence_curve is None
    assert ws.initial_env_name is None


def test_removing_well_clears_settings(
    editor: RealizationDataEditor,
    state: AppState,
) -> None:
    """Test removing well clears its settings."""
    w = _make_mock_well("Well-1")
    state.wells = [w]
    assert "Well-1" in editor._well_settings
    state.wells = []
    assert "Well-1" not in editor._well_settings


def test_status_with_wells(
    editor: RealizationDataEditor,
    state: AppState,
) -> None:
    """Test status shows well count."""
    state.wells = [_make_mock_well("A")]
    html = editor._build_status_html()
    assert "1 well" in html
