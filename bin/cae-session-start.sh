#!/bin/sh
# Session digest for an agent that just opened this repo.
# Prints: tool/credential readiness, every brand run and the step it is parked on,
# and the one instruction the agent should act on next.
# Wired as the SessionStart hook in .claude/settings.json; safe to run by hand.
set -u

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT" || exit 0

STEPS="discover inventory scout prompt feedback coverage_audit extract timeline verify load_ch register_facets smoke"

have() { command -v "$1" >/dev/null 2>&1; }

echo "CAE SESSION START"
echo

missing=""
for t in node python3 ffmpeg curl; do
  have "$t" || missing="$missing $t"
done
if [ -n "$missing" ]; then
  echo "TOOLS missing:$missing  (extraction needs node; media inlining needs ffmpeg)"
else
  echo "TOOLS ok (node python3 ffmpeg curl)"
fi

if have doppler; then
  echo "SECRETS doppler present - run every credentialed command as: doppler run --project <p> --config <c> -- <cmd>"
else
  echo "SECRETS doppler NOT found - operator must supply env vars another way (.env.example lists them)"
fi

if curl -s -m 3 "${CLICKHOUSE_HTTP:-http://127.0.0.1:8123}/ping" >/dev/null 2>&1; then
  echo "WAREHOUSE clickhouse reachable at ${CLICKHOUSE_HTTP:-http://127.0.0.1:8123}"
else
  echo "WAREHOUSE clickhouse NOT reachable at ${CLICKHOUSE_HTTP:-http://127.0.0.1:8123} - the operator starts the tunnel, you do not"
fi

echo
runs=$(find brands -mindepth 2 -maxdepth 2 -name run.yaml 2>/dev/null | grep -v '^brands/example/' | sort)

if [ -z "$runs" ]; then
  echo "RUNS none"
  echo
  echo "NEXT no brand run exists in this clone. Load the onboard-brand skill and interview the"
  echo "NEXT operator before doing anything else. Do not guess a brand id, a scope, or a vertical."
  exit 0
fi

echo "RUNS"
next_action=""
for f in $runs; do
  name=$(basename "$(dirname "$f")")
  bid=$(sed -n 's/^brand_id:[[:space:]]*//p' "$f" | head -1 | sed 's/#.*$//' | tr -d '" ' )
  pending=""
  for s in $STEPS; do
    v=$(sed -n "s/^[[:space:]]*$s:[[:space:]]*//p" "$f" | head -1 | sed 's/#.*$//' | tr -d ' ')
    case "$v" in
      ""|todo|pending|TODO) pending="$s"; break ;;
    esac
  done
  if [ -z "$pending" ]; then
    echo "  $name ($bid) COMPLETE"
  else
    echo "  $name ($bid) parked before: $pending"
    [ -z "$next_action" ] && next_action="$name:$pending"
  fi
done

echo
if [ -z "$next_action" ]; then
  echo "NEXT every run is complete. Ask the operator what they want before starting anything."
else
  brand=${next_action%%:*}
  step=${next_action##*:}
  echo "NEXT brand '$brand' is parked before step '$step'."
  case "$step" in
    discover|inventory)         echo "NEXT load the onboard-brand skill." ;;
    scout|prompt|feedback|coverage_audit) echo "NEXT load the scout-and-prompt skill. This step needs your judgment - it is not scriptable." ;;
    *)                          echo "NEXT load the extract-and-load skill." ;;
  esac
  echo "NEXT confirm with the operator before spending money or writing to a shared table."
fi
