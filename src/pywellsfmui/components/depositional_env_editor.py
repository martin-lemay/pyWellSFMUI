import io
import json
import logging

import pandas as pd
import panel as pn
import param


from pywellsfm.model import Curve
from pywellsfm.model.EnvironmentConditionModel import (
    EnvironmentConditionModelConstant,
    EnvironmentConditionModelCurve,
    EnvironmentConditionModelGaussian,
    EnvironmentConditionModelTriangular,
    EnvironmentConditionModelUniform,
)
from pywellsfm.utils import IntervalDistanceMethod

from pywellsfmui.components.curve_editor import CurveEditor
from pywellsfmui.state.actions import Actions
from pywellsfmui.state.app_state import AppState
from pywellsfmui.theme import Colors, status_html

_NEW_ENV = "New Environment..."
_NEW_COND = "New Condition..."

_MODEL_TYPES = ["Constant", "Uniform", "Triangular", "Gaussian", "Curve"]

_INTERVAL_METHODS = [m.value for m in IntervalDistanceMethod]

_MODEL_TYPE_MAP: dict[type, str] = {
    EnvironmentConditionModelConstant: "Constant",
    EnvironmentConditionModelUniform: "Uniform",
    EnvironmentConditionModelTriangular: "Triangular",
    EnvironmentConditionModelGaussian: "Gaussian",
    EnvironmentConditionModelCurve: "Curve",
}

logger = logging.getLogger(__name__)


