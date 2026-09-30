# Pawlice Report API (local MVP)

FastAPI backend for pets, incidents, journal events, per-pet statistics, and on-demand reports. Dates and times are stored in UTC. A timestamp without a timezone is treated as UTC. A week begins Monday at 00:00 UTC.

## Run locally with MySQL

Use Python 3.9 or newer. Start a dedicated MySQL container from the repository root (only the first time):

```bash
docker run -d --name pawlice-report-mysql \
  -e MYSQL_DATABASE=pawlice_report \
  -e MYSQL_USER=pawlice \
  -e MYSQL_PASSWORD=pawlice \
  -e MYSQL_ROOT_PASSWORD=pawlice-root-dev \
  -p 127.0.0.1:3307:3306 \
  -v pawlice-report-mysql-data:/var/lib/mysql \
  mysql:8.0
```

For later sessions, run `docker start pawlice-report-mysql` if it is stopped. Docker keeps the data in the named volume.

From `backend/`, configure `DATABASE_URL` and a random `SESSION_SECRET` in `.env`, then start the API:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
openssl rand -hex 32
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

Paste the output of `openssl rand -hex 32` after `SESSION_SECRET=` in `.env`. The existing local `.env` is already configured. The example sets `DATABASE_URL=mysql+pymysql://pawlice:pawlice@127.0.0.1:3307/pawlice_report`. Port 8001 is used because another local app occupies 8000; change the port if 8000 becomes free. SQLAlchemy creates missing tables on startup. Existing pets are assigned to the first account created after this update through the new `pet_owners` table; the existing `pets` table is not altered. The API is at `http://127.0.0.1:8001/api`, and interactive API docs are at `http://127.0.0.1:8001/docs`.

## One-time migration for an existing MySQL database

If `incidents` was created before events were added, stop the API, back up the database, and run [migrations/001_events.sql](migrations/001_events.sql) once from the repository root:

```bash
docker exec pawlice-report-mysql mysqldump -upawlice -ppawlice --single-transaction pawlice_report > /private/tmp/pawlice-before-events.sql
docker exec -i pawlice-report-mysql mysql -upawlice -ppawlice pawlice_report < backend/migrations/001_events.sql
```

The migration adds `event_type VARCHAR(20) NOT NULL DEFAULT 'INCIDENT'` and makes `severity` nullable. It leaves incident IDs, timestamps, image URLs, and stored files untouched. Existing rows become `INCIDENT`. A fresh database gets this schema from `create_all()` and does not need the migration; `create_all()` does **not** alter an existing table. The SQL file is intentionally one-time and will fail if rerun after the column exists.

## Routes

- `GET /api/health`
- `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`
- `POST /api/pets`, `GET /api/pets`, `GET /api/pets/{pet_id}`, `DELETE /api/pets/{pet_id}`
- `POST /api/pets/{pet_id}/image`, `GET /api/pets/{pet_id}/image`
- `POST /api/images/prepare` (authenticated JPEG preview for mugshot cropping; does not save a file)
- `POST /api/pets/{pet_id}/incidents`, `GET /api/pets/{pet_id}/incidents`
- `POST /api/pets/{pet_id}/events`, `GET /api/pets/{pet_id}/events`, `DELETE /api/events/{event_id}`
- `POST /api/incidents/{incident_id}/image`, `GET /api/incidents/{incident_id}/image`
- `POST /api/events/{event_id}/image`, `GET /api/events/{event_id}/image`
- `DELETE /api/incidents/{incident_id}`
- `GET /api/pets/{pet_id}/stats`
- `POST /api/pets/{pet_id}/reports`

Account routes accept JSON email and password. Registration and login set a signed, HTTP-only session cookie; logout clears it. Pets and events are private to their owner. Deleting a pet also deletes all its events and stored images. Existing incident routes create and return only `INCIDENT` rows; incident deletion and image routes cannot operate on other event types. A pet's `image_url` is an optional string for a pasted link. New incidents through the legacy route use photo upload instead of an `image_url` in the create request; incident responses still include `image_url` for stored photos and older records. Statistics retain the original incident-only fields and add total and per-type event counts. Most common category and average severity are null when a pet has no incidents. Equal category counts are resolved alphabetically.

The event API accepts `INCIDENT`, `GOOD_CONDUCT`, `FUNNY_MOMENT`, and `WELLNESS`. Use `event_time` in its JSON; the existing MySQL `incident_time` column stores it. Incidents require severity 1–5. Other types store null severity, even if a number is supplied. Categories are validated by type in `app/schemas.py`: existing crime categories for incidents; Good Behavior, Learned Something New, Calm During Grooming, Friendly Interaction, or Other for good conduct; Weird Sleeping Position, Funny Reaction, Got Stuck Somewhere, Random Chaos, or Other for funny moments; and Weight Check, Teeth Brushing, Nail Trim, Bath, Grooming, or Other for wellness. For example:

```bash
curl -fsS -b /tmp/pawlice-cookies.txt -X POST "$API/pets/$PET_ID/events" -H 'Content-Type: application/json' \
  -d '{"event_type":"FUNNY_MOMENT","category":"Weird Sleeping Position","description":"Fell asleep upside down in a box"}'
curl -fsS -b /tmp/pawlice-cookies.txt "$API/pets/$PET_ID/events"
```

