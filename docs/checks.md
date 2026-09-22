# Tests and verification

```bash
.venv/bin/python -m pytest -q                  # 43 tests
.venv/bin/python scripts/verify_workbook.py    # every formula cell vs pandas after LibreOffice recalculation
.venv/bin/python scripts/check_pbip.py         # PBIP text validation + each DAX measure's pandas twin vs the workbook
```

## What the tests cover

- `tests/test_data.py`: snapshot coverage, every StatCan code mapped, per-year reconciliation, NIR bridge, output coverage, an emission factor traced back to the raw rows, and the synthetic book's shape and seeding.
- `tests/test_workbook.py`: every formula cell matches pandas, no hard-coded numbers on derived tabs, scenario and reporting-year inputs flow through after recalculation and the edited workbook still verifies, and the verifier catches a tampered formula and a formula cell with no pandas value.
- `tests/test_dax_twins.py`: one test per DAX measure (twin vs workbook in each filter context), every measure has a twin and every twin has a measure, table, column and measure references in the DAX and report pages resolve, plus negative checks for a wrong twin and an unknown column.
- `tests/test_briefing.py`: the briefing reports the model's headline numbers and the committed copy is current.

## How verification works

`build_workbook.py` writes formulas only. `twin.py` recomputes from the CSVs with pandas without reading any formula, and it reads assumptions from the Inputs tab, so an edited workbook can be re-verified as it stands.

`verify_workbook.py` runs `soffice --headless --convert-to xlsx`. The file is saved with `fullCalcOnLoad`, so LibreOffice recalculates on load and writes cached values that openpyxl can read. It uses a private profile under `$TMPDIR` and leaves nothing running. Formula cells and pandas values must match one-to-one (tolerance 1e-6).

## Power BI project

`powerbi/` is a PBIP project with a TMDL semantic model (three tables, a relationship, two calculated columns and 18 measures) and three report pages: emissions by sector, WACI vs benchmark, and scenario carbon-cost exposure. `scripts/export_powerbi_data.py` writes its CSV extracts to `powerbi/data/`.

It is validated as text only. Each measure has a pandas twin in `scripts/dax_twins.py`, evaluated in the contexts the report uses (total, per sector, per scenario-year) and compared with the workbook cell for the same metric.

To open it in Power BI Desktop, set the `DataFolder` parameter to the absolute path of `powerbi/data/`.
