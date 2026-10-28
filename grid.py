"""Owner grid: for each 0.05° cell, the pack with the most graph nodes there. Writes app asset pack_grid.bin:
"YWPG" u32 ver=1, i32 lat0e2, lon0e2 (×100), u16 rows, cols, u8 nIds, then nIds × (u8 len, ascii id), then rows*cols u8 (0 = none, k = ids[k-1])."""
import struct, sys, array, collections
ids = sys.argv[2:]; out = sys.argv[1]
LAT0, LON0, STEP = 30.0, -85.0, 0.05
ROWS, COLS = int((45.2-LAT0)/STEP)+1, int((-69.8-LON0)/STEP)+1
cnt = [collections.Counter() for _ in range(ROWS*COLS)]
for k, pid in enumerate(ids, 1):
    path = next(p for p in (f"/workspace/routepack/v4/{pid}.ywrp", f"/workspace/routepack/v3/{pid}.ywrp", f"/workspace/routepack/v2/{pid}.ywrp") if __import__("os").path.exists(p))
    b = open(path, "rb").read()
    n = struct.unpack_from("<I", b, 8)[0]; off = 4 + 4 + 7*4 + 4*4
    lat = array.array("i"); lat.frombytes(b[off:off+4*n]); lon = array.array("i"); lon.frombytes(b[off+4*n:off+8*n])
    for a, o in zip(lat, lon):
        r = int((a/1e6-LAT0)/STEP); c = int((o/1e6-LON0)/STEP)
        if 0 <= r < ROWS and 0 <= c < COLS: cnt[r*COLS+c][k] += 1
grid = bytes((c.most_common(1)[0][0] if c else 0) for c in cnt)
with open(out, "wb") as f:
    f.write(b"YWPG" + struct.pack("<IiiHHB", 1, int(LAT0*100), int(LON0*100), ROWS, COLS, len(ids)))
    for i in ids: f.write(bytes([len(i)]) + i.encode())
    f.write(grid)
print(ROWS, COLS, sum(1 for g in grid if g), "cells owned")
