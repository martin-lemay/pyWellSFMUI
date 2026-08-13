import logging
from datetime import datetime

import pytest

from pywellsfmui.state.message_store import (
    Message,
    MessageLevel,
    MessageStore,
)


def test_message_level_values() -> None:
    """Test MessageLevel enum values."""
    assert MessageLevel.DEBUG == "DEBUG"
    assert MessageLevel.INFO == "INFO"
    assert MessageLevel.WARNING == "WARNING"
    assert MessageLevel.ERROR == "ERROR"


def test_message_creation() -> None:
    """Test creating a Message instance."""
    msg = Message(
        timestamp=datetime(2026, 1, 1, 12, 0, 0),
        level=MessageLevel.INFO,
        text="hello",
        source="actions",
    )
    assert msg.level == MessageLevel.INFO
    assert msg.text == "hello"
    assert msg.source == "actions"


def test_message_is_immutable() -> None:
    """Test Message is frozen (immutable)."""
    msg = Message(
        timestamp=datetime(2026, 1, 1),
        level=MessageLevel.INFO,
        text="hello",
        source=None,
    )
    with pytest.raises(AttributeError, match="cannot assign"):
        msg.text = "changed"


def test_add_appends_message() -> None:
    """Test adding a message to the store."""
    store = MessageStore()
    store.add(
        MessageLevel.INFO,
        "test message",
        source="actions",
    )
    assert len(store.messages) == 1
    msg = store.messages[0]
    assert msg.level == MessageLevel.INFO
    assert msg.text == "test message"
    assert msg.source == "actions"
    assert isinstance(msg.timestamp, datetime)


def test_add_without_source() -> None:
    """Test adding a message without source."""
    store = MessageStore()
    store.add(MessageLevel.WARNING, "no source")
    assert store.messages[0].source is None


def test_add_caps_at_max_messages() -> None:
    """Test store caps at MAX_MESSAGES."""
    store = MessageStore()
    for i in range(250):
        store.add(MessageLevel.DEBUG, f"msg {i}")
    assert len(store.messages) == MessageStore.MAX_MESSAGES
    # Oldest messages were dropped
    assert store.messages[0].text == "msg 50"
    assert store.messages[-1].text == "msg 249"


def test_clear() -> None:
    """Test clearing the message store."""
    store = MessageStore()
    store.add(MessageLevel.INFO, "one")
    store.add(MessageLevel.INFO, "two")
    store.clear()
    assert store.messages == []


def test_logging_handler_info() -> None:
    """Test logging handler captures INFO."""
    store = MessageStore()
    handler = store.as_logging_handler()
    logger = logging.getLogger("test.handler.info")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.info("log info message")
    assert len(store.messages) == 1
    assert store.messages[0].level == MessageLevel.INFO
    assert store.messages[0].text == "log info message"
    assert store.messages[0].source == "test.handler.info"
    logger.removeHandler(handler)


def test_logging_handler_level_mapping() -> None:
    """Test logging handler maps levels correctly."""
    store = MessageStore()
    handler = store.as_logging_handler()
    logger = logging.getLogger("test.handler.levels")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    logger.debug("d")
    logger.info("i")
    logger.warning("w")
    logger.error("e")
    logger.critical("c")

    levels = [m.level for m in store.messages]
    assert levels == [
        MessageLevel.DEBUG,
        MessageLevel.INFO,
        MessageLevel.WARNING,
        MessageLevel.ERROR,
        MessageLevel.ERROR,  # CRITICAL -> ERROR
    ]
    logger.removeHandler(handler)
