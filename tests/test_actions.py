import json
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from pywellsfmui.state.actions import Actions
from pywellsfmui.state.app_state import AppState
from pywellsfmui.state.io_manager import IOManager
from pywellsfmui.state.message_store import MessageLevel, MessageStore

from pywellsfm.model import (
    AccumulationCurve,
    AccumulationModel,
    AccumulationModelElementGaussian,
    AccumulationModelElementOptimum,
    Facies,
    FaciesCriteria,
    FaciesCriteriaType,
    FaciesModel,
)
from pywellsfm.model.DepositionalEnvironment import (
    DepositionalEnvironment,
    DepositionalEnvironmentModel,
)
from pywellsfm.model.EnvironmentConditionModel import (
    EnvironmentConditionModelConstant,
    EnvironmentConditionModelGaussian,
    EnvironmentConditionModelTriangular,
    EnvironmentConditionModelUniform,
    EnvironmentConditionsModel,
)
from pywellsfm.simulator import (
    DepositionalEnvironmentSimulator,
)


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
    with (
        patch.object(
            actions._io, "load_facies_model", side_effect=OSError("disk error")
        ),
        pytest.raises(OSError),
    ):
        actions.load_facies_model("/bad/path.json")
    assert len(message_store.messages) == 1
    assert message_store.messages[0].level == MessageLevel.ERROR
    assert "disk error" in message_store.messages[0].text


# --- create_empty_facies_model ---


def test_create_empty_facies_model(actions, state):
    mock_model = MagicMock()
    state.facies_model = mock_model
    actions.create_empty_facies_model()
    assert state.facies_model is None


def test_create_empty_facies_model_when_already_none(actions, state):
    actions.create_empty_facies_model()
    assert state.facies_model is None


# --- add_facies ---


def test_add_facies_creates_model_when_none(actions, state):
    actions.add_facies("Sand", FaciesCriteriaType.SEDIMENTOLOGICAL)
    assert state.facies_model is not None
    assert isinstance(state.facies_model, FaciesModel)
    facies = state.facies_model.getFaciesByName("Sand")
    assert facies is not None
    assert facies.getCriteriaCount() == 0


def test_add_facies_to_existing_model(actions, state):
    crit = FaciesCriteria(name="GrainSize", minRange=0.1, maxRange=2.0)
    f = Facies(
        name="Sand",
        criteria={crit},
        criteriaType=FaciesCriteriaType.SEDIMENTOLOGICAL,
    )
    state.facies_model = FaciesModel(faciesSet={f})
    actions.add_facies("Mud", FaciesCriteriaType.SEDIMENTOLOGICAL)
    assert len(state.facies_model.faciesSet) == 2
    assert state.facies_model.getFaciesByName("Mud") is not None


def test_add_facies_duplicate_name_raises(actions, state):
    actions.add_facies("Sand", FaciesCriteriaType.SEDIMENTOLOGICAL)
    with pytest.raises(ValueError, match="already exists"):
        actions.add_facies("Sand", FaciesCriteriaType.ENVIRONMENTAL)


# --- remove_facies ---


def test_remove_facies(actions, state):
    crit = FaciesCriteria(name="GrainSize")
    f1 = Facies(
        name="Sand",
        criteria={crit},
        criteriaType=FaciesCriteriaType.SEDIMENTOLOGICAL,
    )
    f2 = Facies(
        name="Mud",
        criteria={FaciesCriteria(name="GrainSize")},
        criteriaType=FaciesCriteriaType.SEDIMENTOLOGICAL,
    )
    state.facies_model = FaciesModel(faciesSet={f1, f2})
    actions.remove_facies("Sand")
    assert len(state.facies_model.faciesSet) == 1
    assert state.facies_model.getFaciesByName("Sand") is None


def test_remove_facies_not_found_raises(actions, state):
    crit = FaciesCriteria(name="GrainSize")
    f = Facies(
        name="Sand",
        criteria={crit},
        criteriaType=FaciesCriteriaType.SEDIMENTOLOGICAL,
    )
    state.facies_model = FaciesModel(faciesSet={f})
    with pytest.raises(ValueError, match="not found"):
        actions.remove_facies("Nonexistent")


def test_remove_facies_last_one_raises(actions, state):
    crit = FaciesCriteria(name="GrainSize")
    f = Facies(
        name="Sand",
        criteria={crit},
        criteriaType=FaciesCriteriaType.SEDIMENTOLOGICAL,
    )
    state.facies_model = FaciesModel(faciesSet={f})
    with pytest.raises(ValueError, match="last facies"):
        actions.remove_facies("Sand")


def test_remove_facies_no_model_raises(actions, state):
    with pytest.raises(ValueError, match="No facies model"):
        actions.remove_facies("Sand")


# --- add_criteria / remove_criteria / update_criteria ---


def _make_model_with_sand(state):
    """Helper: set state.facies_model with one Sand facies."""
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


def test_add_criteria(actions, state):
    _make_model_with_sand(state)
    actions.add_criteria("Sand", "Sorting", 0.5, 1.0)
    facies = state.facies_model.getFaciesByName("Sand")
    assert facies.getCriteriaCount() == 2
    added = facies.getCriteria("Sorting")
    assert added is not None
    assert added.minRange == 0.5
    assert added.maxRange == 1.0


def test_add_criteria_duplicate_raises(actions, state):
    _make_model_with_sand(state)
    with pytest.raises(ValueError, match="already exists"):
        actions.add_criteria("Sand", "GrainSize", 0.0, 1.0)


