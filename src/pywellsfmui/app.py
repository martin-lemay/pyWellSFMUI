import panel as pn

from pywellsfmui.state.app_state import AppState
from pywellsfmui.state.actions import Actions
from pywellsfmui.state.io_manager import IOManager
from pywellsfmui.views.well_analysis import WellAnalysisView
from pywellsfmui.views.simulation import SimulationView
from pywellsfmui.views.visualization import VisualizationView

pn.extension("plotly", sizing_mode="stretch_width")


def create_app() -> pn.Tabs:
    state = AppState()
    io_manager = IOManager()
    actions = Actions(state=state, io_manager=io_manager)

    well_analysis = WellAnalysisView(state=state, actions=actions)
    simulation = SimulationView(state=state, actions=actions)
    visualization = VisualizationView(state=state, actions=actions)

    tabs = pn.Tabs(
        ("Well Data Analysis", well_analysis.panel()),
        ("Simulation", simulation.panel()),
        ("Visualization", visualization.panel()),
        sizing_mode="stretch_both",
    )

    return tabs


if __name__.startswith("bokeh") or __name__ == "__main__":
    app = create_app()
    app.servable()
