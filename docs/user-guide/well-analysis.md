# Well Data Analysis

The **Well Data Analysis** section is the first tab in the sidebar. It allows you to load well data, define a facies model, compute accommodation curves, and compare results across wells.

## Step 1 -- Facies Model

The facies model defines the sedimentary, petrophysical, or environmental facies used to interpret well logs.

### Creating or Loading a Model

- Click **New Model** to create an empty facies model.
- Use the **Load Facies Model** file input to load a facies model from a `.json` file.
- Click **Save Facies Model** to download the current model as JSON.

### Editing Facies

The editor uses a master-detail layout:

- **Left table -- Facies List**: Lists all facies in the model. Each facies has a *Name* and a *Type* (sedimentological, petrophysical, or environmental).
  - To **add** a facies: double-click the italic "New Facies..." placeholder row, type a name, then select a type. The facies is created once both fields are filled.
  - To **remove** a facies: select it and click the **Remove** button.
  - Facies name and type are read-only after creation.

- **Right table -- Criteria For Selected Facies**: Shows the criteria (value ranges) for the selected facies.
  - To **add** a criterion: double-click the "New Criterion..." row and provide a name, min, and max value.
  - To **edit** a criterion's range: double-click the Min or Max cell and change the value. Criterion names are read-only.
  - To **remove** a criterion: select it and click **Remove**.

### Status Indicator

A colored status indicator in the top-right corner shows:

- *No facies model* (red) -- No model is loaded.
- *Facies model: N facies, missing criteria* (orange) -- Some facies have no criteria defined.
- *Facies model: N valid facies* (green) -- All facies have at least one criterion.

## Step 2 -- Well Import

Upload well data files to build the well list.

- Use the **Load Well** file input to upload a `.json` or `.las` file. Each file adds one well to the list.
- For each well, select the **facies log** (discrete log) to use for accommodation calculation.
- A **Computed** checkbox indicates whether accommodation has been calculated for that well.
- Click **Remove** to delete a well from the list.

## Step 3 -- Accommodation Computation

Once you have loaded at least one well and a facies model, the status shows "Ready" and the **Compute Accommodation** button becomes active.

Click the button to compute accommodation curves for all loaded wells. The button label changes to "Computing..." during the calculation.

## Results

After computation, two result sections appear.

### Individual Well Analysis

- Select a well from the **Well** dropdown to display its analysis plot.
- The plot shows the well's facies log, water depth, accommodation, and WD/thickness ratio tracks.

**Export buttons** (visible after computation):

| Button | Output |
|--------|--------|
| Export Figure | PNG image of the current well plot |
| Export Water Depth | CSV file of the water depth curve |
| Export Accommodation | CSV file of the accommodation curve |
| Export WD/Thickness | CSV file of the WD/thickness ratio curve |

### Well Comparison

- Select a **Track** to compare across all wells: *Water Depth*, *Accommodation*, or *WD/Thickness Ratio*.
- The comparison plot overlays the selected track for all computed wells.
- Click **Export Figure** to download the comparison plot as PNG.
