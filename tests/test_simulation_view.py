import asyncio
from collections.abc import Callable
from unittest.mock import MagicMock

import panel as pn
import pytest

pn.extension(
    "plotly",
    "tabulator",
    sizing_mode="stretch_width",
)

from pywellsfmui.state.actions import Actions  # noqa: E402
from pywellsfmui.state.app_state import AppState  # noqa: E402
from pywellsfmui.state.io_manager import IOManager  # noqa: E402
from pywellsfmui.state.message_store import MessageStore  # noqa: E402
from pywellsfmui.views.simulation import SimulationView  # noqa: E402


@pytest.fixture
def state() -> AppState:
    """Return a fresh AppState."""
    return AppState()


@pytest.fixture
def actions(state: AppState) -> Actions:
    """Return Actions wired to the given state."""
    io = IOManager()
    ms = MessageStore()
    return Actions(
        state=state,
        io_manager=io,
        message_store=ms,
    )


@pytest.fixture
def nav_spy() -> MagicMock:
    """Return a mock navigation callback."""
    return MagicMock(spec=Callable)


@pytest.fixture
def view(
    state: AppState,
    actions: Actions,
    nav_spy: MagicMock,
) -> SimulationView:
    """Return a SimulationView instance."""
    return SimulationView(
        state=state,
        actions=actions,
        on_navigate=nav_spy,
    )


def test_panel_contains_run_button(
    view: SimulationView,
) -> None:
    """Run Simulation button appears in the layout."""
    col = view.panel()
    widgets = [
        obj
        for obj in col
        if isinstance(obj, pn.widgets.Button) and obj.label == "Run Simulation"
    ]
    assert len(widgets) == 1


def test_run_button_initially_disabled(
    view: SimulationView,
) -> None:
    """Button is disabled and spinner hidden."""
    assert view._run_btn.disabled is True
    assert view._spinner.visible is False


def test_run_button_enabled_when_inputs_ready(
    view: SimulationView,
    state: AppState,
) -> None:
    """Button enables when required inputs are set."""
    state.accumulation_model = MagicMock()
    state.realization_data_list = [MagicMock()]
    assert view._run_btn.disabled is False


def test_run_button_disabled_missing_accumulation(
    view: SimulationView,
    state: AppState,
) -> None:
    """Button stays disabled without accum model."""
    state.realization_data_list = [MagicMock()]
    assert view._run_btn.disabled is True


def test_run_button_disabled_missing_realization(
    view: SimulationView,
    state: AppState,
) -> None:
    """Button stays disabled without realization."""
    state.accumulation_model = MagicMock()
    assert view._run_btn.disabled is True


def _make_state_ready(state: AppState) -> None:
    """Set all required inputs on state."""
    state.accumulation_model = MagicMock()
    state.realization_data_list = [MagicMock()]


def test_run_success_navigates(
    view: SimulationView,
    actions: Actions,
    nav_spy: MagicMock,
    state: AppState,
) -> None:
    """Successful run navigates to visualization."""
    _make_state_ready(state)
    actions.run_simulation = MagicMock()
    asyncio.get_event_loop().run_until_complete(view._on_run_clicked(None))
    actions.run_simulation.assert_called_once()
    nav_spy.assert_called_once_with("visualization")
    assert view._run_btn.disabled is False
    assert view._spinner.visible is False


def test_run_failure_stays_on_tab(
    view: SimulationView,
    actions: Actions,
    nav_spy: MagicMock,
    state: AppState,
) -> None:
    """Failed run re-enables button, no navigate."""
    _make_state_ready(state)
    actions.run_simulation = MagicMock(
        side_effect=ValueError("missing data"),
    )
    asyncio.get_event_loop().run_until_complete(view._on_run_clicked(None))
    nav_spy.assert_not_called()
    assert view._run_btn.disabled is False
    assert view._spinner.visible is False
