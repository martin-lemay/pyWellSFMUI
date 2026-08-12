"""Centralized colors and style helpers for the UI."""


class Colors:
    """Semantic color palette used across all components."""

    ERROR = "#d32f2f"
    SUCCESS = "#2e7d32"
    WARNING = "#ed6c02"
    INACTIVE = "#9E9E9E"
    MUTED = "gray"
    INHERIT = "inherit"
    ACCENT = "#1565C0"


def status_html(text: str, color: str) -> str:
    """Build a colored italic status span."""
    return f'<span style="color: {color}; font-style: italic;">{text}</span>'
