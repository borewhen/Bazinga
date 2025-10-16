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
def compute_profit_table(buyers):
    rows = []
    for mo in MONTHS:  # MONTHS is your list of LNGMonth objects
        for buyer in buyers:
            # Guard against missing month keys in buyer.price
            buyer_price = buyer.price.get(mo.month, None)
            if buyer_price is None:
                # Skip if buyer has no quote for this month
                continue

            country = buyer.country
            final_cost = mo.final_cost_usd_mmbtu[country]  # per-MMBtu
            margin = buyer_price - final_cost              # $/MMBtu
            profit = margin * SELL_POSITION                # unadjusted USD

            # probability_of_default set in LNGBuyer.__post_init__
            pd_ = getattr(buyer, "probability_of_default", 0.0)
            adjusted_profit = profit * (1 - pd_)

            rows.append({
                "Month": mo.month,
                "Buyer": buyer.name,
                "Country": country,
                "Buyer Price ($/MMBtu)": buyer_price,
                "Final Cost ($/MMBtu)": final_cost,
                "Margin ($/MMBtu)": margin,
                "Profit (USD)": profit,
                "Credit Rating": buyer.credit_rating,
                "Probability of Default": pd_,
                "Adjusted Profit (USD)": adjusted_profit,
                "Profile": buyer.profile,
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

# Select buyers
st.sidebar.header("Buyer Availability")

select_all = st.sidebar.checkbox("Select all buyers", value=True)

active_buyers = []
for b in BUYERS:
    default_checked = select_all
    if st.sidebar.checkbox(f"{b.name} ({b.country}, {b.credit_rating})",
                           value=default_checked, key=f"buyer_{b.name}"):
        active_buyers.append(b)

# Recompute controls
st.sidebar.markdown("---")
auto_recompute = st.sidebar.toggle("Auto-recompute on changes", value=False,
                                   help="When ON, we recompute on each change.")
recompute_clicked = st.sidebar.button("Recompute now")


# Run analysis
# --- Compute-on-load + on-demand recompute ---
should_compute = False
if "df" not in st.session_state:
    should_compute = True
elif auto_recompute or recompute_clicked:
    should_compute = True

if should_compute:
    if not active_buyers:
        st.warning("No buyers selected. Please enable at least one buyer.")
        st.session_state.df = pd.DataFrame()
    else:
        st.session_state.df = compute_profit_table(active_buyers)  # <- pass buyers here
        st.success(f"Credit-adjusted profit table computed for {len(active_buyers)} active buyers.")

df = st.session_state.get("df", pd.DataFrame())

if not df.empty:
    st.dataframe(df, use_container_width=True)

    st.subheader("Best Buyer per Month (Credit-Adjusted)")
    best_per_month = df.loc[df.groupby("Month")["Adjusted Profit (USD)"].idxmax()]

    month_order = [m.month for m in MONTHS]
    best_per_month["Month"] = pd.Categorical(best_per_month["Month"], categories=month_order, ordered=True)
    best_per_month = best_per_month.sort_values("Month").reset_index(drop=True)

    st.dataframe(best_per_month[[
        "Month", "Buyer", "Country", "Credit Rating",
        "Probability of Default", "Adjusted Profit (USD)"
    ]])

    total_best_profit = best_per_month["Adjusted Profit (USD)"].sum()
    st.metric("Total Adjusted Profit (USD)", f"{total_best_profit:,.0f}")

    st.subheader("Adjusted Profit by Buyer")
    st.bar_chart(
        df.groupby(["Buyer"])["Adjusted Profit (USD)"].sum().sort_values(ascending=False)
    )