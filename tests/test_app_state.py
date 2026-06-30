from pywellsfmui.state.app_state import AppState


def test_app_state_defaults():
    state = AppState()
    assert state.facies_model is None
    assert state.wells == []
    assert state.accommodation_results == {}
    assert state.accumulation_model is None
    assert state.eustatic_curve is None
    assert state.depositional_env_model is None
    assert state.realization_data_list == []
    assert state.simulator_params is None
    assert state.simulation_outputs is None


def test_app_state_set_facies_model():
    """Verify that setting a param triggers watchers."""
    state = AppState()
    triggered = []

    def on_change(*events):
        triggered.append(events)

    state.param.watch(on_change, ["facies_model"])
    state.facies_model = "mock_model"
    assert len(triggered) == 1
