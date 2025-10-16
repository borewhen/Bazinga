import json
import pandas as pd
import streamlit as st
import plotly.express as px

from model.financials import build_unit_profit_table, pnl_from_allocation
from model.optimisation import optimise_allocation
from model.scenarios import SCENARIOS

st.set_page_config(page_title="LNG Strategy Optimiser", layout="wide")

@st.cache_resource
def load_inputs():
    ports = pd.read_csv("data/ports.csv")
    with open("data/base_inputs.json") as f:
        base_inputs = json.load(f)
    return ports, base_inputs

ports_df, base_inputs = load_inputs()
assumptions = base_inputs["assumptions"]
base_prices = base_inputs["prices_usd_per_unit"]

st.title("LNG Strategy Optimiser — Prototype")
st.caption("Allocate cargo across destinations to maximise profit under capacity and scenario constraints.")

with st.sidebar:
    st.header("Assumptions")
    supply = st.number_input("Monthly supply (cargo units)", min_value=0.0, value=float(assumptions["supply_cargo_units"]), step=1.0)
    boil = st.number_input("Boil-off rate per 1000nm", min_value=0.0, value=float(assumptions["boiloff_rate_per_1000nm"]), step=0.0005, format="%.4f")
    freight = st.number_input("Freight cost / nm / unit (USD)", min_value=0.0, value=float(assumptions["freight_cost_per_nm_per_unit"]), step=0.01)
    var_cost = st.number_input("Variable cost / unit (USD)", min_value=0.0, value=float(assumptions["variable_cost_per_unit"]), step=0.5)
    carbon = st.number_input("Carbon cost / unit (USD)", min_value=0.0, value=float(assumptions.get("carbon_cost_per_unit", 0.0)), step=0.5)
    st.divider()
    scen_name = st.selectbox("Scenario", list(SCENARIOS.keys()), index=0)

# Apply scenario
scenario = SCENARIOS[scen_name]
price_map = base_prices.copy()
for k, v in scenario["price_shocks"].items():
    price_map[k] = price_map.get(k, 0.0) + v

ports_view = ports_df.copy()
if scenario["capacity_multipliers"]:
    ports_view["monthly_capacity_cargo"] = ports_view.apply(
        lambda r: r["monthly_capacity_cargo"] * scenario["capacity_multipliers"].get(r["code"], 1.0), axis=1
    )

# Build unit profit table
assump_dict = dict(
    boiloff_rate_per_1000nm=boil,
    freight_cost_per_nm_per_unit=freight,
    variable_cost_per_unit=var_cost,
    carbon_cost_per_unit=carbon
)
unit_tbl = build_unit_profit_table(ports_view, price_map, assump_dict)

# Optimise
opt = optimise_allocation(unit_tbl, supply)
alloc = opt["allocation"]
pnl = pnl_from_allocation(unit_tbl, alloc)

col1, col2 = st.columns([1,1])
with col1:
    st.subheader("Optimal Allocation")
    alloc_df = pd.DataFrame([{"code": k, "allocation": v} for k, v in alloc.items()]).merge(unit_tbl[["code","name","unit_profit"]], on="code")
    alloc_df = alloc_df.sort_values("allocation", ascending=False)
    st.dataframe(alloc_df, use_container_width=True, hide_index=True)
    st.metric("Expected Profit (objective)", f"${opt['objective']:,.0f}")
    st.metric("Expected Delivered Units", f"{pnl['expected_delivered_units']:.2f}")
with col2:
    st.subheader("Unit Economics by Destination")
    st.dataframe(unit_tbl, use_container_width=True, hide_index=True)
    fig = px.bar(alloc_df, x="name", y="allocation", title="Allocation by Destination")
    st.plotly_chart(fig, use_container_width=True)

st.divider()
st.subheader("Prices & Capacities (after scenario)")
prices_cap_df = ports_view[["name","code","monthly_capacity_cargo"]].copy()
prices_cap_df["price_usd_per_unit"] = prices_cap_df["code"].map(price_map)
st.dataframe(prices_cap_df, use_container_width=True, hide_index=True)

st.caption("Tip: Extend this by adding multi-period flows, vessel constraints, storage decisions, and contract terms.")
