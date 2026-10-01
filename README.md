# Pawlice Report: local Docker Compose

This runs the production React build behind Nginx with FastAPI and a fresh, separate MySQL database. It does not use your existing local MySQL container or Vite server.

## Start

From the repository root:

```sh
cp .env.example .env
```

Edit the new root `.env`: set unique, long alphanumeric `MYSQL_PASSWORD` and `MYSQL_ROOT_PASSWORD` values, a random `SESSION_SECRET` of at least 32 characters, and your `OPENAI_API_KEY`. The app's `DATABASE_URL` is assembled from those MySQL values, so avoid URL punctuation in the MySQL password. Keep `OPENAI_MODEL` at the model you already use. The root `.env` is ignored by Git. If you already configured `backend/.env`, copy only the OpenAI key and model values into the root `.env`; do not commit either file.

```sh
docker compose build
docker compose up -d
docker compose ps
docker compose logs --tail=50
curl http://localhost/
curl http://localhost/api/health
```

Open <http://localhost/>. Stop the stack with `docker compose down` and restart it with `docker compose up -d`. The named volumes survive `down`; `down -v` deletes the database and uploaded images.

## How requests travel

Only Nginx publishes a host port (`80:80`). It serves the compiled React files and sends `/api/*` to `backend:8000`. React Router URLs fall back to `index.html`. All current image endpoints are under `/api/`, so they use the same proxy. FastAPI receives `DATABASE_URL` from Compose, assembled from the root `.env` values with `mysql:3306` as the host. Compose service names resolve through its internal network; `localhost` inside a container means that same container. The frontend image receives no OpenAI key or database credentials.

MySQL data lives in the `mysql_data` named volume. Uploaded pet and event images live in `uploaded_images`, mounted at `/app/uploads` in the backend. The application stores image URLs such as `/api/pets/1/image?...`; Nginx proxies those requests to FastAPI.

## Database initialization

On an empty MySQL volume, MySQL creates the database and user from the root `.env`, then FastAPI's existing startup code creates all tables using the current SQLAlchemy models. This includes `incidents.event_type` with default `INCIDENT` and nullable `incidents.severity`.

`create_all` does **not** change existing tables. If you bring an older pre-events MySQL database into this Compose stack, back it up and apply the one-time [events migration](backend/migrations/001_events.sql) after checking whether `event_type` already exists. Do not apply it twice. Existing local database contents and upload files are not copied into the new named volumes automatically.

## Useful checks

```sh
docker compose exec nginx wget -q -O - http://backend:8000/api/health
docker compose exec backend python -c 'from app.database import engine; from sqlalchemy import text; print(engine.connect().scalar(text("SELECT 1")))'
docker compose logs backend --tail=100
```

To inspect the MySQL schema without exposing its password on the host command line:

```sh
docker compose exec -T mysql sh -c 'MYSQL_PWD="$MYSQL_PASSWORD" mysql -u "$MYSQL_USER" "$MYSQL_DATABASE" -e "SHOW TABLES; SHOW COLUMNS FROM incidents;"'
```
