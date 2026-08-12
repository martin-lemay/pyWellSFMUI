import panel as pn
import pytest

from pywellsfm.model import (
    Facies,
    FaciesCriteria,
    FaciesCriteriaType,
    FaciesModel,
)

from pywellsfmui.components.facies_editor import (
    FaciesEditor,
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
    return FaciesEditor(state=state, actions=actions)


def test_editor_renders_empty_state(editor):
    panel = editor.panel()
    assert isinstance(panel, pn.Column)


def test_editor_renders_with_model(editor, state):
    crit = FaciesCriteria(
        name="GrainSize",
        minRange=0.1,
        maxRange=2.0,
        type=FaciesCriteriaType.SEDIMENTOLOGICAL,
    )
    f = Facies(
        name="Sand",
        criteria={crit},
        criteriaType=FaciesCriteriaType.SEDIMENTOLOGICAL,
    )
    state.facies_model = FaciesModel(faciesSet={f})
    editor._refresh()
    df = editor._facies_table.value
    # 1 facies + 1 placeholder row
    assert len(df) == 2
    assert df.at[0, "Name"] == "Sand"


def test_editor_shows_criteria_on_selection(editor, state):
    crit = FaciesCriteria(
        name="GrainSize",
        minRange=0.1,
        maxRange=2.0,
        type=FaciesCriteriaType.SEDIMENTOLOGICAL,
    )
    f = Facies(
        name="Sand",
        criteria={crit},
        criteriaType=FaciesCriteriaType.SEDIMENTOLOGICAL,
    )
    state.facies_model = FaciesModel(faciesSet={f})
    editor._refresh()
    editor._facies_table.selection = [0]
    editor._on_facies_selected(None)
    df = editor._crit_table.value
    # 1 criterion + 1 placeholder row
    assert len(df) == 2
    assert df.at[0, "Name"] == "GrainSize"


def test_editor_syncs_on_state_change(editor, state, actions):
    actions.add_facies("Sand", FaciesCriteriaType.SEDIMENTOLOGICAL)
    editor._refresh()
    df = editor._facies_table.value
    # 1 facies + 1 placeholder
    assert len(df) == 2
    actions.add_facies("Mud", FaciesCriteriaType.SEDIMENTOLOGICAL)
    editor._refresh()
    df = editor._facies_table.value
    # 2 facies + 1 placeholder
    assert len(df) == 3
