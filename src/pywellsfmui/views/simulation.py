import panel as pn
import param

from pywellsfmui.state.app_state import AppState
from pywellsfmui.state.actions import Actions


class SimulationView(param.Parameterized):
    """Tab 2: Simulation Parameterization.

    Allows defining accumulation model, eustatic curve, depositional
    environments, realization data, and running the simulation.
    """

    def __init__(self, state: AppState, actions: Actions, **params) -> None:
        super().__init__(**params)
        self._state = state
        self._actions = actions

    def _input_panel(self) -> pn.Column:
        return pn.Column(
            pn.pane.Markdown("## Simulation Parameterization"),
            pn.pane.Markdown("*Facies Model (shared) — coming soon*"),
            pn.pane.Markdown("*Accumulation Model editor — coming soon*"),
            pn.pane.Markdown("*Eustatic Curve editor — coming soon*"),
            pn.pane.Markdown("*Depositional Environment editor — coming soon*"),
            pn.pane.Markdown("*Realization Data — coming soon*"),
            pn.pane.Markdown("*Simulator Parameters — coming soon*"),
        )

    def _preview_panel(self) -> pn.Column:
        return pn.Column(
            pn.pane.Markdown("## Input Previews"),
            pn.pane.Markdown("*Eustatic curve plot — coming soon*"),
            pn.pane.Markdown("*Subsidence curves plot — coming soon*"),
            pn.pane.Markdown("*Accumulation curves plot — coming soon*"),
        )

    def panel(self) -> pn.Row:
        return pn.Row(
            self._input_panel(),
            self._preview_panel(),
            sizing_mode="stretch_both",
        )
