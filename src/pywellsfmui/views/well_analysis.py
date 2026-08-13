import io
import logging
from typing import Any

import panel as pn
import param
from pywellsfm.io.curve_io import uncertaintyCurveToBytes
from pywellsfm.utils.plot import (
    plot_well_analysis,
    plot_well_comparison,
)

from pywellsfmui.components.facies_editor import (
    FaciesEditor,
)
from pywellsfmui.components.well_importer import (
    WellImporter,
)
from pywellsfmui.state.actions import Actions
from pywellsfmui.state.app_state import AppState
from pywellsfmui.theme import Colors, status_html

logger = logging.getLogger(__name__)


class WellAnalysisView(param.Parameterized):
    """Tab 1: Well Data Analysis.

    Allows loading wells, setting facies model, and
    computing accommodation curves via
    AccommodationSpaceWellCalculator.
    """

    def __init__(
        self,
        state: AppState,
        actions: Actions,
        **params: Any,
    ) -> None:
        """Initialize the well analysis view."""
        super().__init__(**params)
        self._state = state
        self._actions = actions
        self._facies_editor = FaciesEditor(state=state, actions=actions)
        self._well_importer = WellImporter(state=state, actions=actions)
        self._compute_btn = pn.widgets.Button(
            label="Compute Accommodation",
            color="primary",
            disabled=True,
        )
        self._compute_btn.on_click(self._on_compute)
        self._step3_status = pn.pane.HTML(
            self._build_step3_status(),
            sizing_mode="fixed",
        )

        # --- Individual Well Analysis ---
        self._well_select = pn.widgets.Select(
            label="Well",
            options=[],
            width=200,
        )
        self._results_placeholder = pn.pane.Markdown(
            "*No accommodation results*"
        )
        self._plot_pane = pn.pane.Plotly(
            None,
            sizing_mode="stretch_width",
            visible=False,
        )

        # Export buttons
        self._export_fig_btn = pn.widgets.FileDownload(
            callback=self._export_figure_png,
            filename="well.png",
            label="Export Figure",
            color="success",
            width=120,
            visible=False,
        )
        self._export_wd_btn = pn.widgets.FileDownload(
            callback=self._export_water_depth_csv,
            filename="WaterDepth.csv",
            label="Export Water Depth",
            color="default",
            width=150,
            visible=False,
        )
        self._export_acco_btn = pn.widgets.FileDownload(
            callback=self._export_accommodation_csv,
            filename="Accommodation.csv",
            label="Export Accommodation",
            color="default",
            width=160,
            visible=False,
        )
        self._export_ratio_btn = pn.widgets.FileDownload(
            callback=self._export_ratio_csv,
            filename="WDThicknessRatio.csv",
            label="Export WD/Thickness",
            color="default",
            width=160,
            visible=False,
        )

        # --- Well Comparison ---
        _TRACK_OPTIONS = [
            "Water Depth",
            "Accommodation",
            "WD/Thickness Ratio",
        ]
        self._track_map = {
            "Water Depth": "water_depth",
            "Accommodation": "accommodation",
            "WD/Thickness Ratio": "wd_thickness_ratio",
        }
        self._comparison_track_select = pn.widgets.Select(
            label="Track",
            options=_TRACK_OPTIONS,
            value="Accommodation",
            width=200,
            visible=False,
        )
        self._comparison_plot_pane = pn.pane.Plotly(
            None,
            sizing_mode="stretch_width",
            visible=False,
        )
        self._comparison_export_btn = pn.widgets.FileDownload(
            callback=self._export_comparison_png,
            filename="WellComparison_Accommodation.png",
            label="Export Figure",
            color="success",
            width=120,
            visible=False,
        )

        self._comparison_track_select.param.watch(
            lambda event: self._update_comparison(),
            ["value"],
        )

        # Watchers
        self._state.param.watch(
            lambda event: self._update_step3(),
            ["wells", "facies_model"],
        )
        self._state.param.watch(
            lambda event: self._update_results(),
            ["accommodation_results"],
        )
        self._well_select.param.watch(
            lambda event: self._update_plot(),
            ["value"],
        )
        self._update_step3()

    def _is_step3_ready(self) -> bool:
        return bool(self._state.wells) and self._state.facies_model is not None

    def _build_step3_status(self) -> str:
        if self._is_step3_ready():
            return status_html("Ready", Colors.SUCCESS)
        return status_html("Invalid inputs", Colors.ERROR)

    def _update_step3(self) -> None:
        self._compute_btn.disabled = not self._is_step3_ready()
        self._step3_status.object = self._build_step3_status()

    async def _on_compute(self, event: Any) -> None:
        self._compute_btn.disabled = True
        self._compute_btn.label = "Computing..."
        try:
            await self._actions.compute_all_accommodation_async()
        except Exception:
            logger.debug("Accommodation compute failed", exc_info=True)
        finally:
            self._compute_btn.label = "Compute Accommodation"
            self._update_step3()

    def _get_selected_calculator(self) -> Any | None:
        """Get the calculator for the selected well."""
        name = self._well_select.value
        if not name:
            return None
        return self._state.accommodation_results.get(name)

    def _update_results(self) -> None:
        """Update the results section when results change."""
        results = self._state.accommodation_results
        has_results = bool(results)
        well_names = sorted(results.keys())

        self._well_select.options = well_names
        if well_names and not self._well_select.value:
            self._well_select.value = well_names[0]

        self._results_placeholder.visible = not has_results
        self._plot_pane.visible = has_results
        self._well_select.visible = has_results
        self._export_fig_btn.visible = has_results
        self._export_wd_btn.visible = has_results
        self._export_acco_btn.visible = has_results
        self._export_ratio_btn.visible = has_results

        self._comparison_track_select.visible = has_results
        self._comparison_plot_pane.visible = has_results
        self._comparison_export_btn.visible = has_results

        if has_results:
            self._results_placeholder.object = ""
            self._update_plot()
            self._update_comparison()
        else:
            self._results_placeholder.object = "*No accommodation results*"

    def _update_plot(self) -> None:
        """Rebuild the plot for the selected well."""
        calc = self._get_selected_calculator()
        if calc is None:
            self._plot_pane.object = None
            return
        name = self._well_select.value
        log_name = self._state.well_facies_log_names.get(name, "")
        try:
            fig = plot_well_analysis(calc, log_name)
            self._plot_pane.object = fig
        except Exception:
            logger.debug("Plot update failed", exc_info=True)
            self._plot_pane.object = None
        self._export_fig_btn.filename = f"{name}.png"
        self._export_wd_btn.filename = f"{name}_WaterDepth.csv"
        self._export_acco_btn.filename = f"{name}_Accommodation.csv"
        self._export_ratio_btn.filename = f"{name}_WDThicknessRatio.csv"

    def _export_figure_png(self) -> io.BytesIO:
        calc = self._get_selected_calculator()
        if calc is None:
            return io.BytesIO(b"")
        name = self._well_select.value
        log_name = self._state.well_facies_log_names.get(name, "")
        fig = plot_well_analysis(calc, log_name)
        try:
            png_bytes = fig.to_image(format="png", engine="kaleido")
        except Exception:
            logger.debug("Figure export failed", exc_info=True)
            return io.BytesIO(b"")
        return io.BytesIO(png_bytes)

    def _export_water_depth_csv(self) -> io.BytesIO:
        calc = self._get_selected_calculator()
        if calc is None:
            return io.BytesIO(b"")
        data = uncertaintyCurveToBytes(calc.waterDepthCurve)
        return io.BytesIO(data)

    def _export_accommodation_csv(self) -> io.BytesIO:
        calc = self._get_selected_calculator()
        if calc is None:
            return io.BytesIO(b"")
        data = uncertaintyCurveToBytes(calc.accommodationCurve)
        return io.BytesIO(data)

    def _export_ratio_csv(self) -> io.BytesIO:
        calc = self._get_selected_calculator()
        if calc is None:
            return io.BytesIO(b"")
        name = self._well_select.value
        log_name = self._state.well_facies_log_names.get(name, "")
        ratio = calc.computeWaterDepthThicknessRatioCurve(log_name)
        data = uncertaintyCurveToBytes(ratio)
        return io.BytesIO(data)

    def _update_comparison(self) -> None:
        """Rebuild the comparison plot."""
        results = self._state.accommodation_results
        if not results:
            self._comparison_plot_pane.object = None
            return
        track_label = self._comparison_track_select.value
        track = self._track_map.get(track_label, "accommodation")
        try:
            fig = plot_well_comparison(
                results,
                self._state.well_facies_log_names,
                track=track,
            )
            self._comparison_plot_pane.object = fig
        except Exception:
            logger.debug("Comparison plot failed", exc_info=True)
            self._comparison_plot_pane.object = None
        track_file = track_label.replace("/", "").replace(" ", "")
        self._comparison_export_btn.filename = (
            f"WellComparison_{track_file}.png"
        )

    def _export_comparison_png(self) -> io.BytesIO:
        results = self._state.accommodation_results
        if not results:
            return io.BytesIO(b"")
        track_label = self._comparison_track_select.value
        track = self._track_map.get(track_label, "accommodation")
        fig = plot_well_comparison(
            results,
            self._state.well_facies_log_names,
            track=track,
        )
        try:
            png_bytes = fig.to_image(format="png", engine="kaleido")
        except Exception:
            logger.debug("Comparison export failed", exc_info=True)
            return io.BytesIO(b"")
        return io.BytesIO(png_bytes)

    def panel(self) -> pn.Column:
        """Return the Panel layout for this view."""
        export_row = pn.Row(
            self._export_fig_btn,
            pn.Spacer(width=20),
            self._export_wd_btn,
            self._export_acco_btn,
            self._export_ratio_btn,
            sizing_mode="stretch_width",
            align="center",
        )

        individual_section = pn.Column(
            pn.pane.Markdown("### Individual Well Analysis"),
            self._well_select,
            export_row,
            self._plot_pane,
            self._results_placeholder,
            sizing_mode="stretch_width",
        )

        comparison_section = pn.Column(
            pn.pane.Markdown("### Well Comparison"),
            pn.Row(
                self._comparison_track_select,
                self._comparison_export_btn,
                sizing_mode="stretch_width",
                align="center",
            ),
            self._comparison_plot_pane,
            sizing_mode="stretch_width",
        )

        return pn.Column(
            pn.pane.Markdown("## Well Data Analysis"),
            self._facies_editor.panel(),
            self._well_importer.panel(),
            pn.Row(
                pn.pane.Markdown(
                    "### Step 3 - Accommodation Computation",
                    styles={"margin": "0"},
                ),
                pn.Spacer(),
                self._step3_status,
                sizing_mode="stretch_width",
                align="center",
            ),
            self._compute_btn,
            pn.pane.Markdown("## Results"),
            individual_section,
            comparison_section,
            sizing_mode="stretch_both",
        )
