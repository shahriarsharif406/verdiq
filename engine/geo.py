"""R04 - project polygon overlap (two projects cannot both be paid for the same land)."""
from __future__ import annotations

import math
from itertools import combinations

import pandas as pd
from shapely import wkt
from shapely.ops import transform

from .common import make_flag

MIN_OVERLAP_SHARE = 0.05   # overlap must cover >5% of the smaller polygon to be flagged


def _to_km(geom):
    lat0 = geom.centroid.y
    kx, ky = 111.32 * math.cos(math.radians(lat0)), 110.57
    return transform(lambda x, y, z=None: (x * kx, y * ky), geom)


def project_polygons(issuances: pd.DataFrame) -> dict:
    out = {}
    for r in issuances.drop_duplicates("project_id").itertuples():
        out[r.project_id] = (r.project_name, wkt.loads(r.polygon_wkt))
    return out


def overlap_table(issuances: pd.DataFrame) -> pd.DataFrame:
    polys = project_polygons(issuances)
    rows = []
    for (a, (na, ga)), (b, (nb, gb)) in combinations(polys.items(), 2):
        if not ga.intersects(gb):
            continue
        inter = _to_km(ga.intersection(gb))
        if inter.is_empty:
            continue
        ha = inter.area * 100
        small = min(_to_km(ga).area, _to_km(gb).area) * 100
        rows.append(dict(project_a=a, project_b=b, name_a=na, name_b=nb, overlap_ha=round(ha, 1),
                         share_of_smaller=round(ha / small, 3)))
    return pd.DataFrame(rows, columns=["project_a", "project_b", "name_a", "name_b", "overlap_ha", "share_of_smaller"])


def geo_flags(issuances: pd.DataFrame) -> list:
    flags = []
    ov = overlap_table(issuances)
    for r in ov[ov.share_of_smaller > MIN_OVERLAP_SHARE].itertuples():
        for me, other, oname in ((r.project_a, r.project_b, r.name_b), (r.project_b, r.project_a, r.name_a)):
            iss = issuances[issuances.project_id == me]
            ranges = [(int(x.serial_start), int(x.serial_end)) for x in iss.itertuples()]
            ev = [dict(project=other, name=oname, overlap_ha=r.overlap_ha, share_of_smaller_polygon=r.share_of_smaller)]
            flags.append(make_flag(
                "R04", "project", me,
                f"Polygon overlaps {other} ({oname}) by {r.overlap_ha:,.0f} ha ({r.share_of_smaller:.0%} of the smaller project): "
                "the same land is being credited twice.",
                project_id=me, tco2=int(iss.issued_tco2.sum()), evidence=ev, ranges=ranges))
    return flags
