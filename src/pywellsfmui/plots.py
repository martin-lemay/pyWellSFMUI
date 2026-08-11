"""Shared Plotly plot builders for curve editors."""

import numpy as np
import numpy.typing as npt
import plotly.colors
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from pywellsfm.model import Curve, Marker, Well
from pywellsfm.utils import plot_litho_log

ENVIRONMENT_COLORS: dict[str, str] = {
    "Continent": "brown",
    "SupraTidal": "yellow",
    "Shore": "gold",
    "Lagoon": "lightblue",
    "Buildup": "coral",
    "BackReef": "lightcoral",
    "InnerRampUpperShoreface": "red",
    "InnerRampLowerShoreface": "lightcoral",
    "ReefCrest": "red",
    "ForeReef": "orange",
    "OuterRamp": "lightgreen",
    "ShelfSlope": "lightgray",
    "Basin": "lightsteelblue",
}

_PALETTE = plotly.colors.qualitative.Plotly


def get_environment_color(name: str, seen: set[str]) -> str:
    """Return the display color for an environment name.

    Known environments return their mapped color from
    ``ENVIRONMENT_COLORS``. Unknown names are auto-assigned a color
    from ``plotly.colors.qualitative.Plotly`` (cycling through the
    palette) and cached in ``ENVIRONMENT_COLORS`` so subsequent calls
    return the same color.

    Args:
        name: Environment name.
        seen: Mutable set that tracks auto-assigned names, used to
            determine the palette index for the next unknown name.

    Returns:
        A CSS color string.
    """
    if name in ENVIRONMENT_COLORS:
        return ENVIRONMENT_COLORS[name]
    if name not in seen:
        seen.add(name)
    index = sorted(seen).index(name)
    color = _PALETTE[index % len(_PALETTE)]
    ENVIRONMENT_COLORS[name] = color
    return color


def _add_env_legend_traces(
    fig: go.Figure,
    env_colors: dict[str, str],
    opacity: float,
) -> None:
    """Add invisible scatter traces as legend entries."""
    for env_name, color in env_colors.items():
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                name=env_name,
                marker=dict(
                    size=10,
                    color=color,
                    opacity=opacity,
                    symbol="square",
                ),
                showlegend=True,
            )
        )


def add_environment_spans(
    fig: go.Figure,
    times: npt.NDArray[np.floating],  # type: ignore[type-arg]
    environments: npt.NDArray[np.str_],  # type: ignore[type-arg]
    opacity: float = 0.3,
) -> None:
    """Add colored vertical-rect shapes to *fig* for each environment span.

    Computes midpoint edges between consecutive time samples to define
    span boundaries, then draws one ``vrect`` per contiguous block of
    the same environment name.

    Args:
        fig: Plotly Figure to mutate.
        times: 1-D array of time values (e.g. ages in My), one per
            sample. Span edges are computed as midpoints between
            adjacent samples; the first and last edges are half-steps
            beyond the array bounds.
        environments: 1-D string array of environment names, same
            length as *times*.
        opacity: Fill opacity for the vrect shapes (default 0.3).
    """
    n = len(times)
    if n == 0:
        return

    seen: set[str] = set()

    if n == 1:
        t = float(times[0])
        env = str(environments[0])
        color = get_environment_color(env, seen)
        fig.add_vrect(
            x0=t - 0.5,
            x1=t + 0.5,
            fillcolor=color,
            opacity=opacity,
            line_width=0,
        )
        _add_env_legend_traces(fig, {env: color}, opacity)
        return

    # Build n+1 edges: half-step before first, midpoints, half-step after last
    edges: list[float] = []
    edges.append(float(times[0]) - (float(times[1]) - float(times[0])) / 2.0)
    for i in range(n - 1):
        edges.append((float(times[i]) + float(times[i + 1])) / 2.0)
    edges.append(float(times[-1]) + (float(times[-1]) - float(times[-2])) / 2.0)

    # Walk contiguous blocks
    env_colors: dict[str, str] = {}
    block_start = 0
    for i in range(1, n + 1):
        at_end = i == n
        if at_end or str(environments[i]) != str(environments[block_start]):
            env_name = str(environments[block_start])
            color = get_environment_color(env_name, seen)
            env_colors[env_name] = color
            fig.add_vrect(
                x0=edges[block_start],
                x1=edges[i],
                fillcolor=color,
                opacity=opacity,
                line_width=0,
            )
            block_start = i

    _add_env_legend_traces(fig, env_colors, opacity)


def build_curve_plot(
    x_title: str,
    curve: Curve | None = None,
    trace_name: str = "",
    markers: list[Marker] | None = None,
) -> go.Figure:
    """Build a Plotly value-vs-Age figure.

    Age is on the vertical axis (older at bottom, younger at top).
    The value axis is horizontal.

    Args:
        x_title: Label for the X (value) axis.
        curve: Optional curve to plot as lines+markers.
        trace_name: Legend name for the curve trace.
        markers: Optional well markers shown as horizontal
            dashed lines at their age.

    Returns:
        A Plotly Figure.
    """
    fig = go.Figure()
    if curve is not None and len(curve._abscissa) > 0:
        fig.add_trace(
            go.Scatter(
                x=curve._ordinate,
                y=curve._abscissa,
                mode="lines+markers",
                name=trace_name,
            )
        )
    if markers:
        for m in markers:
            if not np.isnan(m.age):
                fig.add_hline(
                    y=m.age,
                    line_dash="dash",
                    line_color="gray",
                    annotation_text=m.name,
                    annotation_position="right",
                )
    fig.update_layout(
        xaxis_title=x_title,
        yaxis_title="Age (My)",
        yaxis_autorange="reversed",
        margin=dict(l=50, r=20, t=30, b=50),
        height=350,
    )
    return fig


