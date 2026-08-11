import asyncio
import json
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import numpy.typing as npt

from pywellsfm.io.accumulation_model_io import (
    accumulationModelToJsonObj,
    loadAccumulationModelFromJsonObj,
)
from pywellsfm.io.facies_model_io import (
    faciesModelToJsonObj,
    loadFaciesModelFromJsonObj,
)
from pywellsfm.io.well_io import loadWell as _loadWell
from pywellsfm.model import (
    AccommodationSpaceWellCalculator,
    AccumulationCurve,
    AccumulationModel,
    AccumulationModelElementGaussian,
    AccumulationModelElementOptimum,
    Curve,
    DepositionalEnvironmentModel,
    EnvironmentalFacies,
    Facies,
    FaciesCriteria,
    FaciesCriteriaType,
    FaciesModel,
    FSSimulatorParameters,
    Marker,
    PetrophysicalFacies,
    Scenario,
    SedimentaryFacies,
    Well,
)
from pywellsfm.model.DepositionalEnvironment import (
    CarbonateOpenRampDepositionalEnvironmentModel,
    CarbonateProtectedRampDepositionalEnvironmentModel,
    DepositionalEnvironment,
)
from pywellsfm.model.EnvironmentConditionModel import (
    EnvironmentConditionModelConstant,
    EnvironmentConditionModelCurve,
    EnvironmentConditionModelGaussian,
    EnvironmentConditionModelTriangular,
    EnvironmentConditionModelUniform,
    EnvironmentConditionsModel,
)
from pywellsfm.simulator import (
    DESimulatorParameters,
    DepositionalEnvironmentSimulator,
    FSSimulator,
)
from pywellsfmui.state.app_state import AppState
from pywellsfmui.state.io_manager import IOManager
from pywellsfmui.state.message_store import MessageLevel, MessageStore

_FACIES_CONSTRUCTORS: dict[FaciesCriteriaType, type[Facies]] = {
    FaciesCriteriaType.SEDIMENTOLOGICAL: SedimentaryFacies,
    FaciesCriteriaType.PETROPHYSICAL: PetrophysicalFacies,
    FaciesCriteriaType.ENVIRONMENTAL: EnvironmentalFacies,
    FaciesCriteriaType.UNCATEGORIZED: Facies,
}


