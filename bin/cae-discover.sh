#!/bin/sh
# Read an account's shape out of the warehouse before any prompt is written.
#
# Assumes the Hawky warehouse layout: default.ad_metadata_v3 is one row per
# (media_type, daily_date, hash, ad_id) with the day's metrics in the `insights` JSON column
# (there is no spend column), and default.extracted_entities_v2 holds entities keyed by hash.
# `insights` is a native JSON column, so every read of it goes through toString() first;
# `spend` inside it is usually a number but has been seen as a String, hence the JSONType guard.
# ad_metadata_v3 is a ReplacingMergeTree, so every read here goes through FINAL.
#
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

SPEND="if(JSONType(toString(insights),'spend')='String', toFloat64OrZero(JSONExtractString(toString(insights),'spend')), JSONExtractFloat(toString(insights),'spend'))"

q() {
  printf '\n== %s\n' "$1"
  curl -sf "$CH/" -u "${CLICKHOUSE_USER:-}:${CLICKHOUSE_PASSWORD:-}" --data-binary "$2" \
    || printf 'QUERY FAILED - check the tunnel, the credentials, and the column names\n'
}

q "shape" "
SELECT count() AS ad_days, uniq(ad_id) AS ads, uniq(account_id) AS accounts,
       uniq(campaign_id) AS campaigns, uniqIf(hash, hash != '') AS creatives,
       min(daily_date) AS first_day, max(daily_date) AS last_day,
       round(sum($SPEND)) AS spend
FROM default.ad_metadata_v3 FINAL WHERE $WHERE FORMAT Vertical"

q "media mix" "
SELECT media_type, uniqIf(hash, hash != '') AS creatives, uniq(ad_id) AS ads,
       round(sum($SPEND)) AS spend
FROM default.ad_metadata_v3 FINAL WHERE $WHERE
GROUP BY media_type ORDER BY spend DESC FORMAT PrettyCompactMonoBlock"

q "spend concentration - how few creatives carry the account" "
WITH per_hash AS (
  SELECT hash, sum($SPEND) AS s
  FROM default.ad_metadata_v3 FINAL WHERE $WHERE AND hash != '' GROUP BY hash
)
SELECT count() AS creatives, round(sum(s)) AS spend,
       round(sum(s) / count(), 0) AS avg_spend_per_creative,
       arrayStringConcat(arrayMap(x -> toString(round(x)), quantiles(0.5, 0.9, 0.99)(s)), ' / ') AS p50_p90_p99
FROM per_hash FORMAT Vertical"

q "top campaigns" "
SELECT campaign_name, uniqIf(hash, hash != '') AS creatives, round(sum($SPEND)) AS spend
FROM default.ad_metadata_v3 FINAL WHERE $WHERE
GROUP BY campaign_name ORDER BY spend DESC LIMIT 15 FORMAT PrettyCompactMonoBlock"

q "creatives with no hash - these need keying by ad_id instead" "
SELECT countIf(hash = '') AS rows_without_hash, uniqIf(ad_id, hash = '') AS ads_without_hash
FROM default.ad_metadata_v3 FINAL WHERE $WHERE FORMAT Vertical"

q "existing entity coverage - what is already analysed, in scope and out" "
WITH in_scope AS (
  SELECT DISTINCT hash FROM default.ad_metadata_v3 FINAL WHERE $WHERE AND hash != ''
),
analysed AS (
  SELECT DISTINCT hash FROM default.extracted_entities_v2 FINAL WHERE brand_id='$B'
)
SELECT (SELECT count() FROM analysed) AS analysed_total,
       (SELECT count() FROM in_scope) AS in_scope_total,
       (SELECT count() FROM in_scope WHERE hash IN analysed) AS in_scope_analysed,
       (SELECT count() FROM in_scope WHERE hash NOT IN analysed) AS in_scope_to_analyse
FORMAT Vertical"
