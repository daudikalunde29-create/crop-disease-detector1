
## Frontend structure (M1)
Plain HTML5 + CSS3 + Bootstrap 5 + Vanilla JS + JSON. Open `index.html` in a browser or serve the folder with any static server (`python3 -m http.server`).

- `js/language.js` — translations; `js/app.js` — shared helpers and `CDD_CONFIG`
- Auth: `js/auth.js` (central helper), `js/session.js` (protected pages),
  `js/google-auth.js` (real Google Identity Services),
  `js/auth-pages.js` (form wiring)
- Page scripts: dashboard, scan, result, history, profile, admin
- `data/` — mock data only, not real AI output
- Search `FUTURE DJANGO API` for the integration points. See `ROADMAP.md`.

## Authentication

- **Email/password** — register, login, logout, remember-me, forgot/reset
  password, change password, with validation, loading states and clear
  error/success messages.
- **Google authentication** — official Google Identity Services "Continue
  with Google" button (`js/google-auth.js`). The Google ID token is sent to
  Django for server-side verification; it is never used as the app session.
  Provide the public Client ID via `<meta name="cdd-google-client-id">` or `window.CDD_GOOGLE_CLIENT_ID` to enable it. No fake
  Google login, no client secret in frontend code.
- **Session management** — centralized in `js/session.js`; protected pages
  verify the session on every load, expired sessions redirect to login with
  a message, and logout fully destroys the session.
- **Password reset** — `pages/forgot-password.html` and
  `pages/reset-password.html` (token via URL). The reset link is emailed by Django.
- **Protected routes** — dashboard, scan, result, history, profile require
  login; admin dashboard additionally requires the admin role (backend must
  re-check authorization — the frontend gate is UX only).
- **User roles** — `farmer` / `admin` on the user object; navbar elements
  use `data-auth="guest|user|admin"`.
- **Django integration** — every auth function maps 1:1 to a Django
  endpoint with CSRF support. Mock authentication has been removed: login only works once the Django
  backend (M4) serves `/api/auth/*`. Set `window.CDD_API_BASE` if Django runs on another origin.

Full details, API contracts and the testing checklist: `docs/AUTHENTICATION.md`.

## Project structure
- `public/site/` — the Crop Disease Detector app (all pages, CSS, JS). This is the real application.
- The repository root `index.html` redirects to `/site/index.html`; standard Vite serves the existing HTML app directly.
