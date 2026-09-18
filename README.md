# BESS-Exercise

This repository is used to conduct an example techno-economic analysis of battery energy storage system (BESS) in support of a 4MW solar photovoltaics (PV) plant located in Portugal.

## Install

This repository uses `uv` to manage the Python virtual environment and dependencies. Alternatively, `pip` may also be used.

Using `uv`:

    uv sync

Using `pip`:

    pip install . -e

Activate environment

    source .venv/Scripts/activate

## Usage

First, run this script to get the data required for the analysis:

    python bess/get_data.py

This script downloads:

* annual hourly day-ahead electricity wholesale market prices from Portugal in 2025. The API refers to Portugal's [REN database](https://datahub.ren.pt/en/api-instructions).
* annual hourly representative PV generation for a 4MW solar plant located in Algarve, Portugal, for year 2025. The software used is NLR's [PVWatts Model](https://developer.nlr.gov/docs/solar/pvwatts/v8/).

Then, run a simulation with fixed design using the `main.py` script: 
    
    python bess/main.py


Finally, run the full sensitivity analysis using the script `to do`:
