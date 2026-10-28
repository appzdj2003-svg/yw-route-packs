#!/usr/bin/env python3
"""Build a compact driving-route pack (format YWRP v3) from an OpenStreetMap .osm.pbf extract.

Data: (c) OpenStreetMap contributors, ODbL 1.0. The output pack is a Derivative Database and is
offered under the ODbL 1.0 (https://opendatacommons.org/licenses/odbl/1-0/). This script: MIT.

Usage: python3 build_pack.py south-carolina-latest.osm.pbf sc-v3.ywrp
Format v3 (v2 + flags2 bit1 toll) (little-endian):
  "YWRP" u32 ver=2, u32 nNodes, nEdges, nShape, nStrings, nLabels, nRestr, nExits, i32 minLat,minLon,maxLat,maxLon (1e-6 deg)
  i32 lat[nNodes], i32 lon[nNodes]
  u8  nodeCtl[nNodes] (padded to 4)   bit0 traffic_signals, bit1 stop, bit2 give_way, bit3 crossing, bit4 mini_roundabout
  u32 first[nNodes+1]                 CSR offsets into edges
  edges (16 B): u32 to, u32 lenDm, u32 shapeStart, u16 shapeCount, u8 speedKmh, u8 flags
      flags bit0 shape reversed, bits1-4 road class (0 motorway .. 9 living_street), bit5 link, bit6 roundabout, bit7 urban
  u32 label[nEdges]                   index into label table
  u8  ctl[nEdges] (padded to 4)       interior controls: high nibble signals, low nibble stops/give_way (each capped 15)
  u8  flags2[nEdges] (padded to 4)    bit0 maxspeed tagged (edge speed is then the posted limit), bit1 toll (v3:
                                      way toll=yes / toll:motorcar=yes, or a barrier=toll_booth node on the edge)
  i32 shapeLat[nShape], i32 shapeLon[nShape]
  labels (12 B): u32 name, u32 ref, u32 destination   (string indices, 0 = none)
  restrictions (12 B): u32 fromEdge, u32 toEdge, u32 kind (0 = no_*, 1 = only_*)   via-node restrictions only
  exits (8 B): u32 node, u32 string                   motorway_junction ref at a graph node
  u32 lanes[nEdges]  turn:lanes string for the travel direction (0 = none), e.g. "left|through|through;right"
  u32 strOff[nStrings+1], utf8 strings blob
Urban = edge midpoint in a ~1.1 km grid cell with >= URBAN_MIN junction nodes (degree >= 3).
"""
import sys, struct, math, re, array
import osmium

CLS = {"motorway":0,"trunk":1,"primary":2,"secondary":3,"tertiary":4,"unclassified":5,"residential":6,
       "motorway_link":0,"trunk_link":1,"primary_link":2,"secondary_link":3,"tertiary_link":4,"living_street":9}
DEF_KMH = {0:105,1:89,2:72,3:64,4:56,5:48,6:40,9:16}
LINK_KMH = 56
URBAN_MIN = 20
CTL = {"traffic_signals":1, "stop":2, "give_way":4, "crossing":8, "mini_roundabout":16}

def parse_speed(v):
    if not v: return None
    m = re.match(r"\s*(\d+(?:\.\d+)?)\s*(mph|km/h|kmh)?", v)
    if not m: return None
    s = float(m.group(1))
    return s * 1.609344 if (m.group(2) == "mph" or (m.group(2) is None and "mph" in v)) else s

