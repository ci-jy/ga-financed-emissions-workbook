# Climate metrics briefing: general account corporate bond book

*Investment and Risk Committee pre-read. Reporting year 2022 emission factors; portfolio is a **synthetic** $12,000M CAD book of 300 holdings across 22 sectors.*

## Headline metrics (OSFI B-15 style)

| Metric | Value |
|---|---:|
| Financed emissions (PCAF; investees' direct Scope 1) | **1,462,139 tCO2e** |
| Carbon footprint | 121.8 tCO2e per $M invested |
| WACI, portfolio | 274.2 tCO2e per $M revenue |
| WACI, economy-weighted benchmark | 148.5 tCO2e per $M revenue |
| Portfolio vs benchmark | **+85%** |
| Weighted PCAF data-quality score | 4.71 (1 = best, 5 = worst) |

## 1. Five sectors drive most financed emissions

| Sector | Financed emissions (tCO2e) | Share | Share of book | Sector EF (t/$M) |
|---|---:|---:|---:|---:|
| Electric Utilities | 359,168 | 24.6% | 10.0% | 1,028 |
| Oil & Gas Producers | 250,530 | 17.1% | 6.0% | 624 |
| Pipelines | 145,664 | 10.0% | 7.0% | 665 |
| Agriculture & Food | 111,194 | 7.6% | 3.0% | 280 |
| Airlines | 110,178 | 7.5% | 1.5% | 680 |

These five sectors hold 28% of the book but account for 67% of financed emissions. Electricity, upstream oil and gas and pipelines are the classic infrastructure-style credits an insurer buys for long duration, so the concentration is structural rather than a stock-picking outcome.

## 2. WACI vs benchmark

Portfolio WACI is 274.2 t/$M revenue against 148.5 for a benchmark weighted by each sector's share of Canadian gross output, a gap of +85%. The largest allocation effects come from overweights in sectors above the benchmark intensity and underweights in sectors below it:

| Sector | Portfolio weight | Benchmark weight | Allocation effect (t/$M) |
|---|---:|---:|---:|
| Electric Utilities | 10.0% | 1.4% | +75.4 |
| Pipelines | 7.0% | 0.4% | +34.1 |
| Business & Consumer Services | 6.0% | 18.1% | +15.6 |
| Construction | 3.0% | 11.3% | +10.9 |

Services and construction are large in the economy but small in a bond book, so underweighting them raises portfolio WACI even though those sectors are low-emitting.

## 3. Carbon-cost exposure by scenario (2030)

Cost = financed emissions x carbon price x (1 - free allocation share), on today's balance sheet.

| Scenario | Price ($/t) | Free allocation | Carbon cost ($M CAD) | Share of holdings |
|---|---:|---:|---:|---:|
| Current federal policy | 170 | 80% | 49.7 | 0.41% |
| Net-zero shadow price | 300 | 50% | 219.3 | 1.83% |
| Delayed transition | 260 | 80% | 76.0 | 0.63% |

Under the net-zero shadow price scenario the three most exposed sectors are Electric Utilities ($53.9M, 4.5% of sector holdings), Oil & Gas Producers ($37.6M, 5.2% of sector holdings), Pipelines ($21.8M, 2.6% of sector holdings). Sector-level cost relative to holdings is the better early-warning signal than the book-wide share.

## 4. Data-quality caveats

- **PCAF score 4.7.** No issuer-reported emissions are used; 71% of the book also lacks issuer revenue and uses a sector revenue/EVIC proxy (score 5). Scores 4-5 carry wide error bands; issuer CDP or sustainability-report data would move the score toward 1-2.
- **Sector-average factors.** Emission factors are StatCan industry totals divided by gross output, so every issuer in a sector looks the same: a hydro utility and a coal utility get the same intensity.
- **Residence basis.** The physical flow account (38-10-0097-01) counts resident businesses' emissions wherever they occur; it differs from the National Inventory Report by a published bridge (see `reports/reconciliation.md`). Industry rows reconcile to published totals in every year.
- **Coverage.** Portfolio sectors cover 96.6% of StatCan industry emissions in 2022; government, non-profit and owner-occupied dwellings are out of scope, and sovereign and provincial bonds are not in this book.
- **Static stress.** Carbon costs apply future prices to today's emissions; no decarbonisation, pass-through or credit-spread response is modelled.
- **Synthetic book.** Holdings, EVIC and revenues are seeded synthetic data with no real issuers.
