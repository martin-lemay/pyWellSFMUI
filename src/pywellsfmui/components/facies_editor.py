from __future__ import annotations

import contextlib
import io
import json
import logging
import math
from typing import Any

import pandas as pd
import panel as pn
import param
from pywellsfm.model import (
    EnvironmentalFacies,
    FaciesCriteriaType,
    PetrophysicalFacies,
    SedimentaryFacies,
)

from pywellsfmui.state.actions import Actions
from pywellsfmui.state.app_state import AppState
from pywellsfmui.theme import Colors, status_html

_CRITERIA_TYPE_OPTIONS: list[str] = [t.value for t in FaciesCriteriaType]

_TYPE_LABELS: dict[type, str] = {
    SedimentaryFacies: "sedimentological",
    PetrophysicalFacies: "petrophysical",
    EnvironmentalFacies: "environmental",
}

_NEW_FACIES = "New Facies..."
_NEW_CRITERION = "New Criterion..."

logger = logging.getLogger(__name__)


class FaciesEditor(param.Parameterized):
    """Reusable facies model editor.

    Master-detail layout: facies table on the left,
    criteria table on the right. Reads from
    AppState.facies_model, writes through Actions.
    """

    def __init__(
        self,
        state: AppState,
        actions: Actions,
        **params: Any,
    ) -> None:
        """Initialize the facies editor."""
        super().__init__(**params)
        self._state = state
        self._actions = actions
        self._updating_facies = False
        self._updating_crit = False

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
            label="Load Facies Model",
        )
        self._download = pn.widgets.FileDownload(
            callback=self._make_download,
            filename="facies_model.json",
            label="Save Facies Model",
            color="success",
            width=120,
            align="center",
        )

        # Left panel — facies table
        self._facies_df = pd.DataFrame(columns=["Name", "Type"])
        self._facies_table = pn.widgets.Tabulator(
            self._facies_df,
            sizing_mode="stretch_width",
            height=200,
            show_index=False,
            selectable=1,
            widths={"Name": "60%", "Type": "40%"},
            editors={
                "Name": {
                    "type": "input",
                    "selectContents": True,
                },
                "Type": {
                    "type": "list",
                    "values": _CRITERIA_TYPE_OPTIONS,
                },
            },
            configuration={
                "editTriggerEvent": "dblclick",
            },
        )
        self._remove_facies_btn = pn.widgets.Button(
            label="Remove",
            color="danger",
            width=80,
            height=28,
        )

        # Right panel — criteria table
        self._crit_df = pd.DataFrame(columns=["Name", "Min", "Max"])
        self._crit_table = pn.widgets.Tabulator(
            self._crit_df,
            sizing_mode="stretch_width",
            height=200,
            show_index=False,
            selectable=1,
            widths={
                "Name": "50%",
                "Min": "25%",
                "Max": "25%",
            },
            editors={
                "Name": {
                    "type": "input",
                    "selectContents": True,
                },
                "Min": {
                    "type": "number",
                    "selectContents": True,
                },
                "Max": {
                    "type": "number",
                    "selectContents": True,
                },
            },
            configuration={
                "editTriggerEvent": "dblclick",
            },
            disabled=True,
        )
        self._remove_crit_btn = pn.widgets.Button(
            label="Remove",
            color="danger",
            width=80,
            height=28,
        )

        # Status
        self._status = pn.pane.HTML(
            self._build_status_html(),
            sizing_mode="fixed",
        )

        # Wire callbacks
        self._new_btn.on_click(self._on_new_model)
        self._file_input.param.watch(self._on_file_loaded, "value")
        self._remove_facies_btn.on_click(self._on_remove_facies)
        self._facies_table.param.watch(self._on_facies_selected, "selection")
        self._facies_table.on_edit(self._on_facies_table_edit)
        self._remove_crit_btn.on_click(self._on_remove_criterion)
        self._crit_table.on_edit(self._on_crit_table_edit)

        # Watch state changes
        self._state.param.watch(
            lambda event: self._refresh(),
            ["facies_model"],
        )

        # Initialize tables
        self._refresh()

    # --- DataFrame builders ---

    def _build_facies_df(self) -> pd.DataFrame:
        """Build DataFrame from facies model.

        Includes a placeholder row for adding new facies.
        """
        rows: list[dict] = []
        model = self._state.facies_model
        if model is not None:
            facies_list = sorted(model.faciesSet, key=lambda f: f.name)
            for f in facies_list:
                type_label = _TYPE_LABELS.get(type(f), "uncategorized")
                rows.append({"Name": f.name, "Type": type_label})
        rows.append({"Name": _NEW_FACIES, "Type": ""})
        return pd.DataFrame(rows)

    def _build_criteria_df(self) -> pd.DataFrame:
        """Build DataFrame from selected facies criteria.

        Includes a placeholder row for adding new ones.
        """
        facies_name = self._get_selected_facies_name()
        rows: list[dict] = []
        if facies_name is not None and self._state.facies_model is not None:
            facies = self._state.facies_model.getFaciesByName(facies_name)
            if facies is not None:
                crits = sorted(
                    facies.criteriaCollection.getAllCriteria(),
                    key=lambda c: c.name,
                )
                for c in crits:
                    min_val = None if math.isinf(c.minRange) else c.minRange
                    max_val = None if math.isinf(c.maxRange) else c.maxRange
                    rows.append(
                        {
                            "Name": c.name,
                            "Min": min_val,
                            "Max": max_val,
                        }
                    )
        if facies_name is not None:
            rows.append(
                {
                    "Name": _NEW_CRITERION,
                    "Min": None,
                    "Max": None,
                }
            )
        df = pd.DataFrame(rows)
        if not df.empty:
            df["Min"] = df["Min"].astype(object)
            df["Max"] = df["Max"].astype(object)
        return df

    # --- Styling ---

    def _style_facies_placeholder(self, row: pd.Series) -> list[str]:
        if row["Name"] == _NEW_FACIES:
            return ["font-style: italic; color: #999"] * len(row)
        return [""] * len(row)

    def _style_crit_placeholder(self, row: pd.Series) -> list[str]:
        if row["Name"] == _NEW_CRITERION:
            return ["font-style: italic; color: #999"] * len(row)
        return [""] * len(row)

    # --- Refresh ---

    def _build_status_html(self) -> str:
        """Build colored status HTML based on facies model state."""
        model = self._state.facies_model
        if model is None:
            return status_html("No facies model", Colors.ERROR)
        count = len(model.faciesSet)
        if count == 0:
            return status_html("Facies model: 0 facies", Colors.ERROR)
        all_have_criteria = all(
            len(f.criteriaCollection.getAllCriteria()) > 0
            for f in model.faciesSet
        )
        if all_have_criteria:
            return status_html(
                f"Facies model: {count} valid facies",
                Colors.SUCCESS,
            )
        return status_html(
            f"Facies model: {count} facies, missing criteria",
            Colors.WARNING,
        )

    def _refresh(self) -> None:
        """Rebuild both tables from current state."""
        self._update_facies_table()
        self._status.object = self._build_status_html()
        self._update_criteria_table()

    def _get_selected_facies_name(self) -> str | None:
        selection = self._facies_table.selection
        if not selection:
            return None
        row = selection[0]
        df = self._facies_table.value
        if row >= len(df) - 1:
            return None  # placeholder row
        return str(df.at[row, "Name"])

    def _update_facies_table(self) -> None:
        self._updating_facies = True
        prev_sel = self._facies_table.selection
        df = self._build_facies_df()
        self._facies_table.value = df
        self._facies_table.style.apply(self._style_facies_placeholder, axis=1)
        # Restore selection if valid
        if prev_sel and prev_sel[0] < len(df) - 1:
            self._facies_table.selection = prev_sel
        self._updating_facies = False

    def _update_criteria_table(self) -> None:
        self._updating_crit = True
        df = self._build_criteria_df()
        self._crit_table.value = df
        self._crit_table.style.apply(self._style_crit_placeholder, axis=1)
        has_facies = self._get_selected_facies_name() is not None
        self._crit_table.disabled = not has_facies
        self._updating_crit = False

    # --- Callbacks ---

    def _on_new_model(self, event: Any) -> None:
        self._actions.create_empty_facies_model()

    def _on_file_loaded(self, event: Any) -> None:
        if self._file_input.value is None:
            return
        try:
            self._actions.load_facies_model_from_bytes(
                self._file_input.value,
                filename=self._file_input.filename or "",
            )
        except Exception:
            logger.debug("Load facies model failed", exc_info=True)

    def _make_download(self) -> io.BytesIO:
        data = self._actions.export_facies_model_as_json()
        json_bytes = json.dumps(data, indent=2).encode("utf-8")
        return io.BytesIO(json_bytes)

    def _on_facies_table_edit(self, event: Any) -> None:
        """Handle edits in the facies table."""
        if self._updating_facies:
            return
        row = event.row
        column = event.column
        value = event.value
        df = self._facies_table.value
        is_last_row = row == len(df) - 1

        if is_last_row:
            # Editing the placeholder "add" row
            name = df.at[row, "Name"]
            type_val = df.at[row, "Type"]
            if column == "Name":
                name = value
            elif column == "Type":
                type_val = value

            name_str = str(name).strip() if name else ""
            if name_str == _NEW_FACIES:
                name_str = ""
            type_str = str(type_val).strip() if type_val else ""
            if name_str and type_str:
                try:
                    crit_type = FaciesCriteriaType(type_str)
                    self._actions.add_facies(name_str, crit_type)
                except ValueError:
                    pass  # error logged by Actions
        else:
            # Existing rows: Name and Type are read-only
            self._facies_table.patch({column: [(row, event.old)]})

    def _on_remove_facies(self, event: Any) -> None:
        name = self._get_selected_facies_name()
        if name is None:
            return
        with contextlib.suppress(ValueError):
            self._actions.remove_facies(name)

    def _on_facies_selected(self, event: Any) -> None:
        if self._updating_facies:
            return
        self._update_criteria_table()

    def _on_crit_table_edit(self, event: Any) -> None:
        """Handle edits in the criteria table."""
        if self._updating_crit:
            return
        facies_name = self._get_selected_facies_name()
        if not facies_name:
            return

        row = event.row
        column = event.column
        value = event.value
        df = self._crit_table.value
        is_last_row = row == len(df) - 1

        if is_last_row:
            # Editing the placeholder "add" row
            name = df.at[row, "Name"]
            min_val = df.at[row, "Min"]
            max_val = df.at[row, "Max"]
            if column == "Name":
                name = value
            elif column == "Min":
                min_val = value
            elif column == "Max":
                max_val = value

            name_str = str(name).strip() if name else ""
            if name_str == _NEW_CRITERION:
                name_str = ""
            if name_str and min_val is not None and max_val is not None:
                with contextlib.suppress(ValueError):
                    self._actions.add_criteria(
                        facies_name,
                        name_str,
                        float(min_val),
                        float(max_val),
                    )
        else:
            # Editing an existing criterion
            crit_name = df.at[row, "Name"]
            if column == "Name":
                # Name is read-only; revert
                self._crit_table.patch({"Name": [(row, event.old)]})
                return
            if column in ("Min", "Max"):
                min_val = df.at[row, "Min"]
                max_val = df.at[row, "Max"]
                if column == "Min":
                    min_val = value
                else:
                    max_val = value
                if min_val is None or max_val is None:
                    return
                with contextlib.suppress(ValueError):
                    self._actions.update_criteria(
                        facies_name,
                        str(crit_name),
                        float(min_val),
                        float(max_val),
                    )

    def _on_remove_criterion(self, event: Any) -> None:
        facies_name = self._get_selected_facies_name()
        if not facies_name:
            return
        selection = self._crit_table.selection
        if not selection:
            return
        row = selection[0]
        df = self._crit_table.value
        # Can't remove the placeholder row
        if row >= len(df) - 1:
            return
        crit_name = df.at[row, "Name"]
        with contextlib.suppress(ValueError):
            self._actions.remove_criteria(facies_name, str(crit_name))

    def panel(self) -> pn.Column:
        """Assemble and return the full editor layout."""
        left_panel = pn.Column(
            pn.pane.Markdown("**Facies List**"),
            pn.Row(
                pn.Spacer(),
                self._remove_facies_btn,
                sizing_mode="stretch_width",
            ),
            self._facies_table,
            min_width=300,
            sizing_mode="stretch_width",
        )

        right_panel = pn.Column(
            pn.pane.Markdown("**Criteria For Selected Facies**"),
            pn.Row(
                pn.Spacer(),
                self._remove_crit_btn,
                sizing_mode="stretch_width",
            ),
            self._crit_table,
            sizing_mode="stretch_width",
        )

        master_detail = pn.Row(
            left_panel,
            pn.Spacer(width=10),
            right_panel,
            sizing_mode="stretch_width",
        )

        status_row = pn.Row(
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
            status_row,
            button_row,
            master_detail,
            sizing_mode="stretch_width",
        )
