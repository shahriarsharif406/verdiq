"""Synthetic data generator for VERDIQ.

Everything produced here is SYNTHETIC. Company, broker and project names are fictional
(project locations are real regions, but no real registry data is used).
Fixed seed => byte-identical output on every run.
"""
from __future__ import annotations

import json
import math
import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

SEED = 42
OUT = Path(__file__).parent
BLOCK = 2_000_000          # serial block per project: project k owns [k*BLOCK, (k+1)*BLOCK)
VINTAGE_STRIDE = 500_000

METHODOLOGIES = {
    "VM0033 Tidal Wetland Restoration": "mangrove",
    "VM0007 REDD+ Avoided Deforestation": "redd",
    "AR-ACM0003 Afforestation/Reforestation": "arr",
    "GS-TPDDTEC Improved Cookstoves": "cookstove",
    "VM0042 Rice Methane Reduction": "rice",
}
BASE_PRICE = {"mangrove": 18.0, "redd": 9.0, "arr": 14.0, "cookstove": 7.0, "rice": 11.0}

# id, name, country, iso2, methodology, (lon, lat), width_km, height_km, issuance tco2 per vintage, developer
PROJECTS = [
    ("P01", "Sundarbans Mangrove Restoration", "Bangladesh", "BD", "VM0033 Tidal Wetland Restoration", (89.20, 22.10), 6.0, 3.0, (24000, 26500, 27500), "Sundarbans Restoration Trust"),
    ("P02", "Cumilla Improved Cookstoves", "Bangladesh", "BD", "GS-TPDDTEC Improved Cookstoves", (91.12, 23.46), 20.0, 15.0, (60000, 64000, 66500), "Cumilla Stoves Cooperative"),
    ("P03", "Kisumu Clean Cookstoves", "Kenya", "KE", "GS-TPDDTEC Improved Cookstoves", (34.77, -0.09), 18.0, 14.0, (48000, 52000, 54000), "Lake Basin Energy Ltd"),
    ("P04", "Madre de Dios Forest Protection", "Peru", "PE", "VM0007 REDD+ Avoided Deforestation", (-70.50, -12.60), 40.0, 30.0, (210000, 235000, 258000), "Amazonia Conservation SAC"),
    ("P05", "Kalimantan Mangrove Blue Carbon", "Indonesia", "ID", "VM0033 Tidal Wetland Restoration", (110.05, -1.95), 12.0, 8.0, (90000, 96000, 101000), "Borneo Blue Carbon PT"),
    ("P06", "Mekong Delta Low-Methane Rice", "Vietnam", "VN", "VM0042 Rice Methane Reduction", (105.60, 9.90), 30.0, 25.0, (38000, 41500, 44000), "Mekong Growers Alliance"),
    ("P07", "Kakamega Community Reforestation", "Kenya", "KE", "AR-ACM0003 Afforestation/Reforestation", (34.85, 0.28), 10.0, 7.0, (30000, 32500, 35000), "Western Kenya Agroforestry"),
    ("P08", "Cusco Highland Agroforestry", "Peru", "PE", "AR-ACM0003 Afforestation/Reforestation", (-71.90, -13.50), 2.0, 1.5, (11000, 52000, 11500), "Andes Verde SAC"),
    ("P09", "Sundarbans Blue Carbon Phase II", "Bangladesh", "BD", "VM0033 Tidal Wetland Restoration", (89.23, 22.11), 6.0, 3.0, (14000, 15500, 16000), "Delta Carbon Ventures"),
]
VINTAGES = (2021, 2022, 2023)

CORPORATES = ["Meridian Airways", "Northwind Energy", "Fjord Bank", "Kestrel Logistics", "Altura Foods",
              "Sable Mining Co", "Bluepeak Apparel", "Orion Telecom", "Harbor & Vale Insurance", "Tessera Motors"]
