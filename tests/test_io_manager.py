from pathlib import Path

import pytest

from pywellsfmui.state.io_manager import IOManager

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"


@pytest.fixture
def io_manager() -> IOManager:
    """Return a fresh IOManager."""
    return IOManager()


def test_load_facies_model(io_manager: IOManager) -> None:
    """Test loading a facies model from file."""
    model = io_manager.load_facies_model(
        str(EXAMPLES_DIR / "accommodation_facies_model.json")
    )
    assert model.faciesSet


def test_load_well(io_manager: IOManager) -> None:
    """Test loading a well from file."""
    well = io_manager.load_well(str(EXAMPLES_DIR / "accommodation_well.json"))
    assert well.name


def test_load_simulation(io_manager: IOManager) -> None:
    """Test loading a full simulation from file."""
    simulator = io_manager.load_simulation(
        str(EXAMPLES_DIR / "simulation_simple.json")
    )
    assert simulator.scenario.accumulationModel is not None


def test_io_manager_instantiation() -> None:
    """Test IOManager can be instantiated."""
    mgr = IOManager()
    assert mgr is not None
