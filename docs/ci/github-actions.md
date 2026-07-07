# GitHub Actions CI

NeuroAtlas CI runs on [GitHub Actions](https://github.com/neurojihad/neuroatlas-ai/actions)
via `.github/workflows/ci.yml`.

## Jobs

| Job | Makefile targets | Notes |
|-----|------------------|-------|
| `check` | `fmt_check`, `lint` | `--only main,dev` |
| `unit` | `test_in_ci` | `--only main,dev,test,patients,housekeeper,ml,messaging` (excludes heavy `rag`/`llm` groups) |
| `sast` | `sast` | `--only main,dev` |
| `audit` | `pip-audit --local` | `--only main,dev`; informational (`continue-on-error`) |
| `migrations` | `migrate`, `check_migrations` | `--only main,housekeeper` (33 packages, no PyTorch) |
| `build-*` | Docker | Push to `ghcr.io/neurojihad/neuroatlas-ai/{patients,ml,housekeeper}` on `master` when paths change, or on semver tags |

## Local parity

Run the same gates locally before pushing:

```bash
make check    # fmt + lint + test
make sast
make pip_audit
```

With infra up (`make up_infra`):

```bash
make migrate check_migrations
```

## Container images

Images are published to GitHub Container Registry (GHCR) under the repository name.
Ensure **Settings → Actions → General → Workflow permissions** allows `GITHUB_TOKEN` to
write packages for build jobs to push successfully.
