"""Make a brand's rejected (DISAPPROVED) ads visible to Copilot.

Reads default.ad_rejections (written by meta/scripts/fetch-rejected-ads.js) plus the
pipeline's flattened docs (creative url per ad, from run-ad-staged output files) and writes,
for the target brand:
  meta_ads.ad_metrics_daily  one row per rejected ad: ad_effective_status=DISAPPROVED,
                              processed_fields={rejection_status, rejection_reason, rejection_message}
  default.ad_metadata_v3      one row per rejected ad (its created date, zero insights, creative url,
                              hash) so `view` / entity joins work

Usage:
  python3 loaders/sync_rejected_ads.py <source_brand_id> <target_brand_id> <staged_dir> [--account-map src=dst,...]
  env: CLICKHOUSE_URL, CLICKHOUSE_USER, CLICKHOUSE_PASSWORD
hash = md5(url)[:16] (the convention used when the target brand's ad_metadata_v3 was synthesised).
"""
import json, os, sys, glob, hashlib, argparse, urllib.request, urllib.parse, base64, datetime as dt

def ch_dt(iso):
    if not iso: return "1970-01-01 00:00:00"
    return dt.datetime.fromisoformat(iso.replace("+0530", "+05:30")).astimezone(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

ap = argparse.ArgumentParser()
ap.add_argument("source_brand"); ap.add_argument("target_brand"); ap.add_argument("staged_dir")
ap.add_argument("--dry-run", action="store_true")
ap.add_argument("--skip-snapshot", action="store_true")
a = ap.parse_args()

URL = os.environ.get("CLICKHOUSE_URL", "http://127.0.0.1:8123")
AUTH = base64.b64encode(f"{os.environ['CLICKHOUSE_USER']}:{os.environ['CLICKHOUSE_PASSWORD']}".encode()).decode()
def ch(q, body=None):
    req = urllib.request.Request(URL + "/?" + urllib.parse.urlencode({"query": q} if body else {}), data=(body or q).encode(), headers={"Authorization": "Basic " + AUTH})
    return urllib.request.urlopen(req, timeout=300).read().decode()

rej = [json.loads(l) for l in ch(f"SELECT * FROM default.ad_rejections FINAL WHERE brand_id='{a.source_brand}' FORMAT JSONEachRow").splitlines() if l]
print(f"{len(rej)} rejected ads for source brand")

staged = {}
for p in glob.glob(os.path.join(a.staged_dir, "*.staged.json")):
    for d in json.load(open(p)):
        staged[d["ad_id"]] = d
print(f"{len(staged)} staged docs with creatives")

now = dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
today = dt.date.today().isoformat()
snap, meta = [], []
for r in rej:
    d = staged.get(r["ad_id"], {})
    creative = d.get("creative") or {}
    url = creative.get("url") or ""
    h = hashlib.md5(url.encode()).hexdigest()[:16] if url else ""
    reason = " | ".join(r["rejection_reasons"]) if r["rejection_reasons"] else ""
    message = " | ".join(r["rejection_messages"]) if r.get("rejection_messages") else ""
    pf = {"rejection_status": r["effective_status"], "rejection_reason": reason, "rejection_message": message}
    snap.append({
        "brand_id": a.target_brand, "account_id": r["account_id"], "ad_id": r["ad_id"], "adset_id": r["adset_id"], "campaign_id": r["campaign_id"],
        "ad_name": r["ad_name"], "adset_name": d.get("adset_name") or "", "campaign_name": d.get("campaign_name") or "",
        "hash": h, "url": url, "media_type": d.get("media_type") or creative.get("type") or "",
        "campaign_objective": d.get("campaign_objective") or "", "optimization_goal": d.get("optimization_goal") or "APP_INSTALLS",
        "launched_time": r["created_time"][:19].replace("T", " "), "ad_status": r["status"], "ad_effective_status": r["effective_status"],
        "processed_fields": json.dumps(pf, ensure_ascii=False), "snapshot_date": today, "updated_at": now, "_version": int(dt.datetime.utcnow().timestamp()),
        "ad_issues_info": r["issues_info"], "ad_recommendations": r["recommendations"],
    })
    meta.append({
        "url": url, "brand_id": a.target_brand, "ad_id": r["ad_id"], "ad_name": r["ad_name"], "ad_status": r["status"], "ad_effective_status": r["effective_status"],
        "ad_issues_info": json.dumps({"rejection_reason": reason, "rejection_message": message, "ad_review_feedback": json.loads(r["ad_review_feedback"] or "{}")}, ensure_ascii=False),
        "ad_recommendations": r["recommendations"], "ad_created_time": ch_dt(r["created_time"]), "ad_updated_time": ch_dt(r["updated_time"]),
        "ad_preview_shareable_link": r["preview_shareable_link"], "creative": creative or {},
        "campaign_id": r["campaign_id"], "campaign_name": d.get("campaign_name") or "", "campaign_objective": d.get("campaign_objective") or "",
        "adset_id": r["adset_id"], "adset_name": d.get("adset_name") or "", "media_type": d.get("media_type") or creative.get("type") or "",
        "hash": h, "account_id": r["account_id"], "insights": {}, "daily_date": r["created_time"][:10], "channel": "meta",
        "time": now, "last_updated": now, "version": now, "fetch_id": "rejected-sync",
    })

print("with creative url:", sum(1 for m in meta if m["url"]), "| without:", sum(1 for m in meta if not m["url"]))
if a.dry_run:
    print(json.dumps(snap[0], ensure_ascii=False)[:600]); sys.exit(0)
if not a.skip_snapshot:
    ch("INSERT INTO meta_ads.ad_metrics_daily FORMAT JSONEachRow", "\n".join(json.dumps(r, ensure_ascii=False) for r in snap))
ch("INSERT INTO default.ad_metadata_v3 FORMAT JSONEachRow", "\n".join(json.dumps(r, ensure_ascii=False) for r in meta))
print(f"inserted {len(snap)} snapshot rows and {len(meta)} ad_metadata_v3 rows for brand {a.target_brand}")
