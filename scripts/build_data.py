"""Clean the pinned StatCan snapshots into tidy tables and emission factors.

Inputs  data/raw/statcan_38100097_*.csv, data/raw/statcan_36100488_*.csv, data/reference/sector_crosswalk.csv
Outputs data/processed/ghg_by_industry.csv      year, code, industry, emissions_kt
        data/processed/output_by_industry.csv   year, code, industry, output_musd (millions of current CAD)
        data/processed/statcan_totals.csv       published totals and UNFCCC bridge items per year
        data/processed/emission_factors.csv     portfolio sector x year: emissions, output, tCO2e per $M
        data/processed/reconciliation.csv       sum of industry rows vs published total, per year
        reports/reconciliation.md
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import layout  # noqa: E402

RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
GHG_RAW = RAW / "statcan_38100097_ghg_by_industry_canada.csv"
OUTPUT_RAW = RAW / "statcan_36100488_output_by_industry_canada.csv"
CROSSWALK = ROOT / "data" / "reference" / "sector_crosswalk.csv"

TOTAL_ROWS = {
    "Total, industries": "total_industries_kt",
    "Total, households": "total_households_kt",
    "Total, industries and households": "total_industries_households_kt",
    "Total, United Nations Framework Convention on Climate Change (UNFCCC), Canada's submission": "unfccc_total_kt",
    "Total, Reconciliation with Canada's submission to the United Nations Framework Convention on Climate Change (UNFCCC)": "unfccc_reconciliation_kt",
}
CODE_RE = r"^(?P<industry>.*) \[(?P<code>[A-Z]{2}\w{5})\]$"


def split_code(labels: pd.Series) -> pd.DataFrame:
    return labels.str.extract(CODE_RE)


def load_ghg() -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = pd.read_csv(GHG_RAW)
    parts = split_code(raw["Sector"])
    rows = raw.assign(**parts).dropna(subset=["code", "VALUE"])
    ghg = pd.DataFrame({
        "year": rows["REF_DATE"].astype(int),
        "code": rows["code"],
        "industry": rows["industry"].str.replace(r"\s+", " ", regex=True),
        "emissions_kt": rows["VALUE"].astype(float),
    }).sort_values(["year", "code"]).reset_index(drop=True)

    totals = raw[raw["Sector"].isin(TOTAL_ROWS)].pivot(index="REF_DATE", columns="Sector", values="VALUE")
    totals = totals.rename(columns=TOTAL_ROWS)[list(TOTAL_ROWS.values())]
    balancing = raw[raw["Sector"].str.startswith("Balancing item")]
    totals = totals.join(balancing.pivot(index="REF_DATE", columns="Sector", values="VALUE"))
    totals.index = totals.index.astype(int)
    totals.index.name = "year"
    return ghg, totals.reset_index()


def load_output(codes: set[str]) -> tuple[pd.DataFrame, pd.Series]:
    raw = pd.read_csv(OUTPUT_RAW)
    total = raw[raw["Industry"] == "Total industries"].set_index("REF_DATE")["VALUE"]
    parts = split_code(raw["Industry"])
    rows = raw.assign(**parts).dropna(subset=["code", "VALUE"])
    rows = rows[rows["code"].isin(codes)]
    out = pd.DataFrame({
        "year": rows["REF_DATE"].astype(int),
        "code": rows["code"],
        "industry": rows["industry"],
        "output_musd": rows["VALUE"].astype(float),
    }).drop_duplicates(["year", "code"]).sort_values(["year", "code"]).reset_index(drop=True)
    total.index = total.index.astype(int)
    return out, total


def reconcile(ghg: pd.DataFrame, totals: pd.DataFrame) -> pd.DataFrame:
    sums = ghg.groupby("year")["emissions_kt"].agg(industry_rows_sum_kt="sum", industry_rows="count")
    rec = totals.set_index("year").join(sums)
    rec["difference_kt"] = rec["industry_rows_sum_kt"] - rec["total_industries_kt"]
    # Each published row is rounded to the nearest kilotonne, so the sum of n rows can drift by up to n/2 kt.
    rec["tolerance_kt"] = rec["industry_rows"] * 0.5
    rec["within_rounding"] = rec["difference_kt"].abs() <= rec["tolerance_kt"]
    rec["nir_gap_kt"] = rec["unfccc_total_kt"] - rec["total_industries_households_kt"]
    rec["bridge_residual_kt"] = rec["nir_gap_kt"] - rec["unfccc_reconciliation_kt"]
    return rec.reset_index()


def emission_factors(ghg: pd.DataFrame, output: pd.DataFrame, crosswalk: pd.DataFrame) -> pd.DataFrame:
    sector_of = crosswalk.set_index("statcan_code")["portfolio_sector"]
    em = ghg.assign(sector=ghg["code"].map(sector_of)).groupby(["sector", "year"])["emissions_kt"].sum()
    out = output.assign(sector=output["code"].map(sector_of)).groupby(["sector", "year"])["output_musd"].sum()
    idx = pd.MultiIndex.from_product([layout.SECTORS, layout.YEARS], names=["sector", "year"])
    ef = pd.DataFrame({"emissions_kt": em.reindex(idx).fillna(0.0), "output_musd": out.reindex(idx).fillna(0.0)})
    ef["ef_tco2e_per_musd"] = ef["emissions_kt"] * 1000.0 / ef["output_musd"]
    return ef.reset_index()


def write_report(rec: pd.DataFrame, output_cov: pd.DataFrame, path: Path) -> None:
    lines = [
        "# Reconciliation report: StatCan GHG physical flow account (table 38-10-0097-01)",
        "",
        "Generated by `scripts/build_data.py` from the pinned snapshot in `data/raw/`.",
        "",
        "## 1. Industry rows vs the published `Total, industries` row",
        "",
        "Every published industry row is rounded to the nearest kilotonne, so the sum of *n* rows may differ",
        "from the separately rounded total by up to *n*/2 kt. The check passes when |difference| <= that bound.",
        "",
        "| Year | Industry rows | Sum of rows (kt) | Published total (kt) | Difference (kt) | Tolerance (kt) | Result |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for r in rec.itertuples():
        lines.append(f"| {r.year} | {r.industry_rows} | {r.industry_rows_sum_kt:,.0f} | {r.total_industries_kt:,.0f} | "
                     f"{r.difference_kt:+,.0f} | {r.tolerance_kt:,.1f} | {'PASS' if r.within_rounding else 'FAIL'} |")
    lines += [
        "",
        f"All {len(rec)} years reconcile: **{bool(rec['within_rounding'].all())}**; largest absolute difference "
        f"{rec['difference_kt'].abs().max():.0f} kt.",
        "",
        "## 2. Gap to the National Inventory Report (UNFCCC submission)",
        "",
        "The physical flow account follows the System of National Accounts **residence** principle: it counts",
        "emissions of Canadian resident businesses and households wherever they occur (for example Canadian",
        "airlines and truckers abroad) and excludes non-residents operating in Canada. The National Inventory",
        "Report follows the UNFCCC **territorial** principle and also covers waste and some sources the account",
        "allocates differently. StatCan publishes the bridge items, reproduced below.",
        "",
        "| Year | Industries + households (kt) | NIR / UNFCCC total (kt) | Gap (kt) | Published bridge (kt) | Residual (kt) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for r in rec.itertuples():
        lines.append(f"| {r.year} | {r.total_industries_households_kt:,.0f} | {r.unfccc_total_kt:,.0f} | "
                     f"{r.nir_gap_kt:+,.0f} | {r.unfccc_reconciliation_kt:+,.0f} | {r.bridge_residual_kt:+,.0f} |")
    bal_cols = [c for c in rec.columns if c.startswith("Balancing item")]
    latest = rec.iloc[-1]
    lines += [
        "",
        f"Bridge items for {latest['year']} (kt CO2e; negative = in the account but not in the inventory):",
        "",
    ]
    for c in bal_cols:
        lines.append(f"- {c.replace('Balancing item: ', '')}: {latest[c]:+,.0f}")
    lines += [
        "",
        "Aviation and motor-fuel items are negative because resident carriers' fuel burned abroad is in the",
        "account but outside Canada's territorial inventory; waste and biomass items are positive because the",
        "inventory books them in categories the account does not attribute to industries the same way.",
        "",
        "## 3. Coverage of the output table (36-10-0488-01)",
        "",
        "| Year | Output matched to crosswalk ($M) | Published total output ($M) | Coverage |",
        "|---|---:|---:|---:|",
    ]
    for r in output_cov.itertuples():
        lines.append(f"| {r.year} | {r.matched:,.1f} | {r.total:,.1f} | {r.matched / r.total:.4%} |")
    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    crosswalk = pd.read_csv(CROSSWALK)
    ghg, totals = load_ghg()
    unmapped = set(ghg["code"]) - set(crosswalk["statcan_code"])
    if unmapped:
        raise SystemExit(f"crosswalk is missing StatCan codes: {sorted(unmapped)}")
    output, output_total = load_output(set(crosswalk["statcan_code"]))
    rec = reconcile(ghg, totals)
    ef = emission_factors(ghg, output, crosswalk)

    cov = output.groupby("year")["output_musd"].sum().rename("matched").to_frame().join(output_total.rename("total"))
    ghg.to_csv(PROCESSED / "ghg_by_industry.csv", index=False)
    output[output["year"].isin(layout.YEARS)].to_csv(PROCESSED / "output_by_industry.csv", index=False)
    totals.to_csv(PROCESSED / "statcan_totals.csv", index=False)
    ef.to_csv(PROCESSED / "emission_factors.csv", index=False)
    rec.to_csv(PROCESSED / "reconciliation.csv", index=False)
    (ROOT / "reports").mkdir(exist_ok=True)
    write_report(rec, cov.reset_index(), ROOT / "reports" / "reconciliation.md")
    print(f"reconciliation: {int(rec['within_rounding'].sum())}/{len(rec)} years within rounding")
    print(cov.assign(coverage=cov.matched / cov.total).tail(8).to_string())
    return 0 if rec["within_rounding"].all() else 1


if __name__ == "__main__":
    sys.exit(main())
