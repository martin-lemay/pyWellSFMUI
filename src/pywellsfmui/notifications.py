"""Error notifications shown to the user as toasts in the browser."""

import io
import logging
from collections.abc import Callable

import panel as pn

logger = logging.getLogger(__name__)

_ERROR_DURATION_MS = 8000


def notify_error(message: str) -> None:
    """Show an error toast; no-op when notifications are unavailable."""
    notifications = pn.state.notifications
    if notifications is not None:
        notifications.error(message, duration=_ERROR_DURATION_MS)


def guarded_download(
    callback: Callable[[], io.BytesIO], what: str
) -> Callable[[], io.BytesIO]:
    """Wrap a FileDownload callback to report failures to the user.

    On failure the user is notified and the exception is re-raised, which
    aborts the transfer instead of downloading an empty file.

    Args:
        callback: function building the file content.
        what: description of the exported content, used in the message.

    Returns:
        The wrapped callback.
    """

    def _download() -> io.BytesIO:
        try:
            return callback()
        except Exception as exc:
            logger.debug("Export of %s failed", what, exc_info=True)
            notify_error(f"Could not export {what}: {exc}")
            raise

    return _download
