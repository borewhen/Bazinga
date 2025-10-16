import streamlit as st
import pandas as pd
import numpy as np
from models import (LNGMonth, LNGDestination, LNGBuyer, SELL_POSITION, SHIPMENT_VOLUME, TOTAL_TERMINAL_COST,
    ROUTE_FREIGHT_MULT, BOR, BERTHING_COST, UTILISATION_RATES, RESERVATION_RATE_PER_MMBTU, TERMINAL_TARIFF_USD)

st.set_page_config(page_title="Atlantic LNG Optimiser (Mock)", layout="wide")

def init_state():
    ss = st.session_state
    ss.setdefault("months", ["Jan-2026","Feb-2026","Mar-2026","Apr-2026","May-2026","Jun-2026"])
    ss.setdefault("cargo_mmbtu", 3_800_000)
    ss.setdefault("hh_plus", 2.5)
    ss.setdefault("cancel_tolling", 1.5)
    ss.setdefault("slng_daily_cap", 1_400_000)
    ss.setdefault("slng_tariff_usd", 0.20)
    ss.setdefault("brent_usd", 80.0)
    ss.setdefault("jkm_by_month", {m: 12.0 for m in ss["months"]})
    ss.setdefault("hh_by_month",  {m: 3.8  for m in ss["months"]})
    ss.setdefault("route", "Panama")
    ss.setdefault("cold_snap", False)
    ss.setdefault("slng_outage_pct", 0.0)
    ss.setdefault("panama_delay_days", 0)
    ss.setdefault("latest_result", None)

init_state()

DAYS_IN_MONTH = {"Jan-2026":31,"Feb-2026":28,"Mar-2026":31,"Apr-2026":30,"May-2026":31,"Jun-2026":30}

# DATACLASSES HERE
def make_month(month_name, hh, brent_mmbtu, jkm, blng3g, dests):
    freight_cost = {k: blng3g * d.voyage_days for k, d in dests.items()}
    final_cost = {
        k: hh + ((TOTAL_TERMINAL_COST + v) / SHIPMENT_VOLUME)
        for k, v in freight_cost.items()
    }
    return LNGMonth(
        month=month_name,
        cost_usd_hh_mmbtu=hh,
        price_usd_brent_mmbtu=brent_mmbtu,
        price_usd_jkm_mmbtu=jkm,
        BLNG3g=blng3g,
        freight_cost=freight_cost,
        final_cost_usd_mmbtu=final_cost,
    )

DESTS = {
    "SG": LNGDestination(name="SG", voyage_days=48.91125),
    "JP": LNGDestination(name="JP", voyage_days=42.42083333),
    "South CN": LNGDestination(name="South CN", voyage_days=51.79375),
    "CN": LNGDestination(name="CN", voyage_days=53.08375),
}

month_jan = make_month("Jan-2026", 6.665, 21.86775512, 11.64,   52691.62, DESTS)
month_feb = make_month("Feb-2026", 6.464, 20.81119523, 11.61,   56445.97, DESTS)
month_mar = make_month("Mar-2026", 6.107, 20.06360325, 11.345,  60200.31, DESTS)
month_apr = make_month("Apr-2026", 5.973, 18.79462793, 10.91,   64081.92, DESTS)
month_may = make_month("May-2026", 6.006, 17.77944768, 10.835,  67963.53, DESTS)
month_jun = make_month("Jun-2026", 6.169, 19.70773843, 10.93,   71845.14, DESTS)

MONTHS = [month_jan, month_feb, month_mar, month_apr, month_may, month_jun]

MONTH_BY_NAME = {
    "Jan-2026": month_jan, "Feb-2026": month_feb, "Mar-2026": month_mar,
    "Apr-2026": month_apr, "May-2026": month_may, "Jun-2026": month_jun,
}

def price_from_jkm(nf: float) -> dict[str, float]:
    return {m: mo.price_usd_jkm_mmbtu + nf for m, mo in MONTH_BY_NAME.items()}

buyer_Ironman = LNGBuyer(
    name="Iron Man Pte Ltd", 
    country="SG",
    profile="Bunker Supplier", 
    credit_rating="A", 
    negotiation_factor= 4.0, 
    price=price_from_jkm(4.0))

buyer_Thor = LNGBuyer(
    name="Thor Pte Ltd", 
    country="SG",
    profile="Power Utility Company", 
    credit_rating="AA", 
    negotiation_factor= -7.5, 
    price=price_from_jkm(-7.5))