## Weekly and monthly reports

`POST /api/pets/{pet_id}/reports` accepts `{"period":"weekly"}` or `{"period":"monthly"}` for the authenticated pet owner. It returns the current UTC calendar week (Monday to next Monday) or month (first day to first day of next month). `period_start` is inclusive and `period_end` is exclusive. Reports are calculated on demand and are not saved. No database migration is needed.

The response contains `pet_id`, `pet_name`, `period`, `period_start`, `period_end`, `stats`, `notable_events`, `headline`, `officer_summary`, `verdict`, `sentence`, and `narrative_source`. The `stats` object contains `total_events`, counts for each of the four event types, `most_common_incident_category`, `average_incident_severity`, and `most_active_event_day`. Incident category ties are resolved alphabetically; busiest-day ties use the earliest UTC date. Category and average severity are `null` when there are no incidents; busiest day is `null` when there are no events. Notable events include at most five records, preferring the highest-severity incident and the newest event of each other type, then filling by recency; they are returned newest first.

Set `OPENAI_API_KEY` in the backend `.env` to enable optional narrative writing with the official OpenAI SDK. `OPENAI_MODEL` defaults to `gpt-4o-mini` and can be changed in `.env`. The four narrative strings are validated against a strict schema. Missing API keys, provider failures, timeouts, and invalid structured responses use deterministic local text, with `narrative_source` set to `fallback`. The response never includes the API key or raw provider errors. Only the pet name, report statistics, and up to five selected event notes are sent to the provider.

With `API=http://127.0.0.1:8001/api`, `PET_ID` set, and an authenticated cookie jar from the manual checks below:

```bash
curl -fsS -b /tmp/pawlice-cookies.txt -X POST "$API/pets/$PET_ID/reports" \
  -H 'Content-Type: application/json' -d '{"period":"weekly"}'
curl -fsS -b /tmp/pawlice-cookies.txt -X POST "$API/pets/$PET_ID/reports" \
  -H 'Content-Type: application/json' -d '{"period":"monthly"}'
```

Image uploads use a multipart `file` field and accept Pillow-readable raster photos, including JPEG, PNG, WebP, HEIC/HEIF, TIFF, AVIF, BMP, and GIF, up to 15 MB and 50 megapixels. EPS is excluded. The server checks the photo's actual contents rather than trusting its file type label, then converts it to JPEG and stores it in `backend/uploads/` (or `UPLOAD_DIR` from `.env`). `/api/images/prepare` runs that same conversion and returns JPEG bytes without storing them, so the frontend can crop HEIC photos in the browser before a mugshot upload. Event uploads reuse the existing `uploads/incidents/{id}.jpg` storage; old incident image URLs remain valid. The returned `image_url` points to a private `/api/.../image` route; the browser sends the account session cookie when loading it. Uploading again replaces the image. These files are local data: keep the uploads directory if you want to retain them, and set up persistent storage separately before deployment.

For example, after creating a pet and incident, upload images with:

```bash
curl -fsS -b /tmp/pawlice-cookies.txt -F 'file=@/path/to/pet.jpg' "$API/pets/$PET_ID/image"
curl -fsS -b /tmp/pawlice-cookies.txt -F 'file=@/path/to/evidence.png' "$API/incidents/$INCIDENT_ID/image"
```

## Manual API checks

Run these in a second terminal. Use a fresh email address for registration. The cookie jar keeps the session for later requests, and the two Python snippets capture IDs returned by POST requests.

```bash
API=http://127.0.0.1:8001/api
curl -fsS -c /tmp/pawlice-cookies.txt -X POST "$API/auth/register" -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"choose-a-long-password"}'

PET_ID=$(curl -fsS -b /tmp/pawlice-cookies.txt -X POST "$API/pets" -H 'Content-Type: application/json' \
  -d '{"name":"Mochi","species":"Cat","breed":"Tabby","image_url":"https://example.com/mochi.jpg"}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
echo "$PET_ID"

curl -fsS -b /tmp/pawlice-cookies.txt "$API/pets"
curl -fsS -b /tmp/pawlice-cookies.txt "$API/pets/$PET_ID"

INCIDENT_ID=$(curl -fsS -b /tmp/pawlice-cookies.txt -X POST "$API/pets/$PET_ID/incidents" -H 'Content-Type: application/json' \
  -d '{"category":"Food Theft","description":"Stole a sandwich","severity":2}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
echo "$INCIDENT_ID"

curl -fsS -b /tmp/pawlice-cookies.txt "$API/pets/$PET_ID/incidents"
curl -fsS -b /tmp/pawlice-cookies.txt "$API/pets/$PET_ID/stats"
curl -i -b /tmp/pawlice-cookies.txt -X DELETE "$API/incidents/$INCIDENT_ID"
curl -i -b /tmp/pawlice-cookies.txt -X DELETE "$API/pets/$PET_ID"
```

Inspect the database directly (from the repository root):

```bash
docker exec pawlice-report-mysql mysql -upawlice -ppawlice pawlice_report \
  -e 'SHOW TABLES; SELECT id, name, species FROM pets; SELECT id, pet_id, category, severity FROM incidents;'
```

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

Tests exercise the API with an in-memory SQLite database, so they do not need MySQL running.
