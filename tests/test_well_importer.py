import panel as pn
import pytest
from unittest.mock import MagicMock

from pywellsfmui.components.well_importer import (
    WellImporter,
)
from pywellsfmui.state.actions import Actions
from pywellsfmui.state.app_state import AppState
from pywellsfmui.state.io_manager import IOManager
from pywellsfmui.state.message_store import MessageStore


def _make_mock_well(name, discrete_logs=None):
    well = MagicMock()
    well.name = name
    well.getDiscreteLogNames.return_value = set(discrete_logs or [])
    return well


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
def importer(state, actions):
    return WellImporter(state=state, actions=actions)


def test_renders_empty_state(importer):
    panel = importer.panel()
    assert isinstance(panel, pn.Column)
    assert "No wells loaded" in importer._status.object


def test_renders_with_wells(importer, state):
    w1 = _make_mock_well("Well-1", ["lithology", "facies"])
    w2 = _make_mock_well("Well-2", ["litho"])
    state.wells = [w1, w2]
    state.well_facies_log_names = {
        "Well-1": "lithology",
        "Well-2": "litho",
    }
    importer._refresh()
    rows = importer._well_list.objects
    # 1 header + 2 well rows
    assert len(rows) == 3
    assert "2 wells loaded" in importer._status.object


def test_renders_single_well_status(importer, state):
    w = _make_mock_well("Well-1", ["lithology"])
    state.wells = [w]
    state.well_facies_log_names = {"Well-1": "lithology"}
    importer._refresh()
    assert "1 well loaded" in importer._status.object


def test_remove_well_updates_list(importer, state, actions):
    w1 = _make_mock_well("Well-1", ["lithology"])
    w2 = _make_mock_well("Well-2", ["litho"])
    state.wells = [w1, w2]
    state.well_facies_log_names = {
        "Well-1": "lithology",
        "Well-2": "litho",
    }
    importer._refresh()
    # 1 header + 2 well rows
    assert len(importer._well_list.objects) == 3

    actions.remove_well("Well-1")
    importer._refresh()
    # 1 header + 1 well row
    assert len(importer._well_list.objects) == 2


def test_per_well_log_options(importer, state):
    w1 = _make_mock_well("Well-1", ["lithology"])
    w2 = _make_mock_well("Well-2", ["facies", "litho", "zones"])
    state.wells = [w1, w2]
    state.well_facies_log_names = {
        "Well-1": "lithology",
        "Well-2": "facies",
    }
    importer._refresh()
    rows = importer._well_list.objects
    # Row 0 is header; well rows start at index 1
    select_w1 = rows[1][1]
    assert isinstance(select_w1, pn.widgets.Select)
    assert select_w1.options == ["lithology"]
    select_w2 = rows[2][1]
    assert isinstance(select_w2, pn.widgets.Select)
    assert select_w2.options == ["facies", "litho", "zones"]


def test_checkbox_shows_computed_status(importer, state):
    w = _make_mock_well("Well-1", ["lithology"])
    state.wells = [w]
    state.well_facies_log_names = {"Well-1": "lithology"}
    state.well_accommodation_computed = {"Well-1": True}
    importer._refresh()
    rows = importer._well_list.objects
    # Row 0 is header; well row at index 1
    # Checkbox is wrapped in a Column for centering
    cb_container = rows[1][2]
    checkbox = cb_container[0]
    assert isinstance(checkbox, pn.widgets.Checkbox)
    assert checkbox.value is True
    assert checkbox.disabled is True


def test_checkbox_default_false(importer, state):
    w = _make_mock_well("Well-1", ["lithology"])
    state.wells = [w]
    state.well_facies_log_names = {"Well-1": "lithology"}
    importer._refresh()
    rows = importer._well_list.objects
    # Row 0 is header; well row at index 1
    cb_container = rows[1][2]
    checkbox = cb_container[0]
    assert isinstance(checkbox, pn.widgets.Checkbox)
    assert checkbox.value is False
    assert checkbox.disabled is True
