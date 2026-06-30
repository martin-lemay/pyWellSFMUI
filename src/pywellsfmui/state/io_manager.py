from pathlib import Path

from pywellsfm.io import (
    loadAccumulationModel,
    loadCurvesFromFile,
    loadDepositionalEnvironmentModel,
    loadFaciesModel,
    loadFSSimulation,
    loadWell,
    saveAccumulationModel,
    saveCurveToJson,
    saveDepositionalEnvironmentModel,
    saveFaciesModel,
    saveFSSimulation,
    saveWell,
)
from pywellsfm.model import (
    AccumulationModel,
    Curve,
    DepositionalEnvironmentModel,
    FaciesModel,
    Well,
)
from pywellsfm.simulator import FSSimulator


class IOManager:
    """Wraps pyWellSFM IO functions. Single point of contact with the filesystem.

    Designed to be replaceable by a ProjectManager for project-based persistence.
    """

    def load_facies_model(self, path: str) -> FaciesModel:
        return loadFaciesModel(path)

    def save_facies_model(self, model: FaciesModel, path: str) -> None:
        saveFaciesModel(model, path)

    def load_well(self, path: str) -> Well:
        return loadWell(path)

    def save_well(self, well: Well, path: str) -> None:
        saveWell(well, path)

    def load_accumulation_model(self, path: str) -> AccumulationModel:
        return loadAccumulationModel(path)

    def save_accumulation_model(self, model: AccumulationModel, path: str) -> None:
        saveAccumulationModel(model, path)

    def load_curves(self, path: str) -> list[Curve]:
        return loadCurvesFromFile(Path(path))

    def save_curve(self, curve: Curve, path: str) -> None:
        saveCurveToJson(curve, path)

    def load_depositional_env_model(self, path: str) -> DepositionalEnvironmentModel:
        return loadDepositionalEnvironmentModel(path)

    def save_depositional_env_model(
        self, model: DepositionalEnvironmentModel, path: str
    ) -> None:
        saveDepositionalEnvironmentModel(model, path)

    def load_simulation(self, path: str) -> FSSimulator:
        return loadFSSimulation(path)

    def save_simulation(
        self, simulator: FSSimulator, path: str, name: str
    ) -> None:
        saveFSSimulation(simulator, path, name=name)
