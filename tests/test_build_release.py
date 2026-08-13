"""Tests for the build release script."""

from pathlib import Path

from build_release import (
    _assemble_zip,
    _get_version,
)


class TestGetVersion:
    """Tests for _get_version."""

    def test_reads_version_from_init(self) -> None:
        """Reads the version string from pywellsfmui __init__.py."""
        version = _get_version()
        assert version == "0.1.0"


class TestAssembleZip:
    """Tests for _assemble_zip."""

    def test_creates_zip_with_correct_structure(self, tmp_path: Path) -> None:
        """Creates a zip with all expected files in the correct layout."""
        # Set up fake build artifacts
        exes_dir = tmp_path / "exes"
        exes_dir.mkdir()
        (exes_dir / "install.exe").write_bytes(b"fake")
        (exes_dir / "pyWellSFM.exe").write_bytes(b"fake")

        wheels_dir = tmp_path / "wheels"
        wheels_dir.mkdir()
        (wheels_dir / "pywellsfm-0.0.1-py3-none-any.whl").write_bytes(b"fake")
        (wheels_dir / "pywellsfmui-0.1.0-py3-none-any.whl").write_bytes(
            b"fake"
        )

        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        (templates_dir / "config.ini").write_text("[launcher]\nport = 5006\n")
        (templates_dir / "README.txt").write_text("Quick start guide")

        output_dir = tmp_path / "dist"
        output_dir.mkdir()

        zip_path = _assemble_zip(
            version="0.1.0",
            exes_dir=exes_dir,
            wheels_dir=wheels_dir,
            templates_dir=templates_dir,
            output_dir=output_dir,
        )

        assert zip_path.exists()
        assert zip_path.name == "pyWellSFM-v0.1.0.zip"

        import zipfile

        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
            prefix = "pyWellSFM-v0.1.0/"
            assert f"{prefix}install.exe" in names
            assert f"{prefix}pyWellSFM.exe" in names
            assert f"{prefix}config.ini" in names
            assert f"{prefix}README.txt" in names
            whl_names = [n for n in names if n.endswith(".whl")]
            assert len(whl_names) == 2
