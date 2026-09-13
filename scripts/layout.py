"""Shared constants: sheet names, sector order and year ranges used by the workbook and its pandas twin."""
from __future__ import annotations

SECTORS = [
    "Oil & Gas Producers",
    "Petroleum Refining",
    "Pipelines",
    "Electric Utilities",
    "Gas Distribution & Water",
    "Mining & Quarrying",
    "Cement & Building Materials",
    "Metals & Steel",
    "Chemicals & Plastics",
    "Forest & Paper Products",
    "Agriculture & Food",
    "Airlines",
    "Rail",
    "Trucking, Marine & Logistics",
    "Construction",
    "Autos & Transport Equipment",
    "Industrial & Tech Manufacturing",
    "Retail & Wholesale",
    "Telecom & Media",
    "Banks & Insurance",
    "Real Estate",
    "Business & Consumer Services",
]
# Years where both the GHG account and the output table are published.
YEARS = list(range(2009, 2023))
SCENARIO_YEARS = list(range(2024, 2031))
SCENARIOS = ["Current federal policy", "Net-zero shadow price", "Delayed transition"]
