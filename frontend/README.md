# Pawlice Report frontend

React + Vite local MVP. The browser uses relative `/api/...` paths; Vite forwards them to `http://127.0.0.1:8001` during development.

## Run locally

Start MySQL and FastAPI as described in [the backend README](../backend/README.md). In another terminal, from `frontend/`:

```bash
npm install
npm run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:5173/`. Create an account or sign in, then use `/` (My Suspects), `/pets/new` (Add Pet), and `/pets/:id` (Pet Criminal Profile). Each account sees only its own pets. The profile page can delete a pet and all of its incidents. Choosing a mugshot while adding a pet or from its profile opens a square crop dialog before upload. Upload evidence when filing a report or from an incident card; the full photo is shown in the incident log. Common Photos formats including JPEG, PNG, HEIC/HEIF, TIFF, AVIF, and WebP are accepted up to 15 MB. A pet mugshot can also be supplied by URL. Incident evidence uses file upload.

To check the production compilation locally, run `npm run build`.

## Quick manual check

1. Register an account, sign out, and sign in again. Confirm the roster is protected when signed out.
2. Open `/` and confirm your pets appear. If there are none, check the empty state and Add Suspect action.
3. Add a pet with an uploaded mugshot. Move and zoom the crop, then confirm that exact square appears on the new profile and roster. Replace the mugshot from the profile and crop it again.
4. File an incident with uploaded evidence, then replace the evidence from its card. Confirm the entire image is visible and statistics update.
5. File another incident and confirm newest-first ordering. Try a broken pet mugshot URL and confirm the fallback.
6. Delete an incident, then delete the pet profile. Confirm the roster updates.
7. Repeat at a narrow browser width to check the mobile layout.
