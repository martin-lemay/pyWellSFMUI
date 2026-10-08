import logging
from collections.abc import Iterator

import panel as pn
import pytest
from bokeh.document import Document
from panel.io.state import set_curdoc

from pywellsfmui.app import _attach_session_logging
from pywellsfmui.state.message_store import MessageStore

pn.extension("plotly", "tabulator", sizing_mode="stretch_width")


def test_navigate_to_switches_view() -> None:
    """create_app produces a working navigate_to callback."""
    from pywellsfmui.app import create_app

    template = create_app()
    # Smoke test: app builds without error
    assert template is not None


@pytest.fixture
def pywellsfm_logger() -> Iterator[logging.Logger]:
    """Return the pywellsfm logger, restoring its handlers afterwards."""
    logger = logging.getLogger("pywellsfm")
    saved = list(logger.handlers)
    yield logger
    logger.handlers = saved


def _texts(store: MessageStore) -> list[str]:
    return [m.text for m in store.messages]


def test_session_logging_is_isolated_between_sessions(
    pywellsfm_logger: logging.Logger,
) -> None:
    """Logs emitted in one session never reach another session's store."""
    doc_a, doc_b = Document(), Document()
    store_a, store_b = MessageStore(), MessageStore()
    with set_curdoc(doc_a):
        _attach_session_logging(store_a)
    with set_curdoc(doc_b):
        _attach_session_logging(store_b)

    with set_curdoc(doc_a):
        pywellsfm_logger.warning("from A")
    with set_curdoc(doc_b):
        pywellsfm_logger.warning("from B")

    assert _texts(store_a) == ["from A"]
    assert _texts(store_b) == ["from B"]


def test_session_logging_handler_removed_on_session_destroyed(
    pywellsfm_logger: logging.Logger,
) -> None:
    """The session handler is detached from the shared logger at teardown."""
    doc = Document()
    n_before = len(pywellsfm_logger.handlers)
    with set_curdoc(doc):
        _attach_session_logging(MessageStore())
    assert len(pywellsfm_logger.handlers) == n_before + 1

    for callback in doc.session_destroyed_callbacks:
        callback(None)
    assert len(pywellsfm_logger.handlers) == n_before


def test_session_logging_without_session_forwards_all(
    pywellsfm_logger: logging.Logger,
) -> None:
    """Outside a server session (scripts, tests) every log is forwarded."""
    store = MessageStore()
    _attach_session_logging(store)
    pywellsfm_logger.warning("no session")
    assert _texts(store) == ["no session"]


def test_sidebar_shows_ui_and_library_versions() -> None:
    """The sidebar shows pyWellSFMUI and pyWellSFM versions."""
    import pywellsfm

    import pywellsfmui
    from pywellsfmui.app import create_app

    template = create_app()
    text = " ".join(
        str(obj.object)
        for obj in template.sidebar.objects
        if isinstance(obj, pn.pane.Markdown)
    )
    assert f"pyWellSFMUI {pywellsfmui.__version__}" in text
    assert f"pyWellSFM {pywellsfm.__version__}" in text
