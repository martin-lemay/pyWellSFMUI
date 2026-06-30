import param


class AppState(param.Parameterized):
    """Central application state. Single source of truth for all UI data."""

    # Shared inputs
    facies_model = param.Parameter(default=None, doc="FaciesModel instance")

    # Well Analysis inputs/outputs
    wells = param.List(default=[], doc="list[Well] loaded wells")
    accommodation_results = param.Dict(
        default={}, doc="dict[str, UncertaintyCurve] per well name"
    )

    # Simulation inputs
    accumulation_model = param.Parameter(default=None, doc="AccumulationModel instance")
    eustatic_curve = param.Parameter(default=None, doc="Curve instance for eustasy")
    depositional_env_model = param.Parameter(
        default=None, doc="DepositionalEnvironmentModel instance"
    )
    realization_data_list = param.List(
        default=[], doc="list[RealizationData] for simulation"
    )
    simulator_params = param.Parameter(
        default=None, doc="FSSimulatorParameters instance"
    )

    # Simulation outputs
    simulation_outputs = param.Parameter(
        default=None, doc="xarray.Dataset from FSSimulator.finalize()"
    )
