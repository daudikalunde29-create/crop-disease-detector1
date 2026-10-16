# Authentication — Crop Disease Detector

## 1. Current architecture

```text
Frontend (HTML + Bootstrap + Vanilla JS)
        |
        | same-origin /api/*
        v
Vite development proxy
        |
        v
Django + Django REST Framework
        |
        v
Django session + SQLite (M4.1)
```

The frontend is not a fake authentication system. Email/password authentication
is implemented by Django. The browser receives a server-side Django session cookie.

### Frontend files

- `js/auth.js` — authentication API client, CSRF header, auth states and UI helpers.
- `js/session.js` — session checks, protected-page UX, logout and navbar state.
- `js/google-auth.js` — Google Identity Services button; gets the Client ID from `GET /api/auth/google/config/` and posts the ID token to `/api/auth/google/`.
- `js/auth-pages.js` — login/register/forgot/reset form wiring.
- `js/profile.js` — change-password form.
- `js/scan.js` — multipart upload to `/api/predict/` with an honest `not_ready` message.

### Backend files

- `backend/apps/accounts/models.py` — custom Django User model.
- `backend/apps/accounts/views.py` — register/login/logout/session/me, Google, password reset and change-password endpoints.
- `backend/apps/accounts/google.py` — server-side Google ID-token verification.
- `backend/apps/accounts/password_reset.py` — reset tokens and reset email.
- `backend/apps/predictions/` — `/api/predict/` upload validation and the inference boundary.
- `backend/apps/accounts/authentication.py` — CSRF enforcement for unsafe API calls.
- `backend/config/settings.py` — session, CSRF and SQLite configuration.

## 2. Implemented in M4.1

| Method | Endpoint | Status |
|---|---|---|
| GET | `/api/health/` | Implemented |
| POST | `/api/auth/register/` | Implemented |
| POST | `/api/auth/login/` | Implemented |
| POST | `/api/auth/logout/` | Implemented |
| GET | `/api/auth/session/` | Implemented |
| GET | `/api/auth/me/` | Implemented |

Registration and login create a real Django session. Passwords are hashed using
Django's password hasher and are never returned to the frontend.

## 3. Implemented in M4.2

| Method | Endpoint | Status |
|---|---|---|
| GET | `/api/auth/google/config/` | Implemented |
| POST | `/api/auth/google/` | Implemented (token verified server-side) |
| POST | `/api/auth/password-reset/` | Implemented (generic response, rate-limited) |
| POST | `/api/auth/password-reset-confirm/` | Implemented (single-use, expiring token) |
| POST | `/api/auth/change-password/` | Implemented |
| POST | `/api/predict/` | Foundation only: validates the image, returns `not_ready` (503). No AI result exists. |

### Google Sign-In

```text
User -> Google Identity Services -> ID token -> frontend
     -> POST /api/auth/google/ {credential}
     -> Django verifies signature, issuer, audience (GOOGLE_CLIENT_ID), expiry, email_verified
     -> find or create user -> Django session cookie -> {user}
```

The Google ID token is never stored (not in localStorage, sessionStorage or cookies) and is never the session.
Configure `GOOGLE_CLIENT_ID` in `backend/.env` and add the frontend origin under *Authorized JavaScript origins* in Google Cloud Console
(full steps in `backend/README.md`). Without it, the button is shown disabled and the endpoint answers 503.

**Account linking.** An existing email/password account with the same *verified* Google email is linked (never duplicated), and its
unverified local password is discarded and its sessions invalidated; the owner can set a new password through *Forgot password*.
A new Google email creates a `farmer` user with `provider: "google"` and no usable password.
An account linked to a different Google identity gets 409.

### Password reset

`forgot-password.html` → `POST /api/auth/password-reset/` (always the same message) → Django emails `reset-password.html?token=<code>` →
`reset-password.html` → `POST /api/auth/password-reset-confirm/ {token, password}`. Tokens are HMAC-based, not stored, single-use, expire
(default 1 h), and a reset logs the user out everywhere. In development the email is printed in the Django terminal; if the page is opened
without `?token=`, the user can paste the printed code. The frontend never creates or displays a token.

### Change password

Profile page → `POST /api/auth/change-password/ {currentPassword, newPassword}`. The current browser stays signed in; other sessions are
invalidated. Google-only accounts have no local password: the profile hides the form and the API answers `NO_LOCAL_PASSWORD`
(they create a password via *Forgot password*).

### Prediction foundation

`scan.html` posts `multipart/form-data` (`image`) to `/api/predict/`. Django requires a session, validates type (by content), size (5 MB) and
integrity, and answers `{"status":"not_ready", "message":...}` because no model is installed. The scan page shows that message; it never shows a
disease, confidence or treatment it did not receive. `result.html` still displays clearly-labelled **sample** data and is not connected to real predictions.

## 4. Session and CSRF

- `GET /api/auth/session/` is the source of truth for authentication.
- The backend uses Django's server-side session framework.
- `sessionid` is HttpOnly.
- The `csrftoken` cookie is readable by the frontend so `auth.js` can send
  `X-CSRFToken` on unsafe requests.
- CSRF is enforced for anonymous and authenticated unsafe API requests.
- The Vite dev server proxies `/api/*` to `http://127.0.0.1:8000`, keeping
  the browser request same-origin.
- Password-flow endpoints are rate-limited (`password-reset` 10/h, `password-reset-confirm` 20/h, `change-password` 10/h).

## 5. Security rules

- Never store passwords in localStorage/sessionStorage.
- Never treat `localStorage.cdd_user` as proof of authentication.
- Never use a Google ID token as the application session or store it.
- Never hardcode a Google Client ID; it comes from `GOOGLE_CLIENT_ID`. No Google client secret is used.
- Backend role checks must remain authoritative.
- Never commit `backend/.env`, `backend/db.sqlite3`, virtual environments or secrets.

## 6. Automated tests

`python manage.py test` (from `backend/`) covers, without any network access:

- M4.1: registration, duplicates, weak passwords, login, remember-me, session, logout, me, hashing, CSRF, invalid JSON, health.
- Google: real `google-auth` verification against a locally signed JWT (signature, expiry, audience, issuer, unverified email, wrong key,
  malformed, unreachable Google, unconfigured); endpoint behaviour with the verification layer mocked (new user, returning user, account
  linking, pre-hijack defence, conflict, disabled account, session creation, CSRF).
- Password reset: generic response, no enumeration, token validity, tamper/other-user/expired/reused tokens, weak passwords, old password
  rejected, sessions invalidated, no token stored or logged, SMTP failure, rate limit.
- Change password: auth required, wrong current, weak new, success, other sessions invalidated, Google-only account.
- Prediction: auth required, missing/invalid/oversized/unsupported/truncated uploads, valid JPG/PNG/WEBP, `not_ready`, no fabricated result,
  nothing written to disk, inference boundary with a stub engine.

Run:

```sh
cd backend
python manage.py check
python manage.py makemigrations --check
python manage.py test
```

## 7. Not tested automatically

A real Google sign-in (needs your Client ID and a browser) and delivery through a real SMTP server must be verified manually.

MySQL, OpenCV, TensorFlow and real AI predictions remain later stages and are not claimed as implemented.
