import numpy as np
import panel as pn
import param

import plotly.colors

from pywellsfmui.plots import (
    ENVIRONMENT_COLORS,
    build_elevation_plot,
    build_production_rates_plot,
    build_well_log_plot,
    set_markers_visible,
)
from pywellsfmui.state.actions import Actions
from pywellsfmui.state.app_state import AppState


_PLOTLY_PALETTE = plotly.colors.qualitative.Plotly


def _build_element_color_map(
    element_names: list[str],
) -> dict[str, str]:
    """Build a color map for element names.

    Uses the same Plotly default palette that
    ``build_production_rates_plot`` assigns to element
    rate traces, so colors are consistent.
    """
    return {
        name: _PLOTLY_PALETTE[i % len(_PLOTLY_PALETTE)]
        for i, name in enumerate(element_names)
    }


def _collect_log_names(
    wells: list,
) -> list[str]:
    """Return sorted union of all log names across wells."""
    names: set[str] = set()
    for w in wells:
        names |= w.getDiscreteLogNames()
        names |= w.getContinuousLogNames()
    return sorted(names)


def _compute_common_depth_range(
    wells: list,
) -> tuple[float, float] | None:
    """Compute (top, base) depth union across all wells.

    Uses oldest marker depth as the base reference and
    well head (depth=0 end) as the top.
    """
    if not wells:
        return None
    tops: list[float] = []
    bases: list[float] = []
    for w in wells:
        try:
            base = w.oldestMarker.depth
            bases.append(base)
            tops.append(base - w.depth)
        except (AttributeError, IndexError):
            tops.append(0.0)
            bases.append(w.depth)
    return (min(tops), max(bases))


def _compute_common_age_range(
    wells: list,
) -> tuple[float, float] | None:
    """Compute (youngest, oldest) age union across wells.

    Uses marker ages to find the overall age range.
    """
    if not wells:
        return None
    youngest: list[float] = []
    oldest: list[float] = []
    for w in wells:
        markers = w.getMarkers()
        ages = [m.age for m in markers if not np.isnan(m.age)]
        if ages:
            youngest.append(min(ages))
            oldest.append(max(ages))
    if not youngest:
        return None
    return (min(youngest), max(oldest))


