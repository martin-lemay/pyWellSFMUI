# Import and Export

pyWellSFMUI supports loading and saving data at multiple levels. All files use JSON format unless otherwise noted.

## File Formats

### Well Files

Wells can be loaded from two formats:

- **JSON** (`.json`): pyWellSFM's native well format. Contains well metadata, markers, logs, and curves.
- **LAS** (`.las`): Standard Log ASCII Standard files. Continuous and discrete logs are imported as well logs.

Wells are loaded via file input widgets in the Well Analysis tab (Step 2) and the Simulation tab (Step 4 -- Realization Data).

### Facies Model

- **Format**: JSON (`.json`)
- **Load/Save**: via the facies model editor (available in both Well Analysis and Simulation tabs).
- **Contents**: list of facies, each with a name, type (sedimentological / petrophysical / environmental), and criteria (name, min range, max range).

### Accumulation Model

- **Format**: JSON (`.json`)
- **Load/Save**: via the accumulation model editor in the Simulation tab (Step 1).
- **Contents**: list of elements, each with a model type (Gaussian or EnvironmentOptimum), accumulation rate, and optionally reduction curves.

### Reduction Curves

Reduction curves for EnvironmentOptimum elements can be loaded from:

- **JSON** (`.json`): contains a `curve` object with `xAxisName` and a `data` array of `{x, y}` points.
- **CSV** (`.csv`): first column is the X-axis (environmental factor value), subsequent columns are Y-axis values (reduction coefficients). Each column beyond the first creates a separate curve condition.

### Eustatic Curve

- **Format**: JSON (`.json`) or CSV (`.csv`)
- **Load**: via the eustatic curve editor in the Simulation tab (Step 2).
- **Contents**: age-value pairs defining the eustatic sea-level curve.

### Subsidence Curve

- **Format**: JSON (`.json`) or CSV (`.csv`)
- **Load**: via the subsidence curve editor in the Realization Data panel (Step 4).
- **Contents**: age-value pairs defining the subsidence history. Can represent either cumulative subsidence or subsidence rate, as selected by the Subsidence Type dropdown.

### Depositional Environment Conditions

Two file types depending on the mode:

- **Global mode** -- JSON file containing the condition models (Constant, Uniform, Triangular, Gaussian, or Curve).
- **Environments mode** -- JSON file containing the full DE simulation configuration: environments with their properties, conditions, weights, and DE simulator parameters.

### Simulation File

- **Format**: JSON (`.json`)
- **Load/Save**: via the top-level controls in the Simulation tab.
- **Contents**: bundles all simulation inputs into a single file -- accumulation model, eustatic curve, depositional environment model, realization data, and simulator parameters.
- This is the most convenient way to save and restore a complete simulation setup.

## Export Outputs

After running an accommodation computation (Well Analysis tab), the following exports are available:

| Export | Format | Description |
|--------|--------|-------------|
| Export Figure | PNG | Well analysis plot for the selected well |
| Export Water Depth | CSV | Water depth uncertainty curve |
| Export Accommodation | CSV | Accommodation uncertainty curve |
| Export WD/Thickness | CSV | Water-depth/thickness ratio curve |
| Export Figure (Comparison) | PNG | Multi-well comparison plot |

These CSV files contain the pyWellSFM uncertainty curve format (with min, mean, and max columns).
