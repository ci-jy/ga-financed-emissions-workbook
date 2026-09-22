# Workbook tabs and results

## Tabs

Yellow cells on the Inputs tab are the only values meant to be edited. Everything on the derived tabs is a formula.

- Summary: headline B-15 metrics, top-5 sectors (`LARGE` + `INDEX/MATCH`), headline-year scenario costs, reconciliation flag.
- Inputs: reporting year, stated book total, headline year, price paths, free-allocation shares, revenue/EVIC proxies.
- Emission Factors: sector x year emissions, output and EF (`SUMIFS`), plus the reporting-year lookup table.
- Crosswalk: StatCan code to portfolio sector.
- Holdings: 300 synthetic holdings with sector, instrument, rating, outstanding, EVIC and revenue (blank means not on file).
- Financed Emissions: per-holding attribution (`XLOOKUP`, `VLOOKUP`, `ISBLANK`), PCAF score, and a sector roll-up (`COUNTIF`, `SUMIFS`, `SUMPRODUCT`).
- WACI: sector weights x EF, sector and holding-level WACI, carbon footprint.
- Benchmark Comparison: portfolio vs output-weighted benchmark, active weights, allocation effect.
- Carbon Price Scenarios: effective price, cost ($M) and cost as % of holdings by scenario and year, plus sector costs in the headline year.
- Reconciliation: industry rows vs published totals per year, gap to the NIR and the published bridge.
- StatCan GHG, StatCan Output, StatCan Totals: raw source rows, each with a `VLOOKUP` sector mapping.

## Results (reporting year 2022, synthetic book)

- Book: $12,000M CAD, 300 holdings, 22 sectors
- Financed emissions: 1,462,139 tCO2e
- Carbon footprint: 121.8 tCO2e per $M invested
- WACI: 274.2 vs 148.5 tCO2e per $M revenue for the benchmark (+85%)
- Weighted PCAF data-quality score: 4.71, with 71% of the book at score 5
- Portfolio sectors' share of StatCan industry emissions: 96.6%

Top sectors by financed emissions:

| Sector | tCO2e | Share | Share of book |
|---|---:|---:|---:|
| Electric Utilities | 359,168 | 24.6% | 10.0% |
| Oil & Gas Producers | 250,530 | 17.1% | 6.0% |
| Pipelines | 145,664 | 10.0% | 7.0% |
| Agriculture & Food | 111,194 | 7.6% | 3.0% |
| Airlines | 110,178 | 7.5% | 1.5% |

2030 carbon cost:

| Scenario | Carbon cost ($M CAD) | Share of holdings |
|---|---:|---:|
| Current federal policy | 49.7 | 0.41% |
| Net-zero shadow price | 219.3 | 1.83% |
| Delayed transition | 76.0 | 0.63% |
