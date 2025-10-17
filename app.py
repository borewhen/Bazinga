import streamlit as st
import altair as alt
import pandas as pd
import numpy as np
from models import (LNGMonth, LNGDestination, LNGBuyer, SELL_POSITION, SHIPMENT_VOLUME, TOTAL_TERMINAL_COST,
    ROUTE_FREIGHT_MULT, BOR, BERTHING_COST, UTILISATION_RATES, RESERVATION_RATE_PER_MMBTU, TERMINAL_TARIFF_USD)

st.set_page_config(page_title="Bazingaaa!", layout="wide")

COUNTRIES = ["SG", "JP", "CN"]

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

# # --- Hardcoded Open Demand (MMBtu) ---
# OPEN_DEMAND = {
#     "SG": {"Jan-2026": 3_570_000, "Feb-2026": 8_925_000, "Mar-2026": 17_850_000,
#            "Apr-2026": 17_850_000, "May-2026": 23_205_000, "Jun-2026": 23_205_000},
#     "CN": {"Jan-2026": 29_720_000, "Feb-2026": 61_250_000, "Mar-2026": 58_650_000,
#            "Apr-2026": 131_900_000, "May-2026": 151_440_000, "Jun-2026": 166_140_000},
#     "JP": {"Jan-2026": 15_930_000, "Feb-2026": 78_625_000, "Mar-2026": 72_450_000,
#            "Apr-2026": 193_060_000, "May-2026": 170_030_000, "Jun-2026": 161_700_000},
# }

# --- MARKET DEMAND (MMBtu) per country-month (your "Assumed Country Demand") ---
MARKET_DEMAND = {
    "SG": {"Jan-2026": 35_700_000, "Feb-2026": 35_700_000, "Mar-2026": 35_700_000,
           "Apr-2026": 35_700_000, "May-2026": 35_700_000, "Jun-2026": 35_700_000},
    "CN": {"Jan-2026": 297_200_000, "Feb-2026": 245_000_000, "Mar-2026": 234_600_000,
           "Apr-2026": 263_800_000, "May-2026": 252_400_000, "Jun-2026": 276_900_000},
    "JP": {"Jan-2026": 318_600_000, "Feb-2026": 314_500_000, "Mar-2026": 289_800_000,
           "Apr-2026": 275_800_000, "May-2026": 242_900_000, "Jun-2026": 231_000_000},
}

# Helper: pivot {country:{month:val}} -> {month:{country:val}}
def _by_month_country_map(d_country_month: dict) -> dict:
    return {mo.month: {c: float(d_country_month[c][mo.month]) for c in ["SG", "JP", "CN"]} for mo in MONTHS}

MARKET_BY_MC = _by_month_country_map(MARKET_DEMAND)

# Your derived percent tables (0..1) already exist:
# OPEN_PCT_DEFAULT, BUYER_OF_OPEN_PCT_DEFAULT

def _derive_open_and_buyer_totals_from_market(market_by_mc: dict,
                                              open_pct_mc: dict,
                                              buyer_of_open_pct_mc: dict):
    """Return (open_by_mc, buyer_total_by_mc) both as {month:{country:value}}."""
    open_by_mc = {m: {} for m in market_by_mc}
    buyer_total_by_mc = {m: {} for m in market_by_mc}
    for m in market_by_mc:
        for c in ["SG", "JP", "CN"]:
            md = float(market_by_mc[m][c])
            open_ = md * float(open_pct_mc[m][c])
            buyer_total = open_ * float(buyer_of_open_pct_mc[m][c])
            open_by_mc[m][c] = open_
            buyer_total_by_mc[m][c] = buyer_total
    return open_by_mc, buyer_total_by_mc

# --- Buyer% of Open (derived earlier) as defaults; values are 0..1 ---
BUYER_OF_OPEN_PCT_DEFAULT = {
    "Jan-2026": {"SG": 1.00, "CN": 1.00, "JP": 0.05},
    "Feb-2026": {"SG": 0.50, "CN": 0.25, "JP": 0.25},
    "Mar-2026": {"SG": 0.50, "CN": 0.25, "JP": 0.25},
    "Apr-2026": {"SG": 0.50, "CN": 0.50, "JP": 0.70},
    "May-2026": {"SG": 0.50, "CN": 0.60, "JP": 0.70},
    "Jun-2026": {"SG": 0.50, "CN": 0.60, "JP": 0.70},
}

