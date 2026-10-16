# Development Roadmap — Crop Disease Detector

## M0 — Foundation
- [x] Project structure, requirements, Git, environment and documentation

## M1 — Frontend UI
- [x] Public pages: Home, About, How It Works, Supported Crops
- [x] Farmer dashboard, Scan, Result, History, Profile, Admin dashboard
- [x] English / Kiswahili UI
- [x] Responsive Bootstrap interface

## M2 — Frontend Logic & UX
- [x] Navigation and protected-page UX
- [x] Form validation
- [x] Scan image validation and preview
- [x] History/result/dashboard UI
- [x] Clearly marked mock JSON data for UI preview only

## M3 — Frontend Authentication
- [x] Register/login/logout/session UI
- [x] Remember-me contract
- [x] Real Google Identity Services frontend integration contract
- [x] CSRF-ready API client
- [x] Backend session is the authentication source of truth
- [x] No fake authentication

## M4.1 — Django Core + Real Email/Password Authentication — DONE
- [x] Django + Django REST Framework backend
- [x] Custom Django User model
- [x] SQLite development database
- [x] Django session authentication
- [x] Server-side password hashing and validation
- [x] CSRF enforcement for unsafe API requests
- [x] Register, login, logout, session and current-user endpoints
- [x] Health endpoint
- [x] Authentication tests
- [x] Vite `/api/*` development proxy to Django
- [x] Backend and project documentation

## M4.2 — Google Auth + Password Recovery + Prediction API Foundation — DONE (automated verification passed)
- [x] Google ID-token verification on Django (`POST /api/auth/google/`)
- [x] Find/create/link Google users safely (documented account-linking policy)
- [x] Password reset request/confirm (stateless, single-use, expiring tokens)
- [x] Change-password endpoint (Google-only accounts handled)
- [x] Development email backend + SMTP-ready configuration
- [x] `POST /api/predict/` foundation: auth, content-validated upload, size limit, `not_ready` response, inference boundary
- [x] Frontend wired: Google button, forgot/reset password, change password, scan page
- [x] Django tests (100) + frontend lint/build + proxy and flow verification
- [ ] Manual check on your machine: real Google sign-in with your Client ID, and real SMTP delivery (cannot be automated)

## M5 — MySQL Database — NEXT
- [ ] MySQL configuration and environment handling
- [ ] User/profile/crop/disease/prediction/history models
- [ ] Migration verification

## M6 — Image Processing
- [x] Secure image upload foundation (done in M4.2)
- [ ] Persist/handle uploads as the architecture requires
- [ ] OpenCV validation/preprocessing
- [ ] Resize/normalisation/quality checks

## M7 — AI Dataset & Training
- [ ] Dataset preparation
- [ ] Augmentation
- [ ] Transfer-learning training
- [ ] Validation/evaluation
- [ ] Model artifact/versioning

## M8 — Real AI Prediction
- [ ] TensorFlow/Keras inference service
- [ ] `/api/predict/`
- [ ] Confidence handling
- [ ] Persist predictions

## M9 — Disease Knowledge System
- [ ] Verified disease information
- [ ] Symptoms
- [ ] Prevention
- [ ] Management guidance

## M10 — Complete Scan System
- [ ] Camera/upload → preprocessing → AI → result → database → history

## M11 — Admin System
- [ ] User management
- [ ] Crop/disease management
- [ ] Prediction/history management
- [ ] Server-side role permissions

## M12 — Security & Validation
- [ ] Production CSRF/session settings
- [ ] Upload security
- [ ] Rate limiting and abuse controls
- [ ] Authorization review

## M13 — Testing & Accuracy
- [ ] Backend unit/integration tests
- [ ] Frontend tests
- [ ] End-to-end authentication/scan tests
- [ ] Model evaluation and accuracy reporting

## M14 — Deployment
- [ ] Production Django configuration
- [ ] MySQL deployment
- [ ] Static/media serving
- [ ] HTTPS and production environment

## M15 — Final Release
- [ ] Final documentation
- [ ] Installation guide
- [ ] Cleanup
- [ ] Release ZIP
