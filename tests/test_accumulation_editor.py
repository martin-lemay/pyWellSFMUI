import numpy as np
import panel as pn
import pytest

from pywellsfm.model import (
    AccumulationCurve,
    AccumulationModel,
    AccumulationModelElementGaussian,
    AccumulationModelElementOptimum,
)

from pywellsfmui.components.accumulation_editor import (
    _COL_X,
    _COL_Y,
    AccumulationEditor,
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
    return AccumulationEditor(state=state, actions=actions)


def test_editor_renders_empty_state(editor):
    panel = editor.panel()
    assert isinstance(panel, pn.Column)


def test_editor_renders_with_model(editor, state):
    elem = AccumulationModelElementGaussian(
        elementName="Carbonate",
        accumulationRate=100.0,
        std_dev_factor=0.2,
    )
    state.accumulation_model = AccumulationModel(
        name="Test",
        elementAccumulationModels={"Carbonate": elem},
    )
    editor._refresh()
    df = editor._element_table.value
    # 1 element + 1 placeholder row
    assert len(df) == 2
    assert df.at[0, "Name"] == "Carbonate"


def test_editor_shows_gaussian_inputs(editor, state, actions):
    actions.add_accumulation_element("Carbonate")
    editor._refresh()
    editor._element_table.selection = [0]
    editor._on_element_selected(None)
    assert editor._type_select.value == "Gaussian"
    assert editor._rate_input.visible
    assert editor._stddev_input.visible
    assert not editor._curves_top_panel.visible


def test_editor_shows_optimum_inputs(editor, state, actions):
    actions.add_accumulation_element("Carbonate")
    actions.set_accumulation_element_type("Carbonate", "EnvironmentOptimum")
    editor._refresh()
    editor._element_table.selection = [0]
    editor._on_element_selected(None)
    assert editor._type_select.value == "EnvironmentOptimum"
    assert editor._rate_input.visible
    assert not editor._stddev_input.visible
    assert editor._curves_top_panel.visible


def test_editor_shows_curve_data(editor, state):
    elem = AccumulationModelElementOptimum(
        elementName="Carbonate",
        accumulationRate=100.0,
    )
    curve = AccumulationCurve(
        envFactorName="Temperature",
        abscissa=np.array([10.0, 20.0, 30.0]),
        ordinate=np.array([0.2, 1.0, 0.5]),
    )
    elem.addAccumulationCurve(curve)
    state.accumulation_model = AccumulationModel(
        name="Test",
        elementAccumulationModels={"Carbonate": elem},
    )
    editor._refresh()
    editor._element_table.selection = [0]
    editor._on_element_selected(None)
    editor._curve_table.selection = [0]
    editor._on_curve_selected(None)
    df = editor._point_table.value
    # 3 data points + 1 placeholder
    assert len(df) == 4
    assert df.at[0, _COL_X] == 10.0
    assert df.at[0, _COL_Y] == 0.2


def test_editor_syncs_on_state_change(editor, state, actions):
    actions.add_accumulation_element("Carbonate")
    editor._refresh()
    df = editor._element_table.value
    assert len(df) == 2  # 1 + placeholder
    actions.add_accumulation_element("Siliciclastic")
    editor._refresh()
    df = editor._element_table.value
    assert len(df) == 3  # 2 + placeholder
