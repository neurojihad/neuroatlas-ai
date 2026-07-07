<!-- Generated from `origin/master..HEAD` on branch `NSL-65-realise-react-admin-UI-auth-pages`. Auto-updated by pre-push hook. -->

#### Fixed

1) Auth and proxy review fixes — open redirect sanitization; refresh only on JWT expiry; `/auth/me` auto-refresh; cookie delete with matching attrs; guard 502 uses ErrorSchema

2) Makefile / make.ps1 — frontend fix

3) admin_ui guard proxy `/guard/api/v1/*` — frontend fix

4) admin_ui tests — frontend fix

5) src/common/adapters/http/auth_dependencies.py — frontend fix

#### Changed

1) admin_ui auth session (PKCE, cookies, JWT split) — frontend fix

2) src/admin_ui/ service — hexagonal-style shell
ui/.gitignore — added
ui/package.json — added
ui/public/index.html — added
ui/src/App.js — added
ui/src/ConfigError.js — added
ui/src/SuspenseLoader.js — added
ui/src/app/providers/AuthProvider.jsx — added
ui/src/app/providers/QueryClientProvider.jsx — added
ui/src/app/providers/index.jsx — added
ui/src/index.css — added
ui/src/index.js — added
ui/src/layout/AppLayout.jsx — added
ui/src/layout/BackgroundLayer.jsx — added
ui/src/layout/components/Menu.jsx — added
ui/src/layout/index.js — added
ui/src/neural-nexus.css — added
ui/src/pages/auth/AuthLayout.js — added
ui/src/pages/auth/Callback.js — added
ui/src/pages/auth/Login.js — added
ui/src/pages/dashboard/Dashboard.js — added
ui/src/pages/dashboard/index.js — added
ui/src/pages/notfound/NotFound.js — added
ui/src/pages/patients/Patients.js — added
ui/src/pages/patients/index.js — added
ui/src/pages/patients/queries/patients.js — added
ui/src/pages/patients/ui/PatientProfile.js — added
ui/src/pages/patients/ui/PatientsList.js — added
ui/src/pages/session/Session.js — added
ui/src/pages/session/index.js — added
ui/src/setupProxy.js — added
ui/src/shared/api/HttpAuthBase.js — added
ui/src/shared/api/HttpBase.js — added
ui/src/shared/api/httpAuthApi.js — added
ui/src/shared/api/httpPatientsApi.js — added
ui/src/shared/api/httpUserApi.js — added
ui/src/shared/components/NavigateToAuth.js — added
ui/src/shared/components/ProtectedRedirect.js — added
ui/src/shared/components/ProtectedRoute.js — added
ui/src/shared/config/apiConfig.js — added
ui/src/shared/config/index.js — added
ui/src/shared/config/queryClient.js — added
ui/src/shared/constants/api.js — added
ui/src/shared/constants/menu.js — added
ui/src/shared/constants/roles.js — added
ui/src/shared/hooks/useAuth.js — added
ui/src/shared/hooks/withSuspense.js — added
ui/src/shared/services/AuthService.js — added
ui/src/shared/utils/generate.js — added

#### Added

1) .vscode/settings.json — frontend fix

2) bin/make.bat — frontend fix

3) bin/make.cmd — frontend fix

4) docs/design/neural-nexus-demo.html — frontend fix

5) make.bat — frontend fix

6) scripts/dev/install-make-command.ps1 — frontend fix

7) scripts/dev/install-venv-make.ps1 — frontend fix

8) scripts/dev/pycharm-terminal-init.ps1 — frontend fix

9) scripts/dev/setup-pycharm-make.ps1 — frontend fix

10) scripts/dev/venv-make.cmd — frontend fix