def test_add_criteria_facies_not_found_raises(actions, state):
    _make_model_with_sand(state)
    with pytest.raises(ValueError, match="not found"):
        actions.add_criteria("Mud", "Sorting", 0.0, 1.0)


def test_add_criteria_no_model_raises(actions, state):
    with pytest.raises(ValueError, match="No facies model"):
        actions.add_criteria("Sand", "Sorting", 0.0, 1.0)


def test_remove_criteria(actions, state):
    _make_model_with_sand(state)
    actions.add_criteria("Sand", "Sorting", 0.5, 1.0)
    actions.remove_criteria("Sand", "Sorting")
    facies = state.facies_model.getFaciesByName("Sand")
    assert facies.getCriteriaCount() == 1
    assert facies.getCriteria("Sorting") is None


def test_remove_criteria_last_one_succeeds(actions, state):
    _make_model_with_sand(state)
    actions.remove_criteria("Sand", "GrainSize")
    facies = state.facies_model.getFaciesByName("Sand")
    assert facies.getCriteriaCount() == 0


def test_remove_criteria_not_found_raises(actions, state):
    _make_model_with_sand(state)
    with pytest.raises(ValueError, match="not found"):
        actions.remove_criteria("Sand", "Nonexistent")


def test_update_criteria(actions, state):
    _make_model_with_sand(state)
    actions.update_criteria("Sand", "GrainSize", 0.2, 3.0)
    facies = state.facies_model.getFaciesByName("Sand")
    crit = facies.getCriteria("GrainSize")
    assert crit.minRange == 0.2
    assert crit.maxRange == 3.0


def test_update_criteria_not_found_raises(actions, state):
    _make_model_with_sand(state)
    with pytest.raises(ValueError, match="not found"):
        actions.update_criteria("Sand", "Nonexistent", 0.0, 1.0)


# --- load_facies_model_from_bytes / export_facies_model_as_json ---


def test_load_facies_model_from_bytes(actions, state):
    data = json.dumps(
        {
            "format": "pyWellSFM.FaciesModelData",
            "version": "1.0",
            "faciesModel": [
                {
                    "name": "Sand",
                    "criteriaType": "sedimentological",
                    "criteria": [
                        {"name": "GrainSize", "minRange": 0.1, "maxRange": 2.0}
                    ],
                }
            ],
        }
    ).encode("utf-8")
    actions.load_facies_model_from_bytes(data)
    assert state.facies_model is not None
    assert state.facies_model.getFaciesByName("Sand") is not None


def test_load_facies_model_from_bytes_invalid_json(actions):
    with pytest.raises(Exception):
        actions.load_facies_model_from_bytes(b"not json")


def test_export_facies_model_as_json(actions, state):
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
    result = actions.export_facies_model_as_json()
    assert isinstance(result, dict)
    assert result["format"] == "pyWellSFM.FaciesModelData"
    assert len(result["faciesModel"]) == 1


def test_export_facies_model_as_json_no_model(actions):
    with pytest.raises(ValueError, match="No facies model"):
        actions.export_facies_model_as_json()


# --- load_well_from_bytes ---


def test_load_well_from_bytes_json(actions, state):
    data = json.dumps(
        {
            "format": "pyWellSFM.WellData",
            "version": "1.0",
            "well": {
                "name": "TestWell",
                "location": {"x": 0, "y": 0, "z": 0},
                "depth": 100,
                "striplogs": [
                    {
                        "name": "lithology",
                        "intervals": [
                            {
                                "top": 0,
                                "base": 100,
                                "lithology": "sandstone",
                            }
                        ],
                    }
                ],
            },
        }
    ).encode("utf-8")
    actions.load_well_from_bytes(data, filename="test.json")
    assert len(state.wells) == 1
    assert state.wells[0].name == "TestWell"
    assert state.well_facies_log_names["TestWell"] == "lithology"


def test_load_well_from_bytes_invalid_json(actions):
    with pytest.raises(Exception):
        actions.load_well_from_bytes(b"not json", filename="bad.json")


def test_load_well_from_bytes_default_first_log(actions, state):
    data = json.dumps(
        {
            "format": "pyWellSFM.WellData",
            "version": "1.0",
            "well": {
                "name": "MultiLog",
                "location": {"x": 0, "y": 0, "z": 0},
                "depth": 100,
                "striplogs": [
                    {
                        "name": "facies",
                        "intervals": [{"top": 0, "base": 50, "lithology": "sand"}],
                    },
                    {
                        "name": "lithology",
                        "intervals": [{"top": 0, "base": 100, "lithology": "shale"}],
                    },
                ],
            },
        }
    ).encode("utf-8")
    actions.load_well_from_bytes(data, filename="multi.json")
    # Sorted alphabetically: "facies" comes before "lithology"
    assert state.well_facies_log_names["MultiLog"] == "facies"


# --- set_well_facies_log ---


def test_set_well_facies_log(actions, state):
    data = json.dumps(
        {
            "format": "pyWellSFM.WellData",
            "version": "1.0",
            "well": {
                "name": "W1",
                "location": {"x": 0, "y": 0, "z": 0},
                "depth": 100,
                "striplogs": [
                    {
                        "name": "facies",
                        "intervals": [{"top": 0, "base": 50, "lithology": "sand"}],
                    },
                    {
                        "name": "lithology",
                        "intervals": [{"top": 0, "base": 100, "lithology": "shale"}],
                    },
                ],
            },
        }
    ).encode("utf-8")
    actions.load_well_from_bytes(data, filename="w1.json")
    actions.set_well_facies_log("W1", "lithology")
    assert state.well_facies_log_names["W1"] == "lithology"