def _by_month_country(d_country_month: dict) -> dict:
    # {country:{month:val}} -> {month:{country:val}}
    return {mo.month: {c: float(d_country_month[c][mo.month]) for c in ["SG","JP","CN"]} for mo in MONTHS}

def _buyer_total_from_pct(open_by_mc: dict, buyer_pct_of_open_mc: dict) -> dict:
    # Returns {month: {country: buyer_total_mmbtu}}
    out = {}
    for m in open_by_mc:
        out[m] = {}
        for c in ["SG","JP","CN"]:
            open_val = float(open_by_mc[m][c])
            bo_pct   = float(buyer_pct_of_open_mc[m][c])  # 0..1
            out[m][c] = open_val * bo_pct
    return out

# new
def _default_buyer_pct_per_month_from_market(open_by_mc: dict, buyer_total_by_mc: dict):
    """
    Create defaults: {buyer_name:{month: % of Open (0..100)}}.
    Equal split of Buyer Total among buyers in the same country, then converted to % of Open.
    """
    months = [m.month for m in MONTHS]
    pct_map = {b.name: {m: 0.0 for m in months} for b in BUYERS}

    buyers_by_country = {
        "SG": [b for b in BUYERS if b.country == "SG"],
        "JP": [b for b in BUYERS if b.country == "JP"],
        "CN": [b for b in BUYERS if b.country == "CN"],
    }

    for m in months:
        for c, buyers in buyers_by_country.items():
            n = max(1, len(buyers))
            open_c = float(open_by_mc[m][c])
            buyer_total_c = float(buyer_total_by_mc[m][c])
            per_buyer_mmbtu = buyer_total_c / n if n > 0 else 0.0
            pct_of_open = (per_buyer_mmbtu / open_c * 100.0) if open_c > 0 else 0.0
            for b in buyers:
                pct_map[b.name][m] = pct_of_open
    return pct_map

def price_from_jkm(nf: float) -> dict[str, float]:
    return {m: mo.price_usd_jkm_mmbtu + nf for m, mo in MONTH_BY_NAME.items()}

def ironman_price(nf: float) -> dict[str, float]:
    return {m: mo.target_sell_price_mmbtu_sg[1] + nf for m, mo in MONTH_BY_NAME.items()}

buyer_Ironman = LNGBuyer(
    name="Iron Man Pte Ltd", 
    country="SG",
    profile="Bunker Supplier", 
    credit_rating="A", 
    negotiation_factor= 4.0, 
    price=ironman_price(4.0))

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

# ===== Derived default percentages (0..1) =====
# Open% = Open Demand / Assumed Demand
OPEN_PCT_DEFAULT = {
    "Jan-2026": {"SG": 0.10, "CN": 0.10, "JP": 0.05},
    "Feb-2026": {"SG": 0.25, "CN": 0.25, "JP": 0.25},
    "Mar-2026": {"SG": 0.50, "CN": 0.25, "JP": 0.25},
    "Apr-2026": {"SG": 0.50, "CN": 0.50, "JP": 0.70},
    "May-2026": {"SG": 0.65, "CN": 0.60, "JP": 0.70},
    "Jun-2026": {"SG": 0.65, "CN": 0.60, "JP": 0.70},
}

# Buyer% of Open = Buyer Total / Open Demand
BUYER_OF_OPEN_PCT_DEFAULT = {
    "Jan-2026": {"SG": 1.00, "CN": 1.00, "JP": 0.05},
    "Feb-2026": {"SG": 0.50, "CN": 0.25, "JP": 0.25},
    "Mar-2026": {"SG": 0.50, "CN": 0.25, "JP": 0.25},
    "Apr-2026": {"SG": 0.50, "CN": 0.50, "JP": 0.70},
    "May-2026": {"SG": 0.50, "CN": 0.60, "JP": 0.70},
    "Jun-2026": {"SG": 0.50, "CN": 0.60, "JP": 0.70},
}

