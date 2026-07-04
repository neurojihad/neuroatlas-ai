# Authentication Architecture

NeuroAtlas uses **OpenID Connect (OIDC) access tokens in JWT format**, validated at the
API boundary. **Keycloak** is the default identity provider. Domain code depends on the
`AuthAdapter` port only — swapping IdPs does not touch handlers or commands.

**Browser entry (Pioneer / M2):** clinicians use **`admin_ui`** (:8000) — OIDC session,
cookies, embedded React, guard proxy. See [admin UI browser flow](./auth-admin-ui-browser-flow.md).

**API entry (post-Pioneer):** headless **gateway** for mobile, partners, and scripts.
See [API Gateway client flow](./auth-api-gateway-flow.md).

```mermaid
flowchart TB
    subgraph client [Clients]
        Browser[Browser clinician]
        CLI[CLI / Swagger / curl]
        API[Mobile / partner]
    end

    subgraph edge [Edge layer]
        ADMIN[admin_ui :8000]
        GW[gateway planned]
    end

    subgraph idp [Identity Provider]
        KC[Keycloak realm neuroatlas]
    end

    subgraph services [Backend services]
        PAT[patients :8001]
        ML[ml :8002]
    end

    subgraph auth [Auth stack per service]
        H[HTTP handlers]
        DEP[auth_dependencies]
        PORT[AuthAdapter port]
        ADAPT[KeycloakAuthAdapter / NullAuthAdapter]
    end

    subgraph db [PostgreSQL neuroatlas]
        USERS[(users shadow table)]
    end

    Browser -->|OIDC + cookies| ADMIN
    ADMIN -->|Bearer JWT| PAT
    ADMIN --> KC
    API --> GW
    GW --> PAT
    CLI -->|Bearer JWT direct| PAT
    CLI -.->|optional| GW

    PAT --> H
    H --> DEP
    DEP --> PORT
    PORT --> ADAPT
    ADAPT -->|JWKS verify| KC
    DEP -->|JIT upsert| USERS
    H -->|audit user_id| LOG[structlog]
```

## Flow summary

| Path | Client | Token at backend | Status |
|------|--------|------------------|--------|
| **admin_ui browser** | Clinician → admin_ui with cookies | Keycloak JWT forwarded by admin_ui | Pioneer (NLS-61..69) |
| **API Gateway** | Mobile / partner → gateway with Bearer | JWT validated at gateway; forwarded | Planned (NLS-50..51) |
| **Direct API** | curl / Swagger → patients | Keycloak JWT in `Authorization` header | Supported (dev smoke) |
| **Auth disabled** | Any | `NullAuthAdapter` dev user | Local tests (`AUTH_ENABLED=false`) |

## Module layout

| Module | Layer | Purpose |
|--------|-------|---------|
| `common/core/ports/auth.py` | Port | `AuthAdapter` ABC |
| `common/adapters/auth/keycloak.py` | Adapter | JWKS validation, role extraction |
| `common/adapters/http/auth_dependencies.py` | Adapter | FastAPI `Depends`, Swagger `HTTPBearer` |
| `common/core/entities/user.py` | Domain entity | `UserInfo` (no PHI) |
| `src/admin_ui/` | Adapter | BFF: OIDC cookies, React, guard proxy (**NLS-61 scaffold**) |
| `src/gateway/` (planned) | Adapter | Headless API Gateway: JWT, route, rate limit |

## Related diagrams

- [Edge architecture](./edge-architecture.md) — admin_ui vs gateway, target module layout
- [Admin UI browser flow](./auth-admin-ui-browser-flow.md) — **Pioneer clinician login**
- [API Gateway client flow](./auth-api-gateway-flow.md) — mobile / partner path
- [Authenticated request flow (backend)](./auth-request-flow.md)
- [Keycloak user registration (admin)](./auth-keycloak-user-registration.md)
- [Users schema](./auth-users-schema.md)
- [JIT upsert](./auth-jit-upsert.md)
- [PaymentGate comparison](./auth-paymentgate-comparison.md)