def _compute_one_well(
    well: Well,
    facies_list: list,
    facies_log_name: str,
) -> tuple[str, object]:
    """Compute accommodation for one well (picklable target).

    Returns:
        (well_name, AccommodationSpaceWellCalculator) on success.

    Raises:
        Exception on computation failure.
    """
    calculator = AccommodationSpaceWellCalculator(well=well, faciesList=facies_list)
    calculator.computeAccommodationCurve(
        faciesLogName=facies_log_name,
    )
    return (well.name, calculator)


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

    def _reset_accommodation_results(self) -> None:
        """Clear all accommodation results and computed flags."""
        if not self._state.well_accommodation_computed:
            return
        self._state.accommodation_results = {}
        self._state.well_accommodation_computed = dict.fromkeys(
            self._state.well_accommodation_computed, False
        )
        self._messages.add(
            MessageLevel.WARNING,
            "Facies model changed — accommodation results have been reset",
            source="actions",
        )

    # --- Facies Model ---

    def set_facies_model(self, model: FaciesModel) -> None:
        self._state.facies_model = model
        self._reset_accommodation_results()
        self._messages.add(MessageLevel.INFO, "Facies model set", source="actions")

    def load_facies_model(self, path: str) -> None:
        try:
            model = self._io.load_facies_model(path)
            self._state.facies_model = model
            self._reset_accommodation_results()
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

    def load_facies_model_from_bytes(self, data: bytes, filename: str = "") -> None:
        """Load a facies model from raw JSON bytes.

        Args:
            data: UTF-8-encoded JSON bytes conforming to the pyWellSFM
                FaciesModelData schema.
            filename: Original filename for logging.

        Raises:
            Exception: Any parse or schema error from pyWellSFM is re-raised
                after being logged.
        """
        try:
            obj = json.loads(data.decode("utf-8"))
            model = loadFaciesModelFromJsonObj(obj)
            self._state.facies_model = model
            self._reset_accommodation_results()
            label = filename or "file"
            self._messages.add(
                MessageLevel.INFO,
                f"Loaded facies model from {label}",
                source="actions",
            )
        except Exception as e:
            self._messages.add(
                MessageLevel.ERROR,
                f"Failed to load facies model: {e}",
                source="actions",
            )
            raise

    def export_facies_model_as_json(self) -> dict:
        """Serialize the current facies model to a JSON-compatible dict.

        Returns:
            A dict conforming to the pyWellSFM FaciesModelData schema.

        Raises:
            ValueError: If no facies model is currently set.
        """
        if self._state.facies_model is None:
            self._messages.add(
                MessageLevel.WARNING,
                "No facies model to export",
                source="actions",
            )
            raise ValueError("No facies model to export")
        return faciesModelToJsonObj(self._state.facies_model)

    def create_empty_facies_model(self) -> None:
        self._state.facies_model = None
        self._reset_accommodation_results()
        self._messages.add(
            MessageLevel.INFO,
            "Created new empty facies model",
            source="actions",
        )

    def add_facies(self, name: str, criteria_type: FaciesCriteriaType) -> None:
        if (
            self._state.facies_model is not None
            and self._state.facies_model.getFaciesByName(name) is not None
        ):
            self._messages.add(
                MessageLevel.WARNING,
                f"Facies '{name}' already exists",
                source="actions",
            )
            raise ValueError(f"Facies '{name}' already exists")

        cls = _FACIES_CONSTRUCTORS[criteria_type]
        if cls is Facies:
            new_facies = Facies(
                name=name,
                criteria=set(),
                criteriaType=criteria_type,
            )
        else:
            new_facies = cls(name=name, criteria=set())

        if self._state.facies_model is None:
            self._state.facies_model = FaciesModel(faciesSet={new_facies})
        else:
            self._state.facies_model.faciesSet.add(new_facies)
            self._state.facies_model = self._state.facies_model
        self._reset_accommodation_results()
        self._messages.add(
            MessageLevel.INFO,
            f"Added facies '{name}'",
            source="actions",
        )

    def remove_facies(self, facies_name: str) -> None:
        if self._state.facies_model is None:
            self._messages.add(
                MessageLevel.WARNING,
                "No facies model set",
                source="actions",
            )
            raise ValueError("No facies model set")

        facies = self._state.facies_model.getFaciesByName(facies_name)
        if facies is None:
            self._messages.add(
                MessageLevel.WARNING,
                f"Facies '{facies_name}' not found",
                source="actions",
            )
            raise ValueError(f"Facies '{facies_name}' not found")

        if len(self._state.facies_model.faciesSet) == 1:
            self._messages.add(
                MessageLevel.WARNING,
                "Cannot remove last facies",
                source="actions",
            )
            raise ValueError("Cannot remove last facies from model")

        self._state.facies_model.faciesSet.discard(facies)
        self._state.facies_model = self._state.facies_model
        self._reset_accommodation_results()
        self._messages.add(
            MessageLevel.INFO,
            f"Removed facies '{facies_name}'",
            source="actions",
        )

    def _get_facies_or_raise(self, facies_name: str) -> Facies:
        if self._state.facies_model is None:
            self._messages.add(
                MessageLevel.WARNING,
                "No facies model set",
                source="actions",
            )
            raise ValueError("No facies model set")
        facies = self._state.facies_model.getFaciesByName(facies_name)
        if facies is None:
            self._messages.add(
                MessageLevel.WARNING,
                f"Facies '{facies_name}' not found",
                source="actions",
            )
            raise ValueError(f"Facies '{facies_name}' not found")
        return facies

    def add_criteria(
        self,
        facies_name: str,
        criteria_name: str,
        min_range: float,
        max_range: float,
    ) -> None:
        facies = self._get_facies_or_raise(facies_name)
        if facies.getCriteria(criteria_name) is not None:
            self._messages.add(
                MessageLevel.WARNING,
                f"Criterion '{criteria_name}' already exists on facies '{facies_name}'",
                source="actions",
            )
            raise ValueError(
                f"Criterion '{criteria_name}' already exists on facies '{facies_name}'"
            )
        crit = FaciesCriteria(
            name=criteria_name,
            minRange=min_range,
            maxRange=max_range,
            type=facies.criteriaCollection.type,
        )
        facies.addCriteria(crit)
        self._state.facies_model = self._state.facies_model
        self._reset_accommodation_results()
        self._messages.add(
            MessageLevel.INFO,
            f"Added criterion '{criteria_name}' to facies '{facies_name}'",
            source="actions",
        )

    def remove_criteria(self, facies_name: str, criteria_name: str) -> None:
        facies = self._get_facies_or_raise(facies_name)
        if facies.getCriteria(criteria_name) is None:
            self._messages.add(
                MessageLevel.WARNING,
                f"Criterion '{criteria_name}' not found on facies '{facies_name}'",
                source="actions",
            )
            raise ValueError(
                f"Criterion '{criteria_name}' not found on facies '{facies_name}'"
            )
        facies.criteriaCollection.removeCriteria({criteria_name})
        self._state.facies_model = self._state.facies_model
        self._reset_accommodation_results()
        self._messages.add(
            MessageLevel.INFO,
            f"Removed criterion '{criteria_name}' from facies '{facies_name}'",
            source="actions",
        )

    def update_criteria(
        self,
        facies_name: str,
        criteria_name: str,
        min_range: float,
        max_range: float,
    ) -> None:
        facies = self._get_facies_or_raise(facies_name)
        crit = facies.getCriteria(criteria_name)
        if crit is None:
            self._messages.add(
                MessageLevel.WARNING,
                f"Criterion '{criteria_name}' not found on facies '{facies_name}'",
                source="actions",
            )
            raise ValueError(
                f"Criterion '{criteria_name}' not found on facies '{facies_name}'"
            )
        crit.minRange = min_range
        crit.maxRange = max_range
        self._state.facies_model = self._state.facies_model
        self._reset_accommodation_results()
        self._messages.add(
            MessageLevel.INFO,
            f"Updated criterion '{criteria_name}' on facies '{facies_name}'",
            source="actions",
        )

    # --- Wells ---

    def load_well(self, path: str) -> None:
        try:
            well = self._io.load_well(path)
            self._state.wells = [*self._state.wells, well]
            self._messages.add(
                MessageLevel.INFO,
                f"Loaded well '{well.name}' from {path}",
                source="actions",
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
        log_names = dict(self._state.well_facies_log_names)
        log_names.pop(well_name, None)
        self._state.well_facies_log_names = log_names
        computed = dict(self._state.well_accommodation_computed)
        computed.pop(well_name, None)
        self._state.well_accommodation_computed = computed
        results = dict(self._state.accommodation_results)
        results.pop(well_name, None)
        self._state.accommodation_results = results
        self._messages.add(
            MessageLevel.INFO, f"Removed well '{well_name}'", source="actions"
        )

    def add_empty_well(self) -> None:
        """Add an empty well with a unique default name."""
        existing = {w.name for w in self._state.wells}
        idx = 1
        while f"Well_{idx:02d}" in existing:
            idx += 1
        name = f"Well_{idx:02d}"
        well = Well(name, np.array([0.0, 0.0, 0.0]), 0.0)
        self._state.wells = [*self._state.wells, well]
        self._messages.add(
            MessageLevel.INFO,
            f"Added empty well '{name}'",
            source="actions",
        )

    def _find_well(self, well_name: str) -> Well:
        for w in self._state.wells:
            if w.name == well_name:
                return w
        raise ValueError(f"Well '{well_name}' not found")

    def rename_well(self, old_name: str, new_name: str) -> None:
        """Rename a well, updating all related state dicts."""
        if old_name == new_name:
            return
        existing = {w.name for w in self._state.wells}
        if new_name in existing:
            raise ValueError(f"Well '{new_name}' already exists")
        well = self._find_well(old_name)
        well.name = new_name
        # Update keyed state dicts
        for attr in (
            "well_facies_log_names",
            "well_accommodation_computed",
            "accommodation_results",
        ):
            d = dict(getattr(self._state, attr))
            if old_name in d:
                d[new_name] = d.pop(old_name)
                setattr(self._state, attr, d)
        # Re-assign to trigger watchers
        self._state.wells = list(self._state.wells)

    def update_well_location(
        self,
        well_name: str,
        x: float,
        y: float,
        z: float,
    ) -> None:
        """Update well head coordinates."""
        well = self._find_well(well_name)
        well.wellHeadCoords = np.array([x, y, z])

    def update_well_depth(self, well_name: str, depth: float) -> None:
        """Update well depth."""
        well = self._find_well(well_name)
        well.depth = depth

    def set_well_markers(self, well_name: str, markers: list[Marker]) -> None:
        """Replace all markers on a well."""
        well = self._find_well(well_name)
        well.setMarkers(markers)

    def load_well_from_bytes(self, data: bytes, filename: str = "") -> None:
        """Load a well from raw file bytes (JSON or LAS).

        Args:
            data: Raw file bytes.
            filename: Original filename, used to determine format.

        Raises:
            Exception: Any parse error is re-raised after logging.
        """
        ext = Path(filename).suffix.lower() if filename else ".json"
        try:
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                tmp.write(data)
                tmp_path = tmp.name
            try:
                well = _loadWell(tmp_path)
            finally:
                Path(tmp_path).unlink(missing_ok=True)
            self._add_well_with_default_log(well, filename)
        except Exception as e:
            self._messages.add(
                MessageLevel.ERROR,
                f"Failed to load well: {e}",
                source="actions",
            )
            raise

    def _add_well_with_default_log(self, well: Well, filename: str) -> None:
        for existing in self._state.wells:
            if existing.name == well.name and np.allclose(
                existing.wellHeadCoords[:2],
                well.wellHeadCoords[:2],
            ):
                self._messages.add(
                    MessageLevel.WARNING,
                    "Imported well already exists. Check for the name and coordinates",
                    source="actions",
                )
                return
        self._state.wells = [*self._state.wells, well]
        log_names = dict(self._state.well_facies_log_names)
        discrete = sorted(well.getDiscreteLogNames())
        if discrete:
            log_names[well.name] = discrete[0]
        self._state.well_facies_log_names = log_names
        label = filename or "file"
        self._messages.add(
            MessageLevel.INFO,
            f"Loaded well '{well.name}' from {label}",
            source="actions",
        )

    def set_well_facies_log(self, well_name: str, log_name: str) -> None:
        well = next(
            (w for w in self._state.wells if w.name == well_name),
            None,
        )
        if well is None:
            self._messages.add(
                MessageLevel.WARNING,
                f"Well '{well_name}' not found",
                source="actions",
            )
            raise ValueError(f"Well '{well_name}' not found")
        if log_name not in well.getDiscreteLogNames():
            self._messages.add(
                MessageLevel.WARNING,
                f"Log '{log_name}' not found on well '{well_name}'",
                source="actions",
            )
            raise ValueError(f"Log '{log_name}' not found on well '{well_name}'")
        log_names = dict(self._state.well_facies_log_names)
        log_names[well_name] = log_name
        self._state.well_facies_log_names = log_names
        computed = dict(self._state.well_accommodation_computed)
        if well_name in computed:
            computed[well_name] = False
            self._state.well_accommodation_computed = computed

    # --- Accommodation ---

    def compute_all_accommodation(self) -> None:
        """Compute accommodation for all loaded wells.

        Uses the selected facies log for each well.
        """
        if not self._state.wells:
            self._messages.add(
                MessageLevel.WARNING,
                "No wells loaded",
                source="actions",
            )
            raise ValueError("No wells loaded")
        if self._state.facies_model is None:
            self._messages.add(
                MessageLevel.WARNING,
                "No facies model set",
                source="actions",
            )
            raise ValueError("No facies model set")

        for well in self._state.wells:
            log_name = self._state.well_facies_log_names.get(well.name, "")
            try:
                self.compute_accommodation(
                    well_name=well.name,
                    facies_log_name=log_name,
                )
                computed = dict(self._state.well_accommodation_computed)
                computed[well.name] = True
                self._state.well_accommodation_computed = computed
            except Exception:
                pass  # error already logged by compute_accommodation

    async def compute_all_accommodation_async(self) -> None:
        """Async version: compute accommodation in parallel.

        Uses ProcessPoolExecutor for true parallelism.
        Falls back to sequential if pickling fails.
        """
        if not self._state.wells:
            self._messages.add(
                MessageLevel.WARNING,
                "No wells loaded",
                source="actions",
            )
            raise ValueError("No wells loaded")
        if self._state.facies_model is None:
            self._messages.add(
                MessageLevel.WARNING,
                "No facies model set",
                source="actions",
            )
            raise ValueError("No facies model set")

        facies_list = list(self._state.facies_model.faciesSet)
        tasks = []
        for well in self._state.wells:
            log_name = self._state.well_facies_log_names.get(well.name, "")
            tasks.append((well, facies_list, log_name))

        loop = asyncio.get_running_loop()
        try:
            with ProcessPoolExecutor() as executor:
                futures = [
                    loop.run_in_executor(
                        executor,
                        _compute_one_well,
                        well,
                        fl,
                        ln,
                    )
                    for well, fl, ln in tasks
                ]
                raw = await asyncio.gather(*futures, return_exceptions=True)
        except Exception:
            # Pickling failed — fall back to sequential
            self._messages.add(
                MessageLevel.INFO,
                "Parallel computation unavailable, running sequentially",
                source="actions",
            )
            self.compute_all_accommodation()
            return

        results = dict(self._state.accommodation_results)
        computed = dict(self._state.well_accommodation_computed)
        for item, (well, _, _) in zip(raw, tasks):
            if isinstance(item, Exception):
                self._messages.add(
                    MessageLevel.ERROR,
                    f"Failed to compute accommodation for '{well.name}': {item}",
                    source="actions",
                )
            else:
                name, calculator = item
                results[name] = calculator
                computed[name] = True
                self._messages.add(
                    MessageLevel.INFO,
                    f"Computed accommodation for well '{name}'",
                    source="actions",
                )
        self._state.accommodation_results = results
        self._state.well_accommodation_computed = computed

    def compute_accommodation(
        self,
        well_name: str,
        facies_log_name: str,
        from_marker_name: str | None = None,
        to_marker_name: str | None = None,
        accommodation_at_base: float = 0.0,
    ) -> None:
        well = next((w for w in self._state.wells if w.name == well_name), None)
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
            calculator.computeAccommodationCurve(
                faciesLogName=facies_log_name,
                fromMarker=from_marker,
                toMarker=to_marker,
                accommodationAtBase=accommodation_at_base,
            )
            results = dict(self._state.accommodation_results)
            results[well_name] = calculator
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

    def create_empty_accumulation_model(self) -> None:
        """Create a new empty accumulation model."""
        self._state.accumulation_model = AccumulationModel(name="New Model")
        self._messages.add(
            MessageLevel.INFO,
            "Created new empty accumulation model",
            source="actions",
        )

    def load_accumulation_model_from_bytes(
        self, data: bytes, filename: str = ""
    ) -> None:
        """Load an accumulation model from raw JSON bytes.

        Args:
            data: UTF-8 JSON bytes conforming to
                AccumulationModelData schema.
            filename: Original filename for logging.

        Raises:
            Exception: Any parse or schema error from pyWellSFM
                is re-raised after being logged.
        """
        try:
            obj = json.loads(data.decode("utf-8"))
            model = loadAccumulationModelFromJsonObj(obj)
            self._state.accumulation_model = model
            label = filename or "file"
            self._messages.add(
                MessageLevel.INFO,
                f"Loaded accumulation model from {label}",
                source="actions",
            )
        except Exception as e:
            self._messages.add(
                MessageLevel.ERROR,
                f"Failed to load accumulation model: {e}",
                source="actions",
            )
            raise

    def export_accumulation_model_as_json(self) -> dict:
        """Serialize the accumulation model to a dict.

        Returns:
            Dict conforming to AccumulationModelData schema.

        Raises:
            ValueError: If no accumulation model is currently set.
        """
        if self._state.accumulation_model is None:
            self._messages.add(
                MessageLevel.WARNING,
                "No accumulation model to export",
                source="actions",
            )
            raise ValueError("No accumulation model to export")
        return accumulationModelToJsonObj(self._state.accumulation_model)

    # --- Accumulation Model Elements ---

    def _get_accum_element_or_raise(self, element_name: str):
        """Get element from accumulation model or raise."""
        if self._state.accumulation_model is None:
            self._messages.add(
                MessageLevel.WARNING,
                "No accumulation model set",
                source="actions",
            )
            raise ValueError("No accumulation model set")
        elem = self._state.accumulation_model.getElementModel(element_name)
        if elem is None:
            self._messages.add(
                MessageLevel.WARNING,
                f"Element '{element_name}' not found",
                source="actions",
            )
            raise ValueError(f"Element '{element_name}' not found")
        return elem

    def add_accumulation_element(self, element_name: str) -> None:
        """Add a Gaussian element with defaults.

        Creates a new empty AccumulationModel first if none
        is set. Raises ValueError if element already exists.
        """
        if self._state.accumulation_model is None:
            self._state.accumulation_model = AccumulationModel(name="New Model")
        model = self._state.accumulation_model
        if model.getElementModel(element_name) is not None:
            self._messages.add(
                MessageLevel.WARNING,
                f"Element '{element_name}' already exists",
                source="actions",
            )
            raise ValueError(f"Element '{element_name}' already exists")
        elem = AccumulationModelElementGaussian(
            elementName=element_name,
            accumulationRate=100.0,
            std_dev_factor=0.2,
        )
        model.addElement(element_name, elem)
        self._state.accumulation_model = model
        self._messages.add(
            MessageLevel.INFO,
            f"Added element '{element_name}'",
            source="actions",
        )

    def remove_accumulation_element(self, element_name: str) -> None:
        """Remove an element from the accumulation model.

        Raises:
            ValueError: If no model is set or element not
                found.
        """
        self._get_accum_element_or_raise(element_name)
        self._state.accumulation_model.removeElement(element_name)
        self._state.accumulation_model = self._state.accumulation_model
        self._messages.add(
            MessageLevel.INFO,
            f"Removed element '{element_name}'",
            source="actions",
        )

    def update_accumulation_element_rate(self, element_name: str, rate: float) -> None:
        """Update the accumulation rate of an element.

        Raises:
            ValueError: If no model is set or element not
                found.
        """
        elem = self._get_accum_element_or_raise(element_name)
        elem.accumulationRate = rate
        self._state.accumulation_model = self._state.accumulation_model
        self._messages.add(
            MessageLevel.INFO,
            f"Updated rate for '{element_name}' to {rate}",
            source="actions",
        )

    def update_accumulation_element_stddev(
        self, element_name: str, stddev_factor: float
    ) -> None:
        """Update the stddev factor of a Gaussian element.

        Raises:
            ValueError: If no model is set, element not
                found, or element is not Gaussian type.
        """
        elem = self._get_accum_element_or_raise(element_name)
        if not isinstance(elem, AccumulationModelElementGaussian):
            self._messages.add(
                MessageLevel.WARNING,
                f"Element '{element_name}' is not Gaussian",
                source="actions",
            )
            raise ValueError(f"Element '{element_name}' is not Gaussian")
        elem.std_dev_factor = stddev_factor
        self._state.accumulation_model = self._state.accumulation_model
        self._messages.add(
            MessageLevel.INFO,
            f"Updated stddev for '{element_name}' to {stddev_factor}",
            source="actions",
        )

    def set_accumulation_element_type(self, element_name: str, model_type: str) -> None:
        """Replace element with a new type, preserving rate.

        Args:
            element_name: Name of the element to replace.
            model_type: One of ``"Gaussian"`` or
                ``"EnvironmentOptimum"``.

        Raises:
            ValueError: If element not found or model_type
                is not recognised.
        """
        elem = self._get_accum_element_or_raise(element_name)
        rate = elem.accumulationRate
        if model_type == "Gaussian":
            new_elem = AccumulationModelElementGaussian(
                elementName=element_name,
                accumulationRate=rate,
                std_dev_factor=0.2,
            )
        elif model_type == "EnvironmentOptimum":
            new_elem = AccumulationModelElementOptimum(
                elementName=element_name,
                accumulationRate=rate,
            )
        else:
            self._messages.add(
                MessageLevel.WARNING,
                f"Unknown model type '{model_type}'",
                source="actions",
            )
            raise ValueError(f"Unknown model type '{model_type}'")
        model = self._state.accumulation_model
        model.removeElement(element_name)
        model.addElement(element_name, new_elem)
        self._state.accumulation_model = model
        self._messages.add(
            MessageLevel.INFO,
            f"Set '{element_name}' type to {model_type}",
            source="actions",
        )

    # --- Accumulation Curves ---

    def _get_optimum_element_or_raise(
        self, element_name: str
    ) -> AccumulationModelElementOptimum:
        """Get element and verify it's EnvironmentOptimum."""
        elem = self._get_accum_element_or_raise(element_name)
        if not isinstance(elem, AccumulationModelElementOptimum):
            self._messages.add(
                MessageLevel.WARNING,
                f"Element '{element_name}' is not EnvironmentOptimum",
                source="actions",
            )
            raise ValueError(f"Element '{element_name}' is not EnvironmentOptimum")
        return elem

    def _get_curve_or_raise(
        self,
        element_name: str,
        env_factor_name: str,
    ) -> tuple[
        AccumulationModelElementOptimum,
        AccumulationCurve,
    ]:
        """Get optimum element and its curve."""
        elem = self._get_optimum_element_or_raise(element_name)
        curve = elem.getAccumulationCurve(env_factor_name)
        if curve is None:
            self._messages.add(
                MessageLevel.WARNING,
                f"Curve '{env_factor_name}' not found on element '{element_name}'",
                source="actions",
            )
            raise ValueError(
                f"Curve '{env_factor_name}' not found on element '{element_name}'"
            )
        return elem, curve

    def add_accumulation_curve(
        self,
        element_name: str,
        env_factor_name: str,
    ) -> None:
        """Add a reduction curve with default points."""
        elem = self._get_optimum_element_or_raise(element_name)
        if elem.getAccumulationCurve(env_factor_name) is not None:
            self._messages.add(
                MessageLevel.WARNING,
                f"Curve '{env_factor_name}' already exists on element '{element_name}'",
                source="actions",
            )
            raise ValueError(
                f"Curve '{env_factor_name}' already exists on element '{element_name}'"
            )
        curve = AccumulationCurve(
            envFactorName=env_factor_name,
            abscissa=np.array([0.0, 1.0]),
            ordinate=np.array([1.0, 1.0]),
        )
        elem.addAccumulationCurve(curve)
        self._state.accumulation_model = self._state.accumulation_model
        self._messages.add(
            MessageLevel.INFO,
            f"Added curve '{env_factor_name}' to element '{element_name}'",
            source="actions",
        )

    def add_accumulation_curve_from_data(
        self,
        element_name: str,
        env_factor_name: str,
        abscissa: np.ndarray,
        ordinate: np.ndarray,
    ) -> None:
        """Add a reduction curve with given data points."""
        elem = self._get_optimum_element_or_raise(element_name)
        if elem.getAccumulationCurve(env_factor_name) is not None:
            self._messages.add(
                MessageLevel.WARNING,
                f"Curve '{env_factor_name}' already exists on element '{element_name}'",
                source="actions",
            )
            raise ValueError(
                f"Curve '{env_factor_name}' already exists on element '{element_name}'"
            )
        curve = AccumulationCurve(
            envFactorName=env_factor_name,
            abscissa=abscissa,
            ordinate=ordinate,
        )
        elem.addAccumulationCurve(curve)
        self._state.accumulation_model = self._state.accumulation_model
        self._messages.add(
            MessageLevel.INFO,
            f"Added curve '{env_factor_name}' to element '{element_name}'",
            source="actions",
        )

    def set_accumulation_curve_data(
        self,
        element_name: str,
        env_factor_name: str,
        abscissa: np.ndarray,
        ordinate: np.ndarray,
    ) -> None:
        """Replace curve data points on an existing curve."""
        _, curve = self._get_curve_or_raise(element_name, env_factor_name)
        curve._abscissa = abscissa
        curve._ordinate = ordinate
        self._state.accumulation_model = self._state.accumulation_model
        self._messages.add(
            MessageLevel.INFO,
            f"Loaded data for curve '{env_factor_name}' on element '{element_name}'",
            source="actions",
        )

    def remove_accumulation_curve(
        self,
        element_name: str,
        env_factor_name: str,
    ) -> None:
        """Remove a reduction curve."""
        elem, _ = self._get_curve_or_raise(element_name, env_factor_name)
        elem.removeAccumulationCurve(env_factor_name)
        self._state.accumulation_model = self._state.accumulation_model
        self._messages.add(
            MessageLevel.INFO,
            f"Removed curve '{env_factor_name}' from element '{element_name}'",
            source="actions",
        )

    def add_accumulation_curve_point(
        self,
        element_name: str,
        env_factor_name: str,
        x: float,
        y: float,
    ) -> None:
        """Append a data point to a reduction curve."""
        _, curve = self._get_curve_or_raise(element_name, env_factor_name)
        curve._abscissa = np.append(curve._abscissa, x)
        curve._ordinate = np.append(curve._ordinate, y)
        self._state.accumulation_model = self._state.accumulation_model
        self._messages.add(
            MessageLevel.INFO,
            f"Added point ({x}, {y}) to curve '{env_factor_name}'",
            source="actions",
        )

    def remove_accumulation_curve_point(
        self,
        element_name: str,
        env_factor_name: str,
        index: int,
    ) -> None:
        """Remove a data point by index."""
        _, curve = self._get_curve_or_raise(element_name, env_factor_name)
        if index < 0 or index >= len(curve._abscissa):
            self._messages.add(
                MessageLevel.WARNING,
                f"Index {index} out of range",
                source="actions",
            )
            raise ValueError(f"Index {index} out of range")
        curve._abscissa = np.delete(curve._abscissa, index)
        curve._ordinate = np.delete(curve._ordinate, index)
        self._state.accumulation_model = self._state.accumulation_model
        self._messages.add(
            MessageLevel.INFO,
            f"Removed point {index} from curve '{env_factor_name}'",
            source="actions",
        )

    def update_accumulation_curve_point(
        self,
        element_name: str,
        env_factor_name: str,
        index: int,
        x: float,
        y: float,
    ) -> None:
        """Update a data point by index."""
        _, curve = self._get_curve_or_raise(element_name, env_factor_name)
        if index < 0 or index >= len(curve._abscissa):
            self._messages.add(
                MessageLevel.WARNING,
                f"Index {index} out of range",
                source="actions",
            )
            raise ValueError(f"Index {index} out of range")
        curve._abscissa[index] = x
        curve._ordinate[index] = y
        self._state.accumulation_model = self._state.accumulation_model
        self._messages.add(
            MessageLevel.INFO,
            f"Updated point {index} on curve '{env_factor_name}' to ({x}, {y})",
            source="actions",
        )

    # --- Eustatic Curve ---

    def set_eustatic_curve(self, curve: Curve) -> None:
        self._state.eustatic_curve = curve
        self._messages.add(MessageLevel.INFO, "Eustatic curve set", source="actions")

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

    def create_eustatic_curve(
        self,
        ages: npt.NDArray[np.float64],
        values: npt.NDArray[np.float64],
    ) -> None:
        curve = Curve("Age", "Eustatism", ages, values, "linear")
        self._state.eustatic_curve = curve
        self._messages.add(
            MessageLevel.INFO,
            f"Eustatic curve set with {len(ages)} points",
            source="actions",
        )

    def update_eustatic_curve_point(self, index: int, age: float, value: float) -> None:
        curve = self._state.eustatic_curve
        if curve is None:
            raise ValueError("No eustatic curve")
        if index < 0 or index >= len(curve._abscissa):
            raise ValueError(f"Index {index} out of range")
        curve._abscissa[index] = age
        curve._ordinate[index] = value
        self._state.eustatic_curve = self._state.eustatic_curve
        self._messages.add(
            MessageLevel.INFO,
            f"Updated eustatic point {index} to ({age}, {value})",
            source="actions",
        )

    def add_eustatic_curve_point(self, age: float, value: float) -> None:
        curve = self._state.eustatic_curve
        if curve is None:
            self.create_eustatic_curve(np.array([age]), np.array([value]))
            return
        curve.addSampledPoint(age, value)
        self._state.eustatic_curve = self._state.eustatic_curve
        self._messages.add(
            MessageLevel.INFO,
            f"Added eustatic point ({age}, {value})",
            source="actions",
        )

    def remove_eustatic_curve_point(self, index: int) -> None:
        curve = self._state.eustatic_curve
        if curve is None:
            raise ValueError("No eustatic curve")
        if index < 0 or index >= len(curve._abscissa):
            raise ValueError(f"Index {index} out of range")
        curve._abscissa = np.delete(curve._abscissa, index)
        curve._ordinate = np.delete(curve._ordinate, index)
        if len(curve._abscissa) == 0:
            self._state.eustatic_curve = None
            self._messages.add(
                MessageLevel.INFO,
                "Eustatic curve cleared (no points left)",
                source="actions",
            )
        else:
            self._state.eustatic_curve = self._state.eustatic_curve
            self._messages.add(
                MessageLevel.INFO,
                f"Removed eustatic point {index}",
                source="actions",
            )

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

    def set_depositional_env_model(self, model: DepositionalEnvironmentModel) -> None:
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

    def set_realization_data_list(
        self,
        data_list: list,
    ) -> None:
        self._state.realization_data_list = list(data_list)
        n = len(data_list)
        self._messages.add(
            MessageLevel.INFO,
            f"Realization data set for {n} well{'s' if n != 1 else ''}",
            source="actions",
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
            self._state.simulated_wells = simulator.simulatedWells
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

    def load_simulation_file(self, data: bytes) -> None:
        """Load a full simulation JSON file into state."""
        import tempfile

        try:
            with tempfile.NamedTemporaryFile(
                suffix=".json",
                delete=False,
                mode="wb",
            ) as f:
                f.write(data)
                tmp_path = f.name

            simulator = self._io.load_simulation(tmp_path)
            Path(tmp_path).unlink(missing_ok=True)

            sc = simulator.scenario
            self._state.accumulation_model = sc.accumulationModel
            self._state.eustatic_curve = sc.eustaticCurve
            self._state.depositional_env_model = sc.depositionalEnvironmentModel
            self._state.facies_model = sc.faciesModel
            rd_list = list(simulator.realizationDataList)
            self._state.realization_data_list = rd_list
            self._state.wells = [rd.well for rd in rd_list]
            self._state.simulator_params = simulator.params
            self._state.use_de_simulator = simulator.use_deSimulator
            if simulator.deSimulator_weights is not None:
                self._state.de_simulator_weights = dict(simulator.deSimulator_weights)
            if simulator.deSimulator_params is not None:
                self._state.de_simulator_params = simulator.deSimulator_params

            self._messages.add(
                MessageLevel.INFO,
                "Simulation file loaded",
                source="actions",
            )
        except Exception as e:
            self._messages.add(
                MessageLevel.ERROR,
                f"Failed to load simulation: {e}",
                source="actions",
            )
            raise

    def save_simulation_file(self) -> bytes:
        """Save current state as a simulation JSON file."""
        import tempfile

        if self._state.accumulation_model is None:
            raise ValueError("No accumulation model set")

        try:
            scenario = Scenario(
                name="simulation",
                accumulationModel=(self._state.accumulation_model),
                eustaticCurve=self._state.eustatic_curve,
                depositionalEnvironmentModel=(self._state.depositional_env_model),
                faciesModel=self._state.facies_model,
            )
            params = self._state.simulator_params or FSSimulatorParameters()
            use_de_sim = self._state.depositional_env_model is not None
            simulator = FSSimulator(
                scenario=scenario,
                realizationDataList=(self._state.realization_data_list),
                use_depositional_environment_simulator=(use_de_sim),
                deSimulator_weights=(self._state.de_simulator_weights or None),
                deSimulator_params=(self._state.de_simulator_params),
                fsSimulator_params=params,
            )

            with tempfile.NamedTemporaryFile(
                suffix=".json",
                delete=False,
                mode="r",
            ) as f:
                tmp_path = f.name

            self._io.save_simulation(
                simulator,
                tmp_path,
                name="simulation",
            )
            data = Path(tmp_path).read_bytes()
            Path(tmp_path).unlink(missing_ok=True)

            self._messages.add(
                MessageLevel.INFO,
                "Simulation file saved",
                source="actions",
            )
            return data
        except Exception as e:
            self._messages.add(
                MessageLevel.ERROR,
                f"Failed to save simulation: {e}",
                source="actions",
            )
            raise

    def clear_simulation_outputs(self) -> None:
        self._state.simulation_outputs = None
        self._messages.add(
            MessageLevel.INFO, "Simulation outputs cleared", source="actions"
        )

    # --- Depositional Environment: Mode ---

    def set_use_de_simulator(self, enabled: bool) -> None:
        """Toggle between global and multi-environment mode."""
        self._state.use_de_simulator = enabled
        if enabled:
            self._state.global_env_conditions = None
            if self._state.depositional_env_model is None:
                self._state.depositional_env_model = DepositionalEnvironmentModel(
                    name="New Model",
                    environments=[],
                )
        else:
            self._state.depositional_env_model = None
            self._state.de_simulator_weights = {}
            self._state.de_simulator_params = None
        self._messages.add(
            MessageLevel.INFO,
            "DE simulator " + ("enabled" if enabled else "disabled"),
            source="actions",
        )

    # --- Depositional Environment: Model Management ---

    _DE_TEMPLATES: dict[str, type | None] = {
        "empty": None,
        "carbonate_open_ramp": (CarbonateOpenRampDepositionalEnvironmentModel),
        "carbonate_protected_ramp": (
            CarbonateProtectedRampDepositionalEnvironmentModel
        ),
    }

    def create_de_model(self, template: str) -> None:
        """Create a new DE model from a template name."""
        cls = self._DE_TEMPLATES.get(template)
        if cls is None and template != "empty":
            msg = f"Unknown DE template: {template!r}"
            self._messages.add(
                MessageLevel.ERROR,
                msg,
                source="actions",
            )
            raise ValueError(msg)
        if template == "empty":
            model = DepositionalEnvironmentModel(
                name="New Model",
                environments=[],
            )
        else:
            model = cls()
        self._state.depositional_env_model = model
        self._state.de_simulator_weights = {env.name: 1.0 for env in model.environments}
        self._state.de_simulator_params = None
        self._messages.add(
            MessageLevel.INFO,
            f"Created DE model: {model.name}",
            source="actions",
        )

    def load_de_simulation_from_bytes(
        self,
        data: bytes,
        filename: str,
    ) -> None:
        """Load a DE simulation from raw JSON bytes."""
        try:
            obj = json.loads(data)
            sim = self._io.load_de_simulation_from_json_obj(obj)
            self._state.depositional_env_model = sim.depositionalEnvironmentModel
            self._state.de_simulator_weights = dict(sim._weights)
            self._state.de_simulator_params = sim.params
            self._messages.add(
                MessageLevel.INFO,
                f"Loaded DE simulation from {filename}",
                source="actions",
            )
        except Exception as exc:
            self._messages.add(
                MessageLevel.ERROR,
                f"Failed to load DE simulation: {exc}",
                source="actions",
            )
            raise

    def export_de_simulation_as_json(self) -> dict:
        """Export the current DE model as a DESimulation JSON dict."""
        model = self._state.depositional_env_model
        if model is None:
            msg = "No DE model to export"
            self._messages.add(
                MessageLevel.ERROR,
                msg,
                source="actions",
            )
            raise ValueError(msg)
        simulator = DepositionalEnvironmentSimulator(
            depositionalEnvironmentModel=model,
            weights=self._state.de_simulator_weights or None,
            params=self._state.de_simulator_params,
        )
        return self._io.export_de_simulation_to_json_obj(
            simulator,
        )

    # --- Depositional Environment: Global Conditions ---

    def load_global_env_conditions_from_bytes(
        self,
        data: bytes,
        filename: str,
    ) -> None:
        """Load global env conditions from JSON bytes."""
        try:
            obj = json.loads(data)
            model = self._io.load_env_conditions_from_json_obj(
                obj,
            )
            self._state.global_env_conditions = model
            self._messages.add(
                MessageLevel.INFO,
                f"Loaded environment conditions from {filename}",
                source="actions",
            )
        except Exception as exc:
            self._messages.add(
                MessageLevel.ERROR,
                f"Failed to load env conditions: {exc}",
                source="actions",
            )
            raise

    def export_global_env_conditions_as_json(self) -> dict:
        """Export global env conditions as JSON dict."""
        model = self._state.global_env_conditions
        if model is None:
            msg = "No global environment conditions to export"
            self._messages.add(
                MessageLevel.ERROR,
                msg,
                source="actions",
            )
            raise ValueError(msg)
        return self._io.export_env_conditions_to_json_obj(model)

    # --- Depositional Environment: CRUD ---

    def _get_de_model(self) -> DepositionalEnvironmentModel:
        """Get the DE model, raising if None."""
        model = self._state.depositional_env_model
        if model is None:
            raise ValueError("No depositional environment model")
        return model

    def _notify_de_model_changed(self) -> None:
        """Trigger param watchers after in-place mutation."""
        self._state.param.trigger("depositional_env_model")

    def add_environment(self, name: str) -> None:
        """Add a new environment with default Uniform waterDepth."""
        model = self._get_de_model()
        if model.environmentExists(name):
            msg = f"Environment '{name}' already exists"
            self._messages.add(
                MessageLevel.ERROR,
                msg,
                source="actions",
            )
            raise ValueError(msg)
        env = DepositionalEnvironment(
            name=name,
            distality=0.0,
            waterDepthModel=EnvironmentConditionModelUniform(
                "waterDepth",
                0.0,
                100.0,
            ),
        )
        model.addEnvironment(env)
        weights = dict(self._state.de_simulator_weights)
        weights[name] = 1.0
        self._state.de_simulator_weights = weights
        self._notify_de_model_changed()

    def remove_environment(self, name: str) -> None:
        """Remove an environment by name."""
        model = self._get_de_model()
        model.removeEnvironment(name)
        weights = dict(self._state.de_simulator_weights)
        weights.pop(name, None)
        self._state.de_simulator_weights = weights
        self._notify_de_model_changed()

    def rename_environment(
        self,
        old_name: str,
        new_name: str,
    ) -> None:
        """Rename an environment."""
        model = self._get_de_model()
        env = model.getEnvironmentByName(old_name)
        if env is None:
            msg = f"Environment '{old_name}' not found"
            self._messages.add(
                MessageLevel.ERROR,
                msg,
                source="actions",
            )
            raise ValueError(msg)
        if model.environmentExists(new_name):
            msg = f"Environment '{new_name}' already exists"
            self._messages.add(
                MessageLevel.ERROR,
                msg,
                source="actions",
            )
            raise ValueError(msg)
        env.name = new_name
        weights = dict(self._state.de_simulator_weights)
        w = weights.pop(old_name, 1.0)
        weights[new_name] = w
        self._state.de_simulator_weights = weights
        self._notify_de_model_changed()

    # --- Depositional Environment: Properties ---

    def set_environment_distality(
        self,
        env_name: str,
        value: float | None,
    ) -> None:
        """Set the distality of an environment."""
        model = self._get_de_model()
        env = model.getEnvironmentByName(env_name)
        if env is None:
            raise ValueError(f"Environment '{env_name}' not found")
        env.distality = value
        self._notify_de_model_changed()

    _WATER_DEPTH_MODEL_FACTORIES = {
        "Constant": lambda p: EnvironmentConditionModelConstant(
            "waterDepth",
            p["value"],
        ),
        "Uniform": lambda p: EnvironmentConditionModelUniform(
            "waterDepth",
            p["minValue"],
            p["maxValue"],
        ),
        "Triangular": lambda p: EnvironmentConditionModelTriangular(
            "waterDepth",
            p["modeValue"],
            p["minValue"],
            p["maxValue"],
        ),
        "Gaussian": lambda p: EnvironmentConditionModelGaussian(
            "waterDepth",
            p["meanValue"],
            p.get("stdDev"),
            p.get("minValue", float("-inf")),
            p.get("maxValue", float("inf")),
        ),
    }

    def set_environment_water_depth_model(
        self,
        env_name: str,
        model_type: str,
        **params,
    ) -> None:
        """Set the waterDepth model for an environment."""
        model = self._get_de_model()
        env = model.getEnvironmentByName(env_name)
        if env is None:
            raise ValueError(f"Environment '{env_name}' not found")
        factory = self._WATER_DEPTH_MODEL_FACTORIES.get(
            model_type,
        )
        if factory is None:
            raise ValueError(f"Unknown model type: {model_type!r}")
        env.waterDepthModel = factory(params)
        self._notify_de_model_changed()

    # --- Depositional Environment: Conditions ---

    _CONDITION_MODEL_FACTORIES = {
        "Constant": lambda name, p: EnvironmentConditionModelConstant(name, p["value"]),
        "Uniform": lambda name, p: EnvironmentConditionModelUniform(
            name,
            p["minValue"],
            p["maxValue"],
        ),
        "Triangular": lambda name, p: EnvironmentConditionModelTriangular(
            name,
            p["modeValue"],
            p["minValue"],
            p["maxValue"],
        ),
        "Gaussian": lambda name, p: EnvironmentConditionModelGaussian(
            name,
            p["meanValue"],
            p.get("stdDev"),
            p.get("minValue", float("-inf")),
            p.get("maxValue", float("inf")),
        ),
        "Curve": lambda name, p: EnvironmentConditionModelCurve(
            name,
            p["curve"],
        ),
    }

    def _build_condition_model(
        self,
        cond_name: str,
        model_type: str,
        params: dict,
    ):
        """Build an EnvironmentConditionModel from type + params."""
        factory = self._CONDITION_MODEL_FACTORIES.get(model_type)
        if factory is None:
            raise ValueError(f"Unknown condition model type: {model_type!r}")
        return factory(cond_name, params)

    def _get_env_conditions_model(
        self,
        env_name: str,
    ) -> EnvironmentConditionsModel:
        """Get the EnvironmentConditionsModel for an env name.

        For 'global', uses global_env_conditions (creating if
        needed). Otherwise looks up the environment in the DE
        model.
        """
        if env_name == "global":
            if self._state.global_env_conditions is None:
                self._state.global_env_conditions = EnvironmentConditionsModel()
            return self._state.global_env_conditions
        model = self._get_de_model()
        env = model.getEnvironmentByName(env_name)
        if env is None:
            raise ValueError(f"Environment '{env_name}' not found")
        return env.envConditionsModel

    def add_env_condition(
        self,
        env_name: str,
        cond_name: str,
        model_type: str,
        **params,
    ) -> None:
        """Add an environment condition to an environment."""
        cond_model = self._build_condition_model(
            cond_name,
            model_type,
            params,
        )
        ecm = self._get_env_conditions_model(env_name)
        ecm.addEnvironmentConditionModel(cond_name, cond_model)
        if env_name == "global":
            self._state.param.trigger("global_env_conditions")
        else:
            self._notify_de_model_changed()

    def update_env_condition(
        self,
        env_name: str,
        cond_name: str,
        model_type: str,
        **params,
    ) -> None:
        """Update an existing environment condition."""
        cond_model = self._build_condition_model(
            cond_name,
            model_type,
            params,
        )
        ecm = self._get_env_conditions_model(env_name)
        ecm.addEnvironmentConditionModel(cond_name, cond_model)
        if env_name == "global":
            self._state.param.trigger("global_env_conditions")
        else:
            self._notify_de_model_changed()

    def remove_env_condition(
        self,
        env_name: str,
        cond_name: str,
    ) -> None:
        """Remove an environment condition."""
        ecm = self._get_env_conditions_model(env_name)
        ecm.removeEnvironmentConditionModel(cond_name)
        if env_name == "global":
            self._state.param.trigger("global_env_conditions")
        else:
            self._notify_de_model_changed()

    # --- DE Simulator Settings ---

    def set_de_simulator_weight(
        self,
        env_name: str,
        weight: float,
    ) -> None:
        """Set the prior weight for an environment."""
        if weight <= 0:
            msg = "Weight must be > 0"
            self._messages.add(
                MessageLevel.ERROR,
                msg,
                source="actions",
            )
            raise ValueError(msg)
        weights = dict(self._state.de_simulator_weights)
        weights[env_name] = weight
        self._state.de_simulator_weights = weights

    def set_de_simulator_params(self, **params) -> None:
        """Set DE simulator parameters from keyword args."""
        self._state.de_simulator_params = DESimulatorParameters(
            **params,
        )
