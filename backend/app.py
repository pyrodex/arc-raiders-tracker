import os
import sqlite3
import traceback
from flask import Flask, jsonify, request, g
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DATABASE = os.environ.get("DATABASE_PATH", "./arc_raiders.db")


def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA foreign_keys=ON")
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


# ── Schema migrations ─────────────────────────────────────────────────────────
#
# Add new migrations by appending a tuple to MIGRATIONS:
#
#   (version: int, name: str, up: callable(db) -> None)
#
# Rules:
#   - version numbers must be unique and monotonically increasing.
#   - Each callable receives an open sqlite3.Connection and must NOT call
#     db.commit() — the runner handles that.
#   - Never modify or remove an already-applied migration; only append new ones.

def _m001_initial_schema(db):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS characters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            class TEXT,
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS blueprints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            category TEXT NOT NULL DEFAULT 'Uncategorized',
            item_type TEXT,
            rarity TEXT DEFAULT 'Common',
            description TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS character_blueprints (
            character_id   INTEGER NOT NULL,
            blueprint_id   INTEGER NOT NULL,
            updated_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (character_id, blueprint_id),
            FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE,
            FOREIGN KEY (blueprint_id) REFERENCES blueprints(id) ON DELETE CASCADE
        );
    """)


def _m002_blueprints_icon_source(db):
    """Add icon and source columns to blueprints (back-fills existing rows)."""
    for col, typedef in [
        ("icon",   "TEXT DEFAULT '📋'"),
        ("source", "TEXT DEFAULT ''"),
    ]:
        try:
            db.execute(f"ALTER TABLE blueprints ADD COLUMN {col} {typedef}")
        except sqlite3.OperationalError:
            pass  # column already present — safe to ignore


def _m003_character_blueprints_learned_acquired(db):
    """Replace the old single-column status with learned + acquired_count."""
    for col, typedef in [
        ("learned",        "INTEGER NOT NULL DEFAULT 0"),
        ("acquired_count", "INTEGER NOT NULL DEFAULT 0"),
    ]:
        try:
            db.execute(f"ALTER TABLE character_blueprints ADD COLUMN {col} {typedef}")
        except sqlite3.OperationalError:
            pass  # column already present — safe to ignore


def _m004_migrate_legacy_status_values(db):
    """One-time data migration from the old status TEXT column to learned/acquired_count."""
    try:
        db.execute(
            "UPDATE character_blueprints "
            "SET learned=1, acquired_count=0 "
            "WHERE status='learned' AND learned=0 AND acquired_count=0"
        )
        db.execute(
            "UPDATE character_blueprints "
            "SET learned=0, acquired_count=1 "
            "WHERE status='acquired' AND learned=0 AND acquired_count=0"
        )
    except sqlite3.OperationalError:
        pass  # status column does not exist — nothing to migrate


# Ordered list of all migrations.  Append new entries here as the schema evolves.
MIGRATIONS = [
    (1, "initial_schema",                       _m001_initial_schema),
    (2, "blueprints_icon_source",               _m002_blueprints_icon_source),
    (3, "character_blueprints_learned_acquired", _m003_character_blueprints_learned_acquired),
    (4, "migrate_legacy_status_values",          _m004_migrate_legacy_status_values),
]


def _ensure_migrations_table(db):
    db.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version    INTEGER PRIMARY KEY,
            name       TEXT    NOT NULL,
            applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.commit()


def _applied_versions(db):
    return {row[0] for row in db.execute("SELECT version FROM schema_migrations").fetchall()}


def run_migrations():
    """Apply every unapplied migration in version order.

    Each migration runs inside its own transaction so a failure leaves
    previously-applied migrations intact.  A RuntimeError is raised if any
    migration fails, halting application startup.
    """
    with app.app_context():
        db = get_db()
        _ensure_migrations_table(db)
        applied = _applied_versions(db)

        for version, name, up in sorted(MIGRATIONS, key=lambda m: m[0]):
            if version in applied:
                continue
            print(f"[migrations] Applying {version:04d}_{name} …")
            try:
                up(db)
                db.execute(
                    "INSERT INTO schema_migrations (version, name) VALUES (?, ?)",
                    (version, name),
                )
                db.commit()
                print(f"[migrations] {version:04d}_{name} applied successfully.")
            except Exception as exc:
                db.rollback()
                raise RuntimeError(
                    f"Migration {version:04d}_{name} failed: {exc}\n"
                    + traceback.format_exc()
                ) from exc


# ── helpers ──────────────────────────────────────────────────────────────────

def extras(learned, acquired_count):
    """Spare copies: all acquired if already learned, else all-but-one."""
    return acquired_count if learned else max(0, acquired_count - 1)


# ── Characters ───────────────────────────────────────────────────────────────

@app.route("/api/characters", methods=["GET"])
def list_characters():
    db = get_db()
    rows = db.execute("SELECT id, name, class, notes, created_at FROM characters ORDER BY name").fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/characters", methods=["POST"])
def create_character():
    data = request.get_json()
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO characters (name, class, notes) VALUES (?, ?, ?)",
            (name, data.get("class", ""), data.get("notes", "")),
        )
        new_id = cur.lastrowid
        db.execute("""
            INSERT OR IGNORE INTO character_blueprints (character_id, blueprint_id, learned, acquired_count)
            SELECT ?, id, 0, 0 FROM blueprints
        """, (new_id,))
        db.commit()
        row = db.execute("SELECT * FROM characters WHERE id=?", (new_id,)).fetchone()
        return jsonify(dict(row)), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": f"Character '{name}' already exists"}), 409


@app.route("/api/characters/<int:cid>", methods=["GET"])
def get_character(cid):
    db = get_db()
    row = db.execute("SELECT * FROM characters WHERE id=?", (cid,)).fetchone()
    if not row:
        return jsonify({"error": "Not found"}), 404
    return jsonify(dict(row))


@app.route("/api/characters/<int:cid>", methods=["PUT"])
def update_character(cid):
    data = request.get_json()
    db = get_db()
    row = db.execute("SELECT * FROM characters WHERE id=?", (cid,)).fetchone()
    if not row:
        return jsonify({"error": "Not found"}), 404
    name = (data.get("name") or row["name"]).strip()
    try:
        db.execute(
            "UPDATE characters SET name=?, class=?, notes=? WHERE id=?",
            (name, data.get("class", row["class"]), data.get("notes", row["notes"]), cid),
        )
        db.commit()
        return jsonify(dict(db.execute("SELECT * FROM characters WHERE id=?", (cid,)).fetchone()))
    except sqlite3.IntegrityError:
        return jsonify({"error": f"Character '{name}' already exists"}), 409


@app.route("/api/characters/<int:cid>", methods=["DELETE"])
def delete_character(cid):
    db = get_db()
    if not db.execute("SELECT id FROM characters WHERE id=?", (cid,)).fetchone():
        return jsonify({"error": "Not found"}), 404
    db.execute("DELETE FROM characters WHERE id=?", (cid,))
    db.commit()
    return jsonify({"deleted": cid})


# ── Blueprints ───────────────────────────────────────────────────────────────

@app.route("/api/blueprints", methods=["GET"])
def list_blueprints():
    db = get_db()
    return jsonify([dict(r) for r in db.execute("SELECT * FROM blueprints ORDER BY category, name").fetchall()])


@app.route("/api/blueprints", methods=["POST"])
def create_blueprint():
    data = request.get_json()
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO blueprints (name, category, item_type, rarity, icon, source, description) VALUES (?,?,?,?,?,?,?)",
            (name, data.get("category","Uncategorized"), data.get("item_type",""),
             data.get("rarity","Common"), data.get("icon","📋"),
             data.get("source",""), data.get("description","")),
        )
        new_id = cur.lastrowid
        db.execute("""
            INSERT OR IGNORE INTO character_blueprints (character_id, blueprint_id, learned, acquired_count)
            SELECT id, ?, 0, 0 FROM characters
        """, (new_id,))
        db.commit()
        return jsonify(dict(db.execute("SELECT * FROM blueprints WHERE id=?", (new_id,)).fetchone())), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": f"Blueprint '{name}' already exists"}), 409


@app.route("/api/blueprints/<int:bid>", methods=["PUT"])
def update_blueprint(bid):
    data = request.get_json()
    db = get_db()
    row = db.execute("SELECT * FROM blueprints WHERE id=?", (bid,)).fetchone()
    if not row:
        return jsonify({"error": "Not found"}), 404
    db.execute(
        "UPDATE blueprints SET name=?, category=?, item_type=?, rarity=?, icon=?, source=?, description=? WHERE id=?",
        ((data.get("name") or row["name"]).strip(), data.get("category", row["category"]),
         data.get("item_type", row["item_type"]), data.get("rarity", row["rarity"]),
         data.get("icon", row["icon"]), data.get("source", row["source"]),
         data.get("description", row["description"]), bid),
    )
    db.commit()
    return jsonify(dict(db.execute("SELECT * FROM blueprints WHERE id=?", (bid,)).fetchone()))


@app.route("/api/blueprints/<int:bid>", methods=["DELETE"])
def delete_blueprint(bid):
    db = get_db()
    if not db.execute("SELECT id FROM blueprints WHERE id=?", (bid,)).fetchone():
        return jsonify({"error": "Not found"}), 404
    db.execute("DELETE FROM blueprints WHERE id=?", (bid,))
    db.commit()
    return jsonify({"deleted": bid})


@app.route("/api/blueprints/categories", methods=["GET"])
def list_categories():
    db = get_db()
    return jsonify([r["category"] for r in db.execute("SELECT DISTINCT category FROM blueprints ORDER BY category").fetchall()])


# ── Character Blueprint Status ────────────────────────────────────────────────

@app.route("/api/characters/<int:cid>/blueprints", methods=["GET"])
def get_character_blueprints(cid):
    db = get_db()
    rows = db.execute("""
        SELECT b.id, b.name, b.category, b.item_type, b.rarity, b.icon, b.source,
               COALESCE(cb.learned, 0)        AS learned,
               COALESCE(cb.acquired_count, 0) AS acquired_count,
               cb.updated_at
        FROM blueprints b
        LEFT JOIN character_blueprints cb
          ON cb.blueprint_id = b.id AND cb.character_id = ?
        ORDER BY b.category, b.name
    """, (cid,)).fetchall()
    result = [dict(r) | {"extras": extras(r["learned"], r["acquired_count"])} for r in rows]
    return jsonify(result)


@app.route("/api/characters/<int:cid>/blueprints/<int:bid>", methods=["PUT"])
def set_blueprint_status(cid, bid):
    data = request.get_json()
    lrn = int(bool(data.get("learned", 0)))
    cnt = max(0, int(data.get("acquired_count", 0)))
    db = get_db()
    db.execute("""
        INSERT INTO character_blueprints (character_id, blueprint_id, learned, acquired_count, updated_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(character_id, blueprint_id)
        DO UPDATE SET learned=excluded.learned, acquired_count=excluded.acquired_count,
                      updated_at=excluded.updated_at
    """, (cid, bid, lrn, cnt))
    db.commit()
    return jsonify({"character_id": cid, "blueprint_id": bid,
                    "learned": lrn, "acquired_count": cnt, "extras": extras(lrn, cnt)})


@app.route("/api/characters/<int:cid>/blueprints/bulk", methods=["PUT"])
def bulk_set_blueprints(cid):
    updates = request.get_json()
    db = get_db()
    count = 0
    for item in updates:
        bid = item.get("blueprint_id")
        if not bid:
            continue
        lrn = int(bool(item.get("learned", 0)))
        cnt = max(0, int(item.get("acquired_count", 0)))
        db.execute("""
            INSERT INTO character_blueprints (character_id, blueprint_id, learned, acquired_count, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(character_id, blueprint_id)
            DO UPDATE SET learned=excluded.learned, acquired_count=excluded.acquired_count,
                          updated_at=excluded.updated_at
        """, (cid, bid, lrn, cnt))
        count += 1
    db.commit()
    return jsonify({"updated": count})


# ── Reports ───────────────────────────────────────────────────────────────────

@app.route("/api/reports/missing-blueprint", methods=["GET"])
def report_missing_blueprint():
    bid = request.args.get("blueprint_id", type=int)
    if not bid:
        return jsonify({"error": "blueprint_id required"}), 400
    db = get_db()
    bp = db.execute("SELECT * FROM blueprints WHERE id=?", (bid,)).fetchone()
    if not bp:
        return jsonify({"error": "Blueprint not found"}), 404
    rows = db.execute("""
        SELECT c.id, c.name, c.class,
               COALESCE(cb.learned, 0)        AS learned,
               COALESCE(cb.acquired_count, 0) AS acquired_count
        FROM characters c
        LEFT JOIN character_blueprints cb ON cb.character_id=c.id AND cb.blueprint_id=?
        WHERE COALESCE(cb.learned,0)=0 AND COALESCE(cb.acquired_count,0)=0
        ORDER BY c.name
    """, (bid,)).fetchall()
    return jsonify({"blueprint": dict(bp), "missing_count": len(rows),
                    "characters": [dict(r) for r in rows]})


@app.route("/api/reports/character-summary", methods=["GET"])
def report_character_summary():
    db = get_db()
    total = db.execute("SELECT COUNT(*) AS c FROM blueprints").fetchone()["c"]
    chars = db.execute("SELECT id, name, class FROM characters ORDER BY name").fetchall()
    result = []
    for ch in chars:
        row = db.execute("""
            SELECT
                SUM(learned)                                                        AS learned,
                SUM(CASE WHEN learned=0 AND acquired_count>0 THEN 1 ELSE 0 END)    AS acquired_not_learned,
                SUM(CASE WHEN learned=1 THEN acquired_count
                         ELSE MAX(0, acquired_count-1) END)                         AS total_extras
            FROM character_blueprints WHERE character_id=?
        """, (ch["id"],)).fetchone()
        lrn    = row["learned"] or 0
        acq_nl = row["acquired_not_learned"] or 0
        xtr    = row["total_extras"] or 0
        result.append({
            "id": ch["id"], "name": ch["name"], "class": ch["class"],
            "total": total, "learned": lrn,
            "acquired_not_learned": acq_nl,
            "missing": total - lrn - acq_nl,
            "total_extras": xtr,
            "completion_pct": round((lrn / total * 100) if total else 0, 1),
        })
    return jsonify(result)


@app.route("/api/reports/blueprint-coverage", methods=["GET"])
def report_blueprint_coverage():
    db = get_db()
    total_chars = db.execute("SELECT COUNT(*) AS c FROM characters").fetchone()["c"]
    bps = db.execute("SELECT id, name, category, rarity, icon FROM blueprints ORDER BY category, name").fetchall()
    result = []
    for bp in bps:
        row = db.execute("""
            SELECT
                SUM(learned)                                                        AS learned,
                SUM(CASE WHEN learned=0 AND acquired_count>0 THEN 1 ELSE 0 END)    AS acquired_only,
                SUM(CASE WHEN learned=1 THEN acquired_count
                         ELSE MAX(0, acquired_count-1) END)                         AS total_extras
            FROM character_blueprints WHERE blueprint_id=?
        """, (bp["id"],)).fetchone()
        lrn   = row["learned"] or 0
        acq_o = row["acquired_only"] or 0
        xtr   = row["total_extras"] or 0
        result.append({
            "id": bp["id"], "name": bp["name"],
            "category": bp["category"], "rarity": bp["rarity"],
            "total_chars": total_chars,
            "learned": lrn, "acquired_only": acq_o,
            "missing": total_chars - lrn - acq_o,
            "total_extras": xtr,
            "coverage_pct": round((lrn / total_chars * 100) if total_chars else 0, 1),
        })
    return jsonify(result)


@app.route("/api/reports/characters-with-blueprint", methods=["GET"])
def report_chars_with_blueprint():
    bid = request.args.get("blueprint_id", type=int)
    if not bid:
        return jsonify({"error": "blueprint_id required"}), 400
    db = get_db()
    bp = db.execute("SELECT * FROM blueprints WHERE id=?", (bid,)).fetchone()
    if not bp:
        return jsonify({"error": "Blueprint not found"}), 404
    rows = db.execute("""
        SELECT c.id, c.name, c.class, cb.learned, cb.acquired_count, cb.updated_at
        FROM characters c
        JOIN character_blueprints cb ON cb.character_id=c.id
        WHERE cb.blueprint_id=? AND (cb.learned=1 OR cb.acquired_count>0)
        ORDER BY cb.learned DESC, cb.acquired_count DESC, c.name
    """, (bid,)).fetchall()
    out = [dict(r) | {"extras": extras(r["learned"], r["acquired_count"])} for r in rows]
    return jsonify({"blueprint": dict(bp), "characters": out})


@app.route("/api/reports/unique-blueprints", methods=["GET"])
def report_unique_blueprints():
    db = get_db()
        rows = db.execute("""
        SELECT b.id, b.name, b.category, b.rarity, b.icon,
               c.id AS char_id, c.name AS char_name, c.class AS char_class
        FROM blueprints b
        JOIN character_blueprints cb ON cb.blueprint_id=b.id AND cb.learned=1
        JOIN characters c ON c.id=cb.character_id
        WHERE (SELECT COUNT(*) FROM character_blueprints WHERE blueprint_id=b.id AND learned=1)=1
        ORDER BY b.category, b.name
    """).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/reports/extras", methods=["GET"])
def report_extras():
    """All character/blueprint pairs where spare copies > 0."""
    db = get_db()
    rows = db.execute("""
        SELECT c.id AS char_id, c.name AS char_name, c.class AS char_class,
               b.id AS bp_id, b.name AS bp_name, b.category, b.rarity, b.icon,
               cb.learned, cb.acquired_count,
               CASE WHEN cb.learned=1 THEN cb.acquired_count
                    ELSE MAX(0, cb.acquired_count-1) END AS extras
        FROM character_blueprints cb
        JOIN characters c ON c.id=cb.character_id
        JOIN blueprints b ON b.id=cb.blueprint_id
        WHERE (cb.learned=1 AND cb.acquired_count>0)
           OR (cb.learned=0 AND cb.acquired_count>1)
        ORDER BY extras DESC, b.name, c.name
    """).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/reports/search", methods=["GET"])
def report_search():
    q = (request.args.get("q") or "").strip()
    if len(q) < 2:
        return jsonify({"blueprints": [], "characters": []})
    db = get_db()
    like = f"%{q}%"
    bps   = db.execute("SELECT * FROM blueprints WHERE name LIKE ? OR category LIKE ? OR description LIKE ? ORDER BY name LIMIT 50", (like,like,like)).fetchall()
    chars = db.execute("SELECT * FROM characters WHERE name LIKE ? OR class LIKE ? OR notes LIKE ? ORDER BY name LIMIT 50", (like,like,like)).fetchall()
    return jsonify({"blueprints": [dict(r) for r in bps], "characters": [dict(r) for r in chars]})


# ── Health & Seed ─────────────────────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/seed", methods=["POST"])
def seed_sample_data():
    db = get_db()
    blueprints = [
        # ── Weapons ──────────────────────────────────────────────────────
        ("Anvil",                     "Weapons", "Assault Rifle",    "Common",    "🔫", "All maps — Raider Containers"),
        ("Aphelion",                  "Weapons", "Sniper Rifle",     "Rare",      "🎯", "Stella Montis only — any container"),
        ("Bettina",                   "Weapons", "SMG",              "Common",    "🔫", "All maps — Raider Containers"),
        ("Bobcat",                    "Weapons", "LMG",              "Epic",      "🔫", "Event: Locked Gate or Hurricane — First Wave Cache / anywhere"),
        ("Burletta",                  "Weapons", "Pistol",           "Epic",      "🔫", "Quest: Industrial Espionage"),
        ("Canto",                     "Weapons", "SMG",              "Rare",      "🔫", "Event: Hurricane — First Wave Raider Caches (Flashpoint 1.22.0)"),
        ("Deadline",                  "Weapons", "Sniper Rifle",     "Rare",      "🎯", "Stella Montis only — any container"),
        ("Dolabra",                   "Weapons", "Energy Shotgun",   "Legendary", "🔫", "Event: Close Scrutiny — ARC Assessor containers (Flashpoint 1.22.0)"),
        ("Equalizer",                 "Weapons", "Assault Rifle",    "Legendary", "🔫", "Event: Harvester — completion reward"),
        ("Hullcracker",               "Weapons", "Shotgun",          "Epic",      "🔫", "Quest: The Major's Footlocker"),
        ("Il Toro",                   "Weapons", "LMG",              "Common",    "🔫", "All maps — Raider Containers"),
        ("Jupiter",                   "Weapons", "Heavy Weapon",     "Legendary", "🔫", "Event: Harvester — completion reward"),
        ("Osprey",                    "Weapons", "Marksman Rifle",   "Common",    "🎯", "All maps — Raider Containers"),
        ("Showstopper",               "Weapons", "Shotgun",          "Common",    "🔫", "All maps — Raider Containers"),
        ("Tempest I",                 "Weapons", "Assault Rifle",    "Epic",      "🔫", "Event: Night Raid — any map"),
        ("Torrente",                  "Weapons", "Shotgun",          "Common",    "🔫", "All maps — Raider Containers"),
        ("Venator",                   "Weapons", "Assault Rifle",    "Common",    "🔫", "All maps — Raider Containers"),
        ("Vulcano",                   "Weapons", "Grenade Launcher", "Epic",      "🔫", "Event: Hidden Bunker"),
        ("Wolfpack",                  "Weapons", "SMG",              "Rare",      "🔫", "All maps — elevated conditions recommended"),
        # ── Attachments ──────────────────────────────────────────────────
        ("Angled Grip II",            "Attachments", "Grip",     "Common",   "🔧", "All maps — Residential Containers"),
        ("Angled Grip III",           "Attachments", "Grip",     "Uncommon", "🔧", "Electromagnetic Storm / Locked Gate / Night Raid — Residential Containers"),
        ("Compensator II",            "Attachments", "Muzzle",   "Common",   "🔧", "All maps — Residential Containers"),
        ("Compensator III",           "Attachments", "Muzzle",   "Uncommon", "🔧", "Electromagnetic Storm / Locked Gate / Night Raid — Residential Containers"),
        ("Extended Barrel",           "Attachments", "Barrel",   "Uncommon", "🔧", "Electromagnetic Storm / Locked Gate / Night Raid — Residential Containers"),
        ("Extended Light Mag II",     "Attachments", "Magazine", "Common",   "🔧", "All maps — Residential Containers"),
        ("Extended Light Mag III",    "Attachments", "Magazine", "Uncommon", "🔧", "Electromagnetic Storm / Locked Gate / Night Raid — Residential Containers"),
        ("Extended Medium Mag II",    "Attachments", "Magazine", "Uncommon", "🔧", "All maps Night Raid — Residential Containers"),
        ("Extended Medium Mag III",   "Attachments", "Magazine", "Rare",     "🔧", "Electromagnetic Storm / Locked Gate / Night Raid — Residential Containers"),
        ("Extended Shotgun Mag II",   "Attachments", "Magazine", "Common",   "🔧", "All maps — Residential Containers"),
        ("Extended Shotgun Mag III",  "Attachments", "Magazine", "Uncommon", "🔧", "Electromagnetic Storm / Locked Gate / Night Raid — Residential Containers"),
        ("Lightweight Stock",         "Attachments", "Stock",    "Common",   "🔧", "All maps — Residential Containers"),
        ("Muzzle Brake II",           "Attachments", "Muzzle",   "Common",   "🔧", "All maps — Residential Containers"),
        ("Muzzle Brake III",          "Attachments", "Muzzle",   "Uncommon", "🔧", "Electromagnetic Storm / Locked Gate / Night Raid — Residential Containers"),
        ("Padded Stock",              "Attachments", "Stock",    "Common",   "🔧", "All maps — Residential Containers"),
        ("Shotgun Choke II",          "Attachments", "Muzzle",   "Common",   "🔧", "All maps — Residential Containers"),
        ("Shotgun Choke III",         "Attachments", "Muzzle",   "Uncommon", "🔧", "Electromagnetic Storm / Locked Gate / Night Raid — Residential Containers"),
        ("Shotgun Silencer",          "Attachments", "Muzzle",   "Common",   "🔧", "All maps — Residential Containers"),
        ("Silencer I",                "Attachments", "Muzzle",   "Common",   "🔧", "All maps — Residential Containers"),
        ("Silencer II",               "Attachments", "Muzzle",   "Uncommon", "🔧", "Electromagnetic Storm / Locked Gate / Night Raid — Residential Containers"),
        ("Stable Stock II",           "Attachments", "Stock",    "Common",   "🔧", "All maps — Residential Containers"),
        ("Stable Stock III",          "Attachments", "Stock",    "Uncommon", "🔧", "Electromagnetic Storm / Locked Gate / Night Raid — Residential Containers"),
        ("Vertical Grip II",          "Attachments", "Grip",     "Common",   "🔧", "All maps — Residential Containers"),
        ("Vertical Grip III",         "Attachments", "Grip",     "Uncommon", "🔧", "Electromagnetic Storm / Locked Gate / Night Raid — Residential Containers"),
        # ── Grenades & Mines ─────────────────────────────────────────────
        ("Blaze Grenade",             "Grenades & Mines", "Fire Grenade", "Common", "💥", "All maps — Industrial Containers"),
        ("Explosive Mine",            "Grenades & Mines", "Mine",         "Common", "💥", "All maps — Industrial Containers"),
        ("Fireworks Box",             "Grenades & Mines", "Special",      "Epic",   "🎆", "Event: Cold Snap (anywhere) OR Quest: Test Case"),
        ("Gas Mine",                  "Grenades & Mines", "Mine",         "Rare",   "☣️",  "Stella Montis only — any container"),
        ("Jolt Mine",                 "Grenades & Mines", "Mine",         "Common", "⚡", "All maps — Industrial Containers"),
        ("Lure Grenade",              "Grenades & Mines", "Grenade",      "Common", "💥", "All maps"),
        ("Pulse Mine",                "Grenades & Mines", "Mine",         "Common", "💥", "All maps"),
        ("Seeker Grenade",            "Grenades & Mines", "Grenade",      "Common", "💥", "All maps"),
        ("Smoke Grenade",             "Grenades & Mines", "Grenade",      "Common", "💥", "All maps"),
        ("Tagging Grenade",           "Grenades & Mines", "Grenade",      "Common", "💥", "All maps"),
        ("Trailblazer Grenade",       "Grenades & Mines", "Grenade",      "Common", "💥", "All maps"),
        ("Trigger Nade",              "Grenades & Mines", "Grenade",      "Common", "💥", "All maps"),
        # ── Tactical ─────────────────────────────────────────────────────
        ("Barricade Kit",             "Tactical", "Deployable", "Common", "🛡️", "All maps — Electrical Containers"),
        ("Defibrillator",             "Tactical", "Recovery",   "Common", "🛡️", "All maps — Medical Containers"),
        ("Remote Raider Flare",       "Tactical", "Utility",    "Common", "🛡️", "All maps"),
        ("Snap Hook",                 "Tactical", "Traversal",  "Common", "🛡️", "All maps"),
        ("Surge Coil",                "Tactical", "Deployable", "Epic",   "⚡", "Event: Close Scrutiny; Storm reports on Dam (Flashpoint 1.22.0)"),
        # ── Medical ──────────────────────────────────────────────────────
        ("Vita Shot",                 "Medical",  "Healing",    "Common", "💊", "All maps — Medical Containers"),
        ("Vita Spray",                "Medical",  "Healing",    "Common", "💊", "All maps — Medical Containers"),
        # ── Augments Mk.3 ────────────────────────────────────────────────
        ("Combat Mk. 3 (Aggressive)", "Augments", "Combat",  "Rare", "⚡", "Stella Montis / Blue Gate — Security or Medical Containers"),
        ("Combat Mk. 3 (Flanking)",   "Augments", "Combat",  "Rare", "⚡", "Stella Montis / Blue Gate — Security or Medical Containers"),
        ("Looting Mk. 3 (Safekeeper)","Augments", "Looting", "Rare", "⚡", "Stella Montis / Blue Gate — Security Containers"),
        ("Looting Mk. 3 (Survivor)",  "Augments", "Looting", "Rare", "⚡", "Stella Montis / Blue Gate — Security or Medical Containers"),
        ("Tactical Mk. 3 (Defensive)","Augments", "Tactical","Rare", "⚡", "Stella Montis / Blue Gate — Security Containers"),
        ("Tactical Mk. 3 (Healing)",  "Augments", "Tactical","Rare", "⚡", "Stella Montis / Blue Gate — Security Containers"),
        ("Tactical Mk. 3 (Revival)",  "Augments", "Tactical","Rare", "⚡", "Stella Montis / Blue Gate — Security Containers"),
        # ── Crafting Materials ───────────────────────────────────────────
        ("Complex Gun Parts",         "Crafting Materials", "Parts", "Uncommon", "⚙️", "All maps — Security Containers"),
        ("Heavy Gun Parts",           "Crafting Materials", "Parts", "Common",   "⚙️", "All maps — Raider Containers"),
        ("Light Gun Parts",           "Crafting Materials", "Parts", "Common",   "⚙️", "All maps — Raider Containers"),
        ("Medium Gun Parts",          "Crafting Materials", "Parts", "Common",   "⚙️", "All maps — Raider Containers"),
        # ── Light Sticks ─────────────────────────────────────────────────
        ("Blue Light Stick",          "Light Sticks", "Cosmetic", "Common", "🔵", "All maps — Residential Containers"),
        ("Green Light Stick",         "Light Sticks", "Cosmetic", "Common", "🟢", "All maps — Residential Containers"),
        ("Red Light Stick",           "Light Sticks", "Cosmetic", "Common", "🔴", "All maps — Residential Containers"),
        ("Yellow Light Stick",        "Light Sticks", "Cosmetic", "Common", "🟡", "All maps — Residential Containers"),
    ]
    inserted = 0
    for (name, cat, itype, rarity, icon, source) in blueprints:
        try:
            cur = db.execute(
                "INSERT INTO blueprints (name, category, item_type, rarity, icon, source, description) VALUES (?,?,?,?,?,?,?)",
                (name, cat, itype, rarity, icon, source, "")
            )
            new_id = cur.lastrowid
            db.execute("""
                INSERT OR IGNORE INTO character_blueprints (character_id, blueprint_id, learned, acquired_count)
                SELECT id, ?, 0, 0 FROM characters
            """, (new_id,))
            inserted += 1
        except sqlite3.IntegrityError:
            pass
    db.commit()
    return jsonify({"seeded": inserted, "total": len(blueprints)})


# ── Migration status endpoint ─────────────────────────────────────────────────

@app.route("/api/migrations", methods=["GET"])
def list_migrations():
    """Return the list of all known migrations and which have been applied."""
    db = get_db()
    try:
        applied = {
            row["version"]: row["applied_at"]
            for row in db.execute(
                "SELECT version, applied_at FROM schema_migrations ORDER BY version"
            ).fetchall()
        }
    except sqlite3.OperationalError:
        applied = {}

    result = []
    for version, name, _ in sorted(MIGRATIONS, key=lambda m: m[0]):
        result.append({
            "version":    version,
            "name":       name,
            "applied":    version in applied,
            "applied_at": applied.get(version),
        })
    return jsonify(result)


if __name__ == "__main__":
    run_migrations()
    app.run(host="0.0.0.0", port=5000, debug=False)
