import panel as pn
import pytest
from unittest.mock import MagicMock

from pywellsfmui.state.actions import Actions
from pywellsfmui.state.app_state import AppState
from pywellsfmui.state.io_manager import IOManager
from pywellsfmui.state.message_store import MessageStore
from pywellsfmui.views.well_analysis import WellAnalysisView


@pytest.fixture
def state():
    return AppState()


@pytest.fixture
def actions(state):
    return Actions(
        state=state,
        io_manager=IOManager(),
        message_store=MessageStore(),
    )


@pytest.fixture
def view(state, actions):
    return WellAnalysisView(state=state, actions=actions)


def test_compute_button_exists(view):
    _ = view.panel()
    assert isinstance(view._compute_btn, pn.widgets.Button)
    assert view._compute_btn.label == "Compute Accommodation"


def test_compute_button_disabled_no_wells(view, state):
    state.facies_model = MagicMock()
    view._update_step3()
    assert view._compute_btn.disabled is True


def test_compute_button_disabled_no_facies(view, state):
    well = MagicMock()
    well.name = "W1"
    state.wells = [well]
    view._update_step3()
    assert view._compute_btn.disabled is True


def test_compute_button_enabled(view, state):
    well = MagicMock()
    well.name = "W1"
    state.wells = [well]
    state.facies_model = MagicMock()
    view._update_step3()
    assert view._compute_btn.disabled is False


def _make_mock_calculator():
    """Create a mock calculator for testing."""
    calc = MagicMock()
    calc._well = MagicMock()
    calc._well.name = "W1"
    calc._well.depth = 100.0
    calc.accommodationCurve = MagicMock()
    calc.waterDepthCurve = MagicMock()
    return calc


def test_results_placeholder_no_results(view):
    view.panel()
    assert view._results_placeholder.object == ("*No accommodation results*")


def test_well_selector_exists(view):
    _ = view.panel()
    assert isinstance(view._well_select, pn.widgets.Select)


def test_well_selector_updates_on_results(view, state):
    _ = view.panel()
    calc = _make_mock_calculator()
    state.accommodation_results = {"W1": calc}
    view._update_results()
    assert "W1" in view._well_select.options


def test_export_figure_btn_exists(view):
    _ = view.panel()
    assert isinstance(view._export_fig_btn, pn.widgets.FileDownload)


def test_comparison_section_exists(view):
    _ = view.panel()
    assert isinstance(
        view._comparison_track_select,
        pn.widgets.Select,
    )
    assert isinstance(
        view._comparison_plot_pane,
        pn.pane.Plotly,
    )


def test_comparison_export_btn_exists(view):
    _ = view.panel()
    assert isinstance(
        view._comparison_export_btn,
        pn.widgets.FileDownload,
    )


def test_comparison_hidden_no_results(view):
    _ = view.panel()
    assert view._comparison_plot_pane.visible is False
    assert view._comparison_track_select.visible is False
