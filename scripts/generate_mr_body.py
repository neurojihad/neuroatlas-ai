#!/usr/bin/env python3
"""Build a GitHub PR description (Fixed / Changed / Added) from branch commits and diffs."""

from __future__ import annotations

import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

OUTPUT_PATH = Path("MR_BODY.md")
TEMPLATE_PATH = Path(".github/pull_request_template.md")
OUTPUT_PATHS = (OUTPUT_PATH, TEMPLATE_PATH)
BASE_CANDIDATES = ("origin/master", "origin/main", "master", "main")

SECTION_ORDER = ("Fixed", "Changed", "Added")


@dataclass(frozen=True)
class FileChange:
    status: str
    path: str


@dataclass
class MrEntry:
    section: str
    title: str
    body: str
    sub_lines: list[str]


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


def parse_changed_files(lines: list[str]) -> list[FileChange]:
    changes: list[FileChange] = []
    for line in lines:
        if not line.strip():
            continue
        status, _, path = line.partition("\t")
        if path:
            changes.append(FileChange(status=status.strip(), path=path.strip().replace("\\", "/")))
    return changes


def list_changed_files(base_ref: str) -> list[FileChange]:
    if not _branch_exists(base_ref):
        return []

    try:
        diff = _run("git", "diff", "--name-status", f"{base_ref}..HEAD")
    except subprocess.CalledProcessError:
        return []

    if not diff:
        return []

    return parse_changed_files(diff.splitlines())


def _strip_ticket_prefix(subject: str) -> str:
    return re.sub(r"^[A-Z]+-\d+(?:-[A-Za-z0-9-]+)?:\s*", "", subject, flags=re.IGNORECASE).strip()


def categorize_subject(subject: str) -> str:
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


def commit_subjects_for_paths(base_ref: str, paths: list[str]) -> list[str]:
    if not paths or not _branch_exists(base_ref):
        return []

    try:
        log = _run("git", "log", f"{base_ref}..HEAD", "--format=%s", "--", *paths)
    except subprocess.CalledProcessError:
        return []

    seen: set[str] = set()
    subjects: list[str] = []
    for line in log.splitlines():
        cleaned = _strip_ticket_prefix(line.strip())
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            subjects.append(cleaned)
    return subjects


def group_key(path: str) -> str:  # noqa: C901
    """Bucket file paths into MR narrative groups."""
    if path.startswith("docs/diagrams/"):
        return path
    if path.startswith("docs/jira/"):
        return "docs/jira/"
    if path in {"Makefile", "make.ps1", "make.cmd"}:
        return "Makefile / make.ps1"
    if path.startswith("src/admin_ui/adapters/http/proxy"):
        return "admin_ui guard proxy"
    if path.startswith("src/admin_ui/adapters/http/auth") or path.startswith("src/admin_ui/adapters/http/dependencies"):
        return "admin_ui OIDC auth handlers"
    if path.startswith("src/admin_ui/adapters/http/schemas"):
        return "admin_ui OIDC auth handlers"
    if path.startswith("src/admin_ui/auth/"):
        return "admin_ui auth session"
    if path.startswith("src/admin_ui/tests/"):
        return "admin_ui tests"
    if path.startswith("src/admin_ui/"):
        return "src/admin_ui/"
    if path.startswith(".githooks/") or path == "scripts/generate_mr_body.py":
        return "Git hooks / MR generator"
    if path in {".github/pull_request_template.md", ".github/merge_request_templates/Default.md"}:
        return "GitHub PR template"
    if path.startswith(".cursor/"):
        return ".cursor/"
    return path


def group_display_title(group: str, files: list[FileChange]) -> str:
    titles: dict[str, str] = {
        "docs/jira/": "Jira tracking",
        "admin_ui guard proxy": "admin_ui guard proxy `/guard/api/v1/*`",
        "admin_ui OIDC auth handlers": "admin_ui OIDC auth handlers",
        "admin_ui auth session": "admin_ui auth session (PKCE, cookies, JWT split)",
        "admin_ui tests": "admin_ui tests",
        "src/admin_ui/": "src/admin_ui/ service",
        "Makefile / make.ps1": "Makefile / make.ps1",
        "Git hooks / MR generator": "Git hooks / MR body generator",
        "GitHub PR template": "GitHub PR template",
    }
    if group in titles:
        return titles[group]
    if group.startswith("docs/diagrams/"):
        return PurePosixPath(group).name
    return group


