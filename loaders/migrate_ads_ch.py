#!/usr/bin/env python3
"""Copy ad rows from Mongo into ClickHouse `default.ad_metadata_v3` under a different brand id.

This is what makes a TEST BRAND usable. Entities alone give you a brand that looks empty,
because the UI reads ads, not entities - and an entity row whose hash matches no ad row is
invisible. It is also the path for a brand whose data only ever reached Mongo, because a
normal run was performed without a ClickHouse export.

One CH row per (media_type, daily_date, hash, ad_id) - the table's ORDER BY key.
hash is md5(primary_media_url)[:16], the surrogate this brand already uses, and it is
mirrored into creative.analysis_hash / creative.perceptual_hash so the entity join works.

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

def row_for(d, ins):
    url = d.get("primary_media_url") or ""
    h = hashlib.md5(url.encode()).hexdigest()[:16] if url else ""
    cr = dict(d.get("creative") or {})
    if h:
        cr["analysis_hash"] = h
        cr["perceptual_hash"] = h
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
        "aspect_ratio": d.get("aspect_ratio") or "", "hash": h,
        "targeting": d.get("targeting") or {},
        "account_id": d.get("account_id") or "",
        "time": dt(d.get("time") or d.get("ad_updated_time")), "fetch_id": str(d.get("fetch_id") or ""),
        "cache_id": a.dst_brand,
        "video_duration": num(d.get("video_duration") or 0),
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

# One query per day. A single find() over two months outstrips the cursor timeout and dies
# with _OperationCancelled partway through; per-day queries also make a rerun cheap.
import datetime
def days(f, t):
    d0 = datetime.date.fromisoformat(f); d1 = datetime.date.fromisoformat(t)
    while d0 < d1:
        yield d0.isoformat(); d0 += datetime.timedelta(days=1)

def fetch_day(day):
    def go():
        out, skip = [], 0
        for d in col.find({"brand_id": a.src_brand, "daily_date": day}, batch_size=200):
            if not d.get("primary_media_url"):
                skip += 1; continue
            for ins in (d.get("insights") or [{}]):
                out.append(row_for(d, ins))
        return out, skip
    return with_retry(go, f"fetch {day}")

rows, skipped = [], 0
if a.validate or not a.load:
    for day in days(a.date_from, a.date_to):
        r, s_ = fetch_day(day)
        rows += r; skipped += s_
        if a.limit and len(rows) >= a.limit: break
    print(f"source docs -> {len(rows)} CH rows ({skipped} skipped, no media url)")

if a.validate:
    def ch(q):
        req = urllib.request.Request(CH + "/?query=" + urllib.parse.quote(q),
                                     headers={"Authorization": "Basic " + AUTH})
        return urllib.request.urlopen(req, timeout=60).read().decode()
    ok = diff = 0
    for r in rows[:a.limit or 20]:
        got = ch(f"SELECT toString(insights) FROM default.ad_metadata_v3 FINAL "
                 f"WHERE brand_id='{a.dst_brand}' AND hash='{r['hash']}' "
                 f"AND ad_id='{r['ad_id']}' AND daily_date='{r['daily_date']}' LIMIT 1 FORMAT TSVRaw").strip()
        if not got:
            continue
        mine, theirs = r["insights"], json.loads(got)
        keys = set(mine) | set(theirs)
        bad = {k: (mine.get(k), theirs.get(k)) for k in keys
               if str(mine.get(k)) != str(theirs.get(k)) and k != "ad_id"}
        if bad:
            diff += 1
            if diff <= 3:
                print(f"  DIFF {r['hash']} {r['daily_date']}: {dict(list(bad.items())[:6])}")
        else:
            ok += 1
    print(f"validated against existing CH rows: {ok} identical, {diff} differing")
    sys.exit(0)

if not a.load:
    print("dry run - pass --load to write"); print(json.dumps(rows[0], ensure_ascii=False)[:600]); sys.exit(0)

def insert(batch):
    if not batch: return
    cols = list(batch[0].keys())
    q = urllib.parse.quote(f"INSERT INTO default.ad_metadata_v3 ({','.join(cols)}) FORMAT JSONEachRow")
    body = "\n".join(json.dumps(r, ensure_ascii=False) for r in batch).encode()
    req = urllib.request.Request(f"{CH}/?query={q}", data=body, headers={"Authorization": "Basic " + AUTH})
    with_retry(lambda: urllib.request.urlopen(req, timeout=300), "clickhouse insert")

total = 0
for day in days(a.date_from, a.date_to):
    r, s_ = fetch_day(day)
    for i in range(0, len(r), 2000):
        insert(r[i:i+2000])
    total += len(r); skipped += s_
    print(f"  {day}: {len(r):>6} rows  (total {total:,})", flush=True)
print(f"loaded {total:,} rows; {skipped} skipped with no media url")
