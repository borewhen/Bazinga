from __future__ import annotations

def base_scenario():
    return {"name": "Base", "price_shocks": {}, "capacity_multipliers": {}}

def cold_snap_ne_asia():
    # Price spike in Japan & China
    return {"name": "Cold snap NE Asia", "price_shocks": {"JP": +3.0, "CN": +1.5}, "capacity_multipliers": {}}

def slng_outage():
    # Reduce Singapore capacity by 50%
    return {"name": "SLNG outage", "price_shocks": {}, "capacity_multipliers": {"SLNG": 0.5}}

SCENARIOS = {
    "Base": base_scenario(),
    "Cold snap NE Asia": cold_snap_ne_asia(),
    "SLNG outage": slng_outage(),
}
