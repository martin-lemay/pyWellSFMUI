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
from pywellsfmui.state.message_store import MessageLevel, MessageStore


class Actions:
    """Command layer between UI and AppState.

    All state mutations go through this class. UI widgets call these methods;
    they validate, execute pyWellSFM logic, and update AppState.
    """

    def __init__(
        self,
        state: AppState,
        io_manager: IOManager,
        message_store: MessageStore,
    ) -> None:
        self._state = state
        self._io = io_manager
        self._messages = message_store

    # --- Facies Model ---

    def set_facies_model(self, model: FaciesModel) -> None:
        self._state.facies_model = model
        self._messages.add(MessageLevel.INFO, "Facies model set", source="actions")

    def load_facies_model(self, path: str) -> None:
        try:
            model = self._io.load_facies_model(path)
            self._state.facies_model = model
            self._messages.add(
                MessageLevel.INFO, f"Loaded facies model from {path}", source="actions"
            )
        except Exception as e:
            self._messages.add(
                MessageLevel.ERROR,
                f"Failed to load facies model: {e}",
                source="actions",
            )
            raise

    def save_facies_model(self, path: str) -> None:
        if self._state.facies_model is None:
            self._messages.add(
                MessageLevel.WARNING, "No facies model to save", source="actions"
            )
            raise ValueError("No facies model to save")
        try:
            self._io.save_facies_model(self._state.facies_model, path)
            self._messages.add(
                MessageLevel.INFO, f"Saved facies model to {path}", source="actions"
            )
        except Exception as e:
            self._messages.add(
                MessageLevel.ERROR,
                f"Failed to save facies model: {e}",
                source="actions",
            )
            raise

    # --- Wells ---

    def load_well(self, path: str) -> None:
        try:
            well = self._io.load_well(path)
            self._state.wells = [*self._state.wells, well]
            self._messages.add(
                MessageLevel.INFO, f"Loaded well '{well.name}' from {path}", source="actions"
            )
        except Exception as e:
            self._messages.add(
                MessageLevel.ERROR, f"Failed to load well: {e}", source="actions"
            )
            raise

    def remove_well(self, well_name: str) -> None:
        new_wells = [w for w in self._state.wells if w.name != well_name]
        if len(new_wells) == len(self._state.wells):
            self._messages.add(
                MessageLevel.WARNING,
                f"Well '{well_name}' not found",
                source="actions",
            )
            raise ValueError(f"Well '{well_name}' not found")
        self._state.wells = new_wells
        self._messages.add(
            MessageLevel.INFO, f"Removed well '{well_name}'", source="actions"
        )

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
            self._messages.add(
                MessageLevel.WARNING,
                f"Well '{well_name}' not found",
                source="actions",
            )
            raise ValueError(f"Well '{well_name}' not found")
        if self._state.facies_model is None:
            self._messages.add(
                MessageLevel.WARNING, "No facies model set", source="actions"
            )
            raise ValueError("No facies model set")

        try:
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
            self._messages.add(
                MessageLevel.INFO,
                f"Computed accommodation for well '{well_name}'",
                source="actions",
            )
        except Exception as e:
            self._messages.add(
                MessageLevel.ERROR,
                f"Failed to compute accommodation for '{well_name}': {e}",
                source="actions",
            )
            raise

    # --- Accumulation Model ---

    def set_accumulation_model(self, model: AccumulationModel) -> None:
        self._state.accumulation_model = model
        self._messages.add(
            MessageLevel.INFO, "Accumulation model set", source="actions"
        )

    def load_accumulation_model(self, path: str) -> None:
        try:
            model = self._io.load_accumulation_model(path)
            self._state.accumulation_model = model
            self._messages.add(
                MessageLevel.INFO,
                f"Loaded accumulation model from {path}",
                source="actions",
            )
        except Exception as e:
            self._messages.add(
                MessageLevel.ERROR,
                f"Failed to load accumulation model: {e}",
                source="actions",
            )
            raise

    def save_accumulation_model(self, path: str) -> None:
        if self._state.accumulation_model is None:
            self._messages.add(
                MessageLevel.WARNING,
                "No accumulation model to save",
                source="actions",
            )
            raise ValueError("No accumulation model to save")
        try:
            self._io.save_accumulation_model(self._state.accumulation_model, path)
            self._messages.add(
                MessageLevel.INFO,
                f"Saved accumulation model to {path}",
                source="actions",
            )
        except Exception as e:
            self._messages.add(
                MessageLevel.ERROR,
                f"Failed to save accumulation model: {e}",
                source="actions",
            )
            raise

    # --- Eustatic Curve ---

    def set_eustatic_curve(self, curve: Curve) -> None:
        self._state.eustatic_curve = curve
        self._messages.add(
            MessageLevel.INFO, "Eustatic curve set", source="actions"
        )

    def load_eustatic_curve(self, path: str) -> None:
        try:
            curves = self._io.load_curves(path)
            if not curves:
                self._messages.add(
                    MessageLevel.WARNING,
                    f"No curves found in {path}",
                    source="actions",
                )
                raise ValueError(f"No curves found in {path}")
            self._state.eustatic_curve = curves[0]
            self._messages.add(
                MessageLevel.INFO,
                f"Loaded eustatic curve from {path}",
                source="actions",
            )
        except ValueError:
            raise
        except Exception as e:
            self._messages.add(
                MessageLevel.ERROR,
                f"Failed to load eustatic curve: {e}",
                source="actions",
            )
            raise

    def save_eustatic_curve(self, path: str) -> None:
        if self._state.eustatic_curve is None:
            self._messages.add(
                MessageLevel.WARNING,
                "No eustatic curve to save",
                source="actions",
            )
            raise ValueError("No eustatic curve to save")
        try:
            self._io.save_curve(self._state.eustatic_curve, path)
            self._messages.add(
                MessageLevel.INFO,
                f"Saved eustatic curve to {path}",
                source="actions",
            )
        except Exception as e:
            self._messages.add(
                MessageLevel.ERROR,
                f"Failed to save eustatic curve: {e}",
                source="actions",
            )
            raise

    # --- Depositional Environment Model ---

    def set_depositional_env_model(
        self, model: DepositionalEnvironmentModel
    ) -> None:
        self._state.depositional_env_model = model
        self._messages.add(
            MessageLevel.INFO,
            "Depositional environment model set",
            source="actions",
        )

    def load_depositional_env_model(self, path: str) -> None:
        try:
            model = self._io.load_depositional_env_model(path)
            self._state.depositional_env_model = model
            self._messages.add(
                MessageLevel.INFO,
                f"Loaded depositional environment model from {path}",
                source="actions",
            )
        except Exception as e:
            self._messages.add(
                MessageLevel.ERROR,
                f"Failed to load depositional environment model: {e}",
                source="actions",
            )
            raise

    def save_depositional_env_model(self, path: str) -> None:
        if self._state.depositional_env_model is None:
            self._messages.add(
                MessageLevel.WARNING,
                "No depositional environment model to save",
                source="actions",
            )
            raise ValueError("No depositional environment model to save")
        try:
            self._io.save_depositional_env_model(
                self._state.depositional_env_model, path
            )
            self._messages.add(
                MessageLevel.INFO,
                f"Saved depositional environment model to {path}",
                source="actions",
            )
        except Exception as e:
            self._messages.add(
                MessageLevel.ERROR,
                f"Failed to save depositional environment model: {e}",
                source="actions",
            )
            raise

    # --- Simulator Parameters ---

    def set_simulator_params(self, params: FSSimulatorParameters) -> None:
        self._state.simulator_params = params
        self._messages.add(
            MessageLevel.INFO, "Simulator parameters set", source="actions"
        )

    # --- Simulation ---

    def run_simulation(self) -> None:
        if self._state.accumulation_model is None:
            self._messages.add(
                MessageLevel.WARNING,
                "No accumulation model set",
                source="actions",
            )
            raise ValueError("No accumulation model set")
        if not self._state.realization_data_list:
            self._messages.add(
                MessageLevel.WARNING,
                "No realization data defined",
                source="actions",
            )
            raise ValueError("No realization data defined")

        try:
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
            self._messages.add(
                MessageLevel.INFO, "Simulation completed", source="actions"
            )
        except Exception as e:
            self._messages.add(
                MessageLevel.ERROR,
                f"Simulation failed: {e}",
                source="actions",
            )
            raise

    def clear_simulation_outputs(self) -> None:
        self._state.simulation_outputs = None
        self._messages.add(
            MessageLevel.INFO, "Simulation outputs cleared", source="actions"
        )
