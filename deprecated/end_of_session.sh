#!/usr/bin/env bash
# end_of_session.sh
# -----------------
# Run this at the END of every working session to ensure your local changes
# are committed and pushed to the active branch.
#
# Usage:
#   chmod +x end_of_session.sh   (first time only)
#   ./end_of_session.sh
#   ./end_of_session.sh "optional custom commit message"
#
# What it does:
#   1. Shows you what's uncommitted (so nothing is a surprise)
#   2. Updates SESSION_STATE.md with the current timestamp
#   3. Stages ALL tracked + untracked files (excluding .gitignore'd paths)
#   4. Commits with a timestamp message (or your custom message)
#   5. Pushes to the current branch with retry logic
#
# Safety:
#   - Never pushes to master/main
#   - Warns before staging large files (>5MB)
#   - Dry-run mode available: DRY_RUN=1 ./end_of_session.sh

set -euo pipefail

# ── Colours ─────────────────────────────────────────────────────────────────
RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'; NC='\033[0m'

# ── Config ───────────────────────────────────────────────────────────────────
LARGE_FILE_THRESHOLD_KB=5000   # warn if a staged file exceeds 5MB
MAX_RETRIES=4
DRY_RUN="${DRY_RUN:-0}"

# ── Safety check: never push to master/main ──────────────────────────────────
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [[ "$CURRENT_BRANCH" == "master" || "$CURRENT_BRANCH" == "main" ]]; then
    echo -e "${RED}ERROR: You are on '$CURRENT_BRANCH'. This script will not push to master/main.${NC}"
    echo "Switch to your feature branch first:  git checkout -b your-branch-name"
    exit 1
fi

echo -e "${GREEN}Branch:${NC} $CURRENT_BRANCH"

# ── Show current status ───────────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}=== Uncommitted changes ===${NC}"
git status --short
echo ""

# ── Bail early if nothing to do ──────────────────────────────────────────────
if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
    echo -e "${GREEN}Nothing to commit — already in sync.${NC}"
    exit 0
fi

# ── Warn about large files ────────────────────────────────────────────────────
echo -e "${YELLOW}=== Checking for large files ===${NC}"
LARGE_FILES=()
while IFS= read -r -d '' filepath; do
    size_kb=$(du -k "$filepath" 2>/dev/null | cut -f1)
    if [ "${size_kb:-0}" -gt "$LARGE_FILE_THRESHOLD_KB" ]; then
        LARGE_FILES+=("$filepath (${size_kb}KB)")
    fi
done < <(git ls-files --others --exclude-standard -z; git diff --name-only -z; git diff --cached --name-only -z)

if [ ${#LARGE_FILES[@]} -gt 0 ]; then
    echo -e "${RED}WARNING: Large files detected:${NC}"
    for f in "${LARGE_FILES[@]}"; do echo "  $f"; done
    echo ""
    echo "Large binary files (corpus parquets, models) should NOT go in git."
    echo "Add them to .gitignore or use git-lfs."
    read -r -p "Continue anyway? (y/N) " confirm
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        echo "Aborted."
        exit 1
    fi
fi

# ── Commit message ────────────────────────────────────────────────────────────
TIMESTAMP=$(date '+%Y-%m-%d %H:%M')
if [ -n "${1:-}" ]; then
    COMMIT_MSG="$1"
else
    COMMIT_MSG="End-of-session sync — $TIMESTAMP"
fi

# ── Stage everything ──────────────────────────────────────────────────────────
if [ "$DRY_RUN" = "1" ]; then
    echo -e "${YELLOW}[DRY RUN] Would stage all changes and commit: \"$COMMIT_MSG\"${NC}"
    echo -e "${YELLOW}[DRY RUN] Would push to origin/$CURRENT_BRANCH${NC}"
    exit 0
fi

git add -A

echo ""
echo -e "${YELLOW}=== Staged files ===${NC}"
git diff --cached --name-status
echo ""

# ── Commit ────────────────────────────────────────────────────────────────────
git commit -m "$COMMIT_MSG"

# ── Push with retry ───────────────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}=== Pushing to origin/$CURRENT_BRANCH ===${NC}"

attempt=1
delay=2
while [ $attempt -le $MAX_RETRIES ]; do
    if git push -u origin "$CURRENT_BRANCH"; then
        echo -e "${GREEN}Push successful.${NC}"
        break
    else
        if [ $attempt -eq $MAX_RETRIES ]; then
            echo -e "${RED}Push failed after $MAX_RETRIES attempts. Check your network and branch permissions.${NC}"
            exit 1
        fi
        echo -e "${YELLOW}Push failed (attempt $attempt/$MAX_RETRIES). Retrying in ${delay}s...${NC}"
        sleep $delay
        delay=$((delay * 2))
        attempt=$((attempt + 1))
    fi
done

echo ""
echo -e "${GREEN}=== Session synced successfully ===${NC}"
echo "Branch : $CURRENT_BRANCH"
echo "Commit : $(git rev-parse --short HEAD) — $COMMIT_MSG"
