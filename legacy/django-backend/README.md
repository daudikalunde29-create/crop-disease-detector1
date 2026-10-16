# Crop Disease Detector — Django backend (M4.2)

Real Django + Django REST Framework authentication for the frontend in `public/site/`.
Local development database: SQLite (MySQL arrives in **M5**).

Stage: **M4.2 — Google Authentication + Password Recovery + Prediction API Foundation**
(builds on M4.1 — Django core + email/password authentication).

## Setup (Windows PowerShell)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env        # then set DJANGO_SECRET_KEY (and optionally GOOGLE_CLIENT_ID)
python manage.py migrate
python manage.py createsuperuser   # optional, for /admin/ (role=admin)
python manage.py runserver 127.0.0.1:8000
```

macOS/Linux: `source .venv/bin/activate` and `cp .env.example .env`.

Frontend (second terminal, repository root):

```powershell
npm install
npm run dev
```

The Vite dev server proxies `/api/*` to `http://127.0.0.1:8000`; open the URL Vite prints
(this project's host layer serves on port 8080) and go to `/site/index.html`.

## Checks and tests

```powershell
cd backend
python manage.py check
python manage.py makemigrations --check
python manage.py test
```

Frontend (from the repository root): `npm.cmd run build`. There is no lint script in this minimal Vite package.

## Endpoints

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/health/` | – | `{"status":"ok"}` |
| POST | `/api/auth/register/` | – | `{fullName, email, phone, password}` → 201 `{user}` + session. 409 `EMAIL_EXISTS` |
| POST | `/api/auth/login/` | – | `{email, password, remember}` → `{user}`. 400 `AUTH_ERROR` |
| POST | `/api/auth/logout/` | – | Flushes the Django session |
| GET | `/api/auth/session/` | – | `{authenticated, user?}`; also sets the `csrftoken` cookie |
| GET | `/api/auth/me/` | session | `{user}`; 401 `NOT_AUTHENTICATED` |
| GET | `/api/auth/google/config/` | – | `{enabled, clientId}` (public Client ID from `GOOGLE_CLIENT_ID`) |
| POST | `/api/auth/google/` | – | `{credential}` (Google ID token) → `{user, created, linked}` + session |
| POST | `/api/auth/password-reset/` | – | `{email}` → always the same generic 200 message |
| POST | `/api/auth/password-reset-confirm/` | – | `{token, password}` → 200, or 400 `INVALID_RESET_TOKEN` / `VALIDATION_ERROR` |
| POST | `/api/auth/change-password/` | session | `{currentPassword, newPassword}` → `{success:true}` |
| POST | `/api/predict/` | session | multipart field `image` → validated; **503 `{"status":"not_ready", ...}`** until M8 |
| GET/PUT | `/api/profile/` | session | Read/update name and phone; email stays read-only |

User shape (unchanged): `{ id, name, email, phone, role: "farmer"|"admin", provider: "email"|"google", createdAt }`.
Errors are always `{ "code", "message" }` (+ `fields` for validation). No stack traces; passwords and tokens are never returned or logged.

## Google Sign-In

Flow: Google Identity Services → ID token → `POST /api/auth/google/` → Django verifies the token with
Google → finds/creates the user → **Django session**. The Google token is used once and discarded; it is never the app session.

**Server-side checks** (`apps/accounts/google.py`, using `google-auth`): signature against Google's public keys,
expiry, issuer (`accounts.google.com`), audience == `GOOGLE_CLIENT_ID`, `sub` and `email` present, `email_verified` is true.

**Setup**
1. Google Cloud Console → *APIs & Services* → *Credentials* → *Create credentials* → *OAuth client ID* → type **Web application**.
2. Under **Authorized JavaScript origins** add `http://localhost:8080` (and `http://127.0.0.1:8080` if you use that host). No redirect URI is needed.
3. Put the Client ID in `backend/.env`: `GOOGLE_CLIENT_ID=1234-abc.apps.googleusercontent.com`. Restart Django.
4. The frontend reads the same ID from `GET /api/auth/google/config/`, so there is one setting. No client *secret* is used or needed.

Without `GOOGLE_CLIENT_ID` the button renders disabled ("needs backend setup") and `POST /api/auth/google/` answers 503 `GOOGLE_NOT_CONFIGURED`.

**Account linking (deliberate behaviour)**
1. Known Google account (`google_sub`) → signs into that user.
2. Same *verified* email as an existing email/password account → that account is **linked** (no duplicate): `provider` becomes `google`, profile fields (name, phone) are kept. Because our own email sign-up never verified the mailbox, the old local password is **discarded** and the account's existing sessions are invalidated (prevents an attacker who pre-registered someone's email from keeping access). The owner can set a new password via *Forgot password*.
3. Otherwise → a new `farmer` user is created with `provider=google` and no usable password.
4. If the email's account is already linked to a *different* Google identity → 409 `GOOGLE_ACCOUNT_CONFLICT`. Disabled accounts get 403.

## Password reset

`POST /api/auth/password-reset/` always returns *"If an account exists for this email, password reset instructions have been sent."*
(same status and body for unknown, known and inactive emails; no enumeration). Rate limit: 10/hour per client.

The token is Django's `PasswordResetTokenGenerator` (HMAC, bound to the user's current password hash): **nothing is stored in the database**,
it is **single-use** (dies when the password changes), expires after `PASSWORD_RESET_TIMEOUT` (default 1 h), and a successful reset invalidates all the user's sessions.
The emailed value is `<uid>.<token>`; the link is `FRONTEND_ORIGIN/site/pages/reset-password.html?token=...`.

**Test it locally (no SMTP needed)**
1. Run Django with `DJANGO_DEBUG=True` and leave `EMAIL_BACKEND` empty in `.env`.
2. Register a user, log out, open `/site/pages/forgot-password.html`, submit the email.
3. The email is **printed in the Django terminal** (clearly marked *not delivered to any inbox*). Open the printed link, or paste the printed reset code on the reset page.
4. Choose a new password; log in with it.

Production: set `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend` plus `EMAIL_HOST/PORT/HOST_USER/HOST_PASSWORD/USE_TLS`, `DEFAULT_FROM_EMAIL`, and `FRONTEND_ORIGIN`.
If the backend cannot send, the API still returns the generic response (to avoid enumeration) and the failure is logged server-side — the UI never claims an email was *verified delivered*, only that instructions are sent if the account exists.

## Change password

Authenticated only. Verifies `currentPassword`, runs Django's password validators on `newPassword` (must differ from the current one), stores a PBKDF2 hash, keeps the
current browser signed in, and invalidates the user's other sessions. **Google-only accounts** (no local password) get 400 `NO_LOCAL_PASSWORD`; they create a password through *Forgot password*, after which this endpoint works. Rate limit: 10/hour.

## Prediction API foundation (`apps/predictions`)

`POST /api/predict/` — login required, CSRF enforced, `multipart/form-data` field `image`.
It validates the upload (**content decoded by Pillow**, not the filename/Content-Type): JPEG/PNG/WEBP only, max 5 MB (`PREDICT_MAX_UPLOAD_BYTES`),
max 40 megapixels (`PREDICT_MAX_IMAGE_PIXELS`), corrupt/truncated/empty files rejected. Oversized bodies are refused before parsing. Uploads are held in memory and **never written to disk**.

Then it calls the inference boundary (`apps/predictions/inference.py`). No model exists yet, so the default `NullInferenceEngine` reports not ready:

```json
{ "status": "not_ready", "message": "Prediction service is not available yet. The TensorFlow inference engine will be integrated in a later stage." }
```
(HTTP 503). **No disease, confidence, treatment or accuracy is ever fabricated.** A future engine implements `InferenceEngine.is_ready()/predict(image)` and is enabled with `PREDICTION_ENGINE=dotted.path.Class`.

## Security summary

- Django session cookie (`sessionid`, HttpOnly); no JWT, no tokens in localStorage.
- CSRF enforced on **every** unsafe request (anonymous included); the frontend sends `X-CSRFToken`.
- Secrets only in `backend/.env` (git-ignored). `GOOGLE_CLIENT_ID` is public by design.
- Passwords: PBKDF2 hashes; never returned, never logged.

## Why there is no CORS

The browser only talks to the frontend origin; Vite forwards `/api/*` to Django, so cookies stay same-origin. Django sees the
frontend `Origin`, so it is listed in `DJANGO_CSRF_TRUSTED_ORIGINS`. In production, serve both behind one origin or add the public origin there.

## Not implemented yet

MySQL (M5), OpenCV (M6), TensorFlow training (M7), real AI prediction and prediction history (M8+), profile editing (`PUT /api/profile/`), email verification for new email/password sign-ups, per-IP login throttling (M12).