class H(osmium.SimpleHandler):
    def __init__(s):
        super().__init__(); s.ways = []; s.use = {}; s.ctl = {}; s.junc = {}; s.rel = []; s.booth = set()
    def node(s, n):
        t = n.tags
        if not t: return
        hw = t.get("highway")
        if hw in CTL: s.ctl[n.id] = s.ctl.get(n.id, 0) | CTL[hw]
        if hw == "motorway_junction" and "ref" in t: s.junc[n.id] = t["ref"]
        if t.get("crossing") == "traffic_signals": s.ctl[n.id] = s.ctl.get(n.id, 0) | 8
        if t.get("barrier") == "toll_booth": s.booth.add(n.id)
    def way(s, w):
        t = w.tags; hw = t.get("highway")
        if hw not in CLS: return
        if t.get("area") == "yes": return
        if t.get("access") in ("no","private") or t.get("motor_vehicle") in ("no","private") or t.get("motorcar") in ("no","private"): return
        cls = CLS[hw]; link = hw.endswith("_link")
        ow = t.get("oneway", "")
        rb = t.get("junction") in ("roundabout","circular")
        oneway = 1 if ow in ("yes","1","true") else (-1 if ow == "-1" else 0)
        if oneway == 0 and (hw in ("motorway","motorway_link") or rb) and ow != "no": oneway = 1
        sp = parse_speed(t.get("maxspeed")) if "maxspeed" in t else None
        tagged = sp is not None
        if sp is None: sp = LINK_KMH if link and cls <= 1 else DEF_KMH[cls]
        sp = max(5, min(130, round(sp)))
        name = t.get("name", ""); ref = t.get("ref", "").split(";")[0].strip()
        dest = t.get("destination", "") or t.get("destination:ref", "")
        dest = "; ".join(x.strip() for x in dest.split(";")[:2] if x.strip())
        tl = t.get("turn:lanes", ""); lf = t.get("turn:lanes:forward", tl); lb = t.get("turn:lanes:backward", "")
        if oneway == -1: lf, lb = "", (tl or lb)
        refs = []; pts = []
        for n in w.nodes:
            if not n.location.valid(): continue
            refs.append(n.ref); pts.append((round(n.location.lat*1e6), round(n.location.lon*1e6)))
        if len(refs) < 2: return
        if BBOX and not any(BBOX[0] <= a <= BBOX[2] and BBOX[1] <= b <= BBOX[3] for a, b in pts): return
        for i, r in enumerate(refs):
            s.use[r] = s.use.get(r, 0) + (2 if i in (0, len(refs)-1) else 1)
        tv = t.get("toll:motorcar") or t.get("toll") or ""
        toll = tv not in ("", "no") and tv != "none"
        s.ways.append((w.id, refs, pts, oneway, sp, cls, link, rb, tagged | (2 if toll else 0), (name, ref, dest), (lf, lb)))
    def relation(s, r):
        t = r.tags
        if t.get("type") != "restriction": return
        k = t.get("restriction") or t.get("restriction:motorcar")
        if not k or t.get("except", "") in ("motorcar",): return
        kind = 0 if k.startswith("no_") else (1 if k.startswith("only_") else None)
        if kind is None: return
        fr = [m.ref for m in r.members if m.role == "from" and m.type == "w"]
        to = [m.ref for m in r.members if m.role == "to" and m.type == "w"]
        via = [m for m in r.members if m.role == "via"]
        if len(fr) != 1 or len(to) != 1 or len(via) != 1 or via[0].type != "n": s.rel.append(None); return
        s.rel.append((fr[0], via[0].ref, to[0], kind))

# Optional split of a large state: YWRP_BBOX="south,west,north,east" keeps whole ways with any node inside,
# so two halves share the nodes along the split line and join like neighbouring states.
import os
BBOX = [round(float(x)*1e6) for x in os.environ["YWRP_BBOX"].split(",")] if os.environ.get("YWRP_BBOX") else None

def hav(a, b):
    la1, lo1, la2, lo2 = a[0]/1e6, a[1]/1e6, b[0]/1e6, b[1]/1e6
    p = math.pi/180; x = math.sin((la2-la1)*p/2)**2 + math.cos(la1*p)*math.cos(la2*p)*math.sin((lo2-lo1)*p/2)**2
    return 12742000*math.asin(math.sqrt(x))

