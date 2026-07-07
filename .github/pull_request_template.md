<!-- Generated from `origin/master..HEAD` on branch `NLS-66-add-admin_ui-static-SPA-serving`. Auto-updated by pre-push hook. -->

#### Fixed

1) GitHub PR template — frontend fix

2) src/common/application/app_factory.py — frontend fix

#### Changed

1) src/admin_ui/ service — hexagonal-style shell
Dockerfile — uvicorn on port 8000, non-root user
adapters/http/frontend.py — added
lifespan.py — httpx client, auth_manager, PKCE store, OIDC client on app.state
main.py — FastAPI entry via app_factory.create()
settings.py — AdminUiSettings (Keycloak, cookie aliases, service_map)

#### Added

1) admin_ui tests — frontend fix
