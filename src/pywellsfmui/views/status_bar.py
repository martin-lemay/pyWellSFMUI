import panel as pn
import param

from pywellsfmui.state.app_state import AppState
from pywellsfmui.theme import Colors


class StatusBar(param.Parameterized):
    """Reactive status badges for the header bar."""

    def __init__(self, state: AppState, **params) -> None:
        super().__init__(**params)
        self._state = state

    def _render_badges(self) -> str:
        facies_text = "loaded" if self._state.facies_model is not None else "--"
        facies_color = (
            Colors.SUCCESS if self._state.facies_model is not None else Colors.INACTIVE
        )

        well_count = len(self._state.wells)
        wells_text = str(well_count)
        wells_color = Colors.SUCCESS if well_count > 0 else Colors.INACTIVE

        sim_text = "done" if self._state.simulation_outputs is not None else "--"
        sim_color = (
            Colors.SUCCESS
            if self._state.simulation_outputs is not None
            else Colors.INACTIVE
        )

        badges = [
            ("Facies", facies_text, facies_color),
            ("Wells", wells_text, wells_color),
            ("Simulation", sim_text, sim_color),
        ]

        spans = []
        for label, value, color in badges:
            spans.append(
                f'<span style="font-family:monospace; font-size:0.8em; margin-left:12px;">'
                f'<span style="color:{color};">&#9679;</span> '
                f"{label}: {value}</span>"
            )
        return "".join(spans)

    @param.depends(
        "_state.facies_model",
        "_state.wells",
        "_state.simulation_outputs",
        watch=False,
    )
    def _badges_pane(self) -> pn.pane.HTML:
        return pn.pane.HTML(
            self._render_badges(),
            sizing_mode="fixed",
            styles={"color": "white", "display": "flex", "align-items": "center"},
        )

    def panel(self) -> pn.Row:
        return pn.Row(
            self._badges_pane,
            sizing_mode="stretch_width",
            styles={"justify-content": "flex-end"},
        )