def test_set_well_facies_log_not_found(actions, state):
    with pytest.raises(ValueError, match="not found"):
        actions.set_well_facies_log("Nonexistent", "lithology")


def test_set_well_facies_log_invalid_log(actions, state):
    data = json.dumps(
        {
            "format": "pyWellSFM.WellData",
            "version": "1.0",
            "well": {
                "name": "W1",
                "location": {"x": 0, "y": 0, "z": 0},
                "depth": 100,
                "striplogs": [
                    {
                        "name": "lithology",
                        "intervals": [{"top": 0, "base": 100, "lithology": "shale"}],
                    }
                ],
            },
        }
    ).encode("utf-8")
    actions.load_well_from_bytes(data, filename="w1.json")
    with pytest.raises(ValueError, match="not found"):
        actions.set_well_facies_log("W1", "nonexistent_log")


# --- remove_well cleans up log names ---


def test_remove_well_cleans_log_names(actions, state):
    data = json.dumps(
        {
            "format": "pyWellSFM.WellData",
            "version": "1.0",
            "well": {
                "name": "W1",
                "location": {"x": 0, "y": 0, "z": 0},
                "depth": 100,
                "striplogs": [
                    {
                        "name": "lithology",
                        "intervals": [{"top": 0, "base": 100, "lithology": "shale"}],
                    }
                ],
            },
        }
    ).encode("utf-8")
    actions.load_well_from_bytes(data, filename="w1.json")
    assert "W1" in state.well_facies_log_names
    actions.remove_well("W1")
    assert "W1" not in state.well_facies_log_names


# --- duplicate well detection ---


def test_load_duplicate_well_is_rejected(actions, state, message_store):
    data = json.dumps(
        {
            "format": "pyWellSFM.WellData",
            "version": "1.0",
            "well": {
                "name": "W1",
                "location": {"x": 10, "y": 20, "z": 0},
                "depth": 100,
                "striplogs": [
                    {
                        "name": "lithology",
                        "intervals": [{"top": 0, "base": 100, "lithology": "shale"}],
                    }
                ],
            },
        }
    ).encode("utf-8")
    actions.load_well_from_bytes(data, filename="w1.json")
    assert len(state.wells) == 1
    # Load same well again
    actions.load_well_from_bytes(data, filename="w1.json")
    assert len(state.wells) == 1
    warnings = [m for m in message_store.messages if m.level == MessageLevel.WARNING]
    assert any("already exists" in m.text for m in warnings)


# --- accommodation reset on facies changes ---


def _setup_well_with_accommodation(state):
    """Helper: set up a well with a fake accommodation result."""
    well = MagicMock()
    well.name = "W1"
    well.getDiscreteLogNames.return_value = {"lithology"}
    well.wellHeadCoords = [0.0, 0.0, 0.0]
    state.wells = [well]
    state.well_facies_log_names = {"W1": "lithology"}
    state.well_accommodation_computed = {"W1": True}
    state.accommodation_results = {"W1": MagicMock()}


def test_add_facies_resets_accommodation(actions, state, message_store):
    _setup_well_with_accommodation(state)
    actions.add_facies("NewFacies", FaciesCriteriaType.SEDIMENTOLOGICAL)
    assert state.well_accommodation_computed == {"W1": False}
    assert state.accommodation_results == {}
    warnings = [m for m in message_store.messages if m.level == MessageLevel.WARNING]
    assert any("accommodation results have been reset" in m.text for m in warnings)


def test_remove_facies_resets_accommodation(actions, state, message_store):
    _setup_well_with_accommodation(state)
    crit = FaciesCriteria(
        name="GrainSize",
        minRange=0.1,
        maxRange=2.0,
        type=FaciesCriteriaType.SEDIMENTOLOGICAL,
    )
    f1 = Facies(
        name="Sand",
        criteria={crit},
        criteriaType=FaciesCriteriaType.SEDIMENTOLOGICAL,
    )
    f2 = Facies(
        name="Mud",
        criteria={FaciesCriteria(name="GrainSize")},
        criteriaType=FaciesCriteriaType.SEDIMENTOLOGICAL,
    )
    state.facies_model = FaciesModel(faciesSet={f1, f2})
    actions.remove_facies("Sand")
    assert state.well_accommodation_computed == {"W1": False}
    assert state.accommodation_results == {}


def test_update_criteria_resets_accommodation(actions, state, message_store):
    _setup_well_with_accommodation(state)
    _make_model_with_sand(state)
    actions.update_criteria("Sand", "GrainSize", 0.2, 3.0)
    assert state.well_accommodation_computed == {"W1": False}
    assert state.accommodation_results == {}


def test_load_facies_model_resets_accommodation(actions, state, message_store):
    _setup_well_with_accommodation(state)
    mock_model = MagicMock()
    with patch.object(actions._io, "load_facies_model", return_value=mock_model):
        actions.load_facies_model("/fake/path.json")
    assert state.well_accommodation_computed == {"W1": False}
    assert state.accommodation_results == {}


def test_load_facies_model_from_bytes_resets_accommodation(
    actions, state, message_store
):
    _setup_well_with_accommodation(state)
    data = json.dumps(
        {
            "format": "pyWellSFM.FaciesModelData",
            "version": "1.0",
            "faciesModel": [
                {
                    "name": "Sand",
                    "criteriaType": "sedimentological",
                    "criteria": [
                        {
                            "name": "GrainSize",
                            "minRange": 0.1,
                            "maxRange": 2.0,
                        }
                    ],
                }
            ],
        }
    ).encode("utf-8")
    actions.load_facies_model_from_bytes(data)
    assert state.well_accommodation_computed == {"W1": False}
    assert state.accommodation_results == {}


