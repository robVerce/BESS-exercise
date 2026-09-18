import json
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).parent.parent


def api_request_robust(url):
    response = requests.get(url)

    # Check if the request was successful
    if response.status_code == 200:
        data = response.json()
    else:
        raise Exception(f"Error: {response.status_code}")

    return data


YEAR = 2025
DAILY_INDEX = pd.date_range(
    start=f"{YEAR}-01-01", end=f"{YEAR}-12-31", inclusive="both", freq="D"
)
HOURLY_INDEX = pd.date_range(
    start=f"{YEAR}-01-01", end=f"{YEAR + 1}-01-01", inclusive="left", freq="h"
)


def get_prices():

    def get_prices_date(date):
        """
        format YYYY-MM-DD
        """

        url = f"https://servicebus.ren.pt/datahubapi/electricity/ElectricityMarketPricesDaily?culture=en-US&date={date}"
        data = api_request_robust(url)

        # extract data for Portugal specifically (there should only be 1)
        data_pt = [d for d in data["series"] if d["name"] == "PT"]
        assert len(data_pt) == 1

        # extract time-series and validate 24-hours
        series_pt = data_pt[0]["data"]
        if len(series_pt) == 24:
            pass
        elif len(series_pt) == 23:
            series_pt.append(series_pt[-1])
        elif len(series_pt) == 25:
            series_pt.pop()

        assert len(series_pt) == 24, (date, "ERROR", len(series_pt), print(series_pt))

        return series_pt

    # TEST
    # date = "2025-03-30"
    # p = get_prices_date(date)
    # print(len(p))
    # exit()

    prices = []
    for date in DAILY_INDEX:
        p = get_prices_date(date.strftime("%Y-%m-%d"))
        prices.extend(p)
        print(f"DONE {date}", flush=True)

    # construct timeseries
    df_prices = pd.DataFrame(
        {"index": HOURLY_INDEX[: len(prices)], "price_euro_per_MWh": prices}
    )

    df_prices.to_csv(ROOT / "data" / "prices.csv", index=False)
    print("DONE prices.")

    return df_prices


def get_pv_production():
    # https://developer.nlr.gov/docs/solar/pvwatts/v8/

    # this is just a placeholder
    capacity_placeholder_kW = 100

    # true capacity
    capacity_true_MW = 4

    api_key = "AfDJht6IRXgP4beInQeWPW9w0RUtgX2IieaWGuKs"
    params = {
        "azimuth": 180,  # azimuth angle
        "system_capacity": capacity_placeholder_kW,  # system capacity (kW)
        "losses": 14.0757,  # percent losses
        "array_type": 0,  # array type (fixed open rack)
        "module_type": 0,  # standard
        "gcr": 0.4,  # ground coverage ratio
        "dc_ac_ratio": 1,  # dc-ac ratio
        "inv_eff": 96.0,  # inverter efficiency
        "tilt": 25,  # tilt
        "timeframe": "hourly",
        "lat": 37.242000,
        "lon": -8.170000,
    }

    # base url
    url = "https://developer.nlr.gov/api/pvwatts/v8.json?"

    # add
    url += f"api_key={api_key}"

    # recursively
    for key, item in params.items():
        url += f"&{key}={item}"

    resp = requests.get(url)  # , verify=certifi.where())
    data = json.loads(resp.text)

    # extract power, returned in W, convert to MW
    power_dc = (
        np.asarray(data["outputs"]["dc"])
        * 1e-3
        / capacity_placeholder_kW
        * capacity_true_MW
    )

    # assign to dataframe
    index = HOURLY_INDEX
    df_pv = pd.DataFrame(
        data={"index": index, "power_MW": power_dc},
    )

    # write
    df_pv.to_csv(ROOT / "data" / "pv.csv", index=False)
    print("DONE PV generation.")

    return df_pv


if __name__ == "__main__":
    df_prices = get_prices()
    print(len(df_prices))

    df_pv = get_pv_production()
    print(len(df_pv))
