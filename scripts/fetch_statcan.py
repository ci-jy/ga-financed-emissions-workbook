"""Download the Statistics Canada tables used by the workbook and pin Canada-level snapshots.

Tables (open data, no key):
  38-10-0097-01  Physical flow account for greenhouse gas emissions (kilotonnes CO2e), by industry
  36-10-0488-01  Output, by sector and industry (millions of current dollars), same IOIC industry codes

Full-table zips are downloaded into a temporary directory; only the GEO == "Canada" rows are
kept and written to data/raw/ so the rest of the build runs offline from committed snapshots.
"""
from __future__ import annotations

import argparse
import io
import os
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
URL = "https://www150.statcan.gc.ca/n1/tbl/csv/{pid}-eng.zip"

TABLES = {
    "38100097": "statcan_38100097_ghg_by_industry_canada.csv",
    "36100488": "statcan_36100488_output_by_industry_canada.csv",
}
KEEP = ["REF_DATE", "GEO", "Sector", "Industry", "UOM", "SCALAR_FACTOR", "VECTOR", "VALUE", "STATUS"]


def download(pid: str, workdir: Path) -> Path:
    target = workdir / f"{pid}-eng.zip"
    with urllib.request.urlopen(URL.format(pid=pid), timeout=300) as resp, open(target, "wb") as fh:
        while chunk := resp.read(1 << 20):
            fh.write(chunk)
    return target


def extract_canada(zip_path: Path, pid: str) -> pd.DataFrame:
    with zipfile.ZipFile(zip_path) as zf, zf.open(f"{pid}.csv") as fh:
        frames = []
        for chunk in pd.read_csv(io.TextIOWrapper(fh, encoding="utf-8-sig"), chunksize=200_000, low_memory=False):
            frames.append(chunk[chunk["GEO"] == "Canada"])
    df = pd.concat(frames, ignore_index=True)
    return df[[c for c in KEEP if c in df.columns]]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=RAW, help="directory for the pinned snapshots")
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as tmp:
        for pid, name in TABLES.items():
            print(f"downloading table {pid} ...", flush=True)
            df = extract_canada(download(pid, Path(tmp)), pid)
            df.to_csv(args.out / name, index=False)
            print(f"  wrote {args.out / name} ({len(df)} rows, {df.REF_DATE.min()}-{df.REF_DATE.max()})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
