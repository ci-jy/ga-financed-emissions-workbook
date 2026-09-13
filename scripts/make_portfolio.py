"""Generate the seeded SYNTHETIC general-account fixed-income book.

No real issuers: every name is a generated label such as "SYN Electric Utilities 03 Corp".
Sector weights and revenue-to-EVIC proxies come from data/reference/sector_assumptions.csv and are
illustrative of a Canadian insurer's corporate bond book, not of any actual portfolio.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import layout  # noqa: E402

SEED = 20240630
N_HOLDINGS = 300
BOOK_TOTAL_MCAD = 12_000.0  # stated book size, $M CAD
REVENUE_DISCLOSED_SHARE = 0.30  # share of holdings with issuer revenue on file (PCAF score 4)
INSTRUMENTS = ["Public corporate bond", "Private placement", "Infrastructure debt"]
RATINGS = ["AAA", "AA", "A", "BBB"]


def build(seed: int = SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    assumptions = pd.read_csv(ROOT / "data" / "reference" / "sector_assumptions.csv").set_index("portfolio_sector")
    assumptions = assumptions.loc[layout.SECTORS]
    weights = assumptions["target_book_weight"]
    assert abs(weights.sum() - 1.0) < 1e-9

    counts = np.maximum(4, np.floor(weights * N_HOLDINGS)).astype(int)
    order = np.argsort(-(weights * N_HOLDINGS - np.floor(weights * N_HOLDINGS)).to_numpy())
    i = 0
    while counts.sum() < N_HOLDINGS:
        counts.iloc[order[i % len(order)]] += 1
        i += 1
    while counts.sum() > N_HOLDINGS:
        counts.iloc[int(np.argmax(counts.to_numpy()))] -= 1

    rows = []
    for sector, n in counts.items():
        raw = rng.lognormal(mean=0.0, sigma=0.6, size=n)
        amounts = raw / raw.sum() * weights[sector] * BOOK_TOTAL_MCAD
        for k, amount in enumerate(amounts, start=1):
            share_of_evic = rng.uniform(0.002, 0.04)
            evic = amount / share_of_evic
            disclosed = rng.random() < REVENUE_DISCLOSED_SHARE
            revenue = evic * assumptions.loc[sector, "revenue_to_evic_proxy"] * rng.lognormal(0.0, 0.25) if disclosed else np.nan
            rows.append({
                "sector": sector,
                "issuer": f"SYN {sector} {k:02d} Corp",
                "instrument": INSTRUMENTS[int(rng.choice(3, p=[0.6, 0.3, 0.1]))],
                "rating": RATINGS[int(rng.choice(4, p=[0.05, 0.2, 0.4, 0.35]))],
                "outstanding_mcad": amount,
                "evic_mcad": evic,
                "revenue_mcad": revenue,
            })
    df = pd.DataFrame(rows)
    df["outstanding_mcad"] = df["outstanding_mcad"].round(1)
    df.loc[df.index[-1], "outstanding_mcad"] += round(BOOK_TOTAL_MCAD - df["outstanding_mcad"].sum(), 1)
    df["outstanding_mcad"] = df["outstanding_mcad"].round(1)
    df["evic_mcad"] = df["evic_mcad"].round(0)
    df["revenue_mcad"] = df["revenue_mcad"].round(0)
    df.insert(0, "holding_id", [f"H{n:03d}" for n in range(1, len(df) + 1)])
    return df


def main() -> int:
    df = build()
    out = ROOT / "data" / "processed" / "holdings_synthetic.csv"
    df.to_csv(out, index=False)
    print(f"wrote {out}: {len(df)} holdings, {df.sector.nunique()} sectors, "
          f"total ${df.outstanding_mcad.sum():,.1f}M CAD, revenue disclosed for {df.revenue_mcad.notna().sum()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
