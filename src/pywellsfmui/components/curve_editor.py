import io
import json
from collections.abc import Callable

import numpy as np
import pandas as pd
import panel as pn
import param

from pywellsfm.model import Curve

_COL_X = "X"
_COL_Y = "Y"
_NEW_POINT = "New..."


class CurveEditor(param.Parameterized):
    """Generic age-vs-value curve table editor."""

    def __init__(
        self,
        age_title: str,
        value_title: str,
        file_label: str,
        on_curve_changed: Callable[[Curve | None], None],
        **params,
    ) -> None:
        super().__init__(**params)
        self._age_title = age_title
        self._value_title = value_title
        self._file_label = file_label
        self._on_curve_changed = on_curve_changed
        self._curve: Curve | None = None
        self._updating = False
        self._button_row: pn.Row | None = None

        self._file_input = self._make_file_input()
        self._download = pn.widgets.FileDownload(
            callback=self._make_download,
            filename="curve.csv",
            label="Save Curve",
            color="success",
            width=120,
            align="center",
        )
        self._remove_btn = pn.widgets.Button(
            label="Remove",
            color="danger",
            width=80,
            height=28,
        )

        self._df = pd.DataFrame(columns=[_COL_X, _COL_Y])
        self._table = pn.widgets.Tabulator(
            self._df,
            sizing_mode="stretch_width",
            height=250,
            show_index=False,
            selectable=1,
            widths={_COL_X: "50%", _COL_Y: "50%"},
            titles={
                _COL_X: age_title,
                _COL_Y: value_title,
            },
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
        )

        self._file_input.param.watch(self._on_file_loaded, "value")
        self._remove_btn.on_click(self._on_remove_point)
        self._table.on_edit(self._on_table_edit)
        self._refresh()

    # --- Public API ---

    def _make_file_input(self) -> pn.widgets.FileInput:
        return pn.widgets.FileInput(
            accept=".json,.csv",
            width=250,
            align="center",
            label=self._file_label,
        )

    def reset_file_input(self) -> None:
        """Replace the FileInput with a fresh widget.

        Browser file inputs cannot be cleared
        programmatically, so we swap the widget.
        """
        self._file_input = self._make_file_input()
        self._file_input.param.watch(self._on_file_loaded, "value")
        if self._button_row is not None:
            self._button_row[0] = self._file_input

    def set_curve(self, curve: Curve | None) -> None:
        """Set the curve displayed and edited by this widget.

        Args:
            curve: The curve to display, or None to clear.
        """
        self._curve = curve
        self.reset_file_input()
        self._refresh()

    def get_curve(self) -> Curve | None:
        """Return the currently held curve, or None.

        Returns:
            The current Curve instance, or None if no curve is set.
        """
        return self._curve

    def set_value_title(self, title: str) -> None:
        """Update the display title of the value (Y) column.

        Args:
            title: New column header string.
        """
        self._value_title = title
        titles = dict(self._table.titles)
        titles[_COL_Y] = title
        self._table.titles = titles

    # --- DataFrame builder ---

    def _build_df(self) -> pd.DataFrame:
        rows: list[dict] = []
        if self._curve is not None:
            for age, val in zip(
                self._curve._abscissa,
                self._curve._ordinate,
            ):
                rows.append({_COL_X: float(age), _COL_Y: float(val)})
        rows.append({_COL_X: _NEW_POINT, _COL_Y: None})
        df = pd.DataFrame(rows)
        if not df.empty:
            df[_COL_X] = df[_COL_X].astype(object)
            df[_COL_Y] = df[_COL_Y].astype(object)
        return df

    # --- Styling ---

    def _style_placeholder(self, row: pd.Series) -> list[str]:
        for val in row.values:
            if val == _NEW_POINT:
                return ["font-style: italic; color: #999"] * len(row)
        return [""] * len(row)

    # --- Refresh ---

    def _refresh(self) -> None:
        self._updating = True
        df = self._build_df()
        self._table.value = df
        self._table.style.apply(self._style_placeholder, axis=1)
        self._table.param.trigger("value")
        self._updating = False

    # --- Validation ---

    def _validate_age_increasing(
        self,
        df: pd.DataFrame,
        row: int,
        age: float,
        *,
        is_new: bool,
    ) -> bool:
        """Check that ages are strictly increasing.

        Args:
            df: Current table DataFrame (includes placeholder row).
            row: Index of the row being edited or inserted.
            age: The candidate age value.
            is_new: True when adding a new point at the placeholder row.

        Returns:
            True if the resulting age sequence is strictly increasing.
        """
        n_data = len(df) - 1
        ages: list[float] = []
        for i in range(n_data):
            val = df.at[i, _COL_X]
            if val is None or str(val) == _NEW_POINT:
                continue
            if i == row and not is_new:
                ages.append(age)
            else:
                ages.append(float(val))
        if is_new:
            ages.append(age)
        for i in range(1, len(ages)):
            if ages[i] <= ages[i - 1]:
                return False
        return True

    def _revert_edit(self, event) -> None:
        col = _COL_X if event.column == _COL_X else _COL_Y
        self._table.patch({col: [(event.row, event.old)]})

    # --- Curve mutation helpers ---

    def _create_curve(
        self,
        ages: np.ndarray,
        values: np.ndarray,
    ) -> None:
        self._curve = Curve("Age", "Value", ages, values, "linear")
        self._refresh()
        self._on_curve_changed(self._curve)

    def _notify_changed(self) -> None:
        self._refresh()
        self._on_curve_changed(self._curve)

    # --- Callbacks ---

    def _on_table_edit(self, event) -> None:
        if self._updating:
            return
        row = event.row
        column = event.column
        value = event.value
        df = self._table.value
        is_last = row == len(df) - 1

        if is_last:
            x_val = df.at[row, _COL_X]
            y_val = df.at[row, _COL_Y]
            if column == _COL_X:
                x_val = value
            elif column == _COL_Y:
                y_val = value
            x_str = str(x_val).strip() if x_val is not None else ""
            if x_str == _NEW_POINT:
                x_str = ""
            if x_str and y_val is not None:
                x_f = float(x_str)
                y_f = float(y_val)
                if not self._validate_age_increasing(df, row, x_f, is_new=True):
                    self._revert_edit(event)
                    return
                if self._curve is None:
                    self._create_curve(
                        np.array([x_f]),
                        np.array([y_f]),
                    )
                else:
                    self._curve.addSampledPoint(x_f, y_f)
                    self._notify_changed()
        else:
            x_val = df.at[row, _COL_X]
            y_val = df.at[row, _COL_Y]
            if column == _COL_X:
                x_val = value
            elif column == _COL_Y:
                y_val = value
            if x_val is None or y_val is None:
                return
            x_f = float(x_val)
            y_f = float(y_val)
            if not self._validate_age_increasing(df, row, x_f, is_new=False):
                self._revert_edit(event)
                return
            self._curve._abscissa[row] = x_f
            self._curve._ordinate[row] = y_f
            self._notify_changed()

    def _on_remove_point(self, event) -> None:
        sel = self._table.selection
        if not sel:
            return
        row = sel[0]
        df = self._table.value
        if row >= len(df) - 1:
            return
        if self._curve is None:
            return
        self._curve._abscissa = np.delete(self._curve._abscissa, row)
        self._curve._ordinate = np.delete(self._curve._ordinate, row)
        if len(self._curve._abscissa) == 0:
            self._curve = None
        self._notify_changed()

    def _parse_curve_bytes(
        self, data: bytes, filename: str
    ) -> tuple[np.ndarray, np.ndarray] | None:
        """Parse file bytes into (ages, values) arrays.

        Args:
            data: Raw file bytes (.csv or .json).
            filename: Original filename used to detect format.

        Returns:
            A tuple (ages, values) as numpy arrays, or None on failure.
        """
        if filename.lower().endswith(".csv"):
            df = pd.read_csv(io.BytesIO(data))
            if df.shape[1] < 2:
                return None
            ages = pd.to_numeric(df.iloc[:, 0], errors="coerce").dropna().values
            values = pd.to_numeric(df.iloc[:, 1], errors="coerce").dropna().values
            n = min(len(ages), len(values))
            if n < 1:
                return None
            return ages[:n].copy(), values[:n].copy()
        obj = json.loads(data.decode("utf-8"))
        curve_obj = obj.get("curve", {})
        pts = curve_obj.get("data", [])
        if len(pts) < 1:
            return None
        ages = np.array([float(p["x"]) for p in pts])
        values = np.array([float(p["y"]) for p in pts])
        return ages, values

    def _on_file_loaded(self, event) -> None:
        if self._file_input.value is None:
            return
        filename = self._file_input.filename or "curve.json"
        data = self._file_input.value
        result = self._parse_curve_bytes(data, filename)
        if result is None:
            return
        ages, values = result
        self._create_curve(ages, values)

    def _make_download(self) -> io.BytesIO:
        if self._curve is None:
            return io.BytesIO(b"Age,Value\n")
        df = pd.DataFrame(
            {
                "Age": self._curve._abscissa,
                "Value": self._curve._ordinate,
            }
        )
        buf = io.BytesIO()
        df.to_csv(buf, index=False)
        buf.seek(0)
        return buf

    # --- Layout ---

    def panel(self) -> pn.Column:
        """Return the Panel layout for this editor.

        Returns:
            A pn.Column containing the file controls and table.
        """
        self._button_row = pn.Row(
            self._file_input,
            pn.Spacer(),
            self._download,
            sizing_mode="stretch_width",
            align="center",
        )
        remove_row = pn.Row(
            pn.Spacer(),
            self._remove_btn,
            sizing_mode="stretch_width",
        )
        return pn.Column(
            self._button_row,
            remove_row,
            self._table,
            sizing_mode="stretch_width",
        )
