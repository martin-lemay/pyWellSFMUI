import logging

import panel as pn

from pywellsfmui.state.app_state import AppState
from pywellsfmui.state.actions import Actions
from pywellsfmui.state.io_manager import IOManager
from pywellsfmui.state.message_store import MessageStore
from pywellsfmui.views.well_analysis import WellAnalysisView
from pywellsfmui.views.simulation import SimulationView
from pywellsfmui.views.visualization import VisualizationView
from pywellsfmui.views.log_panel import LogPanel

pn.extension("plotly", sizing_mode="stretch_width")


def create_app() -> pn.Column:
    state = AppState()
    io_manager = IOManager()
    message_store = MessageStore()
    actions = Actions(state=state, io_manager=io_manager, message_store=message_store)

    logging.getLogger("pywellsfm").addHandler(message_store.as_logging_handler())

    well_analysis = WellAnalysisView(state=state, actions=actions)
    simulation = SimulationView(state=state, actions=actions)
    visualization = VisualizationView(state=state, actions=actions)
    log_panel = LogPanel(message_store=message_store)

    tabs = pn.Tabs(
        ("Well Data Analysis", well_analysis.panel()),
        ("Simulation", simulation.panel()),
        ("Visualization", visualization.panel()),
        sizing_mode="stretch_both",
    )

    return pn.Column(tabs, log_panel.panel(), sizing_mode="stretch_both")


if __name__.startswith("bokeh") or __name__ == "__main__":
    app = create_app()
    app.servable()
