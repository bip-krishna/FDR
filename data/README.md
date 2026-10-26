# OurAirports source data

`airports.csv` is the OurAirports airport dataset downloaded on 2026-10-24 from https://davidmegginson.github.io/ourairports-data/airports.csv (linked from https://ourairports.com/data/).

OurAirports says the data is updated nightly and released to the public domain. It also provides no guarantee of accuracy or fitness for use. A record's presence does not establish scheduled passenger service. The importer preserves `scheduled_service` and airport `type` so callers can apply transparent eligibility filters.

To refresh the snapshot, download the CSV from the source URL above and rerun `python -m app.import_airports` from `backend/`. Record the retrieval date here when refreshing the data.

## Indian Railways station index

- `rail_stations_2026.csv` contains station names and codes transcribed from the official [Trains at a Glance 2026 Station Code Index](https://rb.indianrailways.gov.in/uploads/directorate/coaching/TAG_2026/Station_Code_Index.pdf).
- Retrieved on 2026-10-26. The original source PDF is retained as `Station_Code_Index_2026.pdf` for provenance and reproducibility.
- This is station reference data only. It does not provide train routes, timetables, fares, or seat availability. Those values remain unavailable until an authorized current provider is connected.
- When refreshing, retrieve the current official Station Code Index, then run `python scripts/import_rail_stations.py data/Station_Code_Index_2026.pdf data/rail_stations_2026.csv`. Review the changes and record the source publication and retrieval dates before replacing the snapshot.