# --- DEFAULT Buyer Open Demand (MMBtu) per buyer per month ---
# Directly hardcoded from provided table.
BUYER_OPEN_DEMAND_DEFAULT = {
    "Iron Man Pte Ltd": {
        "Jan-2026": 3_570_000, "Feb-2026": 4_462_500, "Mar-2026": 8_925_000,
        "Apr-2026": 8_925_000, "May-2026": 11_602_500, "Jun-2026": 11_602_500,
    },
    "Thor Pte Ltd": {
        "Jan-2026": 3_570_000, "Feb-2026": 4_462_500, "Mar-2026": 8_925_000,
        "Apr-2026": 8_925_000, "May-2026": 11_602_500, "Jun-2026": 11_602_500,
    },
    "Vision Pte Ltd": {
        "Jan-2026": 3_570_000, "Feb-2026": 4_462_500, "Mar-2026": 8_925_000,
        "Apr-2026": 8_925_000, "May-2026": 11_602_500, "Jun-2026": 11_602_500,
    },
    "Loki Pte Ltd": {
        "Jan-2026": 3_570_000, "Feb-2026": 4_462_500, "Mar-2026": 8_925_000,
        "Apr-2026": 8_925_000, "May-2026": 11_602_500, "Jun-2026": 11_602_500,
    },
    "Hawk Eye Pte Ltd": {
        "Jan-2026": 796_500, "Feb-2026": 19_656_250, "Mar-2026": 18_112_500,
        "Apr-2026": 135_142_000, "May-2026": 119_021_000, "Jun-2026": 113_190_000,
    },
    "Ultron Pte Ltd": {
        "Jan-2026": 796_500, "Feb-2026": 19_656_250, "Mar-2026": 18_112_500,
        "Apr-2026": 135_142_000, "May-2026": 119_021_000, "Jun-2026": 113_190_000,
    },
    "Quicksilver Pte Ltd": {
        "Jan-2026": 796_500, "Feb-2026": 19_656_250, "Mar-2026": 18_112_500,
        "Apr-2026": 135_142_000, "May-2026": 119_021_000, "Jun-2026": 113_190_000,
    },
    "Hulk Pte Ltd": {
        "Jan-2026": 29_720_000, "Feb-2026": 15_312_500, "Mar-2026": 14_662_500,
        "Apr-2026": 65_950_000, "May-2026": 90_864_000, "Jun-2026": 99_684_000,
    },
}

# Turn {country:{month:val}} into {month:{country:val}}
def _by_month_country(d_country_month: dict) -> dict:
    return {mo.month: {c: float(d_country_month[c][mo.month]) for c in ["SG","JP","CN"]} for mo in MONTHS}

def _buyer_total_from_pct(open_by_mc: dict, buyer_pct_of_open_mc: dict) -> dict:
    # {month:{country: buyer_total_mmbtu}}
    out = {}
    for m in open_by_mc:
        out[m] = {}
        for c in ["SG","JP","CN"]:
            out[m][c] = float(open_by_mc[m][c]) * float(buyer_pct_of_open_mc[m][c])
    return out

# def _default_caps_from_buyer_total(buyer_total_by_mc: dict) -> dict:
#     """
#     Default caps = split each country-month's Buyer Total equally across
#     buyers in that country. Returns {month:{buyer_name: cap_mmbtu}}
#     """
#     months = [m.month for m in MONTHS]
#     by_country = {"SG": [], "JP": [], "CN": []}
#     for b in BUYERS:
#         by_country[b.country].append(b.name)

#     caps = {m: {} for m in months}
#     for m in months:
#         for c in ["SG","JP","CN"]:
#             names = by_country[c]
#             n = max(1, len(names))
#             total = float(buyer_total_by_mc[m][c])
#             per = total / n if n > 0 else 0.0
#             for name in names:
#                 caps[m][name] = caps[m].get(name, 0.0) + per
#     return caps

# --- Helpers to build/validate caps from your per-buyer defaults ---

