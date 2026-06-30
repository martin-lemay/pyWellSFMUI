from pywellsfm.model import (
    AccumulationModel,
    Curve,
    DepositionalEnvironmentModel,
    FaciesModel,
    FSSimulatorParameters,
    Scenario,
    RealizationData,
)
from pywellsfm.model import AccommodationSpaceWellCalculator
from pywellsfm.simulator import FSSimulator

from pywellsfmui.state.app_state import AppState
from pywellsfmui.state.io_manager import IOManager


class Actions:
    """Command layer between UI and AppState.

    All state mutations go through this class. UI widgets call these methods;
    they validate, execute pyWellSFM logic, and update AppState.
    """

    def __init__(self, state: AppState, io_manager: IOManager) -> None:
        self._state = state
        self._io = io_manager

    # --- Facies Model ---

    def set_facies_model(self, model: FaciesModel) -> None:
        self._state.facies_model = model

    def load_facies_model(self, path: str) -> None:
        model = self._io.load_facies_model(path)
        self._state.facies_model = model

    def save_facies_model(self, path: str) -> None:
        if self._state.facies_model is None:
            raise ValueError("No facies model to save")
        self._io.save_facies_model(self._state.facies_model, path)

    # --- Wells ---

    def load_well(self, path: str) -> None:
        well = self._io.load_well(path)
        self._state.wells = [*self._state.wells, well]

    def remove_well(self, well_name: str) -> None:
        new_wells = [w for w in self._state.wells if w.name != well_name]
        if len(new_wells) == len(self._state.wells):
            raise ValueError(f"Well '{well_name}' not found")
        self._state.wells = new_wells

    # --- Accommodation ---

    def compute_accommodation(
        self,
        well_name: str,
        facies_log_name: str,
        from_marker_name: str | None = None,
        to_marker_name: str | None = None,
        accommodation_at_base: float = 0.0,
    ) -> None:
        well = next(
            (w for w in self._state.wells if w.name == well_name), None
        )
        if well is None:
            raise ValueError(f"Well '{well_name}' not found")
        if self._state.facies_model is None:
            raise ValueError("No facies model set")

        facies_list = list(self._state.facies_model.faciesSet)

        from_marker = None
        to_marker = None
        if from_marker_name:
            from_marker = next(
                (m for m in well.markers if m.name == from_marker_name), None
            )
        if to_marker_name:
            to_marker = next(
                (m for m in well.markers if m.name == to_marker_name), None
            )

        calculator = AccommodationSpaceWellCalculator(
            well=well, faciesList=facies_list
        )
        curve = calculator.computeAccommodationCurve(
            faciesLogName=facies_log_name,
            fromMarker=from_marker,
            toMarker=to_marker,
            accommodationAtBase=accommodation_at_base,
        )
        results = dict(self._state.accommodation_results)
        results[well_name] = curve
        self._state.accommodation_results = results

    # --- Accumulation Model ---

    def set_accumulation_model(self, model: AccumulationModel) -> None:
        self._state.accumulation_model = model

    def load_accumulation_model(self, path: str) -> None:
        model = self._io.load_accumulation_model(path)
        self._state.accumulation_model = model

    def save_accumulation_model(self, path: str) -> None:
        if self._state.accumulation_model is None:
            raise ValueError("No accumulation model to save")
        self._io.save_accumulation_model(self._state.accumulation_model, path)

    # --- Eustatic Curve ---

    def set_eustatic_curve(self, curve: Curve) -> None:
        self._state.eustatic_curve = curve

    def load_eustatic_curve(self, path: str) -> None:
        curves = self._io.load_curves(path)
        if not curves:
            raise ValueError(f"No curves found in {path}")
        self._state.eustatic_curve = curves[0]

    def save_eustatic_curve(self, path: str) -> None:
        if self._state.eustatic_curve is None:
            raise ValueError("No eustatic curve to save")
        self._io.save_curve(self._state.eustatic_curve, path)

    # --- Depositional Environment Model ---

    def set_depositional_env_model(
        self, model: DepositionalEnvironmentModel
    ) -> None:
        self._state.depositional_env_model = model

    def load_depositional_env_model(self, path: str) -> None:
        model = self._io.load_depositional_env_model(path)
        self._state.depositional_env_model = model

    def save_depositional_env_model(self, path: str) -> None:
        if self._state.depositional_env_model is None:
            raise ValueError("No depositional environment model to save")
        self._io.save_depositional_env_model(
            self._state.depositional_env_model, path
        )

    # --- Simulator Parameters ---

    def set_simulator_params(self, params: FSSimulatorParameters) -> None:
        self._state.simulator_params = params

    # --- Simulation ---

    def run_simulation(self) -> None:
        if self._state.accumulation_model is None:
            raise ValueError("No accumulation model set")
        if not self._state.realization_data_list:
            raise ValueError("No realization data defined")

        scenario = Scenario(
            name="simulation",
            accumulationModel=self._state.accumulation_model,
            eustaticCurve=self._state.eustatic_curve,
            depositionalEnvironmentModel=self._state.depositional_env_model,
            faciesModel=self._state.facies_model,
        )

        params = self._state.simulator_params or FSSimulatorParameters()
        use_de_sim = self._state.depositional_env_model is not None

        simulator = FSSimulator(
            scenario=scenario,
            realizationDataList=self._state.realization_data_list,
            use_depositional_environment_simulator=use_de_sim,
            fsSimulator_params=params,
        )
        simulator.prepare()
        simulator.run()
        simulator.finalize()
        self._state.simulation_outputs = simulator.outputs

    def clear_simulation_outputs(self) -> None:
        self._state.simulation_outputs = None
