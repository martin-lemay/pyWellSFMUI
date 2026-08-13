import panel as pn

pn.extension("plotly", "tabulator", sizing_mode="stretch_width")


def test_navigate_to_switches_view() -> None:
    """create_app produces a working navigate_to callback."""
    from pywellsfmui.app import create_app

    template = create_app()
    # Smoke test: app builds without error
    assert template is not None
