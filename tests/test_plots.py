"""Tests for pywellsfmui.plots environment color helpers."""

from unittest.mock import MagicMock, patch

import numpy as np
import plotly.colors
import plotly.graph_objects as go

from pywellsfmui.plots import (
    add_environment_spans,
    build_elevation_plot,
    build_production_rates_plot,
    build_well_log_plot,
    get_environment_color,
)


def test_known_environment_returns_mapped_color() -> None:
    """Test known env returns its mapped color."""
    seen: set[str] = set()
    assert get_environment_color("Basin", seen) == "lightsteelblue"


def test_unknown_environment_auto_assigns_color() -> None:
    """Test unknown env gets auto-assigned color."""
    seen: set[str] = set()
    palette = plotly.colors.qualitative.Plotly
    color = get_environment_color("NoSuchEnv", seen)
    assert color in palette
    assert "NoSuchEnv" in seen


def test_unknown_environment_same_color_on_repeat() -> None:
    """Test unknown env gets same color on repeat."""
    seen: set[str] = set()
    c1 = get_environment_color("FooEnv", seen)
    c2 = get_environment_color("FooEnv", seen)
    assert c1 == c2


def test_multiple_unknowns_get_different_colors() -> None:
    """Test multiple unknowns get different colors."""
    seen: set[str] = set()
    c1 = get_environment_color("Env_A", seen)
    c2 = get_environment_color("Env_B", seen)
    assert c1 != c2


def test_add_environment_spans_adds_vrects() -> None:
    """Test env spans add vrects to figure."""
    fig = go.Figure()
    times = np.array([30.0, 20.0, 10.0])
    envs = np.array(["Basin", "Basin", "OuterRamp"])
    add_environment_spans(fig, times, envs)
    assert len(fig.layout.shapes) == 2
    # 2 unique envs -> 2 legend traces
    assert len(fig.data) == 2


def test_add_environment_spans_empty() -> None:
    """Test env spans with empty arrays."""
    fig = go.Figure()
    times = np.array([])
    envs = np.array([])
    add_environment_spans(fig, times, envs)
    assert len(fig.layout.shapes) == 0
    assert len(fig.data) == 0


def test_add_environment_spans_single_point() -> None:
    """Test env spans with a single point."""
    fig = go.Figure()
    times = np.array([10.0])
    envs = np.array(["Basin"])
    add_environment_spans(fig, times, envs)
    assert len(fig.layout.shapes) == 1
    assert len(fig.data) == 1


def test_build_elevation_plot_has_three_traces() -> None:
    """Test elevation plot has 3 traces."""
    t = np.array([30.0, 20.0, 10.0])
    sea = np.array([5.0, 10.0, 8.0])
    base = np.array([-10.0, -15.0, -20.0])
    topo = np.array([0.0, 2.0, -5.0])
    fig = build_elevation_plot(t, sea, base, topo, "Well_1")
    assert len(fig.data) == 3
    names = {tr.name for tr in fig.data}
    assert names == {
        "Sea Level",
        "Basement",
        "Topography",
    }


def test_build_elevation_plot_xaxis_reversed() -> None:
    """Test elevation plot has reversed x-axis."""
    t = np.array([30.0, 20.0, 10.0])
    sea = np.array([5.0, 10.0, 8.0])
    base = np.array([-10.0, -15.0, -20.0])
    topo = np.array([0.0, 2.0, -5.0])
    fig = build_elevation_plot(t, sea, base, topo, "Well_1")
    assert fig.layout.xaxis.autorange == "reversed"


def test_build_production_rates_basic() -> None:
    """Test production rates basic plot."""
    t = np.array([30.0, 20.0, 10.0])
    elem_rates = {
        "Shallow": np.array([1.0, 0.5, 0.2]),
        "Deep": np.array([0.1, 0.3, 0.8]),
    }
    total = np.array([1.1, 0.8, 1.0])
    wd = np.array([5.0, 10.0, 20.0])
    fig = build_production_rates_plot(t, elem_rates, total, wd, None, "Well_1")
    # 2 elements + total + water depth = 4 traces
    assert len(fig.data) == 4
    names = [tr.name for tr in fig.data]
    assert "Total" in names
    assert "Water Depth" in names


