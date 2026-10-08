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

Requires Python >= 3.13. Install the pinned pyWellSFM release, then the UI:

```bash
pip install -r https://raw.githubusercontent.com/martin-lemay/pyWellSFMUI/main/requirements.txt
pip install git+https://github.com/martin-lemay/pyWellSFMUI.git
```

Run the app (opens your browser; extra options are passed to `panel serve`,
e.g. `--port 5007`):

```bash
python -m pywellsfmui
```

Example input files are available in [examples/](examples/).

## Deployment

- **Hosted**: the app runs as a Docker
  [HuggingFace Space](https://huggingface.co/spaces/MartinLemay/WellSFM), built
  from the `Dockerfile` of this repository.
- **Windows desktop**: a self-contained zip is built by the `Package` GitHub
  workflow on each `v*` tag (see `build_release.py` and `launcher/`).

## Development

```bash
git clone https://github.com/martin-lemay/pyWellSFMUI.git
cd pyWellSFMUI
pip install -e ../pyWellSFM
pip install -e ".[dev]"
```

Run the app from the source tree:

```bash
panel serve src/pywellsfmui/app.py --show
```

Run tests:

```bash
pytest
```

## Citation

If you use pyWellSFMUI in your work, please cite it together with
[pyWellSFM](https://github.com/martin-lemay/pyWellSFM). Citation metadata is in
[CITATION.cff](CITATION.cff); on GitHub, use the "Cite this repository" button.
Each release is archived on Zenodo with a DOI.

## License

Apache License 2.0 -- see [LICENSE](LICENSE) for details.
