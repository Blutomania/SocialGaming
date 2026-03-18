#!/bin/bash
# Session-start hook for Choose Your Mystery
# Ensures we're always on the active development branch defined in CLAUDE.md,
# regardless of which branch the task runner created for this session.
set -euo pipefail

# Only run in remote (Claude Code on the web) sessions
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel)}"

# ── 1. Resolve the active branch from CLAUDE.md ──────────────────────────────
# Finds the first `claude/...` branch name after the "## Active Branch" heading
ACTIVE_BRANCH=$(sed -n '/^## Active Branch/,/^## /p' CLAUDE.md \
  | grep -oP '`claude/[^`]+`' | head -1 | tr -d '`')

if [ -z "$ACTIVE_BRANCH" ]; then
  echo "session-start: WARNING — could not parse active branch from CLAUDE.md; staying on current branch" >&2
  exit 0
fi

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

# If the task runner placed us on a different claude/ session branch, stay on it.
# Only override when we're on a non-claude branch (e.g. main, detached HEAD).
if [[ "$CURRENT_BRANCH" == claude/* && "$CURRENT_BRANCH" != "$ACTIVE_BRANCH" ]]; then
  echo "session-start: on task branch '$CURRENT_BRANCH', skipping switch to '$ACTIVE_BRANCH'"
  git pull origin "$CURRENT_BRANCH" || true
elif [ "$CURRENT_BRANCH" != "$ACTIVE_BRANCH" ]; then
  echo "session-start: switching from '$CURRENT_BRANCH' → '$ACTIVE_BRANCH'"
  git fetch origin "$ACTIVE_BRANCH"
  git checkout "$ACTIVE_BRANCH"
  git pull origin "$ACTIVE_BRANCH"
else
  echo "session-start: already on '$ACTIVE_BRANCH', pulling latest"
  git pull origin "$ACTIVE_BRANCH"
fi

# ── 2. Install Python dependencies ───────────────────────────────────────────
echo "session-start: installing pip dependencies"
pip install --quiet \
  "anthropic>=0.18.0" \
  "streamlit>=1.32.0" \
  "requests>=2.31.0" \
  "beautifulsoup4>=4.12.0" \
  "python-dotenv>=1.0.0" \
  "rich>=13.0.0"

echo "session-start: done — on branch $(git rev-parse --abbrev-ref HEAD) @ $(git rev-parse --short HEAD)"
