import json

import numpy as np
import panel as pn
import pytest
from pywellsfm.model import Curve

from pywellsfmui.components.curve_editor import (
    _COL_X,
    _COL_Y,
    _NEW_POINT,
)
from pywellsfmui.components.eustatic_curve_editor import (
    EustaticCurveEditor,
)
from pywellsfmui.state.actions import Actions
from pywellsfmui.state.app_state import AppState
from pywellsfmui.state.io_manager import IOManager
from pywellsfmui.state.message_store import MessageStore


@pytest.fixture
def state() -> AppState:
    """Return a fresh AppState."""
    return AppState()


@pytest.fixture
def actions(state: AppState) -> Actions:
    """Return Actions wired to the given state."""
    return Actions(
        state=state,
        io_manager=IOManager(),
        message_store=MessageStore(),
    )


@pytest.fixture
def editor(
    state: AppState,
    actions: Actions,
) -> EustaticCurveEditor:
    """Return an EustaticCurveEditor instance."""
    return EustaticCurveEditor(state=state, actions=actions)


def test_editor_renders_empty_state(
    editor: EustaticCurveEditor,
) -> None:
    """Test editor renders with no curve."""
    panel = editor.panel()
    assert isinstance(panel, pn.Column)


def test_editor_table_has_placeholder_when_empty(
    editor: EustaticCurveEditor,
) -> None:
    """Test empty table has placeholder row."""
    df = editor._curve_editor._table.value
    assert len(df) == 1
    assert df.at[0, _COL_X] == _NEW_POINT


def test_editor_shows_curve_data(
    editor: EustaticCurveEditor,
    state: AppState,
) -> None:
    """Test curve data is displayed in table."""
    ages = np.array([0.0, 10.0, 20.0])
    values = np.array([5.0, -10.0, 15.0])
    curve = Curve("Age", "Eustatism", ages, values, "linear")
    state.eustatic_curve = curve
    df = editor._curve_editor._table.value
    assert len(df) == 4
    assert float(df.at[0, _COL_X]) == 0.0
    assert float(df.at[1, _COL_Y]) == -10.0
    assert df.at[3, _COL_X] == _NEW_POINT


def test_editor_status_no_curve(
    editor: EustaticCurveEditor,
) -> None:
    """Test status shows no curve message."""
    html = editor._build_status_html()
    assert "No eustatic curve" in html


def test_editor_status_with_valid_curve(
    editor: EustaticCurveEditor,
    state: AppState,
) -> None:
    """Test status shows point count."""
    ages = np.array([0.0, 10.0])
    values = np.array([5.0, -10.0])
    state.eustatic_curve = Curve("Age", "Eustatism", ages, values, "linear")
    html = editor._build_status_html()
    assert "2 points" in html


def test_editor_status_with_single_point(
    editor: EustaticCurveEditor,
    state: AppState,
    actions: Actions,
) -> None:
    """Test status warns about single point."""
    actions.add_eustatic_curve_point(0.0, 5.0)
    html = editor._build_status_html()
    assert "1 point" in html
    assert "need at least 2" in html


def test_add_point_action(
    state: AppState,
    actions: Actions,
) -> None:
    """Test adding points to eustatic curve."""
    actions.add_eustatic_curve_point(0.0, 5.0)
    assert state.eustatic_curve is not None
    assert len(state.eustatic_curve._abscissa) == 1
    actions.add_eustatic_curve_point(10.0, -3.0)
    assert len(state.eustatic_curve._abscissa) == 2


def test_update_point_action(
    state: AppState,
    actions: Actions,
) -> None:
    """Test updating an eustatic curve point."""
    actions.create_eustatic_curve(
        np.array([0.0, 10.0]),
        np.array([5.0, -3.0]),
    )
    actions.update_eustatic_curve_point(1, 15.0, -8.0)
    assert state.eustatic_curve._abscissa[1] == 15.0
    assert state.eustatic_curve._ordinate[1] == -8.0


def test_remove_point_action(
    state: AppState,
    actions: Actions,
) -> None:
    """Test removing a point from eustatic curve."""
    actions.create_eustatic_curve(
        np.array([0.0, 10.0, 20.0]),
        np.array([5.0, -3.0, 8.0]),
    )
    actions.remove_eustatic_curve_point(1)
    assert len(state.eustatic_curve._abscissa) == 2
    assert state.eustatic_curve._abscissa[1] == 20.0


def test_remove_last_point_clears_curve(
    state: AppState,
    actions: Actions,
) -> None:
    """Test removing last point clears the curve."""
    actions.create_eustatic_curve(np.array([0.0]), np.array([5.0]))
    actions.remove_eustatic_curve_point(0)
    assert state.eustatic_curve is None


def test_validate_age_increasing(
    editor: EustaticCurveEditor,
    state: AppState,
    actions: Actions,
) -> None:
    """Test age increasing validation."""
    actions.create_eustatic_curve(
        np.array([0.0, 10.0, 20.0]),
        np.array([1.0, 2.0, 3.0]),
    )
    ce = editor._curve_editor
    df = ce._table.value
    assert ce._validate_age_increasing(df, 1, 15.0, is_new=False)
    assert not ce._validate_age_increasing(df, 1, 25.0, is_new=False)


def test_parse_csv_bytes(
    editor: EustaticCurveEditor,
) -> None:
    """Test parsing CSV bytes."""
    csv_data = b"Age,Eustatism\n0,5\n10,-3\n20,8\n"
    ce = editor._curve_editor
    result = ce._parse_curve_bytes(csv_data, "test.csv")
    assert result is not None
    ages, values = result
    np.testing.assert_array_equal(ages, [0, 10, 20])
    np.testing.assert_array_equal(values, [5, -3, 8])


def test_parse_json_bytes(
    editor: EustaticCurveEditor,
) -> None:
    """Test parsing JSON bytes."""
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
    ce = editor._curve_editor
    result = ce._parse_curve_bytes(data, "test.json")
    assert result is not None
    ages, values = result
    np.testing.assert_array_equal(ages, [0, 10])
    np.testing.assert_array_equal(values, [5, -3])
