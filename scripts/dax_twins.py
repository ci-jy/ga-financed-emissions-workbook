"""Pandas twins of the DAX measures in powerbi/.../tables/Measures.tmdl.

Each twin re-implements its measure over the same CSV extracts the semantic model imports
(powerbi/data/*.csv), evaluated in the filter contexts the report uses (grand total, per sector,
per scenario-year). `evaluate()` returns {"Sheet!Cell": value} so each twin value is checked against
the recalculated Excel workbook cell that reports the same metric.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "powerbi" / "data"
SEC_FIRST = 5
HEADLINE_YEAR = 2030


@dataclass
class PbiData:
    holdings: pd.DataFrame
    sectors: pd.DataFrame
    prices: pd.DataFrame


def load(data_dir: Path = DATA) -> PbiData:
    s = pd.read_csv(data_dir / "sectors.csv")
    h = pd.read_csv(data_dir / "holdings.csv")
    # calculated columns RevenueUsedMCAD and PCAFScore
    rte = h.Sector.map(s.set_index("Sector").RevenueToEVIC)
    h["RevenueUsedMCAD"] = np.where(h.RevenueReportedMCAD.isna(), h.EVICMCAD * rte, h.RevenueReportedMCAD)
    h["PCAFScore"] = np.where(h.RevenueReportedMCAD.isna(), 5, 4)
    h["EF"] = h.Sector.map(s.set_index("Sector").EmissionFactor)
    return PbiData(h, s, pd.read_csv(data_dir / "carbon_prices.csv"))


# ---- measure twins: f(data, holdings-in-context, sectors-in-context, prices-in-context) -------------
def total_outstanding(d, h, s, p): return h.OutstandingMCAD.sum()
def holding_count(d, h, s, p): return float(len(h))
def financed_emissions(d, h, s, p): return (h.OutstandingMCAD / h.EVICMCAD * h.RevenueUsedMCAD * h.EF).sum()
def carbon_footprint(d, h, s, p): return financed_emissions(d, h, s, p) / total_outstanding(d, h, s, p)
def portfolio_weight(d, h, s, p): return total_outstanding(d, h, s, p) / d.holdings.OutstandingMCAD.sum()
def waci(d, h, s, p): return (h.OutstandingMCAD / d.holdings.OutstandingMCAD.sum() * h.EF).sum()
def benchmark_weight(d, h, s, p): return s.OutputMCAD.sum() / d.sectors.OutputMCAD.sum()
def benchmark_waci(d, h, s, p): return (s.OutputMCAD / d.sectors.OutputMCAD.sum() * s.EmissionFactor).sum()
def waci_vs_benchmark(d, h, s, p): return waci(d, h, s, p) / benchmark_waci(d, d.holdings, d.sectors, p) - 1
def weighted_pcaf(d, h, s, p): return (h.OutstandingMCAD * h.PCAFScore).sum() / total_outstanding(d, h, s, p)
def share_pcaf5(d, h, s, p): return h.loc[h.PCAFScore == 5, "OutstandingMCAD"].sum() / total_outstanding(d, h, s, p)
def share_fe(d, h, s, p): return financed_emissions(d, h, s, p) / financed_emissions(d, d.holdings, d.sectors, p)
def effective_price(d, h, s, p): return (p.PricePerTonne * (1 - p.FreeAllocationShare)).mean()
def carbon_cost(d, h, s, p): return financed_emissions(d, h, s, p) * effective_price(d, h, s, p) / 1e6
def carbon_cost_share(d, h, s, p): return carbon_cost(d, h, s, p) / total_outstanding(d, h, s, p)


def cost_in(scenario: str) -> Callable:
    def f(d, h, s, p):
        return carbon_cost(d, h, s, p[(p.Scenario == scenario) & (p.Year == HEADLINE_YEAR)])
    return f


@dataclass
class Twin:
    func: Callable
    total_cell: str | None = None          # workbook cell for the grand-total context
    sector_col: str | None = None          # "Sheet!Col" holding the per-sector values (rows 5..26)
    scenario_block: str | None = None      # "Sheet!Row" first row of a scenario x year block (cols B..H)


FE, BC, CPS = "Financed Emissions", "Benchmark Comparison", "Carbon Price Scenarios"
TWINS: dict[str, Twin] = {
    "Total Outstanding": Twin(total_outstanding, "Summary!B5", f"{FE}!P"),
    "Holding Count": Twin(holding_count, "Summary!B4", f"{FE}!O"),
    "Financed Emissions": Twin(financed_emissions, "Summary!B7", f"{FE}!Q"),
    "Carbon Footprint": Twin(carbon_footprint, "Summary!B8", f"{FE}!T"),
    "Portfolio Weight": Twin(portfolio_weight, None, "WACI!B"),
    "WACI": Twin(waci, "Summary!B9", "WACI!D"),
    "Benchmark Weight": Twin(benchmark_weight, None, f"{BC}!C"),
    "Benchmark WACI": Twin(benchmark_waci, "Summary!B10", f"{BC}!F"),
    "WACI vs Benchmark": Twin(waci_vs_benchmark, "Summary!B11"),
    "Weighted PCAF Score": Twin(weighted_pcaf, "Summary!B12", f"{FE}!S"),
    "Share of Book at PCAF 5": Twin(share_pcaf5, "Summary!B13"),
    "Share of Financed Emissions": Twin(share_fe, None, f"{FE}!R"),
    "Effective Carbon Price": Twin(effective_price, scenario_block=f"{CPS}!5"),
    "Carbon Cost MCAD": Twin(carbon_cost, scenario_block=f"{CPS}!11"),
    "Carbon Cost Share of Holdings": Twin(carbon_cost_share, scenario_block=f"{CPS}!17"),
    "Carbon Cost 2030 Current Policy": Twin(cost_in("Current federal policy"), "Summary!B27"),
    "Carbon Cost 2030 Net-Zero": Twin(cost_in("Net-zero shadow price"), "Summary!B28"),
    "Carbon Cost 2030 Delayed Transition": Twin(cost_in("Delayed transition"), "Summary!B29"),
}


def evaluate(name: str, d: PbiData | None = None) -> dict[str, float]:
    """Evaluate one twin in every context it is reported in; keys are workbook cell references."""
    d = d or load()
    t = TWINS[name]
    out: dict[str, float] = {}
    if t.total_cell:
        out[t.total_cell] = float(t.func(d, d.holdings, d.sectors, d.prices))
    if t.sector_col:
        sheet, col = t.sector_col.split("!")
        for i, sector in enumerate(d.sectors.Sector):
            out[f"{sheet}!{col}{SEC_FIRST + i}"] = float(
                t.func(d, d.holdings[d.holdings.Sector == sector], d.sectors[d.sectors.Sector == sector], d.prices))
    if t.scenario_block:
        sheet, row = t.scenario_block.split("!")
        scenarios = list(dict.fromkeys(d.prices.Scenario))
        years = sorted(d.prices.Year.unique())
        for k, sc in enumerate(scenarios):
            for j, y in enumerate(years):
                p = d.prices[(d.prices.Scenario == sc) & (d.prices.Year == y)]
                out[f"{sheet}!{chr(ord('B') + j)}{int(row) + k}"] = float(t.func(d, d.holdings, d.sectors, p))
    return out
