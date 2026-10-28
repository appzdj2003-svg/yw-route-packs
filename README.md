# yw-route-packs

Compact OpenStreetMap driving-graph packs (formats YWRP v1/v2; the current format is documented in `build_pack.py`).

- `sc-v1`: South Carolina. Built from Geofabrik `south-carolina-latest.osm.pbf` (2026-10-28) with
  `pip install osmium && python3 build_pack.py south-carolina-latest.osm.pbf sc-v1.ywrp && gzip -9 sc-v1.ywrp`.
- `sc-v2`: South Carolina, YWRP v2 (turn restrictions, signals/stops, urban flags, name/ref/destination labels, exit refs, turn:lanes, posted-limit flag). Same Geofabrik extract (2026-10-28);
  `python3 build_pack.py south-carolina-latest.osm.pbf sc-v2.ywrp && gzip -9 sc-v2.ywrp`.

Data © OpenStreetMap contributors, ODbL 1.0. See LICENSE.
