<!-- Generated from `origin/master..HEAD` on branch `NLS-64-set-admin_ui-guard-proxy-to-services`. Auto-updated by pre-push hook. -->

Fixed

Auth and proxy review fixes — open redirect sanitization; refresh only on JWT expiry; `/auth/me` auto-refresh; cookie delete with matching attrs; guard 502 uses ErrorSchema

src/common/tests/test_bus/test_kafka.py — replace AsyncMock/MagicMock with plain stub classes; mypy var-annotated fix

Changed

admin_ui OIDC auth handlers — token, refresh, logout, `/auth/me`; open-redirect guard; cookie env vars
adapters/http/auth.py — routes `/api/v1/auth`, `/token`, `/auth/me`, refresh, logout
adapters/http/dependencies.py — split JWT cookies, session refresh, redirect sanitization

admin_ui auth session (PKCE, cookies, JWT split) — PKCE, split JWT cookies, redirect sanitization, expiry-only refresh

docs/ARCHITECTURE.md — admin_ui auth / cookie flow links and maturity table

auth-admin-ui-browser-flow.md — browser OIDC login and guard proxy flow

auth-architecture.md — admin_ui :8000 browser entry + planned headless gateway

auth-request-flow.md — links to admin_ui cookie flow for browser path

edge-architecture.md — admin_ui vs gateway; split cookies marked implemented

Jira tracking — NLS-ADMIN status and sprint docs

infra/.env.example — NEUROATLAS_* cookie alias env vars

src/admin_ui/ service — hexagonal-style shell
main.py — FastAPI entry via app_factory.create()
settings.py — AdminUiSettings (Keycloak, cookie aliases, service_map)

Added

admin_ui guard proxy `/guard/api/v1/*` — reverse proxy to patients / ml / housekeeper with Bearer JWT forward, X-User-Id, Correlation-Id, implicit refresh
adapters/http/proxy.py — guard path → upstream URL resolution
adapters/http/proxy_handlers.py — catch-all `/guard/{path}` reverse proxy with Bearer forward

admin_ui tests — plain fakes + HTTP tests for auth, guard proxy, and review fixes
tests/fakes.py — plain test doubles (no unittest.mock)
tests/test_auth_session/test_session.py — updated
tests/test_http/test_auth_handlers.py — updated
tests/test_http/test_proxy.py — added
tests/test_http/test_proxy_handlers.py — added

auth-admin-ui-cookie-request-flow.md — cookie session, guard proxy, refresh sequence diagrams
