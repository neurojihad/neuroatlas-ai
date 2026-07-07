<!-- Generated from `origin/master..HEAD` on branch `NLS-67-add-Docker-compose-admin_ui-on-port-8000`. Auto-updated by pre-push hook. -->

#### Fixed

1) Auth and proxy review fixes — open redirect sanitization; refresh only on JWT expiry; `/auth/me` auto-refresh; cookie delete with matching attrs; guard 502 uses ErrorSchema

2) Makefile / make.ps1 — dc admin_ui fix

3) admin_ui tests — plain fakes + HTTP tests for auth, guard proxy, and review fixes
tests/test_http/test_auth_handlers.py — updated
tests/test_http/test_frontend.py — updated

#### Changed

1) admin_ui OIDC auth handlers — dc admin_ui fix

2) infra/.env.example — dc admin_ui fix

3) infra/application.compose.yml — dc admin_ui fix

4) src/admin_ui/ service — hexagonal-style shell
adapters/http/frontend.py — updated
lifespan.py — httpx client, auth_manager, PKCE store, OIDC client on app.state
main.py — FastAPI entry via app_factory.create()
settings.py — AdminUiSettings (Keycloak, cookie aliases, service_map)
ui/src/layout/components/Menu.jsx — updated
ui/src/pages/dashboard/Dashboard.js — updated
ui/src/pages/patients/queries/patients.js — updated
ui/src/pages/patients/ui/PatientsList.js — updated

#### Added

1) —
