# Visualization

The **Visualization** section displays simulation results. It appears after a simulation has been run from the Simulation tab. If no simulation results are available, placeholder messages are shown.

## Results Section

For each well in the simulation, two side-by-side plots are displayed:

### Elevation Plot

Shows the evolution of the sedimentary column through time:

- **X-axis**: Time (My).
- **Basement** curve: tectonic subsidence.
- **Topography** curve: basement + cumulative thickness.
- **Sea level** curve: eustatic sea level.
- The area between basement and topography represents the sedimentary fill.

### Production Rates Plot

Shows depositional rates and environmental conditions through time:

- **Per-element deposition rates**: one trace per sedimentary element (e.g., carbonate, siliciclastic), with matching colors.
- **Total deposition rate**: sum of all element rates.
- **Water depth**: evolution of water depth at the well location.
- **Environment** (if available): the assigned depositional environment at each time step, shown as a categorical color bar.

## Wells Section

Displays well log plots for both the input (real) wells and the simulated wells side by side, allowing direct visual comparison.

### Controls

- **Log** dropdown: Select which log to display. Available options depend on the well data (e.g., Facies, MainElement, Environment, or any continuous/discrete log).
- **Show markers** checkbox: Toggle the visibility of stratigraphic markers on all well plots.
- **Age domain** checkbox: Switch the Y-axis between depth (metres) and age (My).

### Well Log Plots

Each well is shown as a vertical log plot:

- The selected log is displayed with color-coded values.
- For the **MainElement** log, colors match the element traces in the production rates plot.
- For the **Environment** log, colors use a predefined environment color palette.
- Stratigraphic markers (when enabled) are shown as horizontal lines with labels.
- All wells share a common Y-axis range for easy comparison.

For each realization, the input well and simulated well are displayed side by side so you can visually assess the simulation fit.
