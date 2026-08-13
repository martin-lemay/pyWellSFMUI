# src/pywellsfmui/app.py
import logging
from typing import Any

import panel as pn

from pywellsfmui.state.actions import Actions
from pywellsfmui.state.app_state import AppState
from pywellsfmui.state.io_manager import IOManager
from pywellsfmui.state.message_store import MessageStore
from pywellsfmui.theme import Colors
from pywellsfmui.views.log_panel import LogPanel
from pywellsfmui.views.simulation import SimulationView
from pywellsfmui.views.status_bar import StatusBar
from pywellsfmui.views.visualization import VisualizationView
from pywellsfmui.views.well_analysis import WellAnalysisView

pn.extension("plotly", "tabulator", sizing_mode="stretch_width")

_NAV_ITEMS = [
    ("Well Data Analysis", "well_analysis"),
    ("Simulation", "simulation"),
    ("Visualization", "visualization"),
]


def create_app() -> pn.template.FastListTemplate:
    """Assemble and return the main application template."""
    state = AppState()
    io_manager = IOManager()
    message_store = MessageStore()
    actions = Actions(
        state=state,
        io_manager=io_manager,
        message_store=message_store,
    )

    logging.getLogger("pywellsfm").addHandler(
        message_store.as_logging_handler()
    )

    # Main content area — holds the active view
    main_area = pn.Column(
        sizing_mode="stretch_both",
    )

    # Navigation buttons
    nav_buttons: list[pn.widgets.Button] = []
    for label, _key in _NAV_ITEMS:
        btn = pn.widgets.Button(
            label=label,
            color="light",
            width=200,
        )
        nav_buttons.append(btn)
    nav_buttons[0].color = "primary"

    def navigate_to(tab_key: str) -> None:
        """Switch the active view and update sidebar highlight."""
        key_index = {k: i for i, (_, k) in enumerate(_NAV_ITEMS)}
        idx = key_index[tab_key]
        main_area.objects = [views[tab_key].panel()]
        for i, b in enumerate(nav_buttons):
            b.color = "primary" if i == idx else "light"

    log_panel = LogPanel(message_store=message_store)

    views: dict[str, Any] = {
        "well_analysis": WellAnalysisView(
            state=state,
            actions=actions,
        ),
        "simulation": SimulationView(
            state=state,
            actions=actions,
            on_navigate=navigate_to,
            on_expand_log=log_panel.expand,
        ),
        "visualization": VisualizationView(
            state=state,
            actions=actions,
        ),
    }

    # Set initial view
    main_area.objects = [views["well_analysis"].panel()]

    for (_, key), btn in zip(_NAV_ITEMS, nav_buttons, strict=False):
        btn.on_click(lambda event, k=key: navigate_to(k))

    status_bar = StatusBar(state=state)

    # Template
    template = pn.template.FastListTemplate(
        title="pyWellSFM",
        accent_base_color=Colors.ACCENT,
        header_background=Colors.ACCENT,
        sidebar_width=220,
        theme="default",
        main_layout=None,
    )

    # Sidebar
    assert template.sidebar is not None
    template.sidebar.append(
        pn.Column(*nav_buttons, sizing_mode="stretch_width")
    )

    # Header — status badges
    assert template.header is not None
    template.header.append(status_bar.panel())

    # Main — single column: view fills space, log panel at bottom
    content = pn.Column(
        main_area,
        log_panel.panel(),
        sizing_mode="stretch_both",
        styles={
            "display": "flex",
            "flex-direction": "column",
            "min-height": "calc(100vh - 60px)",
        },
    )
    # Make the main_area grow to fill available space
    main_area.styles = {"flex": "1"}
    assert template.main is not None
    template.main.append(content)

    return template


if __name__.startswith("bokeh") or __name__ == "__main__":
    app = create_app()
    app.servable()
