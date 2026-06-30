from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

import param


class MessageLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass(frozen=True)
class Message:
    timestamp: datetime
    level: MessageLevel
    text: str
    source: str | None


class MessageStore(param.Parameterized):
    """Collects messages from Actions and Python logging for display in the UI."""

    messages = param.List(default=[], doc="list[Message]")

    MAX_MESSAGES = 200

    def add(
        self, level: MessageLevel, text: str, source: str | None = None
    ) -> None:
        msg = Message(
            timestamp=datetime.now(),
            level=level,
            text=text,
            source=source,
        )
        updated = [*self.messages, msg]
        if len(updated) > self.MAX_MESSAGES:
            updated = updated[-self.MAX_MESSAGES :]
        self.messages = updated

    def clear(self) -> None:
        self.messages = []

    def as_logging_handler(self) -> logging.Handler:
        return _MessageStoreHandler(self)


_LOGGING_LEVEL_MAP = {
    logging.DEBUG: MessageLevel.DEBUG,
    logging.INFO: MessageLevel.INFO,
    logging.WARNING: MessageLevel.WARNING,
    logging.ERROR: MessageLevel.ERROR,
    logging.CRITICAL: MessageLevel.ERROR,
}


class _MessageStoreHandler(logging.Handler):
    def __init__(self, store: MessageStore) -> None:
        super().__init__()
        self.store = store

    def emit(self, record: logging.LogRecord) -> None:
        level = _LOGGING_LEVEL_MAP.get(record.levelno, MessageLevel.ERROR)
        self.store.add(level, record.getMessage(), source=record.name)
