import param


class AppState(param.Parameterized):
    """Central application state. Single source of truth for all UI data."""

    # Shared inputs
    facies_model = param.Parameter(default=None, doc="FaciesModel instance")

    # Well Analysis inputs/outputs
    wells = param.List(default=[], doc="list[Well] loaded wells")
    well_facies_log_names = param.Dict(
        default={}, doc="dict[str, str] well name -> selected facies log name"
    )
    accommodation_results = param.Dict(
        default={},
        doc="dict[str, AccommodationSpaceWellCalculator] per well name",
    )
    well_accommodation_computed = param.Dict(
        default={},
        doc="dict[str, bool] well name -> accommodation computed flag",
    )

    # Simulation inputs
    accumulation_model = param.Parameter(default=None, doc="AccumulationModel instance")
    eustatic_curve = param.Parameter(default=None, doc="Curve instance for eustasy")
    depositional_env_model = param.Parameter(
        default=None, doc="DepositionalEnvironmentModel instance"
    )
    use_de_simulator = param.Boolean(
        default=False,
        doc="Whether to use depositional environment simulator",
    )
    realization_data_list = param.List(
        default=[], doc="list[RealizationData] for simulation"
    )
    simulator_params = param.Parameter(
        default=None, doc="FSSimulatorParameters instance"
    )
    de_simulator_weights = param.Dict(
        default={},
        doc="dict[str, float] environment name -> prior weight",
    )
    de_simulator_params = param.Parameter(
        default=None,
        doc="DESimulatorParameters instance",
    )
    global_env_conditions = param.Parameter(
        default=None,
        doc="EnvironmentConditionsModel for global mode",
    )

    # Simulation outputs
    simulation_outputs = param.Parameter(
        default=None, doc="xarray.Dataset from FSSimulator.finalize()"
    )
    simulated_wells = param.List(
        default=[],
        doc="list[Well] simulated wells from FSSimulator",
    )
