from pathlib import Path
from typing import Any

from pywellsfm.io import (
    depositionalEnvironmentSimulationToJsonObj,
    environmentConditionsModelToJsonObj,
    loadAccumulationModel,
    loadCurvesFromFile,
    loadDepositionalEnvironmentModel,
    loadDepositionalEnvironmentSimulationFromJsonObj,
    loadEnvironmentConditionsModelFromJsonObj,
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
from pywellsfm.model.EnvironmentConditionModel import (
    EnvironmentConditionsModel,
)
from pywellsfm.simulator import (
    DepositionalEnvironmentSimulator,
    FSSimulator,
)


class IOManager:
    """Wrap pyWellSFM IO functions.

    Single point of contact with the filesystem.
    Designed to be replaceable by a ProjectManager
    for project-based persistence.
    """

    def load_facies_model(self, path: str) -> FaciesModel:
        """Load a facies model from a JSON file."""
        return loadFaciesModel(path)

    def save_facies_model(self, model: FaciesModel, path: str) -> None:
        """Save a facies model to a JSON file."""
        saveFaciesModel(model, path)

    def load_well(self, path: str) -> Well:
        """Load a well from a file."""
        return loadWell(path)

    def save_well(self, well: Well, path: str) -> None:
        """Save a well to a file."""
        saveWell(well, path)

    def load_accumulation_model(self, path: str) -> AccumulationModel:
        """Load an accumulation model from a file."""
        return loadAccumulationModel(path)

    def save_accumulation_model(
        self, model: AccumulationModel, path: str
    ) -> None:
        """Save an accumulation model to a file."""
        saveAccumulationModel(model, path)

    def load_curves(self, path: str) -> list[Curve]:
        """Load curves from a file."""
        return loadCurvesFromFile(Path(path))

    def save_curve(self, curve: Curve, path: str) -> None:
        """Save a curve to a JSON file."""
        saveCurveToJson(curve, path)

    def load_depositional_env_model(
        self, path: str
    ) -> DepositionalEnvironmentModel:
        """Load a depositional environment model."""
        return loadDepositionalEnvironmentModel(path)

    def save_depositional_env_model(
        self,
        model: DepositionalEnvironmentModel,
        path: str,
    ) -> None:
        """Save a depositional environment model."""
        saveDepositionalEnvironmentModel(model, path)

    def load_simulation(self, path: str) -> FSSimulator:
        """Load an FS simulation from a file."""
        return loadFSSimulation(path)

    def save_simulation(
        self, simulator: FSSimulator, path: str, name: str
    ) -> None:
        """Save an FS simulation to a file."""
        saveFSSimulation(simulator, path, name=name)

    def load_de_simulation_from_json_obj(
        self,
        obj: dict[str, Any],
    ) -> DepositionalEnvironmentSimulator:
        """Load a DE simulation from a JSON dict."""
        return loadDepositionalEnvironmentSimulationFromJsonObj(obj)

    def export_de_simulation_to_json_obj(
        self,
        simulator: DepositionalEnvironmentSimulator,
    ) -> dict[str, Any]:
        """Export a DE simulation to a JSON dict."""
        return depositionalEnvironmentSimulationToJsonObj(simulator)

    def load_env_conditions_from_json_obj(
        self,
        obj: dict[str, Any],
    ) -> EnvironmentConditionsModel:
        """Load environment conditions from a JSON dict."""
        return loadEnvironmentConditionsModelFromJsonObj(
            obj,
            base_dir=None,
        )

    def export_env_conditions_to_json_obj(
        self,
        model: EnvironmentConditionsModel,
    ) -> dict[str, Any]:
        """Export environment conditions to a JSON dict."""
        return environmentConditionsModelToJsonObj(model)
