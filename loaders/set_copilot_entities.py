"""Register this vertical's facets as the brand's creative attributes in Copilot.

Copilot derives a brand's attribute names from its Mongo `metrics` doc:
  tags.data.<name>            -> the attribute exists (value: list of known values)
  tags.keyFields.<name>.type  -> "Video" | "Image" | "All" (which media it applies to)
Nothing else tells the agent that a facet like `address_mode` is queryable, and
`creative_group_by` rejects any dimension not in this list.

Also sets `explodeEntityArrays: true` on the doc — the per-brand switch that makes Copilot's
group-by fan out array-valued facets. Brands without the flag keep the original behaviour.

A brand created by hand has no metrics doc at all, and Copilot needs one before any of this
means anything. --from-brand clones the source brand's doc (new _id, new brandId, attributes
cleared) so a fresh test brand works without hand-editing Mongo.

Usage:
  .venv/bin/python3 loaders/set_copilot_entities.py <brand_id> <facets.json>
      [--media Video|Image|All] [--obs obs.json] [--from-brand <source_brand_id>]
  env: MONGO_URI, MONGO_DB_NAME (default test)

facets.json: {"facet": "one-line meaning", ...}. Keys starting with '_' are payloads and
are skipped. --obs fills each facet's known-values list from the observations.
Existing keys the brand already had are left untouched. Idempotent.
"""
import json, os, sys, argparse
from collections import defaultdict
from pymongo import MongoClient
from bson import ObjectId

ap = argparse.ArgumentParser()
ap.add_argument("brand_id")
ap.add_argument("facets_json")
ap.add_argument("--media", choices=["Video", "Image", "All"], default="All")
ap.add_argument("--obs", help="observations JSON — fills known values per facet")
ap.add_argument("--from-brand", dest="from_brand",
                help="clone this brand's metrics doc if the target has none (for a new test brand)")
a = ap.parse_args()

facets = [k for k in json.load(open(a.facets_json)) if not k.startswith("_")]
values = defaultdict(set)
if a.obs:
    for r in json.load(open(a.obs)):
        # a creative the model refused leaves obs as an {"error": ...} dict, not a list;
        # iterating that yields strings and used to abort the whole registration
        if not isinstance(r.get("obs"), list):
            continue
        for o in r["obs"]:
            if not isinstance(o, dict) or "facet" not in o or "value" not in o:
                continue
            if o["facet"] in facets and o["facet"] != "scene_description":
                values[o["facet"]].add(str(o["value"]).strip().lower())

db = MongoClient(os.environ["MONGO_URI"], serverSelectionTimeoutMS=8000)[os.environ.get("MONGO_DB_NAME", "test")]
col = db["metrics"]
doc = col.find_one({"brandId": ObjectId(a.brand_id)}, {"_id": 1, "tags": 1})
if not doc and a.from_brand:
    src = col.find_one({"brandId": ObjectId(a.from_brand)})
    if not src:
        sys.exit(f"--from-brand {a.from_brand} has no metrics doc either")
    src.pop("_id", None)
    src["brandId"] = ObjectId(a.brand_id)
    # Start the test brand with an empty attribute list: the source brand's values describe the
    # source brand's creatives, and carrying them over makes the UI offer attributes this run
    # never extracted.
    src["tags"] = {**(src.get("tags") or {}), "data": {}, "keyFields": {}}
    new_id = col.insert_one(src).inserted_id
    print(f"cloned metrics doc from brand {a.from_brand} -> new doc {new_id}")
    doc = col.find_one({"_id": new_id}, {"_id": 1, "tags": 1})
if not doc:
    sys.exit(f"no metrics doc for brand {a.brand_id} "
             f"(pass --from-brand <source_brand_id> to clone one)")

tags = doc.get("tags") or {}
data = dict(tags.get("data") or {})
key_fields = dict(tags.get("keyFields") or {})
added = 0
for f in facets:
    if f not in data:
        added += 1
    data[f] = sorted(values[f])[:200] if values[f] else data.get(f, [])
    key_fields[f] = {**(key_fields.get(f) or {}), "type": a.media}

col.update_one({"_id": doc["_id"]},
               {"$set": {"tags": {**tags, "data": data, "keyFields": key_fields},
                         "explodeEntityArrays": True}})
print(f"brand {a.brand_id}: {len(facets)} facets registered ({added} new), media={a.media}, total attributes now {len(data)}")
