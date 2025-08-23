#!/usr/bin/env python3
"""
Release helper for Frame2Image.

Usage examples:
  python tools/release.py --version 0.1.2 --push
  python tools/release.py --version 0.1.2 --date 2025-08-23 --push

What it does:
- Update __version__ in app.py
- Ensure CHANGELOG.md has a section for vX.Y.Z with the given date
- Optionally git add/commit/tag/push

Notes:
- If the changelog section for the version doesn't exist, it will be created
  right after the Unreleased section with a placeholder if no content exists yet.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_FILE = REPO_ROOT / "app.py"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"

VERSION_RE = re.compile(r'(^\s*__version__\s*=\s*")[^"]+("\s*$)', re.MULTILINE)
CHANGELOG_HEADER_RE = re.compile(r"^## \[v(?P<ver>[^\]]+)\] - (?P<date>\d{4}-\d{2}-\d{2})\s*$", re.MULTILINE)
UNRELEASED_RE = re.compile(r"^## \[Unreleased\]\s*$", re.MULTILINE)


def run(cmd: list[str]) -> int:
    print("+", " ".join(cmd))
    return subprocess.call(cmd)


def update_app_version(new_version: str) -> None:
    text = APP_FILE.read_text(encoding="utf-8")
    if "__version__" not in text:
        print("ERROR: __version__ not found in app.py", file=sys.stderr)
        sys.exit(1)
    new_text = VERSION_RE.sub(rf'__version__ = "{new_version}"', text)
    if new_text == text:
        print("app.py version already set or pattern not changed; continuing…")
    else:
        APP_FILE.write_text(new_text, encoding="utf-8")
        print(f"Updated app.py to __version__={new_version}")


def ensure_changelog_version(new_version: str, date_str: str) -> None:
    text = CHANGELOG.read_text(encoding="utf-8")

    # If version header exists, replace date
    def repl(m: re.Match[str]) -> str:
        ver = m.group("ver")
        if ver == new_version:
            return f"## [v{new_version}] - {date_str}"
        return m.group(0)

    new_text = CHANGELOG_HEADER_RE.sub(repl, text)
    if new_text != text:
        CHANGELOG.write_text(new_text, encoding="utf-8")
        print(f"Updated CHANGELOG date for v{new_version} -> {date_str}")
        return

    # Insert new section after Unreleased
    m = UNRELEASED_RE.search(text)
    header = f"\n## [v{new_version}] - {date_str}\n\n### Added\n- TBD\n"
    if m:
        insert_pos = m.end()
        new_text = text[:insert_pos] + "\n" + header + text[insert_pos:]
        CHANGELOG.write_text(new_text, encoding="utf-8")
        print(f"Inserted new CHANGELOG section for v{new_version}")
    else:
        # Append at end as fallback
        new_text = text.rstrip() + "\n\n" + header + "\n"
        CHANGELOG.write_text(new_text, encoding="utf-8")
        print(f"Appended new CHANGELOG section for v{new_version}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True, help="New version string, e.g. 0.1.2")
    parser.add_argument("--date", default=None, help="Release date YYYY-MM-DD (default: today)")
    parser.add_argument("--push", action="store_true", help="Also commit, tag, and push")
    args = parser.parse_args()

    new_version = args.version.strip()
    date_str = args.date or dt.date.today().isoformat()

    if not APP_FILE.exists() or not CHANGELOG.exists():
        print("ERROR: Run from repository; app.py or CHANGELOG.md missing.", file=sys.stderr)
        return 1

    update_app_version(new_version)
    ensure_changelog_version(new_version, date_str)

    if args.push:
        rc = run(["git", "add", "-A"])
        if rc: return rc
        rc = run(["git", "commit", "-m", f"v{new_version}: release"])
        # If no changes to commit, continue
        if rc not in (0, 1):
            return rc
        run(["git", "tag", f"v{new_version}"])
        run(["git", "push"])
        run(["git", "push", "--tags"])

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
