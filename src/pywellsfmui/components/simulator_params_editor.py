"""Simulator parameters editor component.

Exposes FSSimulatorParameters fields as numeric inputs with
defaults matching the pyWellSFM dataclass.
"""

from __future__ import annotations

from typing import Any

import panel as pn
import param
from pywellsfm.model import FSSimulatorParameters

from pywellsfmui.state.actions import Actions
from pywellsfmui.state.app_state import AppState


class SimulatorParamsEditor(param.Parameterized):
    """Editor for FSSimulatorParameters.

    Args:
        state: Central application state.
        actions: Command layer used to mutate state.
    """

    def __init__(
        self,
        state: AppState,
        actions: Actions,
        **params: Any,
    ) -> None:
        """Initialize the simulator parameters editor."""
        super().__init__(**params)
        self._state = state
        self._actions = actions
        self._updating = False

        defaults = FSSimulatorParameters()

        self._max_wd_change = pn.widgets.FloatInput(
            label="Max Water-Depth Change / Step (m)",
            value=defaults.max_waterDepth_change_per_step,
            start=0.0,
            step=0.1,
            width=250,
        )
        self._dt_min = pn.widgets.FloatInput(
            label="Min Time Step (Myr)",
            value=defaults.dt_min,
            start=0.0,
            step=1e-4,
            format="0.0000",
            width=250,
        )
        self._dt_max = pn.widgets.FloatInput(
            label="Max Time Step (Myr)",
            value=defaults.dt_max,
            start=0.0,
            step=0.01,
            width=250,
        )
        self._safety = pn.widgets.FloatInput(
            label="Safety Factor",
            value=defaults.safety,
            start=0.0,
            end=1.0,
            step=0.05,
            width=250,
        )
        self._max_steps = pn.widgets.IntInput(
            label="Max Steps",
            value=defaults.max_steps,
            start=1,
            step=1000,
            width=250,
        )

        for w in self._all_widgets():
            w.param.watch(self._on_value_changed, "value")

        self._push_params()

        self._state.param.watch(self._on_state_changed, ["simulator_params"])

    def _all_widgets(self) -> list:
        return [
            self._max_wd_change,
            self._dt_min,
            self._dt_max,
            self._safety,
            self._max_steps,
        ]

    def _build_params(self) -> FSSimulatorParameters:
        return FSSimulatorParameters(
            max_waterDepth_change_per_step=self._max_wd_change.value,
            dt_min=self._dt_min.value,
            dt_max=self._dt_max.value,
            safety=self._safety.value,
            max_steps=self._max_steps.value,
        )

    def _push_params(self) -> None:
        self._actions.set_simulator_params(self._build_params())

    def _on_value_changed(self, event: Any) -> None:
        if self._updating:
            return
        self._push_params()

    def _on_state_changed(self, event: Any) -> None:
        p = event.new
        if p is None:
            return
        self._updating = True
        self._max_wd_change.value = p.max_waterDepth_change_per_step
        self._dt_min.value = p.dt_min
        self._dt_max.value = p.dt_max
        self._safety.value = p.safety
        self._max_steps.value = p.max_steps
        self._updating = False

    def panel(self) -> pn.Card:
        """Return the Panel layout for this editor."""
        fields = pn.Row(
            self._max_wd_change,
            self._dt_min,
            self._dt_max,
            self._safety,
            self._max_steps,
            sizing_mode="stretch_width",
        )

        return pn.Card(
            fields,
            title="Advanced Simulation Parameters",
            collapsed=True,
            sizing_mode="stretch_width",
            stylesheets=[
                """:host {
                    --panel-card-header-justify: start;
                }""",
            ],
            margin=(5, 0),
        )