def _buyer_caps_from_per_buyer_defaults(per_buyer: dict) -> dict:
    """
    Convert {buyer:{month:value}} -> {month:{buyer:value}} for use as caps.
    Only includes buyers that exist in BUYERS. Missing months default to 0.0.
    """
    months = [m.month for m in MONTHS]
    valid_names = {b.name for b in BUYERS}
    caps = {m: {} for m in months}

    for buyer_name in valid_names:
        per_month = per_buyer.get(buyer_name, {})
        for m in months:
            caps[m][buyer_name] = float(per_month.get(m, 0.0))
    return caps


def _validate_caps_against_country_totals(caps_by_month: dict, buyer_total_by_mc: dict) -> dict:
    """
    Ensure that for each (month, country), the sum of caps of buyers in that country
    does not exceed that country’s Buyer Total (Open × Buyer% of Open).
    If it does, scale down the buyers in that country proportionally.
    """
    months = [m.month for m in MONTHS]
    buyers_by_country = {
        "SG": [b.name for b in BUYERS if b.country == "SG"],
        "JP": [b.name for b in BUYERS if b.country == "JP"],
        "CN": [b.name for b in BUYERS if b.country == "CN"],
    }

    # copy so we don't mutate the original
    out = {m: dict(caps_by_month.get(m, {})) for m in months}

    for m in months:
        for c, names in buyers_by_country.items():
            country_cap_sum = sum(out[m].get(n, 0.0) for n in names)
            limit = float(buyer_total_by_mc[m][c])
            if country_cap_sum > 0 and country_cap_sum > limit:
                scale = limit / country_cap_sum
                for n in names:
                    out[m][n] = out[m].get(n, 0.0) * scale
    return out

def _caps_from_buyer_pct_monthly(pct_map_by_buyer: dict, open_by_mc: dict, buyer_total_by_mc: dict) -> dict:
    months = [m.month for m in MONTHS]
    caps = {m: {} for m in months}
    country_by_buyer = {b.name: b.country for b in BUYERS}

    # 1) raw caps from % of Open
    for bname, per_month in pct_map_by_buyer.items():
        c = country_by_buyer[bname]
        for m in months:
            pct = max(0.0, float(per_month.get(m, 0.0))) / 100.0
            caps[m][bname] = float(open_by_mc[m][c]) * pct

    # 2) normalize within (month,country) to not exceed Buyer Total
    buyers_by_country = {
        "SG": [b.name for b in BUYERS if b.country == "SG"],
        "JP": [b.name for b in BUYERS if b.country == "JP"],
        "CN": [b.name for b in BUYERS if b.country == "CN"],
    }
    for m in months:
        for c, names in buyers_by_country.items():
            cap_sum = sum(caps[m].get(n, 0.0) for n in names)
            limit = float(buyer_total_by_mc[m][c])
            if cap_sum > 0 and cap_sum > limit:
                scale = limit / cap_sum
                for n in names:
                    caps[m][n] = caps[m].get(n, 0.0) * scale
    return caps

# Turn buyer %s (0..100 of Open) into per-buyer caps (MMBtu), then validate vs Buyer Totals
def _caps_from_buyer_pct_monthly(pct_map_by_buyer: dict, open_by_mc: dict, buyer_total_by_mc: dict) -> dict:
    months = [m.month for m in MONTHS]
    caps = {m: {} for m in months}
    # build caps from % of Open
    country_by_buyer = {b.name: b.country for b in BUYERS}
    for bname, per_month in pct_map_by_buyer.items():
        c = country_by_buyer[bname]
        for m in months:
            pct = float(per_month.get(m, 0.0)) / 100.0
            caps[m][bname] = float(open_by_mc[m][c]) * max(0.0, pct)

    # validate: do not exceed Buyer Total per (month,country)
    return _validate_caps_against_country_totals(caps, buyer_total_by_mc)

# ---- Helpers for UI state ----
def _buyer_key(name: str) -> str:
    # If you want super-safe keys: return "buyer_" + "".join(ch if ch.isalnum() else "_" for ch in name)
    return f"buyer_{name}"

