# Self-hosted GitLab Runner — implementation plan

**Goal:** Run NeuroAtlas CI on a project-owned runner so pipelines no longer consume GitLab.com shared runner minutes (namespace quota exhausted).

**Scope:** Register one runner, tag it `neuroatlas-self-hosted`, route all jobs via `.gitlab-ci.yml` `default.tags`, document setup for Windows dev machine and Linux VPS.

---

## 1. Decision matrix

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **Linux VPS + Docker executor** | 24/7 availability; native Docker socket; cheap (~$5–10/mo); matches CI images | Requires VPS provisioning | **Primary (production CI)** |
| **Windows dev machine + Docker Desktop** | No extra cost; good for ad-hoc runs while developing | Must stay on; Docker Desktop overhead; slower cold starts | **Secondary (local dev / fallback)** |
| **Shell executor (Windows/Linux)** | Simple install | No `services:` (Postgres in `migrations` job fails); Kaniko/build paths harder | **Not suitable** |

**Recommendation:** Register a **Linux VPS** runner for always-on CI. Optionally register a **Windows** runner on your dev PC for testing runner changes before pushing to VPS.

---

## 2. Executor and CI compatibility

NeuroAtlas `.gitlab-ci.yml` requires **Docker executor**:

| Job | Requirement |
|-----|-------------|
| `check`, `unit`, `sast`, `audit` | Job `image: python:3.12-slim-bookworm` |
| `migrations` | Job image + **service** `pgvector/pgvector:pg16` |
| `build:*` | Kaniko image; pulls/builds via Docker |

Docker executor pulls job images and runs service containers on the same Docker host. Mount `/var/run/docker.sock` (Linux) or use Docker Desktop (Windows).

---

## 3. Registration (GitLab UI)

1. Open **https://gitlab.com/neurojihad/neuroatlas** (adjust path if different).
2. **Settings → CI/CD → Runners** → expand **Project runners**.
3. **New project runner**:
   - Tags: `neuroatlas-self-hosted`
   - Run untagged jobs: **off**
   - Lock to current projects: **on**
4. Copy the **runner authentication token** (starts with `glrt-` on GitLab 16+). Use it once at registration; never commit it.

Optional (group-level): **Group → Settings → CI/CD → Runners** if multiple repos should share one machine. For NeuroAtlas, **project runner** is sufficient and safer.

---

## 4. Tag strategy and CI changes

**Tag:** `neuroatlas-self-hosted` (single tag; add `windows` / `linux` later if needed).

**`.gitlab-ci.yml`:**

```yaml
default:
  tags:
    - neuroatlas-self-hosted
```

Shared runners on GitLab.com will **not** pick these jobs (they lack the tag). Only your registered runner runs the pipeline.

**GitLab project setting (manual):** Settings → CI/CD → Runners → disable **shared runners** for the project once the self-hosted runner is online (belt-and-suspenders).

---

## 5. Repo deliverables

| Path | Purpose |
|------|---------|
| `docs/ci/self-hosted-runner.md` | Operator setup guide (VPS + Windows) |
| `docs/ci/self-hosted-runner-plan.md` | This plan |
| `scripts/ci/register-gitlab-runner.sh` | Linux registration helper |
| `scripts/ci/register-gitlab-runner.ps1` | Windows registration helper |
| `infra/ci/runner/docker-compose.yml` | Optional: runner in Docker on Linux VPS |
| `.gitlab-ci.yml` | `default.tags` |

---

## 6. Security checklist

- [ ] **Project runner** (or locked group runner), not a public shared instance
- [ ] **Untagged jobs disabled** on the runner
- [ ] Token only in env var / one-time registration — not in git
- [ ] VPS: SSH key auth, firewall (22 from your IP only), unattended upgrades
- [ ] Docker: runner user in `docker` group; avoid `--privileged` unless required (Kaniko does not need privileged on docker executor)
- [ ] Rotate runner token if leaked (GitLab → runner → reset token)
- [ ] Disable shared runners on the project after verification

---

## 7. Verification

1. Register runner; confirm **green** in GitLab → Settings → CI/CD → Runners.
2. Push a branch or run pipeline on `master`; jobs should show runner name (not `gitlab-org` shared).
3. Confirm stages pass: `check` → `unit` → `migrations` (Postgres service) → optional `build:*` on master.
4. **Pending forever:** no runner with tag, runner offline, or Docker not running.
5. **Docker errors:** socket permissions (`/var/run/docker.sock`), Docker Desktop not started (Windows).

---

## 8. Phased tasks (implementer)

### Phase A — Repo wiring (no machine required)

1. Add `default.tags` to `.gitlab-ci.yml`
2. Add `docs/ci/self-hosted-runner.md` + registration scripts
3. Add `infra/ci/runner/docker-compose.yml`
4. Update `docs/jira/plan.md` → **NLS-705**

### Phase B — Linux VPS (recommended)

1. Provision Ubuntu 22.04+ VPS (2 vCPU, 4 GB RAM minimum for Kaniko builds)
2. Install Docker: `curl -fsSL https://get.docker.com | sh`
3. Install GitLab Runner (official repo package)
4. Run `scripts/ci/register-gitlab-runner.sh` with `GITLAB_RUNNER_TOKEN`
5. Optional: `docker compose -f infra/ci/runner/docker-compose.yml up -d` after host registration
6. Disable shared runners on project; trigger pipeline

### Phase C — Windows dev (optional)

1. Install [GitLab Runner (Windows)](https://docs.gitlab.com/runner/install/windows.html) and Docker Desktop
2. Run `scripts/ci/register-gitlab-runner.ps1`
3. Use for local pipeline validation only if VPS is primary

### Phase D — Hardening (follow-up)

- Runner concurrency limit in `config.toml` (`concurrent = 2`)
- Cache volume for Docker layers / poetry venv (optional `[[runners.cache]]`)
- Monitoring: runner version, disk space alerts on VPS

---

## 9. Rollback

If self-hosted runner fails, temporarily remove `default.tags` from `.gitlab-ci.yml` and re-enable shared runners (requires available minutes or purchased quota).
