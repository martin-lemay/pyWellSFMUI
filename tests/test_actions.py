import pytest
from unittest.mock import MagicMock, patch
from pywellsfmui.state.app_state import AppState
from pywellsfmui.state.io_manager import IOManager
from pywellsfmui.state.actions import Actions
from pywellsfmui.state.message_store import MessageStore, MessageLevel


@pytest.fixture
def state():
    return AppState()


@pytest.fixture
def io_manager():
    return IOManager()


@pytest.fixture
def message_store():
    return MessageStore()


@pytest.fixture
def actions(state, io_manager, message_store):
    return Actions(state=state, io_manager=io_manager, message_store=message_store)


def test_set_facies_model(actions, state):
    mock_model = MagicMock()
    actions.set_facies_model(mock_model)
    assert state.facies_model is mock_model


def test_load_facies_model(actions, state):
    mock_model = MagicMock()
    with patch.object(actions._io, "load_facies_model", return_value=mock_model) as m:
        actions.load_facies_model("/fake/path.json")
        m.assert_called_once_with("/fake/path.json")
    assert state.facies_model is mock_model


def test_save_facies_model(actions, state):
    mock_model = MagicMock()
    state.facies_model = mock_model
    with patch.object(actions._io, "save_facies_model") as m:
        actions.save_facies_model("/fake/output.json")
        m.assert_called_once_with(mock_model, "/fake/output.json")


def test_save_facies_model_raises_when_none(actions):
    with pytest.raises(ValueError, match="No facies model"):
        actions.save_facies_model("/fake/output.json")


def test_load_well(actions, state):
    mock_well = MagicMock()
    mock_well.name = "Well-1"
    with patch.object(actions._io, "load_well", return_value=mock_well):
        actions.load_well("/fake/well.json")
    assert len(state.wells) == 1
    assert state.wells[0].name == "Well-1"


def test_remove_well(actions, state):
    mock_well = MagicMock()
    mock_well.name = "Well-1"
    state.wells = [mock_well]
    actions.remove_well("Well-1")
    assert state.wells == []


def test_remove_well_not_found(actions):
    with pytest.raises(ValueError, match="not found"):
        actions.remove_well("Nonexistent")


def test_set_accumulation_model(actions, state):
    mock_model = MagicMock()
    actions.set_accumulation_model(mock_model)
    assert state.accumulation_model is mock_model


def test_set_eustatic_curve(actions, state):
    mock_curve = MagicMock()
    actions.set_eustatic_curve(mock_curve)
    assert state.eustatic_curve is mock_curve


def test_set_depositional_env_model(actions, state):
    mock_model = MagicMock()
    actions.set_depositional_env_model(mock_model)
    assert state.depositional_env_model is mock_model


def test_clear_simulation_outputs(actions, state):
    state.simulation_outputs = MagicMock()
    actions.clear_simulation_outputs()
    assert state.simulation_outputs is None


def test_load_facies_model_logs_info(actions, state, message_store):
    mock_model = MagicMock()
    with patch.object(actions._io, "load_facies_model", return_value=mock_model):
        actions.load_facies_model("/fake/path.json")
    assert len(message_store.messages) == 1
    assert message_store.messages[0].level == MessageLevel.INFO
    assert "/fake/path.json" in message_store.messages[0].text


def test_save_facies_model_none_logs_warning(actions, message_store):
    with pytest.raises(ValueError):
        actions.save_facies_model("/fake/output.json")
    assert len(message_store.messages) == 1
    assert message_store.messages[0].level == MessageLevel.WARNING


def test_load_facies_model_io_error_logs_error(actions, message_store):
    with patch.object(
        actions._io, "load_facies_model", side_effect=OSError("disk error")
    ):
        with pytest.raises(OSError):
            actions.load_facies_model("/bad/path.json")
    assert len(message_store.messages) == 1
    assert message_store.messages[0].level == MessageLevel.ERROR
    assert "disk error" in message_store.messages[0].text