def _toggle_all_buyers():
    val = st.session_state.get("select_all", True)
    for b in BUYERS:
        st.session_state[_buyer_key(b.name)] = val
    # mark recompute
    st.session_state["trigger_recompute"] = True

def _mark_dirty():
    st.session_state["trigger_recompute"] = True

# Extend init_state() to store demand + buyer % defaults
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
    ss.setdefault("open_pct", OPEN_PCT_DEFAULT)
    ss.setdefault("buyer_of_open_pct", BUYER_OF_OPEN_PCT_DEFAULT)

    # DERIVE from MARKET: Open and Buyer Totals
    open_by_mc, buyer_total_by_mc = _derive_open_and_buyer_totals_from_market(
        MARKET_BY_MC, ss["open_pct"], ss["buyer_of_open_pct"]
    )
    ss.setdefault("open_demand", open_by_mc)     # {month:{country: MMBtu}}
    ss.setdefault("buyer_total", buyer_total_by_mc)

    # Default per-buyer % of Open (0..100) from market-derived totals (equal share in-country)
    ss.setdefault("buyer_pct_monthly", _default_buyer_pct_per_month_from_market(open_by_mc, buyer_total_by_mc))

    # Build per-buyer caps from those %s (bounded by Buyer Totals)
    ss.setdefault("buyer_caps", _caps_from_buyer_pct_monthly(ss["buyer_pct_monthly"], open_by_mc, buyer_total_by_mc))

init_state()

# -------------------------------------------------
# Compute Profitability
# -------------------------------------------------
def _buyer_caps_by_month(buyers, buyer_weights_by_country, buyer_total_by_mc):
    """
    Returns caps: {month: {buyer_name: cap_mmbtu}}
    Splits each country-month BuyerTotal across *active* buyers by their per-month weight.
    """
    caps = {m.month: {} for m in MONTHS}
    for mo in MONTHS:
        m = mo.month
        for c in ["SG","JP","CN"]:
            total_c = float(buyer_total_by_mc[m][c])
            # sum weights for active buyers of this country in this month
            denom = 0.0
            w_this = {}
            for b in buyers:
                if b.country != c: 
                    continue
                w = float(buyer_weights_by_country.get(c, {}).get(b.name, {}).get(m, 0.0))
                if w > 0:
                    w_this[b.name] = w
                    denom += w
            if total_c <= 0 or denom <= 0:
                continue
            # per-buyer caps from weights
            for name, w in w_this.items():
                caps[m][name] = caps[m].get(name, 0.0) + total_c * (w / denom)
    return caps

def compute_profit_table_greedy_caps(buyers, buyer_caps_by_month, monthly_supply_mmbtu):
    """
    For each month:
      - Build candidate buyers with cap > 0 and a valid price for that month.
      - Compute margin = price - final_cost(country).
      - Sort by margin DESC and allocate greedily until supply is exhausted or caps filled.

    buyer_caps_by_month: {month:{buyer_name: cap_mmbtu}}
    """
    rows = []

    for mo in MONTHS:
        m = mo.month
        supply_remaining = float(monthly_supply_mmbtu)

        # Candidates: active buyers with a cap for this month
        candidates = []
        for b in buyers:
            cap = float(buyer_caps_by_month.get(m, {}).get(b.name, 0.0))
            if cap <= 0:
                continue
            price = b.price.get(m)
            if price is None:
                continue
            c = b.country
            final_cost = mo.final_cost_usd_mmbtu[c]
            margin = price - final_cost
            candidates.append({
                "buyer": b, "cap": cap, "country": c,
                "price": price, "final_cost": final_cost, "margin": margin
            })

        # Sort by margin DESC
        candidates.sort(key=lambda x: x["margin"], reverse=True)

        # Greedy allocation
        for item in candidates:
            if supply_remaining <= 0:
                break
            take = min(item["cap"], supply_remaining)
            if take <= 0:
                continue

            b = item["buyer"]
            profit = item["margin"] * take
            pd_ = getattr(b, "probability_of_default", 0.0)
            adj_profit = profit * (1 - pd_)

            rows.append({
                "Month": m,
                "Country": item["country"],
                "Buyer": b.name,
                "Allocated Volume (MMBtu)": take,
                "Buyer Price ($/MMBtu)": item["price"],
                "Final Cost ($/MMBtu)": item["final_cost"],
                "Margin ($/MMBtu)": item["margin"],
                "Profit (USD)": profit,
                "Credit Rating": b.credit_rating,
                "Probability of Default": pd_,
                "Adjusted Profit (USD)": adj_profit,
                "Profile": b.profile,
            })

            # reduce cap and supply
            buyer_caps_by_month[m][b.name] = item["cap"] - take
            supply_remaining -= take

        # Optional: expose leftover monthly supply metric
        st.session_state[f"leftover_supply_{m}"] = supply_remaining

    return pd.DataFrame(rows)