buyer_Vision = LNGBuyer(
    name="Vision Pte Ltd", 
    country="SG",
    profile="Trader", 
    credit_rating="BB", 
    negotiation_factor= -1.5, 
    price=price_from_jkm(-1.5))

buyer_Loki = LNGBuyer(
    name="Loki Pte Ltd", 
    country="SG",
    profile="Trader", 
    credit_rating="CCC", 
    negotiation_factor= -1.5, 
    price=price_from_jkm(-1.5))

buyer_Hawkeye = LNGBuyer(
    name="Hawk Eye Pte Ltd", 
    country="JP",
    profile="Trader", 
    credit_rating="AA", 
    negotiation_factor= -7.5, 
    price=price_from_jkm(-7.5))

buyer_Ultron = LNGBuyer(
    name="Ultron Pte Ltd", 
    country="JP",
    profile="Trader", 
    credit_rating="B", 
    negotiation_factor= 0.0, 
    price=price_from_jkm(0.0))

buyer_Quicksilver = LNGBuyer(
    name="Quicksilver Pte Ltd", 
    country="JP",
    profile="Trader", 
    credit_rating="A", 
    negotiation_factor= -7.5, 
    price=price_from_jkm(-7.5))

buyer_Hulk = LNGBuyer(
    name="Hulk Pte Ltd", 
    country="CN",
    profile="Trader", 
    credit_rating="BB", 
    negotiation_factor= -1.5, 
    price=price_from_jkm(-1.5))

BUYERS = [buyer_Ironman, buyer_Thor, buyer_Vision, buyer_Loki, buyer_Hawkeye, buyer_Ultron, buyer_Quicksilver, buyer_Hulk]

# -------------------------------------------------
# Compute Profitability
# -------------------------------------------------
def compute_profit_table():
    rows = []
    for mo in MONTHS:
        for buyer in BUYERS:
            country = buyer.country
            buyer_price = buyer.price[mo.month]
            final_cost = mo.final_cost_usd_mmbtu[country]
            margin = buyer_price - final_cost
            profit = margin * SELL_POSITION
            expected_profit = profit * (1 - buyer.probability_of_default)
            rows.append({
                "Month": mo.month,
                "Buyer": buyer.name,
                "Country": country,
                "Buyer Price ($/MMBtu)": buyer_price,
                "Final Cost ($/MMBtu)": final_cost,
                "Margin ($/MMBtu)": margin,
                "Profit (USD)": profit,
                "Credit Rating": buyer.credit_rating,
                "Probability of Default": buyer.probability_of_default,
                "Adjusted Profit (USD)": expected_profit,
                "Profile": buyer.profile
            })
    return pd.DataFrame(rows)

# -------------------------------------------------
# Streamlit UI
# -------------------------------------------------
st.title("Atlantic LNG Optimiser — Dataclass-Driven Model")
st.caption("Optimisation based on buyer price and LNGMonth final costs.")

st.sidebar.header("Assumptions")
st.sidebar.metric("Sell Position (MMBtu)", f"{SELL_POSITION:,.0f}")
st.sidebar.metric("Shipment Volume (MMBtu)", f"{SHIPMENT_VOLUME:,.0f}")
st.sidebar.metric("Total Terminal Cost (USD)", f"{TOTAL_TERMINAL_COST:,.0f}")

# Run analysis
# Run analysis
if st.button("Compute Profit Table"):
    df = compute_profit_table()
    st.success("Credit-adjusted profit table generated successfully.")
    st.dataframe(df, use_container_width=True)

    st.subheader("Best Buyer per Month (Credit-Adjusted)")
    best_per_month = df.loc[df.groupby("Month")["Adjusted Profit (USD)"].idxmax()]

    # Ensure month order matches chronological LNGMonth list
    month_order = [m.month for m in MONTHS]  # e.g. ["Jan-2026", "Feb-2026", ...]
    best_per_month["Month"] = pd.Categorical(best_per_month["Month"], categories=month_order, ordered=True)
    best_per_month = best_per_month.sort_values("Month").reset_index(drop=True)

    st.dataframe(
        best_per_month[[
            "Month", "Buyer", "Country", "Credit Rating",
            "Probability of Default", "Adjusted Profit (USD)"
        ]]
    )

    total_best_profit = best_per_month["Adjusted Profit (USD)"].sum()
    st.metric("Total Adjusted Profit (USD)", f"{total_best_profit:,.0f}")

    st.subheader("Adjusted Profit by Buyer")
    st.bar_chart(df.groupby(["Buyer"])["Adjusted Profit (USD)"].sum().sort_values(ascending=False))