BROKERS = ["GreenBridge Brokers", "CarbonLink Exchange", "Tidewater Trading", "Aurora Carbon Desk"]
HOST_COUNTRIES = {"BD": "Bangladesh", "KE": "Kenya", "PE": "Peru", "ID": "Indonesia", "VN": "Vietnam"}
CLAIM_PURPOSES = ["FY2023 Scope 1 neutrality", "FY2024 Scope 2 residual", "Net-zero programme 2030",
                  "FY2024 customer-flight offsets", "FY2025 voluntary commitment"]


def rect_wkt(lon: float, lat: float, w_km: float, h_km: float) -> tuple[str, float]:
    dlon = (w_km / 2) / (111.32 * math.cos(math.radians(lat)))
    dlat = (h_km / 2) / 110.57
    pts = [(lon - dlon, lat - dlat), (lon + dlon, lat - dlat), (lon + dlon, lat + dlat), (lon - dlon, lat + dlat), (lon - dlon, lat - dlat)]
    wkt = "POLYGON((" + ", ".join(f"{x:.5f} {y:.5f}" for x, y in pts) + "))"
    return wkt, round(w_km * h_km * 100, 1)


def d(s: date, days: int) -> date:
    return s + timedelta(days=days)


def build() -> dict:
    rng = random.Random(SEED)
    issuances, trades, retirements = [], [], []
    tcount = [0]
    rcount = [0]

    def new_trade(ss, se, seller, buyer, price, dt, tid=None):
        if tid is None:
            tcount[0] += 1
            tid = f"T{tcount[0]:04d}"
        trades.append(dict(trade_id=tid, serial_start=ss, serial_end=se, seller=seller, buyer=buyer,
                           price_usd=round(price, 2), date=dt.isoformat()))
        return tid

    def new_ret(ss, se, entity, claimed_for, dt, rid=None):
        if rid is None:
            rcount[0] += 1
            rid = f"R{rcount[0]:04d}"
        retirements.append(dict(retirement_id=rid, serial_start=ss, serial_end=se, retiring_entity=entity,
                                claimed_for=claimed_for, date=dt.isoformat()))
        return rid

    proj_meta = {}
    leftovers = {}   # issuance_id -> (start, end, date, developer, base_price, pid)
    held_lots = []   # (ss, se, owner, date_acquired, pid, issuance_id, price)

    for k, (pid, name, country, iso, meth, (lon, lat), w, h, vols, dev) in enumerate(PROJECTS, start=1):
        wkt, area = rect_wkt(lon, lat, w, h)
        cat = METHODOLOGIES[meth]
        proj_meta[pid] = dict(name=name, country=country, iso=iso, cat=cat, developer=dev, area=area)
        for vi, (vint, vol) in enumerate(zip(VINTAGES, vols)):
            ss = k * BLOCK + vi * VINTAGE_STRIDE + 1
            se = ss + vol - 1
            iss_date = date(vint + 1, 2, 1) + timedelta(days=rng.randint(0, 40))
            iid = f"ISS-{pid}-{vint}"
            issuances.append(dict(project_id=pid, project_name=name, serial_start=ss, serial_end=se,
                                  vintage_year=vint, country=country, methodology=meth, issued_tco2=vol,
                                  polygon_wkt=wkt, area_ha=area, issuance_id=iid, developer=dev,
                                  issuance_date=iss_date.isoformat()))
            # --- legitimate secondary market: carve lots, leave a tail unsold
            cursor = ss
            sell_end = ss + int(vol * rng.uniform(0.80, 0.90)) - 1
            while cursor <= sell_end:
                size = min(rng.randint(2000, 12000) if vol > 30000 else rng.randint(1500, 6000), sell_end - cursor + 1)
                if sell_end - (cursor + size - 1) < 800:
                    size = sell_end - cursor + 1
                lo, hi = cursor, cursor + size - 1
                cursor = hi + 1
                base = BASE_PRICE[cat] * (1 + 0.04 * (vint - 2021)) * rng.lognormvariate(0, 0.07)
                t0 = d(iss_date, rng.randint(10, 400))
                use_broker = rng.random() < 0.6
                buyer = rng.choice(CORPORATES)
                if use_broker:
                    b = rng.choice(BROKERS)
                    new_trade(lo, hi, dev, b, base, t0)
                    t1 = d(t0, rng.randint(7, 60))
                    new_trade(lo, hi, b, buyer, base * rng.uniform(1.04, 1.10), t1)
                    last_dt, price_paid = t1, base * 1.07
                else:
                    new_trade(lo, hi, dev, buyer, base, t0)
                    last_dt, price_paid = t0, base
                held_lots.append((lo, hi, buyer, last_dt, pid, iid, price_paid))
                if rng.random() < 0.7:        # buyer retires all or part of the lot
                    frac_end = hi if rng.random() < 0.65 else lo + int((hi - lo) * rng.uniform(0.4, 0.8))
                    rdt = d(last_dt, rng.randint(15, 300))
                    if rdt <= date(2025, 9, 30):
                        new_ret(lo, frac_end, buyer, rng.choice(CLAIM_PURPOSES), rdt)
            leftovers[iid] = dict(start=cursor, end=se, date=iss_date, dev=dev, base=BASE_PRICE[cat] * (1 + 0.04 * (vint - 2021)), pid=pid, cat=cat)

    gt_cases = []
    iss_df = pd.DataFrame(issuances)

    def case(ctype, name, desc, expected_rules, subjects, **extra):
        gt_cases.append(dict(case_id=f"GT-{len(gt_cases)+1:02d}", fraud_type=ctype, name=name, description=desc,
                             expected_rules=expected_rules, subject_ids=subjects, **extra))

    # ---------------------------------------------------------------- F1 double sold
    lot = next(t for t in trades if t["seller"] == "Lake Basin Energy Ltd" and t["trade_id"].startswith("T") and int(t["trade_id"][1:]) > 40)
    ss, se = lot["serial_start"], lot["serial_end"]
    dt = date.fromisoformat(lot["date"]) + timedelta(days=21)
    new_trade(ss, se, lot["seller"], "Northwind Energy" if lot["buyer"] != "Northwind Energy" else "Orion Telecom",
              float(lot["price_usd"]) * 0.97, dt, tid="T9001")
    case(1, "Same serial range sold to two buyers",
         f"{lot['seller']} sold {se-ss+1:,} tCO2 (Kisumu) to {lot['buyer']} on {lot['date']}, then sold the identical serial range again 21 days later.",
         ["R01"], ["T9001"], original_trade=lot["trade_id"])
    # phantom sale: broker sells credits it never held
    pl = next(t for t in trades if t["seller"] == "Mekong Growers Alliance")
    new_trade(pl["serial_start"], pl["serial_start"] + 1999, "Cobalt Carbon Partners", "Fjord Bank", 10.5, date(2024, 11, 3), tid="T9002")
    case(1, "Phantom sale (seller never held the credits)",
         "Cobalt Carbon Partners (an unregistered trader) sold 2,000 tCO2 of Mekong rice credits it never acquired.", ["R10"], ["T9002"], variant=True)

    # ---------------------------------------------------------------- F2 double retired
    rr = next(r for r in retirements if r["retirement_id"] == "R0020")
    new_ret(rr["serial_start"], rr["serial_end"], rr["retiring_entity"], "FY2025 voluntary commitment",
            date.fromisoformat(rr["date"]) + timedelta(days=140), rid="R9001")
    case(2, "Same serial range retired twice",
         f"{rr['retiring_entity']} retired the same {rr['serial_end']-rr['serial_start']+1:,} tCO2 a second time for a different claim.",
         ["R02"], ["R9001"], original_retirement=rr["retirement_id"])
    rr2 = next(r for r in retirements if r["retirement_id"] == "R0045")
    new_ret(rr2["serial_start"], rr2["serial_end"], "Tessera Motors" if rr2["retiring_entity"] != "Tessera Motors" else "Orion Telecom",
            "FY2024 customer-flight offsets", date.fromisoformat(rr2["date"]) + timedelta(days=60), rid="R9002")
    case(2, "Retired by an entity that is not the owner",
         "A second company retired credits that were already retired by their owner.", ["R02"], ["R9002"], variant=True)

    # ---------------------------------------------------------------- F3 never issued
    pe = iss_df[iss_df.issuance_id == "ISS-P05-2022"].iloc[0]
    gap_s = int(pe.serial_end) + 1000          # in the gap beyond the issued range
    new_trade(gap_s, gap_s + 4999, "Borneo Blue Carbon PT", "Meridian Airways", 17.6, date(2024, 6, 14), tid="T9003")
    new_ret(gap_s, gap_s + 4999, "Meridian Airways", "FY2024 customer-flight offsets", date(2024, 8, 1), rid="R9003")
    case(3, "Credits traded and retired that were never issued",
         "5,000 tCO2 were sold and then retired from a serial range the registry never issued (Kalimantan).",
         ["R03", "R03"], ["T9003", "R9003"])

    # ---------------------------------------------------------------- F4 / F5 are in the issuance table
    case(4, "Two projects with overlapping polygons",
         "Sundarbans Mangrove Restoration (P01) and Sundarbans Blue Carbon Phase II (P09) claim ~85% overlapping mangrove area.",
         ["R04"], ["P01", "P09"])
    case(5, "Claimed sequestration above the physical ceiling",
         "Cusco Highland Agroforestry issued 52,000 tCO2 for 300 ha in 2022 (173 tCO2/ha/yr; the ARR physical ceiling is 40).",
         ["R05"], ["ISS-P08-2022"])

    # ---------------------------------------------------------------- F7 wash loop + price spike (from unsold tails)
    lf = leftovers["ISS-P04-2022"]
    ws, we = lf["start"], lf["start"] + 7999
    base = lf["base"]
    new_trade(ws, we, lf["dev"], "Tidewater Trading", base, date(2024, 2, 5), tid="T8000")
    new_trade(ws, we, "Tidewater Trading", "CarbonLink Exchange", base * 1.9, date(2024, 2, 12), tid="T9004")
    new_trade(ws, we, "CarbonLink Exchange", "Aurora Carbon Desk", base * 2.8, date(2024, 2, 19), tid="T9005")
    new_trade(ws, we, "Aurora Carbon Desk", "Tidewater Trading", base * 3.9, date(2024, 2, 26), tid="T9006")
    case(7, "Wash-trading loop",
         "Tidewater Trading -> CarbonLink Exchange -> Aurora Carbon Desk -> Tidewater Trading: the same 8,000 tCO2 circle among three related desks in 3 weeks, price rising 2x.",
         ["R07"], ["T9004", "T9005", "T9006"])
    lf2 = leftovers["ISS-P07-2022"]
    new_trade(lf2["start"], lf2["start"] + 2999, lf2["dev"], "Orion Telecom", lf2["base"] * 12.0, date(2024, 5, 20), tid="T9007")
    case(7, "Suspicious price spike", "3,000 tCO2 of Kakamega ARR credits traded at 12x the project median price.",
         ["R08"], ["T9007"], variant=True)

    # ---------------------------------------------------------------- F6 host-country double claim
    bd_ret = next(r for r in retirements if 1 * BLOCK <= r["serial_start"] < 3 * BLOCK and r["retirement_id"] > "R0030" and r["retirement_id"].startswith("R0"))
    hc = []
    hc.append(dict(claim_id="HC9001", country="Bangladesh", serial_start=bd_ret["serial_start"], serial_end=bd_ret["serial_end"],
                   basis="NDC progress report 2024", corresponding_adjustment=False, date="2025-01-15"))
    # negative controls: authorised transfers with a corresponding adjustment applied (legitimate Article 6.2)
    for r in [x for x in retirements if 3 * BLOCK <= x["serial_start"] < 4 * BLOCK][:3]:
        hc.append(dict(claim_id=f"HC{len(hc):04d}", country="Kenya", serial_start=r["serial_start"], serial_end=r["serial_end"],
                       basis="Authorised ITMO, corresponding adjustment applied", corresponding_adjustment=True, date="2025-01-15"))
    case(6, "Host country and corporate buyer claim the same tonnes",
         f"Bangladesh counted the same {bd_ret['serial_end']-bd_ret['serial_start']+1:,} tCO2 toward its NDC while {bd_ret['retiring_entity']} retired them for its own claim (no corresponding adjustment).",
         ["R06"], ["HC9001"], retirement=bd_ret["retirement_id"])

    # ---------------------------------------------------------------- F8 greenwashing + legit claims
    ret_df = pd.DataFrame(retirements)
    ret_df["tco2"] = ret_df.serial_end - ret_df.serial_start + 1
    tot = ret_df[~ret_df.retirement_id.str.startswith("R9")].groupby("retiring_entity").tco2.sum().to_dict()
    claims = []
    ci = 0
    for comp in CORPORATES:
        if comp == "Meridian Airways":
            continue
        retired = int(tot.get(comp, 0))
        if retired < 3000:
            continue
        ci += 1
        claims.append(dict(claim_id=f"CL{ci:04d}", company=comp,
                           claim_text=f"We have retired {int(retired*rng.uniform(0.6, 0.95)):,} tCO2 of verified carbon credits.",
                           claimed_tco2=int(retired * rng.uniform(0.6, 0.95)), channel="Sustainability report", date="2025-03-10"))
    for c in claims:  # keep text and number consistent
        c["claim_text"] = f"We have retired {c['claimed_tco2']:,} tCO2 of verified carbon credits."
    m_ret = int(tot.get("Meridian Airways", 0))
    claimed = max(100_000, int(math.ceil(m_ret * 3 / 50_000)) * 50_000)
    claims.append(dict(claim_id="CL9001", company="Meridian Airways",
                       claim_text=f"Meridian Airways offset {claimed:,} tCO2: every flight is carbon neutral.",
                       claimed_tco2=claimed, channel="Press release", date="2025-04-22"))
    case(8, "Greenwashing claim",
         f"Meridian Airways publicly claims {claimed:,} tCO2 offset but only retired {m_ret:,} tCO2, part of it from credits that fail verification.",
         ["R09"], ["CL9001"])

    # --- write
    pd.DataFrame(issuances).to_csv(OUT / "registry_issuances.csv", index=False)
    pd.DataFrame(sorted(trades, key=lambda t: (t["date"], t["trade_id"]))).to_csv(OUT / "market_trades.csv", index=False)
    pd.DataFrame(sorted(retirements, key=lambda t: (t["date"], t["retirement_id"]))).to_csv(OUT / "retirements.csv", index=False)
    pd.DataFrame(hc).to_csv(OUT / "host_country_claims.csv", index=False)
    pd.DataFrame(claims).to_csv(OUT / "corporate_claims.csv", index=False)

    types = {c["fraud_type"] for c in gt_cases}
    gt = dict(
        note="SYNTHETIC ground truth for engine evaluation. subject_ids are the entities the engine must flag.",
        seed=SEED, fraud_types=sorted(types), cases=gt_cases,
        expected_subjects=sorted({s for c in gt_cases for s in c["subject_ids"]}),
    )
    (OUT / "ground_truth.json").write_text(json.dumps(gt, indent=2), encoding="utf-8")
    return gt


if __name__ == "__main__":
    gt = build()
    print(f"generated: {len(gt['cases'])} injected cases covering fraud types {gt['fraud_types']}")
