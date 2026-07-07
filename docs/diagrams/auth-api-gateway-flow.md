# API Gateway Client Flow

Headless **gateway** service for **all non-browser API clients** (mobile, partners, scripts).
Validates Keycloak JWT at the edge, applies rate limiting and audit (planned), proxies to
internal services.

**Jira:** NLS-50..51, NLS-101..104 · **Status:** Planned (post-Pioneer)

Browser clinicians use [**admin_ui**](./auth-admin-ui-browser-flow.md) instead.

```mermaid
sequenceDiagram
    participant App as Mobile app / partner / script
    participant GW as API Gateway :api
    participant PAT as patients (internal)
    participant KC as Keycloak

    Note over App,PAT: They already have a token (from Keycloak elsewhere)
    App->>GW: GET /api/v1/patients + Bearer JWT
    GW->>GW: Check token, rate limit, log who asked
    GW->>PAT: Same request + Bearer JWT
    PAT->>KC: Verify signature (JWKS)
    PAT-->>GW: JSON
    GW-->>App: JSON

    Note over App,PAT: Optional later: admin_ui also uses gateway
    participant UI as admin_ui
    UI->>GW: GET /api/v1/patients (after browser login)
    GW->>PAT: proxy
```

## Gateway vs admin_ui

| | admin_ui | gateway |
|--|----------|---------|
| **Users** | Clinicians (browser) | Mobile, partners, automation |
| **UI** | React SPA embedded | None |
| **Login** | Keycloak OIDC + cookies | Bearer JWT only (client obtains token separately) |
| **When** | Pioneer (NLS-61..69) | Post-Pioneer |

## Related diagrams

- [Edge architecture](./edge-architecture.md)
- [Authentication architecture](./auth-architecture.md)
- [PaymentGate comparison](./auth-paymentgate-comparison.md)
