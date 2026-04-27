# ARC Raiders — Blueprint Tracker

A self-hosted Docker app to track blueprint acquisition and learning status across multiple ARC Raiders characters.

## Features

- **Dashboard** — At-a-glance stats, character completion leaderboard, uncovered blueprints
- **Tracker** — Per-character blueprint status (Not Acquired / Acquired / Learned) with batch save
- **Reports** — Character summaries, blueprint coverage, missing-blueprint queries, exclusive blueprint detection, full-text search
- **Admin** — Full CRUD for characters and blueprints; seed sample data

## Stack

| Layer | Tech |
|---|---|
| Frontend | React 18 + Vite, served via nginx |
| Backend | Python 3.12 + Flask |
| Database | SQLite (persisted via Docker volume) |

## Quick Start

### Prerequisites
- Docker + Docker Compose v2

### Run

```bash
git clone <this-repo>
cd arc-raiders-tracker
docker compose up -d --build
```

- **App:** http://localhost:3333
- **API:** http://localhost:3333/api (proxied through nginx)

### First-Time Setup

1. Go to **Admin** → **Blueprints** → click **⚡ Seed Samples** to load ~20 sample blueprints across common categories
2. Go to **Admin** → **Characters** → add your characters
3. Go to **Tracker**, pick a character, and start marking blueprint statuses
4. Use **Reports** to analyze gaps across your roster

## Development (without Docker)

**Backend:**
```bash
cd backend
pip install -r requirements.txt
DATABASE_PATH=./arc_raiders.db python app.py
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev   # proxies /api → localhost:5000
```

## Data Model

```
characters          blueprints
──────────          ──────────
id                  id
name (unique)       name (unique)
class               category
notes               item_type
created_at          rarity
                    icon
                    source
                    description
                    created_at
                         │
                    character_blueprints       schema_migrations
                    ────────────────────       ─────────────────
                    character_id (FK)          version (PK)
                    blueprint_id (FK)          name
                    learned (0/1)              applied_at
                    acquired_count
                    updated_at
```

## Blueprint Statuses

| Field | Meaning |
|---|---|
| `learned = 1` | Fully learned — can craft this item |
| `learned = 0, acquired_count > 0` | Have the blueprint, not yet learned |
| `learned = 0, acquired_count = 0` | Haven't found/received this blueprint |

`extras` (computed) = spare copies available to trade: all `acquired_count` if already learned, otherwise `acquired_count - 1`.

## Schema Migrations

The backend uses a lightweight, built-in migration system — no external tools required.

### How it works

- On every startup `run_migrations()` is called before Flask begins serving requests.
- A `schema_migrations` table records which migrations have been applied (version number, name, timestamp).
- Pending migrations are applied in version order; already-applied ones are skipped.
- Each migration runs in its own transaction — a failure rolls back that migration only and halts startup with a descriptive error.

### Inspecting migration state at runtime

```
GET /api/migrations
```

Returns a JSON array describing every known migration and whether it has been applied:

```json
[
  { "version": 1, "name": "initial_schema",                       "applied": true, "applied_at": "2025-01-01 12:00:00" },
  { "version": 2, "name": "blueprints_icon_source",               "applied": true, "applied_at": "2025-01-02 09:00:00" },
  { "version": 3, "name": "character_blueprints_learned_acquired", "applied": true, "applied_at": "2025-01-02 09:00:00" },
  { "version": 4, "name": "migrate_legacy_status_values",          "applied": true, "applied_at": "2025-01-02 09:00:00" }
]
```

### Adding a new migration

1. Write a function that accepts a single `db` (`sqlite3.Connection`) argument and performs the schema change. Do **not** call `db.commit()` inside it — the runner commits for you.
2. Append a tuple to the `MIGRATIONS` list in `backend/app.py`:

```python
def _m005_add_blueprints_patch_notes(db):
    db.execute("ALTER TABLE blueprints ADD COLUMN patch_notes TEXT DEFAULT ''")

MIGRATIONS = [
    ...
    (5, "add_blueprints_patch_notes", _m005_add_blueprints_patch_notes),
]
```

3. Restart the backend — the new migration runs automatically on the next startup.

> **Rule:** never edit or remove an already-applied migration. Version numbers must be unique and always increasing.

## Stopping / Data

```bash
docker compose down          # stop containers, keep data
docker compose down -v       # stop and DELETE all data
```

Data is persisted via the bind mount `./data:/data` inside the container (`./data/arc_raiders.db` on the host).
