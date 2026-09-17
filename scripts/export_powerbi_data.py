"""Write the CSV extracts the Power BI semantic model imports, and the PBIP report pages.

powerbi/data/holdings.csv       holding-level book (SYNTHETIC)
powerbi/data/sectors.csv        reporting-year StatCan emission factors, output and revenue/EVIC proxy
powerbi/data/carbon_prices.csv  scenario x year price paths with free-allocation share
powerbi/GAFinancedEmissions.Report/report.json  three report pages bound to the DAX measures
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import layout as L  # noqa: E402

DATA = ROOT / "powerbi" / "data"
REPORT = ROOT / "powerbi" / "GAFinancedEmissions.Report" / "report.json"
REPORTING_YEAR = 2022

PAGES = [
    ("Emissions by Sector", [
        ("card", [("Measures", "Financed Emissions")]),
        ("card", [("Measures", "Carbon Footprint")]),
        ("card", [("Measures", "Weighted PCAF Score")]),
        ("clusteredBarChart", [("Sectors", "Sector"), ("Measures", "Financed Emissions")]),
        ("tableEx", [("Sectors", "Sector"), ("Measures", "Total Outstanding"), ("Measures", "Holding Count"),
                     ("Measures", "Financed Emissions"), ("Measures", "Share of Financed Emissions"),
                     ("Measures", "Share of Book at PCAF 5")]),
    ]),
    ("WACI vs Benchmark", [
        ("card", [("Measures", "WACI")]),
        ("card", [("Measures", "Benchmark WACI")]),
        ("card", [("Measures", "WACI vs Benchmark")]),
        ("clusteredColumnChart", [("Sectors", "Sector"), ("Measures", "Portfolio Weight"), ("Measures", "Benchmark Weight")]),
        ("tableEx", [("Sectors", "Sector"), ("Sectors", "EmissionFactor"), ("Measures", "Portfolio Weight"),
                     ("Measures", "Benchmark Weight"), ("Measures", "WACI"), ("Measures", "Benchmark WACI")]),
    ]),
    ("Scenario Carbon-Cost Exposure", [
        ("slicer", [("CarbonPrices", "Scenario")]),
        ("card", [("Measures", "Carbon Cost 2030 Current Policy")]),
        ("card", [("Measures", "Carbon Cost 2030 Net-Zero")]),
        ("card", [("Measures", "Carbon Cost 2030 Delayed Transition")]),
        ("lineChart", [("CarbonPrices", "Year"), ("CarbonPrices", "Scenario"), ("Measures", "Carbon Cost MCAD")]),
        ("tableEx", [("CarbonPrices", "Scenario"), ("CarbonPrices", "Year"), ("Measures", "Effective Carbon Price"),
                     ("Measures", "Carbon Cost MCAD"), ("Measures", "Carbon Cost Share of Holdings")]),
    ]),
]


def visual(kind: str, fields: list[tuple[str, str]], x: int, y: int, w: int, h: int, idx: int) -> dict:
    selects, roles = [], {}
    for table, name in fields:
        is_measure = table == "Measures"
        ref = {"Measure" if is_measure else "Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": name},
               "Name": f"{table}.{name}"}
        selects.append(ref)
        role = "Values" if is_measure else ("Category" if kind != "tableEx" else "Values")
        if kind == "lineChart" and table == "CarbonPrices" and name == "Scenario":
            role = "Series"
        roles.setdefault("Y" if is_measure and kind not in ("card", "tableEx") else role, []).append({"queryRef": f"{table}.{name}"})
    config = {"name": f"v{idx:02d}", "singleVisual": {"visualType": kind, "projections": roles,
                                                       "prototypeQuery": {"Version": 2, "Select": selects}}}
    return {"x": x, "y": y, "z": idx, "width": w, "height": h, "config": json.dumps(config)}


def report() -> dict:
    sections = []
    for p, (name, visuals) in enumerate(PAGES):
        containers, cards = [], 0
        for i, (kind, fields) in enumerate(visuals):
            if kind in ("card", "slicer"):
                containers.append(visual(kind, fields, 20 + cards * 310, 20, 290, 110, i)); cards += 1
            elif kind == "tableEx":
                containers.append(visual(kind, fields, 650, 150, 610, 550, i))
            else:
                containers.append(visual(kind, fields, 20, 150, 610, 550, i))
        sections.append({"name": f"page{p + 1}", "displayName": name, "ordinal": p, "width": 1280, "height": 720,
                         "displayOption": 1, "visualContainers": containers})
    return {"config": json.dumps({"version": "5.43"}), "layoutOptimization": 0, "sections": sections}


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    h = pd.read_csv(ROOT / "data" / "processed" / "holdings_synthetic.csv")
    pd.DataFrame({
        "HoldingID": h.holding_id, "Issuer": h.issuer, "Sector": h.sector, "Instrument": h.instrument,
        "OutstandingMCAD": h.outstanding_mcad, "EVICMCAD": h.evic_mcad, "RevenueReportedMCAD": h.revenue_mcad,
    }).to_csv(DATA / "holdings.csv", index=False)

    ef = pd.read_csv(ROOT / "data" / "processed" / "emission_factors.csv")
    ef = ef[ef.year == REPORTING_YEAR].set_index("sector").loc[L.SECTORS]
    rte = pd.read_csv(ROOT / "data" / "reference" / "sector_assumptions.csv").set_index("portfolio_sector")
    pd.DataFrame({
        "Sector": L.SECTORS, "EmissionFactor": ef.ef_tco2e_per_musd.values, "OutputMCAD": ef.output_musd.values,
        "EmissionsKt": ef.emissions_kt.values, "RevenueToEVIC": rte.loc[L.SECTORS, "revenue_to_evic_proxy"].values,
    }).to_csv(DATA / "sectors.csv", index=False, float_format="%.10g")

    sc = pd.read_csv(ROOT / "data" / "reference" / "carbon_price_scenarios.csv")
    long = sc.melt(id_vars=["scenario", "free_allocation_share"], value_vars=[str(y) for y in L.SCENARIO_YEARS],
                   var_name="Year", value_name="PricePerTonne")
    long = long.rename(columns={"scenario": "Scenario", "free_allocation_share": "FreeAllocationShare"})
    long["Year"] = long.Year.astype(int)
    long[["Scenario", "Year", "PricePerTonne", "FreeAllocationShare"]].to_csv(DATA / "carbon_prices.csv", index=False)

    REPORT.write_text(json.dumps(report(), indent=2) + "\n")
    print(f"wrote Power BI extracts to {DATA} and {REPORT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
