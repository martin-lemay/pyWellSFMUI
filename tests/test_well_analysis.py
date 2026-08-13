from unittest.mock import MagicMock

import panel as pn
import pytest

from pywellsfmui.state.actions import Actions
from pywellsfmui.state.app_state import AppState
from pywellsfmui.state.io_manager import IOManager
from pywellsfmui.state.message_store import MessageStore
from pywellsfmui.views.well_analysis import (
    WellAnalysisView,
)


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
def view(
    state: AppState,
    actions: Actions,
) -> WellAnalysisView:
    """Return a WellAnalysisView instance."""
    return WellAnalysisView(state=state, actions=actions)


def test_compute_button_exists(
    view: WellAnalysisView,
) -> None:
    """Test compute button exists in panel."""
    _ = view.panel()
    assert isinstance(view._compute_btn, pn.widgets.Button)
    assert view._compute_btn.label == "Compute Accommodation"


def test_compute_button_disabled_no_wells(
    view: WellAnalysisView,
    state: AppState,
) -> None:
    """Test button disabled without wells."""
    state.facies_model = MagicMock()
    view._update_step3()
    assert view._compute_btn.disabled is True


def test_compute_button_disabled_no_facies(
    view: WellAnalysisView,
    state: AppState,
) -> None:
    """Test button disabled without facies model."""
    well = MagicMock()
    well.name = "W1"
    state.wells = [well]
    view._update_step3()
    assert view._compute_btn.disabled is True


def test_compute_button_enabled(
    view: WellAnalysisView,
    state: AppState,
) -> None:
    """Test button enabled with wells and facies."""
    well = MagicMock()
    well.name = "W1"
    state.wells = [well]
    state.facies_model = MagicMock()
    view._update_step3()
    assert view._compute_btn.disabled is False


def _make_mock_calculator() -> MagicMock:
    """Create a mock calculator for testing."""
    calc = MagicMock()
    calc._well = MagicMock()
    calc._well.name = "W1"
    calc._well.depth = 100.0
    calc.accommodationCurve = MagicMock()
    calc.waterDepthCurve = MagicMock()
    return calc


def test_results_placeholder_no_results(
    view: WellAnalysisView,
) -> None:
    """Test placeholder text when no results."""
    view.panel()
    assert view._results_placeholder.object == ("*No accommodation results*")


def test_well_selector_exists(
    view: WellAnalysisView,
) -> None:
    """Test well selector widget exists."""
    _ = view.panel()
    assert isinstance(view._well_select, pn.widgets.Select)


def test_well_selector_updates_on_results(
    view: WellAnalysisView,
    state: AppState,
) -> None:
    """Test well selector updates with results."""
    _ = view.panel()
    calc = _make_mock_calculator()
    state.accommodation_results = {"W1": calc}
    view._update_results()
    assert "W1" in view._well_select.options


def test_export_figure_btn_exists(
    view: WellAnalysisView,
) -> None:
    """Test export figure button exists."""
    _ = view.panel()
    assert isinstance(
        view._export_fig_btn,
        pn.widgets.FileDownload,
    )


def test_comparison_section_exists(
    view: WellAnalysisView,
) -> None:
    """Test comparison section widgets exist."""
    _ = view.panel()
    assert isinstance(
        view._comparison_track_select,
        pn.widgets.Select,
    )
    assert isinstance(
        view._comparison_plot_pane,
        pn.pane.Plotly,
    )


def test_comparison_export_btn_exists(
    view: WellAnalysisView,
) -> None:
    """Test comparison export button exists."""
    _ = view.panel()
    assert isinstance(
        view._comparison_export_btn,
        pn.widgets.FileDownload,
    )


def test_comparison_hidden_no_results(
    view: WellAnalysisView,
) -> None:
    """Test comparison hidden when no results."""
    _ = view.panel()
    assert view._comparison_plot_pane.visible is False
    assert view._comparison_track_select.visible is False
