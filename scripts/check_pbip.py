"""Validate the Power BI PBIP project as text and check every DAX measure against its pandas twin.

Checks: JSON artifacts parse; every TMDL table/column/measure reference in DAX and in the report pages
resolves; every measure has a twin in scripts/dax_twins.py (and vice versa); every twin is exercised by
tests/test_dax_twins.py; and each twin's values match the LibreOffice-recalculated workbook within 1e-6.
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import dax_twins  # noqa: E402

PBIP = ROOT / "powerbi"
MODEL = PBIP / "GAFinancedEmissions.SemanticModel" / "definition"
TOL = 1e-6

TABLE_RE = re.compile(r"^table\s+('?)(.+?)\1\s*$")
COLUMN_RE = re.compile(r"^\tcolumn\s+('?)([^'=]+?)\1\s*(=\s*(.+))?$")
MEASURE_RE = re.compile(r"^\tmeasure\s+('?)([^'=]+?)\1\s*=\s*(.+)$")
COLREF_RE = re.compile(r"('?)([A-Za-z][\w ]*)\1\[([^\]]+)\]")
MEASREF_RE = re.compile(r"(?<![\w'\]])\[([^\]]+)\]")


def parse_model() -> tuple[dict[str, set[str]], dict[str, str], dict[str, str]]:
    columns: dict[str, set[str]] = {}
    measures: dict[str, str] = {}
    calc_columns: dict[str, str] = {}
    for path in sorted((MODEL / "tables").glob("*.tmdl")):
        table = None
        for line in path.read_text().splitlines():
            if m := TABLE_RE.match(line):
                table = m.group(2)
                columns.setdefault(table, set())
            elif m := COLUMN_RE.match(line):
                columns[table].add(m.group(2).strip())
                if m.group(4):
                    calc_columns[f"{table}[{m.group(2).strip()}]"] = m.group(4)
            elif m := MEASURE_RE.match(line):
                measures[m.group(2).strip()] = m.group(3).strip()
    return columns, measures, calc_columns


def static_problems() -> list[str]:
    problems: list[str] = []
    for p in [PBIP / "GAFinancedEmissions.pbip", MODEL.parent / "definition.pbism",
              PBIP / "GAFinancedEmissions.Report" / "definition.pbir", PBIP / "GAFinancedEmissions.Report" / "report.json"]:
        try:
            json.loads(p.read_text())
        except (OSError, ValueError) as exc:
            problems.append(f"{p.relative_to(ROOT)}: {exc}")
    columns, measures, calc = parse_model()
    model_text = (MODEL / "model.tmdl").read_text()
    for table in columns:
        if f"ref table {table}" not in model_text:
            problems.append(f"model.tmdl does not reference table {table}")
    for rel in re.findall(r"(?:from|to)Column:\s*(\w+)\.(\w+)", (MODEL / "relationships.tmdl").read_text()):
        if rel[1] not in columns.get(rel[0], set()):
            problems.append(f"relationship column {rel[0]}.{rel[1]} does not exist")
    for name, expr in {**measures, **calc}.items():
        for _, table, col in COLREF_RE.findall(expr):
            if col not in columns.get(table.strip(), set()):
                problems.append(f"{name}: unknown column {table}[{col}]")
        stripped = COLREF_RE.sub("", expr)
        for ref in MEASREF_RE.findall(stripped):
            if ref not in measures:
                problems.append(f"{name}: unknown measure [{ref}]")
        if expr.count("(") != expr.count(")"):
            problems.append(f"{name}: unbalanced parentheses")
    report = json.loads((PBIP / "GAFinancedEmissions.Report" / "report.json").read_text())
    pages = [s["displayName"] for s in report["sections"]]
    for section in report["sections"]:
        for vc in section["visualContainers"]:
            for sel in json.loads(vc["config"])["singleVisual"]["prototypeQuery"]["Select"]:
                kind = "Measure" if "Measure" in sel else "Column"
                table, prop = sel[kind]["Expression"]["SourceRef"]["Entity"], sel[kind]["Property"]
                ok = prop in measures if kind == "Measure" else prop in columns.get(table, set())
                if not ok:
                    problems.append(f"report page {section['displayName']!r}: unknown {kind.lower()} {table}.{prop}")
    if len(pages) < 3:
        problems.append(f"expected 3 report pages, found {pages}")
    return problems


def twin_coverage_problems() -> list[str]:
    _, measures, _ = parse_model()
    problems = [f"measure {m!r} has no pandas twin" for m in measures if m not in dax_twins.TWINS]
    problems += [f"twin {t!r} has no DAX measure" for t in dax_twins.TWINS if t not in measures]
    tests = (ROOT / "tests" / "test_dax_twins.py").read_text()
    if "dax_twins.TWINS" not in tests:
        problems.append("tests/test_dax_twins.py does not parametrize over dax_twins.TWINS")
    return problems


def value_problems(recalculated: openpyxl.Workbook) -> tuple[int, list[str]]:
    data = dax_twins.load()
    problems, checked = [], 0
    for name in dax_twins.TWINS:
        values = dax_twins.evaluate(name, data)
        if not values:
            problems.append(f"twin {name!r} is not mapped to any workbook cell")
        for ref, expected in values.items():
            sheet, cell = ref.split("!")
            got = recalculated[sheet][cell].value
            checked += 1
            if got is None or abs(float(got) - expected) > TOL * max(1.0, abs(expected)):
                problems.append(f"{name}: {ref} workbook={got!r} twin={expected!r}")
    return checked, problems


def main() -> int:
    from verify_workbook import recalculate

    problems = static_problems() + twin_coverage_problems()
    _, measures, _ = parse_model()
    with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as tmp:
        wb = openpyxl.load_workbook(recalculate(ROOT / "financed_emissions.xlsx", Path(tmp)), data_only=True)
    checked, vp = value_problems(wb)
    problems += vp
    print(f"{len(measures)} DAX measures, {len(dax_twins.TWINS)} pandas twins, {checked} twin values checked")
    for p in problems:
        print("  " + p)
    print("PASS" if not problems else "FAIL")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
