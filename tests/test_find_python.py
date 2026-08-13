"""Tests for the Python finder utility."""

from unittest.mock import MagicMock, patch

from launcher.find_python import (
    _check_python_version,
    _find_anaconda_python,
    _find_path_python,
    _find_py_launcher_python,
    find_python,
)


class TestCheckPythonVersion:
    """Tests for _check_python_version."""

    @patch("launcher.find_python.subprocess.run")
    def test_valid_python_313(self, mock_run: MagicMock) -> None:
        """Python 3.13 is accepted."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="Python 3.13.1\n"
        )
        assert _check_python_version(r"C:\Python313\python.exe")

    @patch("launcher.find_python.subprocess.run")
    def test_valid_python_314(self, mock_run: MagicMock) -> None:
        """Python 3.14 is accepted."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="Python 3.14.0\n"
        )
        assert _check_python_version(r"C:\Python314\python.exe")

    @patch("launcher.find_python.subprocess.run")
    def test_old_python_312(self, mock_run: MagicMock) -> None:
        """Python 3.12 is rejected."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="Python 3.12.4\n"
        )
        assert not _check_python_version(r"C:\Python312\python.exe")

    @patch("launcher.find_python.subprocess.run")
    def test_python_not_found(self, mock_run: MagicMock) -> None:
        """FileNotFoundError returns False."""
        mock_run.side_effect = FileNotFoundError
        assert not _check_python_version(r"C:\bad\python.exe")

    @patch("launcher.find_python.subprocess.run")
    def test_python_nonzero_exit(self, mock_run: MagicMock) -> None:
        """Non-zero exit code returns False."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        assert not _check_python_version(r"C:\bad\python.exe")


class TestFindPyLauncher:
    """Tests for _find_py_launcher_python."""

    @patch("launcher.find_python._check_python_version")
    @patch("launcher.find_python.shutil.which")
    def test_py_launcher_found(
        self,
        mock_which: MagicMock,
        mock_check: MagicMock,
    ) -> None:
        """Returns 'py -3.13' when py launcher is available."""
        mock_which.return_value = r"C:\Windows\py.exe"
        mock_check.return_value = True
        result = _find_py_launcher_python()
        assert result == "py -3.13"

    @patch("launcher.find_python.shutil.which")
    def test_py_launcher_not_found(self, mock_which: MagicMock) -> None:
        """Returns None when py launcher is absent."""
        mock_which.return_value = None
        assert _find_py_launcher_python() is None


class TestFindPathPython:
    """Tests for _find_path_python."""

    @patch("launcher.find_python._check_python_version")
    @patch("launcher.find_python.shutil.which")
    def test_python_on_path(
        self,
        mock_which: MagicMock,
        mock_check: MagicMock,
    ) -> None:
        """Returns the path when a valid python is on PATH."""
        mock_which.return_value = r"C:\Python313\python.exe"
        mock_check.return_value = True
        assert _find_path_python() == r"C:\Python313\python.exe"

    @patch("launcher.find_python.shutil.which")
    def test_python_not_on_path(self, mock_which: MagicMock) -> None:
        """Returns None when python is not on PATH."""
        mock_which.return_value = None
        assert _find_path_python() is None


class TestFindAnacondaPython:
    """Tests for _find_anaconda_python."""

    @patch("launcher.find_python._check_python_version")
    @patch("launcher.find_python.Path.exists")
    @patch("launcher.find_python.os.environ.get")
    def test_anaconda_found_userprofile(
        self,
        mock_env: MagicMock,
        mock_exists: MagicMock,
        mock_check: MagicMock,
    ) -> None:
        """Returns path when Anaconda found under USERPROFILE."""
        mock_env.side_effect = lambda k, d="": {
            "USERPROFILE": r"C:\Users\Geo",
            "LOCALAPPDATA": "",
            "PROGRAMDATA": "",
        }.get(k, d)
        mock_exists.return_value = True
        mock_check.return_value = True
        result = _find_anaconda_python()
        assert result is not None
        assert "python.exe" in result

    @patch("launcher.find_python._check_python_version")
    @patch("launcher.find_python.Path.exists")
    @patch("launcher.find_python.os.environ.get")
    def test_anaconda_not_found(
        self,
        mock_env: MagicMock,
        mock_exists: MagicMock,
        mock_check: MagicMock,
    ) -> None:
        """Returns None when no Anaconda installation exists."""
        mock_env.return_value = ""
        mock_exists.return_value = False
        assert _find_anaconda_python() is None


class TestFindPython:
    """Tests for the main find_python function."""

    @patch("launcher.find_python._find_conda_base_python")
    @patch("launcher.find_python._find_anaconda_python")
    @patch("launcher.find_python._find_path_python")
    @patch("launcher.find_python._find_py_launcher_python")
    def test_returns_first_match(
        self,
        mock_py: MagicMock,
        mock_path: MagicMock,
        mock_anaconda: MagicMock,
        mock_conda: MagicMock,
    ) -> None:
        """Returns the first finder result that is not None."""
        mock_py.return_value = None
        mock_path.return_value = r"C:\Python313\python.exe"
        mock_anaconda.return_value = None
        mock_conda.return_value = None
        assert find_python() == r"C:\Python313\python.exe"

    @patch("launcher.find_python._find_conda_base_python")
    @patch("launcher.find_python._find_anaconda_python")
    @patch("launcher.find_python._find_path_python")
    @patch("launcher.find_python._find_py_launcher_python")
    def test_returns_none_when_no_python(
        self,
        mock_py: MagicMock,
        mock_path: MagicMock,
        mock_anaconda: MagicMock,
        mock_conda: MagicMock,
    ) -> None:
        """Returns None when no Python 3.13+ interpreter is found."""
        mock_py.return_value = None
        mock_path.return_value = None
        mock_anaconda.return_value = None
        mock_conda.return_value = None
        assert find_python() is None
