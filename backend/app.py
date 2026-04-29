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


def _m005_backfill_blueprint_icons(db):
    """Set correct per-item icons for all seeded blueprints that still have the default 📋."""
    icon_map = [
        # Weapons
        ("Anvil",                      "🔫"),
        ("Aphelion",                   "🎯"),
        ("Bettina",                    "🔫"),
        ("Bobcat",                     "🔫"),
        ("Burletta",                   "🔫"),
        ("Canto",                      "🔫"),
        ("Deadline",                   "🎯"),
        ("Dolabra",                    "🔫"),
        ("Equalizer",                  "🔫"),
        ("Hullcracker",                "🔫"),
        ("Il Toro",                    "🔫"),
        ("Jupiter",                    "🔫"),
        ("Osprey",                     "🎯"),
        ("Showstopper",                "🔫"),
        ("Tempest I",                  "🔫"),
        ("Torrente",                   "🔫"),
        ("Venator",                    "🔫"),
        ("Vulcano",                    "🔫"),
        ("Wolfpack",                   "🔫"),
        # Attachments
        ("Angled Grip II",             "🔧"),
        ("Angled Grip III",            "🔧"),
        ("Compensator II",             "🔧"),
        ("Compensator III",            "🔧"),
        ("Extended Barrel",            "🔧"),
        ("Extended Light Mag II",      "🔧"),
        ("Extended Light Mag III",     "🔧"),
        ("Extended Medium Mag II",     "🔧"),
        ("Extended Medium Mag III",    "🔧"),
        ("Extended Shotgun Mag II",    "🔧"),
        ("Extended Shotgun Mag III",   "🔧"),
        ("Lightweight Stock",          "🔧"),
        ("Muzzle Brake II",            "🔧"),
        ("Muzzle Brake III",           "🔧"),
        ("Padded Stock",               "🔧"),
        ("Shotgun Choke II",           "🔧"),
        ("Shotgun Choke III",          "🔧"),
        ("Shotgun Silencer",           "🔧"),
        ("Silencer I",                 "🔧"),
        ("Silencer II",                "🔧"),
        ("Stable Stock II",            "🔧"),
        ("Stable Stock III",           "🔧"),
        ("Vertical Grip II",           "🔧"),
        ("Vertical Grip III",          "🔧"),
        # Grenades & Mines
        ("Blaze Grenade",              "💥"),
        ("Explosive Mine",             "💥"),
        ("Fireworks Box",              "🎆"),
        ("Gas Mine",                   "☣️"),
        ("Jolt Mine",                  "⚡"),
        ("Lure Grenade",               "💥"),
        ("Pulse Mine",                 "💥"),
        ("Seeker Grenade",             "💥"),
        ("Smoke Grenade",              "💥"),
        ("Tagging Grenade",            "💥"),
        ("Trailblazer Grenade",        "💥"),
        ("Trigger Nade",               "💥"),
        # Tactical
        ("Barricade Kit",              "🛡️"),
        ("Defibrillator",              "🛡️"),
        ("Remote Raider Flare",        "🛡️"),
        ("Snap Hook",                  "🛡️"),
        ("Surge Coil",                 "⚡"),
        # Medical
        ("Vita Shot",                  "💊"),
        ("Vita Spray",                 "💊"),
        # Augments
        ("Combat Mk. 3 (Aggressive)",  "⚡"),
        ("Combat Mk. 3 (Flanking)",    "⚡"),
        ("Looting Mk. 3 (Safekeeper)", "⚡"),
        ("Looting Mk. 3 (Survivor)",   "⚡"),
        ("Tactical Mk. 3 (Defensive)", "⚡"),
        ("Tactical Mk. 3 (Healing)",   "⚡"),
        ("Tactical Mk. 3 (Revival)",   "⚡"),
        # Crafting Materials
        ("Complex Gun Parts",          "⚙️"),
        ("Heavy Gun Parts",            "⚙️"),
        ("Light Gun Parts",            "⚙️"),
        ("Medium Gun Parts",           "⚙️"),
        # Light Sticks
        ("Blue Light Stick",           "🔵"),
        ("Green Light Stick",          "🟢"),
        ("Red Light Stick",            "🔴"),
        ("Yellow Light Stick",         "🟡"),
    ]
    for name, icon in icon_map:
        db.execute(
            "UPDATE blueprints SET icon=? WHERE name=? AND (icon IS NULL OR icon='' OR icon='📋')",
            (icon, name),
        )