def test_build_production_rates_with_environments() -> None:
    """Test production rates with env spans."""
    t = np.array([30.0, 20.0, 10.0])
    elem_rates = {"Mud": np.array([0.5, 0.5, 0.5])}
    total = np.array([0.5, 0.5, 0.5])
    wd = np.array([50.0, 50.0, 50.0])
    envs = np.array(["Basin", "Basin", "ShelfSlope"])
    fig = build_production_rates_plot(t, elem_rates, total, wd, envs, "Well_1")
    # 1 elem + total + water depth + 2 env = 5
    assert len(fig.data) == 5
    # 2 environment spans
    assert len(fig.layout.shapes) == 2
    env_names = {tr.name for tr in fig.data if tr.marker.symbol}
    assert "Basin" in env_names
    assert "ShelfSlope" in env_names


def test_build_production_rates_xaxis_reversed() -> None:
    """Test production rates has reversed x-axis."""
    t = np.array([30.0, 20.0, 10.0])
    elem_rates = {"A": np.array([1.0, 1.0, 1.0])}
    total = np.array([1.0, 1.0, 1.0])
    wd = np.array([5.0, 5.0, 5.0])
    fig = build_production_rates_plot(t, elem_rates, total, wd, None, "W")
    assert fig.layout.xaxis.autorange == "reversed"


def test_build_well_log_plot_discrete() -> None:
    """Discrete log delegates to plot_litho_log."""
    well = MagicMock()
    well.name = "W1"
    well.getDiscreteLogNames.return_value = {"Facies"}
    well.getContinuousLogNames.return_value = set()

    fake_fig = MagicMock(spec=go.Figure)
    fake_fig.update_layout = MagicMock()
    fake_fig.update_yaxes = MagicMock()

    with patch(
        "pywellsfmui.plots.plot_litho_log",
        return_value=fake_fig,
    ) as mock_plot:
        fig = build_well_log_plot(well, "Facies")
        mock_plot.assert_called_once_with(
            well,
            "Facies",
            None,
            depth_range=None,
        )
    assert fig is fake_fig


def test_build_well_log_plot_discrete_with_color_map() -> None:
    """Discrete log passes color_map."""
    well = MagicMock()
    well.name = "W1"
    well.getDiscreteLogNames.return_value = {"MainElement"}
    well.getContinuousLogNames.return_value = set()

    fake_fig = MagicMock(spec=go.Figure)
    fake_fig.update_layout = MagicMock()
    cmap = {"Mud": "#636EFA", "Sand": "#EF553B"}

    with patch(
        "pywellsfmui.plots.plot_litho_log",
        return_value=fake_fig,
    ) as mock_plot:
        build_well_log_plot(
            well,
            "MainElement",
            color_map=cmap,
        )
        mock_plot.assert_called_once_with(
            well,
            "MainElement",
            cmap,
            depth_range=None,
        )


def test_build_well_log_plot_continuous() -> None:
    """Continuous log produces a line scatter plot."""
    well = MagicMock()
    well.name = "W1"
    well.getDiscreteLogNames.return_value = set()
    well.getContinuousLogNames.return_value = {"GR"}

    mock_curve = MagicMock()
    mock_curve._abscissa = np.array([100.0, 200.0, 300.0])
    mock_curve._ordinate = np.array([50.0, 80.0, 30.0])
    well.getDepthLog.return_value = mock_curve

    fig = build_well_log_plot(well, "GR")
    assert len(fig.data) == 1
    assert fig.data[0].mode == "lines"
    np.testing.assert_array_equal(fig.data[0].x, [50.0, 80.0, 30.0])
    np.testing.assert_array_equal(fig.data[0].y, [100.0, 200.0, 300.0])
    assert fig.layout.yaxis.autorange == "reversed"


def test_build_well_log_plot_missing() -> None:
    """Missing log returns placeholder with N/A."""
    well = MagicMock()
    well.name = "W1"
    well.getDiscreteLogNames.return_value = set()
    well.getContinuousLogNames.return_value = set()
    well.getDepthLog.return_value = None

    fig = build_well_log_plot(well, "NoSuchLog")
    annotations = fig.layout.annotations
    assert any("N/A" in a.text for a in annotations)


def test_build_well_log_plot_continuous_depth_range() -> None:
    """Continuous log respects depth_range."""
    well = MagicMock()
    well.name = "W1"
    well.getDiscreteLogNames.return_value = set()
    well.getContinuousLogNames.return_value = {"GR"}

    mock_curve = MagicMock()
    mock_curve._abscissa = np.array([100.0, 200.0, 300.0])
    mock_curve._ordinate = np.array([50.0, 80.0, 30.0])
    well.getDepthLog.return_value = mock_curve

    fig = build_well_log_plot(well, "GR", depth_range=(50.0, 350.0))
    y_range = fig.layout.yaxis.range
    assert y_range[0] == 350.0  # reversed: max first
    assert y_range[1] == 50.0
