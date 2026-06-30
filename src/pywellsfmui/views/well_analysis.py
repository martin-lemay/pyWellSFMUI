import panel as pn
import param

from pywellsfmui.state.app_state import AppState
from pywellsfmui.state.actions import Actions


class WellAnalysisView(param.Parameterized):
    """Tab 1: Well Data Analysis.

    Allows loading wells, setting facies model, and computing
    accommodation curves via AccommodationSpaceWellCalculator.
    """

    def __init__(self, state: AppState, actions: Actions, **params) -> None:
        super().__init__(**params)
        self._state = state
        self._actions = actions

    def _input_panel(self) -> pn.Column:
        return pn.Column(
            pn.pane.Markdown("## Well Data Analysis"),
            pn.pane.Markdown("*Facies Model editor — coming soon*"),
            pn.pane.Markdown("*Well import — coming soon*"),
            pn.pane.Markdown("*Accommodation computation — coming soon*"),
        )

    def _output_panel(self) -> pn.Column:
        return pn.Column(
            pn.pane.Markdown("## Results"),
            pn.pane.Markdown("*Water depth & accommodation curves — coming soon*"),
        )

    def panel(self) -> pn.Row:
        return pn.Row(
            self._input_panel(),
            self._output_panel(),
            sizing_mode="stretch_both",
        )
