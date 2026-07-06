# Admin UI Cookie Session — Request Flow

How **`admin_ui`** (:8000) uses **HTTP cookies** for browser sessions: split JWT storage,
refresh handling, and guard proxy forwarding. The browser never sends `Authorization: Bearer`
to backend services directly — only `admin_ui` does, after reconstructing the Keycloak access
token from cookies.

**Jira:** NLS-ADMIN-03 (NLS-63) auth handlers · NLS-ADMIN-04 (NLS-64) guard proxy

For the high-level login story, see [Admin UI browser login flow](./auth-admin-ui-browser-flow.md).
For JWT validation inside `patients` / `ml`, see [Authenticated request flow (backend)](./auth-request-flow.md).

---

## Cookie model

After OIDC login, `admin_ui` stores three cookies (names from `AdminUiSettings`):

| Cookie | Default name | httpOnly | Purpose |
|--------|--------------|----------|---------|
| Access payload | `NEUROATLAS_ACCESS_TOKEN` | No | JWT `header.payload` — readable by SPA for role hints |
| Access signature | `NEUROATLAS_TOKEN_SIGN` | Yes | JWT signature — cannot be forged without server read |
| Refresh token | `NEUROATLAS_REFRESH_TOKEN` | Yes | Keycloak refresh token for silent session renewal |

The full access JWT is rebuilt server-side: `header.payload` + `.` + `signature`.

```mermaid
flowchart LR
    subgraph browser [Browser]
        JS[React SPA]
        COOK[document.cookie]
    end

    subgraph cookies [Session cookies]
        P[NEUROATLAS_ACCESS_TOKEN<br/>header.payload]
        S[NEUROATLAS_TOKEN_SIGN<br/>signature httponly]
        R[NEUROATLAS_REFRESH_TOKEN<br/>httponly]
    end

    subgraph bff [admin_ui BFF]
        JOIN[join_jwt]
        FWD[Authorization Bearer]
    end

    JS -.->|reads roles only| P
    COOK --> P
    COOK --> S
    COOK --> R
    P --> JOIN
    S --> JOIN
    JOIN --> FWD
    R -->|refresh when expired| bff
```

**Why split?** PaymentGate-style UX: the SPA can read claims from the payload cookie (e.g.
`realm_access.roles`) without holding a forgeable full JWT. The signature stays httpOnly.

**Flags:** `Path=/`, `SameSite=Lax`, `Secure` when `ENVIRONMENT != local`. Logout clears cookies with the same attributes.

**Post-login redirect:** `?redirect=` on `GET /api/v1/auth` must be a relative path (`/patients`). External URLs are rejected (`sanitize_redirect_path` → `/`).

---

## Route families

| Prefix | Auth mechanism | Example |
|--------|----------------|---------|
| `/api/v1/auth*` | OIDC + cookies | Login, callback, `/auth/me`, refresh, logout |
| `/guard/api/v1/*` | Session cookies → Bearer forward | `GET /guard/api/v1/patients` |
| `/health` | None | Public health check |

---

## 1. Establish session (login callback)

Triggered after Keycloak redirects to `GET /api/v1/token?code=…&state=…`.

```mermaid
sequenceDiagram
    participant B as Browser
    participant UI as admin_ui :8000
    participant KC as Keycloak

    Note over B,KC: Prior: GET /api/v1/auth → user logged in at Keycloak
    KC->>B: Redirect with authorization code
    B->>UI: GET /api/v1/token?code&state
    UI->>UI: Validate PKCE state, pop code_verifier
    UI->>KC: POST /token (code + PKCE verifier)
    KC-->>UI: access_token + refresh_token
    UI->>UI: split_jwt(access) → payload + signature cookies
    UI-->>B: Set-Cookie (3) + 302 redirect to app
```

**Sets:** all three session cookies. **Does not** return tokens in the JSON body.

---

## 2. Read current user (`/auth/me`)

```mermaid
sequenceDiagram
    participant B as Browser
    participant UI as admin_ui :8000
    participant JWKS as Keycloak JWKS

    B->>UI: GET /api/v1/auth/me (cookies only)
    UI->>UI: join_jwt from NEUROATLAS_ACCESS_TOKEN + NEUROATLAS_TOKEN_SIGN
    UI->>JWKS: Verify JWT (iss, aud, exp, roles)
    UI-->>B: 200 { user_id, email, roles }
```

No Bearer header from the browser. Used by React `AuthProvider` to gate routes.

---

## 3. Guard proxy — general API request (main app flow)

Every data call from the SPA uses `/guard/...`. This is the **default request flow** after login.

