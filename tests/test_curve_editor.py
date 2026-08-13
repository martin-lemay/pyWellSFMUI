import json
from typing import Any

import numpy as np
import panel as pn
import pytest
from pywellsfm.model import Curve

from pywellsfmui.components.curve_editor import (
    CurveEditor,
)

_COL_X = "X"
_COL_Y = "Y"
_NEW_POINT = "New..."


@pytest.fixture
def changes() -> list[Any]:
    """Return a list to track curve changes."""
    return []


@pytest.fixture
def editor(changes: list[Any]) -> CurveEditor:
    """Return a CurveEditor instance."""
    return CurveEditor(
        age_title="Age (My)",
        value_title="Eustatism (m)",
        file_label="Load Curve",
        on_curve_changed=lambda c: changes.append(c),
    )


def test_renders_panel(
    editor: CurveEditor,
) -> None:
    """Test editor renders a panel."""
    panel = editor.panel()
    assert isinstance(panel, pn.Column)


def test_empty_table_has_placeholder(
    editor: CurveEditor,
) -> None:
    """Test empty table has a placeholder row."""
    df = editor._table.value
    assert len(df) == 1
    assert df.at[0, _COL_X] == _NEW_POINT


def test_set_curve_populates_table(
    editor: CurveEditor,
) -> None:
    """Test setting a curve populates the table."""
    curve = Curve(
        "Age",
        "Val",
        np.array([0.0, 10.0]),
        np.array([5.0, -3.0]),
        "linear",
    )
    editor.set_curve(curve)
    df = editor._table.value
    assert len(df) == 3  # 2 data + 1 placeholder
    assert float(df.at[0, _COL_X]) == 0.0
    assert float(df.at[1, _COL_Y]) == -3.0


def test_set_curve_none_clears_table(
    editor: CurveEditor,
) -> None:
    """Test setting None clears the table."""
    curve = Curve(
        "Age",
        "Val",
        np.array([0.0, 10.0]),
        np.array([5.0, -3.0]),
        "linear",
    )
    editor.set_curve(curve)
    editor.set_curve(None)
    df = editor._table.value
    assert len(df) == 1


def test_get_curve_returns_current(
    editor: CurveEditor,
) -> None:
    """Test get_curve returns the current curve."""
    assert editor.get_curve() is None
    curve = Curve(
        "Age",
        "Val",
        np.array([0.0]),
        np.array([5.0]),
        "linear",
    )
    editor.set_curve(curve)
    assert editor.get_curve() is curve


def test_set_value_title_updates_table(
    editor: CurveEditor,
) -> None:
    """Test set_value_title updates column title."""
    editor.set_value_title("Subsidence (m)")
    assert editor._table.titles[_COL_Y] == "Subsidence (m)"


def test_validate_age_increasing(
    editor: CurveEditor,
) -> None:
    """Test age validation for increasing order."""
    curve = Curve(
        "Age",
        "Val",
        np.array([0.0, 10.0, 20.0]),
        np.array([1.0, 2.0, 3.0]),
        "linear",
    )
    editor.set_curve(curve)
    df = editor._table.value
    assert editor._validate_age_increasing(df, 1, 15.0, is_new=False)
    assert not editor._validate_age_increasing(df, 1, 25.0, is_new=False)


def test_parse_csv_bytes(
    editor: CurveEditor,
) -> None:
    """Test parsing CSV bytes into curve data."""
    csv_data = b"Age,Value\n0,5\n10,-3\n20,8\n"
    result = editor._parse_curve_bytes(csv_data, "test.csv")
    assert result is not None
    ages, values = result
    np.testing.assert_array_equal(ages, [0, 10, 20])
    np.testing.assert_array_equal(values, [5, -3, 8])


def test_parse_json_bytes(
    editor: CurveEditor,
) -> None:
    """Test parsing JSON bytes into curve data."""
    obj = {
        "curve": {
            "xAxisName": "Age",
            "data": [
                {"x": 0, "y": 5},
                {"x": 10, "y": -3},
            ],
        }
    }
    data = json.dumps(obj).encode("utf-8")
    result = editor._parse_curve_bytes(data, "test.json")
    assert result is not None
    ages, values = result
    np.testing.assert_array_equal(ages, [0, 10])
    np.testing.assert_array_equal(values, [5, -3])
