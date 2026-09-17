import os
import sys
import tempfile
from pathlib import Path

import openpyxl
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import dax_twins  # noqa: E402
import verify_workbook  # noqa: E402

WORKBOOK = ROOT / "financed_emissions.xlsx"


@pytest.fixture(scope="session")
def workdir():
    with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as tmp:
        yield Path(tmp)


@pytest.fixture(scope="session")
def recalculated(workdir):
    return openpyxl.load_workbook(verify_workbook.recalculate(WORKBOOK, workdir / "base"), data_only=True)


@pytest.fixture(scope="session")
def pbi_data():
    return dax_twins.load()