```mermaid
sequenceDiagram
    participant B as Browser
    participant UI as admin_ui :8000
    participant KC as Keycloak
    participant API as patients / ml :8001+

    B->>UI: GET /guard/api/v1/patients (cookies only)
    UI->>UI: join_jwt from session cookies
    alt access token valid
        UI->>UI: KeycloakAuthAdapter.get_user(token)
    else access expired (exp claim) + refresh cookie present
        UI->>KC: POST /token (grant_type=refresh_token)
        KC-->>UI: new access (+ optional refresh)
        UI->>UI: set_auth_cookies on response
        UI->>UI: validate new access token
    else no valid session
        UI-->>B: 401 Unauthorized
    end
    UI->>API: GET /api/v1/patients<br/>Authorization: Bearer JWT<br/>X-User-Id, Correlation-Id
    API->>API: JWKS verify + optional JIT users upsert
    API-->>UI: 200 JSON
    UI-->>B: 200 JSON (+ Set-Cookie if refreshed)
```

**Path rewrite examples:**

| Guard request | Upstream |
|---------------|----------|
| `/guard/api/v1/patients` | `{PATIENTS_ROUTE}/api/v1/patients` |
| `/guard/api/v1/ml/predict` | `{ML_ROUTE}/api/v1/predict` |
| `/guard/api/v1/housekeeper/db/health` | `{HOUSEKEEPER_ROUTE}/api/v1/db/health` |

Configured via `service_map` in `src/admin_ui/settings.py`.

---

## 4. Explicit refresh (`POST /api/v1/token/refresh`)

The SPA may call this on `401` before retrying (see NLS-ADMIN-05 `HttpAuthBase` pattern).

```mermaid
sequenceDiagram
    participant B as Browser
    participant UI as admin_ui :8000
    participant KC as Keycloak

    B->>UI: POST /api/v1/token/refresh (NEUROATLAS_REFRESH_TOKEN cookie)
    UI->>KC: POST /token (refresh_token)
    KC-->>UI: new access_token (+ refresh_token)
    UI-->>B: 200 + updated session cookies
```

Guard proxy can also refresh **implicitly** (section 3) without this call.

---

## 5. Logout

```mermaid
sequenceDiagram
    participant B as Browser
    participant UI as admin_ui :8000

    B->>UI: POST /api/v1/logout (session cookies)
    UI->>UI: clear_auth_cookies (all three)
    UI-->>B: 200 { logout_url } optional Keycloak end-session URL
```

---

## End-to-end overview

```mermaid
flowchart TB
    subgraph login [Once per session]
        A1[GET /api/v1/auth] --> KC[Keycloak login]
        KC --> A2[GET /api/v1/token]
        A2 --> C[Set 3 cookies]
    end

    subgraph app [Every app interaction]
        C --> G[GET /guard/api/v1/*]
        G --> R{JWT valid?}
        R -->|yes| P[Proxy + Bearer]
        R -->|expired| RF[Refresh via Keycloak]
        RF --> P
        P --> BE[patients / ml / housekeeper]
        BE --> G
    end

    subgraph meta [Session metadata]
        C --> M[GET /api/v1/auth/me]
    end

    subgraph end [End session]
        L[POST /api/v1/logout] --> CLR[Clear cookies]
    end
```

---

## What the browser never does

| Avoided | Reason |
|---------|--------|
| Call `patients:8001` directly | Backends internal; CORS and token exposure |
| Store refresh token in JS | httpOnly cookie only |
| Send full JWT in `Authorization` from SPA | BFF reconstructs and forwards server-side |
| AtomID / token exchange | Same Keycloak JWT end-to-end ([comparison](./auth-paymentgate-comparison.md)) |

---

## Code references

| Concern | Module |
|---------|--------|
| Cookie set/clear/join | `src/admin_ui/adapters/http/dependencies.py` |
| JWT split/join, PKCE | `src/admin_ui/auth/session.py` |
| Auth routes | `src/admin_ui/adapters/http/auth.py` |
| Guard proxy | `src/admin_ui/adapters/http/proxy_handlers.py` |
| Upstream URL map | `src/admin_ui/adapters/http/proxy.py`, `settings.service_map` |

---

## Related diagrams

- [Admin UI browser login flow](./auth-admin-ui-browser-flow.md) — clinician journey
- [Edge architecture](./edge-architecture.md) — admin_ui vs gateway
- [Authentication architecture](./auth-architecture.md) — component map
- [Authenticated request flow (backend)](./auth-request-flow.md) — inside patients/ml
- [JIT user upsert](./auth-jit-upsert.md) — first proxied call creates `users` row
