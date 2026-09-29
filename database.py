import sqlite3
import os
import sys
import json
import secrets
import time

if getattr(sys, "frozen", False):
    appdata = os.getenv("APPDATA")
    DATA_DIR = os.path.join(appdata, "MyGameList") if appdata else os.path.dirname(sys.executable)
else:
    DATA_DIR = os.path.dirname(os.path.abspath(__file__))

os.makedirs(DATA_DIR, exist_ok=True)

DB_NAME = os.path.join(DATA_DIR, "games.db")


def get_connection():
    """Veritabanına bağlantı açar. Foreign key desteğini aktif eder."""
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """games.db dosyasını ve tabloları oluşturur (yoksa)."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS deleted_game_entries (
            token TEXT PRIMARY KEY,
            snapshot TEXT NOT NULL,
            expires_at REAL NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            release_date TEXT,
            metacritic INTEGER,
            genre TEXT,
            platforms TEXT,
            developer TEXT,
            publisher TEXT,
            description TEXT,
            cover_url TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS my_games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'Want to Play',
            my_rating REAL,
            note TEXT,
            favorite INTEGER NOT NULL DEFAULT 0,
            played_date TEXT,
            FOREIGN KEY (game_id) REFERENCES games (id)
        )
    """)
    # Eski veritabanlarına yeni kolonu güvenli şekilde ekler (zaten varsa hata vermez)
    try:
        cursor.execute("ALTER TABLE games ADD COLUMN local_image_path TEXT")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


def get_my_games(filter_by="all", sort_by="recent"):
    """my_games ve games tablolarını birleştirip, filtre ve sıralamaya göre listeyi döner."""
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT
            games.id AS game_id,
            games.name,
            games.cover_url,
            games.local_image_path,
            games.metacritic,
            my_games.id AS my_game_id,
            my_games.status,
            my_games.my_rating,
            my_games.note,
            my_games.favorite
        FROM my_games
        JOIN games ON my_games.game_id = games.id
    """

    params = []

    status_map = {
        "want_to_play": "Want to Play",
        "playing": "Playing",
        "played": "Played",
        "dropped": "Dropped"
    }

    if filter_by == "favorites":
        query += " WHERE my_games.favorite = 1"
    elif filter_by in status_map:
        query += " WHERE my_games.status = ?"
        params.append(status_map[filter_by])

    sort_map = {
        "played_date_asc": "NULLIF(my_games.played_date, '') IS NULL, my_games.played_date ASC, my_games.id DESC",
        "played_date_desc": "NULLIF(my_games.played_date, '') IS NULL, my_games.played_date DESC, my_games.id DESC",
        "name_asc": "games.name ASC",
        "name_desc": "games.name DESC",
        "metacritic_desc": "games.metacritic DESC",
        "metacritic_asc": "games.metacritic ASC",
        "rating_desc": "my_games.my_rating DESC",
        "rating_asc": "my_games.my_rating ASC",
        "recent": "my_games.id DESC",
        "oldest": "my_games.id ASC"

    }

    order_clause = sort_map.get(sort_by, "my_games.id DESC")
    query += f" ORDER BY {order_clause}"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_my_games_stats():
    """Dashboard için özet istatistikleri hesaplar."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS count FROM my_games WHERE favorite = 1")
    favorites = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) AS count FROM my_games WHERE status = 'Played'")
    played = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) AS count FROM my_games WHERE status = 'Want to Play'")
    want_to_play = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) AS count FROM my_games WHERE status = 'Playing'")
    playing = cursor.fetchone()["count"]

    cursor.execute("SELECT AVG(my_rating) AS avg_rating FROM my_games WHERE my_rating IS NOT NULL")
    avg_rating = cursor.fetchone()["avg_rating"]

    conn.close()

    return {
        "favorites": favorites,
        "played": played,
        "want_to_play": want_to_play,
        "playing": playing,
        "avg_rating": round(avg_rating, 1) if avg_rating else None
    }


def delete_with_undo(game_id):
    """Keep the entire library entry for five minutes, including its original ID."""
    conn = get_connection()
    try:
        with conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("DELETE FROM deleted_game_entries WHERE expires_at < ?", (time.time(),))
            entry = conn.execute("SELECT * FROM my_games WHERE game_id = ?", (game_id,)).fetchone()
            if entry is None:
                return None
            token = secrets.token_urlsafe(24)
            conn.execute("INSERT INTO deleted_game_entries VALUES (?, ?, ?)",
                         (token, json.dumps(dict(entry)), time.time() + 300))
            conn.execute("DELETE FROM my_games WHERE game_id = ?", (game_id,))
            return token
    finally:
        conn.close()


def undo_delete(token):
    """Restore without overwriting a game that has already been re-added."""
    conn = get_connection()
    try:
        with conn:
            conn.execute("BEGIN IMMEDIATE")
            saved = conn.execute("SELECT * FROM deleted_game_entries WHERE token = ?", (token,)).fetchone()
            if saved is None or saved["expires_at"] < time.time():
                return False
            entry = json.loads(saved["snapshot"])
            columns = ("id", "game_id", "status", "my_rating", "note", "favorite", "played_date")
            cursor = conn.execute(
                "INSERT OR IGNORE INTO my_games (id, game_id, status, my_rating, note, favorite, played_date) VALUES (?, ?, ?, ?, ?, ?, ?)",
                tuple(entry[column] for column in columns),
            )
            conn.execute("DELETE FROM deleted_game_entries WHERE token = ?", (token,))
            return cursor.rowcount == 1
    finally:
        conn.close()


def delete_from_my_list(game_id):
    """Oyunu my_games tablosundan siler (games tablosuna dokunmaz)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM my_games WHERE game_id = ?", (game_id,))
    conn.commit()
    conn.close()


def get_my_game_by_id(game_id):
    """Tek bir oyunun my_games + games bilgisini birlikte döner (edit formu için)."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            games.id AS game_id,
            games.name,
            games.cover_url,
            my_games.status,
            my_games.my_rating,
            my_games.note,
            my_games.favorite,
            my_games.played_date
        FROM my_games
        JOIN games ON my_games.game_id = games.id
        WHERE games.id = ?
    """, (game_id,))

    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def update_my_game(game_id, status, my_rating, note, favorite, played_date):
    """my_games tablosundaki status, rating, not, favori ve tarihi günceller."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE my_games
        SET status = ?, my_rating = ?, note = ?, favorite = ?, played_date = ?
        WHERE game_id = ?
    """, (status, my_rating, note, favorite, played_date, game_id))

    conn.commit()
    conn.close()

def get_owned_game_ids(game_ids):
    """Verilen id listesinden hangilerinin zaten my_games'te olduğunu döner (set olarak)."""
    if not game_ids:
        return set()

    conn = get_connection()
    cursor = conn.cursor()

    placeholders = ",".join("?" for _ in game_ids)
    cursor.execute(f"SELECT game_id FROM my_games WHERE game_id IN ({placeholders})", game_ids)
    rows = cursor.fetchall()

    conn.close()
    return {row["game_id"] for row in rows}

def update_status_only(game_id, status):
    """Sadece status alanını günceller, diğer alanlara (rating, not, vs.) dokunmaz."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE my_games SET status = ? WHERE game_id = ?", (status, game_id))
    conn.commit()
    conn.close()

def get_local_game_data(game_id):
    """games tablosundan tek bir oyunun tüm yerel bilgisini döner (offline yedek için)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM games WHERE id = ?", (game_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

if __name__ == "__main__":
    init_db()
    print("Veritabanı ve tablolar hazır: games.db")
