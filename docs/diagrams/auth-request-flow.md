# Authentication Request Flow

Authenticated API requests follow this sequence. `/health` remains public.

```mermaid
sequenceDiagram
    participant C as Client
    participant F as FastAPI handler
    participant D as require_clinician
    participant A as KeycloakAuthAdapter
    participant K as Keycloak JWKS
    participant R as UserRepository
    participant DB as users table

    C->>F: GET /api/v1/patients + Authorization Bearer
    F->>D: Depends(require_clinician)
    D->>A: get_user(token)
    A->>K: fetch signing key
    A->>A: verify iss, aud, exp, realm roles
    A-->>D: UserInfo(user_id=usr_sub, email, roles)
    opt USER_UPSERT_ENABLED and AUTH_ENABLED
        D->>R: upsert_from_user_info
        R->>DB: INSERT ON CONFLICT UPDATE
    end
    D->>D: check clinician or admin in roles
    D-->>F: UserInfo
    F->>F: execute query/command with user_id audit
```

## Local development

When `AUTH_ENABLED=false`, `NullAuthAdapter` returns a fixed dev user with
`clinician` and `admin` roles. No Keycloak or Postgres connection is required.