# -------------------------------------------------
# Streamlit UI
# -------------------------------------------------
st.title("Bazingaaa!")
st.caption("Optimisation based on buyer price and LNGMonth final costs.")

# -------------------------------------------------
# Top-of-page variable controls
# -------------------------------------------------
controls = st.container()
with controls:
    st.subheader("Assumptions")
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Sell Position (MMBtu)", f"{SELL_POSITION:,.0f}")
    with m2:
        st.metric("Shipment Volume (MMBtu)", f"{SHIPMENT_VOLUME:,.0f}")
    with m3:
        st.metric("Total Terminal Cost (USD)", f"{TOTAL_TERMINAL_COST:,.0f}")

    st.markdown("---")

    st.subheader("Buyer Availability & Allocation")

    # Master toggle
    select_all = st.checkbox("Select all buyers", value=True, key="select_all", on_change=_toggle_all_buyers)

    active_buyers = []
    months = [m.month for m in MONTHS]

    # Header row for months (optional)
    hdr = st.columns([0.40] + [0.10]*6)
    hdr[0].markdown("**Buyer (Country, Rating)**")
    for i, m in enumerate(months):
        hdr[i+1].markdown(f"**{m.split('-')[0]}**")

    # Collect % inputs per buyer per month (0..100)
    for b in BUYERS:
        row = st.columns([0.40] + [0.10]*6)

        checked = row[0].checkbox(
            f"{b.name} ({b.country}, {b.credit_rating})",
            value=st.session_state.get(_buyer_key(b.name), select_all),
            key=_buyer_key(b.name),
            on_change=_mark_dirty
        )
        if checked:
            active_buyers.append(b)

        # defaults from state
        defaults = st.session_state.buyer_pct_monthly.get(b.name, {m: 0.0 for m in months})

        new_vals = {}
        for i, m in enumerate(months):
            new_vals[m] = row[i+1].number_input(
                label=f"% {m}",  # label hidden by Streamlit when in column; okay
                min_value=0.0, max_value=100.0, step=1.0,
                value=float(defaults.get(m, 0.0)),
                key=f"pct_{b.name}_{m}",
                help="% of that country's Open Demand to allocate to this buyer for the given month.",
                on_change=_mark_dirty
            )

        # persist if any changed
        if any(new_vals[m] != defaults.get(m, 0.0) for m in months):
            st.session_state.buyer_pct_monthly[b.name] = new_vals
            st.session_state["trigger_recompute"] = True



    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        auto_recompute = st.toggle(
            "Auto-recompute on changes",
            value=False,
            help="When ON, we recompute on each change."
        )
    with c2:
        recompute_clicked = st.button("Recompute now")

    st.markdown("---")
    st.subheader("Buyer Capacities (MMBtu) per Month")

    months = [m.month for m in MONTHS]

    # # Button to regenerate caps from the current Buyer Totals (handy after you tweak percentages)
    # if st.button("Reset caps from current Buyer Totals"):
    #     st.session_state.buyer_total = _buyer_total_from_pct(
    #         st.session_state.open_demand,
    #         st.session_state.buyer_of_open_pct
    #     )
    #     st.session_state.buyer_caps = _default_caps_from_buyer_total(st.session_state.buyer_total)
    #     st.session_state["trigger_recompute"] = True
    #     st.success("Caps reset from Buyer Totals.")

    if st.button("Load caps from Buyer Open Demand defaults"):
        st.session_state.buyer_total = _buyer_total_from_pct(
            st.session_state.open_demand, st.session_state.buyer_of_open_pct
        )
        st.session_state.buyer_caps = _validate_caps_against_country_totals(
            _buyer_caps_from_per_buyer_defaults(BUYER_OPEN_DEMAND_DEFAULT),
            st.session_state.buyer_total
        )
        st.session_state["trigger_recompute"] = True
        st.success("Caps loaded from Buyer Open Demand defaults.")

    # Build caps editor DF: rows=buyers (all), cols=months
    rows = []
    for b in BUYERS:  # show all; inactive ones just won't be used in compute
        r = {"Buyer": b.name, "Country": b.country}
        for m in months:
            r[m] = float(st.session_state.buyer_caps.get(m, {}).get(b.name, 0.0))
        rows.append(r)

    caps_df = pd.DataFrame(rows, columns=["Buyer","Country"] + months)

    edited_caps = st.data_editor(
        caps_df,
        use_container_width=True,
        num_rows="fixed",
        key="buyer_caps_editor",
        column_config={
            "Buyer": st.column_config.TextColumn(disabled=True),
            "Country": st.column_config.TextColumn(disabled=True),
            **{m: st.column_config.NumberColumn(format="%.0f", min_value=0.0) for m in months},
        },
    )

    # Persist edits back
    persisted = {m: {} for m in months}
    for _, r in edited_caps.iterrows():
        name = r["Buyer"]
        for m in months:
            persisted[m][name] = float(r[m])

    if persisted != st.session_state.buyer_caps:
        st.session_state.buyer_caps = persisted
        st.session_state["trigger_recompute"] = True