# --- set_well_facies_log clears computed flag ---


def test_set_well_facies_log_clears_computed_flag(actions, state):
    data = json.dumps(
        {
            "format": "pyWellSFM.WellData",
            "version": "1.0",
            "well": {
                "name": "W1",
                "location": {"x": 0, "y": 0, "z": 0},
                "depth": 100,
                "striplogs": [
                    {
                        "name": "facies",
                        "intervals": [
                            {
                                "top": 0,
                                "base": 50,
                                "lithology": "sand",
                            }
                        ],
                    },
                    {
                        "name": "lithology",
                        "intervals": [
                            {
                                "top": 0,
                                "base": 100,
                                "lithology": "shale",
                            }
                        ],
                    },
                ],
            },
        }
    ).encode("utf-8")
    actions.load_well_from_bytes(data, filename="w1.json")
    state.well_accommodation_computed = {"W1": True}
    actions.set_well_facies_log("W1", "lithology")
    assert state.well_accommodation_computed["W1"] is False


# --- remove_well cleans computed flag ---


def test_remove_well_cleans_computed_flag(actions, state):
    data = json.dumps(
        {
            "format": "pyWellSFM.WellData",
            "version": "1.0",
            "well": {
                "name": "W1",
                "location": {"x": 0, "y": 0, "z": 0},
                "depth": 100,
                "striplogs": [
                    {
                        "name": "lithology",
                        "intervals": [
                            {
                                "top": 0,
                                "base": 100,
                                "lithology": "shale",
                            }
                        ],
                    }
                ],
            },
        }
    ).encode("utf-8")
    actions.load_well_from_bytes(data, filename="w1.json")
    state.well_accommodation_computed = {"W1": True}
    actions.remove_well("W1")
    assert "W1" not in state.well_accommodation_computed


# --- compute_all_accommodation ---


def test_compute_all_accommodation_no_wells(actions, state, message_store):
    state.facies_model = MagicMock()
    with pytest.raises(ValueError, match="No wells"):
        actions.compute_all_accommodation()


def test_compute_all_accommodation_no_facies_model(actions, state, message_store):
    well = MagicMock()
    well.name = "W1"
    state.wells = [well]
    with pytest.raises(ValueError, match="No facies model"):
        actions.compute_all_accommodation()


def test_compute_all_accommodation(actions, state):
    well = MagicMock()
    well.name = "W1"
    well.markers = []
    state.wells = [well]
    state.well_facies_log_names = {"W1": "lithology"}
    state.facies_model = MagicMock()
    state.facies_model.faciesSet = set()

    with patch.object(
        actions,
        "compute_accommodation",
    ) as mock_compute:
        actions.compute_all_accommodation()
        mock_compute.assert_called_once_with(
            well_name="W1",
            facies_log_name="lithology",
        )
    assert state.well_accommodation_computed.get("W1") is True


# --- Accumulation Model: model-level ---


def test_create_empty_accumulation_model(actions, state):
    actions.create_empty_accumulation_model()
    assert state.accumulation_model is not None
    assert state.accumulation_model.name == "New Model"
    assert state.accumulation_model.elements == {}


def test_create_empty_accumulation_model_replaces_existing(actions, state):
    mock_model = MagicMock()
    state.accumulation_model = mock_model
    actions.create_empty_accumulation_model()
    assert state.accumulation_model is not mock_model
    assert state.accumulation_model.name == "New Model"


def test_load_accumulation_model_from_bytes(actions, state):
    data = json.dumps(
        {
            "format": "pyWellSFM.AccumulationModelData",
            "version": "1.0",
            "accumulationModel": {
                "name": "TestModel",
                "elements": {
                    "Carbonate": {
                        "accumulationRate": 50.0,
                        "model": {
                            "modelType": "Gaussian",
                            "stddevFactor": 0.1,
                        },
                    }
                },
            },
        }
    ).encode("utf-8")
    actions.load_accumulation_model_from_bytes(data)
    assert state.accumulation_model is not None
    assert state.accumulation_model.name == "TestModel"
    elem = state.accumulation_model.getElementModel("Carbonate")
    assert elem is not None


def test_load_accumulation_model_from_bytes_invalid(actions):
    with pytest.raises(Exception):
        actions.load_accumulation_model_from_bytes(b"bad")


def test_load_accumulation_model_from_bytes_logs_error(actions, message_store):
    with pytest.raises(Exception):
        actions.load_accumulation_model_from_bytes(b"bad")
    assert any(m.level == MessageLevel.ERROR for m in message_store.messages)


def test_export_accumulation_model_as_json(actions, state):
    from pywellsfm.model import (
        AccumulationModel,
        AccumulationModelElementGaussian,
    )

    elem = AccumulationModelElementGaussian(
        elementName="Carb",
        accumulationRate=100.0,
        std_dev_factor=0.2,
    )
    model = AccumulationModel(
        name="Test",
        elementAccumulationModels={"Carb": elem},
    )
    state.accumulation_model = model
    result = actions.export_accumulation_model_as_json()
    assert isinstance(result, dict)
    assert result["format"] == "pyWellSFM.AccumulationModelData"
    assert "Carb" in result["accumulationModel"]["elements"]


def test_export_accumulation_model_no_model(actions):
    with pytest.raises(ValueError, match="No accumulation model"):
        actions.export_accumulation_model_as_json()


# --- Element CRUD helpers ---


