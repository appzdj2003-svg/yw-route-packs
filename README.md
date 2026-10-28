# yw-route-packs

Compact OpenStreetMap driving-graph packs for the Your World Travel app (format YWRP v2, documented in `build_pack.py`).
Each pack is a release asset (`<id>.ywrp.gz`); the app downloads only on request and checks the SHA-256 of the unpacked file.

| Pack | Region | Download (gz) | Unpacked | Source extract (Geofabrik, 2026-10-28) |
|---|---|---|---|---|
| `sc-v2` | South Carolina | 27.9 MB | 57.0 MB | `south-carolina-latest.osm.pbf` |
| `nc-v2` | North Carolina | 54.2 MB | 110.5 MB | `north-carolina-latest.osm.pbf` |
| `ga-v2` | Georgia | 44.2 MB | 91.4 MB | `georgia-latest.osm.pbf` |
| `ct-v2` | Connecticut | 10.6 MB | 21.8 MB | `connecticut-latest.osm.pbf` |
| `ri-v2` | Rhode Island | 3.4 MB | 7.3 MB | `rhode-island-latest.osm.pbf` |
| `ma-v2` | Massachusetts | 21.4 MB | 46.9 MB | `massachusetts-latest.osm.pbf` |
| `nyd-v2` | New York downstate (NYC, Long Island, Hudson Valley; south of 41.75°N) | 16.2 MB | 34.6 MB | `new-york-latest.osm.pbf`, `YWRP_BBOX=40.40,-75.00,41.75,-71.80` |
| `nyu-v2` | Upstate New York (north of 41.75°N) | 25.8 MB | 50.9 MB | `new-york-latest.osm.pbf`, `YWRP_BBOX=41.75,-79.90,45.10,-73.20` |
| `nj-v2` | New Jersey | 20.2 MB | 43.4 MB | `new-jersey-latest.osm.pbf` |

`sc-v1` (format v1) is superseded by `sc-v2`.

Build: `pip install osmium && python3 build_pack.py <state>-latest.osm.pbf <id>.ywrp && gzip -9 -k <id>.ywrp`.

Large states are split to keep phone memory down: `YWRP_BBOX=south,west,north,east python3 build_pack.py ...` keeps every
way with a node inside the box whole, so the halves share nodes along the cut and join like neighbouring states.
`grid.py` writes the app's owner grid (0.05° cells → pack with the most nodes) used to pick only the packs a route needs.

Cross-state routes: the app loads neighbouring packs together and joins them on the OSM nodes they share along the
border (Geofabrik extracts keep border-crossing ways whole). Checksums in `SHA256SUMS`.

Data © OpenStreetMap contributors, ODbL 1.0. See LICENSE.
