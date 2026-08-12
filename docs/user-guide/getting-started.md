# Getting Started

## Launching the App

Install the dependencies and start the Panel server:

```bash
pip install -e ../pyWellSFM
pip install -e .
panel serve src/pywellsfmui/app.py
```

Open the URL printed in the terminal (typically `http://localhost:5006/app`).

## Interface Overview

The interface is divided into four areas:

- **Sidebar** (left) -- Navigation buttons to switch between the three main sections: *Well Data Analysis*, *Simulation*, and *Visualization*.
- **Header bar** (top) -- Status badges showing the current state of your session: whether a facies model is loaded, how many wells are loaded, and whether a simulation has been completed.
- **Main area** (center) -- The active section's content.
- **Log panel** (bottom) -- A collapsible panel showing application messages. It auto-expands on warnings or errors. You can filter messages by level (Debug, Info, Warning, Error) and clear the log.

## Typical Workflow

A complete stratigraphic forward modeling session follows these steps:

### 1. Well Data Analysis (optional)

If you have real well data and want to compute accommodation curves before running a simulation:

1. Load or create a **facies model** (Step 1).
2. **Import wells** from JSON or LAS files (Step 2).
3. Click **Compute Accommodation** (Step 3).
4. Inspect individual well analysis plots and well comparison plots.
5. Export results (figures, water depth, accommodation, WD/thickness ratio) as needed.

### 2. Simulation

1. Define an **accumulation model** with sedimentary elements and their production rates (Step 1).
2. Optionally set an **eustatic curve** (Step 2).
3. Configure **depositional environments and conditions** -- either globally or per-environment (Step 3).
4. Add wells and configure **realization data**: initial bathymetry, initial environment, markers, and subsidence curves (Step 4).
5. Optionally load or adjust the **facies model** (Step 5) and **simulator parameters**.
6. Click **Run Simulation**. The app automatically navigates to the Visualization section when done.

### 3. Visualization

Review the simulation outputs:

- **Results** section: elevation profiles and production rate plots for each well.
- **Wells** section: well log plots (Facies, MainElement, Environment, or any other log). Toggle markers and switch between depth and age domains.

## Saving and Loading

You can save and reload your work at any point:

- Each editor (facies model, accumulation model, depositional environments) supports loading from and saving to JSON files.
- The Simulation tab also provides a single **simulation file** that bundles all inputs together.

See {doc}`import-export` for details on supported file formats.
