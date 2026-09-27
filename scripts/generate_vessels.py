"""Generate a large, fictional-but-plausible maritime fleet catalog for demos.

Produces examples/vessels.json, examples/vessels.csv, and examples/vessels.xlsx —
the same 130-vessel fleet in all three formats metacurate accepts. All names,
IMO numbers, and companies are invented; classification societies, flag
states, and ports are real-world categories used for realism only.

Run: python scripts/generate_vessels.py
"""

from __future__ import annotations

import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"

TODAY = date(2026, 9, 27)

FLAGS = [
    "Panama", "Liberia", "Marshall Islands", "Hong Kong", "Singapore", "Malta",
    "Bahamas", "Greece", "Japan", "China", "Cyprus", "Isle of Man",
    "United Kingdom", "Norway", "Denmark", "Netherlands", "South Korea", "Italy",
]

CLASS_SOCIETIES = [
    "DNV", "Lloyd's Register", "ABS", "Bureau Veritas", "ClassNK", "RINA",
    "China Classification Society", "Korean Register",
]

HOME_PORTS = [
    "Singapore", "Rotterdam", "Shanghai", "Busan", "Hamburg", "Antwerp",
    "Hong Kong", "Jebel Ali", "Los Angeles", "Long Beach", "Piraeus",
    "Valencia", "Colombo", "Santos", "New York/New Jersey", "Tokyo",
    "Felixstowe", "Bremerhaven", "Panama City", "Southampton",
]

COMPANIES = [
    "Nordwind Shipping Co.", "Pacific Rim Maritime", "Atlas Ocean Carriers",
    "Meridian Bulk Lines", "Solstice Tankers Ltd.", "Blue Horizon Shipping",
    "Coral Sea Logistics", "Trident Marine Group", "Zenith Ocean Transport",
    "Cascade Maritime Holdings", "Aurora Fleet Services", "Vanguard Shipping Corp.",
    "Neptune Global Lines", "Silverline Maritime", "Emerald Coast Shipping",
    "Northstar Ocean Carriers", "Continental Sealift", "Harborview Shipping Group",
    "Deepwater Logistics Inc.", "Voyager Marine Enterprises",
]

NAME_ADJECTIVES = [
    "Northern", "Pacific", "Atlantic", "Southern", "Arctic", "Golden", "Silver",
    "Crimson", "Emerald", "Coral", "Amber", "Celestial", "Meridian", "Western",
    "Eastern", "Royal", "Grand", "Noble", "Radiant", "Azure", "Crystal", "Great",
]

NAME_NOUNS = [
    "Star", "Wave", "Current", "Tide", "Horizon", "Spirit", "Glory", "Dawn",
    "Enterprise", "Falcon", "Eagle", "Osprey", "Dolphin", "Explorer",
    "Pathfinder", "Guardian", "Discovery", "Legacy", "Pride", "Venture",
    "Voyager", "Odyssey", "Navigator", "Pioneer", "Endeavour", "Mariner",
    "Comet", "Aurora", "Sentinel", "Frontier", "Trader", "Carrier",
]

STATUS_WEIGHTS = [
    ("In Service", 78),
    ("Under Maintenance", 8),
    ("Under Construction", 6),
    ("Laid Up", 5),
    ("Decommissioned", 3),
]

PROPULSION_OPTIONS = [
    "Diesel, 2-stroke slow-speed",
    "Diesel, 4-stroke medium-speed",
    "Diesel-electric",
    "Dual-fuel (LNG/diesel)",
    "Gas turbine",
]

