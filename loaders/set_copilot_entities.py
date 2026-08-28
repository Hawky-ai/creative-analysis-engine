"""Register this vertical's facets as the brand's creative attributes in Copilot.

Copilot derives a brand's attribute names from its Mongo `metrics` doc:
  tags.data.<name>            -> the attribute exists (value: list of known values)
  tags.keyFields.<name>.type  -> "Video" | "Image" | "All" (which media it applies to)
Nothing else tells the agent that a facet like `address_mode` is queryable, and
`creative_group_by` rejects any dimension not in this list.

Usage:
  python3 loaders/set_copilot_entities.py <brand_id> <facets.json> [--media Video|Image|All]
                                          [--obs obs.json]
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
a = ap.parse_args()

facets = [k for k in json.load(open(a.facets_json)) if not k.startswith("_")]
values = defaultdict(set)
if a.obs:
    for r in json.load(open(a.obs)):
        for o in r.get("obs") or []:
            if o["facet"] in facets and o["facet"] != "scene_description":
                values[o["facet"]].add(str(o["value"]).strip().lower())

db = MongoClient(os.environ["MONGO_URI"], serverSelectionTimeoutMS=8000)[os.environ.get("MONGO_DB_NAME", "test")]
col = db["metrics"]
doc = col.find_one({"brandId": ObjectId(a.brand_id)}, {"_id": 1, "tags": 1})
if not doc:
    sys.exit(f"no metrics doc for brand {a.brand_id}")

tags = doc.get("tags") or {}
data = dict(tags.get("data") or {})
key_fields = dict(tags.get("keyFields") or {})
added = 0
for f in facets:
    if f not in data:
        added += 1
    data[f] = sorted(values[f])[:200] if values[f] else data.get(f, [])
    key_fields[f] = {**(key_fields.get(f) or {}), "type": a.media}

col.update_one({"_id": doc["_id"]}, {"$set": {"tags.data": data, "tags.keyFields": key_fields}})
print(f"brand {a.brand_id}: {len(facets)} facets registered ({added} new), media={a.media}, total attributes now {len(data)}")
