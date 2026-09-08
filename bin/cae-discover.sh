#!/bin/sh
# Read an account's shape out of the warehouse before any prompt is written.
#
# Assumes the Hawky warehouse layout: default.ad_metadata_v3 is one row per ad per day with the
# creative payload, and default.extracted_entities_v2 holds entities keyed by hash.
# Reads only. Run it through the secret manager so CLICKHOUSE_USER/PASSWORD are present:
#   doppler run --project <p> --config <c> -- bin/cae-discover.sh <brand_id> [date_from] [date_to]
# CLICKHOUSE_HTTP overrides the endpoint (default: the local tunnel).
set -eu

B=${1:?usage: cae-discover.sh <brand_id> [date_from] [date_to]}
FROM=${2:-}
TO=${3:-}
CH=${CLICKHOUSE_HTTP:-http://127.0.0.1:8123}

WHERE="brand_id='$B'"
[ -n "$FROM" ] && WHERE="$WHERE AND daily_date >= '$FROM'"
[ -n "$TO" ] && WHERE="$WHERE AND daily_date <= '$TO'"

q() {
  printf '\n== %s\n' "$1"
  curl -sf "$CH/" -u "${CLICKHOUSE_USER:-}:${CLICKHOUSE_PASSWORD:-}" --data-binary "$2" \
    || printf 'QUERY FAILED - check the tunnel, the credentials, and the column names\n'
}

q "shape" "
SELECT count() AS ad_days, uniq(ad_id) AS ads, uniq(account_id) AS accounts,
       uniq(campaign_id) AS campaigns, min(daily_date) AS first_day, max(daily_date) AS last_day,
       round(sum(spend)) AS spend
FROM default.ad_metadata_v3 WHERE $WHERE FORMAT Vertical"

q "media mix (unique creatives per type)" "
SELECT media_type, uniq(hash) AS creatives, uniq(ad_id) AS ads, round(sum(spend)) AS spend
FROM default.ad_metadata_v3 WHERE $WHERE AND hash != ''
GROUP BY media_type ORDER BY spend DESC FORMAT PrettyCompactMonoBlock"

q "spend concentration (how few creatives cover the account)" "
SELECT count() AS creatives, round(sum(s)) AS spend,
       round(100 * sum(s) / (SELECT sum(spend) FROM default.ad_metadata_v3 WHERE $WHERE), 1) AS pct_of_spend
FROM (SELECT hash, sum(spend) AS s FROM default.ad_metadata_v3 WHERE $WHERE AND hash != '' GROUP BY hash)
FORMAT Vertical"

q "top campaigns" "
SELECT campaign_name, uniq(hash) AS creatives, round(sum(spend)) AS spend
FROM default.ad_metadata_v3 WHERE $WHERE
GROUP BY campaign_name ORDER BY spend DESC LIMIT 15 FORMAT PrettyCompactMonoBlock"

q "existing entity coverage (how much is already analysed, and on which schema)" "
SELECT count() AS rows_in_entities FROM default.extracted_entities_v2 FINAL WHERE brand_id='$B' FORMAT Vertical"
