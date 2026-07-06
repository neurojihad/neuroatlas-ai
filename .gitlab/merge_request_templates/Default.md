<!-- Generated from `origin/master..HEAD` on branch `NLS-64-set-admin_ui-guard-proxy-to-services`. Auto-updated by pre-push hook. -->

#### Fixed

1) Auth and proxy review fixes — open redirect sanitization; refresh only on JWT expiry; `/auth/me` auto-refresh; cookie delete with matching attrs; guard 502 uses ErrorSchema

2) .gitlab-ci.yml — git runner fix

3) Git hooks / MR body generator — template fix

4) GitLab MR template — template fix

5) Makefile / make.ps1 — template fix

6) src/common/tests/test_bus/test_kafka.py — replace AsyncMock/MagicMock with plain stub classes; mypy var-annotated fix

#### Changed

1) admin_ui OIDC auth handlers — token, refresh, logout, `/auth/me`; open-redirect guard; cookie env vars
adapters/http/auth.py — routes `/api/v1/auth`, `/token`, `/auth/me`, refresh, logout
adapters/http/dependencies.py — split JWT cookies, session refresh, redirect sanitization

2) admin_ui auth session (PKCE, cookies, JWT split) — PKCE, split JWT cookies, redirect sanitization, expiry-only refresh

3) docs/ARCHITECTURE.md — admin_ui auth / cookie flow links and maturity table

4) auth-admin-ui-browser-flow.md — browser OIDC login and guard proxy flow

5) auth-architecture.md — admin_ui :8000 browser entry + planned headless gateway

6) auth-request-flow.md — links to admin_ui cookie flow for browser path

7) edge-architecture.md — admin_ui vs gateway; split cookies marked implemented

8) Jira tracking — git runner fix

9) infra/.env.example — NEUROATLAS_* cookie alias env vars

10) src/admin_ui/ service — hexagonal-style shell
main.py — FastAPI entry via app_factory.create()
settings.py — AdminUiSettings (Keycloak, cookie aliases, service_map)

#### Added

1) admin_ui guard proxy `/guard/api/v1/*` — reverse proxy to patients / ml / housekeeper with Bearer JWT forward, X-User-Id, Correlation-Id, implicit refresh
adapters/http/proxy.py — guard path → upstream URL resolution
adapters/http/proxy_handlers.py — catch-all `/guard/{path}` reverse proxy with Bearer forward

2) admin_ui tests — plain fakes + HTTP tests for auth, guard proxy, and review fixes
tests/fakes.py — plain test doubles (no unittest.mock)
tests/test_auth_session/test_session.py — updated
tests/test_http/test_auth_handlers.py — updated
tests/test_http/test_proxy.py — added
tests/test_http/test_proxy_handlers.py — added

3) docs/ci/self-hosted-runner-plan.md — git runner fix

4) docs/ci/self-hosted-runner.md — git runner fix

5) auth-admin-ui-cookie-request-flow.md — cookie session, guard proxy, refresh sequence diagrams

6) infra/ci/runner/docker-compose.yml — git runner fix

7) scripts/ci/register-gitlab-runner.ps1 — git runner fix

8) scripts/ci/register-gitlab-runner.sh — git runner fix

9) scripts/jira/create_runner_task.ps1 — git runner fix
