---
title: pyWellSFMUI
emoji: 🌊
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
suggested_hardware: cpu-basic
---

[![CI](https://github.com/martin-lemay/pyWellSFMUI/actions/workflows/ci.yml/badge.svg)](https://github.com/martin-lemay/pyWellSFMUI/actions)
[![docs](https://readthedocs.org/projects/pywellsfmui/badge/?version=latest)](https://pywellsfmui.readthedocs.io/en/latest/)

# pyWellSFMUI

Web-based interface for the [pyWellSFM](https://github.com/martin-lemay/pyWellSFM) stratigraphic forward modeling simulator. Built with [Panel](https://panel.holoviz.org/) and [Plotly](https://plotly.com/python/), it lets you create, edit, and run 1-D stratigraphic simulations entirely in your browser.

The app is organized into three main sections:

- **Well Data Analysis** -- Load wells, define a facies model, compute accommodation curves, and compare results across wells.
- **Simulation** -- Build a complete simulation scenario (accumulation model, eustatic curve, depositional environments, realization data) and run the forward model.
- **Visualization** -- Inspect simulation outputs: elevation profiles, production rate plots, and well log comparisons.

A full documentation can be found [here](https://pywellsfmui.readthedocs.io/en/latest/).

## Quickstart

Install from GitHub:

```bash
pip install git+https://github.com/martin-lemay/pyWellSFM.git
pip install git+https://github.com/martin-lemay/pyWellSFMUI.git
```

Run the app:

```bash
panel serve src/pywellsfmui/app.py
```

## Development

```bash
git clone https://github.com/martin-lemay/pyWellSFMUI.git
cd pyWellSFMUI
pip install -e ../pyWellSFM
pip install -e ".[dev]"
```

Run tests:

```bash
pytest
```

## License

Apache License 2.0 -- see [LICENSE](LICENSE) for details.
