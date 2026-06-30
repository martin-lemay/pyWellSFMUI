from datetime import datetime

import pytest

from pywellsfmui.state.message_store import Message, MessageLevel


def test_message_level_values():
    assert MessageLevel.DEBUG == "DEBUG"
    assert MessageLevel.INFO == "INFO"
    assert MessageLevel.WARNING == "WARNING"
    assert MessageLevel.ERROR == "ERROR"


def test_message_creation():
    msg = Message(
        timestamp=datetime(2026, 1, 1, 12, 0, 0),
        level=MessageLevel.INFO,
        text="hello",
        source="actions",
    )
    assert msg.level == MessageLevel.INFO
    assert msg.text == "hello"
    assert msg.source == "actions"


def test_message_is_immutable():
    msg = Message(
        timestamp=datetime(2026, 1, 1),
        level=MessageLevel.INFO,
        text="hello",
        source=None,
    )
    with pytest.raises(AttributeError):
        msg.text = "changed"


from pywellsfmui.state.message_store import MessageStore


def test_add_appends_message():
    store = MessageStore()
    store.add(MessageLevel.INFO, "test message", source="actions")
    assert len(store.messages) == 1
    msg = store.messages[0]
    assert msg.level == MessageLevel.INFO
    assert msg.text == "test message"
    assert msg.source == "actions"
    assert isinstance(msg.timestamp, datetime)


def test_add_without_source():
    store = MessageStore()
    store.add(MessageLevel.WARNING, "no source")
    assert store.messages[0].source is None


def test_add_caps_at_max_messages():
    store = MessageStore()
    for i in range(250):
        store.add(MessageLevel.DEBUG, f"msg {i}")
    assert len(store.messages) == MessageStore.MAX_MESSAGES
    # Oldest messages were dropped — first message should be msg 50
    assert store.messages[0].text == "msg 50"
    assert store.messages[-1].text == "msg 249"


def test_clear():
    store = MessageStore()
    store.add(MessageLevel.INFO, "one")
    store.add(MessageLevel.INFO, "two")
    store.clear()
    assert store.messages == []


import logging


def test_logging_handler_info():
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


def test_logging_handler_level_mapping():
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
        MessageLevel.ERROR,  # CRITICAL maps to ERROR
    ]
    logger.removeHandler(handler)
