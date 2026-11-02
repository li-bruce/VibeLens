"""Independently compare retained rendered ports with their exact owners' geometry."""
from collections import Counter
import json
import math
from pathlib import Path
OUT=Path(__file__).resolve().parent
checks=[];errors=[]
for dimension in ("2d","3d"):
    axes=("x","y") if dimension=="2d" else ("x","y","z")
    for shape in ("straight","curve","orthogonal","bus"):
        value=json.loads((OUT/("routes-"+dimension+"-"+shape+".json")).read_text(encoding="utf-8"))
        edges={edge["id"]:edge for edge in value["edges"]}
        boxes={box["id"]:box for box in value["boxes"]}
        ports=value["ports"] if dimension=="2d" else value["spatial"]["edgePorts"]
        for port in ports:
            if port["id"].startswith("projection:"):continue
            edge=edges[port["id"]]
            for side,endpoint in (("start","from"),("end","to")):
                owner=edge[endpoint];point=port[side]
                center=boxes[owner]["point"] if dimension=="2d" else value["positions"][owner]
                distance=math.dist([point[axis] for axis in axes],[center[axis] for axis in axes])
                match="owner_center" if distance<.01 else None
                if match is None:
                    volumes=[r for r in value["regions"] if r["id"]==owner] if dimension=="2d" else [v for v in value["spatial"]["volumes"] if v["id"]==owner]
                    for volume in volumes:
                        c={"x":volume["cx"],"y":volume["cy"]} if dimension=="2d" else volume["center"]
                        radius=volume["radius"]
                        plane_ok=dimension=="2d" or abs(point["y"]-c["y"])<.01
                        radial=math.dist([point[axis] for axis in axes],[c[axis] for axis in axes])
                        if plane_ok and abs(radial-radius)<.01:match="owner_region_boundary";break
                row={"dimension":dimension,"shape":shape,"edge":port["id"],"endpoint":side,"owner":owner,"matches":match}
                checks.append(row)
                if match is None:errors.append({**row,"point":point,"center":center,"distance":distance})
result={"valid":not errors,"checked_endpoints":len(checks),"matches":dict(Counter(check["matches"] for check in checks)),"errors":errors,"checks":checks,
    "boundary":"Checks owner identity, exact node center or that same owner's actual region circumference/semantic plane. It does not certify optimal crossings, labels, or unseen graph geometries."}
(OUT/"port-geometry-audit.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
print(json.dumps({key:result[key] for key in ("valid","checked_endpoints","matches","errors")}))
assert not errors