def _file_blurb(change: FileChange) -> str:
    name = PurePosixPath(change.path).name
    blurbs: dict[str, str] = {
        "main.py": "FastAPI entry via app_factory.create()",
        "settings.py": "AdminUiSettings (Keycloak, cookie aliases, service_map)",
        "lifespan.py": "httpx client, auth_manager, PKCE store, OIDC client on app.state",
        "Dockerfile": "uvicorn on port 8000, non-root user",
        "auth.py": "routes `/api/v1/auth`, `/token`, `/auth/me`, refresh, logout",
        "dependencies.py": "split JWT cookies, session refresh, redirect sanitization",
        "proxy_handlers.py": "catch-all `/guard/{path}` reverse proxy with Bearer forward",
        "proxy.py": "guard path → upstream URL resolution",
        "session.py": "PKCE store, JWT split/join, authorize URL builder",
        "keycloak.py": "Keycloak token exchange and refresh client",
        "fakes.py": "plain test doubles (no unittest.mock)",
        "test_health.py": "GET /health → 200, service admin_ui",
        ".env.example": "admin_ui env vars (Keycloak UI client, routes, cookie names)",
    }
    if name in blurbs:
        return blurbs[name]
    verbs = {"A": "added", "M": "updated", "D": "removed", "R": "renamed"}
    return verbs.get(change.status, "changed")


GENERIC_FIX_SUBJECTS = frozenset(
    {"fix", "auth fix", "tests fix", "general fix", "jira fix", "fixed", "bugfix"}
)


def _filter_subjects(subjects: list[str]) -> list[str]:
    return [s for s in subjects if s.strip().lower() not in GENERIC_FIX_SUBJECTS]


def _section_for_group(group: str, files: list[FileChange], subjects: list[str]) -> str:
    if group in {"admin_ui OIDC auth handlers", "admin_ui auth session", "src/admin_ui/"}:
        return "Changed"

    added = sum(1 for f in files if f.status == "A")
    modified = sum(1 for f in files if f.status in {"M", "R"})
    total = len(files)

    if added > 0 and added >= modified:
        return "Added"

    if all(f.path.startswith(("docs/", "infra/")) for f in files):
        return "Added" if added and added == total else "Changed"

    meaningful = _filter_subjects(subjects)
    if modified == total and meaningful and all(categorize_subject(s) == "Fixed" for s in meaningful):
        return "Fixed"

    if modified == total and subjects and all(categorize_subject(s) == "Fixed" for s in subjects):
        if total <= 2:
            return "Fixed"

    return "Changed"


def _describe_group(group: str, files: list[FileChange], subjects: list[str]) -> tuple[str, list[str]]:  # noqa: C901
    sub_lines: list[str] = []
    meaningful = _filter_subjects(subjects)

    if meaningful:
        summary = "; ".join(meaningful[:4])
        if len(meaningful) > 4:
            summary += "; …"
    else:
        summary = _default_summary(group, files)

    scaffold_groups = {"src/admin_ui/", "admin_ui tests", "admin_ui guard proxy", "admin_ui OIDC auth handlers"}
    if group in scaffold_groups and len(files) >= 2:
        if group == "src/admin_ui/":
            headline = "hexagonal-style shell"
        elif group == "admin_ui guard proxy":
            headline = (
                "reverse proxy to patients / ml / housekeeper with Bearer JWT forward, "
                "X-User-Id, Correlation-Id, implicit refresh"
            )
        elif group == "admin_ui OIDC auth handlers":
            headline = "token, refresh, logout, `/auth/me`; open-redirect guard; cookie env vars"
        elif group == "admin_ui tests":
            headline = "plain fakes + HTTP tests for auth, guard proxy, and review fixes"
        else:
            headline = summary
        for change in sorted(files, key=lambda f: f.path):
            rel = change.path
            if rel.startswith("src/admin_ui/"):
                rel = rel[len("src/admin_ui/") :]
            sub_lines.append(f"{rel} — {_file_blurb(change)}")
        return headline, sub_lines

    if group.startswith("docs/diagrams/"):
        name = PurePosixPath(group).stem.replace("-", " ")
        body = summary or f"{name} diagram updates"
        return body, sub_lines

    if group == "docs/jira/":
        paths = ", ".join(PurePosixPath(f.path).name for f in files)
        body = summary or f"plan and sprint docs ({paths})"
        return body, sub_lines

    if group == "docs/ARCHITECTURE.md":
        body = summary or "diagram index and admin_ui / auth flow references"
        return body, sub_lines

    if group == "Makefile / make.ps1":
        body = summary or "run_admin_ui / test_admin_ui / mr_body / setup_hooks targets"
        return body, sub_lines

    if group == "infra/.env.example":
        body = summary or "Keycloak UI client, backend routes, session cookie name env vars"
        return body, sub_lines

    if group == "src/common/tests/test_bus/test_kafka.py":
        body = summary or "replace AsyncMock with plain stub classes; mypy annotation fix"
        return body, sub_lines

    if len(files) == 1:
        body = summary or _file_blurb(files[0])
        return body, sub_lines

    body = summary or _summarize_files(files)
    return body, sub_lines