else:
    st.info("Click **Compute Profit Table** to run the analysis.")




# def delivered_fraction(distance_nm):
#     return max(0.0, 1.0 - (distance_nm/1000.0)*BOR)

# def freight_usd_per_mmbtu(distance_nm, base_rate=0.12, route="Panama"):
#     return base_rate * ROUTE_FREIGHT_MULT.get(route, 1.0) * (distance_nm/1000.0)

# def purchase_price(month, hh_by_month, hh_plus):
#     return hh_by_month.get(month, 3.8) + hh_plus

# def sell_price_sg(month, brent_usd, slng_tariff_usd):
#     base = 0.13 * brent_usd
#     return base + ((3.0+7.5)/2.0) + slng_tariff_usd

# def sell_price_jp(month, jkm_by_month, cold_snap=False):
#     jkm = jkm_by_month.get(month, 12.0)
#     bump = 2.0 if cold_snap else 0.0
#     return jkm + ((0.5+1.2)/2.0) + 0.10 + bump

# def sell_price_cn(month, jkm_by_month, cold_snap=False):
#     jkm = jkm_by_month.get(month, 12.0)
#     bump = 1.0 if cold_snap else 0.0
#     return jkm + ((2.0+3.5)/2.0) + 0.10 + bump

# def month_unit_econ(month, params):
#     fob = purchase_price(month, params["hh_by_month"], params["hh_plus"])
#     rows = []
#     for dest in ["SG","JP","CN"]:
#         dist = DIST_NM[dest]
#         df = delivered_fraction(dist)
#         fr = freight_usd_per_mmbtu(dist, route=params["route"])
#         if dest == "SG":
#             sell = sell_price_sg(month, params["brent_usd"], params["slng_tariff_usd"])
#             tariff = params["slng_tariff_usd"]
#         elif dest == "JP":
#             sell = sell_price_jp(month, params["jkm_by_month"], cold_snap=params["cold_snap"])
#             tariff = 0.0
#         else:
#             sell = sell_price_cn(month, params["jkm_by_month"], cold_snap=params["cold_snap"])
#             tariff = 0.0
#         unit_profit = sell*df - (fob + fr + tariff)
#         rows.append({"month": month, "dest": dest, "delivered_frac": df, "fob": fob, "freight": fr,
#                      "tariff": tariff, "sell": sell, "unit_profit": unit_profit})
#     return pd.DataFrame(rows)

# def mock_optimise(params):
#     MONTHS = params["months"]
#     cap_sg = (1.0 - params["slng_outage_pct"]) * params["slng_daily_cap"]
#     results = []
#     total_profit = 0.0

#     for mo in MONTHS:
#         econ = month_unit_econ(mo, params).sort_values("unit_profit", ascending=False).reset_index(drop=True)
#         best = econ.iloc[0]
#         volume = params["cargo_mmbtu"]
#         if best["unit_profit"] <= 0:
#             pnl = - params["cancel_tolling"] * volume
#             results.append({"month": mo, "dest": "CANCEL", "alloc_mmbtu": 0.0, "unit_profit": -params["cancel_tolling"],
#                             "profit_usd": pnl})
#             total_profit += pnl
#         else:
#             if best["dest"] == "SG":
#                 max_sg = cap_sg * DAYS_IN_MONTH[mo]
#                 alloc = min(volume, max_sg)
#                 pnl = alloc * best["unit_profit"]
#                 results.append({"month": mo, "dest": "SG", "alloc_mmbtu": alloc, "unit_profit": best["unit_profit"],
#                                 "profit_usd": pnl})
#                 total_profit += pnl
#                 remain = volume - alloc
#                 if remain > 0:
#                     nxt = econ.iloc[1]
#                     if nxt["unit_profit"] > 0:
#                         pnl2 = remain * nxt["unit_profit"]
#                         results.append({"month": mo, "dest": nxt["dest"], "alloc_mmbtu": remain,
#                                         "unit_profit": nxt["unit_profit"], "profit_usd": pnl2})
#                         total_profit += pnl2
#                     else:
#                         pnl2 = - params["cancel_tolling"] * remain
#                         results.append({"month": mo, "dest": "CANCEL", "alloc_mmbtu": 0.0,
#                                         "unit_profit": -params["cancel_tolling"], "profit_usd": pnl2})
#                         total_profit += pnl2
#             else:
#                 pnl = volume * best["unit_profit"]
#                 results.append({"month": mo, "dest": best["dest"], "alloc_mmbtu": volume,
#                                 "unit_profit": best["unit_profit"], "profit_usd": pnl})
#                 total_profit += pnl

