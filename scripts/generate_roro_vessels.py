"""Generate a fictional-but-plausible Ro-Ro-only fleet for demos.

Same idea as generate_vessels.py, but narrowed to one vessel family: Ro-Ro
(roll-on/roll-off), across its real-world subtypes — pure car/truck
carriers, ConRo, RoPax ferries, and general Ro-Ro cargo ships. Produces
examples/roro_fleet.json, .csv, and .xlsx. All names, IMO numbers, and
companies are invented.

Run: python scripts/generate_roro_vessels.py
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

# subtype -> prefix, vehicle capacity (CEU), TEU (ConRo only), passengers (RoPax
# only), lane metres, stern/quarter ramp capacity, dwt, gt, length, beam,
# draft, speed, crew, relative frequency
RORO_SUBTYPES = {
    "Pure Car Truck Carrier (PCTC)": dict(
        prefix="MV", vehicle=(4000, 8500), teu=(0, 0), passengers=(0, 0),
        lane=(2800, 5200), ramp=(20, 50), dwt=(12000, 25000), gt=(35000, 75000),
        length=(180, 230), beam=(28, 38), draft=(9, 11.5), speed=(18, 21),
        crew=(20, 26), weight=32,
    ),
    "ConRo (Container/Ro-Ro)": dict(
        prefix="MV", vehicle=(500, 2000), teu=(1000, 3000), passengers=(0, 0),
        lane=(1200, 2600), ramp=(30, 70), dwt=(15000, 30000), gt=(20000, 45000),
        length=(180, 240), beam=(26, 32), draft=(8.5, 10.5), speed=(19, 22),
        crew=(20, 26), weight=18,
    ),
    "RoPax Ferry": dict(
        prefix="MS", vehicle=(150, 700), teu=(0, 0), passengers=(400, 2800),
        lane=(1000, 2400), ramp=(15, 40), dwt=(2000, 8000), gt=(10000, 40000),
        length=(120, 215), beam=(21, 30), draft=(5.5, 7), speed=(21, 27),
        crew=(40, 120), weight=32,
    ),
    "Ro-Ro Cargo Ship": dict(
        prefix="MV", vehicle=(200, 1200), teu=(0, 0), passengers=(0, 12),
        lane=(1500, 4200), ramp=(30, 80), dwt=(8000, 25000), gt=(15000, 60000),
        length=(130, 240), beam=(21, 32), draft=(6, 8.5), speed=(18, 22),
        crew=(18, 26), weight=18,
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


def generate_roro_fleet(count: int, seed: int = 4102) -> list[dict]:
    rand = random.Random(seed)
    used_imos: set[int] = set()
    used_names: set[str] = set()
    subtype_names, subtype_weights = zip(*[(k, v["weight"]) for k, v in RORO_SUBTYPES.items()])

    fleet = []
    for _ in range(count):
        subtype = rand.choices(subtype_names, weights=subtype_weights, k=1)[0]
        spec = RORO_SUBTYPES[subtype]

        while True:
            name = f"{rand.choice(NAME_ADJECTIVES)} {rand.choice(NAME_NOUNS)}"
            if name not in used_names:
                used_names.add(name)
                break

        imo = make_imo(rand, used_imos)
        last_special_survey = random_date(rand, date(2021, 1, 1), TODAY)
        next_drydock = last_special_survey + timedelta(days=rand.randint(365, 5 * 365))
        owner = rand.choice(COMPANIES)
        operator = owner if rand.random() < 0.6 else rand.choice(COMPANIES)

        vessel = {
            "id": str(imo),
            "name": f"{spec['prefix']} {name}",
            "roro_subtype": subtype,
            "flag": rand.choice(FLAGS),
            "built_year": rand.randint(1995, 2025),
            "gross_tonnage": round(rand.uniform(*spec["gt"])),
            "deadweight_tonnes": round(rand.uniform(*spec["dwt"])),
            "length_m": round(rand.uniform(*spec["length"]), 1),
            "beam_m": round(rand.uniform(*spec["beam"]), 1),
            "draft_m": round(rand.uniform(*spec["draft"]), 1),
            "service_speed_knots": round(rand.uniform(*spec["speed"]), 1),
            "lane_metres": round(rand.uniform(*spec["lane"])),
            "vehicle_capacity_ceu": round(rand.uniform(*spec["vehicle"])),
            "teu_capacity": round(rand.uniform(*spec["teu"])),
            "passenger_capacity": round(rand.uniform(*spec["passengers"])),
            "ramp_capacity_tonnes": round(rand.uniform(*spec["ramp"])),
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
        fleet.append(vessel)

    return fleet


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
    fleet = generate_roro_fleet(120)
    EXAMPLES_DIR.mkdir(exist_ok=True)
    write_json(fleet, EXAMPLES_DIR / "roro_fleet.json")
    write_csv(fleet, EXAMPLES_DIR / "roro_fleet.csv")
    write_xlsx(fleet, EXAMPLES_DIR / "roro_fleet.xlsx")
    print(f"Wrote {len(fleet)} Ro-Ro vessels to examples/roro_fleet.{{json,csv,xlsx}}")
