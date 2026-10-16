# Build audit — M4.2 early workflow

This ZIP keeps the static frontend under `public/site/` and Django backend under `backend/`. It removes the old generated frontend scaffold and serves the static frontend with standard Vite.

## Fixes in this build

- CSRF initialization in `public/site/js/auth.js`: before a first POST, fetches `/api/auth/session/` if the CSRF cookie is missing. This targets the registration/login/password-reset failure caused by submitting before Django issued the cookie.
- Added authenticated `GET/PUT /api/profile/` for profile name and phone. Email is read-only.
- Added profile API tests.
- Added Windows setup/run scripts that use `backend/.venv` rather than accidentally creating the environment in the project root.
- Added clear demo-data banners to dashboard, history and admin preview; added a sample-result link from Scan.
- Demo JSON remains UI preview data only; no fake login and no fake AI prediction.
- Removed stale generated host-scaffold files and dependencies.

## Verification limits

Static JavaScript and Python syntax checks can be run without network access. Django tests require installing the backend requirements. Vite production build requires npm dependencies to be downloaded. This build must still be runtime-tested on the user's Windows machine.

## Still not implemented

- MySQL (M5)
- OpenCV preprocessing (M6)
- Dataset/model training (M7)
- Real TensorFlow/Keras inference (M8)
- Database-backed prediction history and disease knowledge/admin APIs
