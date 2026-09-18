import json
import os
from copy import deepcopy
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).parent.parent


def dispatch(
    prices_electricity_day,
    generation_pv_day,
    grid_capacity,
    bess_rated_power,
    bess_rated_capacity_true,
    bess_efficiency,
):

    # Pair each element with its index, and sort by the value (x[1])
    sorted_pairs = sorted(enumerate(prices_electricity_day), key=lambda x: x[1])
    # print("Sorted (index, value) pairs:", sorted_pairs)
    # Output: [(1, 10), (3, 20), (2, 30), (0, 40)]

    # get first 12 elements for charging, rest for discharging
    elements_charging = sorted_pairs[:12]
    elements_discharging = sorted_pairs[12:]
    elements_discharging.reverse()

    # charging routine
    # -------------------------

    # charge during low prices until storage is full
    total_energy_charged_MWh = 0
    power_bess_charge_MW = np.zeros(24)

    # loop through low prices
    for index, (index_original, price) in enumerate(elements_charging):
        if total_energy_charged_MWh >= bess_rated_capacity_true:
            break

        # extract generation
        generation = generation_pv_day[index_original]

        # calculate max based on grid capacity
        power_charge_max_MW = grid_capacity + generation

        # power cannot be higher than rated power
        power_charge_max_MW = min(power_charge_max_MW, bess_rated_power)

        # next energy cannot be higher than total energy
        power_charge_max_MW = min(
            power_charge_max_MW, (bess_rated_capacity_true - total_energy_charged_MWh)
        )

        # update energy
        total_energy_charged_MWh += power_charge_max_MW * bess_efficiency

        # assign charging power (-)
        power_bess_charge_MW[index_original] = -power_charge_max_MW
        # print("charging", index, index_original, price, generation, -power_charge_max_MW)

    # discharging routine
    # -----------------------------

    # discharge until storage is empty
    total_energy_discharged_MWh = 0
    power_bess_discharge_MW = np.zeros(24)

    for index, (index_original, price) in enumerate(elements_discharging):
        if total_energy_discharged_MWh >= bess_rated_capacity_true:
            break

        # extract generation
        generation = generation_pv_day[index_original]

        # calculate max based on grid capacity
        power_discharge_max_MW = (grid_capacity - generation) / bess_efficiency

        # power cannot be higher than rated power
        power_discharge_max_MW = min(power_discharge_max_MW, bess_rated_power)

        # next energy cannot be higher than total energy
        power_discharge_max_MW = min(
            power_discharge_max_MW,
            (bess_rated_capacity_true - total_energy_discharged_MWh),
        )

        # update energy
        total_energy_discharged_MWh += power_discharge_max_MW

        # assign discharging power (+)
        power_bess_discharge_MW[index_original] = power_discharge_max_MW
        # print("discharging", index, index_original, price, generation, power_discharge_max_MW)

    return power_bess_charge_MW, power_bess_discharge_MW


def simulate_year(
    bess_rated_energy_MWh, bess_rated_power_MW, df_prices_electricity, df_pv_generation
):

    # dataframe
    df_results = pd.DataFrame(
        index=df_pv_generation.index,
        data={
            "generation_pv_MW": df_pv_generation["power_MW"],
            "prices_electricity_euro_per_MWh": df_prices_electricity[
                "price_euro_per_MWh"
            ],
            "power_bess_net_discharge_raw_MW": None,
            "power_bess_net_discharge_MW": None,
            "battery_energy_MWh": None,
            "power_grid_net_sold_MW": None,
        },
    )

    # constant values
    bess_rated_efficiency = 0.75
    grid_rated_power_MW = 8

    # calculate battery operating values
    bess_rated_energy_MWh_true = bess_rated_energy_MWh / 2
    bess_rated_efficiency_true = bess_rated_efficiency / 2

    # track battery state
    state_battery_energy_kWh = bess_rated_energy_MWh_true

    # simulate one day at a time
    for i in range(365):
        i_start = i * 24
        i_end = (i + 1) * 24

        prices_electricity_day = df_results["prices_electricity_euro_per_MWh"].values[
            i_start:i_end
        ]
        generation_pv_day = df_results["generation_pv_MW"].values[i_start:i_end]

        # dispatch
        power_bess_charge_MW, power_bess_discharge_MW = dispatch(
            prices_electricity_day,
            generation_pv_day,
            grid_rated_power_MW,
            bess_rated_power_MW,
            bess_rated_energy_MWh_true,
            bess_rated_efficiency_true,
        )

        # calculate net balance
        for j in range(24):
            index = df_results.index[i * 24 + j]

            # update battery state
            power_bess_net_discharge_MW_raw = (
                power_bess_charge_MW[j] + power_bess_discharge_MW[j]
            )
            power_bess_net_discharge_MW = (
                power_bess_charge_MW[j]
                + power_bess_discharge_MW[j] * bess_rated_efficiency_true
            )
            state_battery_energy_kWh -= (
                power_bess_charge_MW[j] * bess_rated_efficiency_true
                + power_bess_discharge_MW[j]
            )
            power_sold_net_MW = generation_pv_day[j] + power_bess_net_discharge_MW

            assert power_sold_net_MW <= grid_rated_power_MW
            assert -power_sold_net_MW <= grid_rated_power_MW

            df_results.at[index, "power_bess_net_discharge_raw_MW"] = (
                power_bess_net_discharge_MW_raw
            )
            df_results.at[index, "power_bess_net_discharge_MW"] = (
                power_bess_net_discharge_MW
            )
            df_results.at[index, "battery_energy_MWh"] = state_battery_energy_kWh
            df_results.at[index, "power_grid_net_sold_MW"] = power_sold_net_MW

        print(f"DONE {i}", flush=True)

    return df_results