class DepositionalEnvEditor(param.Parameterized):
    """Editor for depositional environments and conditions.

    3-column layout in multi-env mode, 2-column in global.
    """

    def __init__(
        self,
        state: AppState,
        actions: Actions,
        **params,
    ) -> None:
        super().__init__(**params)
        self._state = state
        self._actions = actions
        self._updating = False
        self._current_mode: bool | None = None

        self._build_widgets()
        self._wire_callbacks()
        self._watch_state()
        self._refresh()

    # --- Widget construction ---

    def _build_widgets(self) -> None:
        # Mode toggle
        _GLOBAL_LABEL = "Global mode: environmental conditions are defined globally"
        _ENVS_LABEL = (
            "Environments mode: environmental conditions are defined per environment"
        )
        self._mode_labels = {
            _GLOBAL_LABEL: False,
            _ENVS_LABEL: True,
        }
        self._mode_toggle = pn.widgets.RadioBoxGroup(
            options=list(self._mode_labels.keys()),
            value=_GLOBAL_LABEL,
            inline=False,
        )

        # Global mode buttons
        self._global_load = pn.widgets.FileInput(
            accept=".json",
            width=250,
        )
        self._global_save = pn.widgets.FileDownload(
            callback=self._make_global_download,
            filename="environment_conditions.json",
            label="Save Conditions",
            color="success",
            width=120,
        )

        # Multi-env buttons
        self._multi_load = pn.widgets.FileInput(
            accept=".json",
            width=250,
        )
        self._multi_save = pn.widgets.FileDownload(
            callback=self._make_multi_download,
            filename="de_simulation.json",
            label="Save DE Simulation",
            color="success",
            width=120,
        )
        self._new_model_btn = pn.widgets.MenuButton(
            label="New Model",
            items=[
                ("Empty", "empty"),
                ("Carbonate Open Ramp", "carbonate_open_ramp"),
                (
                    "Carbonate Protected Ramp",
                    "carbonate_protected_ramp",
                ),
            ],
            color="primary",
            width=160,
        )

        # Environment list table (multi-env)
        self._env_df = pd.DataFrame(columns=["Name"])
        self._env_table = pn.widgets.Tabulator(
            self._env_df,
            sizing_mode="stretch_width",
            height=200,
            show_index=False,
            selectable=1,
            editors={
                "Name": {
                    "type": "input",
                    "selectContents": True,
                },
            },
            configuration={"editTriggerEvent": "dblclick"},
        )
        self._remove_env_btn = pn.widgets.Button(
            label="Remove",
            color="danger",
            width=80,
            height=28,
        )

        # Environment detail widgets (multi-env)
        self._env_name_input = pn.widgets.TextInput(
            label="Name",
            width=200,
        )
        self._distality_input = pn.widgets.FloatInput(
            label="Distality",
            width=120,
            step=0.1,
            value=None,
        )
        self._wd_min = pn.widgets.FloatInput(
            label="Min",
            width=100,
            step=1.0,
            value=0.0,
        )
        self._wd_max = pn.widgets.FloatInput(
            label="Max",
            width=100,
            step=0.1,
        )

        # Conditions table
        self._cond_df = pd.DataFrame(
            columns=["Name", "Type"],
        )
        self._cond_table = pn.widgets.Tabulator(
            self._cond_df,
            sizing_mode="stretch_width",
            height=180,
            show_index=False,
            selectable=1,
            editors={
                "Name": {
                    "type": "input",
                    "selectContents": True,
                },
                "Type": None,
            },
            configuration={"editTriggerEvent": "dblclick"},
        )
        self._remove_cond_btn = pn.widgets.Button(
            label="Remove",
            color="danger",
            width=80,
            height=28,
        )

        # Condition detail widgets
        self._cond_name_display = pn.pane.Markdown(
            "",
            sizing_mode="stretch_width",
        )
        self._cond_type_select = pn.widgets.Select(
            label="Model Type",
            options=_MODEL_TYPES,
            value="Uniform",
            width=150,
        )
        self._cond_value = pn.widgets.FloatInput(
            label="Value",
            width=100,
            step=0.1,
        )
        self._cond_min = pn.widgets.FloatInput(
            label="Min",
            width=100,
            step=0.1,
            value=0.0,
        )
        self._cond_max = pn.widgets.FloatInput(
            label="Max",
            width=100,
            step=0.1,
            value=1.0,
        )
        self._cond_mode = pn.widgets.FloatInput(
            label="Mode",
            width=100,
            step=0.1,
        )
        self._cond_mean = pn.widgets.FloatInput(
            label="Mean",
            width=100,
            step=0.1,
        )
        self._cond_stddev = pn.widgets.FloatInput(
            label="Std Dev",
            width=100,
            step=0.1,
        )

        # Curve-type condition widgets
        self._cond_related_input = pn.widgets.TextInput(
            label="Related Condition (X-axis)",
            placeholder="e.g. waterDepth, age",
            width=200,
        )
        self._cond_curve_editor = CurveEditor(
            age_title="X",
            value_title="Y",
            file_label="Load Curve",
            on_curve_changed=self._on_cond_curve_data_changed,
        )

        # DE Simulator settings (multi-env only)
        self._weights_df = pd.DataFrame(
            columns=["Environment", "Weight"],
        )
        self._weights_table = pn.widgets.Tabulator(
            self._weights_df,
            sizing_mode="stretch_width",
            height=150,
            show_index=False,
            editors={
                "Environment": None,
                "Weight": {
                    "type": "number",
                    "selectContents": True,
                },
            },
            configuration={"editTriggerEvent": "dblclick"},
        )
        self._wd_sigma = pn.widgets.FloatInput(
            label="waterDepth sigma",
            value=2.0,
            step=0.1,
            start=0.01,
            width=120,
        )
        self._wd_weight = pn.widgets.FloatInput(
            label="waterDepth weight",
            value=1.0,
            step=0.1,
            start=0.0,
            width=120,
        )
        self._trans_sigma = pn.widgets.FloatInput(
            label="transition sigma",
            value=1.0,
            step=0.1,
            start=0.01,
            width=120,
        )
        self._trans_weight = pn.widgets.FloatInput(
            label="transition weight",
            value=1.0,
            step=0.1,
            start=0.0,
            width=120,
        )
        self._trend_sigma = pn.widgets.FloatInput(
            label="trend sigma",
            value=2.0,
            step=0.1,
            start=0.01,
            width=120,
        )
        self._trend_window = pn.widgets.IntInput(
            label="trend window",
            value=5,
            step=1,
            start=2,
            width=120,
        )
        self._trend_weight = pn.widgets.FloatInput(
            label="trend weight",
            value=1.0,
            step=0.1,
            start=0.0,
            width=120,
        )
        self._interval_method = pn.widgets.Select(
            label="interval distance method",
            options=_INTERVAL_METHODS,
            value="gap_overlapping_width",
            width=180,
        )

        # Status
        self._status = pn.pane.HTML(
            self._build_status_html(),
            sizing_mode="fixed",
        )

    # --- Callback wiring ---

    def _wire_callbacks(self) -> None:
        self._mode_toggle.param.watch(
            self._on_mode_changed,
            "value",
        )
        self._global_load.param.watch(
            self._on_global_load,
            "value",
        )
        self._multi_load.param.watch(
            self._on_multi_load,
            "value",
        )
        self._new_model_btn.on_click(self._on_new_model)
        self._env_table.param.watch(
            self._on_env_selected,
            "selection",
        )
        self._env_table.on_edit(self._on_env_table_edit)
        self._remove_env_btn.on_click(self._on_remove_env)
        self._env_name_input.param.watch(
            self._on_env_name_changed,
            "value",
        )
        self._distality_input.param.watch(
            self._on_distality_changed,
            "value",
        )
        for w in (self._wd_min, self._wd_max):
            w.param.watch(self._on_wd_param_changed, "value")
        self._cond_table.param.watch(
            self._on_cond_selected,
            "selection",
        )
        self._cond_table.on_edit(self._on_cond_table_edit)
        self._remove_cond_btn.on_click(self._on_remove_cond)
        self._cond_type_select.param.watch(
            self._on_cond_type_changed,
            "value",
        )
        for w in (
            self._cond_value,
            self._cond_min,
            self._cond_max,
            self._cond_mode,
            self._cond_mean,
            self._cond_stddev,
        ):
            w.param.watch(
                self._on_cond_param_changed,
                "value",
            )
        self._cond_related_input.param.watch(
            self._on_cond_param_changed,
            "value",
        )
        self._weights_table.on_edit(self._on_weight_edit)
        for w in (
            self._wd_sigma,
            self._wd_weight,
            self._trans_sigma,
            self._trans_weight,
            self._trend_sigma,
            self._trend_window,
            self._trend_weight,
            self._interval_method,
        ):
            w.param.watch(
                self._on_de_param_changed,
                "value",
            )

    def _watch_state(self) -> None:
        self._state.param.watch(
            lambda e: self._refresh(),
            [
                "depositional_env_model",
                "global_env_conditions",
                "use_de_simulator",
                "de_simulator_weights",
                "de_simulator_params",
            ],
        )

    # --- Selection helpers ---

    def _get_selected_env_name(self) -> str | None:
        sel = self._env_table.selection
        if not sel:
            return None
        row = sel[0]
        df = self._env_table.value
        if row >= len(df) - 1:
            return None  # placeholder row
        return str(df.at[row, "Name"])

    def _get_selected_cond_name(self) -> str | None:
        sel = self._cond_table.selection
        if not sel:
            return None
        row = sel[0]
        df = self._cond_table.value
        if row >= len(df) - 1:
            return None
        return str(df.at[row, "Name"])

    def _current_env_name(self) -> str:
        """Return 'global' in global mode, else selected env."""
        if not self._state.use_de_simulator:
            return "global"
        return self._get_selected_env_name() or ""

    # --- DataFrame builders ---

    def _build_env_df(self) -> pd.DataFrame:
        rows: list[dict] = []
        model = self._state.depositional_env_model
        if model is not None:
            for env in model.environments:
                rows.append({"Name": env.name})
        rows.append({"Name": _NEW_ENV})
        return pd.DataFrame(rows)

    def _build_cond_df(self) -> pd.DataFrame:
        rows: list[dict] = []
        env_name = self._current_env_name()
        ecm = self._get_conditions_model_for_display(env_name)
        if ecm is not None:
            for name in sorted(ecm.environmentConditionNames):
                model = ecm.envConditionModels[name]
                type_label = _MODEL_TYPE_MAP.get(
                    type(model),
                    "Unknown",
                )
                rows.append({"Name": name, "Type": type_label})
        rows.append({"Name": _NEW_COND, "Type": ""})
        return pd.DataFrame(rows)

    def _get_conditions_model_for_display(self, env_name):
        if env_name == "global":
            return self._state.global_env_conditions
        if not env_name:
            return None
        model = self._state.depositional_env_model
        if model is None:
            return None
        env = model.getEnvironmentByName(env_name)
        if env is None:
            return None
        return env.envConditionsModel

    def _build_weights_df(self) -> pd.DataFrame:
        weights = self._state.de_simulator_weights
        rows = [{"Environment": k, "Weight": v} for k, v in sorted(weights.items())]
        return pd.DataFrame(
            rows,
            columns=["Environment", "Weight"],
        )

    # --- Styling ---

    def _style_env_placeholder(self, row):
        if row["Name"] == _NEW_ENV:
            return ["font-style: italic; color: #999"] * len(row)
        return [""] * len(row)

    def _style_cond_placeholder(self, row):
        if row["Name"] == _NEW_COND:
            return ["font-style: italic; color: #999"] * len(row)
        return [""] * len(row)

    # --- Status ---

    def _build_status_html(self) -> str:
        if not self._state.use_de_simulator:
            ecm = self._state.global_env_conditions
            n = len(ecm.environmentConditionNames) if ecm else 0
            color = Colors.SUCCESS if n > 0 else Colors.WARNING
            return status_html(
                f"Global: {n} conditions",
                color,
            )
        model = self._state.depositional_env_model
        if model is None or model.isEmpty():
            return status_html(
                "No environments",
                Colors.ERROR,
            )
        n = model.getEnvironmentCount()
        all_ok = all(
            len(e.envConditionsModel.environmentConditionNames) > 0
            for e in model.environments
        )
        if all_ok:
            return status_html(
                f"{n} environments",
                Colors.SUCCESS,
            )
        return status_html(
            f"{n} environments, some incomplete",
            Colors.WARNING,
        )

    # --- Refresh methods ---

    def _refresh(self) -> None:
        self._updating = True
        self._status.object = self._build_status_html()
        is_multi = self._state.use_de_simulator
        labels = list(self._mode_labels.keys())
        self._mode_toggle.value = labels[1] if is_multi else labels[0]
        # Only rebuild layout when mode actually changed
        if hasattr(self, "_main_col") and self._current_mode != is_multi:
            self._current_mode = is_multi
            self._rebuild_layout()
        if is_multi:
            self._refresh_env_table()
            self._refresh_weights_table()
            self._refresh_de_params()
        self._refresh_cond_table()
        self._updating = False

    def _refresh_env_table(self) -> None:
        prev_sel = self._env_table.selection
        df = self._build_env_df()
        self._env_table.value = df
        self._env_table.style.apply(
            self._style_env_placeholder,
            axis=1,
        )
        if prev_sel and prev_sel[0] < len(df) - 1:
            self._env_table.selection = prev_sel
        self._refresh_env_detail()

    def _refresh_env_detail(self) -> None:
        env_name = self._get_selected_env_name()
        if env_name is None:
            self._env_name_input.value = ""
            self._distality_input.value = None
            return
        model = self._state.depositional_env_model
        if model is None:
            return
        env = model.getEnvironmentByName(env_name)
        if env is None:
            return
        self._env_name_input.value = env.name
        self._distality_input.value = env.distality
        wd = env.waterDepthModel
        if hasattr(wd, "minValue"):
            self._wd_min.value = wd.minValue
            self._wd_max.value = wd.maxValue

    def _refresh_cond_table(self) -> None:
        prev_sel = self._cond_table.selection
        df = self._build_cond_df()
        self._cond_table.value = df
        self._cond_table.style.apply(
            self._style_cond_placeholder,
            axis=1,
        )
        if prev_sel and prev_sel[0] < len(df) - 1:
            self._cond_table.selection = prev_sel
        self._refresh_cond_detail()

    def _refresh_cond_detail(self) -> None:
        cond_name = self._get_selected_cond_name()
        if cond_name is None:
            self._cond_name_display.object = ""
            if hasattr(self, "_cond_detail_col"):
                self._rebuild_cond_detail_col()
            return
        self._cond_name_display.object = f"**Model for {cond_name} condition**"
        env_name = self._current_env_name()
        ecm = self._get_conditions_model_for_display(env_name)
        if ecm is None:
            return
        cond = ecm.envConditionModels.get(cond_name)
        if cond is None:
            return
        cond_type = _MODEL_TYPE_MAP.get(
            type(cond),
            "Uniform",
        )
        self._cond_type_select.value = cond_type
        self._sync_cond_fields(cond_type, cond)
        if hasattr(self, "_cond_detail_col"):
            self._rebuild_cond_detail_col()

    def _sync_cond_fields(self, cond_type, cond_model) -> None:
        if cond_type == "Constant":
            self._cond_value.value = cond_model.value
        elif cond_type == "Uniform":
            self._cond_min.value = cond_model.minValue
            self._cond_max.value = cond_model.maxValue
        elif cond_type == "Triangular":
            self._cond_min.value = cond_model.minValue
            self._cond_mode.value = cond_model.mode
            self._cond_max.value = cond_model.maxValue
        elif cond_type == "Gaussian":
            self._cond_mean.value = cond_model.meanValue
            self._cond_stddev.value = cond_model.stdDev
            self._cond_min.value = cond_model.minValue
            self._cond_max.value = cond_model.maxValue
        elif cond_type == "Curve":
            self._cond_related_input.value = cond_model.relatedConditionName
            self._cond_curve_editor.set_curve(cond_model.curve)

    def _refresh_weights_table(self) -> None:
        df = self._build_weights_df()
        self._weights_table.value = df

    def _refresh_de_params(self) -> None:
        p = self._state.de_simulator_params
        if p is None:
            return
        self._wd_sigma.value = p.waterDepth_sigma
        self._wd_weight.value = p.waterDepth_weight
        self._trans_sigma.value = p.transition_sigma
        self._trans_weight.value = p.transition_weight
        self._trend_sigma.value = p.trend_sigma
        self._trend_window.value = p.trend_window
        self._trend_weight.value = p.trend_weight
        self._interval_method.value = str(p.interval_distance_method)

    # --- Callbacks ---

    def _on_mode_changed(self, event) -> None:
        if self._updating:
            return
        enabled = self._mode_labels.get(event.new, False)
        self._actions.set_use_de_simulator(enabled)

    def _on_global_load(self, event) -> None:
        if self._global_load.value is None:
            return
        try:
            self._actions.load_global_env_conditions_from_bytes(
                self._global_load.value,
                self._global_load.filename or "",
            )
        except Exception:
            logger.debug(
                "Load global env conditions failed",
                exc_info=True,
            )

    def _make_global_download(self) -> io.BytesIO:
        data = self._actions.export_global_env_conditions_as_json()
        return io.BytesIO(
            json.dumps(data, indent=2).encode("utf-8"),
        )

    def _on_multi_load(self, event) -> None:
        if self._multi_load.value is None:
            return
        try:
            self._actions.load_de_simulation_from_bytes(
                self._multi_load.value,
                self._multi_load.filename or "",
            )
        except Exception:
            logger.debug(
                "Load DE simulation failed",
                exc_info=True,
            )

    def _make_multi_download(self) -> io.BytesIO:
        data = self._actions.export_de_simulation_as_json()
        return io.BytesIO(
            json.dumps(data, indent=2).encode("utf-8"),
        )

    def _on_new_model(self, event) -> None:
        if isinstance(event.new, str):
            template = event.new
        else:
            template = "empty"
        self._actions.create_de_model(template)

    def _on_env_selected(self, event) -> None:
        if self._updating:
            return
        self._updating = True
        self._refresh_env_detail()
        self._refresh_cond_table()
        self._updating = False

    def _deferred_refresh(self) -> None:
        """Schedule a refresh on the next event loop tick.

        Needed when mutating state from within Tabulator
        on_edit callbacks — the table can't be updated while
        it's still processing the edit event.
        """
        pn.state.execute(self._refresh)

    def _on_env_table_edit(self, event) -> None:
        if self._updating:
            return
        row = event.row
        df = self._env_table.value
        is_last = row == len(df) - 1
        if is_last:
            name = str(event.value).strip()
            if name and name != _NEW_ENV:
                try:
                    self._actions.add_environment(name)
                    self._deferred_refresh()
                except ValueError:
                    pass
        else:
            self._env_table.patch(
                {"Name": [(row, event.old)]},
            )

    def _on_remove_env(self, event) -> None:
        name = self._get_selected_env_name()
        if name:
            try:
                self._actions.remove_environment(name)
                self._deferred_refresh()
            except ValueError:
                pass

    def _on_env_name_changed(self, event) -> None:
        if self._updating:
            return
        old_name = self._get_selected_env_name()
        new_name = event.new.strip()
        if old_name and new_name and old_name != new_name:
            try:
                self._actions.rename_environment(
                    old_name,
                    new_name,
                )
                self._deferred_refresh()
            except ValueError:
                pass

    def _on_distality_changed(self, event) -> None:
        if self._updating:
            return
        env_name = self._get_selected_env_name()
        if env_name:
            try:
                self._actions.set_environment_distality(
                    env_name,
                    event.new,
                )
            except ValueError:
                pass

    def _on_wd_param_changed(self, event) -> None:
        if self._updating:
            return
        env_name = self._get_selected_env_name()
        if not env_name:
            return
        try:
            self._actions.set_environment_water_depth_model(
                env_name,
                "Uniform",
                minValue=self._wd_min.value,
                maxValue=self._wd_max.value,
            )
        except (ValueError, TypeError):
            pass

    def _on_cond_selected(self, event) -> None:
        if self._updating:
            return
        self._updating = True
        self._refresh_cond_detail()
        self._updating = False

    def _on_cond_table_edit(self, event) -> None:
        if self._updating:
            return
        row = event.row
        df = self._cond_table.value
        is_last = row == len(df) - 1
        if is_last:
            name = str(event.value).strip()
            if name and name != _NEW_COND:
                env_name = self._current_env_name()
                if env_name:
                    try:
                        self._actions.add_env_condition(
                            env_name,
                            name,
                            "Uniform",
                            minValue=0.0,
                            maxValue=1.0,
                        )
                        self._deferred_refresh()
                    except ValueError:
                        pass
        else:
            self._cond_table.patch(
                {event.column: [(row, event.old)]},
            )

    def _on_remove_cond(self, event) -> None:
        cond_name = self._get_selected_cond_name()
        env_name = self._current_env_name()
        if cond_name and env_name:
            try:
                self._actions.remove_env_condition(
                    env_name,
                    cond_name,
                )
                self._deferred_refresh()
            except ValueError:
                pass

    def _on_cond_type_changed(self, event) -> None:
        if self._updating:
            return
        if hasattr(self, "_cond_detail_col"):
            self._rebuild_cond_detail_col()
        self._apply_cond_model()

    def _on_cond_param_changed(self, event) -> None:
        if self._updating:
            return
        self._apply_cond_model()

    def _on_cond_curve_data_changed(
        self,
        curve: Curve | None,
    ) -> None:
        if self._updating:
            return
        self._apply_cond_model()

    def _apply_cond_model(self) -> None:
        cond_name = self._get_selected_cond_name()
        env_name = self._current_env_name()
        if not cond_name or not env_name:
            return
        mt = self._cond_type_select.value
        try:
            params = self._collect_cond_params(mt)
            if params is None:
                return
            self._actions.update_env_condition(
                env_name,
                cond_name,
                mt,
                **params,
            )
        except (ValueError, TypeError):
            pass

    def _collect_cond_params(self, model_type: str) -> dict | None:
        if model_type == "Constant":
            return {"value": self._cond_value.value}
        if model_type == "Uniform":
            return {
                "minValue": self._cond_min.value,
                "maxValue": self._cond_max.value,
            }
        if model_type == "Triangular":
            return {
                "minValue": self._cond_min.value,
                "modeValue": self._cond_mode.value,
                "maxValue": self._cond_max.value,
            }
        if model_type == "Gaussian":
            return {
                "meanValue": self._cond_mean.value,
                "stdDev": self._cond_stddev.value,
                "minValue": self._cond_min.value,
                "maxValue": self._cond_max.value,
            }
        if model_type == "Curve":
            related = self._cond_related_input.value.strip()
            curve = self._cond_curve_editor.get_curve()
            if not related or curve is None:
                return None
            cond_name = self._get_selected_cond_name() or ""
            c = Curve(
                related,
                cond_name,
                curve._abscissa.copy(),
                curve._ordinate.copy(),
                "linear",
            )
            return {"curve": c}
        return {}

    def _on_weight_edit(self, event) -> None:
        if self._updating:
            return
        df = self._weights_table.value
        env_name = df.at[event.row, "Environment"]
        try:
            self._actions.set_de_simulator_weight(
                str(env_name),
                float(event.value),
            )
        except ValueError:
            pass

    def _on_de_param_changed(self, event) -> None:
        if self._updating:
            return
        try:
            self._actions.set_de_simulator_params(
                waterDepth_sigma=self._wd_sigma.value,
                waterDepth_weight=self._wd_weight.value,
                transition_sigma=self._trans_sigma.value,
                transition_weight=self._trans_weight.value,
                trend_sigma=self._trend_sigma.value,
                trend_window=self._trend_window.value,
                trend_weight=self._trend_weight.value,
                interval_distance_method=(
                    IntervalDistanceMethod(self._interval_method.value)
                ),
            )
        except (ValueError, TypeError):
            pass

    # --- Dynamic field visibility ---

    def _cond_fields_for_type(
        self,
        model_type: str,
    ) -> pn.Row | pn.Column:
        if model_type == "Constant":
            return pn.Row(self._cond_value)
        if model_type == "Uniform":
            return pn.Row(self._cond_min, self._cond_max)
        if model_type == "Triangular":
            return pn.Row(
                self._cond_min,
                self._cond_mode,
                self._cond_max,
            )
        if model_type == "Gaussian":
            return pn.Row(
                self._cond_mean,
                self._cond_stddev,
                self._cond_min,
                self._cond_max,
            )
        if model_type == "Curve":
            return pn.Column(
                self._cond_related_input,
                self._cond_curve_editor.panel(),
                sizing_mode="stretch_width",
            )
        return pn.Row()

    # --- Layout ---

    def panel(self) -> pn.Column:
        title_row = pn.Row(
            pn.pane.Markdown(
                "### Step 3 - Depositional Environment And Conditions",
                styles={"margin": "0"},
            ),
            pn.Spacer(),
            self._status,
            sizing_mode="stretch_width",
            align="center",
        )

        self._global_btn_row = pn.Row(
            self._global_load,
            pn.Spacer(),
            self._global_save,
            sizing_mode="stretch_width",
        )
        self._multi_btn_row = pn.Row(
            self._multi_load,
            pn.Spacer(),
            self._new_model_btn,
            self._multi_save,
            sizing_mode="stretch_width",
        )

        self._env_list_col = pn.Column(
            pn.pane.Markdown("**Environments**"),
            pn.Row(
                pn.Spacer(),
                self._remove_env_btn,
                sizing_mode="stretch_width",
            ),
            self._env_table,
            min_width=200,
            sizing_mode="stretch_width",
        )

        self._env_detail_col = pn.Column(
            sizing_mode="stretch_width",
        )

        self._cond_detail_col = pn.Column(
            sizing_mode="stretch_width",
            min_width=200,
        )

        self._de_settings_card = pn.Card(
            pn.pane.Markdown("**Environment Weights**"),
            self._weights_table,
            pn.pane.Markdown("**DE Simulator Parameters**"),
            pn.Row(
                self._wd_sigma,
                self._wd_weight,
                self._trans_sigma,
                self._trans_weight,
            ),
            pn.Row(
                self._trend_sigma,
                self._trend_window,
                self._trend_weight,
                self._interval_method,
            ),
            title="DE Simulator Settings",
            collapsed=True,
            sizing_mode="stretch_width",
        )

        self._content_row = pn.Row(
            sizing_mode="stretch_width",
        )

        self._main_col = pn.Column(
            title_row,
            self._mode_toggle,
            sizing_mode="stretch_width",
        )

        self._current_mode = self._state.use_de_simulator
        self._rebuild_layout()
        return self._main_col

    def _rebuild_layout(self) -> None:
        is_multi = self._state.use_de_simulator

        self._main_col.objects = self._main_col.objects[:2]

        if is_multi:
            self._main_col.append(self._multi_btn_row)
            self._rebuild_env_detail_col()
            self._rebuild_cond_detail_col()
            self._content_row.objects = [
                self._env_list_col,
                pn.Spacer(width=10),
                self._env_detail_col,
                pn.Spacer(width=10),
                self._cond_detail_col,
            ]
            self._main_col.append(self._content_row)
            self._main_col.append(self._de_settings_card)
        else:
            self._main_col.append(self._global_btn_row)
            self._rebuild_cond_detail_col()
            cond_table_col = pn.Column(
                pn.pane.Markdown("**Environment Conditions**"),
                pn.Row(
                    pn.Spacer(),
                    self._remove_cond_btn,
                    sizing_mode="stretch_width",
                ),
                self._cond_table,
                min_width=250,
                sizing_mode="stretch_width",
            )
            self._content_row.objects = [
                cond_table_col,
                pn.Spacer(width=10),
                self._cond_detail_col,
            ]
            self._main_col.append(self._content_row)

    def _rebuild_env_detail_col(self) -> None:
        self._env_detail_col.objects = [
            pn.pane.Markdown("**Environment Properties**"),
            pn.Row(
                self._env_name_input,
                self._distality_input,
            ),
            pn.pane.Markdown("**Water Depth Range**"),
            pn.Row(self._wd_min, self._wd_max),
        ]

    def _rebuild_cond_detail_col(self) -> None:
        ct = self._cond_type_select.value
        has_selection = self._get_selected_cond_name() is not None
        detail = (
            [
                self._cond_name_display,
                self._cond_type_select,
                self._cond_fields_for_type(ct),
            ]
            if has_selection
            else []
        )
        if self._state.use_de_simulator:
            self._cond_detail_col.objects = [
                pn.pane.Markdown("**Environment Conditions**"),
                pn.Row(
                    pn.Spacer(),
                    self._remove_cond_btn,
                    sizing_mode="stretch_width",
                ),
                self._cond_table,
                *detail,
            ]
        else:
            self._cond_detail_col.objects = detail
