# Self-hosted GitLab Runner

NeuroAtlas CI is configured to run on a **project runner** tagged `neuroatlas-self-hosted`. Jobs on that runner do **not** use GitLab.com shared runner minutes — you pay for the host (VPS or your PC) instead.

See also: [implementation plan](self-hosted-runner-plan.md).

---

## Prerequisites

- GitLab **Maintainer** access to the NeuroAtlas project
- **Docker** on the runner host (Docker Engine on Linux, or Docker Desktop on Windows)
- Outbound HTTPS to `gitlab.com` and container registries (`registry.gitlab.com`, `gcr.io`, Docker Hub)

---

## 1. Create a project runner in GitLab

1. Project → **Settings → CI/CD → Runners** → **New project runner**
2. **Tags:** `neuroatlas-self-hosted`
3. **Run untagged jobs:** disabled
4. **Lock to current projects:** enabled
5. Create runner and copy the **authentication token** (`glrt-...`)

Store the token in a password manager or shell env — **never commit it**.

---

## 2. Linux VPS (recommended)

Works 24/7; best for team pipelines and Kaniko image builds.

### Install Docker and GitLab Runner

```bash
# Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker "$USER"
# log out/in so group membership applies

# GitLab Runner (Debian/Ubuntu)
curl -L "https://packages.gitlab.com/install/repositories/runner/gitlab-runner/script.deb.sh" | sudo bash
sudo apt-get install -y gitlab-runner
sudo usermod -aG docker gitlab-runner
```

### Register

```bash
export GITLAB_RUNNER_TOKEN="glrt-xxxxxxxx"   # from GitLab UI
export GITLAB_PROJECT_URL="https://gitlab.com/neurojihad/neuroatlas"
./scripts/ci/register-gitlab-runner.sh
sudo gitlab-runner restart
```

Verify: GitLab → Settings → CI/CD → Runners shows **online** with tag `neuroatlas-self-hosted`.

### Optional: runner via Docker Compose

After registering on the host once, you can manage the runner container with:

```bash
docker compose -f infra/ci/runner/docker-compose.yml up -d
```

The compose file mounts the host Docker socket so job containers (Python, Postgres services, Kaniko) run as siblings on the host.

---

## 3. Windows dev machine (optional)

Use for local validation when the VPS is down or while tuning runner config.

1. Install [GitLab Runner for Windows](https://docs.gitlab.com/runner/install/windows.html)
2. Install and start **Docker Desktop** (Linux containers mode)
3. In PowerShell:

```powershell
$env:GITLAB_RUNNER_TOKEN = "glrt-xxxxxxxx"
$env:GITLAB_PROJECT_URL = "https://gitlab.com/neurojihad/neuroatlas"
.\scripts\ci\register-gitlab-runner.ps1
Restart-Service gitlab-runner
```

Registration uses the **docker** executor; Docker Desktop must be running before jobs start.

---

## 4. Disable shared runners (project)

After the self-hosted runner is online:

1. Settings → CI/CD → Runners
2. Turn **off** shared runners for this project

Pipelines will only run when your tagged runner is available.

---

## 5. Verify CI

Push any branch or open an MR. In the pipeline job log, the runner name should be your machine (not `saas-linux-small-amd64` shared runner).

Expected jobs (from `infra/ci/test.ci.yml`):

- `check` — fmt + lint
- `unit` — pytest + coverage artifacts
- `sast` — bandit
- `audit` — pip-audit (allowed to fail)
- `migrations` — Postgres **service** container + Alembic

On `master`, Kaniko `build:*` jobs also require Docker.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Jobs stuck **pending** | No online runner with tag | Register runner; check `gitlab-runner verify`; confirm tag |
| `Cannot connect to Docker daemon` | Socket permissions / Desktop off | Linux: `gitlab-runner` in `docker` group; Windows: start Docker Desktop |
| `migrations` fails to reach Postgres | Service container not starting | Docker executor required; check `docker ps` during job |
| Kaniko push fails | Registry auth | `CI_REGISTRY_*` vars are set by GitLab; runner needs outbound network |
| Still uses shared minutes | Missing `default.tags` or untagged jobs enabled | Pull latest `.gitlab-ci.yml`; disable shared runners |

---

## Manual registration (reference)

```bash
sudo gitlab-runner register \
  --non-interactive \
  --url "https://gitlab.com/" \
  --token "$GITLAB_RUNNER_TOKEN" \
  --executor "docker" \
  --docker-image "python:3.12-slim-bookworm" \
  --description "neuroatlas-self-hosted"
```

With GitLab 16.11+ runner tokens (`glrt-...`), **tags, lock, and untagged** are configured in the GitLab UI when you create the runner — not on the `register` command line.

Edit `/etc/gitlab-runner/config.toml` if you need `privileged = false` (default), pull policy, or concurrency limits.
