import pandas as pd
import pytest

import build_data
import layout
import make_portfolio

ROOT = build_data.ROOT


@pytest.fixture(scope="module")
def cleaned():
    crosswalk = pd.read_csv(build_data.CROSSWALK)
    ghg, totals = build_data.load_ghg()
    output, output_total = build_data.load_output(set(crosswalk.statcan_code))
    return crosswalk, ghg, totals, output, output_total


def test_snapshots_cover_expected_years(cleaned):
    _, ghg, totals, output, _ = cleaned
    assert ghg.year.min() == 2009 and ghg.year.max() >= 2023
    assert set(layout.YEARS) <= set(output.year)
    assert len(totals) == ghg.year.nunique()


def test_every_statcan_industry_code_is_mapped(cleaned):
    crosswalk, ghg, _, output, _ = cleaned
    assert set(ghg.code) <= set(crosswalk.statcan_code)
    assert set(crosswalk.portfolio_sector) - set(layout.SECTORS) <= {
        "Out of scope: owner-occupied dwellings", "Out of scope: fictive industries",
        "Out of scope: government and non-profit"}
    assert set(layout.SECTORS) <= set(crosswalk.portfolio_sector)


def test_industry_rows_reconcile_to_published_totals_every_year(cleaned):
    _, ghg, totals, _, _ = cleaned
    rec = build_data.reconcile(ghg, totals)
    assert rec.within_rounding.all()
    assert rec.difference_kt.abs().max() <= 10


def test_nir_bridge_explains_gap_within_rounding(cleaned):
    _, ghg, totals, _, _ = cleaned
    rec = build_data.reconcile(ghg, totals)
    assert (rec.nir_gap_kt < 0).all()                 # residence-basis account exceeds the territorial inventory
    assert rec.bridge_residual_kt.abs().max() <= 10   # published bridge items close the gap


def test_output_matched_codes_cover_total_output(cleaned):
    _, _, _, output, total = cleaned
    matched = output.groupby("year").output_musd.sum()
    for y in layout.YEARS:
        assert matched[y] == pytest.approx(total[y], rel=1e-5)


def test_emission_factor_traces_to_raw_rows(cleaned):
    crosswalk, ghg, _, output, _ = cleaned
    ef = build_data.emission_factors(ghg, output, crosswalk).set_index(["sector", "year"])
    raw_ghg = pd.read_csv(build_data.GHG_RAW)
    raw_out = pd.read_csv(build_data.OUTPUT_RAW)
    kt = raw_ghg.loc[(raw_ghg.REF_DATE == 2022) & raw_ghg.Sector.str.endswith("[BS22110]"), "VALUE"].item()
    musd = raw_out.loc[(raw_out.REF_DATE == 2022) & raw_out.Industry.str.endswith("[BS22110]"), "VALUE"].item()
    assert ef.loc[("Electric Utilities", 2022), "ef_tco2e_per_musd"] == pytest.approx(kt * 1000 / musd)
    assert (ef.ef_tco2e_per_musd > 0).all()
    assert ef.xs(2022, level="year").ef_tco2e_per_musd.idxmax() == "Electric Utilities"


def test_synthetic_book_shape_and_labels():
    df = make_portfolio.build()
    assert len(df) == make_portfolio.N_HOLDINGS
    assert df.outstanding_mcad.sum() == pytest.approx(make_portfolio.BOOK_TOTAL_MCAD, abs=1e-6)
    assert set(df.sector) == set(layout.SECTORS)
    assert df.issuer.str.startswith("SYN ").all()
    assert (df.outstanding_mcad > 0).all() and (df.evic_mcad > df.outstanding_mcad).all()
    assert df.holding_id.is_unique


def test_synthetic_book_is_seeded_and_matches_committed_file():
    a, b = make_portfolio.build(), make_portfolio.build()
    pd.testing.assert_frame_equal(a, b)
    committed = pd.read_csv(ROOT / "data" / "processed" / "holdings_synthetic.csv")
    pd.testing.assert_frame_equal(a.reset_index(drop=True), committed, check_dtype=False)
