"""Tests for SimulatorParamsEditor component."""

import panel as pn
import pytest

from pywellsfm.model import FSSimulatorParameters

from pywellsfmui.components.simulator_params_editor import (
    SimulatorParamsEditor,
)
from pywellsfmui.state.actions import Actions
from pywellsfmui.state.app_state import AppState
from pywellsfmui.state.io_manager import IOManager
from pywellsfmui.state.message_store import MessageStore


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
def editor(state, actions):
    return SimulatorParamsEditor(state=state, actions=actions)


def test_panel_returns_card(editor):
    result = editor.panel()
    assert isinstance(result, pn.Card)


def test_defaults_pushed_on_init(state, editor):
    """Editor pushes default FSSimulatorParameters to state on init."""
    p = state.simulator_params
    assert p is not None
    defaults = FSSimulatorParameters()
    assert p.max_waterDepth_change_per_step == defaults.max_waterDepth_change_per_step
    assert p.dt_min == defaults.dt_min
    assert p.dt_max == defaults.dt_max
    assert p.safety == defaults.safety
    assert p.max_steps == defaults.max_steps


def test_widget_change_updates_state(state, editor):
    """Changing a widget value pushes updated params to state."""
    editor._dt_max.value = 0.5
    assert state.simulator_params.dt_max == 0.5


def test_state_change_updates_widgets(state, actions, editor):
    """Programmatic state change syncs back to widgets."""
    new_params = FSSimulatorParameters(
        max_waterDepth_change_per_step=1.0,
        dt_min=0.01,
        dt_max=0.2,
        safety=0.8,
        max_steps=5000,
    )
    actions.set_simulator_params(new_params)
    assert editor._max_wd_change.value == 1.0
    assert editor._dt_min.value == 0.01
    assert editor._dt_max.value == 0.2
    assert editor._safety.value == 0.8
    assert editor._max_steps.value == 5000
