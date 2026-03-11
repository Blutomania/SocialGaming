#!/usr/bin/env python3
"""
Session Summary Generator — Choose Your Mystery
Automatically appends a session summary to SESSIONS.md and commits it.

Usage:
    python scripts/session_summary.py              # interactive (prompts for notes)
    python scripts/session_summary.py --auto       # fully automated, no prompts
    python scripts/session_summary.py --auto --quiet  # automated, minimal output (used by Stop hook)
"""

import subprocess
import sys
import os
from datetime import datetime

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSIONS_FILE = os.path.join(REPO_ROOT, "SESSIONS.md")

AUTO = "--auto" in sys.argv
QUIET = "--quiet" in sys.argv


def run(cmd, capture=True):
    result = subprocess.run(cmd, shell=True, capture_output=capture, text=True, cwd=REPO_ROOT)
    return result.stdout.strip() if capture else None


def has_meaningful_changes():
    """Only generate a summary if something has actually changed this session."""
    status = run("git status --porcelain")
    log = run("git log --oneline -1 --format=%H")
    # Check if there are uncommitted changes or if the last commit was recent (within this session)
    return bool(status)


def collect_session_data():
    branch = run("git rev-parse --abbrev-ref HEAD")
    commit = run("git rev-parse --short HEAD")
    date = datetime.now().strftime("%B %d, %Y")
    time_str = datetime.now().strftime("%H:%M")

    # Files changed since last session entry (uncommitted)
    changed_files = run("git status --porcelain")
    # Recent commits on this branch not on main
    recent_commits = run("git log --oneline origin/main..HEAD 2>/dev/null || git log --oneline -5")
    # Staged + unstaged diff summary
    diff_stat = run("git diff --stat HEAD")

    return {
        "branch": branch,
        "commit": commit,
        "date": date,
        "time": time_str,
        "changed_files": changed_files,
        "recent_commits": recent_commits,
        "diff_stat": diff_stat,
    }


def build_summary(data, notes=""):
    files_section = ""
    if data["changed_files"]:
        lines = []
        for line in data["changed_files"].splitlines():
            if line.strip():
                status_code = line[:2].strip()
                filepath = line[3:].strip()
                status_map = {"M": "Modified", "A": "Added", "D": "Deleted", "??": "Untracked"}
                label = status_map.get(status_code, status_code)
                lines.append(f"- `{filepath}` — {label}")
        files_section = "\n".join(lines) if lines else "_No uncommitted changes_"
    else:
        files_section = "_No uncommitted changes_"

    commits_section = data["recent_commits"] if data["recent_commits"] else "_No new commits_"
    notes_section = notes if notes else "_No additional notes recorded_"

    return f"""
---

## Session — {data['date']} at {data['time']}
**Branch:** `{data['branch']}`
**Latest commit:** `{data['commit']}`

### Files changed this session
{files_section}

### Commits this session
```
{commits_section}
```

### Session notes
{notes_section}

### Resume from here
See **Consolidated To-Do List** above for next steps.
Check `CLAUDE.md` for project conventions and current priorities.
"""


def append_to_sessions(summary):
    with open(SESSIONS_FILE, "r") as f:
        content = f.read()

    # Insert after the first H1 heading and any intro paragraph
    insert_marker = "\n---\n"
    idx = content.find(insert_marker)
    if idx != -1:
        new_content = content[:idx] + summary + content[idx:]
    else:
        new_content = content + summary

    with open(SESSIONS_FILE, "w") as f:
        f.write(new_content)


def commit_summary(branch, commit):
    run(f'git add "{SESSIONS_FILE}"', capture=False)
    message = f"chore: auto-update SESSIONS.md with session summary [{commit}]"
    result = subprocess.run(
        ["git", "commit", "-m", message],
        capture_output=True, text=True, cwd=REPO_ROOT
    )
    if result.returncode == 0:
        push = subprocess.run(
            ["git", "push"],
            capture_output=True, text=True, cwd=REPO_ROOT
        )
        return push.returncode == 0
    return False


def main():
    if not has_meaningful_changes():
        if not QUIET:
            print("No uncommitted changes detected — skipping session summary.")
        return

    data = collect_session_data()

    notes = ""
    if not AUTO:
        print("\n=== Session Summary Generator ===")
        print(f"Branch: {data['branch']}  |  Commit: {data['commit']}")
        print("\nPaste any session notes (what was built, decisions made, next steps).")
        print("Press Enter twice when done:\n")
        lines = []
        while True:
            line = input()
            if line == "" and lines and lines[-1] == "":
                break
            lines.append(line)
        notes = "\n".join(lines).strip()

    summary = build_summary(data, notes)
    append_to_sessions(summary)

    committed = commit_summary(data["branch"], data["commit"])

    if not QUIET:
        if committed:
            print(f"\nSession summary committed and pushed to {data['branch']}.")
        else:
            print("\nSession summary written to SESSIONS.md (commit/push may need manual run).")


if __name__ == "__main__":
    main()
