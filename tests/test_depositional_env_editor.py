import numpy as np
import panel as pn
import pytest

from pywellsfm.model import Curve
from pywellsfm.model.EnvironmentConditionModel import (
    EnvironmentConditionModelCurve,
)

from pywellsfmui.components.depositional_env_editor import (
    DepositionalEnvEditor,
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
    return DepositionalEnvEditor(state=state, actions=actions)


def test_editor_creates(editor):
    panel = editor.panel()
    assert isinstance(panel, pn.Column)


def test_editor_global_mode_default(editor, state):
    assert state.use_de_simulator is False
    panel = editor.panel()
    assert panel is not None


def test_editor_switch_to_multi_env(editor, state, actions):
    actions.set_use_de_simulator(True)
    actions.create_de_model("carbonate_open_ramp")
    assert state.depositional_env_model is not None


def test_add_curve_condition_global(state, actions):
    """Add a Curve-type condition in global mode."""
    curve = Curve(
        "waterDepth",
        "oxygen",
        np.array([0.0, 100.0]),
        np.array([0.8, 0.2]),
        "linear",
    )
    actions.add_env_condition(
        "global",
        "oxygen",
        "Curve",
        curve=curve,
    )
    ecm = state.global_env_conditions
    assert ecm is not None
    model = ecm.envConditionModels["oxygen"]
    assert isinstance(model, EnvironmentConditionModelCurve)
    assert model.relatedConditionName == "waterDepth"


def test_editor_curve_detail_panel(editor, state, actions):
    """Curve type shows related-condition input and curve editor."""
    editor.panel()
    actions.add_env_condition(
        "global",
        "oxygen",
        "Uniform",
        minValue=0.0,
        maxValue=1.0,
    )
    # Select the condition row
    editor._cond_table.selection = [0]
    editor._refresh_cond_detail()
    # Switch to Curve type
    editor._updating = False
    editor._cond_type_select.value = "Curve"
    # The related-condition input should exist in the detail
    assert editor._cond_related_input is not None
    assert editor._cond_curve_editor is not None