def main(src, dst):
    h = H(); h.apply_file(src, locations=True, idx="sparse_file_array")
    nid = {}; osm_of = []; lat = array.array("i"); lon = array.array("i")
    def node(r, p):
        i = nid.get(r)
        if i is None: i = nid[r] = len(lat); lat.append(p[0]); lon.append(p[1]); osm_of.append(r)
        return i
    strs = {"": 0}; strlist = [""]
    def S(x):
        i = strs.get(x)
        if i is None: i = strs[x] = len(strlist); strlist.append(x)
        return i
    labels = {(0,0,0): 0}; labellist = [(0,0,0)]
    shpLat = array.array("i"); shpLon = array.array("i")
    adj = []  # [from, to, lenDm, shapeStart, cnt, speed, flags, label, ctl, flags2, wayId]
    for wid, refs, pts, oneway, sp, cls, link, rb, tagged, (name, ref, dest), (lf, lb) in h.ways:
        key = (S(name), S(ref), S(dest))
        li = labels.get(key)
        if li is None: li = labels[key] = len(labellist); labellist.append(key)
        a = 0
        for j in range(1, len(refs)):
            if j != len(refs)-1 and h.use.get(refs[j], 0) < 2: continue
            seg = pts[a:j+1]
            L = sum(hav(seg[k], seg[k+1]) for k in range(len(seg)-1))
            sig = sum(1 for r in refs[a+1:j] if h.ctl.get(r, 0) & 1)
            stp = sum(1 for r in refs[a+1:j] if h.ctl.get(r, 0) & 6)
            ctl = (min(sig, 15) << 4) | min(stp, 15)
            u = node(refs[a], pts[a]); v = node(refs[j], pts[j])
            if u != v:
                ss = len(shpLat)
                for q in seg[1:-1]: shpLat.append(q[0]); shpLon.append(q[1])
                cnt = len(seg) - 2; dm = max(1, round(L*10)); fl = (cls << 1) | (32 if link else 0) | (64 if rb else 0)
                f2 = (tagged & 1) | (2 if (tagged & 2) or any(r in h.booth for r in refs[a:j+1]) else 0)
                if oneway >= 0: adj.append([u, v, dm, ss, cnt, sp, fl, li, ctl, f2, wid, S(lf)])
                if oneway <= 0: adj.append([v, u, dm, ss, cnt, sp, fl | 1, li, ctl, f2, wid, S(lb)])
            a = j
    n = len(lat)
    # urban grid
    deg = array.array("I", [0]*n)
    for e in adj: deg[e[0]] += 1; deg[e[1]] += 1
    cells = {}
    for i in range(n):
        if deg[i] >= 5:  # ~degree>=3 counting both directions of two-way streets
            c = (lat[i] // 10000, lon[i] // 10000); cells[c] = cells.get(c, 0) + 1
    for e in adj:
        c = ((lat[e[0]] + lat[e[1]]) // 2 // 10000, (lon[e[0]] + lon[e[1]]) // 2 // 10000)
        if cells.get(c, 0) >= URBAN_MIN: e[6] |= 128
    adj.sort(key=lambda e: e[0])
    first = array.array("I", [0]*(n+1))
    for e in adj: first[e[0]+1] += 1
    for i in range(n): first[i+1] += first[i]
    # restrictions
    into = {}; outof = {}
    for idx, e in enumerate(adj):
        into.setdefault((e[10], e[1]), []).append(idx); outof.setdefault((e[10], e[0]), []).append(idx)
    restr = []; skipped = sum(1 for r in h.rel if r is None); unmatched = 0
    for r in h.rel:
        if r is None: continue
        fw, via, tw, kind = r
        vn = nid.get(via)
        fe = into.get((fw, vn), []) if vn is not None else []; te = outof.get((tw, vn), []) if vn is not None else []
        if not fe or not te: unmatched += 1; continue
        for a in fe:
            for b in te: restr.append((a, b, kind))
    nodeCtl = bytearray(n)
    for i in range(n): nodeCtl[i] = h.ctl.get(osm_of[i], 0) & 31
    exits = [(nid[o], S(ref)) for o, ref in h.junc.items() if o in nid]
    blob = bytearray(); off = array.array("I")
    for s_ in strlist: off.append(len(blob)); blob += s_.encode("utf-8")
    off.append(len(blob))
    pad = lambda b: bytes(b) + bytes((-len(b)) % 4)
    with open(dst, "wb") as f:
        f.write(b"YWRP" + struct.pack("<8I4i", 3, n, len(adj), len(shpLat), len(strlist), len(labellist), len(restr), len(exits), min(lat), min(lon), max(lat), max(lon)))
        f.write(lat.tobytes()); f.write(lon.tobytes()); f.write(pad(nodeCtl)); f.write(first.tobytes())
        eb = bytearray()
        for e in adj: eb += struct.pack("<IIIHBB", e[1], e[2], e[3], min(e[4], 65535), e[5], e[6])
        f.write(eb)
        f.write(array.array("I", [e[7] for e in adj]).tobytes())
        f.write(pad(bytearray(e[8] for e in adj))); f.write(pad(bytearray(e[9] for e in adj)))
        f.write(shpLat.tobytes()); f.write(shpLon.tobytes())
        f.write(array.array("I", [x for l in labellist for x in l]).tobytes())
        f.write(array.array("I", [x for r in restr for x in r]).tobytes())
        f.write(array.array("I", [x for e in exits for x in e]).tobytes())
        f.write(array.array("I", [e[11] for e in adj]).tobytes())
        f.write(off.tobytes()); f.write(bytes(blob))
    urb = sum(1 for e in adj if e[6] & 128)
    print(f"nodes={n} edges={len(adj)} urban_edges={urb} shape={len(shpLat)} strings={len(strlist)} labels={len(labellist)} "
          f"restrictions={len(restr)} (relations {len(h.rel)}, unsupported via-way/multi {skipped}, unmatched {unmatched}) "
          f"exits={len(exits)} signal_nodes={sum(1 for c in nodeCtl if c & 1)} stop_nodes={sum(1 for c in nodeCtl if c & 6)} toll_edges={sum(1 for e in adj if e[9] & 2)} toll_booths={len(h.booth)}")

if __name__ == "__main__": main(sys.argv[1], sys.argv[2])
