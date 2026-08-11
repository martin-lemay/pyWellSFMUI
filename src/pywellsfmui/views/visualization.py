import numpy as np
import panel as pn
import param

from pywellsfmui.plots import (
    build_elevation_plot,
    build_production_rates_plot,
    build_well_log_plot,
)
from pywellsfmui.state.actions import Actions
from pywellsfmui.state.app_state import AppState


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

            elev_fig = build_elevation_plot(times, sea_level, base, topo, well_name)

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
            return pn.Column(
                pn.pane.Markdown("## Wells"),
                pn.pane.Markdown("*No logs available.*"),
            )

        default = "Facies" if "Facies" in log_names else log_names[0]
        log_select = pn.widgets.Select(
            name="Log",
            options=log_names,
            value=default,
            width=200,
        )

        depth_range = _compute_common_depth_range(all_wells)

        def _build_wells_row(log_name: str) -> pn.Row:
            groups: list[pn.Row] = []
            for i, rd in enumerate(rd_list):
                real_fig = build_well_log_plot(rd.well, log_name, depth_range)
                pair: list = [
                    pn.pane.Plotly(
                        real_fig,
                        sizing_mode="stretch_width",
                    )
                ]
                if i < len(sim_wells):
                    sim_fig = build_well_log_plot(sim_wells[i], log_name, depth_range)
                    pair.append(
                        pn.pane.Plotly(
                            sim_fig,
                            sizing_mode="stretch_width",
                        )
                    )
                group = pn.Row(*pair)
                groups.append(group)

            if len(groups) <= 1:
                return pn.Row(*groups)

            separated: list = [groups[0]]
            for g in groups[1:]:
                separated.append(pn.Spacer(width=20))
                separated.append(g)
            return pn.Row(*separated)

        wells_row = pn.bind(_build_wells_row, log_select)

        return pn.Column(
            pn.pane.Markdown("## Wells"),
            log_select,
            wells_row,
            sizing_mode="stretch_both",
        )

    def panel(self) -> pn.Column:
        """Return the top-level Panel layout for this tab."""
        return pn.Column(
            self._results_panel,
            self._wells_panel,
            sizing_mode="stretch_both",
        )
