from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from copy import deepcopy
import json

from bess.simulate import main as main_simulate

ROOT = Path(__file__).parent.parent

print(ROOT)
exit

if __name__ == "__main__":

    config =  {
        "output_directory": ROOT / "results" / "000",
        "bess_power_MW": 4,
        "bess_energy_MWh": 16
    }

    main_simulate(config)