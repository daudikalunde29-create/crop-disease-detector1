# Crop Disease Detector

A web application that lets farmers and agronomists upload photos of crop leaves, keep a history of their scans, and track results — with AI-powered disease detection as a planned capability.

## What it does

- **Sign up & sign in** — email/password and Google accounts. New users are given the `farmer` role automatically.
- **Scan a crop** — upload a photo of a plant leaf (up to 5 MB). The image is stored securely and a scan record is created for your account.
- **Scan history** — browse your own past scans, view each scan's details and photo, and delete any scan.
- **Profile** — view and update your account details; change your password.
- **Admin area** — users with the `admin` role can review scan activity and manage crop/disease reference data. Regular users cannot enter this area.
- **Honest results** — scans are stored as `not_ready` until a real detection model is connected. The app never shows a made-up prediction. Sample content is clearly labelled **DEMO DATA**.

## Tech stack

- **Frontend:** vanilla HTML, CSS and Bootstrap (in `public/site/`)
- **Backend:** Lovable Cloud (hosted database, authentication, and file storage)
- **Bridge:** a small script bundle (`public/site/js/cloud.bundle.js`, built from `src/cloud-bridge/`) connects the static pages to the backend
- **Reference code:** the original Django backend is kept under `legacy/django-backend` for reference only — it is not used or deployed

## Project structure

```
public/site/          # The website (HTML pages, styles, scripts)
src/cloud-bridge/     # Script that connects the site pages to the backend
scripts/build-bridge.sh  # Rebuild the bridge bundle after editing the bridge
drizzle/migrations/   # Database tables, permissions, and signup rules
legacy/django-backend # Original Django code (reference only, not deployed)
```

## Running locally

You need [Node.js](https://nodejs.org) (v20+) or [Bun](https://bun.sh) installed.

1. Install dependencies:

```sh
bun install        # or: npm install
```

2. Add a `.env` file with your backend URL and publishable key:

```
VITE_SUPABASE_URL=https://your-project-url
VITE_SUPABASE_PUBLISHABLE_KEY=your-publishable-key
VITE_SUPABASE_PROJECT_ID=your-project-id
```

3. Start the app:

```sh
bun run dev        # or: npm run dev
```

4. Open the app — the home address redirects to the site pages.

## Making changes

- Edit the website files directly in `public/site/`.
- If you change anything in `src/cloud-bridge/`, rebuild the bundle with:

```sh
bash scripts/build-bridge.sh
```

- Database changes are managed through migration files in `drizzle/migrations/`.

## Roles

Roles are stored in a protected `user_roles` table (never in user-editable profile data):

| Role   | Access                                              |
|--------|-----------------------------------------------------|
| farmer | Default for new users. Scans, history, profile.     |
| admin  | Everything a farmer has, plus the admin area.       |

Admin access is checked on the server, so a regular user cannot grant themselves admin.

## Storage

Uploaded scan photos go into a private storage bucket (`scan-images`) with a 5 MB size limit. Each user can only read the files they uploaded.

## Roadmap

- Connect a real crop-disease AI model so scans return genuine predictions instead of `not_ready`.
- Email confirmation and password-reset emails.
