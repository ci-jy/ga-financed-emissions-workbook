"""Write the 2-page analyst briefing (reports/briefing.md) and the overview figure (docs/overview.png).

All numbers come from the pandas twin, which tests prove equal to the recalculated workbook.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import twin  # noqa: E402

WORKBOOK = ROOT / "financed_emissions.xlsx"


def figure(m: twin.Model, path: Path) -> None:
    sec = m.sectors
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.2), gridspec_kw={"width_ratios": [1.25, 1.25, 0.9]})
    top = sec.fe.sort_values().tail(10) / 1000
    axes[0].barh(top.index, top.values, color="#1F4E78")
    axes[0].set_title("Financed emissions by sector (kt CO2e)")
    for y, v in enumerate(top.values):
        axes[0].text(v, y, f" {v:,.0f}", va="center", fontsize=8)

    w = sec.sort_values("waci_contrib").tail(10)
    ypos = range(len(w))
    axes[1].barh([y + 0.2 for y in ypos], w.waci_contrib, height=0.4, color="#1F4E78", label="Portfolio")
    axes[1].barh([y - 0.2 for y in ypos], w.bench_contrib, height=0.4, color="#A6A6A6", label="Benchmark")
    axes[1].set_yticks(list(ypos), w.index)
    axes[1].set_title(f"WACI contribution (t/$M revenue)\nportfolio {m.metrics['waci']:,.0f} vs "
                      f"benchmark {m.metrics['benchmark_waci']:,.0f}")
    axes[1].legend(loc="lower right")

    sc = m.scenario_cost.div(m.metrics["book_value"]) * 100
    for name, row in sc.iterrows():
        axes[2].plot(row.index, row.values, marker="o", label=name)
    axes[2].set_title("Carbon cost as % of holdings")
    axes[2].set_ylabel("% of book value")
    axes[2].legend(fontsize=8)
    axes[2].grid(alpha=0.3)
    fig.suptitle("Synthetic Canadian insurer general account: PCAF financed emissions, WACI and carbon-price stress "
                 f"(StatCan {m.inputs.reporting_year} emission factors)", fontsize=11)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=110)
    plt.close(fig)


def briefing(m: twin.Model) -> str:
    x, inp = m.metrics, m.inputs
    sec = m.sectors
    top5 = sec.sort_values("fe", ascending=False).head(5)
    hy = inp.headline_year
    lines = [
        "# Climate metrics briefing: general account corporate bond book",
        "",
        f"*Investment and Risk Committee pre-read. Reporting year {inp.reporting_year} emission factors; "
        f"portfolio is a **synthetic** ${x['book_value']:,.0f}M CAD book of {x['holdings']} holdings across "
        f"{len(sec)} sectors.*",
        "",
        "## Headline metrics (OSFI B-15 style)",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Financed emissions (PCAF; investees' direct Scope 1) | **{x['financed_emissions']:,.0f} tCO2e** |",
        f"| Carbon footprint | {x['carbon_footprint']:,.1f} tCO2e per $M invested |",
        f"| WACI, portfolio | {x['waci']:,.1f} tCO2e per $M revenue |",
        f"| WACI, economy-weighted benchmark | {x['benchmark_waci']:,.1f} tCO2e per $M revenue |",
        f"| Portfolio vs benchmark | **{x['waci_vs_benchmark']:+.0%}** |",
        f"| Weighted PCAF data-quality score | {x['dq_weighted']:.2f} (1 = best, 5 = worst) |",
        "",
        "## 1. Five sectors drive most financed emissions",
        "",
        "| Sector | Financed emissions (tCO2e) | Share | Share of book | Sector EF (t/$M) |",
        "|---|---:|---:|---:|---:|",
    ]
    for s, r in top5.iterrows():
        lines.append(f"| {s} | {r.fe:,.0f} | {r.fe_share:.1%} | {r.weight:.1%} | {r.ef:,.0f} |")
    lines += [
        "",
        f"These five sectors hold {top5.weight.sum():.0%} of the book but account for "
        f"{top5.fe_share.sum():.0%} of financed emissions. Electricity, upstream oil and gas and pipelines "
        "are the classic infrastructure-style credits an insurer buys for long duration, so the concentration "
        "is structural rather than a stock-picking outcome.",
        "",
        "## 2. WACI vs benchmark",
        "",
        f"Portfolio WACI is {x['waci']:,.1f} t/$M revenue against {x['benchmark_waci']:,.1f} for a benchmark "
        f"weighted by each sector's share of Canadian gross output, a gap of {x['waci_vs_benchmark']:+.0%}. "
        "The largest allocation effects come from overweights in sectors above the benchmark intensity and "
        "underweights in sectors below it:",
        "",
        "| Sector | Portfolio weight | Benchmark weight | Allocation effect (t/$M) |",
        "|---|---:|---:|---:|",
    ]
    for s, r in sec.sort_values("allocation", ascending=False).head(4).iterrows():
        lines.append(f"| {s} | {r.weight:.1%} | {r.bench_weight:.1%} | {r.allocation:+,.1f} |")
    lines += [
        "",
        "Services and construction are large in the economy but small in a bond book, so underweighting "
        "them raises portfolio WACI even though those sectors are low-emitting.",
        "",
        f"## 3. Carbon-cost exposure by scenario ({hy})",
        "",
        "Cost = financed emissions x carbon price x (1 - free allocation share), on today's balance sheet.",
        "",
        "| Scenario | Price ($/t) | Free allocation | Carbon cost ($M CAD) | Share of holdings |",
        "|---|---:|---:|---:|---:|",
    ]
    for s in inp.prices.index:
        lines.append(f"| {s} | {inp.prices.at[s, hy]:,.0f} | {inp.free_share[s]:.0%} | "
                     f"{x[f'carbon_cost::{s}']:,.1f} | {x[f'carbon_cost_share::{s}']:.2%} |")
    worst = max(inp.prices.index, key=lambda s: x[f"carbon_cost::{s}"])
    sc_sec = m.sector_cost[worst].sort_values(ascending=False).head(3)
    lines += [
        "",
        f"Under the {worst.lower()} scenario the three most exposed sectors are "
        + ", ".join(f"{s} (${v:,.1f}M, {v / sec.at[s, 'outstanding']:.1%} of sector holdings)" for s, v in sc_sec.items())
        + ". Sector-level cost relative to holdings is the better early-warning signal than the book-wide share.",
        "",
        "## 4. Data-quality caveats",
        "",
        f"- **PCAF score {x['dq_weighted']:.1f}.** No issuer-reported emissions are used; {x['dq5_share']:.0%} of the "
        "book also lacks issuer revenue and uses a sector revenue/EVIC proxy (score 5). Scores 4-5 carry wide "
        "error bands; issuer CDP or sustainability-report data would move the score toward 1-2.",
        "- **Sector-average factors.** Emission factors are StatCan industry totals divided by gross output, "
        "so every issuer in a sector looks the same: a hydro utility and a coal utility get the same intensity.",
        "- **Residence basis.** The physical flow account (38-10-0097-01) counts resident businesses' "
        "emissions wherever they occur; it differs from the National Inventory Report by a published bridge "
        "(see `reports/reconciliation.md`). Industry rows reconcile to published totals in every year.",
        f"- **Coverage.** Portfolio sectors cover {x['coverage']:.1%} of StatCan industry emissions in "
        f"{inp.reporting_year}; government, non-profit and owner-occupied dwellings are out of scope, and "
        "sovereign and provincial bonds are not in this book.",
        "- **Static stress.** Carbon costs apply future prices to today's emissions; no decarbonisation, "
        "pass-through or credit-spread response is modelled.",
        "- **Synthetic book.** Holdings, EVIC and revenues are seeded synthetic data with no real issuers.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    m = twin.compute(WORKBOOK)
    figure(m, ROOT / "docs" / "overview.png")
    (ROOT / "reports" / "briefing.md").write_text(briefing(m))
    print("wrote docs/overview.png and reports/briefing.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
