#!/usr/bin/env bash
# end_of_session.sh
# =============================================================================
# Run at the end of every work session to commit all changes and push to the
# current branch.
#
# Usage:
#   ./end_of_session.sh "Your commit message"
#   ./end_of_session.sh            # uses a default timestamped message
#
# What it does:
#   1. Checks you are on a valid claude/* branch (avoids accidental main pushes)
#   2. Stages all tracked and untracked changes
#   3. Commits (skips if nothing to commit)
#   4. Pushes with retry + exponential backoff (2 → 4 → 8 → 16 s)
#   5. Reminds you to update SESSION_STATE.md if you forgot
# =============================================================================

set -euo pipefail

# ── helpers ──────────────────────────────────────────────────────────────────
red()    { printf '\033[0;31m%s\033[0m\n' "$*"; }
green()  { printf '\033[0;32m%s\033[0m\n' "$*"; }
yellow() { printf '\033[0;33m%s\033[0m\n' "$*"; }
bold()   { printf '\033[1m%s\033[0m\n' "$*"; }

die() { red "ERROR: $*"; exit 1; }

# ── 0. must be run from repo root ────────────────────────────────────────────
if [ ! -d ".git" ]; then
  die "Run this script from the repository root (where .git lives)."
fi

# ── 1. branch safety check ───────────────────────────────────────────────────
BRANCH=$(git rev-parse --abbrev-ref HEAD)

if [[ "$BRANCH" == "main" || "$BRANCH" == "master" ]]; then
  die "You are on '$BRANCH'. Never push session work directly to main/master."
fi

if [[ "$BRANCH" != claude/* ]]; then
  yellow "Warning: branch '$BRANCH' does not start with 'claude/'."
  yellow "Push may fail with HTTP 403 if the remote enforces the naming rule."
  printf 'Continue anyway? [y/N] '
  read -r answer
  [[ "$answer" == "y" || "$answer" == "Y" ]] || die "Aborted."
fi

bold "Branch: $BRANCH"

# ── 2. remind about SESSION_STATE.md ─────────────────────────────────────────
if git diff --quiet SESSION_STATE.md 2>/dev/null && \
   git diff --cached --quiet SESSION_STATE.md 2>/dev/null; then
  yellow "Note: SESSION_STATE.md has no staged/unstaged changes."
  yellow "      Did you update 'Current State' before ending the session?"
fi

# ── 3. stage everything ───────────────────────────────────────────────────────
git add -A

# ── 4. build commit message ───────────────────────────────────────────────────
if [ $# -ge 1 ] && [ -n "$1" ]; then
  MSG="$1"
else
  TIMESTAMP=$(date '+%Y-%m-%d %H:%M')
  MSG="Session sync — $TIMESTAMP"
fi

# ── 5. commit (skip if nothing changed) ──────────────────────────────────────
if git diff --cached --quiet; then
  yellow "Nothing to commit — working tree is clean."
else
  git commit -m "$MSG"
  green "Committed: $MSG"
fi

# ── 6. push with exponential-backoff retry ────────────────────────────────────
MAX_ATTEMPTS=5
DELAY=2
ATTEMPT=1

while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
  bold "Push attempt $ATTEMPT / $MAX_ATTEMPTS …"
  if git push -u origin "$BRANCH"; then
    green "Pushed to origin/$BRANCH"
    break
  fi

  if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    die "Push failed after $MAX_ATTEMPTS attempts. Check your network / permissions."
  fi

  yellow "Push failed. Retrying in ${DELAY}s …"
  sleep "$DELAY"
  DELAY=$(( DELAY * 2 ))
  ATTEMPT=$(( ATTEMPT + 1 ))
done

# ── 7. summary ────────────────────────────────────────────────────────────────
echo ""
bold "=== Session sync complete ==="
git log --oneline -5
echo ""
green "All done. See you next session!"
