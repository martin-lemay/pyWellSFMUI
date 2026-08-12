import panel as pn
import param

from pywellsfmui.state.message_store import MessageLevel, MessageStore
from pywellsfmui.theme import Colors

_LEVEL_COLORS = {
    MessageLevel.DEBUG: Colors.MUTED,
    MessageLevel.INFO: Colors.INHERIT,
    MessageLevel.WARNING: Colors.WARNING,
    MessageLevel.ERROR: Colors.ERROR,
}

_LEVEL_ORDER = [
    MessageLevel.DEBUG,
    MessageLevel.INFO,
    MessageLevel.WARNING,
    MessageLevel.ERROR,
]


class LogPanel(param.Parameterized):
    """Collapsible log panel displayed at the bottom of the UI."""

    min_level = param.Selector(
        default=MessageLevel.INFO,
        objects=_LEVEL_ORDER,
        doc="Minimum message level to display",
    )

    def __init__(self, message_store: MessageStore, **params) -> None:
        super().__init__(**params)
        self._store = message_store
        self._card = None
        self._message_area = pn.Column(
            sizing_mode="stretch_width",
            scroll=True,
            height=200,
        )
        self._clear_button = pn.widgets.Button(label="Clear", color="light", width=80)
        self._clear_button.on_click(self._on_clear)
        self._level_widget = pn.widgets.Select.from_param(
            self.param.min_level, width=100, label="Min Level"
        )
        self._store.param.watch(self._on_messages_changed, "messages")
        self.param.watch(self._on_filter_changed, "min_level")

    def _format_message(self, msg) -> pn.pane.HTML:
        color = _LEVEL_COLORS.get(msg.level, "inherit")
        ts = msg.timestamp.strftime("%H:%M:%S")
        source_str = f" [{msg.source}]" if msg.source else ""
        text = (
            f'<span style="color:{color}; font-family:monospace; font-size:0.85em;">'
            f"[{ts}] [{msg.level.value}]{source_str} {msg.text}"
            f"</span>"
        )
        return pn.pane.HTML(text, sizing_mode="stretch_width")

    def _filtered_messages(self) -> list:
        min_idx = _LEVEL_ORDER.index(self.min_level)
        return [
            m for m in self._store.messages if _LEVEL_ORDER.index(m.level) >= min_idx
        ]

    def _refresh_message_area(self) -> None:
        filtered = self._filtered_messages()
        self._message_area.objects = [self._format_message(m) for m in filtered]

    def _update_title(self) -> None:
        count = len(self._store.messages)
        title = f"Log ({count})" if count else "Log"
        if self._card is not None:
            self._card.title = title

    def _on_messages_changed(self, event) -> None:
        self._refresh_message_area()
        self._update_title()
        # Auto-expand on WARNING or ERROR
        if self._card is not None and self._card.collapsed and event.new:
            last = event.new[-1]
            if last.level in (MessageLevel.WARNING, MessageLevel.ERROR):
                self._card.collapsed = False

    def _on_filter_changed(self, event) -> None:
        self._refresh_message_area()

    def _on_clear(self, event) -> None:
        self._store.clear()

    def expand(self) -> None:
        """Expand the log panel if it is collapsed."""
        if self._card is not None:
            self._card.collapsed = False

    def panel(self) -> pn.Card:
        header = pn.Row(self._level_widget, self._clear_button)
        self._card = pn.Card(
            header,
            self._message_area,
            title="Log",
            collapsed=True,
            collapsible=True,
            sizing_mode="stretch_width",
        )
        return self._card
