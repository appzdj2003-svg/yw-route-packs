#!/usr/bin/env python3
"""Build a compact driving-route pack (format YWRP v1) from an OpenStreetMap .osm.pbf extract.

Data: (c) OpenStreetMap contributors, ODbL 1.0. The output pack is a Derivative Database and is
offered under the ODbL 1.0 (https://opendatacommons.org/licenses/odbl/1-0/). This script: MIT.

Usage: python3 build_pack.py south-carolina-latest.osm.pbf sc.ywrp
Format (little-endian):
  header  "YWRP" u32 ver=1, u32 nNodes, u32 nEdges, u32 nShape, u32 nNames, i32 minLat,minLon,maxLat,maxLon (1e-6 deg)
  i32 lat[nNodes], i32 lon[nNodes]                     graph nodes (intersections / dead ends)
  u32 first[nNodes+1]                                  CSR offsets into edges
  edges (nEdges x 16 bytes): u32 to, u32 lenDm, u32 shapeStart, u16 shapeCount, u8 speedKmh, u8 flags
      flags bit0 = shape stored reversed, bits1-4 = road class (0 motorway .. 9 living_street), bit5 = link
  i32 shapeLat[nShape], i32 shapeLon[nShape]           interior points of segments (excl. endpoints)
  u32 nameEdge[nEdges]                                 name index per edge
  u32 nameOff[nNames+1], utf8 names blob
"""
import sys, struct, math, re, array
import osmium

CLS = {"motorway":0,"trunk":1,"primary":2,"secondary":3,"tertiary":4,"unclassified":5,"residential":6,
       "motorway_link":0,"trunk_link":1,"primary_link":2,"secondary_link":3,"tertiary_link":4,"living_street":9}
DEF_KMH = {0:105,1:89,2:72,3:64,4:56,5:48,6:40,9:16}
LINK_KMH = 56

def parse_speed(v):
    if not v: return None
    m = re.match(r"\s*(\d+(?:\.\d+)?)\s*(mph|km/h|kmh)?", v)
    if not m: return None
    s = float(m.group(1))
    return s * 1.609344 if (m.group(2) == "mph" or (m.group(2) is None and "mph" in v)) else s

class Ways(osmium.SimpleHandler):
    def __init__(s):
        super().__init__(); s.ways = []; s.use = {}
    def way(s, w):
        t = w.tags; hw = t.get("highway")
        if hw not in CLS: return
        if t.get("area") == "yes": return
        if t.get("access") in ("no","private") or t.get("motor_vehicle") in ("no","private") or t.get("motorcar") in ("no","private"): return
        cls = CLS[hw]; link = hw.endswith("_link")
        ow = t.get("oneway", "")
        oneway = 1 if ow in ("yes","1","true") else (-1 if ow == "-1" else 0)
        if oneway == 0 and (hw in ("motorway","motorway_link") or t.get("junction") in ("roundabout","circular")) and ow != "no": oneway = 1
        sp = parse_speed(t.get("maxspeed")) if "maxspeed" in t else None
        if sp is None: sp = LINK_KMH if link and cls <= 1 else DEF_KMH[cls]
        sp = max(5, min(130, round(sp)))
        name = t.get("name", ""); ref = t.get("ref", "")
        label = (name + (" (" + ref + ")" if ref and name else "")) if name else ref
        refs = []; pts = []
        for n in w.nodes:
            if not n.location.valid(): continue
            refs.append(n.ref); pts.append((round(n.location.lat*1e6), round(n.location.lon*1e6)))
        if len(refs) < 2: return
        for i, r in enumerate(refs):
            s.use[r] = s.use.get(r, 0) + (2 if i in (0, len(refs)-1) else 1)
        s.ways.append((refs, pts, oneway, sp, cls, link, label))

def hav(a, b):
    la1, lo1, la2, lo2 = a[0]/1e6, a[1]/1e6, b[0]/1e6, b[1]/1e6
    p = math.pi/180; x = math.sin((la2-la1)*p/2)**2 + math.cos(la1*p)*math.cos(la2*p)*math.sin((lo2-lo1)*p/2)**2
    return 12742000*math.asin(math.sqrt(x))

def main(src, dst):
    h = Ways(); h.apply_file(src, locations=True, idx="sparse_file_array")
    nid = {}; lat = array.array("i"); lon = array.array("i")
    def node(r, p):
        i = nid.get(r)
        if i is None: i = nid[r] = len(lat); lat.append(p[0]); lon.append(p[1])
        return i
    names = {"": 0}; namelist = [""]
    shpLat = array.array("i"); shpLon = array.array("i")
    adj = []  # (from, to, lenDm, shapeStart, shapeCount, speed, flags, name)
    for refs, pts, oneway, sp, cls, link, label in h.ways:
        ni = names.get(label)
        if ni is None: ni = names[label] = len(namelist); namelist.append(label)
        a = 0
        for j in range(1, len(refs)):
            if j != len(refs)-1 and h.use.get(refs[j], 0) < 2: continue
            seg = pts[a:j+1]
            L = sum(hav(seg[k], seg[k+1]) for k in range(len(seg)-1))
            u = node(refs[a], pts[a]); v = node(refs[j], pts[j])
            if u != v:
                ss = len(shpLat)
                for q in seg[1:-1]: shpLat.append(q[0]); shpLon.append(q[1])
                cnt = len(seg) - 2; dm = max(1, round(L*10)); fl = (cls << 1) | (32 if link else 0)
                if oneway >= 0: adj.append((u, v, dm, ss, cnt, sp, fl, ni))
                if oneway <= 0: adj.append((v, u, dm, ss, cnt, sp, fl | 1, ni))
            a = j
    adj.sort(key=lambda e: e[0])
    n = len(lat); first = array.array("I", [0]*(n+1))
    for e in adj: first[e[0]+1] += 1
    for i in range(n): first[i+1] += first[i]
    blob = bytearray(); off = array.array("I")
    for s in namelist: off.append(len(blob)); blob += s.encode("utf-8")
    off.append(len(blob))
    with open(dst, "wb") as f:
        f.write(b"YWRP" + struct.pack("<5I4i", 1, n, len(adj), len(shpLat), len(namelist), min(lat), min(lon), max(lat), max(lon)))
        f.write(lat.tobytes()); f.write(lon.tobytes()); f.write(first.tobytes())
        eb = bytearray()
        for e in adj: eb += struct.pack("<IIIHBB", e[1], e[2], e[3], min(e[4], 65535), e[5], e[6])
        f.write(eb); f.write(shpLat.tobytes()); f.write(shpLon.tobytes())
        f.write(array.array("I", [e[7] for e in adj]).tobytes())
        f.write(off.tobytes()); f.write(bytes(blob))
    print(f"nodes={n} edges={len(adj)} shape={len(shpLat)} names={len(namelist)}")

if __name__ == "__main__": main(sys.argv[1], sys.argv[2])
