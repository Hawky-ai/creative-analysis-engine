#!/usr/bin/env python3
"""Copy ad rows from Mongo into ClickHouse `default.ad_metadata_v3` under a different brand id.

This is what makes a TEST BRAND usable. Entities alone give you a brand that looks empty,
because the UI reads ads, not entities - and an entity row whose hash matches no ad row is
invisible. It is also the path for a brand whose data only ever reached Mongo, because a
normal run was performed without a ClickHouse export.

One CH row per (media_type, daily_date, hash, ad_id) - the table's ORDER BY key.
The hash is the analysis service's own content hash (loaders/media_hash.py: phash for images,
sha256 over sampled frame hashes for video), mirrored into creative.analysis_hash /
creative.perceptual_hash so the entity join works and so the value matches what the real
pipeline would compute for the same creative.

  .venv/bin/python3 loaders/migrate_ads_ch.py <src_brand> <dst_brand> <from> <to> [--validate|--load]
  env: MONGO_URI, CLICKHOUSE_HTTP, CLICKHOUSE_USER, CLICKHOUSE_PASSWORD

--validate first, always. It flattens the source and diffs it against rows already in
ClickHouse for a period that has been migrated before, which is the only honest way to know
the field mapping is right. Meta metrics arrive as [{action_type, value}] lists and the
warehouse stores them flattened to <field>_<action_type>; getting that wrong is silent.

Two mappings that are not obvious and were found the hard way: the ad name is `name`, not
`ad_name`, and `ad_copy` is not stored on the source doc at all - the warehouse derives it
from `creative`.

--validate flattens the source and diffs it against rows already in ClickHouse instead of
writing anything. Nothing is written without --load.
"""
import os, sys, json, hashlib, argparse, urllib.request, urllib.parse, base64
from pymongo import MongoClient
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from media_hash import hash_url

HASH_WORKERS = int(os.environ.get("MIGRATE_HASH_WORKERS", "8"))
hash_failures = []

ap = argparse.ArgumentParser()
ap.add_argument("src_brand"); ap.add_argument("dst_brand")
ap.add_argument("date_from"); ap.add_argument("date_to")
ap.add_argument("--load", action="store_true")
ap.add_argument("--validate", action="store_true")
ap.add_argument("--limit", type=int)
a = ap.parse_args()

CH = os.environ.get("CLICKHOUSE_HTTP", "http://127.0.0.1:8123")
AUTH = base64.b64encode(f"{os.environ['CLICKHOUSE_USER']}:{os.environ['CLICKHOUSE_PASSWORD']}".encode()).decode()

# Meta returns these as [{action_type, value}]; the warehouse stores them flattened to
# <field>_<action_type>, with dots in the action type turned into underscores.
LIST_FIELDS = ["actions", "action_values", "conversions", "cost_per_action_type",
               "cost_per_outbound_click", "cost_per_unique_outbound_click",
               "outbound_clicks", "outbound_clicks_ctr", "purchase_roas",
               "unique_outbound_clicks", "unique_outbound_clicks_ctr", "website_ctr",
               "video_p25_watched_actions", "video_p50_watched_actions",
               "video_p75_watched_actions", "video_p95_watched_actions",
               "video_p100_watched_actions", "video_play_actions",
               "video_thruplay_watched_actions"]

def num(v):
    try:
        f = float(v)
        return int(f) if f.is_integer() else f
    except (TypeError, ValueError):
        return v

def flatten_insights(e):
    out = {}
    for k, v in e.items():
        if k in LIST_FIELDS and isinstance(v, list):
            for item in v:
                if isinstance(item, dict) and "action_type" in item:
                    out[f"{k}_{item['action_type'].replace('.', '_')}"] = num(item.get("value"))
        elif k == "video_play_curve_actions" and isinstance(v, list):
            for item in v:
                if isinstance(item, dict) and "action_type" in item:
                    out[f"{k}_{item['action_type'].replace('.', '_')}"] = item.get("value")
        else:
            out[k] = num(v)
    return out

def dt(v, default="1970-01-01 00:00:00"):
    if not v: return default
    s = str(v)
    return s.replace("T", " ")[:19] if len(s) >= 10 else default

# Hashes come from media_hash, which reimplements the analysis service's algorithm, so rows
# pushed here carry the SAME hash the pipeline would compute. HASH_MAP is filled in before
# row_for runs (hashing downloads media, so it happens once per url, in parallel).
HASH_MAP = {}
HASH_META = {}

