<!-- Generated from `origin/master..HEAD` on branch `NLS-64-set-admin_ui-guard-proxy-to-services`. Auto-updated by pre-push hook. -->

#### Fixed

1) Auth and proxy review fixes — open redirect sanitization; refresh only on JWT expiry; `/auth/me` auto-refresh; cookie delete with matching attrs; guard 502 uses ErrorSchema

2) .gitignore — gitignore fix; body fix

3) .idea/neuroatlas.iml — gitignore fix

4) poetry.lock — poetry.lock

5) src/common/application/healthcheck.py — check fix

6) src/common/application/settings.py — settings.py

7) src/common/core/exceptions.py — exceptions.py

8) src/common/core/ports/uow.py — check fix

9) src/common/http/error_handlers.py — error_handlers.py

10) src/common/tests/test_bus/test_kafka.py — replace AsyncMock/MagicMock with plain stub classes; mypy var-annotated fix

11) src/housekeeper/migrations/env.py — env.py

12) src/patients/adapters/http/handlers.py — handlers.py

13) src/patients/domain/commands.py — commands.py

14) src/patients/lifespan.py — lifespan.py

#### Changed

1) .gitlab-ci.yml — github migration fix; git runner fix

2) README.md — embedded jira into project

3) admin_ui OIDC auth handlers — token, refresh, logout, `/auth/me`; open-redirect guard; cookie env vars
adapters/http/auth.py — routes `/api/v1/auth`, `/token`, `/auth/me`, refresh, logout
adapters/http/dependencies.py — split JWT cookies, session refresh, redirect sanitization
adapters/http/schemas.py — added

4) admin_ui auth session (PKCE, cookies, JWT split) — add handlers

5) docs/ARCHITECTURE.md — github migration fix; add admin_ui scaffold; fix diagrams; gitignore fix

6) infra/.env.example — add keycloak client; add admin_ui scaffold; embedded jira into project; gitignore fix

7) infra/ci/build.ci.yml — github migration fix

8) infra/ci/deploy.ci.yml — github migration fix

9) infra/ci/prepare.ci.yml — github migration fix

10) infra/ci/test.ci.yml — github migration fix; check fix

11) infra/infra.compose.yml — gitignore fix

12) infra/kafka/init_topics.py — gitignore fix

13) pyproject.toml — Merge branch 'master' into NLS-006-add-models-into-repo; check fix

14) src/admin_ui/ service — hexagonal-style shell
Dockerfile — uvicorn on port 8000, non-root user
adapters/__init__.py — added
adapters/http/__init__.py — added
lifespan.py — httpx client, auth_manager, PKCE store, OIDC client on app.state
main.py — FastAPI entry via app_factory.create()
settings.py — AdminUiSettings (Keycloak, cookie aliases, service_map)

#### Added

1) .cursor/ — add admin_ui scaffold; embedded jira into project; body fix

2) .github/workflows/ci.yml — github migration fix

3) Git hooks / MR body generator — github migration fix; template fix; body fix

4) GitHub PR template — github migration fix; Move merge request template to GitLab layout for repo migration.

5) Makefile / make.ps1 — template fix; add admin_ui scaffold; gitignore fix; body fix

6) admin_ui guard proxy `/guard/api/v1/*` — reverse proxy to patients / ml / housekeeper with Bearer JWT forward, X-User-Id, Correlation-Id, implicit refresh
adapters/http/proxy.py — guard path → upstream URL resolution
adapters/http/proxy_handlers.py — catch-all `/guard/{path}` reverse proxy with Bearer forward

7) admin_ui tests — plain fakes + HTTP tests for auth, guard proxy, and review fixes
tests/fakes.py — plain test doubles (no unittest.mock)
tests/test_auth_session/test_session.py — added
tests/test_http/test_auth_handlers.py — added
tests/test_http/test_health.py — GET /health → 200, service admin_ui
tests/test_http/test_proxy.py — added
tests/test_http/test_proxy_handlers.py — added

8) docs/ci/github-actions.md — github migration fix

9) auth-admin-ui-browser-flow.md — add keycloak client; add admin_ui scaffold

10) auth-admin-ui-cookie-request-flow.md — cookie session, guard proxy, refresh sequence diagrams

11) auth-api-gateway-flow.md — add admin_ui scaffold

12) auth-architecture.md — add admin_ui scaffold; fix diagrams; gitignore fix

13) auth-browser-gateway-flow.md — add keycloak client; fix diagrams

14) auth-jit-upsert.md — fix diagrams

15) auth-keycloak-user-registration.md — add keycloak client; fix diagrams; gitignore fix

16) auth-paymentgate-comparison.md — fix diagrams

17) auth-request-flow.md — fix diagrams

18) auth-users-schema.md — fix diagrams

19) edge-architecture.md — add admin_ui scaffold

20) Jira tracking — git runner fix; add keycloak client; add admin_ui scaffold; add admin_ui plan; …

21) infra/keycloak/import/neuroatlas-realm.json — add keycloak client; gitignore fix

22) scripts/jira/bootstrap_backlog.ps1 — embedded jira into project

23) scripts/jira/bootstrap_pioneer.ps1 — embedded jira into project

24) scripts/jira/create_admin_ui_tasks.ps1 — add admin_ui plan

25) scripts/jira/create_gateway_auth_tasks.ps1 — embedded jira into project

26) scripts/jira/create_runner_task.ps1 — git runner fix

27) scripts/jira/jira_api.ps1 — embedded jira into project

28) scripts/jira/jira_api.sh — embedded jira into project

29) scripts/jira/rename_project_key.ps1 — embedded jira into project

30) src/common/adapters/auth/base.py — base.py

31) src/common/adapters/auth/keycloak.py — keycloak.py

32) src/common/adapters/database/models/user.py — gitignore fix

33) src/common/adapters/database/user_repository.py — user_repository.py

34) src/common/adapters/http/auth_dependencies.py — stash pop fix; body fix

35) src/common/core/entities/user.py — user.py

36) src/common/core/ports/auth.py — auth.py

37) src/common/core/ports/user_repository.py — user_repository.py

38) src/common/tests/paths.py — add keycloak client

39) src/common/tests/test_adapters/test_auth.py — test_auth.py

40) src/common/tests/test_infra/test_keycloak_realm.py — add keycloak client

41) src/common/tests/test_utils/test_identifiers.py — test_identifiers.py

42) src/common/utils/identifiers.py — identifiers.py

43) src/housekeeper/migrations/versions/0002_users.py — 0002_users.py

44) src/patients/tests/test_http/test_handlers.py — test_handlers.py
