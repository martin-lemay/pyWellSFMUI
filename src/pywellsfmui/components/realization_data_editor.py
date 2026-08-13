"""Realization data editor component.

Master-detail layout: well list on the left with per-well
bathymetry and environment settings; well detail panel on the
right showing well properties, markers, and subsidence curve
for the selected well.
"""

from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
import panel as pn
import param
import plotly.graph_objects as go
from pywellsfm.model import (
    Curve,
    Marker,
    RealizationData,
    SubsidenceType,
    Well,
)
from pywellsfm.model.Marker import StratigraphicSurfaceType

from pywellsfmui.components.curve_editor import CurveEditor
from pywellsfmui.plots import build_curve_plot
from pywellsfmui.state.actions import Actions
from pywellsfmui.state.app_state import AppState
from pywellsfmui.theme import Colors, status_html

_SUBSIDENCE_TITLES: dict[SubsidenceType, str] = {
    SubsidenceType.CUMULATIVE: "Subsidence (m)",
    SubsidenceType.RATE: "Subsidence Rate (m/My)",
}

_NO_ENVIRONMENT = "(none)"

_STRAT_TYPES: list[str] = [t.value for t in StratigraphicSurfaceType]

_MK_NAME = "Name"
_MK_DEPTH = "Depth"
_MK_AGE = "Age"
_MK_TYPE = "Type"
_NEW_MARKER = "New..."


@dataclass
class WellSettings:
    """Per-well realization settings.

    Attributes:
        bathymetry: Initial bathymetry in metres.
        initial_env_name: Selected depositional environment name,
            or None when unset.
        subsidence_type: Whether the curve is cumulative or a rate.
        subsidence_curve: Optional subsidence Curve instance.
    """

    bathymetry: float = 0.0
    initial_env_name: str | None = None
    subsidence_type: SubsidenceType = SubsidenceType.CUMULATIVE
    subsidence_curve: Curve | None = None


logger = logging.getLogger(__name__)


