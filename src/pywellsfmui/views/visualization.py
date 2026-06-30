import panel as pn
import param

from pywellsfmui.state.app_state import AppState
from pywellsfmui.state.actions import Actions


class VisualizationView(param.Parameterized):
    """Tab 3: Result Visualization.

    Displays simulation outputs (xarray.Dataset) as interactive Plotly plots.
    """

    def __init__(self, state: AppState, actions: Actions, **params) -> None:
        super().__init__(**params)
        self._state = state
        self._actions = actions

    @param.depends("_state.simulation_outputs")
    def _results_panel(self) -> pn.Column:
        if self._state.simulation_outputs is None:
            return pn.Column(
                pn.pane.Markdown("## Results"),
                pn.pane.Markdown("*No simulation results yet. Run a simulation in the Simulation tab.*"),
            )

        return pn.Column(
            pn.pane.Markdown("## Results"),
            pn.pane.Markdown("*Sea level / basement / thickness plots — coming soon*"),
            pn.pane.Markdown("*Deposition rates plots — coming soon*"),
            pn.pane.Markdown("*Water depth plot — coming soon*"),
            pn.pane.Markdown("*Environment plot — coming soon*"),
        )

    def panel(self) -> pn.Column:
        return pn.Column(
            self._results_panel,
            sizing_mode="stretch_both",
        )