def _make_accum_model_with_element(state):
    """Helper: set state with one Gaussian element."""
    elem = AccumulationModelElementGaussian(
        elementName="Carbonate",
        accumulationRate=100.0,
        std_dev_factor=0.2,
    )
    state.accumulation_model = AccumulationModel(
        name="Test",
        elementAccumulationModels={"Carbonate": elem},
    )


# --- add_accumulation_element ---


def test_add_accumulation_element_creates_model(actions, state):
    actions.add_accumulation_element("Carbonate")
    assert state.accumulation_model is not None
    elem = state.accumulation_model.getElementModel("Carbonate")
    assert elem is not None
    assert isinstance(elem, AccumulationModelElementGaussian)
    assert elem.accumulationRate == 100.0


def test_add_accumulation_element_to_existing(actions, state):
    _make_accum_model_with_element(state)
    actions.add_accumulation_element("Siliciclastic")
    assert len(state.accumulation_model.elements) == 2
    elem = state.accumulation_model.getElementModel("Siliciclastic")
    assert elem is not None


def test_add_accumulation_element_duplicate_raises(actions, state):
    _make_accum_model_with_element(state)
    with pytest.raises(ValueError, match="already exists"):
        actions.add_accumulation_element("Carbonate")


# --- remove_accumulation_element ---


def test_remove_accumulation_element(actions, state):
    _make_accum_model_with_element(state)
    actions.add_accumulation_element("Siliciclastic")
    actions.remove_accumulation_element("Carbonate")
    assert len(state.accumulation_model.elements) == 1
    assert state.accumulation_model.getElementModel("Carbonate") is None


def test_remove_accumulation_element_no_model_raises(actions, state):
    with pytest.raises(ValueError, match="No accumulation model"):
        actions.remove_accumulation_element("Carbonate")


def test_remove_accumulation_element_not_found_raises(actions, state):
    _make_accum_model_with_element(state)
    with pytest.raises(ValueError, match="not found"):
        actions.remove_accumulation_element("Nonexistent")


# --- update_accumulation_element_rate ---


def test_update_accumulation_element_rate(actions, state):
    _make_accum_model_with_element(state)
    actions.update_accumulation_element_rate("Carbonate", 200.0)
    elem = state.accumulation_model.getElementModel("Carbonate")
    assert elem.accumulationRate == 200.0


def test_update_accumulation_element_rate_not_found(actions, state):
    _make_accum_model_with_element(state)
    with pytest.raises(ValueError, match="not found"):
        actions.update_accumulation_element_rate("Nonexistent", 200.0)


# --- update_accumulation_element_stddev ---


def test_update_accumulation_element_stddev(actions, state):
    _make_accum_model_with_element(state)
    actions.update_accumulation_element_stddev("Carbonate", 0.5)
    elem = state.accumulation_model.getElementModel("Carbonate")
    assert elem.std_dev_factor == 0.5


def test_update_accumulation_element_stddev_wrong_type(actions, state):
    _make_accum_model_with_element(state)
    actions.set_accumulation_element_type("Carbonate", "EnvironmentOptimum")
    with pytest.raises(ValueError, match="not Gaussian"):
        actions.update_accumulation_element_stddev("Carbonate", 0.5)


# --- set_accumulation_element_type ---


def test_set_element_type_to_optimum(actions, state):
    _make_accum_model_with_element(state)
    actions.set_accumulation_element_type("Carbonate", "EnvironmentOptimum")
    elem = state.accumulation_model.getElementModel("Carbonate")
    assert isinstance(elem, AccumulationModelElementOptimum)
    assert elem.accumulationRate == 100.0


def test_set_element_type_to_gaussian(actions, state):
    _make_accum_model_with_element(state)
    actions.set_accumulation_element_type("Carbonate", "EnvironmentOptimum")
    actions.set_accumulation_element_type("Carbonate", "Gaussian")
    elem = state.accumulation_model.getElementModel("Carbonate")
    assert isinstance(elem, AccumulationModelElementGaussian)
    assert elem.accumulationRate == 100.0


def test_set_element_type_not_found(actions, state):
    _make_accum_model_with_element(state)
    with pytest.raises(ValueError, match="not found"):
        actions.set_accumulation_element_type("Nonexistent", "Gaussian")


def test_set_element_type_invalid_type(actions, state):
    _make_accum_model_with_element(state)
    with pytest.raises(ValueError, match="Unknown"):
        actions.set_accumulation_element_type("Carbonate", "InvalidType")


# --- Curve CRUD helpers ---


def _make_accum_model_with_optimum(state):
    """Helper: model with one EnvironmentOptimum element."""
    elem = AccumulationModelElementOptimum(
        elementName="Carbonate",
        accumulationRate=100.0,
    )
    curve = AccumulationCurve(
        envFactorName="Temperature",
        abscissa=np.array([0.0, 1.0]),
        ordinate=np.array([1.0, 1.0]),
    )
    elem.addAccumulationCurve(curve)
    state.accumulation_model = AccumulationModel(
        name="Test",
        elementAccumulationModels={"Carbonate": elem},
    )


# --- add_accumulation_curve ---


def test_add_accumulation_curve(actions, state):
    _make_accum_model_with_optimum(state)
    actions.add_accumulation_curve("Carbonate", "Salinity")
    elem = state.accumulation_model.getElementModel("Carbonate")
    curve = elem.getAccumulationCurve("Salinity")
    assert curve is not None
    assert len(curve._abscissa) == 2


def test_add_accumulation_curve_not_optimum_raises(actions, state):
    _make_accum_model_with_element(state)
    with pytest.raises(ValueError, match="not EnvironmentOptimum"):
        actions.add_accumulation_curve("Carbonate", "Salinity")


