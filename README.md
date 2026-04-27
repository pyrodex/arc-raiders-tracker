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

- **App:** http://localhost:3000
- **API:** http://localhost:5000/api

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
                    description
                    created_at
                         │
                    character_blueprints
                    ────────────────────
                    character_id (FK)
                    blueprint_id (FK)
                    status: not_acquired | acquired | learned
                    updated_at
```

## Blueprint Statuses

| Status | Meaning |
|---|---|
| `not_acquired` | Haven't found/received this blueprint |
| `acquired` | Have the blueprint but haven't learned/crafted it yet |
| `learned` | Fully learned — can craft this item |

## Stopping / Data

```bash
docker compose down          # stop containers, keep data
docker compose down -v       # stop and DELETE all data
```

Data is stored in a Docker named volume `arc-raiders-tracker_sqlite_data`.
