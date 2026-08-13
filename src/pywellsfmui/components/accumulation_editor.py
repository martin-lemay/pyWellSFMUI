from __future__ import annotations

import contextlib
import io
import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pywellsfm.model.AccumulationModel import (
        AccumulationModelElementBase,
    )
    from pywellsfm.model.Curve import AccumulationCurve

import numpy as np
import pandas as pd
import panel as pn
import param
import plotly.graph_objects as go
from pywellsfm.model import (
    AccumulationModelElementGaussian,
    AccumulationModelElementOptimum,
)

from pywellsfmui.state.actions import Actions
from pywellsfmui.state.app_state import AppState
from pywellsfmui.theme import Colors, status_html

_NEW_ELEMENT = "New Element..."
_NEW_CURVE = "New Curve..."
_NEW_POINT = "New..."
_MODEL_TYPES = ["Gaussian", "EnvironmentOptimum"]
_COL_X = "X"
_COL_Y = "Y"
_TITLE_X = "Env. Factor Value"
_TITLE_Y = "Reduction Coefficient"

logger = logging.getLogger(__name__)


class AccumulationEditor(param.Parameterized):
    """Reusable accumulation model editor.

    Master-detail layout: element list on the left,
    element definition on the right. Reads from
    AppState.accumulation_model, writes through Actions.
    """

    def __init__(
        self,
        state: AppState,
        actions: Actions,
        **params: object,
    ) -> None:
        """Initialize the accumulation model editor."""
        super().__init__(**params)
        self._state = state
        self._actions = actions
        self._updating_elements = False
        self._updating_curves = False
        self._updating_points = False
        self._updating_detail = False

        # Top bar
        self._new_btn = pn.widgets.Button(
            label="New Model",
            color="primary",
            width=120,
            align="center",
        )
        self._file_input = pn.widgets.FileInput(
            accept=".json",
            width=250,
            align="center",
            label="Load Accumulation Model",
        )
        self._download = pn.widgets.FileDownload(
            callback=self._make_download,
            filename="accumulation_model.json",
            label="Save Accum. Model",
            color="success",
            width=120,
            align="center",
        )

        # Left panel — element table
        self._element_df = pd.DataFrame(columns=["Name"])
        self._element_table = pn.widgets.Tabulator(
            self._element_df,
            sizing_mode="stretch_width",
            height=200,
            show_index=False,
            selectable=1,
            widths={"Name": "100%"},
            editors={
                "Name": {
                    "type": "input",
                    "selectContents": True,
                },
            },
            configuration={
                "editTriggerEvent": "dblclick",
            },
        )
        self._init_from_facies_btn = pn.widgets.Button(
            label="Init From Facies Model",
            color="default",
            width=160,
            height=28,
        )
        self._remove_element_btn = pn.widgets.Button(
            label="Remove",
            color="danger",
            width=80,
            height=28,
        )

        # Right panel — element definition
        self._type_select = pn.widgets.Select(
            label="Model Type",
            options=_MODEL_TYPES,
            value="Gaussian",
            width=200,
            visible=False,
        )
        self._rate_input = pn.widgets.FloatInput(
            label="Mean Accumulation Rate (m/My)",
            value=100.0,
            step=1.0,
            start=0.0,
            width=250,
            visible=False,
        )
        self._stddev_input = pn.widgets.FloatInput(
            label="Std Dev Factor",
            value=0.2,
            step=0.01,
            start=0.0,
            width=250,
            visible=False,
        )

        # Curves sub-panel (for EnvironmentOptimum)
        self._curve_df = pd.DataFrame(columns=["Condition"])
        self._curve_table = pn.widgets.Tabulator(
            self._curve_df,
            sizing_mode="stretch_width",
            height=180,
            show_index=False,
            selectable=1,
            widths={"Condition": "100%"},
            titles={"Condition": "Env. Condition"},
            editors={
                "Condition": {
                    "type": "input",
                    "selectContents": True,
                },
            },
            configuration={
                "editTriggerEvent": "dblclick",
            },
        )
        self._remove_curve_btn = pn.widgets.Button(
            label="Remove",
            color="danger",
            width=80,
            height=28,
        )

        # Point table
        self._point_df = pd.DataFrame(columns=[_COL_X, _COL_Y])
        self._point_table = pn.widgets.Tabulator(
            self._point_df,
            sizing_mode="stretch_width",
            height=180,
            show_index=False,
            selectable=1,
            widths={_COL_X: "50%", _COL_Y: "50%"},
            titles={_COL_X: _TITLE_X, _COL_Y: _TITLE_Y},
            editors={
                _COL_X: {
                    "type": "number",
                    "selectContents": True,
                },
                _COL_Y: {
                    "type": "number",
                    "selectContents": True,
                },
            },
            configuration={
                "editTriggerEvent": "dblclick",
            },
            disabled=True,
        )
        self._remove_point_btn = pn.widgets.Button(
            label="Remove",
            color="danger",
            width=80,
            height=28,
        )

        self._curves_title = pn.pane.Markdown(
            "**Reduction Curves**", visible=False
        )
        self._load_curve_input = pn.widgets.FileInput(
            accept=".json,.csv",
            width=250,
            align="center",
            label="Load Reduction Curve",
        )

        self._reduction_plot = pn.pane.Plotly(
            self._build_reduction_plot(),
            sizing_mode="stretch_width",
            height=250,
        )

        # Top part: env conditions list + load file
        self._curves_top_panel = pn.Column(
            self._curves_title,
            self._load_curve_input,
            pn.Row(
                pn.Spacer(),
                self._remove_curve_btn,
                sizing_mode="stretch_width",
            ),
            self._curve_table,
            sizing_mode="stretch_width",
            visible=False,
        )

        # Bottom part: curve data table (left) + plot (right)
        self._curves_bottom_panel = pn.Row(
            pn.Column(
                pn.pane.Markdown("**Curve Data**"),
                pn.Row(
                    pn.Spacer(),
                    self._remove_point_btn,
                    sizing_mode="stretch_width",
                ),
                self._point_table,
                sizing_mode="stretch_width",
            ),
            self._reduction_plot,
            sizing_mode="stretch_width",
            visible=False,
        )

        # Status
        self._status = pn.pane.HTML(
            self._build_status_html(),
            sizing_mode="fixed",
        )

        # Wire callbacks
        self._new_btn.on_click(self._on_new_model)
        self._file_input.param.watch(self._on_file_loaded, "value")
        self._init_from_facies_btn.on_click(self._on_init_from_facies)
        self._remove_element_btn.on_click(self._on_remove_element)
        self._element_table.param.watch(self._on_element_selected, "selection")
        self._element_table.on_edit(self._on_element_table_edit)
        self._type_select.param.watch(self._on_type_changed, "value")
        self._rate_input.param.watch(self._on_rate_changed, "value")
        self._stddev_input.param.watch(self._on_stddev_changed, "value")
        self._load_curve_input.param.watch(self._on_curve_file_loaded, "value")
        self._remove_curve_btn.on_click(self._on_remove_curve)
        self._curve_table.param.watch(self._on_curve_selected, "selection")
        self._curve_table.on_edit(self._on_curve_table_edit)
        self._remove_point_btn.on_click(self._on_remove_point)
        self._point_table.on_edit(self._on_point_table_edit)

        # Watch state changes
        self._state.param.watch(
            lambda event: self._refresh(),
            ["accumulation_model"],
        )

        self._refresh()

    # --- DataFrame builders ---

    def _build_element_df(self) -> pd.DataFrame:
        rows: list[dict] = []
        model = self._state.accumulation_model
        if model is not None:
            for name in sorted(model.elements.keys()):
                rows.append({"Name": name})
        rows.append({"Name": _NEW_ELEMENT})
        return pd.DataFrame(rows)

    def _build_curve_df(self) -> pd.DataFrame:
        elem = self._get_selected_optimum_element()
        rows: list[dict] = []
        if elem is not None:
            for name in sorted(elem.accumulationCurves.keys()):
                rows.append({"Condition": name})
        if self._get_selected_element_name() is not None:
            sel_elem = self._get_selected_element()
            if isinstance(
                sel_elem,
                AccumulationModelElementOptimum,
            ):
                rows.append({"Condition": _NEW_CURVE})
        return pd.DataFrame(rows)

    def _build_point_df(self) -> pd.DataFrame:
        curve = self._get_selected_curve()
        rows: list[dict] = []
        if curve is not None:
            for x, y in zip(curve._abscissa, curve._ordinate, strict=False):
                rows.append({_COL_X: float(x), _COL_Y: float(y)})
            rows.append({_COL_X: _NEW_POINT, _COL_Y: None})
        df = pd.DataFrame(rows)
        if not df.empty:
            df[_COL_X] = df[_COL_X].astype(object)
            df[_COL_Y] = df[_COL_Y].astype(object)
        return df

    # --- Styling ---

    def _style_placeholder(self, row: pd.Series) -> list[str]:
        for val in row.values:
            if val in (
                _NEW_ELEMENT,
                _NEW_CURVE,
                _NEW_POINT,
            ):
                return ["font-style: italic; color: #999"] * len(row)
        return [""] * len(row)

    # --- Selection helpers ---

    def _get_selected_element_name(
        self,
    ) -> str | None:
        sel = self._element_table.selection
        if not sel:
            return None
        row = sel[0]
        df = self._element_table.value
        if row >= len(df) - 1:
            return None
        return str(df.at[row, "Name"])

    def _get_selected_element(
        self,
    ) -> AccumulationModelElementBase | None:
        name = self._get_selected_element_name()
        if name is None or self._state.accumulation_model is None:
            return None
        return self._state.accumulation_model.getElementModel(name)

    def _get_selected_optimum_element(
        self,
    ) -> AccumulationModelElementOptimum | None:
        elem = self._get_selected_element()
        if isinstance(elem, AccumulationModelElementOptimum):
            return elem
        return None

    def _get_selected_curve_name(
        self,
    ) -> str | None:
        sel = self._curve_table.selection
        if not sel:
            return None
        row = sel[0]
        df = self._curve_table.value
        if row >= len(df) - 1:
            return None
        return str(df.at[row, "Condition"])

    def _get_selected_curve(
        self,
    ) -> AccumulationCurve | None:
        elem = self._get_selected_optimum_element()
        curve_name = self._get_selected_curve_name()
        if elem is None or curve_name is None:
            return None
        return elem.getAccumulationCurve(curve_name)

    # --- Status ---

    def _is_element_valid(
        self,
        elem: AccumulationModelElementBase,
    ) -> bool:
        if elem.accumulationRate <= 0:
            return False
        if isinstance(elem, AccumulationModelElementGaussian):
            return elem.std_dev_factor > 0
        if isinstance(elem, AccumulationModelElementOptimum):
            if not elem.accumulationCurves:
                return False
            return all(
                len(c._abscissa) >= 2 for c in elem.accumulationCurves.values()
            )
        return False

    def _build_status_html(self) -> str:
        model = self._state.accumulation_model
        if model is None:
            return status_html("No accumulation model", Colors.ERROR)
        count = len(model.elements)
        if count == 0:
            return status_html(
                "Accumulation model: 0 elements",
                Colors.ERROR,
            )
        all_valid = all(
            self._is_element_valid(e) for e in model.elements.values()
        )
        if all_valid:
            return status_html(
                f"{count} valid elements",
                Colors.SUCCESS,
            )
        return status_html(
            f"{count} elements, incomplete",
            Colors.WARNING,
        )

    def _build_reduction_plot(self) -> go.Figure:
        """Build a Plotly figure for the selected reduction curve."""
        fig = go.Figure()
        curve = self._get_selected_curve()
        curve_name = self._get_selected_curve_name()
        if curve is not None and len(curve._abscissa) > 0:
            fig.add_trace(
                go.Scatter(
                    x=curve._abscissa,
                    y=curve._ordinate,
                    mode="lines+markers",
                    name=curve_name or "Reduction",
                )
            )
        fig.update_layout(
            xaxis_title=curve_name or "Env. Factor Value",
            yaxis_title="Reduction Coefficient",
            yaxis_range=[0, 1.05],
            margin={"l": 50, "r": 20, "t": 30, "b": 50},
            height=250,
        )
        return fig

    # --- Refresh ---

    def _refresh(self) -> None:
        self._update_element_table()
        self._status.object = self._build_status_html()
        self._update_element_detail()

    def _update_element_table(self) -> None:
        self._updating_elements = True
        prev_sel = self._element_table.selection
        df = self._build_element_df()
        self._element_table.value = df
        self._element_table.style.apply(self._style_placeholder, axis=1)
        self._element_table.param.trigger("value")
        if prev_sel and prev_sel[0] < len(df) - 1:
            self._element_table.selection = prev_sel
        self._updating_elements = False

    def _update_element_detail(self) -> None:
        elem = self._get_selected_element()
        has_elem = elem is not None
        self._type_select.visible = has_elem
        self._rate_input.visible = has_elem
        if not has_elem or elem is None:
            self._stddev_input.visible = False
            self._curves_top_panel.visible = False
            self._curves_bottom_panel.visible = False
            return
        is_gaussian = isinstance(elem, AccumulationModelElementGaussian)
        is_optimum = isinstance(elem, AccumulationModelElementOptimum)
        # Guard against spurious callbacks while syncing
        self._updating_detail = True
        self._type_select.value = (
            "Gaussian" if is_gaussian else "EnvironmentOptimum"
        )
        self._rate_input.label = (
            "Mean Accumulation Rate (m/My)"
            if is_gaussian
            else "Maximum Accumulation Rate (m/My)"
        )
        self._rate_input.value = elem.accumulationRate
        self._stddev_input.visible = is_gaussian
        if is_gaussian:
            self._stddev_input.value = elem.std_dev_factor
        self._updating_detail = False
        self._curves_top_panel.visible = is_optimum
        if is_optimum:
            self._update_curve_table()
        else:
            self._curves_bottom_panel.visible = False

    def _update_curve_table(self) -> None:
        self._updating_curves = True
        prev_sel = self._curve_table.selection
        df = self._build_curve_df()
        self._curve_table.value = df
        self._curve_table.style.apply(self._style_placeholder, axis=1)
        self._curve_table.param.trigger("value")
        if prev_sel and prev_sel[0] < len(df) - 1:
            self._curve_table.selection = prev_sel
        self._updating_curves = False
        self._update_point_table()

    def _update_point_table(self) -> None:
        self._updating_points = True
        curve_name = self._get_selected_curve_name()
        has_curve = self._get_selected_curve() is not None
        self._curves_bottom_panel.visible = has_curve
        x_title = curve_name if curve_name else _TITLE_X
        self._point_table.titles = {_COL_X: x_title, _COL_Y: _TITLE_Y}
        df = self._build_point_df()
        self._point_table.value = df
        self._point_table.style.apply(self._style_placeholder, axis=1)
        self._point_table.param.trigger("value")
        self._point_table.disabled = not has_curve
        self._reduction_plot.object = self._build_reduction_plot()
        self._updating_points = False

    # --- Callbacks ---

    def _on_new_model(self, event: Any) -> None:
        self._actions.create_empty_accumulation_model()

    def _on_file_loaded(self, event: Any) -> None:
        if self._file_input.value is None:
            return
        try:
            self._actions.load_accumulation_model_from_bytes(
                self._file_input.value,
                filename=(self._file_input.filename or ""),
            )
        except Exception:
            logger.debug(
                "Load accumulation model failed",
                exc_info=True,
            )

    def _make_download(self) -> io.BytesIO:
        data = self._actions.export_accumulation_model_as_json()
        json_bytes = json.dumps(data, indent=2).encode("utf-8")
        return io.BytesIO(json_bytes)

    def _on_element_table_edit(self, event: Any) -> None:
        if self._updating_elements:
            return
        row = event.row
        df = self._element_table.value
        is_last = row == len(df) - 1
        if is_last:
            name = str(event.value).strip()
            if name and name != _NEW_ELEMENT:
                with contextlib.suppress(ValueError):
                    self._actions.add_accumulation_element(name)
        else:
            self._element_table.patch({"Name": [(row, event.old)]})

    def _on_init_from_facies(self, event: Any) -> None:
        fm = self._state.facies_model
        if fm is None:
            return
        self._actions.create_empty_accumulation_model()
        for facies in sorted(fm.faciesSet, key=lambda f: f.name):
            with contextlib.suppress(ValueError):
                self._actions.add_accumulation_element(facies.name)

    def _on_remove_element(self, event: Any) -> None:
        name = self._get_selected_element_name()
        if name is None:
            return
        with contextlib.suppress(ValueError):
            self._actions.remove_accumulation_element(name)

    def _on_element_selected(self, event: Any) -> None:
        if self._updating_elements:
            return
        self._update_element_detail()

    def _on_type_changed(self, event: Any) -> None:
        if self._updating_detail:
            return
        name = self._get_selected_element_name()
        if name is None:
            return
        with contextlib.suppress(ValueError):
            self._actions.set_accumulation_element_type(name, event.new)

    def _on_rate_changed(self, event: Any) -> None:
        if self._updating_detail:
            return
        name = self._get_selected_element_name()
        if name is None or event.new is None:
            return
        with contextlib.suppress(ValueError):
            self._actions.update_accumulation_element_rate(
                name, float(event.new)
            )

    def _on_stddev_changed(self, event: Any) -> None:
        if self._updating_detail:
            return
        name = self._get_selected_element_name()
        if name is None or event.new is None:
            return
        with contextlib.suppress(ValueError):
            self._actions.update_accumulation_element_stddev(
                name, float(event.new)
            )

    def _on_curve_table_edit(self, event: Any) -> None:
        if self._updating_curves:
            return
        elem_name = self._get_selected_element_name()
        if not elem_name:
            return
        row = event.row
        df = self._curve_table.value
        is_last = row == len(df) - 1
        if is_last:
            name = str(event.value).strip()
            if name and name != _NEW_CURVE:
                with contextlib.suppress(ValueError):
                    self._actions.add_accumulation_curve(elem_name, name)
        else:
            self._curve_table.patch({"Condition": [(row, event.old)]})

    def _parse_curve_bytes(
        self, data: bytes, filename: str
    ) -> list[tuple[str, np.ndarray, np.ndarray]]:
        """Parse curve file bytes into (name, x, y) tuples."""
        if filename.lower().endswith(".csv"):
            df = pd.read_csv(io.BytesIO(data))
            if df.shape[1] < 2:
                return []
            name = str(df.columns[0]).strip()
            x = pd.to_numeric(df.iloc[:, 0], errors="coerce").dropna().values
            result = []
            for col_idx in range(1, df.shape[1]):
                y = (
                    pd.to_numeric(df.iloc[:, col_idx], errors="coerce")
                    .dropna()
                    .values
                )
                n = min(len(x), len(y))
                if n >= 2:
                    result.append((name, x[:n].copy(), y[:n].copy()))
            return result
        # JSON
        obj = json.loads(data.decode("utf-8"))
        curve_obj = obj.get("curve", {})
        name = curve_obj.get("xAxisName", "x")
        pts = curve_obj.get("data", [])
        if len(pts) < 2:
            return []
        x = np.array([float(p["x"]) for p in pts])
        y = np.array([float(p["y"]) for p in pts])
        return [(name, x, y)]

    def _on_curve_file_loaded(self, event: Any) -> None:
        if self._load_curve_input.value is None:
            return
        elem_name = self._get_selected_element_name()
        if not elem_name:
            return
        filename = self._load_curve_input.filename or "curve.json"
        data = self._load_curve_input.value
        try:
            parsed = self._parse_curve_bytes(data, filename)
            for name, x, y in parsed:
                with contextlib.suppress(ValueError):
                    self._actions.add_accumulation_curve(elem_name, name)
                with contextlib.suppress(ValueError):
                    self._actions.set_accumulation_curve_data(
                        elem_name, name, x, y
                    )
        except Exception:
            logger.debug("Load curve file failed", exc_info=True)

    def _on_remove_curve(self, event: Any) -> None:
        elem_name = self._get_selected_element_name()
        curve_name = self._get_selected_curve_name()
        if not elem_name or not curve_name:
            return
        with contextlib.suppress(ValueError):
            self._actions.remove_accumulation_curve(elem_name, curve_name)

    def _on_curve_selected(self, event: Any) -> None:
        if self._updating_curves:
            return
        self._update_point_table()

    def _validate_point(
        self,
        df: pd.DataFrame,
        row: int,
        x: float,
        y: float,
        *,
        is_new: bool,
    ) -> bool:
        """Check that y is in [0,1] and x is monotonically increasing."""
        if y < 0.0 or y > 1.0:
            return False
        n_data = len(df) - 1  # exclude placeholder row
        xs: list[float] = []
        for i in range(n_data):
            val = df.at[i, _COL_X]
            if val is None or str(val) == _NEW_POINT:
                continue
            if i == row and not is_new:
                xs.append(x)
            else:
                xs.append(float(val))
        if is_new:
            xs.append(x)
        return all(xs[i] > xs[i - 1] for i in range(1, len(xs)))

    def _revert_edit(self, event: Any) -> None:
        """Revert a table edit to its old value."""
        col = _COL_X if event.column == _COL_X else _COL_Y
        self._point_table.patch({col: [(event.row, event.old)]})

    def _on_point_table_edit(self, event: Any) -> None:
        if self._updating_points:
            return
        elem_name = self._get_selected_element_name()
        curve_name = self._get_selected_curve_name()
        if not elem_name or not curve_name:
            return
        row = event.row
        column = event.column
        value = event.value
        df = self._point_table.value
        x_col = _COL_X
        is_last = row == len(df) - 1
        if is_last:
            x_val = df.at[row, x_col]
            y_val = df.at[row, _COL_Y]
            if column == x_col:
                x_val = value
            elif column == _COL_Y:
                y_val = value
            x_str = str(x_val).strip() if x_val else ""
            if x_str == _NEW_POINT:
                x_str = ""
            if x_str and y_val is not None:
                x_f = float(x_str)
                y_f = float(y_val)
                if not self._validate_point(df, row, x_f, y_f, is_new=True):
                    self._revert_edit(event)
                    return
                with contextlib.suppress(ValueError):
                    self._actions.add_accumulation_curve_point(
                        elem_name,
                        curve_name,
                        x_f,
                        y_f,
                    )
        else:
            x_val = df.at[row, x_col]
            y_val = df.at[row, _COL_Y]
            if column == x_col:
                x_val = value
            elif column == _COL_Y:
                y_val = value
            if x_val is None or y_val is None:
                return
            x_f = float(x_val)
            y_f = float(y_val)
            if not self._validate_point(df, row, x_f, y_f, is_new=False):
                self._revert_edit(event)
                return
            with contextlib.suppress(ValueError):
                self._actions.update_accumulation_curve_point(
                    elem_name,
                    curve_name,
                    row,
                    x_f,
                    y_f,
                )

    def _on_remove_point(self, event: Any) -> None:
        elem_name = self._get_selected_element_name()
        curve_name = self._get_selected_curve_name()
        if not elem_name or not curve_name:
            return
        sel = self._point_table.selection
        if not sel:
            return
        row = sel[0]
        df = self._point_table.value
        if row >= len(df) - 1:
            return
        with contextlib.suppress(ValueError):
            self._actions.remove_accumulation_curve_point(
                elem_name, curve_name, row
            )

    def panel(self) -> pn.Column:
        """Assemble and return the full layout."""
        left_panel = pn.Column(
            pn.pane.Markdown("**Element List**"),
            pn.Row(
                self._init_from_facies_btn,
                pn.Spacer(),
                self._remove_element_btn,
                sizing_mode="stretch_width",
            ),
            self._element_table,
            min_width=200,
            sizing_mode="stretch_width",
        )

        detail_left = pn.Column(
            pn.pane.Markdown("**Selected Element**"),
            self._type_select,
            self._rate_input,
            self._stddev_input,
            sizing_mode="stretch_width",
        )
        right_panel = pn.Column(
            pn.Row(
                detail_left,
                self._curves_top_panel,
                sizing_mode="stretch_width",
            ),
            self._curves_bottom_panel,
            sizing_mode="stretch_width",
        )

        master_detail = pn.FlexBox(
            left_panel,
            right_panel,
            flex_direction="row",
            gap="10px",
            sizing_mode="stretch_width",
        )
        left_panel.styles = {"flex": "1 1 33%", "min-width": "200px"}
        right_panel.styles = {"flex": "2 1 66%"}

        title_row = pn.Row(
            pn.pane.Markdown(
                "### Step 1 - Accumulation Model",
                styles={"margin": "0"},
            ),
            pn.Spacer(),
            self._status,
            sizing_mode="stretch_width",
            align="center",
        )

        button_row = pn.Row(
            self._file_input,
            pn.Spacer(),
            self._new_btn,
            self._download,
            sizing_mode="stretch_width",
            align="center",
        )

        return pn.Column(
            title_row,
            button_row,
            master_detail,
            sizing_mode="stretch_width",
        )
