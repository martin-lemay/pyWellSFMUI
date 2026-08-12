import asyncio
import io
import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

import panel as pn
import param

from pywellsfmui.components.accumulation_editor import (
    AccumulationEditor,
)
from pywellsfmui.components.eustatic_curve_editor import (
    EustaticCurveEditor,
)
from pywellsfmui.components.facies_editor import (
    FaciesEditor,
)
from pywellsfmui.components.depositional_env_editor import (
    DepositionalEnvEditor,
)
from pywellsfmui.components.realization_data_editor import (
    RealizationDataEditor,
)
from pywellsfmui.components.simulator_params_editor import (
    SimulatorParamsEditor,
)
from pywellsfmui.state.actions import Actions
from pywellsfmui.state.app_state import AppState
from pywellsfmui.theme import Colors, status_html

logger = logging.getLogger(__name__)

_EXECUTOR = ThreadPoolExecutor(max_workers=1)


class SimulationView(param.Parameterized):
    """Tab 2: Simulation Parameterization.

    Allows defining accumulation model, eustatic curve,
    depositional environments, realization data, and
    running the simulation.
    """

    def __init__(
        self,
        state: AppState,
        actions: Actions,
        on_navigate: Callable[[str], None] | None = None,
        on_expand_log: Callable[[], None] | None = None,
        **params,
    ) -> None:
        super().__init__(**params)
        self._state = state
        self._actions = actions
        self._on_navigate = on_navigate
        self._on_expand_log = on_expand_log
        self._facies_editor = FaciesEditor(
            state=state,
            actions=actions,
        )
        self._accumulation_editor = AccumulationEditor(
            state=state,
            actions=actions,
        )
        self._eustatic_editor = EustaticCurveEditor(
            state=state,
            actions=actions,
        )
        self._de_editor = DepositionalEnvEditor(
            state=state,
            actions=actions,
        )
        self._realization_editor = RealizationDataEditor(
            state=state,
            actions=actions,
        )
        self._params_editor = SimulatorParamsEditor(
            state=state,
            actions=actions,
        )

        # Load / Save simulation file
        self._load_input = pn.widgets.FileInput(
            accept=".json",
            width=250,
            align="center",
        )
        self._save_btn = pn.widgets.FileDownload(
            callback=self._make_save_download,
            filename="simulation.json",
            label="Save Simulation File",
            color="success",
            width=180,
            align="center",
        )
        self._load_input.param.watch(
            self._on_simulation_file_loaded,
            "value",
        )

        self._run_btn = pn.widgets.Button(
            label="Run Simulation",
            color="primary",
            sizing_mode="stretch_width",
            disabled=True,
        )
        self._spinner = pn.indicators.LoadingSpinner(
            value=True,
            size=25,
            visible=False,
        )
        self._status_label = pn.pane.Markdown(
            "",
            width=300,
        )
        self._run_status = pn.pane.HTML(
            self._build_run_status(),
            sizing_mode="fixed",
        )
        self._run_btn.on_click(
            lambda event: asyncio.ensure_future(self._on_run_clicked(event)),
        )

        self._state.param.watch(
            lambda event: self._update_run_readiness(),
            [
                "accumulation_model",
                "realization_data_list",
            ],
        )
        self._update_run_readiness()

    def _on_simulation_file_loaded(
        self,
        event: param.parameterized.Event,
    ) -> None:
        if self._load_input.value is None:
            return
        try:
            self._actions.load_simulation_file(
                self._load_input.value,
            )
        except Exception:
            logger.debug("Load simulation file failed", exc_info=True)
        finally:
            self._load_input.value = None  # type: ignore[assignment]

    def _make_save_download(self) -> io.BytesIO:
        try:
            data = self._actions.save_simulation_file()
            return io.BytesIO(data)
        except Exception:
            logger.debug("Save simulation failed", exc_info=True)
            return io.BytesIO(b"")

    def _is_run_ready(self) -> bool:
        return self._state.accumulation_model is not None and bool(
            self._state.realization_data_list
        )

    def _build_run_status(self) -> str:
        if self._is_run_ready():
            return status_html("Ready", Colors.SUCCESS)
        return status_html("Invalid inputs", Colors.ERROR)

    def _update_run_readiness(self) -> None:
        self._run_btn.disabled = not self._is_run_ready()
        self._run_status.object = self._build_run_status()

    async def _on_run_clicked(self, event: object) -> None:
        """Handle Run Simulation click."""
        self._run_btn.disabled = True
        self._spinner.visible = True
        self._status_label.object = "*Running simulation...*"
        if self._on_expand_log is not None:
            self._on_expand_log()
        # TODO: Phase 2 — Add progress_callback to
        # FSSimulator.run() in pyWellSFM, then update
        # _status_label with the current age in real time
        # (e.g., "Simulating age 45.2 / 100.0 Ma...").
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                _EXECUTOR,
                self._actions.run_simulation,
            )
            self._status_label.object = ""
            if self._on_navigate is not None:
                self._on_navigate("visualization")
        except Exception:
            logger.debug("Simulation run failed", exc_info=True)
            self._status_label.object = ""
        finally:
            self._spinner.visible = False
            self._update_run_readiness()

    def panel(self) -> pn.Column:
        """Render the Simulation Parameterization tab."""
        card_css = """:host {
            --panel-card-header-justify: start;
        }
        :host .card-header {
            justify-content: start !important;
        }"""
        run_status_row = pn.Row(
            self._spinner,
            self._status_label,
            pn.Spacer(),
            self._run_status,
            sizing_mode="stretch_width",
            align="center",
        )
        load_save_row = pn.Row(
            self._load_input,
            self._save_btn,
            sizing_mode="stretch_width",
            align="center",
        )
        eustatic_card = pn.Card(
            self._eustatic_editor.panel(),
            title="Step 2 [Optional] Eustatism",
            collapsed=True,
            sizing_mode="stretch_width",
            stylesheets=[card_css],
            margin=(5, 0),
        )
        facies_card = pn.Card(
            self._facies_editor.panel(),
            title="Step 5 [Optional] Facies Model",
            collapsed=True,
            sizing_mode="stretch_width",
            stylesheets=[card_css],
            margin=(5, 0),
        )
        return pn.Column(
            pn.pane.Markdown(
                "## Simulation Parameterization",
            ),
            load_save_row,
            self._accumulation_editor.panel(),
            eustatic_card,
            self._de_editor.panel(),
            self._realization_editor.panel(),
            facies_card,
            self._params_editor.panel(),
            self._run_btn,
            run_status_row,
            sizing_mode="stretch_both",
        )
