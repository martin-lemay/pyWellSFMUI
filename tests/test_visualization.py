"""Tests for VisualizationView."""

from unittest.mock import MagicMock, patch

import numpy as np
import panel as pn
import plotly.graph_objects as go
import xarray as xr

from pywellsfmui.state.actions import Actions
from pywellsfmui.state.app_state import AppState
from pywellsfmui.state.io_manager import IOManager
from pywellsfmui.state.message_store import MessageStore
from pywellsfmui.views.visualization import VisualizationView


def _make_actions(state: AppState) -> Actions:
    return Actions(
        state=state,
        io_manager=IOManager(),
        message_store=MessageStore(),
    )


def _make_mock_well(
    name: str,
    discrete_logs: set[str] | None = None,
    continuous_logs: set[str] | None = None,
) -> MagicMock:
    """Create a mock Well with log name sets."""
    w = MagicMock()
    w.name = name
    w.getDiscreteLogNames.return_value = discrete_logs or set()
    w.getContinuousLogNames.return_value = continuous_logs or set()
    w.oldestMarker.depth = 500.0
    w.depth = 600.0
    return w


def test_no_outputs_shows_placeholder():
    state = AppState()
    actions = _make_actions(state)
    view = VisualizationView(state=state, actions=actions)
    panel = view._results_panel()
    md_texts = [o.object for o in panel.objects if isinstance(o, pn.pane.Markdown)]
    assert any("No simulation" in t for t in md_texts)


def _make_dataset(n_real: int = 2, n_time: int = 5) -> xr.Dataset:
    times = np.linspace(30, 10, n_time)
    ds = xr.Dataset(
        {
            "sea_level": ("time", np.ones(n_time)),
            "basement": (
                ("realization", "time"),
                np.zeros((n_real, n_time)),
            ),
            "thickness_cumul": (
                ("realization", "time"),
                np.ones((n_real, n_time)),
            ),
            "depo_rate_total": (
                ("realization", "time"),
                np.ones((n_real, n_time)),
            ),
            "depo_rate_Mud": (
                ("realization", "time"),
                np.ones((n_real, n_time)),
            ),
            "waterDepth": (
                ("realization", "time"),
                5.0 * np.ones((n_real, n_time)),
            ),
        },
        coords={
            "time": times,
            "realization": np.arange(n_real),
        },
    )
    return ds


def test_results_panel_renders_plots():
    state = AppState()
    actions = _make_actions(state)
    state.simulation_outputs = _make_dataset(n_real=2)

    rd1 = MagicMock()
    rd1.well.name = "Well_1"
    rd2 = MagicMock()
    rd2.well.name = "Well_2"
    state.realization_data_list = [rd1, rd2]

    accum = MagicMock()
    accum.elements = {"Mud": MagicMock()}
    state.accumulation_model = accum

    view = VisualizationView(state=state, actions=actions)
    panel = view._results_panel()

    rows = [o for o in panel.objects if isinstance(o, pn.Row)]
    assert len(rows) == 2


def test_wells_panel_no_outputs_shows_placeholder():
    state = AppState()
    actions = _make_actions(state)
    view = VisualizationView(state=state, actions=actions)
    panel = view._wells_panel()
    md_texts = [o.object for o in panel.objects if isinstance(o, pn.pane.Markdown)]
    assert any("No simulation" in t for t in md_texts)


def test_wells_panel_renders_grouped_wells():
    state = AppState()
    actions = _make_actions(state)
    state.simulation_outputs = _make_dataset(n_real=2)

    real1 = _make_mock_well("W1", discrete_logs={"Facies"})
    real2 = _make_mock_well("W2", discrete_logs={"Facies"})
    sim1 = _make_mock_well("W1_sim_0", discrete_logs={"Facies", "MainElement"})
    sim2 = _make_mock_well("W2_sim_1", discrete_logs={"Facies", "MainElement"})

    rd1 = MagicMock()
    rd1.well = real1
    rd2 = MagicMock()
    rd2.well = real2
    state.realization_data_list = [rd1, rd2]
    state.simulated_wells = [sim1, sim2]

    view = VisualizationView(state=state, actions=actions)
    panel = view._wells_panel()

    md_texts = [o.object for o in panel.objects if isinstance(o, pn.pane.Markdown)]
    assert any("## Wells" in t for t in md_texts)

    selects = [o for o in panel.objects if isinstance(o, pn.widgets.Select)]
    assert len(selects) == 1
    expected_options = sorted({"Facies", "MainElement"})
    assert selects[0].options == expected_options


def test_wells_panel_dropdown_defaults_to_facies():
    state = AppState()
    actions = _make_actions(state)
    state.simulation_outputs = _make_dataset(n_real=1)

    real = _make_mock_well("W1", discrete_logs={"Facies", "GR"})
    sim = _make_mock_well("W1_sim_0", discrete_logs={"Facies", "MainElement"})
    rd = MagicMock()
    rd.well = real
    state.realization_data_list = [rd]
    state.simulated_wells = [sim]

    view = VisualizationView(state=state, actions=actions)

    with patch(
        "pywellsfmui.views.visualization.build_well_log_plot",
        return_value=go.Figure(),
    ):
        panel = view._wells_panel()

    selects = [o for o in panel.objects if isinstance(o, pn.widgets.Select)]
    assert len(selects) == 1
    assert selects[0].value == "Facies"
