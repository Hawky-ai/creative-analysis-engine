#!/bin/sh
# One-command install for the creative-analysis-engine.
#
#   curl -fsSL https://raw.githubusercontent.com/Hawky-ai/creative-analysis-engine/main/install.sh | sh
#
# Clones the repo, checks the toolchain, seeds .env, and tells you how to start.
# Re-running in an existing clone updates it instead of failing.
# Installs nothing globally and touches nothing outside the clone.
set -eu

REPO=${CAE_REPO:-https://github.com/Hawky-ai/creative-analysis-engine}
DIR=${CAE_DIR:-creative-analysis-engine}

say()  { printf '%s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }

have git || { say "git is required."; exit 1; }

if [ -d "$DIR/.git" ]; then
  say "Updating existing clone in $DIR"
  git -C "$DIR" pull --ff-only
elif [ -d .git ] && [ -f AGENTS.md ] && [ -d .agents/skills ]; then
  say "Already inside a clone; updating in place"
  git pull --ff-only
  DIR=.
else
  say "Cloning into $DIR"
  git clone "$REPO" "$DIR"
fi

cd "$DIR"

missing=""
for t in node python3 ffmpeg curl; do
  have "$t" || missing="$missing $t"
done

if [ -n "$missing" ]; then
  say ""
  say "Missing:$missing"
  say "  node    runs the extractors"
  say "  python3 runs the loaders and quality gates"
  say "  ffmpeg  downscales video before it is sent to the model - without it, large"
  say "          creatives are uploaded raw and big runs get slow and expensive"
  have brew && say "  macOS:  brew install$missing"
fi

if [ ! -f .env ]; then
  cp .env.example .env
  say ""
  say "Wrote .env from .env.example - fill it in, or skip it entirely and use a secret"
  say "manager instead (recommended):  doppler run --project <p> --config <c> -- <cmd>"
fi

say ""
say "Installed. Start the guided flow from inside the clone:"
say ""
say "    cd $DIR && claude"
say ""
say "The agent reads AGENTS.md, runs a session digest, and interviews you for the brand,"
say "the scope, the credentials and the focus brief before it touches anything."
say "Any other coding agent works too - point it at AGENTS.md."