def build_elevation_plot(
    times: npt.NDArray[np.floating],  # type: ignore[type-arg]
    sea_level: npt.NDArray[np.floating],  # type: ignore[type-arg]
    basement: npt.NDArray[np.floating],  # type: ignore[type-arg]
    topography: npt.NDArray[np.floating],  # type: ignore[type-arg]
    well_name: str,
) -> go.Figure:
    """Build a Plotly elevation vs. time figure for a well.

    Plots three traces: sea level, basement, and topography elevation
    over time.

    Args:
        times: 1-D array of time values (e.g. ages in My).
        sea_level: 1-D array of sea level elevations (m).
        basement: 1-D array of basement elevations (m).
        topography: 1-D array of topography elevations (m).
        well_name: Name of the well for the plot title.

    Returns:
        A Plotly Figure.
    """
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=times,
            y=sea_level,
            mode="lines",
            name="Sea Level",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=times,
            y=basement,
            mode="lines",
            name="Basement",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=times,
            y=topography,
            mode="lines",
            name="Topography",
        )
    )
    fig.update_layout(
        title=well_name,
        xaxis_title="Time (Myr)",
        yaxis_title="Elevation (m)",
        xaxis_autorange="reversed",
        margin=dict(l=50, r=20, t=40, b=50),
        height=300,
    )
    return fig


def build_production_rates_plot(
    times: npt.NDArray[np.floating],  # type: ignore[type-arg]
    element_rates: dict[str, npt.NDArray[np.floating]],  # type: ignore[type-arg]
    total_rate: npt.NDArray[np.floating],  # type: ignore[type-arg]
    water_depth: npt.NDArray[np.floating],  # type: ignore[type-arg]
    environments: npt.NDArray[np.str_] | None,  # type: ignore[type-arg]
    well_name: str,
) -> go.Figure:
    """Build a Plotly production rates vs. time figure with water depth.

    Plots element production rates (primary y-axis), total rate
    (dashed black line on primary y-axis), and water depth
    (dashed navy line on secondary y-axis) over time.
    If environments are provided, colored background spans
    are added for each environment.

    Args:
        times: 1-D array of time values (e.g. ages in My).
        element_rates: Dict mapping element names to 1-D arrays
            of production rates (m/Myr).
        total_rate: 1-D array of total production rates
            (m/Myr).
        water_depth: 1-D array of water depths (m).
        environments: Optional 1-D string array of environment
            names, same length as *times*. When provided,
            colored background spans are drawn.
        well_name: Name of the well for the plot title.

    Returns:
        A Plotly Figure with dual y-axes.
    """
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    for name, rates in element_rates.items():
        fig.add_trace(
            go.Scatter(
                x=times,
                y=rates,
                mode="lines",
                name=name,
            ),
            secondary_y=False,
        )

    fig.add_trace(
        go.Scatter(
            x=times,
            y=total_rate,
            mode="lines",
            name="Total",
            line=dict(color="black", dash="dash"),
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=times,
            y=water_depth,
            mode="lines",
            name="Water Depth",
            line=dict(color="blue", dash="dash"),
        ),
        secondary_y=True,
    )

    if environments is not None:
        add_environment_spans(fig, times, environments)

    wd_min = float(np.min(water_depth))
    fig.update_yaxes(
        range=[min(0, wd_min), None],
        secondary_y=True,
    )

    fig.update_layout(
        title=well_name,
        xaxis_title="Time (Myr)",
        xaxis_autorange="reversed",
        margin=dict(l=50, r=50, t=40, b=50),
        height=300,
    )
    fig.update_yaxes(
        title_text="Production rate (m/Myr)",
        secondary_y=False,
    )
    fig.update_yaxes(
        title_text="Water Depth (m)",
        secondary_y=True,
    )
    return fig


def build_well_log_plot(
    well: Well,
    log_name: str,
    depth_range: tuple[float, float] | None = None,
) -> go.Figure:
    """Build a Plotly figure for a single well log track.

    Args:
        well: Well object containing the log.
        log_name: Name of the log to display.
        depth_range: Optional (top, base) depth limits.

    Returns:
        A Plotly Figure.
    """
    discrete_names = well.getDiscreteLogNames()
    continuous_names = well.getContinuousLogNames()

    if log_name in discrete_names:
        fig = plot_litho_log(well, log_name, None, depth_range=depth_range)
        fig.update_layout(
            title=well.name,
            height=500,
        )
        return fig

    if log_name in continuous_names:
        log = well.getDepthLog(log_name)
        fig = go.Figure()
        if log is not None:
            fig.add_trace(
                go.Scatter(
                    x=log._ordinate,
                    y=log._abscissa,
                    mode="lines",
                    name=log_name,
                )
            )
        fig.update_layout(
            title=well.name,
            xaxis_title=log_name,
            yaxis_title="Depth",
            yaxis_autorange="reversed",
            margin=dict(l=50, r=20, t=40, b=50),
            height=500,
        )
        if depth_range is not None:
            fig.update_yaxes(
                range=[depth_range[1], depth_range[0]],
            )
        return fig

    # Missing log — return placeholder with N/A annotation
    fig = go.Figure()
    fig.add_annotation(
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        text="N/A",
        showarrow=False,
        font=dict(size=24, color="gray"),
    )
    fig.update_layout(
        title=well.name,
        yaxis_title="Depth",
        yaxis_autorange="reversed",
        margin=dict(l=50, r=20, t=40, b=50),
        height=500,
    )
    if depth_range is not None:
        fig.update_yaxes(
            range=[depth_range[1], depth_range[0]],
        )
    return fig
