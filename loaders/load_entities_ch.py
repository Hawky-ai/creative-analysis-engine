"""Load extracted observations into ClickHouse `default.extracted_entities_v2`
(the per-creative entity table Copilot's include_entities path reads).

Groups observations per hash into one flat JSON object {facet: "v1, v2"}, optionally
publishing each facet under alias names the consuming prompt library expects.

Usage:
  python3 loaders/load_entities_ch.py <obs.json> <brand_id> [--aliases aliases.json] [--dry-run]
  CH endpoint: env CLICKHOUSE_URL (default http://127.0.0.1:8123), auth CLICKHOUSE_USER/PASSWORD.

extracted_entities_v2 is a ReplacingMergeTree on (hash) versioned by insert time:
loading is non-destructive — old rows survive on disk until merge; a re-load of older
data 'reverts' what FINAL reads. Never DELETE to undo a load; load the previous state back.
"""
import json, os, sys, argparse, urllib.request, urllib.parse, base64
from collections import defaultdict

ap = argparse.ArgumentParser()
ap.add_argument("obs_json")
ap.add_argument("brand_id")
ap.add_argument("--aliases", help="JSON {facet: [alias, ...]} — publish facet under extra names")
ap.add_argument("--dry-run", action="store_true")
a = ap.parse_args()

aliases = json.load(open(a.aliases)) if a.aliases else {}
rows_out = []
for r in json.load(open(a.obs_json)):
    if not isinstance(r.get("obs"), list): continue
    grouped = defaultdict(list)
    for o in r["obs"]:
        v = str(o["value"])
        if v not in grouped[o["facet"]]: grouped[o["facet"]].append(v)
    ent = {}
    for f, vals in grouped.items():
        joined = ", ".join(vals)[:500]
        ent[f] = joined
        for al in aliases.get(f, []): ent[al] = joined
    rows_out.append({"hash": r["hash"], "brand_id": a.brand_id, "extracted_entities": ent})

print(f"{len(rows_out)} entity rows for brand {a.brand_id}")
if a.dry_run:
    print(json.dumps(rows_out[0], indent=1)[:600]); sys.exit(0)

url = os.environ.get("CLICKHOUSE_URL", "http://127.0.0.1:8123")
auth = base64.b64encode(f"{os.environ['CLICKHOUSE_USER']}:{os.environ['CLICKHOUSE_PASSWORD']}".encode()).decode()
q = urllib.parse.quote("INSERT INTO default.extracted_entities_v2 (hash, brand_id, extracted_entities) FORMAT JSONEachRow")
body = "\n".join(json.dumps(r, ensure_ascii=False) for r in rows_out).encode()
req = urllib.request.Request(f"{url}/?query={q}", data=body, headers={"Authorization": "Basic " + auth})
urllib.request.urlopen(req, timeout=300)
print("loaded.")
