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
| `paw-v2` | Western Pennsylvania (west of 77.6°W) | 20.8 MB | 41.4 MB | `pennsylvania-latest.osm.pbf`, `YWRP_BBOX=39.60,-80.60,42.40,-77.60` |
| `pae-v2` | Eastern Pennsylvania (east of 77.6°W) | 28.7 MB | 58.6 MB | `pennsylvania-latest.osm.pbf`, `YWRP_BBOX=39.60,-77.60,42.40,-74.60` |
| `oh-v2` | Ohio | 41.7 MB | 86.7 MB | `ohio-latest.osm.pbf` |
| `wv-v2` | West Virginia | 15.3 MB | 30.0 MB | `west-virginia-latest.osm.pbf` |
| `md-v2` | Maryland | 18.0 MB | 37.5 MB | `maryland-latest.osm.pbf` |
| `de-v2` | Delaware | 3.4 MB | 7.6 MB | `delaware-latest.osm.pbf` |

`sc-v1` (format v1) is superseded by `sc-v2`.

Build: `pip install osmium && python3 build_pack.py <state>-latest.osm.pbf <id>.ywrp && gzip -9 -k <id>.ywrp`.

Large states are split to keep phone memory down: `YWRP_BBOX=south,west,north,east python3 build_pack.py ...` keeps every
way with a node inside the box whole, so the halves share nodes along the cut and join like neighbouring states.
`grid.py` writes the app's owner grid (0.05° cells → pack with the most nodes) used to pick only the packs a route needs.

Cross-state routes: the app loads neighbouring packs together and joins them on the OSM nodes they share along the
border (Geofabrik extracts keep border-crossing ways whole). Checksums in `SHA256SUMS`.

Data © OpenStreetMap contributors, ODbL 1.0. See LICENSE.

## v3 packs (2026-10-28)
YWRP format 3 adds a per-edge toll flag (OSM `toll=yes`, `barrier=toll_booth`) used by the app's Avoid tolls option. Releases `<id>-v3` for sc nc ga ct ri ma nyd nyu nj paw pae oh wv md de. SHA-256 (decompressed) in SHA256SUMS. v2 packs still work without toll data.

Data © OpenStreetMap contributors, ODbL 1.0.

## Midwest v3 packs (2026-10-28)
Releases `mis-v3` (Michigan south of 43.1°N), `min-v3` (northern Lower Peninsula + UP), `in-v3`, `ilc-v3` (Illinois north of 41.0°N incl. Chicago), `ils-v3` (Illinois south of 41.0°N), `wi-v3`. Built from Geofabrik extracts of 2026-10-28; toll flags included. MI and IL are split to keep downloads ~12–29 MB each. SHA-256 (decompressed) in SHA256SUMS.

## Cameras
`cams-v2` (`cams-us-v2.json.gz`): 587 fixed speed/red-light cameras from OSM (adds IL, IN, WI; MI has none in OSM). Informational, may be incomplete. City of Chicago portal data is not included.

Data © OpenStreetMap contributors, ODbL 1.0.
