<!-- Generated from `origin/master..HEAD` on branch `NLS-78-add-DatabaseException-adapter-layer-exception`. Auto-updated by pre-push hook. -->

#### Fixed

1) Auth and proxy review fixes — open redirect sanitization; refresh only on JWT expiry; `/auth/me` auto-refresh; cookie delete with matching attrs; guard 502 uses ErrorSchema

2) GitHub PR template — error handlers fix

3) admin_ui guard proxy `/guard/api/v1/*` — error handlers fix

4) src/common/application/app_factory.py — error handlers fix

5) src/common/core/exceptions.py — error handlers fix

6) src/housekeeper/adapters/http/handlers.py — error handlers fix

7) src/ml/adapters/http/handlers.py — error handlers fix

8) src/patients/adapters/http/handlers.py — error handlers fix

#### Changed

1) admin_ui OIDC auth handlers — error handlers fix

2) src/common/http/error_handlers.py	src/common/application/error_handlers.py — error_handlers.py

3) src/common/http/schemas.py	src/common/adapters/http/schemas.py — schemas.py

#### Added

1) src/common/adapters/http/__init__.py — error handlers fix

2) src/common/tests/test_http/test_error_handlers.py — error handlers fix
