"""Tests for the install script."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from launcher.install_script import (
    _create_venv,
    _install_wheels,
    _verify_install,
)


class TestCreateVenv:
    """Tests for _create_venv."""

    @patch("launcher.install_script.shutil.rmtree")
    @patch("launcher.install_script.subprocess.run")
    def test_creates_venv(
        self,
        mock_run: MagicMock,
        mock_rmtree: MagicMock,
    ) -> None:
        """Verify subprocess.run is called with correct venv args."""
        mock_run.return_value = MagicMock(returncode=0)
        venv_dir = Path(r"C:\app\.venv")
        _create_venv("python", venv_dir)
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "python" in args[0]
        assert "-m" in args
        assert "venv" in args

    @patch("launcher.install_script.shutil.rmtree")
    @patch("launcher.install_script.subprocess.run")
    @patch("launcher.install_script.Path.exists")
    def test_removes_existing_venv(
        self,
        mock_exists: MagicMock,
        mock_run: MagicMock,
        mock_rmtree: MagicMock,
    ) -> None:
        """Verify existing venv directory is removed before recreating."""
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(returncode=0)
        venv_dir = Path(r"C:\app\.venv")
        _create_venv("python", venv_dir)
        mock_rmtree.assert_called_once_with(venv_dir)

    @patch("builtins.input")
    @patch("launcher.install_script.shutil.rmtree")
    @patch("launcher.install_script.subprocess.run")
    def test_raises_on_failure(
        self,
        mock_run: MagicMock,
        mock_rmtree: MagicMock,
        mock_input: MagicMock,
    ) -> None:
        """Verify SystemExit is raised when venv creation fails."""
        mock_run.return_value = MagicMock(returncode=1)
        with pytest.raises(SystemExit):
            _create_venv("python", Path(r"C:\app\.venv"))


class TestInstallWheels:
    """Tests for _install_wheels."""

    @patch("launcher.install_script.glob.glob")
    @patch("launcher.install_script.subprocess.run")
    def test_installs_wheels(
        self,
        mock_run: MagicMock,
        mock_glob: MagicMock,
    ) -> None:
        """Verify pip install is called with discovered wheel files."""
        mock_glob.return_value = [r"C:\app\wheels\pkg.whl"]
        mock_run.return_value = MagicMock(returncode=0)
        venv_dir = Path(r"C:\app\.venv")
        wheels_dir = Path(r"C:\app\wheels")
        _install_wheels(venv_dir, wheels_dir)
        args = mock_run.call_args[0][0]
        assert "pip" in str(args[0])
        assert "install" in args

    @patch("builtins.input")
    @patch("launcher.install_script.glob.glob")
    @patch("launcher.install_script.subprocess.run")
    def test_raises_on_pip_failure(
        self,
        mock_run: MagicMock,
        mock_glob: MagicMock,
        mock_input: MagicMock,
    ) -> None:
        """Verify SystemExit is raised when pip install fails."""
        mock_glob.return_value = [r"C:\app\wheels\pkg.whl"]
        mock_run.return_value = MagicMock(returncode=1)
        with pytest.raises(SystemExit):
            _install_wheels(
                Path(r"C:\app\.venv"),
                Path(r"C:\app\wheels"),
            )


class TestVerifyInstall:
    """Tests for _verify_install."""

    @patch("launcher.install_script.subprocess.run")
    def test_verify_success(self, mock_run: MagicMock) -> None:
        """Verify no exception raised when import check succeeds."""
        mock_run.return_value = MagicMock(returncode=0)
        # Should not raise
        _verify_install(Path(r"C:\app\.venv"))

    @patch("builtins.input")
    @patch("launcher.install_script.subprocess.run")
    def test_verify_failure(
        self,
        mock_run: MagicMock,
        mock_input: MagicMock,
    ) -> None:
        """Verify SystemExit is raised when import verification fails."""
        mock_run.return_value = MagicMock(returncode=1, stderr="ImportError")
        with pytest.raises(SystemExit):
            _verify_install(Path(r"C:\app\.venv"))
