#!/bin/sh
# Install or update the creative-analysis-engine.
#
#   gh repo clone Hawky-ai/creative-analysis-engine && cd creative-analysis-engine && ./install.sh
#
# Clones or updates the repo, checks you have the tools, and offers to fill in .env.
# The repo is PRIVATE, so you cannot pipe this from raw.githubusercontent.com - that gives a
# 404 to anyone without a token, which looks like the file is missing when it is not.
#
#   ./install.sh          install, update, and offer to set credentials if they are not set
#   ./install.sh --creds  only set the credentials
#
# Installs nothing globally and touches nothing outside the clone.
set -eu

SLUG=${CAE_SLUG:-Hawky-ai/creative-analysis-engine}
REPO=${CAE_REPO:-https://github.com/$SLUG}
DIR=${CAE_DIR:-creative-analysis-engine}
CREDS_ONLY=0
[ "${1:-}" = "--creds" ] && CREDS_ONLY=1

say()  { printf '%s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }

# Ask for one value and append it to .env. Keys and passwords are read with the terminal echo
# turned off, so nothing secret ends up on screen or in your shell history. The value is only
# ever written to .env, which is gitignored.
ask() {
  _var=$1; _label=$2; _secret=$3; _default=${4:-}
  if [ "$_secret" = secret ]; then
    printf '%s: ' "$_label"
    stty -echo 2>/dev/null || true
    read -r _val || _val=""
    stty echo 2>/dev/null || true
    printf '\n'
  elif [ -n "$_default" ]; then
    printf '%s [%s]: ' "$_label" "$_default"
    read -r _val || _val=""
    [ -z "$_val" ] && _val=$_default
  else
    printf '%s: ' "$_label"
    read -r _val || _val=""
  fi
  [ -z "$_val" ] && return 0
  # drop any existing line for this var, then append the new one
  if [ -f .env ]; then
    grep -v "^$_var=" .env > .env.tmp 2>/dev/null || true
    mv .env.tmp .env
  fi
  printf '%s=%s\n' "$_var" "$_val" >> .env
  _val=""
}

set_creds() {
  [ -f .env ] || cp .env.example .env
  chmod 600 .env
  say ""
  say "Paste your credentials. Press Enter to skip any of them - skipped values stay blank and"
  say "you can use a secret manager instead (doppler run --project <p> --config <c> -- <cmd>)."
  say "Keys and passwords are not shown as you type. Everything goes into .env, which is"
  say "gitignored, so it never gets committed."
  say ""
  ask LLM_BASE_URL            "LLM proxy base URL"       plain "https://your-llm-proxy.example/v1"
  ask LLM_API_KEY             "LLM API key"              secret
  ask BIFROST_GENAI_BASE_URL  "Bifrost GenAI base URL"   plain "https://your-bifrost.example/genai/v1beta"
  ask BIFROST_API_KEY         "Bifrost API key"          secret
  ask CLICKHOUSE_USER         "ClickHouse user"          plain
  ask CLICKHOUSE_PASSWORD     "ClickHouse password"      secret
  chmod 600 .env
  say ""
  say "Saved to .env (readable only by you)."
}

# --- find or make the clone -------------------------------------------------

if [ "$CREDS_ONLY" = 1 ]; then
  [ -f AGENTS.md ] || { say "Run this from inside the clone."; exit 1; }
  set_creds
  exit 0
fi

have git || { say "git is required."; exit 1; }

# The repo is private, so a plain `git clone` over HTTPS asks for a password that no longer
# exists. `gh repo clone` uses the login the GitHub CLI already has.
clone() {
  if have gh && [ "${REPO#http}" != "$REPO" ]; then
    gh repo clone "$SLUG" "$1"
  else
    git clone "$REPO" "$1"
  fi
}

if [ -d .git ] && [ -f AGENTS.md ] && [ -d .agents/skills ]; then
  say "Already inside a clone; updating in place"
  DIR=.
elif [ -d "$DIR/.git" ]; then
  say "Updating existing clone in $DIR"
else
  say "Cloning into $DIR"
  clone "$DIR"
fi

cd "$DIR"

# A clone whose `origin` has been removed fails to update with "'origin' does not appear to be
# a git repository", which reads like a broken install and is not. Put it back.
if [ -z "$(git remote 2>/dev/null)" ]; then
  say "No git remote set; adding origin -> $REPO"
  git remote add origin "$REPO"
fi

git pull --ff-only 2>/dev/null || git pull --ff-only origin main || \
  say "Could not update automatically - pull by hand, or check 'gh auth status'."

# --- tools ------------------------------------------------------------------

missing=""
for t in node python3 ffmpeg curl; do
  have "$t" || missing="$missing $t"
done

if [ -n "$missing" ]; then
  say ""
  say "Missing:$missing"
  say "  node    runs the extractors"
  say "  python3 runs the loaders and the checks"
  say "  ffmpeg  shrinks video before it is sent to the model - without it, big creatives go"
  say "          up at full size and runs get slow and expensive"
  have brew && say "  macOS:  brew install$missing"
fi

if ! have gh; then
  say ""
  say "The GitHub CLI (gh) is not installed. You do not need it to run the engine, but this"
  say "repo is private, so updates do:  brew install gh && gh auth login"
fi

# --- credentials ------------------------------------------------------------

[ -f .env ] || { cp .env.example .env; chmod 600 .env; }

if grep -q '^LLM_API_KEY=$' .env 2>/dev/null; then
  if [ -t 0 ]; then
    printf '\nSet your credentials now? [y/N]: '
    read -r reply || reply=""
    case "$reply" in y|Y|yes|YES) set_creds ;; *) say "Skipped. Run ./install.sh --creds later." ;; esac
  else
    say ""
    say ".env still needs credentials. Run ./install.sh --creds to paste them in, or use a"
    say "secret manager:  doppler run --project <p> --config <c> -- <cmd>"
  fi
fi

say ""
say "Installed. Start it with:"
say ""
if [ "$DIR" = "." ]; then say "    claude"; else say "    cd $DIR && claude"; fi
say ""
say "It reads AGENTS.md, prints what it can see, and asks you which brand to analyse."
say "Any other coding agent works too - point it at AGENTS.md."
