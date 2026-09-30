# Pawlice Report backend

FastAPI, MySQL, SQLAlchemy, and signed cookie accounts. Pets and incidents are private to their owner. Pet profiles can be deleted.

Set `DATABASE_URL` and `SESSION_SECRET` in `backend/.env`, then run `uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload`.
