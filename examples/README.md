# pyWellSFMUI Examples

Example input files for the pyWellSFMUI application, organized by
complexity. Each example can be loaded directly into the app.

## Accommodation Workflow (Well Data Analysis tab)

These files are loaded separately into the Well Data Analysis tab.

| File | Description |
|------|-------------|
| `accommodation_facies_model.json` | 3 siliciclastic facies (sandstone, siltstone, shale) with water depth criteria |
| `accommodation_well.json` | Well with 9 lithology intervals (120 m depth) |
| `accommodation_well2.json` | Second well for multi-well comparison |

**Steps:** Load the facies model, import wells, then run the accommodation
calculation. See the User Guide for a full walkthrough.

## Simulation Workflow (Simulation tab)

These are complete simulation files that can be loaded via
**File > Load Simulation**.

| File | Complexity | Description |
|------|------------|-------------|
| `simulation_simple.json` | Simple | 2 wells, 3 carbonate elements (Gaussian model), no depositional environments |
| `simulation_carbonate_platform.json` | Advanced | 5 wells across a protected carbonate ramp, 6 elements with water depth + energy reduction curves, 11 depositional environments |