def _m006_blueprints_add_icon_url(db):
    """Add icon_url column to blueprints for full-size wiki images."""
    try:
        db.execute("ALTER TABLE blueprints ADD COLUMN icon_url TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass  # column already present


def _m007_url_map():
    """Return the canonical (name, icon_url) pairs for all seeded blueprints."""
    BASE = "https://arcraiders.wiki/w/images"
    return [
        # ── Weapons ────────────────────────────────────────────────────────
        ("Anvil",                      f"{BASE}/0/00/Anvil-Level1.png"),
        ("Aphelion",                   f"{BASE}/8/88/Aphelion.png"),
        ("Bettina",                    f"{BASE}/a/ac/Bettina.png"),
        ("Bobcat",                     f"{BASE}/3/36/Bobcat-Level1.png"),
        ("Burletta",                   f"{BASE}/d/d4/Burletta-Level1.png"),
        ("Canto",                      f"{BASE}/8/83/Canto-Level1.png"),
        ("Deadline",                   f"{BASE}/c/c7/Deadline.png"),
        ("Dolabra",                    f"{BASE}/0/07/Dolabra-Level1.png"),
        ("Equalizer",                  f"{BASE}/9/96/Equalizer.png"),
        ("Hullcracker",                f"{BASE}/b/ba/Hullcracker-Level1.png"),
        ("Il Toro",                    f"{BASE}/5/50/Il_Toro-Level1.png"),
        ("Jupiter",                    f"{BASE}/6/68/Jupiter.png"),
        ("Osprey",                     f"{BASE}/a/ae/Osprey-Level1.png"),
        ("Showstopper",                f"{BASE}/1/18/Showstopper.png"),
        ("Tempest I",                  f"{BASE}/3/36/Bobcat-Level1.png"),   # no Tempest image on wiki yet; use placeholder
        ("Torrente",                   f"{BASE}/1/1e/Torrente-Level1.png"),
        ("Venator",                    f"{BASE}/b/b4/Venator-Level1.png"),
        ("Vulcano",                    f"{BASE}/d/da/Vulcano-Level1.png"),
        ("Wolfpack",                   f"{BASE}/2/24/Wolfpack.png"),
        # ── Attachments ────────────────────────────────────────────────────
        ("Angled Grip II",             f"{BASE}/2/2b/Angled_Grip_II.png"),
        ("Angled Grip III",            f"{BASE}/0/0f/Angled_Grip_III.png"),
        ("Compensator II",             f"{BASE}/0/0a/Compensator_II.png"),
        ("Compensator III",            f"{BASE}/a/af/Compensator_III.png"),
        ("Extended Barrel",            f"{BASE}/2/2f/Extended_Barrel.png"),
        ("Extended Light Mag II",      f"{BASE}/c/cf/Extended_Light_Mag_II.png"),
        ("Extended Light Mag III",     f"{BASE}/4/40/Extended_Light_Mag_III.png"),
        ("Extended Medium Mag II",     f"{BASE}/5/50/Extended_Medium_Mag_II.png"),
        ("Extended Medium Mag III",    f"{BASE}/a/a1/Extended_Medium_Mag_III.png"),
        ("Extended Shotgun Mag II",    f"{BASE}/4/4f/Extended_Shotgun_Mag_II.png"),
        ("Extended Shotgun Mag III",   f"{BASE}/7/77/Extended_Shotgun_Mag_III.png"),
        ("Lightweight Stock",          f"{BASE}/c/cb/Lightweight_Stock.png"),
        ("Muzzle Brake II",            f"{BASE}/2/23/Muzzle_Brake_II.png"),
        ("Muzzle Brake III",           f"{BASE}/a/a2/Muzzle_Brake_III.png"),
        ("Padded Stock",               f"{BASE}/4/4b/Padded_Stock.png"),
        ("Shotgun Choke II",           f"{BASE}/6/63/Shotgun_Choke_II.png"),
        ("Shotgun Choke III",          f"{BASE}/3/36/Shotgun_Choke_III.png"),
        ("Shotgun Silencer",           f"{BASE}/4/4d/Shotgun_Silencer.png"),
        ("Silencer I",                 f"{BASE}/f/f7/Silencer_I.png"),
        ("Silencer II",                f"{BASE}/c/c0/Silencer_II.png"),
        ("Stable Stock II",            f"{BASE}/b/b4/Stable_Stock_II.png"),
        ("Stable Stock III",           f"{BASE}/e/eb/Stable_Stock_III.png"),
        ("Vertical Grip II",           f"{BASE}/3/3c/Vertical_Grip_II.png"),
        ("Vertical Grip III",          f"{BASE}/2/20/Vertical_Grip_III.png"),
        # ── Grenades & Mines ───────────────────────────────────────────────
        ("Blaze Grenade",              f"{BASE}/2/24/Blaze_Grenade.png"),
        ("Explosive Mine",             f"{BASE}/2/22/Explosive_Mine.png"),
        ("Fireworks Box",              f"{BASE}/0/0f/Fireworks_Box.png"),
        ("Gas Mine",                   f"{BASE}/c/ce/Gas_Mine.png"),
        ("Jolt Mine",                  f"{BASE}/5/5a/Jolt_Mine.png"),
        ("Lure Grenade",               f"{BASE}/7/77/Lure_Grenade.png"),
        ("Pulse Mine",                 f"{BASE}/a/af/Pulse_Mine.png"),
        ("Seeker Grenade",             f"{BASE}/3/35/Seeker_Grenade.png"),
        ("Smoke Grenade",              f"{BASE}/d/d5/Smoke_Grenade.png"),
        ("Tagging Grenade",            f"{BASE}/e/e5/Tagging_Grenade.png"),
        ("Trailblazer Grenade",        f"{BASE}/8/89/Trailblazer.png"),
        ("Trigger Nade",               f"{BASE}/0/09/Trigger_Nade.png"),
        # ── Tactical ───────────────────────────────────────────────────────
        ("Barricade Kit",              f"{BASE}/c/cb/Barricade_Kit.png"),
        ("Defibrillator",              f"{BASE}/5/5f/Defibrillator.png"),
        ("Remote Raider Flare",        f"{BASE}/f/ff/Remote_Raider_Flare.png"),
        ("Snap Hook",                  f"{BASE}/5/56/Snap_Hook.png"),
        ("Surge Coil",                 f"{BASE}/5/5b/Surge_Coil.png"),
        # ── Medical ────────────────────────────────────────────────────────
        ("Vita Shot",                  f"{BASE}/7/7d/Vita_Shot.png"),
        ("Vita Spray",                 f"{BASE}/1/1d/Vita_Spray.png"),
        # ── Augments ───────────────────────────────────────────────────────
        ("Combat Mk. 3 (Aggressive)",  f"{BASE}/a/a4/Combat_Mk._3_%28Aggressive%29.png"),
        ("Combat Mk. 3 (Flanking)",    f"{BASE}/7/73/Combat_Mk._3_%28Flanking%29.png"),
        ("Looting Mk. 3 (Safekeeper)", f"{BASE}/c/c6/Looting_Mk._3_%28Safekeeper%29.png"),
        ("Looting Mk. 3 (Survivor)",   f"{BASE}/7/74/Looting_Mk._3_%28Survivor%29.png"),
        ("Tactical Mk. 3 (Defensive)", f"{BASE}/a/a9/Tactical_Mk._3_%28Defensive%29.png"),
        ("Tactical Mk. 3 (Healing)",   f"{BASE}/1/12/Tactical_Mk._3_%28Healing%29.png"),
        ("Tactical Mk. 3 (Revival)",   f"{BASE}/e/e0/Tactical_Mk._3_%28Revival%29.png"),
        # ── Crafting Materials ─────────────────────────────────────────────
        ("Complex Gun Parts",          f"{BASE}/3/3d/Complex_Gun_Parts.png"),
        ("Heavy Gun Parts",            f"{BASE}/3/33/Heavy_Gun_Parts.png"),
        ("Light Gun Parts",            f"{BASE}/c/c9/Light_Gun_Parts.png"),
        ("Medium Gun Parts",           f"{BASE}/9/9a/Medium_Gun_Parts.png"),
        # ── Light Sticks ───────────────────────────────────────────────────
        ("Blue Light Stick",           f"{BASE}/c/cc/Blue_Light_Stick.png"),
        ("Green Light Stick",          f"{BASE}/2/27/Green_Light_Stick.png"),
        ("Red Light Stick",            f"{BASE}/9/93/Red_Light_Stick.png"),
        ("Yellow Light Stick",         f"{BASE}/1/1f/Yellow_Light_Stick.png"),
    ]


def _m007_backfill_blueprint_icon_urls(db):
    """Populate icon_url from arcraiders.wiki for all seeded blueprints."""
    for name, url in _m007_url_map():
        db.execute(
            "UPDATE blueprints SET icon_url=? WHERE name=? AND (icon_url IS NULL OR icon_url='')",
            (url, name),
        )


def _m008_local_map():
    """Return (name, local_icon_url) pairs using the bundled static images."""
    P = "/images/blueprints"
    return [
        # ── Weapons ────────────────────────────────────────────────────────
        ("Anvil",                      f"{P}/Anvil.png"),
        ("Aphelion",                   f"{P}/Aphelion.png"),
        ("Bettina",                    f"{P}/Bettina.png"),
        ("Bobcat",                     f"{P}/Bobcat.png"),
        ("Burletta",                   f"{P}/Burletta.png"),
        ("Canto",                      f"{P}/Canto.png"),
        ("Deadline",                   f"{P}/Deadline.png"),
        ("Dolabra",                    f"{P}/Dolabra.png"),
        ("Equalizer",                  f"{P}/Equalizer.png"),
        ("Hullcracker",                f"{P}/Hullcracker.png"),
        ("Il Toro",                    f"{P}/Il_Toro.png"),
        ("Jupiter",                    f"{P}/Jupiter.png"),
        ("Osprey",                     f"{P}/Osprey.png"),
        ("Showstopper",                f"{P}/Showstopper.png"),
        ("Tempest I",                  f"{P}/Tempest_I.png"),
        ("Torrente",                   f"{P}/Torrente.png"),
        ("Venator",                    f"{P}/Venator.png"),
        ("Vulcano",                    f"{P}/Vulcano.png"),
        ("Wolfpack",                   f"{P}/Wolfpack.png"),
        # ── Attachments ────────────────────────────────────────────────────
        ("Angled Grip II",             f"{P}/Angled_Grip_II.png"),
        ("Angled Grip III",            f"{P}/Angled_Grip_III.png"),
        ("Compensator II",             f"{P}/Compensator_II.png"),
        ("Compensator III",            f"{P}/Compensator_III.png"),
        ("Extended Barrel",            f"{P}/Extended_Barrel.png"),
        ("Extended Light Mag II",      f"{P}/Extended_Light_Mag_II.png"),
        ("Extended Light Mag III",     f"{P}/Extended_Light_Mag_III.png"),
        ("Extended Medium Mag II",     f"{P}/Extended_Medium_Mag_II.png"),
        ("Extended Medium Mag III",    f"{P}/Extended_Medium_Mag_III.png"),
        ("Extended Shotgun Mag II",    f"{P}/Extended_Shotgun_Mag_II.png"),
        ("Extended Shotgun Mag III",   f"{P}/Extended_Shotgun_Mag_III.png"),
        ("Lightweight Stock",          f"{P}/Lightweight_Stock.png"),
        ("Muzzle Brake II",            f"{P}/Muzzle_Brake_II.png"),
        ("Muzzle Brake III",           f"{P}/Muzzle_Brake_III.png"),
        ("Padded Stock",               f"{P}/Padded_Stock.png"),
        ("Shotgun Choke II",           f"{P}/Shotgun_Choke_II.png"),
        ("Shotgun Choke III",          f"{P}/Shotgun_Choke_III.png"),
        ("Shotgun Silencer",           f"{P}/Shotgun_Silencer.png"),
        ("Silencer I",                 f"{P}/Silencer_I.png"),
        ("Silencer II",                f"{P}/Silencer_II.png"),
        ("Stable Stock II",            f"{P}/Stable_Stock_II.png"),
        ("Stable Stock III",           f"{P}/Stable_Stock_III.png"),
        ("Vertical Grip II",           f"{P}/Vertical_Grip_II.png"),
        ("Vertical Grip III",          f"{P}/Vertical_Grip_III.png"),
        # ── Grenades & Mines ───────────────────────────────────────────────
        ("Blaze Grenade",              f"{P}/Blaze_Grenade.png"),
        ("Explosive Mine",             f"{P}/Explosive_Mine.png"),
        ("Fireworks Box",              f"{P}/Fireworks_Box.png"),
        ("Gas Mine",                   f"{P}/Gas_Mine.png"),
        ("Jolt Mine",                  f"{P}/Jolt_Mine.png"),
        ("Lure Grenade",               f"{P}/Lure_Grenade.png"),
        ("Pulse Mine",                 f"{P}/Pulse_Mine.png"),
        ("Seeker Grenade",             f"{P}/Seeker_Grenade.png"),
        ("Smoke Grenade",              f"{P}/Smoke_Grenade.png"),
        ("Tagging Grenade",            f"{P}/Tagging_Grenade.png"),
        ("Trailblazer Grenade",        f"{P}/Trailblazer_Grenade.png"),
        ("Trigger Nade",               f"{P}/Trigger_Nade.png"),
        # ── Tactical ───────────────────────────────────────────────────────
        ("Barricade Kit",              f"{P}/Barricade_Kit.png"),
        ("Defibrillator",              f"{P}/Defibrillator.png"),
        ("Remote Raider Flare",        f"{P}/Remote_Raider_Flare.png"),
        ("Snap Hook",                  f"{P}/Snap_Hook.png"),
        ("Surge Coil",                 f"{P}/Surge_Coil.png"),
        # ── Medical ────────────────────────────────────────────────────────
        ("Vita Shot",                  f"{P}/Vita_Shot.png"),
        ("Vita Spray",                 f"{P}/Vita_Spray.png"),
        # ── Augments ───────────────────────────────────────────────────────
        ("Combat Mk. 3 (Aggressive)",  f"{P}/Combat_Mk3_Aggressive.png"),
        ("Combat Mk. 3 (Flanking)",    f"{P}/Combat_Mk3_Flanking.png"),
        ("Looting Mk. 3 (Safekeeper)", f"{P}/Looting_Mk3_Safekeeper.png"),
        ("Looting Mk. 3 (Survivor)",   f"{P}/Looting_Mk3_Survivor.png"),
        ("Tactical Mk. 3 (Defensive)", f"{P}/Tactical_Mk3_Defensive.png"),
        ("Tactical Mk. 3 (Healing)",   f"{P}/Tactical_Mk3_Healing.png"),
        ("Tactical Mk. 3 (Revival)",   f"{P}/Tactical_Mk3_Revival.png"),
        # ── Crafting Materials ─────────────────────────────────────────────
        ("Complex Gun Parts",          f"{P}/Complex_Gun_Parts.png"),
        ("Heavy Gun Parts",            f"{P}/Heavy_Gun_Parts.png"),
        ("Light Gun Parts",            f"{P}/Light_Gun_Parts.png"),
        ("Medium Gun Parts",           f"{P}/Medium_Gun_Parts.png"),
        # ── Light Sticks ───────────────────────────────────────────────────
        ("Blue Light Stick",           f"{P}/Blue_Light_Stick.png"),
        ("Green Light Stick",          f"{P}/Green_Light_Stick.png"),
        ("Red Light Stick",            f"{P}/Red_Light_Stick.png"),
        ("Yellow Light Stick",         f"{P}/Yellow_Light_Stick.png"),
    ]


def _m008_switch_icon_urls_to_local(db):
    """Replace remote wiki URLs with local static-asset paths for all seeded blueprints."""
    for name, local_url in _m008_local_map():
        db.execute("UPDATE blueprints SET icon_url=? WHERE name=?", (local_url, name))


def _m009_clear_blueprint_sources(db):
    """Remove all source/where-found text from blueprints — no longer shown in the UI."""
    db.execute("UPDATE blueprints SET source=''")


def _m011_correct_blueprint_data(db):
    """Fix categories and rarities to match in-game values."""
    corrections = [
        # (name, category, rarity)
        ("Anvil",                      "Weapons",   "Epic"),
        ("Aphelion",                   "Weapons",   "Legendary"),
        ("Bettina",                    "Weapons",   "Epic"),
        ("Bobcat",                     "Weapons",   "Epic"),
        ("Burletta",                   "Weapons",   "Uncommon"),
        ("Canto",                      "Weapons",   "Epic"),
        ("Dolabra",                    "Weapons",   "Legendary"),
        ("Equalizer",                  "Weapons",   "Legendary"),
        ("Hullcracker",                "Weapons",   "Epic"),
        ("Il Toro",                    "Weapons",   "Epic"),
        ("Jupiter",                    "Weapons",   "Legendary"),
        ("Osprey",                     "Weapons",   "Epic"),
        ("Tempest I",                  "Weapons",   "Epic"),
        ("Torrente",                   "Weapons",   "Epic"),
        ("Venator",                    "Weapons",   "Epic"),
        ("Vulcano",                    "Weapons",   "Epic"),
        ("Angled Grip II",             "Mods",      "Epic"),
        ("Angled Grip III",            "Mods",      "Epic"),
        ("Compensator II",             "Mods",      "Epic"),
        ("Compensator III",            "Mods",      "Epic"),
        ("Extended Barrel",            "Mods",      "Epic"),
        ("Extended Light Mag II",      "Mods",      "Epic"),
        ("Extended Light Mag III",     "Mods",      "Epic"),
        ("Extended Medium Mag II",     "Mods",      "Epic"),
        ("Extended Medium Mag III",    "Mods",      "Epic"),
        ("Extended Shotgun Mag II",    "Mods",      "Epic"),
        ("Extended Shotgun Mag III",   "Mods",      "Epic"),
        ("Lightweight Stock",          "Mods",      "Epic"),
        ("Muzzle Brake II",            "Mods",      "Epic"),
        ("Muzzle Brake III",           "Mods",      "Epic"),
        ("Padded Stock",               "Mods",      "Epic"),
        ("Shotgun Choke II",           "Mods",      "Epic"),
        ("Shotgun Choke III",          "Mods",      "Epic"),
        ("Shotgun Silencer",           "Mods",      "Epic"),
        ("Silencer I",                 "Mods",      "Epic"),
        ("Silencer II",                "Mods",      "Epic"),
        ("Stable Stock II",            "Mods",      "Epic"),
        ("Stable Stock III",           "Mods",      "Epic"),
        ("Vertical Grip II",           "Mods",      "Epic"),
        ("Vertical Grip III",          "Mods",      "Epic"),
        ("Blaze Grenade",              "Grenades",  "Epic"),
        ("Lure Grenade",               "Grenades",  "Epic"),
        ("Seeker Grenade",             "Grenades",  "Epic"),
        ("Showstopper",                "Grenades",  "Epic"),
        ("Smoke Grenade",              "Grenades",  "Epic"),
        ("Tagging Grenade",            "Grenades",  "Epic"),
        ("Trailblazer Grenade",        "Grenades",  "Epic"),
        ("Trigger Nade",               "Grenades",  "Epic"),
        ("Wolfpack",                   "Grenades",  "Epic"),
        ("Deadline",                   "Mines",     "Epic"),
        ("Explosive Mine",             "Mines",     "Epic"),
        ("Gas Mine",                   "Mines",     "Epic"),
        ("Jolt Mine",                  "Mines",     "Epic"),
        ("Pulse Mine",                 "Mines",     "Epic"),
        ("Barricade Kit",              "Quick Use", "Epic"),
        ("Blue Light Stick",           "Quick Use", "Epic"),
        ("Defibrillator",              "Quick Use", "Epic"),
        ("Fireworks Box",              "Quick Use", "Epic"),
        ("Green Light Stick",          "Quick Use", "Epic"),
        ("Red Light Stick",            "Quick Use", "Epic"),
        ("Remote Raider Flare",        "Quick Use", "Epic"),
        ("Snap Hook",                  "Quick Use", "Epic"),
        ("Surge Coil",                 "Quick Use", "Epic"),
        ("Vita Shot",                  "Quick Use", "Epic"),
        ("Vita Spray",                 "Quick Use", "Epic"),
        ("Yellow Light Stick",         "Quick Use", "Epic"),
        ("Combat Mk. 3 (Aggressive)",  "Augments",  "Epic"),
        ("Combat Mk. 3 (Flanking)",    "Augments",  "Epic"),
        ("Looting Mk. 3 (Safekeeper)", "Augments",  "Epic"),
        ("Looting Mk. 3 (Survivor)",   "Augments",  "Epic"),
        ("Tactical Mk. 3 (Defensive)", "Augments",  "Epic"),
        ("Tactical Mk. 3 (Healing)",   "Augments",  "Epic"),
        ("Tactical Mk. 3 (Revival)",   "Augments",  "Epic"),
        ("Complex Gun Parts",          "Materials", "Epic"),
        ("Heavy Gun Parts",            "Materials", "Epic"),
        ("Light Gun Parts",            "Materials", "Epic"),
        ("Medium Gun Parts",           "Materials", "Epic"),
    ]
    for name, category, rarity in corrections:
        db.execute(
            "UPDATE blueprints SET category=?, rarity=? WHERE name=?",
            (category, rarity, name),
        )


def _m010_drop_blueprint_source(db):
    """Drop the source column from blueprints using rename-recreate (SQLite safe)."""
    db.executescript("""
        CREATE TABLE IF NOT EXISTS blueprints_new (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL UNIQUE,
            category    TEXT NOT NULL DEFAULT 'Uncategorized',
            rarity      TEXT DEFAULT 'Common',
            icon        TEXT DEFAULT '📋',
            icon_url    TEXT DEFAULT '',
            description TEXT,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        INSERT INTO blueprints_new
            (id, name, category, rarity, icon, icon_url, description, created_at)
        SELECT  id, name, category, rarity, icon, icon_url, description, created_at
        FROM blueprints;

        DROP TABLE blueprints;

        ALTER TABLE blueprints_new RENAME TO blueprints;
    """)


def _m012_drop_blueprint_item_type(db):
    """Drop the item_type column — category alone is sufficient."""
    db.executescript("""
        CREATE TABLE IF NOT EXISTS blueprints_new (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL UNIQUE,
            category    TEXT NOT NULL DEFAULT 'Uncategorized',
            rarity      TEXT DEFAULT 'Common',
            icon        TEXT DEFAULT '📋',
            icon_url    TEXT DEFAULT '',
            description TEXT,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        INSERT INTO blueprints_new
            (id, name, category, rarity, icon, icon_url, description, created_at)
        SELECT  id, name, category, rarity, icon, icon_url, description, created_at
        FROM blueprints;

        DROP TABLE blueprints;

        ALTER TABLE blueprints_new RENAME TO blueprints;
    """)


# Ordered list of all migrations.  Append new entries here as the schema evolves.
MIGRATIONS = [
    (1,  "initial_schema",                       _m001_initial_schema),
    (2,  "blueprints_icon_source",               _m002_blueprints_icon_source),
    (3,  "character_blueprints_learned_acquired", _m003_character_blueprints_learned_acquired),
    (4,  "migrate_legacy_status_values",          _m004_migrate_legacy_status_values),
    (5,  "backfill_blueprint_icons",              _m005_backfill_blueprint_icons),
    (6,  "blueprints_add_icon_url",               _m006_blueprints_add_icon_url),
    (7,  "backfill_blueprint_icon_urls",          _m007_backfill_blueprint_icon_urls),
    (8,  "switch_icon_urls_to_local",             _m008_switch_icon_urls_to_local),
    (9,  "clear_blueprint_sources",               _m009_clear_blueprint_sources),
    (10, "drop_blueprint_source",                 _m010_drop_blueprint_source),
    (11, "correct_blueprint_data",                _m011_correct_blueprint_data),
    (12, "drop_blueprint_item_type",              _m012_drop_blueprint_item_type),
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
            "INSERT INTO blueprints (name, category, rarity, icon, description) VALUES (?,?,?,?,?)",
            (name, data.get("category","Uncategorized"),
             data.get("rarity","Common"), data.get("icon","📋"),
             data.get("description","")),
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
        "UPDATE blueprints SET name=?, category=?, rarity=?, icon=?, description=? WHERE id=?",
        ((data.get("name") or row["name"]).strip(), data.get("category", row["category"]),
         data.get("rarity", row["rarity"]),
         data.get("icon", row["icon"]), data.get("description", row["description"]), bid),
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
        SELECT b.id, b.name, b.category, b.rarity, b.icon, b.icon_url,
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
    bps = db.execute("SELECT id, name, category, rarity, icon, icon_url FROM blueprints ORDER BY category, name").fetchall()
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
            "icon": bp["icon"], "icon_url": bp["icon_url"],
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
        SELECT b.id, b.name, b.category, b.rarity, b.icon, b.icon_url,
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
               b.id AS bp_id, b.name AS bp_name, b.category, b.rarity, b.icon, b.icon_url,
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
    # (name, category, rarity, icon)
    # Categories: Weapons | Mods | Grenades | Mines | Quick Use | Augments | Materials
    blueprints = [
        # ── Weapons ──────────────────────────────────────────────────────
        ("Anvil",                     "Weapons",   "Epic",      "🔫"),
        ("Aphelion",                  "Weapons",   "Legendary", "🎯"),
        ("Bettina",                   "Weapons",   "Epic",      "🔫"),
        ("Bobcat",                    "Weapons",   "Epic",      "🔫"),
        ("Burletta",                  "Weapons",   "Uncommon",  "🔫"),
        ("Canto",                     "Weapons",   "Epic",      "🔫"),
        ("Dolabra",                   "Weapons",   "Legendary", "🔫"),
        ("Equalizer",                 "Weapons",   "Legendary", "🔫"),
        ("Hullcracker",               "Weapons",   "Epic",      "🔫"),
        ("Il Toro",                   "Weapons",   "Epic",      "🔫"),
        ("Jupiter",                   "Weapons",   "Legendary", "🔫"),
        ("Osprey",                    "Weapons",   "Epic",      "🎯"),
        ("Tempest I",                 "Weapons",   "Epic",      "🔫"),
        ("Torrente",                  "Weapons",   "Epic",      "🔫"),
        ("Venator",                   "Weapons",   "Epic",      "🔫"),
        ("Vulcano",                   "Weapons",   "Epic",      "🔫"),
        # ── Mods ─────────────────────────────────────────────────────────
        ("Angled Grip II",            "Mods", "Epic", "🔧"),
        ("Angled Grip III",           "Mods", "Epic", "🔧"),
        ("Compensator II",            "Mods", "Epic", "🔧"),
        ("Compensator III",           "Mods", "Epic", "🔧"),
        ("Extended Barrel",           "Mods", "Epic", "🔧"),
        ("Extended Light Mag II",     "Mods", "Epic", "🔧"),
        ("Extended Light Mag III",    "Mods", "Epic", "🔧"),
        ("Extended Medium Mag II",    "Mods", "Epic", "🔧"),
        ("Extended Medium Mag III",   "Mods", "Epic", "🔧"),
        ("Extended Shotgun Mag II",   "Mods", "Epic", "🔧"),
        ("Extended Shotgun Mag III",  "Mods", "Epic", "🔧"),
        ("Lightweight Stock",         "Mods", "Epic", "🔧"),
        ("Muzzle Brake II",           "Mods", "Epic", "🔧"),
        ("Muzzle Brake III",          "Mods", "Epic", "🔧"),
        ("Padded Stock",              "Mods", "Epic", "🔧"),
        ("Shotgun Choke II",          "Mods", "Epic", "🔧"),
        ("Shotgun Choke III",         "Mods", "Epic", "🔧"),
        ("Shotgun Silencer",          "Mods", "Epic", "🔧"),
        ("Silencer I",                "Mods", "Epic", "🔧"),
        ("Silencer II",               "Mods", "Epic", "🔧"),
        ("Stable Stock II",           "Mods", "Epic", "🔧"),
        ("Stable Stock III",          "Mods", "Epic", "🔧"),
        ("Vertical Grip II",          "Mods", "Epic", "🔧"),
        ("Vertical Grip III",         "Mods", "Epic", "🔧"),
        # ── Grenades ─────────────────────────────────────────────────────
        ("Blaze Grenade",        "Grenades", "Epic", "💥"),
        ("Lure Grenade",         "Grenades", "Epic", "💥"),
        ("Seeker Grenade",       "Grenades", "Epic", "💥"),
        ("Showstopper",          "Grenades", "Epic", "💥"),
        ("Smoke Grenade",        "Grenades", "Epic", "💥"),
        ("Tagging Grenade",      "Grenades", "Epic", "💥"),
        ("Trailblazer Grenade",  "Grenades", "Epic", "💥"),
        ("Trigger Nade",         "Grenades", "Epic", "💥"),
        ("Wolfpack",             "Grenades", "Epic", "💥"),
        # ── Mines ────────────────────────────────────────────────────────
        ("Deadline",             "Mines", "Epic", "💥"),
        ("Explosive Mine",       "Mines", "Epic", "💥"),
        ("Gas Mine",             "Mines", "Epic", "☣️"),
        ("Jolt Mine",            "Mines", "Epic", "⚡"),
        ("Pulse Mine",           "Mines", "Epic", "💥"),
        # ── Quick Use ────────────────────────────────────────────────────
        ("Barricade Kit",        "Quick Use", "Epic", "🛡️"),
        ("Blue Light Stick",     "Quick Use", "Epic", "🔵"),
        ("Crash Mat",            "Quick Use", "Epic", "🛡️"),
        ("Defibrillator",        "Quick Use", "Epic", "🛡️"),
        ("Fireworks Box",        "Quick Use", "Epic", "🎆"),
        ("Green Light Stick",    "Quick Use", "Epic", "🟢"),
        ("Powered Descender",    "Quick Use", "Epic", "🪂"),
        ("Red Light Stick",      "Quick Use", "Epic", "🔴"),
        ("Remote Raider Flare",  "Quick Use", "Epic", "🛡️"),
        ("Snap Hook",            "Quick Use", "Epic", "🛡️"),
        ("Surge Coil",           "Quick Use", "Epic", "⚡"),
        ("Vita Shot",            "Quick Use", "Epic", "💊"),
        ("Vita Spray",           "Quick Use", "Epic", "💊"),
        ("White Flag",           "Quick Use", "Epic", "🏳️"),
        ("Yellow Light Stick",   "Quick Use", "Epic", "🟡"),
        # ── Augments ─────────────────────────────────────────────────────
        ("Combat Mk. 3 (Aggressive)",  "Augments", "Epic", "⚡"),
        ("Combat Mk. 3 (Flanking)",    "Augments", "Epic", "⚡"),
        ("Looting Mk. 3 (Safekeeper)", "Augments", "Epic", "⚡"),
        ("Looting Mk. 3 (Survivor)",   "Augments", "Epic", "⚡"),
        ("Tactical Mk. 3 (Defensive)", "Augments", "Epic", "⚡"),
        ("Tactical Mk. 3 (Healing)",   "Augments", "Epic", "⚡"),
        ("Tactical Mk. 3 (Revival)",   "Augments", "Epic", "⚡"),
        ("Tactical Mk. 3 (Smoke)",     "Augments", "Epic", "⚡"),
        # ── Materials ────────────────────────────────────────────────────
        ("Complex Gun Parts",    "Materials", "Epic", "⚙️"),
        ("Heavy Gun Parts",      "Materials", "Epic", "⚙️"),
        ("Light Gun Parts",      "Materials", "Epic", "⚙️"),
        ("Medium Gun Parts",     "Materials", "Epic", "⚙️"),
    ]
    # Build icon_url lookup from the local-path map so seed and migration stay in sync
    icon_url_lookup = {name: url for name, url in _m008_local_map()}

    inserted = 0
    updated = 0
    for (name, cat, rarity, icon) in blueprints:
        icon_url = icon_url_lookup.get(name, "")
        existing = db.execute("SELECT id FROM blueprints WHERE name=?", (name,)).fetchone()
        if existing:
            db.execute(
                "UPDATE blueprints SET category=?, rarity=?, icon=?, icon_url=? WHERE id=?",
                (cat, rarity, icon, icon_url, existing["id"]),
            )
            updated += 1
            new_id = existing["id"]
        else:
            cur = db.execute(
                "INSERT INTO blueprints (name, category, rarity, icon, description, icon_url) VALUES (?,?,?,?,'',?)",
                (name, cat, rarity, icon, icon_url),
            )
            new_id = cur.lastrowid
            inserted += 1
        db.execute("""
            INSERT OR IGNORE INTO character_blueprints (character_id, blueprint_id, learned, acquired_count)
            SELECT id, ?, 0, 0 FROM characters
        """, (new_id,))
    db.commit()
    return jsonify({"inserted": inserted, "updated": updated, "total": len(blueprints)})


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
