from __future__ import annotations

from typing import Any

import panel as pn
import param
from pywellsfm.model import Curve

from pywellsfmui.components.curve_editor import CurveEditor
from pywellsfmui.plots import build_curve_plot
from pywellsfmui.state.actions import Actions
from pywellsfmui.state.app_state import AppState
from pywellsfmui.theme import Colors, status_html


class EustaticCurveEditor(param.Parameterized):
    """Editor for the eustatic curve, wrapping CurveEditor."""

    def __init__(
        self,
        state: AppState,
        actions: Actions,
        **params: Any,
    ) -> None:
        """Initialize the eustatic curve editor."""
        super().__init__(**params)
        self._state = state
        self._actions = actions
        self._syncing = False

        self._curve_editor = CurveEditor(
            age_title="Age (My)",
            value_title="Eustatism (m)",
            file_label="Load Eustatic Curve",
            on_curve_changed=self._on_curve_changed,
        )

        self._status = pn.pane.HTML(
            self._build_status_html(),
            sizing_mode="fixed",
        )
        self._plot_pane = pn.pane.Plotly(
            build_curve_plot(
                "Eustatism (m)",
                self._state.eustatic_curve,
                "Eustatism",
            ),
            sizing_mode="stretch_width",
            height=350,
        )

        self._state.param.watch(
            lambda event: self._sync_from_state(),
            ["eustatic_curve"],
        )
        self._sync_from_state()

    def _sync_from_state(self) -> None:
        self._syncing = True
        self._curve_editor.set_curve(self._state.eustatic_curve)
        self._status.object = self._build_status_html()
        self._plot_pane.object = build_curve_plot(
            "Eustatism (m)",
            self._state.eustatic_curve,
            "Eustatism",
        )
        self._syncing = False

    def _on_curve_changed(self, curve: Curve | None) -> None:
        if self._syncing:
            return
        if curve is None:
            self._actions.clear_eustatic_curve()
        else:
            ages = curve._abscissa.copy()
            values = curve._ordinate.copy()
            self._actions.create_eustatic_curve(ages, values)
        self._plot_pane.object = build_curve_plot(
            "Eustatism (m)",
            self._state.eustatic_curve,
            "Eustatism",
        )

    def _build_status_html(self) -> str:
        """Build status indicator HTML for the current eustatic curve.

        Returns:
            HTML string describing the current curve state.
        """
        curve = self._state.eustatic_curve
        if curve is None:
            return status_html("No eustatic curve", Colors.ERROR)
        n = len(curve._abscissa)
        if n < 2:
            return status_html(
                f"{n} point — need at least 2",
                Colors.WARNING,
            )
        return status_html(f"{n} points", Colors.SUCCESS)

    def panel(self) -> pn.Column:
        """Return the Panel layout for this editor.

        Returns:
            A pn.Column containing the title row, and a side-by-side
            layout with the curve table (left) and plot (right).
        """
        content_row = pn.Row(
            self._curve_editor.panel(),
            self._plot_pane,
            sizing_mode="stretch_width",
        )

        return pn.Column(
            pn.Row(
                pn.Spacer(),
                self._status,
                sizing_mode="stretch_width",
                align="center",
            ),
            content_row,
            sizing_mode="stretch_width",
        )