# name_prefix, cargo_field, cargo_range, dwt_range, gt_range, length_range,
# beam_range, draft_range, speed_range, crew_range, weight (relative frequency)
VESSEL_TYPES = {
    "Container Ship": dict(
        prefix="MV", cargo_field="teu_capacity", cargo_range=(1000, 24000),
        dwt=(15000, 220000), gt=(20000, 235000), length=(150, 400),
        beam=(25, 62), draft=(9, 16.5), speed=(18, 24), crew=(13, 25), weight=16,
    ),
    "Bulk Carrier": dict(
        prefix="MV", cargo_field="cargo_deadweight_tonnes", cargo_range=(10000, 210000),
        dwt=(10000, 210000), gt=(8000, 175000), length=(100, 340), beam=(16, 60),
        draft=(8, 18), speed=(12, 15), crew=(18, 25), weight=16,
    ),
    "Crude Oil Tanker": dict(
        prefix="MT", cargo_field="cargo_capacity_barrels", cargo_range=(300000, 2200000),
        dwt=(30000, 320000), gt=(20000, 235000), length=(180, 380), beam=(30, 62),
        draft=(11, 22), speed=(14, 16), crew=(20, 30), weight=10,
    ),
    "Product Tanker": dict(
        prefix="MT", cargo_field="cargo_capacity_barrels", cargo_range=(80000, 550000),
        dwt=(10000, 75000), gt=(6000, 45000), length=(90, 245), beam=(15, 43),
        draft=(7, 14.5), speed=(14, 16), crew=(18, 24), weight=10,
    ),
    "Chemical Tanker": dict(
        prefix="MT", cargo_field="cargo_capacity_cbm", cargo_range=(5000, 45000),
        dwt=(5000, 50000), gt=(4000, 35000), length=(90, 185), beam=(14, 32),
        draft=(6, 12.5), speed=(13, 16), crew=(18, 24), weight=7,
    ),
    "LNG Carrier": dict(
        prefix="MV", cargo_field="cargo_capacity_cbm", cargo_range=(130000, 266000),
        dwt=(60000, 120000), gt=(90000, 175000), length=(275, 345), beam=(43, 55),
        draft=(11, 12.5), speed=(19, 20), crew=(24, 34), weight=5,
    ),
    "LPG Carrier": dict(
        prefix="MV", cargo_field="cargo_capacity_cbm", cargo_range=(20000, 84000),
        dwt=(18000, 55000), gt=(15000, 60000), length=(150, 230), beam=(24, 37),
        draft=(9, 12), speed=(16, 18), crew=(20, 26), weight=4,
    ),
    "Ro-Ro Cargo Ship": dict(
        prefix="MV", cargo_field="lane_metres", cargo_range=(1500, 4200),
        dwt=(8000, 25000), gt=(15000, 60000), length=(130, 240), beam=(21, 32),
        draft=(6, 8.5), speed=(18, 22), crew=(20, 26), weight=5,
    ),
    "Vehicle Carrier": dict(
        prefix="MV", cargo_field="vehicle_capacity_units", cargo_range=(2000, 8500),
        dwt=(12000, 25000), gt=(30000, 75000), length=(160, 230), beam=(28, 38),
        draft=(9, 11.5), speed=(18, 21), crew=(20, 26), weight=5,
    ),
    "General Cargo Ship": dict(
        prefix="MV", cargo_field="cargo_deadweight_tonnes", cargo_range=(3000, 18000),
        dwt=(3000, 18000), gt=(2500, 15000), length=(80, 160), beam=(13, 24),
        draft=(6, 9.5), speed=(13, 17), crew=(14, 20), weight=7,
    ),
    "Refrigerated Cargo Ship": dict(
        prefix="MV", cargo_field="cargo_capacity_cbm", cargo_range=(300000, 600000),
        dwt=(8000, 14000), gt=(9000, 15000), length=(140, 175), beam=(21, 25),
        draft=(8, 9.5), speed=(20, 22), crew=(16, 22), weight=3,
    ),
    "Cruise Ship": dict(
        prefix="MS", cargo_field="passenger_capacity", cargo_range=(800, 6500),
        dwt=(4000, 20000), gt=(50000, 230000), length=(200, 360), beam=(28, 66),
        draft=(7, 9.5), speed=(20, 24), crew=(700, 2300), weight=5,
    ),
    "Ferry": dict(
        prefix="MS", cargo_field="passenger_capacity", cargo_range=(150, 2800),
        dwt=(1000, 8000), gt=(3000, 40000), length=(60, 200), beam=(14, 30),
        draft=(4, 6.5), speed=(18, 27), crew=(20, 90), weight=6,
    ),
    "Offshore Supply Vessel": dict(
        prefix="MV", cargo_field="deck_cargo_tonnes", cargo_range=(1500, 4500),
        dwt=(1500, 5000), gt=(1800, 6500), length=(55, 95), beam=(14, 20),
        draft=(5, 7), speed=(12, 16), crew=(10, 20), weight=6,
    ),
    "Tugboat": dict(
        prefix="MV", cargo_field="bollard_pull_tonnes", cargo_range=(20, 90),
        dwt=(200, 1200), gt=(150, 1000), length=(20, 40), beam=(8, 13),
        draft=(3, 5.5), speed=(11, 14), crew=(4, 9), weight=4,
    ),
    "Fishing Trawler": dict(
        prefix="MV", cargo_field="fish_hold_cbm", cargo_range=(150, 2500),
        dwt=(200, 3500), gt=(150, 3000), length=(20, 80), beam=(7, 16),
        draft=(3, 7), speed=(10, 15), crew=(6, 30), weight=3,
    ),
    "Research Vessel": dict(
        prefix="MV", cargo_field="lab_space_sqm", cargo_range=(80, 600),
        dwt=(500, 3500), gt=(800, 6500), length=(40, 100), beam=(10, 20),
        draft=(4, 7), speed=(12, 16), crew=(20, 60), weight=2,
    ),
    "Livestock Carrier": dict(
        prefix="MV", cargo_field="livestock_capacity_head", cargo_range=(3000, 20000),
        dwt=(5000, 20000), gt=(6000, 22000), length=(100, 175), beam=(18, 27),
        draft=(6, 9), speed=(14, 17), crew=(18, 26), weight=2,
    ),
    "Heavy Lift Ship": dict(
        prefix="MV", cargo_field="crane_capacity_tonnes", cargo_range=(200, 2000),
        dwt=(8000, 45000), gt=(9000, 40000), length=(100, 215), beam=(18, 33),
        draft=(7, 11), speed=(14, 17), crew=(16, 24), weight=2,
    ),
    "Dredger": dict(
        prefix="MV", cargo_field="hopper_capacity_cbm", cargo_range=(2000, 35000),
        dwt=(3000, 40000), gt=(3500, 42000), length=(80, 175), beam=(18, 32),
        draft=(6, 11), speed=(11, 14), crew=(20, 40), weight=2,
    ),
}


