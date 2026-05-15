# CLAUDE.md — Grants Compliance Dashboard

## Stack
- Python 3.11+
- Streamlit (multipage via `/pages`)
- SQLAlchemy 2.x ORM (async-free; sync sessions only)
- Alembic for all schema changes
- Supabase Postgres (psycopg2-binary driver)
- Pandas + Plotly for data and charts
- streamlit-calendar for the calendar page

## Conventions
- All DB access via `get_session()` context manager from `src/db.py`
- All user identity via `get_current_user()` from `src/auth.py` — never hardcode user IDs elsewhere
- Every owned table has `organization_id` defaulting to 1
- Enums live in `src/models.py`; never use raw strings for status/type fields
- Business logic goes in `src/services/`; raw queries go in `src/repositories/`
- Never commit `.env` or `.streamlit/secrets.toml`

## Schema changes
Run `alembic revision --autogenerate -m "description"` then review the generated file before applying.
Never edit the DB schema by hand.

## Running locally
```bash
cp .env.example .env          # fill in DATABASE_URL and APP_PASSWORD
pip install -r requirements.txt
alembic upgrade head
python seed.py                # optional: load sample data
streamlit run app.py
```

## Deploying to Streamlit Community Cloud
1. Push to GitHub
2. Connect repo in Streamlit Cloud
3. Add secrets: `password = "yourpassword"` and `DATABASE_URL = "..."`
4. Set main file to `app.py`
