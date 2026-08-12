from unittest.mock import MagicMock

from pywellsfmui.state.app_state import AppState
from pywellsfmui.theme import Colors
from pywellsfmui.views.status_bar import StatusBar


def test_status_bar_defaults():
    state = AppState()
    bar = StatusBar(state=state)
    html = bar._render_badges()
    assert "Facies: --" in html
    assert "Wells: 0" in html
    assert "Simulation: --" in html


def test_status_bar_facies_loaded():
    state = AppState()
    state.facies_model = MagicMock()
    bar = StatusBar(state=state)
    html = bar._render_badges()
    assert "Facies: loaded" in html
    assert Colors.SUCCESS in html


def test_status_bar_wells_loaded():
    state = AppState()
    state.wells = [MagicMock(), MagicMock()]
    bar = StatusBar(state=state)
    html = bar._render_badges()
    assert "Wells: 2" in html
    assert Colors.SUCCESS in html


def test_status_bar_simulation_done():
    state = AppState()
    state.simulation_outputs = MagicMock()
    bar = StatusBar(state=state)
    html = bar._render_badges()
    assert "Simulation: done" in html
    assert Colors.SUCCESS in html


def test_status_bar_reactivity():
    state = AppState()
    bar = StatusBar(state=state)
    html_before = bar._render_badges()
    assert "Facies: --" in html_before
    state.facies_model = MagicMock()
    html_after = bar._render_badges()
    assert "Facies: loaded" in html_after
