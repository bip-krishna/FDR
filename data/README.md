# OurAirports source data

`airports.csv` is the OurAirports airport dataset downloaded on 2026-10-24 from https://davidmegginson.github.io/ourairports-data/airports.csv (linked from https://ourairports.com/data/).

OurAirports says the data is updated nightly and released to the public domain. It also provides no guarantee of accuracy or fitness for use. A record's presence does not establish scheduled passenger service. The importer preserves `scheduled_service` and airport `type` so callers can apply transparent eligibility filters.

To refresh the snapshot, download the CSV from the source URL above and rerun `python -m app.import_airports` from `backend/`. Record the retrieval date here when refreshing the data.
