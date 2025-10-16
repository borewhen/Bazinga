# LNG Strategy App (Prototype)

A lightweight framework to prototype an LNG commercial optimisation model and expose it via a Streamlit UI.

## Quick start

```bash
# 1) Create & activate a virtual env (recommended)
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2) Install deps
pip install -r requirements.txt

# 3) Run the app
streamlit run app.py
```

## What this does

- Maximises profit by allocating a fixed cargo supply across destination ports subject to capacity constraints.
- Computes unit economics per destination (delivered volume after boil-off, shipping cost by distance, variable cost).
- Lets you run scenarios (e.g., cold snap in NE Asia, SLNG outage) and compare Base vs Scenario results.
- Visualises allocations, PnL, and sensitivity.

> **Note:** This is a scaffold: you can plug in real prices, distances, fleet/vessel constraints, contract terms, etc.

## Project structure

```
lng_strategy_app/
├── app.py                     # Streamlit UI
├── requirements.txt
├── README.md
├── data/
│   ├── ports.csv              # Destination metadata (distance, capacity, names)
│   └── base_inputs.json       # Default financial assumptions
└── model/
    ├── optimisation.py        # LP model (PuLP)
    ├── financials.py          # Unit economics + PnL helpers
    └── scenarios.py           # Scenario definitions
```

## Extending the model

- Add more destinations in `data/ports.csv`.
- Incorporate vessel routing & timing as MIP (multi-period, integer decisions).
- Add storage vs immediate sale with inventory balance constraints.
- Wire to live data feeds (prices, outages, freight) via your internal adapters.
- Harden inputs & outputs with pydantic and add tests.