def row_for(d, ins):
    url = d.get("primary_media_url") or ""
    h = HASH_MAP.get(url, "")
    cr = dict(d.get("creative") or {})
    if h:
        cr["analysis_hash"] = h
        cr["perceptual_hash"] = h
    meta = HASH_META.get(url) or {}
    day = (ins.get("date_start") or d.get("daily_date") or "")[:10]
    return {
        "url": url, "brand_id": a.dst_brand, "ad_id": str(d.get("ad_id") or ""),
        "media_asset_id": str(d.get("asset_id") or ""),
        # the source calls it `name`; there is no ad_name key
        "ad_name": d.get("name") or d.get("ad_name") or "", "ad_status": d.get("ad_status") or "",
        "ad_effective_status": d.get("ad_effective_status") or "",
        "ad_issues_info": json.dumps(d.get("ad_issues_info") or []),
        "ad_recommendations": json.dumps(d.get("ad_recommendations") or []),
        "ad_created_time": dt(d.get("ad_created_time")), "ad_updated_time": dt(d.get("ad_updated_time")),
        "ad_preview_shareable_link": d.get("ad_preview_shareable_link") or "",
        # ad_copy is not stored on the source doc - the warehouse derives it from creative
        "creative": cr, "ad_copy": {k: cr.get(k, "" if not k.endswith("_variants") else [])
                                    for k in ("cta", "cta_variants", "description",
                                              "description_variants", "headline",
                                              "headline_variants", "primary_text",
                                              "primary_text_variants", "url_tags")},
        "campaign_id": str(d.get("campaign_id") or ""), "campaign_name": d.get("campaign_name") or "",
        "campaign_objective": d.get("campaign_objective") or "",
        "campaign_status": d.get("campaign_status") or "",
        "campaign_effective_status": d.get("campaign_effective_status") or "",
        "campaign_start_time": dt(d.get("campaign_start_time")),
        "campaign_created_time": dt(d.get("campaign_created_time")),
        "campaign_updated_time": dt(d.get("campaign_updated_time")),
        "campaign_daily_budget": num(d.get("campaign_daily_budget") or 0),
        "campaign_budget_rebalance_flag": bool(d.get("campaign_budget_rebalance_flag")),
        "campaign_bid_strategy": d.get("campaign_bid_strategy") or "",
        "campaign_buying_type": d.get("campaign_buying_type") or "",
        "channel": "meta_ads", "campaign_type": d.get("campaign_type") or "",
        "adset_id": str(d.get("adset_id") or ""), "adset_name": d.get("adset_name") or "",
        "adset_status": d.get("adset_status") or "",
        "adset_effective_status": d.get("adset_effective_status") or "",
        "adset_start_time": dt(d.get("adset_start_time")),
        "adset_created_time": dt(d.get("adset_created_time")),
        "adset_updated_time": dt(d.get("adset_updated_time")),
        "adset_budget_remaining": num(d.get("adset_budget_remaining") or 0),
        "adset_bid_amount": num(d.get("adset_bid_amount") or 0),
        "adset_account_id": str(d.get("adset_account_id") or ""),
        "media_type": d.get("primary_media_type") or d.get("media_type") or "",
        "aspect_ratio": meta.get("aspect") or d.get("aspect_ratio") or "", "hash": h,
        "targeting": d.get("targeting") or {},
        "account_id": d.get("account_id") or "",
        "time": dt(d.get("time") or d.get("ad_updated_time")), "fetch_id": str(d.get("fetch_id") or ""),
        "cache_id": a.dst_brand,
        "video_duration": num(meta.get("duration") or d.get("video_duration") or 0),
        "insights": flatten_insights(ins), "daily_date": day,
        "label": d.get("label") or {},
    }

# The SSM tunnel stalls under sustained load and the driver gives up. Reconnect and retry
# rather than losing a two-month migration to a transient forwarding hiccup.
import time
def connect():
    cl = MongoClient(os.environ["MONGO_URI"], serverSelectionTimeoutMS=20000,
                     socketTimeoutMS=120000, connectTimeoutMS=20000)
    return cl["meta_ads_db_final"]["themetaadsprocessed_final"]

col = connect()

def with_retry(fn, what, tries=8):
    global col
    for i in range(1, tries + 1):
        try:
            return fn()
        except Exception as e:
            if i == tries:
                raise
            print(f"  ! {what} failed ({type(e).__name__}), reconnecting in {5*i}s", flush=True)
            time.sleep(5 * i)
            try: col = connect()
            except Exception: pass
q = {"brand_id": a.src_brand, "daily_date": {"$gte": a.date_from, "$lt": a.date_to}}

# `daily_date` on the source is the FETCH marker, not the metric day: a whole month of
# documents shares one value (7,585 docs on 2026-06-01). So paging by date degenerates into a
# single enormous cursor that outruns the tunnel. Page by _id instead - short queries, and a
# rerun costs nothing because the target is a ReplacingMergeTree.
from bson import ObjectId

