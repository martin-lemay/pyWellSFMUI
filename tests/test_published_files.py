"""Checks on the files published with the documentation."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# README, documentation pages and the example files the docs link to.
PUBLISHED_FILES = sorted(
    [
        ROOT / "README.md",
        *(ROOT / "docs").glob("*.md"),
        *(ROOT / "docs" / "user-guide").glob("*.md"),
        *(ROOT / "examples").glob("*"),
    ]
)

# Absolute paths of a local machine: Windows drive paths, user/system
# directories of POSIX systems and installed packages.
ABSOLUTE_PATH = re.compile(
    r"\b[A-Za-z]:[\\/]+[^\\/\s\"'<>]+[\\/]"
    r"|(?<![\w.])/(?:home|Users|root|mnt|tmp|opt|var)/"
    r"|site-packages"
)


@pytest.mark.parametrize(
    "path", PUBLISHED_FILES, ids=lambda p: p.relative_to(ROOT).as_posix()
)
def test_published_file_has_no_absolute_path(path: Path) -> None:
    """Published files must not leak paths of a local machine."""
    leaks = [
        f"line {number}: {match.group(0)!r}"
        for number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        )
        for match in ABSOLUTE_PATH.finditer(line)
    ]
    assert not leaks, "Absolute paths found:\n" + "\n".join(leaks)