def test_add_accumulation_curve_duplicate_raises(actions, state):
    _make_accum_model_with_optimum(state)
    with pytest.raises(ValueError, match="already exists"):
        actions.add_accumulation_curve("Carbonate", "Temperature")


# --- remove_accumulation_curve ---


def test_remove_accumulation_curve(actions, state):
    _make_accum_model_with_optimum(state)
    actions.remove_accumulation_curve("Carbonate", "Temperature")
    elem = state.accumulation_model.getElementModel("Carbonate")
    assert elem.getAccumulationCurve("Temperature") is None


def test_remove_accumulation_curve_not_found_raises(actions, state):
    _make_accum_model_with_optimum(state)
    with pytest.raises(ValueError, match="not found"):
        actions.remove_accumulation_curve("Carbonate", "Nonexistent")


# --- add_accumulation_curve_point ---


def test_add_accumulation_curve_point(actions, state):
    _make_accum_model_with_optimum(state)
    actions.add_accumulation_curve_point("Carbonate", "Temperature", 0.5, 0.8)
    elem = state.accumulation_model.getElementModel("Carbonate")
    curve = elem.getAccumulationCurve("Temperature")
    assert len(curve._abscissa) == 3


# --- remove_accumulation_curve_point ---


def test_remove_accumulation_curve_point(actions, state):
    _make_accum_model_with_optimum(state)
    actions.add_accumulation_curve_point("Carbonate", "Temperature", 0.5, 0.8)
    actions.remove_accumulation_curve_point("Carbonate", "Temperature", 1)
    elem = state.accumulation_model.getElementModel("Carbonate")
    curve = elem.getAccumulationCurve("Temperature")
    assert len(curve._abscissa) == 2


def test_remove_accumulation_curve_point_bad_index(actions, state):
    _make_accum_model_with_optimum(state)
    with pytest.raises(ValueError, match="out of range"):
        actions.remove_accumulation_curve_point("Carbonate", "Temperature", 99)


# --- update_accumulation_curve_point ---


def test_update_accumulation_curve_point(actions, state):
    _make_accum_model_with_optimum(state)
    actions.update_accumulation_curve_point("Carbonate", "Temperature", 0, 5.0, 0.3)
    elem = state.accumulation_model.getElementModel("Carbonate")
    curve = elem.getAccumulationCurve("Temperature")
    assert curve._abscissa[0] == 5.0
    assert curve._ordinate[0] == 0.3


def test_update_accumulation_curve_point_bad_index(actions, state):
    _make_accum_model_with_optimum(state)
    with pytest.raises(ValueError, match="out of range"):
        actions.update_accumulation_curve_point(
            "Carbonate", "Temperature", 99, 1.0, 0.5
        )


def test_set_realization_data_list(actions, state):
    mock_rd = MagicMock()
    actions.set_realization_data_list([mock_rd])
    assert len(state.realization_data_list) == 1
    assert state.realization_data_list[0] is mock_rd


def test_app_state_de_fields_defaults(state):
    assert state.use_de_simulator is False
    assert state.de_simulator_weights == {}
    assert state.de_simulator_params is None
    assert state.global_env_conditions is None


# --- IOManager: DE simulation roundtrip ---


def test_io_manager_env_conditions_roundtrip(io_manager):
    model = EnvironmentConditionsModel(
        [
            EnvironmentConditionModelUniform("energy", 0.0, 1.0),
        ]
    )
    obj = io_manager.export_env_conditions_to_json_obj(model)
    assert obj["format"] == "pyWellSFM.EnvironmentConditionsModelData"
    loaded = io_manager.load_env_conditions_from_json_obj(obj)
    assert "energy" in loaded.environmentConditionNames


def test_io_manager_de_simulation_roundtrip(io_manager):
    env = DepositionalEnvironment(
        name="TestEnv",
        waterDepthModel=EnvironmentConditionModelUniform("waterDepth", 0.0, 100.0),
    )
    de_model = DepositionalEnvironmentModel(name="Test", environments=[env])
    simulator = DepositionalEnvironmentSimulator(
        depositionalEnvironmentModel=de_model,
    )
    obj = io_manager.export_de_simulation_to_json_obj(simulator)
    assert obj["format"] == "pyWellSFM.DESimulationSchema"
    loaded = io_manager.load_de_simulation_from_json_obj(obj)
    assert loaded.depositionalEnvironmentModel.name == "Test"


# --- Actions: DE mode toggle ---


def test_set_use_de_simulator_to_true(actions, state):
    actions.set_use_de_simulator(True)
    assert state.use_de_simulator is True
    assert state.depositional_env_model is not None
    assert state.depositional_env_model.name == "New Model"
    assert len(state.depositional_env_model.environments) == 0
    assert state.global_env_conditions is None


def test_set_use_de_simulator_to_false(actions, state):
    actions.set_use_de_simulator(True)
    actions.create_de_model("empty")
    assert state.depositional_env_model is not None
    actions.set_use_de_simulator(False)
    assert state.use_de_simulator is False
    assert state.depositional_env_model is None
    assert state.de_simulator_weights == {}
    assert state.de_simulator_params is None


# --- Actions: create_de_model ---


def test_create_de_model_empty(actions, state):
    actions.set_use_de_simulator(True)
    actions.create_de_model("empty")
    model = state.depositional_env_model
    assert model is not None
    assert model.name == "New Model"
    assert len(model.environments) == 0


def test_create_de_model_carbonate_open_ramp(actions, state):
    actions.set_use_de_simulator(True)
    actions.create_de_model("carbonate_open_ramp")
    model = state.depositional_env_model
    assert model is not None
    assert model.name == "Carbonate Open Ramp"
    assert len(model.environments) > 0
    assert len(state.de_simulator_weights) == len(model.environments)


