# Admin UI Browser Login Flow

Clinician login through **`admin_ui`** (port 8000): Keycloak OIDC, session cookies, guard proxy
to `patients`. No AtomID token exchange — the same Keycloak JWT is forwarded to backends.

**Jira:** NLS-ADMIN-02 (NLS-62) · NLS-ADMIN-03..08 (NLS-63..68) · **Scaffold:** NLS-ADMIN-01 (NLS-61)

Keycloak client **`neuroatlas-ui`** (public, PKCE) redirects to `http://localhost:8000/api/v1/token`
after login — configured in `infra/keycloak/import/neuroatlas-realm.json`.

See also [edge architecture](./edge-architecture.md) for module layout and [cookie request flow](./auth-admin-ui-cookie-request-flow.md) for session/guard mechanics.

```mermaid
sequenceDiagram
    participant You as Clinician (browser)
    participant UI as admin_ui :8000
    participant KC as Keycloak (login page)
    participant PAT as patients :8001 (hidden inside)

    Note over You,PAT: Step 1 — Open the app
    You->>UI: Open https://localhost:8000/patients

    Note over You,PAT: Step 2 — Not logged in?
    UI->>You: Show "Sign in" page

    Note over You,PAT: Step 3 — Click Sign in
    You->>UI: Click SSO
    UI->>KC: Redirect to Keycloak
    KC->>You: Show username + password form
    You->>KC: Type password

    Note over You,PAT: Step 4 — Come back with a ticket
    KC->>UI: Redirect with secret code
    UI->>KC: Swap code for tokens
    UI->>You: Set safe cookies + show patients page

    Note over You,PAT: Step 5 — Click around in the app
    You->>UI: List patients (cookies only, no password again)
    UI->>PAT: Forward request + Bearer JWT
    PAT->>PAT: Check token + save user row
    PAT-->>UI: Patient list JSON
    UI-->>You: Table on screen
```

## HTTP routes

| Route | Purpose |
|-------|---------|
| `GET /api/v1/auth` | Start OIDC redirect |
| `GET /api/v1/token` | Exchange code; set cookies |
| `POST /api/v1/token/refresh` | Refresh session |
| `POST /api/v1/logout` | Clear cookies |
| `GET /api/v1/auth/me` | Current user + roles |
| `/guard/api/v1/*` | Proxy to patients / ml / housekeeper |

Detail: [cookie request flow](./auth-admin-ui-cookie-request-flow.md).

## Related diagrams

- [Cookie session request flow](./auth-admin-ui-cookie-request-flow.md)
- [Authenticated request flow (backend)](./auth-request-flow.md)
- [JIT user upsert](./auth-jit-upsert.md)
- [API Gateway client flow](./auth-api-gateway-flow.md) (non-browser clients)
