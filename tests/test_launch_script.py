"""Tests for the launch script."""

import socket
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from launcher.launch_script import (
    _check_venv,
    _is_port_in_use,
    _read_config,
)


class TestCheckVenv:
    """Tests for _check_venv."""

    @patch("launcher.launch_script.Path.exists")
    def test_venv_exists(self, mock_exists: MagicMock) -> None:
        """No error when venv python.exe exists."""
        mock_exists.return_value = True
        # Should not raise
        _check_venv(Path(r"C:\app\.venv"))

    @patch("launcher.launch_script.Path.exists")
    def test_venv_missing(self, mock_exists: MagicMock) -> None:
        """SystemExit raised when venv python.exe is absent."""
        mock_exists.return_value = False
        with pytest.raises(SystemExit), patch("builtins.input"):
            _check_venv(Path(r"C:\app\.venv"))


class TestReadConfig:
    """Tests for _read_config."""

    def test_read_default_config(self, tmp_path: Path) -> None:
        """Port 5006 is returned when config has default."""
        config_file = tmp_path / "config.ini"
        config_file.write_text("[launcher]\nport = 5006\n")
        config = _read_config(config_file)
        assert config["port"] == 5006

    def test_read_custom_port(self, tmp_path: Path) -> None:
        """Custom port value is read from config file."""
        config_file = tmp_path / "config.ini"
        config_file.write_text("[launcher]\nport = 8080\n")
        config = _read_config(config_file)
        assert config["port"] == 8080

    def test_missing_config_uses_defaults(self, tmp_path: Path) -> None:
        """Default port 5006 is used when config file is absent."""
        config_file = tmp_path / "nonexistent.ini"
        config = _read_config(config_file)
        assert config["port"] == 5006


class TestIsPortInUse:
    """Tests for _is_port_in_use."""

    def test_unused_port(self) -> None:
        """High ephemeral port is reported as free."""
        # Use a high port unlikely to be in use
        assert not _is_port_in_use(59123)

    def test_used_port(self) -> None:
        """Actively bound port is reported as in use."""
        # Bind a port, then check
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.listen(1)
        try:
            assert _is_port_in_use(port)
        finally:
            sock.close()