def test_create_de_model_carbonate_protected_ramp(actions, state):
    actions.set_use_de_simulator(True)
    actions.create_de_model("carbonate_protected_ramp")
    model = state.depositional_env_model
    assert model is not None
    assert "Protected" in model.name
    assert len(model.environments) > 0


# --- Actions: load/export DE simulation ---


def test_load_de_simulation_from_bytes(actions, state):
    env = DepositionalEnvironment(
        name="Env1",
        waterDepthModel=EnvironmentConditionModelUniform(
            "waterDepth",
            0.0,
            50.0,
        ),
    )
    de_model = DepositionalEnvironmentModel(
        name="LoadTest",
        environments=[env],
    )
    simulator = DepositionalEnvironmentSimulator(
        depositionalEnvironmentModel=de_model,
    )
    obj = actions._io.export_de_simulation_to_json_obj(
        simulator,
    )
    raw = json.dumps(obj).encode("utf-8")
    actions.set_use_de_simulator(True)
    actions.load_de_simulation_from_bytes(raw, "test.json")
    assert state.depositional_env_model is not None
    assert state.depositional_env_model.name == "LoadTest"


def test_export_de_simulation_as_json(actions, state):
    actions.set_use_de_simulator(True)
    actions.create_de_model("carbonate_open_ramp")
    result = actions.export_de_simulation_as_json()
    assert result["format"] == "pyWellSFM.DESimulationSchema"
    assert "depositionalEnvironmentModel" in result


# --- Actions: global env conditions load/export ---


def test_load_global_env_conditions_from_bytes(actions, state):
    model = EnvironmentConditionsModel(
        [
            EnvironmentConditionModelUniform("energy", 0.0, 1.0),
        ]
    )
    obj = actions._io.export_env_conditions_to_json_obj(model)
    raw = json.dumps(obj).encode("utf-8")
    actions.load_global_env_conditions_from_bytes(
        raw,
        "cond.json",
    )
    assert state.global_env_conditions is not None
    names = state.global_env_conditions.environmentConditionNames
    assert "energy" in names


def test_export_global_env_conditions_as_json(actions, state):
    state.global_env_conditions = EnvironmentConditionsModel(
        [
            EnvironmentConditionModelUniform("temp", 10.0, 30.0),
        ]
    )
    result = actions.export_global_env_conditions_as_json()
    assert result["format"] == ("pyWellSFM.EnvironmentConditionsModelData")
    assert "temp" in result["environmentConditions"]


# --- Actions: Environment CRUD ---


def _setup_multi_env(actions):
    """Helper: switch to multi-env mode with empty model."""
    actions.set_use_de_simulator(True)
    actions.create_de_model("empty")


def test_add_environment(actions, state):
    _setup_multi_env(actions)
    actions.add_environment("Shore")
    model = state.depositional_env_model
    assert model.getEnvironmentByName("Shore") is not None
    assert "Shore" in state.de_simulator_weights


def test_add_environment_duplicate(actions, state):
    _setup_multi_env(actions)
    actions.add_environment("Shore")
    with pytest.raises(ValueError, match="already exists"):
        actions.add_environment("Shore")


def test_remove_environment(actions, state):
    _setup_multi_env(actions)
    actions.add_environment("Shore")
    actions.remove_environment("Shore")
    model = state.depositional_env_model
    assert model.getEnvironmentByName("Shore") is None
    assert "Shore" not in state.de_simulator_weights


def test_rename_environment(actions, state):
    _setup_multi_env(actions)
    actions.add_environment("OldName")
    actions.rename_environment("OldName", "NewName")
    model = state.depositional_env_model
    assert model.getEnvironmentByName("OldName") is None
    assert model.getEnvironmentByName("NewName") is not None
    assert "NewName" in state.de_simulator_weights
    assert "OldName" not in state.de_simulator_weights


# --- Actions: Environment properties ---


def test_set_environment_distality(actions, state):
    _setup_multi_env(actions)
    actions.add_environment("Shore")
    actions.set_environment_distality("Shore", 0.5)
    env = state.depositional_env_model.getEnvironmentByName(
        "Shore",
    )
    assert env.distality == 0.5


def test_set_environment_distality_none(actions, state):
    _setup_multi_env(actions)
    actions.add_environment("Shore")
    actions.set_environment_distality("Shore", 0.5)
    actions.set_environment_distality("Shore", None)
    env = state.depositional_env_model.getEnvironmentByName(
        "Shore",
    )
    assert env.distality is None


def test_set_water_depth_model_uniform(actions, state):
    _setup_multi_env(actions)
    actions.add_environment("Shore")
    actions.set_environment_water_depth_model(
        "Shore",
        "Uniform",
        minValue=0.0,
        maxValue=50.0,
    )
    env = state.depositional_env_model.getEnvironmentByName(
        "Shore",
    )
    assert isinstance(
        env.waterDepthModel,
        EnvironmentConditionModelUniform,
    )
    assert env.waterDepthModel.minValue == 0.0
    assert env.waterDepthModel.maxValue == 50.0


def test_set_water_depth_model_constant(actions, state):
    _setup_multi_env(actions)
    actions.add_environment("Shore")
    actions.set_environment_water_depth_model(
        "Shore",
        "Constant",
        value=10.0,
    )
    env = state.depositional_env_model.getEnvironmentByName(
        "Shore",
    )
    assert isinstance(
        env.waterDepthModel,
        EnvironmentConditionModelConstant,
    )


