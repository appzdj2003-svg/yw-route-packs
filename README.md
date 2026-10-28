# yw-route-packs

Compact OpenStreetMap driving-graph packs for the Your World Travel app (format YWRP v2, documented in `build_pack.py`).
Each pack is a release asset (`<id>.ywrp.gz`); the app downloads only on request and checks the SHA-256 of the unpacked file.

| Pack | Region | Download (gz) | Unpacked | Source extract (Geofabrik, 2026-10-28) |
|---|---|---|---|---|
| `sc-v2` | South Carolina | 27.9 MB | 57.0 MB | `south-carolina-latest.osm.pbf` |
| `nc-v2` | North Carolina | 54.2 MB | 110.5 MB | `north-carolina-latest.osm.pbf` |
| `ga-v2` | Georgia | 44.2 MB | 91.4 MB | `georgia-latest.osm.pbf` |

`sc-v1` (format v1) is superseded by `sc-v2`.

Build: `pip install osmium && python3 build_pack.py <state>-latest.osm.pbf <id>.ywrp && gzip -9 -k <id>.ywrp`.

Cross-state routes: the app loads neighbouring packs together and joins them on the OSM nodes they share along the
border (Geofabrik extracts keep border-crossing ways whole). Checksums in `SHA256SUMS`.

Data © OpenStreetMap contributors, ODbL 1.0. See LICENSE.
