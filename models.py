from dataclasses import dataclass
from typing import Dict, Optional, Tuple

# =========================
# GLOBAL CONSTANTS
# =========================
SELL_POSITION: float = 3_800_000      # MMBtu
SHIPMENT_VOLUME: float = 4_100_000    # MMBtu
BOR: float = 300_000                  # ASSUMPTION (units up to you)
BERTHING_COST: float = 0.10           # USD/MMBtu (assumption)
ROUTE_FREIGHT_MULT: Dict[str, float] = {"Panama": 1.00, "Suez": 1.15, "Cape": 1.25}

# Terminal/utility parameters
UTILISATION_RATES: Dict[str, float] = {
    "peak": 0.17167382,
    "shoulder": 0.093640265,
    "offpeak": 0.015606711,
}

RESERVATION_RATE_PER_MMBTU: float = 0.780335544  # USD/MMBtu

# If this is a per-cargo fixed fee, keep as USD value
TERMINAL_TARIFF_USD: float = 136_558.7202

def utility_total(volume: float = SHIPMENT_VOLUME) -> float:
    """Weighted total utilisation charge for a cargo."""
    w = (0.5 * UTILISATION_RATES["peak"] +
         (1/6) * UTILISATION_RATES["shoulder"] +
         (1/3) * UTILISATION_RATES["offpeak"])
    return w * volume

def reservation_total(volume: float = SHIPMENT_VOLUME) -> float:
    """Reservation charge total for a cargo."""
    return RESERVATION_RATE_PER_MMBTU * volume

# Total terminal cost per cargo (fixed + variable components)
TOTAL_TERMINAL_COST: float = TERMINAL_TARIFF_USD + utility_total() + reservation_total()

# =========================
# DATACLASSES
# =========================
@dataclass
class LNGDestination:
    name: str
    voyage_days: float
    tariff_usd: float = 0.0
    distance_nm: Optional[float] = None

@dataclass
class LNGMonth:
    """
    Month-level market & cost view. 
    - price_usd_brent_mmbtu: your Brent-derived reference (per MMBtu)
    - price_usd_jkm_mmbtu:   JKM forward (per MMBtu)
    - freight_cost:          per-destination total freight (USD) for one cargo
    - final_cost_usd_mmbtu:  per-destination fully-loaded cost per MMBtu
    """
    month: str
    cost_usd_hh_mmbtu: float
    price_usd_brent_mmbtu: float
    price_usd_jkm_mmbtu: float
    BLNG3g: float
    freight_cost: Dict[str, float]
    final_cost_usd_mmbtu: Dict[str, float]

    @property
    def cost_usd_hh_total(self) -> float:
        return self.cost_usd_hh_mmbtu * SHIPMENT_VOLUME

    @property
    def price_usd_brent_total(self) -> float:
        return self.price_usd_brent_mmbtu * SHIPMENT_VOLUME

    @property
    def price_usd_jkm_total(self) -> float:
        return self.price_usd_jkm_mmbtu * SHIPMENT_VOLUME

    @property
    def target_sell_price_mmbtu_sg(self) -> Tuple[float, float]:
        # Example: Brent index + tariff (adjust to your spec)
        lo = (self.price_usd_brent_mmbtu * 0.13 + 3.0) + 0.029
        hi = (self.price_usd_brent_mmbtu * 0.13 + 7.5) + 0.029
        return lo, hi

    @property
    def target_sell_price_mmbtu_jp(self) -> Tuple[float, float]:
        lo = self.price_usd_jkm_mmbtu + 0.5 + BERTHING_COST
        hi = self.price_usd_jkm_mmbtu + 1.2 + BERTHING_COST
        return lo, hi

    @property
    def target_sell_price_mmbtu_cn(self) -> Tuple[float, float]:
        lo = self.price_usd_jkm_mmbtu + 2.0 + BERTHING_COST
        hi = self.price_usd_jkm_mmbtu + 3.5 + BERTHING_COST
        return lo, hi

@dataclass
class LNGBuyer:
    name: str
    country: str
    profile: str
    credit_rating: str
    negotiation_factor: float
    price: Dict[str, float]
    probability_of_default: Optional[float] = None

    def __post_init__(self):
        # default PD mapping if not provided
        PD_TABLE = {
            "AAA": 0.0001,
            "AA": 0.0002,
            "A": 0.0005,
            "BBB": 0.002,
            "BB": 0.008,
            "B": 0.02,
            "CCC": 0.10,
        }
        if self.probability_of_default is None:
            self.probability_of_default = PD_TABLE.get(self.credit_rating.upper(), 0.05)