def test_set_water_depth_model_triangular(actions, state):
    _setup_multi_env(actions)
    actions.add_environment("Shore")
    actions.set_environment_water_depth_model(
        "Shore",
        "Triangular",
        minValue=0.0,
        modeValue=5.0,
        maxValue=20.0,
    )
    env = state.depositional_env_model.getEnvironmentByName(
        "Shore",
    )
    assert isinstance(
        env.waterDepthModel,
        EnvironmentConditionModelTriangular,
    )


def test_set_water_depth_model_gaussian(actions, state):
    _setup_multi_env(actions)
    actions.add_environment("Shore")
    actions.set_environment_water_depth_model(
        "Shore",
        "Gaussian",
        meanValue=25.0,
        stdDev=5.0,
    )
    env = state.depositional_env_model.getEnvironmentByName(
        "Shore",
    )
    assert isinstance(
        env.waterDepthModel,
        EnvironmentConditionModelGaussian,
    )
    assert env.waterDepthModel.meanValue == 25.0


# --- Actions: Environment conditions (multi-env) ---


def test_add_env_condition(actions, state):
    _setup_multi_env(actions)
    actions.add_environment("Shore")
    actions.add_env_condition(
        "Shore",
        "energy",
        "Uniform",
        minValue=0.0,
        maxValue=1.0,
    )
    env = state.depositional_env_model.getEnvironmentByName(
        "Shore",
    )
    names = env.envConditionsModel.environmentConditionNames
    assert "energy" in names


def test_update_env_condition(actions, state):
    _setup_multi_env(actions)
    actions.add_environment("Shore")
    actions.add_env_condition(
        "Shore",
        "energy",
        "Uniform",
        minValue=0.0,
        maxValue=1.0,
    )
    actions.update_env_condition(
        "Shore",
        "energy",
        "Constant",
        value=0.5,
    )
    env = state.depositional_env_model.getEnvironmentByName(
        "Shore",
    )
    cond = env.envConditionsModel.envConditionModels["energy"]
    assert isinstance(cond, EnvironmentConditionModelConstant)


def test_remove_env_condition(actions, state):
    _setup_multi_env(actions)
    actions.add_environment("Shore")
    actions.add_env_condition(
        "Shore",
        "energy",
        "Uniform",
        minValue=0.0,
        maxValue=1.0,
    )
    actions.remove_env_condition("Shore", "energy")
    env = state.depositional_env_model.getEnvironmentByName(
        "Shore",
    )
    names = env.envConditionsModel.environmentConditionNames
    assert "energy" not in names


# --- Actions: Environment conditions (global) ---


def test_add_env_condition_global(actions, state):
    actions.add_env_condition(
        "global",
        "temperature",
        "Uniform",
        minValue=10.0,
        maxValue=30.0,
    )
    model = state.global_env_conditions
    assert model is not None
    assert "temperature" in model.environmentConditionNames


def test_update_env_condition_global(actions, state):
    actions.add_env_condition(
        "global",
        "temperature",
        "Uniform",
        minValue=10.0,
        maxValue=30.0,
    )
    actions.update_env_condition(
        "global",
        "temperature",
        "Gaussian",
        meanValue=20.0,
        stdDev=3.0,
    )
    cond = state.global_env_conditions.envConditionModels["temperature"]
    assert isinstance(cond, EnvironmentConditionModelGaussian)


def test_remove_env_condition_global(actions, state):
    actions.add_env_condition(
        "global",
        "temperature",
        "Uniform",
        minValue=10.0,
        maxValue=30.0,
    )
    actions.remove_env_condition("global", "temperature")
    names = state.global_env_conditions.environmentConditionNames
    assert "temperature" not in names


# --- Actions: DE simulator settings ---


def test_set_de_simulator_weight(actions, state):
    _setup_multi_env(actions)
    actions.add_environment("Shore")
    actions.set_de_simulator_weight("Shore", 2.5)
    assert state.de_simulator_weights["Shore"] == 2.5


def test_set_de_simulator_weight_invalid(actions, state):
    _setup_multi_env(actions)
    actions.add_environment("Shore")
    with pytest.raises(ValueError, match="> 0"):
        actions.set_de_simulator_weight("Shore", -1.0)


def test_set_de_simulator_params(actions, state):
    _setup_multi_env(actions)
    actions.set_de_simulator_params(
        waterDepth_sigma=3.0,
        trend_window=10,
    )
    params = state.de_simulator_params
    assert params is not None
    assert params.waterDepth_sigma == 3.0
    assert params.trend_window == 10
    assert params.waterDepth_weight == 1.0


def test_run_simulation_stores_simulated_wells(state, io_manager, message_store):
    """run_simulation populates state.simulated_wells."""
    actions = Actions(
        state=state,
        io_manager=io_manager,
        message_store=message_store,
    )

    mock_well_1 = MagicMock()
    mock_well_1.name = "W1"
    mock_well_2 = MagicMock()
    mock_well_2.name = "W2"

    mock_simulator = MagicMock()
    mock_simulator.outputs = MagicMock()
    mock_simulator.simulatedWells = [mock_well_1, mock_well_2]

    state.accumulation_model = MagicMock()
    state.accumulation_model.elements = {"Mud": MagicMock()}
    state.realization_data_list = [MagicMock(), MagicMock()]

    with (
        patch(
            "pywellsfmui.state.actions.FSSimulator",
            return_value=mock_simulator,
        ),
        patch(
            "pywellsfmui.state.actions.Scenario",
        ),
    ):
        actions.run_simulation()

    assert state.simulated_wells == [mock_well_1, mock_well_2]
