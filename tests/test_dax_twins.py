import pytest

import check_pbip
import dax_twins


@pytest.mark.parametrize("name", list(dax_twins.TWINS))
def test_twin_matches_workbook(name, recalculated, pbi_data):
    values = dax_twins.evaluate(name, pbi_data)
    assert values, f"{name} is not mapped to a workbook cell"
    for ref, expected in values.items():
        sheet, cell = ref.split("!")
        got = recalculated[sheet][cell].value
        assert got == pytest.approx(expected, rel=1e-6, abs=1e-6), ref


def test_every_measure_has_a_twin_and_back():
    assert check_pbip.twin_coverage_problems() == []


def test_measure_count_and_names():
    _, measures, _ = check_pbip.parse_model()
    assert 15 <= len(measures) <= 20
    assert set(measures) == set(dax_twins.TWINS)


def test_pbip_static_validation():
    assert check_pbip.static_problems() == []


def test_static_check_catches_unknown_column(monkeypatch):
    real = check_pbip.parse_model

    def broken():
        cols, measures, calc = real()
        measures = dict(measures, WACI="SUMX(Holdings, Holdings[NoSuchColumn])")
        return cols, measures, calc

    monkeypatch.setattr(check_pbip, "parse_model", broken)
    assert any("NoSuchColumn" in p for p in check_pbip.static_problems())


def test_value_check_catches_wrong_twin(recalculated, monkeypatch):
    twin = dax_twins.TWINS["WACI"]
    monkeypatch.setitem(dax_twins.TWINS, "WACI", dax_twins.Twin(lambda d, h, s, p: twin.func(d, h, s, p) * 1.01,
                                                              twin.total_cell, twin.sector_col))
    _, problems = check_pbip.value_problems(recalculated)
    assert any(p.startswith("WACI:") for p in problems)
