# Examples

pyWellSFMUI ships with ready-to-use example files that cover the two main
workflows -- accommodation calculation and forward simulation -- at increasing
levels of complexity.

## Download All Examples

| File | Description |
|------|-------------|
| {download}`accommodation_facies_model.json <../../examples/accommodation_facies_model.json>` | Facies model (3 siliciclastic facies) |
| {download}`accommodation_well.json <../../examples/accommodation_well.json>` | Well0 -- 120 m, 9 intervals |
| {download}`accommodation_well2.json <../../examples/accommodation_well2.json>` | Well1 -- 100 m, 9 intervals |
| {download}`simulation_simple.json <../../examples/simulation_simple.json>` | Simple carbonate simulation (3 producers, 2 wells) |
| {download}`simulation_carbonate_platform.json <../../examples/simulation_carbonate_platform.json>` | Carbonate protected ramp (6 producers, 5 wells, 11 environments) |

## Accommodation Calculation

**Files:**

- {download}`accommodation_facies_model.json <../../examples/accommodation_facies_model.json>` -- Facies model
- {download}`accommodation_well.json <../../examples/accommodation_well.json>` -- Well0 (120 m, 9 intervals)
- {download}`accommodation_well2.json <../../examples/accommodation_well2.json>` -- Well1 (100 m, 9 intervals)

**Geological context:**
A simple siliciclastic setting with three facies defined by water depth
criteria:

- **sandstone** -- 0 to 5 m (shoreline to very shallow marine)
- **siltstone** -- 5 to 30 m (shallow to mid-shelf)
- **shale** -- 20 to 50 m (mid-shelf to outer shelf)

Note the overlap between siltstone and shale (20--30 m), which introduces
uncertainty in the accommodation calculation.

**Walkthrough:**

1) Open the **Well Data Analysis** tab.
2) In the **Facies Model** section, click **Load** and select
   `accommodation_facies_model.json`.
   Three facies appear in the table, each with a WaterDepth criterion.
3) In the **Well Import** section, click **Load Well** and select
   `accommodation_well.json`. The lithology striplog is displayed.
4) (Optional) Load `accommodation_well2.json` to add a second well.
5) Click **Compute Accommodation**. The app calculates accommodation
   uncertainty envelopes (min / median / max) for each well based on the
   facies water depth ranges.
6) Inspect results in the **Results** section:
   - The single-well plot shows accommodation vs. depth with the uncertainty
     envelope.
   - If two wells are loaded, the **Well Comparison** section lets you overlay
     their accommodation curves.

## Simple Simulation

**File:** {download}`simulation_simple.json <../../examples/simulation_simple.json>`

**Geological context:**
A minimal carbonate platform with three sediment producers, each modeled
with a Gaussian accumulation distribution:

| Element | Rate (m/Myr) | Std. Dev. Factor | Peak Water Depth |
|---------|-------------|------------------|------------------|
| CarbonateShallow | 1.0 | 0.4 | Shallowest |
| CarbonateIntermediate | 0.5 | 0.2 | Intermediate |
| CarbonateDeep | 0.1 | 0.05 | Deepest |

Two wells at different initial bathymetries (15 m and 20 m) are simulated
over 30 Myr with an oscillating eustatic curve and linear cumulative
subsidence.

**Walkthrough:**

1) Open the **Simulation** tab.
2) Click **Load Simulation** and select `simulation_simple.json`.
   All inputs are populated automatically:
   - The **Accumulation Model** shows three Gaussian elements.
   - The **Eustatism** curve oscillates between -10 m and +20 m.
   - Two wells appear in the **Realization Data** section with their
     subsidence curves and markers.
3) Click **Run Simulation**.
4) Switch to the **Visualization** tab to inspect results:
   - **Results** section: elevation vs. time and production rate plots for
     each well.
   - **Wells** section: simulated well logs showing the stacking pattern of
     the three carbonate facies.

**What to observe:**
The shallow well (15 m initial bathymetry) records more CarbonateShallow
intervals, while the deeper well (20 m) has thicker CarbonateIntermediate
and CarbonateDeep intervals. Sea-level oscillations create cyclic
alternations in both wells.

## Advanced Simulation: Carbonate Protected Ramp

**File:** {download}`simulation_carbonate_platform.json <../../examples/simulation_carbonate_platform.json>`

**Geological context:**
A Cretaceous-style carbonate protected ramp with six sediment producers
controlled by water depth and wave energy:

| Element | Rate (m/Myr) | Optimal Water Depth | Optimal Energy |
|---------|-------------|--------------------:|---------------:|
| Miliolid | 1.0 | 0--5 m | Low (0.0) |
| Rudist | 2.0 | ~10 m | Medium (0.5) |
| Corals | 5.0 | 0--5 m | High (1.0) |
| Ooid | 1.5 | ~20 m | Medium (0.5) |
| Bioclast | 1.0 | ~50 m | Low (0.0) |
| BasinalMud | 0.5 | 80+ m | Low (0.0) |

Each element uses **EnvironmentOptimum** reduction curves for both water
depth and energy, meaning the actual accumulation rate is the product of
the base rate and two reduction coefficients.

Eleven depositional environments span from Continent to Basin, each with
water depth, energy, and temperature ranges. The depositional environment
simulator is enabled, so the app assigns environments at each time step
based on local conditions.

Five wells sample the ramp profile:

| Well | Initial Bathymetry | Initial Environment |
|------|-------------------:|---------------------|
| Lagoon_Well | 5 m | Lagoon |
| Buildup_Well | 1 m | Buildup |
| ForeReef_Well | 10 m | ForeReef |
| OuterRamp_Well | 30 m | OuterRamp |
| Basin_Well | 200 m | ShelfSlope |

**Walkthrough:**

1) Open the **Simulation** tab.
2) Click **Load Simulation** and select
   `simulation_carbonate_platform.json`. All inputs are populated:
   - The **Accumulation Model** shows six EnvironmentOptimum elements, each
     with WaterDepth and Energy reduction curves.
   - The **Depositional Environments** section shows 11 environments with
     their condition ranges.
   - Five wells appear in **Realization Data**, each with an initial
     environment and shared cumulative subsidence curves.
3) Click **Run Simulation**.
4) Switch to the **Visualization** tab:
   - **Results** section: compare elevation histories and production rate
     breakdowns across the five wells.
   - **Wells** section: examine the simulated lithostratigraphy and
     environment assignments for each well.

**What to observe:**
- The Lagoon and Buildup wells are dominated by Miliolid and Corals
  (shallow, low-to-high energy producers).
- The ForeReef well shows a mix of Rudist and Corals at moderate depths.
- The OuterRamp well transitions to Ooid and Bioclast as water deepens.
- The Basin well records mostly BasinalMud with very low accumulation rates.
- During sea-level lowstands, shallow wells may emerge (Continent
  environment) and stop producing sediment, creating gaps in the record.
