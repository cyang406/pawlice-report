# Pawlice Report frontend

React + Vite local MVP. The browser uses relative `/api/...` paths; Vite forwards them to `http://127.0.0.1:8001` during development.

## Run locally

Start MySQL and FastAPI as described in [the backend README](../backend/README.md). In another terminal, from `frontend/`:

```bash
npm install
npm run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:5173/`. Create an account or sign in, then use `/` (My Suspects), `/pets/new` (Add Pet), and `/pets/:id` (Pet Criminal Profile). Each account sees only its own pets. The profile page can delete a pet and all of its incidents. Upload a mugshot while adding a pet or from its profile; upload evidence when filing a report or from an incident card. JPEG, PNG, and WebP images up to 5 MB are accepted. The existing image URL fields still accept links; an uploaded file takes priority when both are supplied.

To check the production compilation locally, run `npm run build`.

## Quick manual check

1. Register an account, sign out, and sign in again. Confirm the roster is protected when signed out.
2. Open `/` and confirm your pets appear. If there are none, check the empty state and Add Suspect action.
3. Add a pet with an uploaded mugshot. Confirm it appears on the new profile and roster. Replace the mugshot from the profile.
4. File an incident with uploaded evidence, then replace the evidence from its card. Confirm the photo and statistics update.
5. File another incident with an image URL and confirm newest-first ordering. Try a broken URL and confirm the fallback.
6. Delete an incident, then delete the pet profile. Confirm the roster updates.
7. Repeat at a narrow browser width to check the mobile layout.
