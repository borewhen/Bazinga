from __future__ import annotations
import pandas as pd
import numpy as np

def delivered_fraction(distance_nm: float, boiloff_rate_per_1000nm: float) -> float:
    "Simple linear boil-off approximation."
    loss = (distance_nm / 1000.0) * boiloff_rate_per_1000nm
    frac = max(0.0, 1.0 - loss)
    return frac

def unit_profit_for_destination(
    price_per_unit: float,
    distance_nm: float,
    handling_fee_per_unit: float,
    boiloff_rate_per_1000nm: float,
    freight_cost_per_nm_per_unit: float,
    variable_cost_per_unit: float,
    carbon_cost_per_unit: float = 0.0,
) -> float:
    """
    Returns *expected profit per loaded unit sent* to this destination.
    Delivered units are reduced by boil-off. Profit counted on delivered units.
    """
    delivered_frac = delivered_fraction(distance_nm, boiloff_rate_per_1000nm)
    revenue = price_per_unit * delivered_frac
    freight = freight_cost_per_nm_per_unit * distance_nm
    costs = variable_cost_per_unit + handling_fee_per_unit + freight + carbon_cost_per_unit
    return revenue - costs

def build_unit_profit_table(ports_df: pd.DataFrame, price_map: dict, assumptions: dict) -> pd.DataFrame:
    rows = []
    for _, r in ports_df.iterrows():
        code = r["code"]
        price = price_map.get(code, np.nan)
        up = unit_profit_for_destination(
            price_per_unit=price,
            distance_nm=float(r["distance_nm"]),
            handling_fee_per_unit=float(r["handling_fee_per_unit"]),
            boiloff_rate_per_1000nm=float(assumptions["boiloff_rate_per_1000nm"]),
            freight_cost_per_nm_per_unit=float(assumptions["freight_cost_per_nm_per_unit"]),
            variable_cost_per_unit=float(assumptions["variable_cost_per_unit"]),
            carbon_cost_per_unit=float(assumptions.get("carbon_cost_per_unit", 0.0)),
        )
        rows.append({
            "code": code,
            "name": r["name"],
            "distance_nm": r["distance_nm"],
            "monthly_capacity_cargo": r["monthly_capacity_cargo"],
            "price_per_unit": price,
            "unit_profit": up,
            "delivered_fraction": delivered_fraction(r["distance_nm"], assumptions["boiloff_rate_per_1000nm"]),
        })
    return pd.DataFrame(rows)

def pnl_from_allocation(unit_table: pd.DataFrame, allocation_map: dict[str, float]) -> dict:
    df = unit_table.set_index("code")
    pnl = 0.0
    delivered = 0.0
    for code, x in allocation_map.items():
        up = float(df.loc[code, "unit_profit"])
        df_deliv_frac = float(df.loc[code, "delivered_fraction"])
        pnl += up * x
        delivered += df_deliv_frac * x
    return {"expected_profit": pnl, "expected_delivered_units": delivered}