class VisualizationView(param.Parameterized):
    """Tab 3: Result Visualization."""

    def __init__(
        self,
        state: AppState,
        actions: Actions,
        **params,
    ) -> None:
        super().__init__(**params)
        self._state = state
        self._actions = actions

        # Wells panel widgets — created once, reused
        # across rebuilds to preserve user selections
        self._log_select = pn.widgets.Select(
            label="Log",
            options=[],
            width=200,
        )
        self._markers_cb = pn.widgets.Checkbox(
            label="Show markers",
            value=False,
        )
        self._age_cb = pn.widgets.Checkbox(
            label="Age domain",
            value=False,
        )

        # Persistent pane storage — (pane, well) pairs
        self._well_pane_map: list[tuple[pn.pane.Plotly, object]] = []

        # Cached simulation data for figure rebuilds
        self._cached_depth_range: tuple[float, float] | None = None
        self._cached_age_range: tuple[float, float] | None = None
        self._cached_element_colors: dict[str, str] = {}

        # Log/age change → rebuild figures
        self._log_select.param.watch(
            lambda e: self._rebuild_well_figures(),
            ["value"],
        )
        self._age_cb.param.watch(
            lambda e: self._rebuild_well_figures(),
            ["value"],
        )
        # Markers change → toggle visibility only
        self._markers_cb.param.watch(
            lambda e: self._toggle_markers(),
            ["value"],
        )

    def _get_color_map(
        self,
        log_name: str,
    ) -> dict[str, str] | None:
        if log_name == "MainElement":
            return self._cached_element_colors
        if log_name == "Environment":
            return dict(ENVIRONMENT_COLORS)
        return None

    def _rebuild_well_figures(self) -> None:
        """Rebuild all well figures for current log/age
        settings and update persistent panes in place."""
        if not self._well_pane_map:
            return
        log_name = self._log_select.value
        use_age = self._age_cb.value
        show_markers = self._markers_cb.value
        y_range = self._cached_age_range if use_age else self._cached_depth_range
        cmap = self._get_color_map(log_name)

        for pane, well in self._well_pane_map:
            fig = build_well_log_plot(
                well,
                log_name,
                y_range,
                color_map=cmap,
                show_markers=show_markers,
                use_age=use_age,
            )
            pane.object = fig

    def _toggle_markers(self) -> None:
        """Toggle marker visibility on existing figures
        without rebuilding them."""
        visible = self._markers_cb.value
        for pane, _ in self._well_pane_map:
            if pane.object is not None:
                set_markers_visible(pane.object, visible)
                pane.param.trigger("object")

    @param.depends("_state.simulation_outputs")
    def _results_panel(self) -> pn.Column:
        ds = self._state.simulation_outputs
        if ds is None:
            return pn.Column(
                pn.pane.Markdown("## Results"),
                pn.pane.Markdown(
                    "*No simulation results yet."
                    " Run a simulation in the"
                    " Simulation tab.*"
                ),
            )

        rd_list = self._state.realization_data_list
        accum = self._state.accumulation_model
        element_names = list(accum.elements.keys()) if accum is not None else []

        times = ds["time"].values
        sea_level = ds["sea_level"].values
        has_env = "environment" in ds.data_vars

        rows: list[pn.Row] = []
        for i, rd in enumerate(rd_list):
            well_name = rd.well.name
            base = ds["basement"].isel(realization=i).values
            topo = base + ds["thickness_cumul"].isel(realization=i).values

            elev_fig = build_elevation_plot(
                times,
                sea_level,
                base,
                topo,
                well_name,
            )

            elem_rates: dict[str, np.ndarray] = {}
            for en in element_names:
                key = f"depo_rate_{en}"
                if key in ds.data_vars:
                    elem_rates[en] = ds[key].isel(realization=i).values

            total = ds["depo_rate_total"].isel(realization=i).values
            wd = ds["waterDepth"].isel(realization=i).values
            envs = ds["environment"].isel(realization=i).values if has_env else None

            rates_fig = build_production_rates_plot(
                times,
                elem_rates,
                total,
                wd,
                envs,
                well_name,
            )

            rows.append(
                pn.Row(
                    pn.pane.Plotly(
                        elev_fig,
                        sizing_mode="stretch_width",
                    ),
                    pn.pane.Plotly(
                        rates_fig,
                        sizing_mode="stretch_width",
                    ),
                )
            )

        return pn.Column(
            pn.pane.Markdown("## Results"),
            *rows,
            sizing_mode="stretch_both",
        )

    @param.depends("_state.simulation_outputs")
    def _wells_panel(self) -> pn.Column:
        ds = self._state.simulation_outputs
        if ds is None:
            self._well_pane_map = []
            return pn.Column(
                pn.pane.Markdown("## Wells"),
                pn.pane.Markdown(
                    "*No simulation results yet."
                    " Run a simulation in the"
                    " Simulation tab.*"
                ),
            )

        rd_list = self._state.realization_data_list
        sim_wells = self._state.simulated_wells

        all_wells: list = []
        for i, rd in enumerate(rd_list):
            all_wells.append(rd.well)
            if i < len(sim_wells):
                all_wells.append(sim_wells[i])

        log_names = _collect_log_names(all_wells)
        if not log_names:
            self._well_pane_map = []
            return pn.Column(
                pn.pane.Markdown("## Wells"),
                pn.pane.Markdown("*No logs available.*"),
            )

        # Update persistent widgets — preserves user
        # selections when the chosen value is still valid
        old_value = self._log_select.value
        self._log_select.options = log_names
        if old_value in log_names:
            self._log_select.value = old_value
        else:
            self._log_select.value = "Facies" if "Facies" in log_names else log_names[0]

        # Cache data for _rebuild_well_figures
        self._cached_depth_range = _compute_common_depth_range(all_wells)
        self._cached_age_range = _compute_common_age_range(all_wells)
        accum = self._state.accumulation_model
        element_names = list(accum.elements.keys()) if accum is not None else []
        self._cached_element_colors = _build_element_color_map(element_names)

        # Build initial figures and persistent panes
        log_name = self._log_select.value
        use_age = self._age_cb.value
        show_markers = self._markers_cb.value
        y_range = self._cached_age_range if use_age else self._cached_depth_range
        cmap = self._get_color_map(log_name)

        self._well_pane_map = []
        groups: list[pn.Row] = []
        for i, rd in enumerate(rd_list):
            real_fig = build_well_log_plot(
                rd.well,
                log_name,
                y_range,
                color_map=cmap,
                show_markers=show_markers,
                use_age=use_age,
            )
            real_pane = pn.pane.Plotly(
                real_fig,
                sizing_mode="stretch_width",
            )
            self._well_pane_map.append((real_pane, rd.well))
            pair: list = [real_pane]

            if i < len(sim_wells):
                sim_fig = build_well_log_plot(
                    sim_wells[i],
                    log_name,
                    y_range,
                    color_map=cmap,
                    show_markers=show_markers,
                    use_age=use_age,
                )
                sim_pane = pn.pane.Plotly(
                    sim_fig,
                    sizing_mode="stretch_width",
                )
                self._well_pane_map.append((sim_pane, sim_wells[i]))
                pair.append(sim_pane)

            groups.append(pn.Row(*pair))

        if len(groups) <= 1:
            wells_content = pn.Row(*groups)
        else:
            separated: list = [groups[0]]
            for g in groups[1:]:
                separated.append(pn.Spacer(width=20))
                separated.append(g)
            wells_content = pn.Row(*separated)

        return pn.Column(
            pn.pane.Markdown("## Wells"),
            pn.Row(
                self._log_select,
                self._markers_cb,
                self._age_cb,
            ),
            wells_content,
            sizing_mode="stretch_both",
        )

    def panel(self) -> pn.Column:
        """Return the top-level Panel layout for this tab."""
        return pn.Column(
            self._results_panel,
            self._wells_panel,
            sizing_mode="stretch_both",
        )
