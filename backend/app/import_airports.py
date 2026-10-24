import csv
from pathlib import Path

from sqlalchemy import delete

from .database import Base, SessionLocal, engine, PROJECT_ROOT
from .models import Airport

CSV_PATH = PROJECT_ROOT / "data" / "airports.csv"


def parse_coordinate(value: str) -> float | None:
    try:
        return float(value) if value else None
    except ValueError:
        return None


def import_airports(path: Path = CSV_PATH) -> int:
    Base.metadata.create_all(engine)
    count = 0
    with SessionLocal.begin() as session, path.open(newline="", encoding="utf-8") as source:
        session.execute(delete(Airport))
        for row in csv.DictReader(source):
            service = row.get("scheduled_service", "").strip().lower()
            session.add(Airport(
                source_id=row["id"], ident=row["ident"], type=row["type"], name=row["name"],
                latitude_deg=parse_coordinate(row.get("latitude_deg", "")),
                longitude_deg=parse_coordinate(row.get("longitude_deg", "")),
                iso_country=row.get("iso_country") or None, iso_region=row.get("iso_region") or None,
                municipality=row.get("municipality") or None,
                scheduled_service=True if service == "yes" else False if service == "no" else None,
                icao_code=row.get("icao_code") or None,
                iata_code=(row.get("iata_code") or "").upper() or None,
            ))
            count += 1
    return count


if __name__ == "__main__":
    print(f"Imported {import_airports()} airport records from {CSV_PATH}")
