#!/bin/sh
# One-command install for the creative-analysis-engine.
#
#   gh repo clone Hawky-ai/creative-analysis-engine && cd creative-analysis-engine && ./install.sh
#
# Clones the repo, checks the toolchain, seeds .env, and tells you how to start.
# The repo is PRIVATE, so it cannot be piped from raw.githubusercontent.com - that returns a
# 404 for anyone without a token, which reads as "file missing" rather than "not authorized".
# Re-running in an existing clone updates it instead of failing.
# Installs nothing globally and touches nothing outside the clone.
set -eu

SLUG=${CAE_SLUG:-Hawky-ai/creative-analysis-engine}
REPO=${CAE_REPO:-https://github.com/$SLUG}
DIR=${CAE_DIR:-creative-analysis-engine}

say()  { printf '%s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }

have git || { say "git is required."; exit 1; }

# The repo is private, so a plain `git clone` over HTTPS prompts for a password that no longer
# exists. `gh repo clone` reuses the GitHub CLI's stored credentials, which is what everyone
# already has; fall back to git for a local path or an already-authenticated environment.
clone() {
  if have gh && [ "${REPO#http}" != "$REPO" ]; then
    gh repo clone "$SLUG" "$1"
  else
    git clone "$REPO" "$1"
  fi
}

if [ -d "$DIR/.git" ]; then
  say "Updating existing clone in $DIR"
  git -C "$DIR" pull --ff-only
elif [ -d .git ] && [ -f AGENTS.md ] && [ -d .agents/skills ]; then
  say "Already inside a clone; updating in place"
  git pull --ff-only
  DIR=.
else
  say "Cloning into $DIR"
  clone "$DIR"
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

if ! have gh; then
  say ""
  say "The GitHub CLI (gh) is not installed. It is not needed to run the engine, but this repo"
  say "is private, so updates need it:  brew install gh && gh auth login"
fi

say ""
say "Installed. Start the guided flow:"
say ""
if [ "$DIR" = "." ]; then say "    claude"; else say "    cd $DIR && claude"; fi
say ""
say "The agent reads AGENTS.md, runs a session digest, and interviews you for the brand,"
say "the scope, the credentials and the focus brief before it touches anything."
say "Any other coding agent works too - point it at AGENTS.md."
