# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

pyWellSFMUI is a web-based UI for the pyWellSFM stratigraphic forward modeling simulator, built with Panel (param.Parameterized) and Plotly. It wraps the pyWellSFM library (located at ../pyWellSFM) to let users create/edit/load/save simulation inputs, run simulations, and visualize results. Deployable on HuggingFace Spaces.

## Commands

```bash
# Install (pyWellSFM must be installed first from sibling directory)
pip install -e ../pyWellSFM
pip install -e ".[dev]"

# Run the app
panel serve src/pywellsfmui/app.py

# Run all tests
pytest

# Run a single test
pytest tests/test_actions.py
pytest tests/test_actions.py::test_load_facies_model -v
```

## Architecture

The app follows a unidirectional data flow pattern:

```
UI Widgets (views/) --> Actions (state/actions.py) --> AppState (state/app_state.py)
                                                            |
                                                    param.depends (reactive)
                                                            |
                                                      Views update
```

**Key rule: UI widgets never modify AppState directly.** They call `Actions` methods, which validate inputs, execute pyWellSFM logic, and update `AppState`.

### Core layers

- **`state/app_state.py`** — Central `param.Parameterized` class. Single source of truth for all UI data (facies model, wells, simulation inputs/outputs).
- **`state/actions.py`** — Command layer between UI and state. All state mutations flow through here. Also the future API surface for LLM integration.
- **`state/io_manager.py`** — Wraps pyWellSFM IO functions (JSON load/save). Single point of contact with the filesystem. Used internally by Actions.
- **`views/`** — Three tab views (`WellAnalysisView`, `SimulationView`, `VisualizationView`), each a `param.Parameterized` class receiving `state` and `actions` via constructor. Views read state via `param.depends` and trigger actions via callbacks.
- **`components/`** — Reusable editor widgets (facies, curve, accumulation, etc.) — planned, not yet implemented.
- **`app.py`** — Entry point. Assembles the three tabs into a `pn.Tabs` layout.

### Dependencies on pyWellSFM

The UI depends heavily on pyWellSFM's data model (`FaciesModel`, `Well`, `AccumulationModel`, `Curve`, `DepositionalEnvironmentModel`, `RealizationData`, `FSSimulatorParameters`, `Scenario`) and its IO functions. Plot functions also live in pyWellSFM, not in this repo.

## Design spec

The full design specification is at `docs/superpowers/specs/2026-06-26-pywellsfmui-design.md`. Consult it for tab details, data flow diagrams, and planned features.
