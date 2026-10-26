"""Extract the Indian Railways TAG station-code PDF into a small CSV index."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

from pypdf import PdfReader


def parse_station_lines(lines: list[str]) -> list[tuple[str, str]]:
    rows: dict[str, str] = {}
    pending_name: str | None = None
    for raw in lines:
        line = raw.strip()
        if not line or line in {"Station Name Code", "Station Code Index6", "TAG-26"} or line.isdigit():
            continue
        match = re.fullmatch(r"(.+?)\s+([A-Z0-9/]{2,7})", line)
        if match:
            name, code = match.groups()
            if name.upper() not in {"STATION NAME", "CODE"}:
                rows[code] = name.strip()
            pending_name = None
        elif re.fullmatch(r"[A-Z0-9/]{2,7}", line) and pending_name:
            rows[line] = pending_name
            pending_name = None
        elif any(char.isalpha() for char in line):
            pending_name = f"{pending_name} {line}".strip() if pending_name else line
    return sorted(((name, code) for code, name in rows.items()), key=lambda row: row[0].casefold())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path, help="Downloaded official Station Code Index PDF")
    parser.add_argument("output", type=Path, nargs="?", default=Path("data/rail_stations_2026.csv"))
    args = parser.parse_args()

    lines: list[str] = []
    for page in PdfReader(str(args.pdf)).pages:
        lines.extend(page.extract_text().splitlines())
    stations = parse_station_lines(lines)
    if len(stations) < 500:
        raise SystemExit(f"Only {len(stations)} stations parsed; inspect the source PDF before replacing the snapshot.")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as target:
        writer = csv.writer(target, lineterminator="\n")
        writer.writerow(("name", "code"))
        writer.writerows(stations)
    print(f"Wrote {len(stations)} stations to {args.output}")


if __name__ == "__main__":
    main()