#     df = pd.DataFrame(results)
#     monthly_pnl = df.groupby("month")["profit_usd"].sum().reindex(MONTHS, fill_value=0.0)
#     return {"details": df, "monthly_pnl": monthly_pnl, "total_profit": float(total_profit)}

# st.title("Atlantic LNG Optimiser — Mock UI")

# with st.sidebar:
#     st.header("Inputs")
#     st.number_input("Cargo size (MMBtu)", min_value=1_000_000, max_value=6_000_000,
#                     value=st.session_state["cargo_mmbtu"], key="cargo_mmbtu")
#     st.number_input("HH adder (+$/MMBtu)", value=st.session_state["hh_plus"], step=0.1, key="hh_plus")
#     st.number_input("Cancel tolling ($/MMBtu)", value=st.session_state["cancel_tolling"], step=0.1, key="cancel_tolling")
#     st.number_input("SLNG daily cap (MMBtu/day)", value=st.session_state["slng_daily_cap"], step=50_000, key="slng_daily_cap")
#     st.number_input("SLNG tariff (USD/MMBtu)", value=st.session_state["slng_tariff_usd"], step=0.05, key="slng_tariff_usd")
#     st.number_input("Brent (USD/bbl)", value=st.session_state["brent_usd"], step=1.0, key="brent_usd")
#     st.selectbox("Route", options=list(ROUTE_FREIGHT_MULT.keys()), key="route")
#     st.checkbox("Cold Snap (JKM bump)", key="cold_snap")
#     st.slider("SLNG outage reduction", 0.0, 1.0, value=st.session_state["slng_outage_pct"], key="slng_outage_pct")
#     st.number_input("Panama delay (days)", min_value=0, max_value=60, value=st.session_state["panama_delay_days"], key="panama_delay_days")

#     st.markdown("---")
#     st.subheader("Forward Curves (mock)")
#     cols = st.columns(2)
#     with cols[0]:
#         for m in MONTHS:
#             st.session_state["jkm_by_month"][m] = st.number_input(f"JKM {m} (USD/MMBtu)", value=st.session_state["jkm_by_month"][m], key=f"jkm_{m}")
#     with cols[1]:
#         for m in MONTHS:
#             st.session_state["hh_by_month"][m] = st.number_input(f"HH {m} (USD/MMBtu)", value=st.session_state["hh_by_month"][m], key=f"hh_{m}")

# run = st.button("Run mock optimisation")

# if run:
#     params = {
#         "months": MONTHS,
#         "cargo_mmbtu": st.session_state["cargo_mmbtu"],
#         "hh_plus": st.session_state["hh_plus"],
#         "cancel_tolling": st.session_state["cancel_tolling"],
#         "slng_daily_cap": st.session_state["slng_daily_cap"],
#         "slng_tariff_usd": st.session_state["slng_tariff_usd"],
#         "brent_usd": st.session_state["brent_usd"],
#         "jkm_by_month": st.session_state["jkm_by_month"],
#         "hh_by_month": st.session_state["hh_by_month"],
#         "route": st.session_state["route"],
#         "cold_snap": st.session_state["cold_snap"],
#         "slng_outage_pct": st.session_state["slng_outage_pct"],
#         "panama_delay_days": st.session_state["panama_delay_days"],
#     }
#     res = mock_optimise(params)
#     st.session_state["latest_result"] = res

# res = st.session_state.get("latest_result")
# if res:
#     left, right = st.columns([1.2,1])
#     with left:
#         st.subheader("Per-month allocations")
#         st.dataframe(res["details"].pivot_table(index="month", columns="dest", values="alloc_mmbtu", aggfunc="sum").fillna(0.0))
#         st.subheader("Monthly PnL")
#         st.bar_chart(res["monthly_pnl"])
#     with right:
#         st.metric("Total Profit (USD)", f"{res['total_profit']:,.0f}")
#         st.caption("Greedy mock optimiser — for UI prototyping. Hook up your MILP later.")
# else:
#     st.info("Set inputs and click **Run mock optimisation**.")
