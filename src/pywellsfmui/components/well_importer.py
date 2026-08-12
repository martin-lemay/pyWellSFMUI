import logging

import panel as pn
import param

from pywellsfmui.state.actions import Actions
from pywellsfmui.state.app_state import AppState
from pywellsfmui.theme import Colors, status_html

logger = logging.getLogger(__name__)


class WellImporter(param.Parameterized):
    """Well import widget.

    Allows loading wells from JSON/LAS files, selecting
    the litho log per well, and removing wells.
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

        # File input
        self._file_input = pn.widgets.FileInput(
            accept=".json,.las",
            width=250,
            align="start",
            label="Load Well",
        )

        # Well list container (rebuilt on refresh)
        self._well_list = pn.Column(sizing_mode="stretch_width")

        # Status
        self._status = pn.pane.HTML(
            self._build_status_html(),
            sizing_mode="fixed",
        )

        # Wire callbacks
        self._file_input.param.watch(self._on_file_loaded, "value")

        # Watch state changes
        self._state.param.watch(
            lambda event: self._refresh(),
            [
                "wells",
                "well_facies_log_names",
                "well_accommodation_computed",
            ],
        )

        self._refresh()

    def _make_well_row(self, well) -> pn.Row:
        """Build a row with well name, log selector, and
        remove button for a single well."""
        discrete = sorted(well.getDiscreteLogNames())
        current = self._state.well_facies_log_names.get(well.name, "")

        name_label = pn.pane.Markdown(
            f"**{well.name}**",
            align="center",
            min_width=150,
        )

        if discrete:
            log_select = pn.widgets.Select(
                options=discrete,
                value=current
                if current in discrete
                else (discrete[0] if discrete else ""),
                width=200,
                align="center",
            )

            def _on_log_change(event, wn=well.name) -> None:
                if self._updating:
                    return
                try:
                    self._actions.set_well_facies_log(wn, event.new)
                except ValueError:
                    pass

            log_select.param.watch(_on_log_change, "value")
        else:
            log_select = pn.pane.Markdown(
                "*No litho log*",
                align="center",
                width=200,
            )

        computed = self._state.well_accommodation_computed.get(well.name, False)
        computed_cb = pn.Column(
            pn.widgets.Checkbox(
                label="",
                value=computed,
                disabled=True,
            ),
            width=100,
            align="center",
            styles={
                "display": "flex",
                "align-items": "center",
                "justify-content": "center",
            },
        )

        remove_btn = pn.widgets.Button(
            label="Remove",
            color="danger",
            width=80,
            height=28,
            align="center",
        )

        def _on_remove(event, wn=well.name) -> None:
            try:
                self._actions.remove_well(wn)
            except ValueError:
                pass

        remove_btn.on_click(_on_remove)

        return pn.Row(
            name_label,
            log_select,
            computed_cb,
            remove_btn,
            sizing_mode="fixed",
            align="start",
        )

    def _make_header_row(self) -> pn.Row:
        """Column headers for the well table."""
        return pn.Row(
            pn.pane.Markdown("**Well**", min_width=150),
            pn.pane.Markdown("**Facies log**", width=200),
            pn.pane.Markdown("**Computed**", width=100),
            pn.pane.Markdown("", width=80),
            sizing_mode="fixed",
        )

    def _build_status_html(self) -> str:
        """Build colored status HTML based on wells state."""
        count = len(self._state.wells)
        if count == 0:
            return status_html("No wells loaded", Colors.ERROR)
        label = f"{count} well{'s' if count != 1 else ''} loaded"
        return status_html(label, Colors.SUCCESS)

    def _refresh(self) -> None:
        self._updating = True
        self._well_list.clear()

        if self._state.wells:
            self._well_list.append(self._make_header_row())

        for well in self._state.wells:
            self._well_list.append(self._make_well_row(well))

        self._status.object = self._build_status_html()
        self._updating = False

    def _on_file_loaded(self, event) -> None:
        if self._file_input.value is None:
            return
        try:
            self._actions.load_well_from_bytes(
                self._file_input.value,
                filename=self._file_input.filename or "",
            )
        except Exception:
            logger.debug("Load well file failed", exc_info=True)

    def panel(self) -> pn.Column:
        title_row = pn.Row(
            pn.pane.Markdown(
                "### Step 2 - Well Import",
                styles={"margin": "0"},
            ),
            pn.Spacer(),
            self._status,
            sizing_mode="stretch_width",
            align="center",
        )

        return pn.Column(
            title_row,
            pn.pane.Markdown(
                "*Upload a .json or .las file to add a well to the list*",
            ),
            self._file_input,
            self._well_list,
            sizing_mode="stretch_width",
        )
