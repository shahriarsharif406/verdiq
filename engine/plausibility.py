"""R05 - physical plausibility: issued tCO2 per hectare per year versus a methodology ceiling.

ASSUMPTIONS (documented, deliberately generous so honest projects never trip the rule; values are
order-of-magnitude figures from public literature, rounded up - not authoritative standards):
  mangrove restoration (tidal wetland): 25 tCO2e/ha/yr  (fast-growing mangrove incl. soil carbon, upper range)
  REDD+ avoided deforestation:          30 tCO2e/ha/yr  (avoided emissions on intact tropical forest)
  afforestation/reforestation (ARR):    40 tCO2e/ha/yr  (fast-growing plantations, upper range)
  rice methane reduction:                8 tCO2e/ha/yr
  cookstoves: not area-based -> no ceiling (checked by other rules)
"""
from __future__ import annotations

import pandas as pd

from .common import make_flag

CEILING_TCO2_HA_YR = {
    "VM0033 Tidal Wetland Restoration": 25.0,
    "VM0007 REDD+ Avoided Deforestation": 30.0,
    "AR-ACM0003 Afforestation/Reforestation": 40.0,
    "VM0042 Rice Methane Reduction": 8.0,
    "GS-TPDDTEC Improved Cookstoves": None,
}


def yield_table(issuances: pd.DataFrame) -> pd.DataFrame:
    df = issuances.copy()
    df["tco2_per_ha"] = df.issued_tco2 / df.area_ha
    df["ceiling"] = df.methodology.map(CEILING_TCO2_HA_YR)
    df["ratio_to_ceiling"] = df.tco2_per_ha / df.ceiling
    return df[["issuance_id", "project_id", "project_name", "vintage_year", "methodology", "issued_tco2", "area_ha",
               "tco2_per_ha", "ceiling", "ratio_to_ceiling", "serial_start", "serial_end"]]


def plausibility_flags(issuances: pd.DataFrame) -> list:
    flags = []
    yt = yield_table(issuances)
    for r in yt[yt.ratio_to_ceiling > 1.0].itertuples():
        flags.append(make_flag(
            "R05", "issuance", r.issuance_id,
            f"{r.issued_tco2:,} tCO2 issued for {r.area_ha:,.0f} ha = {r.tco2_per_ha:,.0f} tCO2/ha/yr, "
            f"{r.ratio_to_ceiling:.1f}x the physical ceiling ({r.ceiling:.0f}) for {r.methodology}.",
            project_id=r.project_id, serial_start=int(r.serial_start), serial_end=int(r.serial_end), tco2=r.issued_tco2,
            evidence=[dict(area_ha=r.area_ha, issued_tco2=r.issued_tco2, tco2_per_ha=round(r.tco2_per_ha, 1), ceiling=r.ceiling)]))
    return flags
