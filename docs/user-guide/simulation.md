# Simulation

The **Simulation** section is where you configure all inputs for a stratigraphic forward modeling run. It is organized into numbered steps plus optional sections.

## Loading and Saving Simulation Files

At the top of the Simulation tab:

- Use the **file input** (accepts `.json`) to load a complete simulation file. This populates all editors below (accumulation model, eustatic curve, depositional environments, realization data, simulator parameters).
- Click **Save Simulation File** to download the current configuration as a single JSON file.

## Step 1 -- Accumulation Model

The accumulation model defines the sedimentary elements and their production rates.

### Creating or Loading

- Click **New Model** to create an empty accumulation model.
- Use the **Load Accumulation Model** file input to load from JSON.
- Click **Save Accum. Model** to download the current model.
- Click **Init From Facies Model** to create one element per facies in the currently loaded facies model.

### Editing Elements

The editor uses a master-detail layout:

- **Left -- Element List**: Shows all elements.
  - To **add** an element: double-click the "New Element..." row and type a name.
  - To **remove**: select and click **Remove**.

- **Right -- Selected Element**: When an element is selected, configure:
  - **Model Type**: *Gaussian* or *EnvironmentOptimum*.
  - **Accumulation Rate** (m/My): mean rate for Gaussian, maximum rate for EnvironmentOptimum.
  - **Std Dev Factor** (Gaussian only): controls rate variability.

### Reduction Curves (EnvironmentOptimum only)

When the model type is *EnvironmentOptimum*, a reduction curves section appears:

- **Env. Condition list**: Each condition has a reduction curve that modulates the element's production rate based on an environmental factor.
  - To **add** a condition: double-click the "New Curve..." row and type a name.
  - To **load** a curve from a file: use the **Load Reduction Curve** file input (`.json` or `.csv`).
  - To **remove** a condition: select and click **Remove**.

- **Curve Data table**: Edit individual (X, Y) points of the selected curve.
  - X values must be monotonically increasing.
  - Y values (reduction coefficients) must be between 0 and 1.
  - A live **plot** on the right visualizes the curve.

## Step 2 (Optional) -- Eustatism

This section is collapsed by default. Expand it to define a eustatic (sea-level) curve.

- The **curve editor** lets you add/edit/remove (Age, Eustatism) points in a table.
- Load a curve from a `.json` or `.csv` file.
- A live **plot** shows the eustatic curve.
- The curve needs at least 2 points to be valid.

## Step 3 -- Depositional Environment and Conditions

This section defines the environmental conditions that control facies distribution.

### Mode Selection

Two modes are available via a radio button:

1. **Global mode**: Environmental conditions are defined once and apply everywhere. Simpler setup.
2. **Environments mode**: Conditions are defined per depositional environment. Used with the DE (Depositional Environment) simulator.

### Global Mode

- Load/save conditions from/to JSON.
- A two-column layout shows:
  - **Environment Conditions table**: list of conditions (e.g., waterDepth, temperature).
  - **Condition Detail**: configure the selected condition's model.

### Environments Mode

- Create a new model from templates: *Empty*, *Carbonate Open Ramp*, or *Carbonate Protected Ramp*.
- Load/save the full DE simulation configuration from/to JSON.
- A three-column layout:
  1. **Environments list**: add/remove environments.
  2. **Environment Properties**: name, distality, water depth range (min/max).
  3. **Conditions table + detail**: same as global mode, but per-environment.

### Condition Model Types

Each condition can use one of five model types:

| Type | Parameters |
|------|-----------|
| Constant | Value |
| Uniform | Min, Max |
| Triangular | Min, Mode, Max |
| Gaussian | Mean, Std Dev, Min, Max |
| Curve | Related Condition (X-axis), curve data points |

### DE Simulator Settings (Environments mode only)

A collapsed card at the bottom exposes advanced DE simulator parameters:

- **Environment Weights table**: weight per environment.
- **Simulator parameters**: waterDepth sigma/weight, transition sigma/weight, trend sigma/window/weight, and interval distance method.

## Step 4 -- Realization Data

This section defines per-well settings for the simulation.

### Adding Wells

- Use the **Load Well** file input to upload `.json` or `.las` files.
- Click **Add** to create an empty well.

### Well List (Left Panel)

Each well row shows:

- **Well name** (click to select and show detail).
- **Initial Bathymetry** (m): starting water depth for the simulation.
- **Initial Environment**: dropdown populated from the depositional environment model.
- **Remove** button.

### Well Detail (Right Panel)

When a well is selected, the detail panel shows:

- **Well Name**: editable (renames the well).
- **Depth** (m): total well depth.
- **Well Head Coordinates**: X, Y, Z.
- **Markers table**: stratigraphic markers with Name, Depth, Age, and Type (MFS, SB, TS, Unknown, etc.). Add markers by editing the "New..." row. Remove with the **Remove Marker** button.
- **Subsidence Curve**: choose between *Cumulative* and *Rate* subsidence types. Edit curve data in the table, load from file, or erase. A live plot shows the curve with marker positions.

## Step 5 (Optional) -- Facies Model

Same facies model editor as in the Well Analysis tab (see {doc}`well-analysis`). Collapsed by default.

## Advanced Simulation Parameters

A collapsed card at the bottom exposes:

| Parameter | Description |
|-----------|-------------|
| Max Water-Depth Change / Step (m) | Maximum allowed water depth change per time step |
| Min Time Step (Myr) | Minimum simulation time step |
| Max Time Step (Myr) | Maximum simulation time step |
| Safety Factor | Adaptive time-stepping safety factor (0--1) |
| Max Steps | Maximum number of simulation steps |

## Running the Simulation

The **Run Simulation** button is enabled when an accumulation model and at least one well with realization data are defined. A status indicator shows "Ready" (green) or "Invalid inputs" (red).

When clicked:

1. The button is disabled and a spinner appears.
2. The log panel expands to show simulation progress.
3. Upon completion, the app automatically navigates to the **Visualization** tab.
