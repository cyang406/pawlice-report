# Pawlice Report frontend

React + Vite local MVP. The browser uses relative `/api/...` paths; Vite forwards them to `http://127.0.0.1:8001` during development.

## Run locally

Start MySQL and FastAPI as described in [the backend README](../backend/README.md). In another terminal, from `frontend/`:

```bash
npm install
npm run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:5173/`. Create an account or sign in, then use `/` (My Suspects), `/pets/new` (Add Pet), and `/pets/:id` (Pet Criminal Profile and Journal). Each account sees only its own pets. The profile page can delete a pet and all of its journal entries. The Add Event form defaults to Incident and also supports Good Conduct, Funny Moment, and Wellness, with categories matched to the selected type. The timeline shows all event types, and statistics keep the crime details alongside journal counts. Choosing a mugshot while adding a pet or from its profile opens a square crop dialog before upload. Upload a photo with any event or from its timeline card; the full photo is shown in the journal. Common Photos formats including JPEG, PNG, HEIC/HEIF, TIFF, AVIF, and WebP are accepted up to 15 MB. A pet mugshot can also be supplied by URL.

To check the production compilation locally, run `npm run build`.

## Quick manual check

1. Register an account, sign out, and sign in again. Confirm the roster is protected when signed out.
2. Open `/` and confirm your pets appear. If there are none, check the empty state and Add Suspect action.
3. Add a pet with an uploaded mugshot. Move and zoom the crop, then confirm that exact square appears on the new profile and roster. Replace the mugshot from the profile and crop it again.
4. File an incident with severity 1–5 and uploaded evidence. Confirm it appears in the timeline and the crime statistics update.
5. Switch the form to Good Conduct, Funny Moment, and Wellness. Confirm each has its own categories and no severity field. Add one of each and confirm the timeline is newest first and all four counts update.
6. Replace a timeline photo; confirm the full image appears. Existing incident photos should still load. Entries with broken image links should show the photo fallback.
7. Delete each type of entry and confirm the timeline and counts refresh. Delete the pet profile and confirm the roster updates.
8. Repeat at a narrow browser width to check the mobile layout.
