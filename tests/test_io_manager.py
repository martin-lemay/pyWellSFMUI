import os
import pytest
from pywellsfmui.state.io_manager import IOManager


PYWELLSFM_TEST_DATA = "C:\\Users\\MartinLemay\\OneDrive - ELIIS\\PERSO\\python\\SFM\\pyWellSFM\\tests\\data"


@pytest.fixture
def io_manager():
    return IOManager()


@pytest.mark.skipif(
    not os.path.isdir(PYWELLSFM_TEST_DATA),
    reason="pyWellSFM test data not found",
)
class TestIOManagerWithData:
    def test_load_facies_model(self, io_manager):
        path = os.path.join(PYWELLSFM_TEST_DATA, "facies_model.json")
        if not os.path.exists(path):
            pytest.skip("facies_model.json not found in test data")
        model = io_manager.load_facies_model(path)
        assert model is not None

    def test_load_well(self, io_manager):
        # Find a well JSON in test data
        well_files = [
            f
            for f in os.listdir(PYWELLSFM_TEST_DATA)
            if "well" in f.lower() and f.endswith(".json")
        ]
        if not well_files:
            pytest.skip("No well JSON found in test data")
        well = io_manager.load_well(os.path.join(PYWELLSFM_TEST_DATA, well_files[0]))
        assert well is not None


def test_io_manager_instantiation():
    mgr = IOManager()
    assert mgr is not None
