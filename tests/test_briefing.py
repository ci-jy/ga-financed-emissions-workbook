from pathlib import Path

import make_briefing
import twin
from conftest import WORKBOOK

ROOT = Path(__file__).resolve().parents[1]


def test_briefing_reports_headline_metrics_from_the_model():
    m = twin.compute(WORKBOOK)
    text = make_briefing.briefing(m)
    x = m.metrics
    assert f"{x['financed_emissions']:,.0f} tCO2e" in text
    assert f"{x['waci']:,.1f}" in text and f"{x['benchmark_waci']:,.1f}" in text
    for s in m.inputs.prices.index:
        assert f"{x[f'carbon_cost_share::{s}']:.2%}" in text
    for s in m.sectors.fe.sort_values(ascending=False).head(5).index:
        assert f"| {s} |" in text
    assert "Data-quality caveats" in text


def test_committed_briefing_is_current():
    m = twin.compute(WORKBOOK)
    assert (ROOT / "reports" / "briefing.md").read_text() == make_briefing.briefing(m)


def test_briefing_fits_two_pages():
    words = len((ROOT / "reports" / "briefing.md").read_text().split())
    assert words < 1100
