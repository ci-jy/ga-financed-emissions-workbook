"""Rebuild everything offline from the pinned StatCan snapshots in data/raw/.

  1. clean StatCan tables, emission factors, reconciliation report
  2. synthetic general-account book
  3. financed_emissions.xlsx (live formulas)
  4. Power BI PBIP data extracts
  5. figure and analyst briefing
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STEPS = ["build_data.py", "make_portfolio.py", "build_workbook.py", "export_powerbi_data.py", "make_briefing.py"]


def main() -> int:
    for step in STEPS:
        print(f"==> {step}", flush=True)
        subprocess.run([sys.executable, str(ROOT / "scripts" / step)], check=True, cwd=ROOT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
