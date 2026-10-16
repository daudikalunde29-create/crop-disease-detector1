# M4.2 change record

| FILE | CHANGE | REASON | TEST | STATUS |
|---|---|---|---|---|
| backend/apps/accounts/google.py (new) | Server-side Google ID-token verification (signature, issuer, audience, expiry, email_verified) | Real Google sign-in | Django tests (offline signed JWT + mocked layer) | PASS |
| backend/apps/accounts/models.py + migrations/0002_google_identity.py | `google_sub` (unique, nullable), `picture_url` | Link Google identity safely | makemigrations --check, tests | PASS |
| backend/apps/accounts/views.py | Google, google-config, password-reset, password-reset-confirm, change-password views | M4.2 endpoints | Django tests, live curl | PASS |
| backend/apps/accounts/password_reset.py (new) | Stateless HMAC reset token + email | Secure reset, nothing stored | Django tests, live curl | PASS |
| backend/apps/accounts/email_backends.py (new) | Copy-pasteable dev console email backend | Local reset testing without SMTP | Django tests, live curl | PASS |
| backend/apps/accounts/serializers.py, exceptions.py, urls.py | New serializers, 429/415 JSON errors, routes | Contracts | Django tests | PASS |
| backend/apps/predictions/ (new app) | `/api/predict/`, Pillow content validation, inference boundary, NullInferenceEngine | Prediction API foundation, no fake AI | Django tests (22), live curl | PASS |
| backend/api/urls.py, config/settings.py | Route + settings (Google, email, throttles, upload limits, in-memory uploads) | Wiring | check, tests | PASS |
| backend/requirements.txt, .env.example | google-auth, requests, Pillow; all new env vars documented | Dependencies/config | install + tests | PASS |
| public/site/js/google-auth.js | Client ID from /api/auth/google/config/; posts to /api/auth/google/ | One config source, no hardcoded ID | jsdom check | PASS (live Google NOT TESTED) |
| public/site/js/auth-pages.js, pages/reset-password.html | Token from link or pasted code; token removed from URL | Working reset UI | jsdom check | PASS |
| public/site/js/scan.js | Honest not_ready handling, multipart without forced Content-Type, 401 redirect | Scan page integration | jsdom check, live curl through Vite proxy | PASS |
| public/site/js/profile.js, pages/forgot-password.html | Comments/contract notes only (change-password already wired) | Accuracy | jsdom check | PASS |
| README.md, backend/README.md, public/site/ROADMAP.md, public/site/docs/AUTHENTICATION.md | M4.2 documentation | Required docs | review | PASS |