def make_imo(rand: random.Random, used: set[int]) -> int:
    while True:
        digits = [rand.randint(1, 9)] + [rand.randint(0, 9) for _ in range(5)]
        check = sum(d * (7 - i) for i, d in enumerate(digits)) % 10
        imo = int("".join(map(str, digits)) + str(check))
        if imo not in used:
            used.add(imo)
            return imo


def weighted_choice(rand: random.Random, options: list[tuple[str, int]]) -> str:
    names, weights = zip(*options)
    return rand.choices(names, weights=weights, k=1)[0]


def random_date(rand: random.Random, start: date, end: date) -> date:
    span = (end - start).days
    return start + timedelta(days=rand.randint(0, max(span, 0)))


def generate_vessels(count: int, seed: int = 2024) -> list[dict]:
    rand = random.Random(seed)
    used_imos: set[int] = set()
    used_names: set[str] = set()
    types_pool = list(VESSEL_TYPES.items())
    type_names, type_weights = zip(*[(name, spec["weight"]) for name, spec in types_pool])

    vessels = []
    for _ in range(count):
        vessel_type = rand.choices(type_names, weights=type_weights, k=1)[0]
        spec = VESSEL_TYPES[vessel_type]

        while True:
            name = f"{rand.choice(NAME_ADJECTIVES)} {rand.choice(NAME_NOUNS)}"
            if name not in used_names:
                used_names.add(name)
                break

        imo = make_imo(rand, used_imos)
        built_year = rand.randint(1992, 2025)
        last_special_survey = random_date(rand, date(2021, 1, 1), TODAY)
        next_drydock = last_special_survey + timedelta(days=rand.randint(365, 5 * 365))
        owner = rand.choice(COMPANIES)
        operator = owner if rand.random() < 0.6 else rand.choice(COMPANIES)

        vessel = {
            "id": str(imo),
            "name": f"{spec['prefix']} {name}",
            "vessel_type": vessel_type,
            "flag": rand.choice(FLAGS),
            "built_year": built_year,
            "gross_tonnage": round(rand.uniform(*spec["gt"])),
            "deadweight_tonnes": round(rand.uniform(*spec["dwt"])),
            "length_m": round(rand.uniform(*spec["length"]), 1),
            "beam_m": round(rand.uniform(*spec["beam"]), 1),
            "draft_m": round(rand.uniform(*spec["draft"]), 1),
            "service_speed_knots": round(rand.uniform(*spec["speed"]), 1),
            spec["cargo_field"]: round(rand.uniform(*spec["cargo_range"])),
            "propulsion": rand.choice(PROPULSION_OPTIONS),
            "crew_capacity": round(rand.uniform(*spec["crew"])),
            "owner": owner,
            "operator": operator,
            "classification_society": rand.choice(CLASS_SOCIETIES),
            "home_port": rand.choice(HOME_PORTS),
            "status": weighted_choice(rand, STATUS_WEIGHTS),
            "last_special_survey": last_special_survey.isoformat(),
            "next_drydock": next_drydock.isoformat(),
        }
        vessels.append(vessel)

    return vessels


def write_json(vessels: list[dict], path: Path) -> None:
    path.write_text(json.dumps(vessels, indent=2) + "\n")


def write_csv(vessels: list[dict], path: Path) -> None:
    fieldnames = sorted({key for vessel in vessels for key in vessel})
    fieldnames = ["id", "name"] + [f for f in fieldnames if f not in ("id", "name")]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, restval="")
        writer.writeheader()
        writer.writerows(vessels)


def write_xlsx(vessels: list[dict], path: Path) -> None:
    from openpyxl import Workbook

    fieldnames = sorted({key for vessel in vessels for key in vessel})
    fieldnames = ["id", "name"] + [f for f in fieldnames if f not in ("id", "name")]
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(fieldnames)
    for vessel in vessels:
        sheet.append([vessel.get(field, "") for field in fieldnames])
    workbook.save(path)


if __name__ == "__main__":
    fleet = generate_vessels(130)
    EXAMPLES_DIR.mkdir(exist_ok=True)
    write_json(fleet, EXAMPLES_DIR / "vessels.json")
    write_csv(fleet, EXAMPLES_DIR / "vessels.csv")
    write_xlsx(fleet, EXAMPLES_DIR / "vessels.xlsx")
    print(f"Wrote {len(fleet)} vessels to examples/vessels.{{json,csv,xlsx}}")
