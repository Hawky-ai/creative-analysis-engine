#!/bin/sh
# Install or update the creative-analysis-engine.
#
#   gh repo clone Hawky-ai/creative-analysis-engine && cd creative-analysis-engine && ./install.sh
#
# Clones or updates the repo, checks you have the tools, and offers to fill in .env.
# The repo is PRIVATE, so you cannot pipe this from raw.githubusercontent.com - that gives a
# 404 to anyone without a token, which looks like the file is missing when it is not.
#
# It does not ask for credentials. It leaves you a .env with the variable names in it, and the
# agent walks you through filling it in on the first session.
#
# Installs nothing globally and touches nothing outside the clone.
set -eu

SLUG=${CAE_SLUG:-Hawky-ai/creative-analysis-engine}
REPO=${CAE_REPO:-https://github.com/$SLUG}
DIR=${CAE_DIR:-creative-analysis-engine}
say()  { printf '%s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }

# --- find or make the clone -------------------------------------------------

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

# --- .env ---------------------------------------------------------------------

if [ ! -f .env ]; then
  cp .env.example .env
  chmod 600 .env
fi

say ""
say "Installed. Start it with:"
say ""
if [ "$DIR" = "." ]; then say "    claude"; else say "    cd $DIR && claude"; fi
say ""
say "It will tell you what this is, show you which values .env needs, and ask which brand"
say "to analyse. Any other coding agent works too - point it at AGENTS.md."
