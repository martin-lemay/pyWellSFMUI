import io
from unittest.mock import MagicMock

import panel as pn
import pytest

from pywellsfmui.notifications import guarded_download, notify_error


@pytest.fixture
def toasts(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Replace the Panel notification area with a mock."""
    area = MagicMock()
    monkeypatch.setattr(
        type(pn.state), "notifications", property(lambda _self: area)
    )
    return area


def test_notify_error_shows_toast(toasts: MagicMock) -> None:
    """notify_error forwards the message to the notification area."""
    notify_error("boom")
    toasts.error.assert_called_once()
    assert toasts.error.call_args.args[0] == "boom"


def test_notify_error_without_notification_area() -> None:
    """notify_error is a no-op outside a server session."""
    notify_error("ignored")


def test_guarded_download_returns_callback_result(toasts: MagicMock) -> None:
    """A successful download is passed through unchanged."""
    buf = io.BytesIO(b"data")
    assert guarded_download(lambda: buf, "the data")() is buf
    toasts.error.assert_not_called()


def test_guarded_download_notifies_and_reraises(toasts: MagicMock) -> None:
    """A failing download notifies the user and aborts the transfer."""

    def _fail() -> io.BytesIO:
        raise ValueError("no accumulation model")

    with pytest.raises(ValueError, match="no accumulation model"):
        guarded_download(_fail, "the simulation")()
    message = toasts.error.call_args.args[0]
    assert "the simulation" in message
    assert "no accumulation model" in message