class RealizationDataEditor(param.Parameterized):
    """Realization data editor.

    Master-detail layout: well list (left) with per-well settings,
    well detail panel (right) for the selected well.

    Args:
        state: Central application state.
        actions: Command layer used to mutate state.
    """

    def __init__(
        self,
        state: AppState,
        actions: Actions,
        **params: Any,
    ) -> None:
        """Initialize the realization data editor."""
        super().__init__(**params)
        self._state = state
        self._actions = actions
        self._updating = False
        self._well_settings: dict[str, WellSettings] = {}
        self._selected_well: str | None = None

        # --- Left panel widgets ---
        self._file_input = pn.widgets.FileInput(
            accept=".json,.las",
            width=250,
            align="start",
            label="Load Well",
        )
        self._add_btn = pn.widgets.Button(
            label="Add",
            color="primary",
            width=80,
            height=28,
            align="center",
        )
        self._add_btn.on_click(self._on_add_well)
        self._well_list = pn.Column(sizing_mode="stretch_width")

        # --- Right panel: well detail ---
        self._detail_title = pn.pane.Markdown("**Select a well**")

        # Well properties
        self._name_input = pn.widgets.TextInput(
            label="Well Name",
            width=250,
        )
        self._x_input = pn.widgets.FloatInput(
            label="X",
            value=0.0,
            step=1.0,
            width=110,
        )
        self._y_input = pn.widgets.FloatInput(
            label="Y",
            value=0.0,
            step=1.0,
            width=110,
        )
        self._z_input = pn.widgets.FloatInput(
            label="Z",
            value=0.0,
            step=1.0,
            width=110,
        )
        self._depth_input = pn.widgets.FloatInput(
            label="Depth (m)",
            value=0.0,
            step=1.0,
            width=150,
        )

        # Markers table
        self._marker_df = pd.DataFrame(
            columns=[_MK_NAME, _MK_DEPTH, _MK_AGE, _MK_TYPE],
        )
        self._marker_table = pn.widgets.Tabulator(
            self._marker_df,
            sizing_mode="stretch_width",
            height=200,
            show_index=False,
            selectable=1,
            widths={
                _MK_NAME: "25%",
                _MK_DEPTH: "25%",
                _MK_AGE: "25%",
                _MK_TYPE: "25%",
            },
            editors={
                _MK_NAME: {
                    "type": "input",
                    "selectContents": True,
                },
                _MK_DEPTH: {
                    "type": "number",
                    "selectContents": True,
                },
                _MK_AGE: {
                    "type": "number",
                    "selectContents": True,
                },
                _MK_TYPE: {
                    "type": "list",
                    "values": _STRAT_TYPES,
                    "valuesLookup": True,
                },
            },
            configuration={
                "editTriggerEvent": "dblclick",
            },
        )
        self._marker_remove_btn = pn.widgets.Button(
            label="Remove Marker",
            color="danger",
            width=120,
            height=28,
        )

        # Subsidence curve
        self._curve_editor = CurveEditor(
            age_title="Age (My)",
            value_title="Subsidence (m)",
            file_label="Load Subsidence Curve",
            on_curve_changed=self._on_subsidence_curve_changed,
        )
        self._sub_type_select = pn.widgets.Select(
            label="Subsidence Type",
            options=[
                SubsidenceType.CUMULATIVE,
                SubsidenceType.RATE,
            ],
            value=SubsidenceType.CUMULATIVE,
            width=200,
            align="start",
        )

        self._subsidence_plot = pn.pane.Plotly(
            self._build_subsidence_plot(),
            sizing_mode="stretch_width",
            height=350,
        )

        self._erase_curve_btn = pn.widgets.Button(
            label="Erase Curve",
            color="danger",
            width=110,
            height=28,
            align="center",
        )
        self._erase_curve_btn.on_click(self._on_erase_curve)

        # Assemble detail panel
        self._detail_panel = pn.Column(
            self._detail_title,
            pn.Row(
                self._name_input,
                self._depth_input,
                align="end",
            ),
            pn.pane.Markdown("**Well Head Coordinates**"),
            pn.Row(
                self._x_input,
                self._y_input,
                self._z_input,
                align="end",
            ),
            pn.pane.Markdown("**Markers**"),
            self._marker_table,
            pn.Row(
                pn.Spacer(),
                self._marker_remove_btn,
                sizing_mode="stretch_width",
            ),
            pn.pane.Markdown("**Subsidence Curve**"),
            pn.Row(
                self._sub_type_select,
                pn.Spacer(),
                self._erase_curve_btn,
                align="end",
                sizing_mode="stretch_width",
            ),
            pn.Row(
                self._curve_editor.panel(),
                self._subsidence_plot,
                sizing_mode="stretch_width",
            ),
            sizing_mode="stretch_width",
            visible=False,
        )

        self._status = pn.pane.HTML(
            self._build_status_html(),
            sizing_mode="fixed",
        )

        # --- Wire watchers ---
        self._file_input.param.watch(self._on_file_loaded, "value")
        self._name_input.param.watch(self._on_name_changed, "value")
        self._x_input.param.watch(self._on_coord_changed, "value")
        self._y_input.param.watch(self._on_coord_changed, "value")
        self._z_input.param.watch(self._on_coord_changed, "value")
        self._depth_input.param.watch(self._on_depth_changed, "value")
        self._marker_table.on_edit(self._on_marker_edit)
        self._marker_remove_btn.on_click(self._on_marker_remove)
        self._sub_type_select.param.watch(self._on_sub_type_changed, "value")
        self._state.param.watch(
            lambda event: self._refresh(),
            ["wells"],
        )
        self._state.param.watch(
            lambda event: self._refresh(),
            ["depositional_env_model"],
        )
        self._refresh()

    # --- Environment options ---

    def _get_environment_options(self) -> list[str]:
        """Return environment names from the depositional model."""
        model = self._state.depositional_env_model
        if model is None:
            return [_NO_ENVIRONMENT]
        names = [e.name for e in model.environments]
        if not names:
            return [_NO_ENVIRONMENT]
        return [_NO_ENVIRONMENT] + names

    # --- Status ---

    def _build_status_html(self) -> str:
        """Return a colored status string describing the well count.

        Returns:
            An HTML span string.
        """
        count = len(self._state.wells)
        if count == 0:
            return status_html("No wells", Colors.ERROR)
        label = f"{count} well{'s' if count != 1 else ''}"
        return status_html(label, Colors.SUCCESS)

    def _build_subsidence_plot(self) -> go.Figure:
        """Build a Plotly figure for the selected well's subsidence."""
        curve = None
        y_title = "Subsidence (m)"
        well = self._get_selected_well_obj()
        if self._selected_well is not None:
            ws = self._well_settings.get(self._selected_well)
            if ws is not None:
                curve = ws.subsidence_curve
                y_title = _SUBSIDENCE_TITLES[ws.subsidence_type]
        markers = list(well.getMarkers()) if well is not None else None
        return build_curve_plot(
            y_title,
            curve,
            "Subsidence",
            markers=markers,
        )

    # --- Well settings sync ---

    def _sync_well_settings(self) -> None:
        well_names = {w.name for w in self._state.wells}
        for name in list(self._well_settings):
            if name not in well_names:
                del self._well_settings[name]
        # Index existing realization data by well name
        rd_by_name: dict[str, RealizationData] = {}
        for rd in self._state.realization_data_list:
            rd_by_name[rd.well.name] = rd
        for w in self._state.wells:
            if w.name not in self._well_settings:
                rd = rd_by_name.get(w.name)
                if rd is not None:
                    self._well_settings[w.name] = WellSettings(
                        bathymetry=rd.initialBathymetry,
                        initial_env_name=(rd.initialEnvironmentName),
                        subsidence_type=rd.subsidenceType,
                        subsidence_curve=rd.subsidenceCurve,
                    )
                else:
                    self._well_settings[w.name] = WellSettings()
        if self._selected_well and self._selected_well not in well_names:
            self._selected_well = None

    # --- Build realization data on-the-fly ---

    def _build_and_push_realization_data(self) -> None:
        data_list: list[RealizationData] = []
        for well in self._state.wells:
            ws = self._well_settings.get(well.name)
            if ws is None:
                continue
            env_name = ws.initial_env_name
            if env_name == _NO_ENVIRONMENT:
                env_name = None
            rd = RealizationData(
                well=well,
                initialBathymetry=ws.bathymetry,
                initialEnvironmentName=env_name,
                subsidenceCurve=ws.subsidence_curve,
                subsidenceType=ws.subsidence_type,
            )
            data_list.append(rd)
        self._actions.set_realization_data_list(data_list)

    # --- Well row builder ---

    def _make_well_row(self, well: Well) -> pn.Row:
        name = well.name
        ws = self._well_settings[name]

        name_btn = pn.widgets.Button(
            label=name,
            color=("primary" if name == self._selected_well else "default"),
            width=140,
            height=28,
            align="center",
            margin=(5, 5),
        )

        bath_input = pn.widgets.FloatInput(
            label="",
            value=ws.bathymetry,
            step=1.0,
            width=140,
            align="center",
            margin=(5, 5),
        )

        env_options = self._get_environment_options()
        env_select = pn.widgets.Select(
            options=env_options,
            value=(
                ws.initial_env_name
                if ws.initial_env_name in env_options
                else env_options[0]
            ),
            width=140,
            align="center",
            margin=(5, 5),
        )

        remove_btn = pn.widgets.Button(
            label="Remove",
            color="danger",
            width=80,
            height=28,
            align="center",
        )

        def _on_select(event: Any, wn: str = name) -> None:
            self._selected_well = wn
            self._refresh_well_list()
            self._update_detail_panel()

        def _on_bath_changed(event: Any, wn: str = name) -> None:
            if self._updating:
                return
            self._well_settings[wn].bathymetry = event.new
            self._build_and_push_realization_data()

        def _on_env_changed(event: Any, wn: str = name) -> None:
            if self._updating:
                return
            self._well_settings[wn].initial_env_name = event.new
            self._build_and_push_realization_data()

        def _on_remove(event: Any, wn: str = name) -> None:
            with contextlib.suppress(ValueError):
                self._actions.remove_well(wn)

        name_btn.on_click(_on_select)
        bath_input.param.watch(_on_bath_changed, "value")
        env_select.param.watch(_on_env_changed, "value")
        remove_btn.on_click(_on_remove)

        return pn.Row(
            name_btn,
            bath_input,
            env_select,
            pn.Spacer(),
            remove_btn,
            sizing_mode="fixed",
            align="start",
        )

    def _make_header_row(self) -> pn.Row:
        return pn.Row(
            pn.pane.Markdown("**Well**", width=140, margin=(5, 5)),
            pn.pane.Markdown(
                "**Initial Bathymetry (m)**",
                width=140,
                margin=(5, 5),
            ),
            pn.pane.Markdown(
                "**Initial Environment**",
                width=140,
                margin=(5, 5),
            ),
            pn.Spacer(),
            pn.pane.Markdown("", width=80),
            sizing_mode="stretch_width",
        )

    # --- Markers ---

    def _get_selected_well_obj(self) -> Well | None:
        if self._selected_well is None:
            return None
        for w in self._state.wells:
            if w.name == self._selected_well:
                return w
        return None

    def _build_marker_df(self, well: Well) -> pd.DataFrame:
        rows: list[dict] = []
        for m in well.getMarkers():
            rows.append(
                {
                    _MK_NAME: m.name,
                    _MK_DEPTH: m.depth,
                    _MK_AGE: m.age if not np.isnan(m.age) else None,
                    _MK_TYPE: m.stratigraphicType.value,
                }
            )
        rows.append(
            {
                _MK_NAME: _NEW_MARKER,
                _MK_DEPTH: None,
                _MK_AGE: None,
                _MK_TYPE: StratigraphicSurfaceType.UNKNOWN.value,
            }
        )
        df = pd.DataFrame(rows)
        for col in [_MK_NAME, _MK_DEPTH, _MK_AGE, _MK_TYPE]:
            df[col] = df[col].astype(object)
        return df

    def _markers_from_table(self) -> list[Marker]:
        """Read markers from the current table (excluding placeholder)."""
        df = self._marker_table.value
        markers: list[Marker] = []
        for i in range(len(df) - 1):
            name = df.at[i, _MK_NAME]
            depth = df.at[i, _MK_DEPTH]
            age = df.at[i, _MK_AGE]
            stype = df.at[i, _MK_TYPE]
            if name is None or depth is None:
                continue
            markers.append(
                Marker(
                    name=str(name),
                    depth=float(depth),
                    age=float(age) if age is not None else np.nan,
                    stratigraphicType=StratigraphicSurfaceType(stype),
                )
            )
        return markers

    def _push_markers(self) -> None:
        """Push current marker table to the well."""
        well = self._get_selected_well_obj()
        if well is None:
            return
        markers = self._markers_from_table()
        self._actions.set_well_markers(well.name, markers)
        self._subsidence_plot.object = self._build_subsidence_plot()

    def _style_marker_placeholder(self, row: pd.Series) -> list[str]:
        for val in row.values:
            if val == _NEW_MARKER:
                return ["font-style: italic; color: #999"] * len(row)
        return [""] * len(row)

    def _refresh_marker_table(self, well: Well) -> None:
        self._updating = True
        df = self._build_marker_df(well)
        self._marker_table.value = df
        self._marker_table.style.apply(self._style_marker_placeholder, axis=1)
        self._marker_table.param.trigger("value")
        self._updating = False

    # --- Refresh ---

    def _refresh_well_list(self) -> None:
        self._updating = True
        self._well_list.clear()
        if self._state.wells:
            self._well_list.append(self._make_header_row())
        for well in self._state.wells:
            self._well_list.append(self._make_well_row(well))
        self._updating = False

    def _update_detail_panel(self) -> None:
        well = self._get_selected_well_obj()
        if well is None:
            self._detail_panel.visible = False
            return
        ws = self._well_settings.get(well.name)
        if ws is None:
            self._detail_panel.visible = False
            return

        self._detail_panel.visible = True
        self._detail_title.object = f"**Well — {well.name}**"

        self._updating = True
        self._name_input.value = well.name
        coords = well.wellHeadCoords
        self._x_input.value = float(coords[0])
        self._y_input.value = float(coords[1])
        self._z_input.value = float(coords[2])
        self._depth_input.value = float(well.depth)
        self._sub_type_select.value = ws.subsidence_type
        self._updating = False

        self._refresh_marker_table(well)

        title = _SUBSIDENCE_TITLES[ws.subsidence_type]
        self._curve_editor.set_value_title(title)
        self._curve_editor.set_curve(ws.subsidence_curve)
        self._subsidence_plot.object = self._build_subsidence_plot()

    def _refresh(self) -> None:
        self._sync_well_settings()
        self._refresh_well_list()
        self._update_detail_panel()
        self._status.object = self._build_status_html()
        if self._state.wells:
            self._build_and_push_realization_data()

    # --- Callbacks ---

    def _on_add_well(self, event: Any) -> None:
        self._actions.add_empty_well()

    def _on_file_loaded(self, event: Any) -> None:
        if self._file_input.value is None:
            return
        try:
            self._actions.load_well_from_bytes(
                self._file_input.value,
                filename=self._file_input.filename or "",
            )
        except Exception:
            logger.debug("Load well file failed", exc_info=True)

    def _on_name_changed(self, event: Any) -> None:
        if self._updating or self._selected_well is None:
            return
        old_name = self._selected_well
        new_name = event.new.strip()
        if not new_name or new_name == old_name:
            return
        # Pre-rename the settings key so _sync_well_settings
        # doesn't lose the existing WellSettings
        if old_name in self._well_settings:
            self._well_settings[new_name] = self._well_settings.pop(old_name)
        self._selected_well = new_name
        try:
            self._actions.rename_well(old_name, new_name)
        except ValueError:
            # Revert on failure (e.g. duplicate name)
            self._well_settings[old_name] = self._well_settings.pop(new_name)
            self._selected_well = old_name
            self._updating = True
            self._name_input.value = old_name
            self._updating = False

    def _on_coord_changed(self, event: Any) -> None:
        if self._updating or self._selected_well is None:
            return
        self._actions.update_well_location(
            self._selected_well,
            float(self._x_input.value or 0),
            float(self._y_input.value or 0),
            float(self._z_input.value or 0),
        )

    def _on_depth_changed(self, event: Any) -> None:
        if self._updating or self._selected_well is None:
            return
        self._actions.update_well_depth(
            self._selected_well,
            float(self._depth_input.value or 0),
        )

    def _on_marker_edit(self, event: Any) -> None:
        if self._updating:
            return
        df = self._marker_table.value
        row = event.row
        is_last = row == len(df) - 1

        if is_last:
            # Check if enough data to create a new marker
            name_val = df.at[row, _MK_NAME]
            depth_val = df.at[row, _MK_DEPTH]
            if event.column == _MK_NAME:
                name_val = event.value
            elif event.column == _MK_DEPTH:
                depth_val = event.value
            name_str = str(name_val).strip() if name_val is not None else ""
            if name_str == _NEW_MARKER:
                name_str = ""
            if name_str and depth_val is not None:
                age_val = df.at[row, _MK_AGE]
                if event.column == _MK_AGE:
                    age_val = event.value
                type_val = df.at[row, _MK_TYPE]
                if event.column == _MK_TYPE:
                    type_val = event.value
                well = self._get_selected_well_obj()
                if well is None:
                    return
                new_marker = Marker(
                    name=name_str,
                    depth=float(depth_val),
                    age=(float(age_val) if age_val is not None else np.nan),
                    stratigraphicType=StratigraphicSurfaceType(
                        type_val or "Unknown"
                    ),
                )
                markers = list(well.getMarkers())
                markers.append(new_marker)
                self._actions.set_well_markers(well.name, markers)
                self._refresh_marker_table(well)
                self._subsidence_plot.object = self._build_subsidence_plot()
        else:
            self._push_markers()

    def _on_marker_remove(self, event: Any) -> None:
        sel = self._marker_table.selection
        if not sel:
            return
        row = sel[0]
        df = self._marker_table.value
        if row >= len(df) - 1:
            return
        well = self._get_selected_well_obj()
        if well is None:
            return
        markers = list(well.getMarkers())
        if row < len(markers):
            markers.pop(row)
            self._actions.set_well_markers(well.name, markers)
            self._refresh_marker_table(well)
            self._subsidence_plot.object = self._build_subsidence_plot()

    def _on_erase_curve(self, event: Any) -> None:
        if self._selected_well is None:
            return
        ws = self._well_settings.get(self._selected_well)
        if ws is None:
            return
        ws.subsidence_curve = None
        self._curve_editor.set_curve(None)
        self._subsidence_plot.object = self._build_subsidence_plot()
        self._build_and_push_realization_data()

    def _on_sub_type_changed(self, event: Any) -> None:
        if self._updating or self._selected_well is None:
            return
        ws = self._well_settings.get(self._selected_well)
        if ws is None:
            return
        ws.subsidence_type = event.new
        title = _SUBSIDENCE_TITLES[event.new]
        self._curve_editor.set_value_title(title)
        self._subsidence_plot.object = self._build_subsidence_plot()
        self._build_and_push_realization_data()

    def _on_subsidence_curve_changed(self, curve: Curve | None) -> None:
        if self._updating or self._selected_well is None:
            return
        ws = self._well_settings.get(self._selected_well)
        if ws is None:
            return
        ws.subsidence_curve = curve
        self._subsidence_plot.object = self._build_subsidence_plot()
        self._build_and_push_realization_data()

    # --- Layout ---

    def panel(self) -> pn.Column:
        """Return the Panel layout for this editor.

        Returns:
            A pn.Column containing the title bar, well list, and
            well detail panel.
        """
        title_row = pn.Row(
            pn.pane.Markdown(
                "### Step 4 - Realization Data",
                styles={"margin": "0"},
            ),
            pn.Spacer(),
            self._status,
            sizing_mode="stretch_width",
            align="center",
        )

        left_panel = pn.Column(
            pn.pane.Markdown(
                "*Upload a .json or .las file to add a well*",
            ),
            pn.Row(
                self._file_input,
                self._add_btn,
                align="end",
            ),
            self._well_list,
            sizing_mode="stretch_width",
            styles={"flex": "5"},
        )

        right_panel = pn.Column(
            self._detail_panel,
            sizing_mode="stretch_width",
            styles={"flex": "5"},
        )

        master_detail = pn.Row(
            left_panel,
            pn.Spacer(width=10),
            right_panel,
            sizing_mode="stretch_width",
        )

        return pn.Column(
            title_row,
            master_detail,
            sizing_mode="stretch_width",
        )