def insert(batch):
    if not batch: return
    cols = list(batch[0].keys())
    q = urllib.parse.quote(f"INSERT INTO default.ad_metadata_v3 ({','.join(cols)}) FORMAT JSONEachRow")
    body = "\n".join(json.dumps(r, ensure_ascii=False) for r in batch).encode()
    req = urllib.request.Request(f"{CH}/?query={q}", data=body, headers={"Authorization": "Basic " + AUTH})
    with_retry(lambda: urllib.request.urlopen(req, timeout=300), "clickhouse insert")

def ch_query(sql):
    req = urllib.request.Request(CH + "/?query=" + urllib.parse.quote(sql),
                                 headers={"Authorization": "Basic " + AUTH})
    return urllib.request.urlopen(req, timeout=60).read().decode()

PAGE = 150
last_id = None
total = docs_seen = skipped = 0
checked = identical = differing = 0

while True:
    def page():
        qq = {"brand_id": a.src_brand, "daily_date": {"$gte": a.date_from, "$lt": a.date_to}}
        if last_id is not None:
            qq["_id"] = {"$gt": last_id}
        return list(col.find(qq).sort("_id", 1).limit(PAGE))
    docs = with_retry(page, f"page after {last_id}")
    if not docs:
        break
    last_id = docs[-1]["_id"]

    # hash every new url in this page once, in parallel - this downloads media, so it is the
    # slow part of the migration and must not be repeated per insights row
    todo = {d["primary_media_url"]: (d.get("primary_media_type") or "video")
            for d in docs if d.get("primary_media_url") and d["primary_media_url"] not in HASH_MAP}
    if todo:
        with ThreadPoolExecutor(max_workers=HASH_WORKERS) as pool:
            futs = {pool.submit(hash_url, u, mt): u for u, mt in todo.items()}
            for fut in as_completed(futs):
                u = futs[fut]
                try:
                    h, dur, ar = fut.result()
                    HASH_MAP[u] = h
                    HASH_META[u] = {"duration": dur, "aspect": ar}
                except Exception as e:
                    HASH_MAP[u] = ""          # no invented value: a bad hash is worse than none
                    hash_failures.append((u, str(e)[:80]))

    rows = []
    for d in docs:
        if not d.get("primary_media_url"):
            skipped += 1; continue
        if not HASH_MAP.get(d["primary_media_url"]):
            continue                          # unhashable media is skipped, and counted below
        for ins in (d.get("insights") or [{}]):
            rows.append(row_for(d, ins))
    docs_seen += len(docs); total += len(rows)

    if a.validate:
        # diff what we WOULD write against rows already in ClickHouse; write nothing
        for r in rows:
            if checked >= (a.limit or 40):
                break
            got = ch_query(
                f"SELECT toString(insights) FROM default.ad_metadata_v3 FINAL "
                f"WHERE brand_id='{a.dst_brand}' AND hash='{r['hash']}' AND ad_id='{r['ad_id']}' "
                f"AND daily_date='{r['daily_date']}' LIMIT 1 FORMAT TSVRaw").strip()
            if not got:
                continue
            checked += 1
            mine, theirs = r["insights"], json.loads(got)
            bad = {k: (mine.get(k), theirs.get(k)) for k in set(mine) | set(theirs)
                   if str(mine.get(k)) != str(theirs.get(k))
                   and k not in ("ad_id", "fetch_id", "fetch_day_id")}
            if bad:
                differing += 1
                if differing <= 3:
                    print(f"  DIFF {r['hash']} {r['daily_date']}: {dict(list(bad.items())[:6])}")
            else:
                identical += 1
        if checked >= (a.limit or 40):
            break
        continue

    if not a.load:
        print(f"dry run - {len(rows)} rows from the first {len(docs)} docs; pass --load to write")
        print(json.dumps(rows[0], ensure_ascii=False)[:600])
        sys.exit(0)

    for i in range(0, len(rows), 2000):
        insert(rows[i:i+2000])
    print(f"  {docs_seen:>6,} docs -> {total:>7,} rows", flush=True)

if a.validate:
    print(f"validated against existing ClickHouse rows: {identical} identical, {differing} differing "
          f"(fetch_id/fetch_day_id ignored - they record which run wrote the row)")
    sys.exit(0)

print(f"loaded {total:,} rows; {skipped} skipped with no media url; "
      f"{len(hash_failures)} media could not be hashed")
for u, e in hash_failures[:5]:
    print(f"  unhashable: {e}  {u[:90]}")