# Run analysis
# --- Compute-on-load + on-demand/auto recompute ---
should_compute = False

# compute on first load
if "df" not in st.session_state:
    should_compute = True

# consume and clear the dirty flag set by checkbox changes
trigger_recompute = st.session_state.pop("trigger_recompute", False)

# recompute on demand or auto if dirty
if recompute_clicked or (auto_recompute and trigger_recompute):
    should_compute = True

if should_compute:
    if not active_buyers:
        st.warning("No buyers selected. Please enable at least one buyer.")
        st.session_state.df = pd.DataFrame()
    else:
        # REBUILD on compute (inside your should_compute block)
        open_by_mc, buyer_total_by_mc = _derive_open_and_buyer_totals_from_market(
            MARKET_BY_MC, st.session_state.open_pct, st.session_state.buyer_of_open_pct
        )
        st.session_state.open_demand = open_by_mc
        st.session_state.buyer_total = buyer_total_by_mc

        st.session_state.buyer_caps = _caps_from_buyer_pct_monthly(
            st.session_state.buyer_pct_monthly,
            st.session_state.open_demand,
            st.session_state.buyer_total
        )

        st.session_state.df = compute_profit_table_greedy_caps(
            active_buyers,
            st.session_state.buyer_caps,
            monthly_supply_mmbtu=SELL_POSITION
        )


        diag = (
            st.session_state.df.groupby(["Month","Country"])["Allocated Volume (MMBtu)"]
            .sum().rename("Allocated (MMBtu)").reset_index()
        )
        # Show leftover supply per month
        leftovers = [{ "Month": m.month, "Leftover Supply (MMBtu)": st.session_state.get(f"leftover_supply_{m.month}", 0.0)} for m in MONTHS]
        col1, col2 = st.columns(2)
        with col1:
            st.dataframe(diag, use_container_width=True)
        with col2:
            st.dataframe(pd.DataFrame(leftovers), use_container_width=True)

        st.success(f"Credit-adjusted profit table computed for {len(active_buyers)} active buyers.")

df = st.session_state.get("df", pd.DataFrame())

