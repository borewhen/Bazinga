from __future__ import annotations
import pulp
import pandas as pd

def optimise_allocation(unit_table: pd.DataFrame, total_supply_units: float) -> dict:
    """
    Linear program: maximise sum(unit_profit[d] * x[d]) subject to
    0 <= x[d] <= capacity[d] and sum_d x[d] <= total_supply_units
    """
    codes = unit_table["code"].tolist()
    profit = {row["code"]: float(row["unit_profit"]) for _, row in unit_table.iterrows()}
    capacity = {row["code"]: float(row["monthly_capacity_cargo"]) for _, row in unit_table.iterrows()}

    m = pulp.LpProblem("lng_allocation", pulp.LpMaximize)
    x = pulp.LpVariable.dicts("alloc", codes, lowBound=0)

    # Objective
    m += pulp.lpSum([profit[c]*x[c] for c in codes])

    # Constraints
    m += pulp.lpSum([x[c] for c in codes]) <= float(total_supply_units), "SupplyLimit"
    for c in codes:
        m += x[c] <= capacity[c], f"Cap_{c}"

    m.solve(pulp.PULP_CBC_CMD(msg=False))

    alloc = {c: float(x[c].value() or 0.0) for c in codes}
    obj = pulp.value(m.objective)
    return {"allocation": alloc, "objective": obj}
