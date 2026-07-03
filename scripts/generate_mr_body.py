#!/usr/bin/env python3
"""Build a GitLab MR description (Fixed / Changed / Added) from branch commits."""

from __future__ import annotations

import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

OUTPUT_PATH = Path("MR_BODY.md")
BASE_CANDIDATES = ("origin/master", "origin/main", "master", "main")

SECTION_ORDER = ("Fixed", "Changed", "Added")


def _run(*args: str) -> str:
    return subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL).strip()


def _branch_exists(ref: str) -> bool:
    try:
        _run("git", "rev-parse", "--verify", ref)
        return True
    except subprocess.CalledProcessError:
        return False


def detect_base_ref() -> str:
    """Pick the merge base branch for the current HEAD."""
    for ref in BASE_CANDIDATES:
        if not _branch_exists(ref):
            continue
        try:
            _run("git", "merge-base", "--is-ancestor", ref, "HEAD")
            return ref
        except subprocess.CalledProcessError:
            continue

    try:
        upstream = _run("git", "rev-parse", "--abbrev-ref", "HEAD@{upstream}")
        if upstream and upstream != "HEAD":
            return upstream
    except subprocess.CalledProcessError:
        pass

    return "master"


def list_commits(base_ref: str) -> list[tuple[str, str]]:
    """Return (short_sha, subject) for commits on this branch but not on base."""
    if not _branch_exists(base_ref):
        return []

    try:
        log = _run("git", "log", f"{base_ref}..HEAD", "--format=%h|%s")
    except subprocess.CalledProcessError:
        return []

    if not log:
        return []

    commits: list[tuple[str, str]] = []
    for line in log.splitlines():
        sha, _, subject = line.partition("|")
        commits.append((sha, subject))
    return commits


def _strip_ticket_prefix(subject: str) -> str:
    return re.sub(r"^[A-Z]+-\d+:\s*", "", subject, flags=re.IGNORECASE).strip()


def categorize(subject: str) -> str:
    """Map a commit subject to Fixed, Changed, or Added."""
    cleaned = _strip_ticket_prefix(subject)
    lower = cleaned.lower()

    fixed_patterns = (
        r"^fix\b",
        r"^fixed\b",
        r"^bug\b",
        r"^hotfix\b",
        r"^patch\b",
        r"\bfix\b",
        r"\bbugfix\b",
        r"\bresolve\b",
    )
    added_patterns = (
        r"^add\b",
        r"^added\b",
        r"^feat\b",
        r"^feature\b",
        r"^new\b",
        r"^implement\b",
        r"^realise\b",
        r"^realize\b",
        r"^scaffold\b",
        r"^create\b",
        r"\badded\b",
    )

    for pattern in fixed_patterns:
        if re.search(pattern, lower):
            return "Fixed"

    for pattern in added_patterns:
        if re.search(pattern, lower):
            return "Added"

    return "Changed"


def format_entry(index: int, subject: str, sha: str) -> str:
    label = _strip_ticket_prefix(subject) or subject
    return f"{index}) {label} ({sha})"


def render_body(commits: list[tuple[str, str]], base_ref: str, branch: str) -> str:
    grouped: dict[str, list[str]] = defaultdict(list)

    for sha, subject in commits:
        section = categorize(subject)
        grouped[section].append((sha, subject))

    lines = [
        f"<!-- Generated from `{base_ref}..HEAD` on branch `{branch}`. Paste into GitLab MR description. -->",
        "",
    ]

    for section in SECTION_ORDER:
        lines.append(f"#### {section}")
        lines.append("")
        entries = grouped.get(section, [])
        if not entries:
            lines.append(f"1) —")
        else:
            for index, (sha, subject) in enumerate(entries, start=1):
                lines.append(format_entry(index, subject, sha))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    base_ref = detect_base_ref()
    branch = _run("git", "rev-parse", "--abbrev-ref", "HEAD")
    commits = list_commits(base_ref)

    if not commits:
        body = (
            f"<!-- No commits between `{base_ref}` and `{branch}`. -->\n\n"
            "#### Fixed\n\n1) —\n\n#### Changed\n\n1) —\n\n#### Added\n\n1) —\n"
        )
    else:
        body = render_body(commits, base_ref, branch)

    OUTPUT_PATH.write_text(body, encoding="utf-8")
    print(f"Updated {OUTPUT_PATH} ({len(commits)} commit(s) vs {base_ref}).")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"generate_mr_body: git command failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