def plot_operation(df):

    fig, axes = plt.subplots(3, 1, figsize=(20, 18))

    # grid signals
    df[
        [
            "generation_pv_MW",
            "power_bess_net_discharge_MW",
            "power_grid_net_sold_MW",
        ]
    ].plot(ax=axes[0], legend=True, drawstyle="steps-post", marker=".")

    # energy storage
    df[
        [
            "battery_energy_MWh",
        ]
    ].plot(ax=axes[1], legend=True, drawstyle="steps-post", marker=".")

    # energy cost
    df[
        [
            "prices_electricity_euro_per_MWh",
        ]
    ].plot(ax=axes[2], legend=True, drawstyle="steps-post", marker=".")

    return fig, axes


def postprocess(df, bess_rated_energy_MWh, bess_rated_power_MW):

    # aggregated metrics
    # --------------------
    total_energy_pv_MWh = df["generation_pv_MW"].sum()
    total_energy_sold_net_MWh = df["power_grid_net_sold_MW"].sum()
    total_energy_discharged_net_MWh = df["power_bess_net_discharge_MW"].sum()

    # economics
    # ------------------

    # calculate total capital cost
    cost_bess_capex_per_MWh = 30
    cost_bess_capex_per_MW = 500000

    # total cost
    bess_total_capex_euro = (
        bess_rated_energy_MWh * cost_bess_capex_per_MWh
        + bess_rated_power_MW * cost_bess_capex_per_MW
    )

    # annualize
    annualized_bess_total_capex_euro = bess_total_capex_euro * 0

    # calculate total operating cost
    cost_bess_oem_fixed_per_MWh = 1
    cost_bess_oem_variable_per_MWh_discharged = 2
    total_energy_discharged_MWh = (
        df["power_bess_net_discharge_raw_MW"].clip(lower=0).sum()
    )

    total_cost_oem = (
        bess_rated_energy_MWh * cost_bess_oem_fixed_per_MWh
        + total_energy_discharged_MWh * cost_bess_oem_variable_per_MWh_discharged
    )

    # calculate total revenue
    net_revenue = df["power_grid_net_sold_MW"] * df["prices_electricity_euro_per_MWh"]
    total_revenue = net_revenue.sum()

    # profit
    net_profit = total_revenue - annualized_bess_total_capex_euro - total_cost_oem

    metrics = {
        "pv_total_energy_MWh": total_energy_pv_MWh,
        "grid_total_energy_sold_net_MWh": total_energy_sold_net_MWh,
        "bess_total_energy_discharged_net_MWh": total_energy_discharged_net_MWh,
        "bess_capex_total": bess_total_capex_euro,
        "bess_capex_annualized": annualized_bess_total_capex_euro,
        "bess_opex": total_cost_oem,
        "revenue": total_revenue,
        "profit": net_profit,
    }

    return metrics


def main(config):

    # extract
    output_directory = Path(config["output_directory"])
    os.makedirs(output_directory, exist_ok=True)

    bess_rated_power_MW = config["bess_power_MW"]
    bess_rated_energy_MWh = config["bess_energy_MWh"]

    # load data
    df_prices_electricity = pd.read_csv(
        ROOT / "prices.csv", index_col="index", parse_dates=True
    )
    df_pv_generation = pd.read_csv(ROOT / "pv.csv", index_col="index", parse_dates=True)

    # simulate one year of operation
    df_results = simulate_year(
        bess_rated_energy_MWh,
        bess_rated_power_MW,
        df_prices_electricity,
        df_pv_generation,
    )
    df_results.to_csv(output_directory / "timeseries.csv")

    # plot operation
    df_plot = df_results.iloc[:24]
    fig, axes = plot_operation(df_plot)
    fig.savefig(output_directory / "timeseries.png")

    # postprocess timeseries
    metrics = postprocess(df_results, bess_rated_energy_MWh, bess_rated_power_MW)

    summary = deepcopy(config)
    summary.update(metrics)
    summary["output_directory"] = str(output_directory)

    with open(output_directory / "summary.json", "w") as f:
        json.dump(summary, f)



if __name__ == "__main__":
    config = {
        "output_directory": ROOT / "results" / "000",
        "bess_power_MW": 4,
        "bess_energy_MWh": 16,
    }

    main(config)
