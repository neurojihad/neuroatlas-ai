# E2E smoke — admin_ui browser path (NLS-68)

Verifies the **admin_ui BFF → patients** path with a real Keycloak JWT and JIT shadow-user upsert.

Automated test: `src/common/tests/integration/test_nls68_admin_ui_smoke.py`  
Make target: `make smoke_admin_ui` (Windows: `.\make.ps1 smoke_admin_ui`)

## Prerequisites

1. **Infra + app stack**

   ```powershell
   .\make.ps1 up_infra
   .\make.ps1 migrate
   ```

   In `infra/.env`:

   ```env
   AUTH_ENABLED=true
   USER_UPSERT_ENABLED=true
   ```

   ```powershell
   .\make.ps1 up_app
   ```

2. **Keycloak clinician user** (one-time) — see [auth-keycloak-user-registration.md](../diagrams/auth-keycloak-user-registration.md):
   - Create user in Keycloak Admin Console (`http://localhost:8080`, admin/admin)
   - Set password (not temporary)
   - Assign realm role **clinician**

3. **Smoke credentials** in `infra/.env` (or shell env):

   ```env
   SMOKE_USERNAME=dr.sokolov@clinic.org
   SMOKE_PASSWORD=your-password
   ```

## Automated smoke

```powershell
.\make.ps1 smoke_admin_ui
```

Uses password grant against `neuroatlas-api` to obtain a JWT, builds the same split session cookies as the browser BFF, then:

1. `GET /api/v1/auth/me` on admin_ui → 200
2. `GET /guard/api/v1/patients` → 200
3. Asserts a row exists in Postgres `users` for the token `sub` (JIT upsert)

## Manual browser smoke (curl-free)

1. Open [http://localhost:8000](http://localhost:8000)
2. Sign in via Keycloak SSO
3. Navigate to **Patients Registry** — list loads without 401/502
4. Optional DB check:

   ```sql
   SELECT id, keycloak_sub, email FROM users ORDER BY created_at DESC LIMIT 5;
   ```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Keycloak **Client not found** (`neuroatlas-ui`) | `.\make.ps1 keycloak_ensure` (or `.\make.ps1 reset_keycloak` + recreate user) |
| `401` on `/guard/api/v1/patients` | `AUTH_ENABLED=true`; token has `clinician` role; audience mapper on Keycloak clients |
| No `users` row | `USER_UPSERT_ENABLED=true`; run `make migrate`; patients Postgres reachable |
| Keycloak `invalid_grant` | Reset password; use `--data-urlencode` in curl; check username |
| Smoke test skipped | Export `SMOKE_INTEGRATION=1` and set `SMOKE_USERNAME` / `SMOKE_PASSWORD` |
