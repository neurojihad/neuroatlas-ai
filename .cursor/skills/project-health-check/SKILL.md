---
name: project-health-check
description: Runs NeuroAtlas quality gates (fmt_check, lint, test, sast), fixes safe issues automatically, and reports remaining findings as a severity-grouped checklist. Use when the user asks for a project health check, quality gate status, pre-push validation, or "is the repo healthy".
---

# Project Health Check

Assess repository health by running Makefile quality gates, applying safe fixes, and reporting what remains.

## Quick start

1. Run all gates (see below) and capture output.
2. Apply safe auto-fixes, then re-run failed gates.
3. Produce a severity-grouped checklist.
4. Fix remaining issues the user approves; ask before risky changes.

## Quality gates

Run from the repository root:

```bash
make fmt_check    # isort + ruff format (check only)
make lint         # ruff check + mypy
make test         # pytest src
make sast         # bandit
```

Run gates in parallel when possible. If a gate fails, still run the others to surface the full picture.

`make check` runs `fmt lint test` but **not** `sast` — always include `sast` separately.

## Safe auto-fixes (apply without asking)

| Issue | Command |
|-------|---------|
| Import order / formatting | `make fmt` |
| Ruff lint auto-fixes | `make lint_fix` |

After auto-fixes, re-run the gates that previously failed.

## Ask before fixing

Get user confirmation before:

- Changing logic to fix mypy or test failures
- Suppressing bandit findings or adding `# nosec`
- Modifying production code for any non-mechanical fix
- Changing `pyproject.toml` tool config

## Severity grouping

Classify every finding into exactly one bucket:

| Severity | Criteria | Examples |
|----------|----------|----------|
| **Critical** | Blocks merge; correctness or security risk | Test failures, bandit high-severity, mypy errors in changed code |
| **Important** | Should fix before push | Lint errors without auto-fix, fmt_check failures after `make fmt`, mypy errors elsewhere |
| **Minor** | Low-risk cleanup | Style warnings, coverage gaps outside scope, informational bandit low findings |

## Output format

Use this template:

```markdown
# Project Health Check

## Summary
- Gates run: fmt_check, lint, test, sast
- Status: [PASS | FAIL]
- Auto-fixes applied: [list or "none"]

## Critical
- [ ] ...

## Important
- [ ] ...

## Minor
- [ ] ...

## Gate results

| Gate | Status | Notes |
|------|--------|-------|
| fmt_check | pass/fail | |
| lint | pass/fail | |
| test | pass/fail | |
| sast | pass/fail | |

## Recommended next steps
1. ...
```

Mark items `[x]` when resolved during the session.

## Workflow checklist

```
- [ ] Run fmt_check, lint, test, sast
- [ ] Apply safe auto-fixes (fmt, lint_fix)
- [ ] Re-run failed gates
- [ ] Publish severity-grouped checklist
- [ ] Fix approved items; ask before risky changes
- [ ] Re-run gates until pass or user stops
```

## Notes

- Do not commit unless the user explicitly asks.
- Prefer `make` targets over ad-hoc tool invocations so local and CI stay aligned.
- If Poetry/env is missing, report as **Critical** with setup steps (`make install`, `make init`).
