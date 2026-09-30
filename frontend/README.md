# Pawlice Report frontend

React + Vite local MVP. The browser uses relative `/api/...` paths; Vite forwards them to `http://127.0.0.1:8001` during development.

## Run locally

Start MySQL and FastAPI as described in [the backend README](../backend/README.md). In another terminal, from `frontend/`:

```bash
npm install
npm run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:5173/`. Create an account or sign in, then use `/` (My Suspects), `/pets/new` (Add Pet), `/pets/:id` (Pet Criminal Profile and Journal), and `/pets/:id/report` (shareable report). Each account sees only its own pets. The profile page can delete a pet and all of its journal entries. The Add Event form defaults to Incident and also supports Good Conduct, Funny Moment, and Wellness, with categories matched to the selected type. The timeline shows all event types, and statistics keep the crime details alongside journal counts. Choosing a mugshot while adding a pet or from its profile opens a square crop dialog before upload. Upload a photo with any event or from its timeline card; the full photo is shown in the journal. Common Photos formats including JPEG, PNG, HEIC/HEIF, TIFF, AVIF, and WebP are accepted up to 15 MB. A pet mugshot can also be supplied by URL.

From a pet profile, select **Generate Pawlice Report** to open the report page. Choose the current UTC week or month, generate the report, and download the card as a PNG. The page uses the backend's report statistics and narrative as returned; it does not recalculate them. PNG export uses `html-to-image` on the card element at 2× resolution, leaving page controls out of the file. Uploaded photos are embedded before export. External image URLs are included when their host allows browser cross-origin access; otherwise the card uses the existing no-mugshot fallback so export still works. The report API is called only when you select Generate or Refresh.

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
9. Open a pet's report page. Generate Weekly and Monthly reports, compare the card figures with the API response, and download each PNG. Check the exported image contains only the card. Try a pet with no events and a pet with a missing photo.