def _default_summary(group: str, files: list[FileChange]) -> str:
    defaults: dict[str, str] = {
        "admin_ui guard proxy": "NLS-64 guard proxy `/guard/api/v1/*` → patients / ml / housekeeper",
        "admin_ui OIDC auth handlers": "NLS-63 session cookies, refresh, logout, `/auth/me`",
        "admin_ui auth session": "PKCE, split JWT cookies, redirect sanitization, expiry-only refresh",
        "admin_ui tests": "auth + guard proxy coverage with plain fakes",
        "docs/ARCHITECTURE.md": "admin_ui auth / cookie flow links and maturity table",
        "docs/jira/": "NLS-ADMIN status and sprint docs",
        "infra/.env.example": "NEUROATLAS_* cookie alias env vars",
        "src/common/tests/test_bus/test_kafka.py": (
            "replace AsyncMock/MagicMock with plain stub classes; mypy var-annotated fix"
        ),
    }
    if group in defaults:
        return defaults[group]
    if group.startswith("docs/diagrams/"):
        stem = PurePosixPath(group).stem
        if "cookie" in stem:
            return "cookie session, guard proxy, refresh sequence diagrams"
        if "browser" in stem:
            return "browser OIDC login and guard proxy flow"
        if "edge" in stem:
            return "admin_ui vs gateway; split cookies marked implemented"
        if "architecture" in stem:
            return "admin_ui :8000 browser entry + planned headless gateway"
        if "request" in stem:
            return "links to admin_ui cookie flow for browser path"
    return _summarize_files(files)


def _summarize_files(files: list[FileChange]) -> str:
    names = [PurePosixPath(f.path).name for f in files[:5]]
    suffix = f" (+{len(files) - 5} more)" if len(files) > 5 else ""
    return ", ".join(names) + suffix


def build_entries(base_ref: str, commits: list[tuple[str, str]], files: list[FileChange]) -> list[MrEntry]:
    grouped_files: dict[str, list[FileChange]] = defaultdict(list)
    for change in files:
        grouped_files[group_key(change.path)].append(change)

    entries: list[MrEntry] = []

    review_paths = {
        "src/admin_ui/auth/session.py",
        "src/admin_ui/adapters/http/dependencies.py",
        "src/admin_ui/adapters/http/auth.py",
        "src/admin_ui/adapters/http/proxy_handlers.py",
    }
    if review_paths & {f.path for f in files}:
        entries.append(
            MrEntry(
                section="Fixed",
                title="Auth and proxy review fixes",
                body=(
                    "open redirect sanitization; refresh only on JWT expiry; `/auth/me` auto-refresh; "
                    "cookie delete with matching attrs; guard 502 uses ErrorSchema"
                ),
                sub_lines=[],
            )
        )

    for group, group_files in sorted(grouped_files.items(), key=lambda item: item[0]):
        paths = [f.path for f in group_files]
        subjects = commit_subjects_for_paths(base_ref, paths)
        section = _section_for_group(group, group_files, subjects)
        body, sub_lines = _describe_group(group, group_files, subjects)
        title = group_display_title(group, group_files)
        entries.append(MrEntry(section=section, title=title, body=body, sub_lines=sub_lines))

    return entries


def format_entry(index: int, entry: MrEntry) -> str:
    headline = f"{index}) {entry.title} — {entry.body}"
    if not entry.sub_lines:
        return headline
    return headline + "\n" + "\n".join(entry.sub_lines)


def render_body(
    entries: list[MrEntry],
    base_ref: str,
    branch: str,
) -> str:
    by_section: dict[str, list[MrEntry]] = defaultdict(list)
    for entry in entries:
        by_section[entry.section].append(entry)

    lines = [
        f"<!-- Generated from `{base_ref}..HEAD` on branch `{branch}`. Auto-updated by pre-push hook. -->",
        "",
    ]

    for section in SECTION_ORDER:
        lines.append(f"#### {section}")
        lines.append("")
        section_entries = by_section.get(section, [])
        if not section_entries:
            lines.append("1) —")
        else:
            for index, entry in enumerate(section_entries, start=1):
                lines.append(format_entry(index, entry))
                if index < len(section_entries):
                    lines.append("")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_empty_body(base_ref: str, branch: str) -> str:
    return (
        f"<!-- No commits between `{base_ref}` and `{branch}`. Auto-updated by pre-push hook. -->\n\n"
        "#### Fixed\n\n1) —\n\n#### Changed\n\n1) —\n\n#### Added\n\n1) —\n"
    )


def write_outputs(body: str) -> None:
    for path in OUTPUT_PATHS:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")


def main() -> int:
    base_ref = detect_base_ref()
    branch = _run("git", "rev-parse", "--abbrev-ref", "HEAD")
    commits = list_commits(base_ref)
    files = list_changed_files(base_ref)

    if not commits and not files:
        body = render_empty_body(base_ref, branch)
    else:
        entries = build_entries(base_ref, commits, files)
        body = render_body(entries, base_ref, branch)

    write_outputs(body)
    paths = ", ".join(str(path) for path in OUTPUT_PATHS)
    print(f"Updated {paths} ({len(commits)} commit(s), {len(files)} file(s) vs {base_ref}).")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"generate_mr_body: git command failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