if not df.empty:
    # keep month order consistent
    month_order = [m.month for m in MONTHS]
    df["Month"] = pd.Categorical(df["Month"], categories=month_order, ordered=True)

    st.dataframe(df, use_container_width=True)

    # --- Remove: "Best Buyer per Month (Credit-Adjusted)" table ---

    # Total adjusted profit metric (entire horizon)
    total_adj_profit = float(df["Adjusted Profit (USD)"].sum())
    st.metric("Total Adjusted Profit (USD)", f"{total_adj_profit:,.0f}")

    # --- New: Per-Month Breakdown by Buyer (stacked) ---
    st.subheader("Adjusted Profit — Breakdown by Buyer & Month")
    chart_profit = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("Month:N", sort=month_order, title="Month"),
            y=alt.Y("sum(Adjusted Profit (USD)):Q", title="Adjusted Profit (USD)"),
            color=alt.Color("Buyer:N", legend=alt.Legend(title="Buyer")),
            tooltip=[
                alt.Tooltip("Month:N"),
                alt.Tooltip("Buyer:N"),
                alt.Tooltip("Country:N"),
                alt.Tooltip("sum(Allocated Volume (MMBtu)):Q", title="Allocated Volume (MMBtu)", format=",.0f"),
                alt.Tooltip("sum(Adjusted Profit (USD)):Q", title="Adjusted Profit (USD)", format=",.0f"),
            ],
        )
        .properties(height=360)
    )
    st.altair_chart(chart_profit, use_container_width=True)

    # Optional: also show allocated volume by buyer per month (stacked)
    st.subheader("Allocated Volume — Breakdown by Buyer & Month")
    chart_vol = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("Month:N", sort=month_order, title="Month"),
            y=alt.Y("sum(Allocated Volume (MMBtu)):Q", title="Allocated Volume (MMBtu)"),
            color=alt.Color("Buyer:N", legend=alt.Legend(title="Buyer")),
            tooltip=[
                alt.Tooltip("Month:N"),
                alt.Tooltip("Buyer:N"),
                alt.Tooltip("Country:N"),
                alt.Tooltip("sum(Allocated Volume (MMBtu)):Q", title="Allocated Volume (MMBtu)", format=",.0f"),
                alt.Tooltip("sum(Adjusted Profit (USD)):Q", title="Adjusted Profit (USD)", format=",.0f"),
            ],
        )
        .properties(height=360)
    )
    st.altair_chart(chart_vol, use_container_width=True)

    # Optional: facet by Country to see pool-level composition
    with st.expander("Show per-country facets"):
        chart_profit_country = chart_profit.facet(column=alt.Column("Country:N", title=None))
        st.altair_chart(chart_profit_country, use_container_width=True)

    # (Optional) Keep a simple totals-by-buyer view (not per-month)
    with st.expander("Totals by Buyer (entire horizon)"):
        totals = (
            df.groupby("Buyer", as_index=False)
              .agg({"Allocated Volume (MMBtu)": "sum", "Adjusted Profit (USD)": "sum"})
              .sort_values("Adjusted Profit (USD)", ascending=False)
        )
        st.dataframe(
            totals.style.format({
                "Allocated Volume (MMBtu)": "{:,.0f}",
                "Adjusted Profit (USD)": "{:,.0f}",
            }),
            use_container_width=True
        )

    with st.expander("Demand Assumptions (Open Demand by Country & Month)", expanded=False):
        # Build a DataFrame for editing
        demand_df = pd.DataFrame.from_dict(st.session_state.open_demand, orient="index")
        demand_df = demand_df[COUNTRIES]  # ensure consistent column order
        demand_df.index.name = "Month"

        # Editor: users can change Open Demand (MMBtu)
        edited_demand = st.data_editor(
            demand_df.reset_index(),
            num_rows="fixed",
            use_container_width=True,
            key="open_demand_editor",
            column_config={
                "Month": st.column_config.TextColumn(disabled=True),
                "SG": st.column_config.NumberColumn(format="%.0f", min_value=0),
                "JP": st.column_config.NumberColumn(format="%.0f", min_value=0),
                "CN": st.column_config.NumberColumn(format="%.0f", min_value=0),
            },
        )

        # Persist back to session_state and mark dirty if changed
        new_demand_map = {
            row["Month"]: {c: float(row[c]) for c in COUNTRIES}
            for _, row in edited_demand.iterrows()
        }
        if new_demand_map != st.session_state.open_demand:
            st.session_state.open_demand = new_demand_map
            st.session_state["trigger_recompute"] = True
