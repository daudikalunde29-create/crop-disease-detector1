<!-- LOVABLE:BEGIN -->
> [!IMPORTANT]
> This project is connected to [Lovable](https://lovable.dev). Avoid rewriting
> published git history — force pushing, or rebasing/amending/squashing commits
> that are already pushed — as it rewrites history on Lovable's side and the
> user will likely lose their project history.
>
> Commits you push to the connected branch sync back to Lovable and show up in
> the editor, so keep the branch in a working state.
<!-- LOVABLE:END -->

## Crop Disease Detector
- The user-facing UI is the vanilla HTML/Bootstrap site in `public/site/`; `/` redirects there. Why: preserves the original M1–M4.2 UI.
- Static pages reach Lovable Cloud only via `window.CDDCloud` from `public/site/js/cloud.bundle.js`, built from `src/cloud-bridge/entry.ts` with `scripts/build-bridge.sh`. Rebuild after editing the entry. Why: shares the generated client and preview auth storage.
- Roles live in `user_roles` (new users get `farmer`); admin access is enforced by RLS via `has_role`. Why: prevents privilege escalation.
- Scans store an image plus a `not_ready` record; never fabricate predictions until a real model exists.
- `legacy/django-backend` is reference only, not deployed.
