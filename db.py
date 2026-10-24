from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "football.db"

def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with connect() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            match_id INTEGER PRIMARY KEY,
            competition_code TEXT NOT NULL,
            competition_name TEXT NOT NULL,
            season INTEGER NOT NULL,
            utc_date TEXT NOT NULL,
            status TEXT NOT NULL,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            home_goals INTEGER,
            away_goals INTEGER,
            source TEXT NOT NULL DEFAULT 'football-data.org',
            fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_matches_comp_date
        ON matches(competition_code, utc_date)
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id INTEGER NOT NULL,
            model_version TEXT NOT NULL,
            predicted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            lambda_home REAL NOT NULL,
            lambda_away REAL NOT NULL,
            p_home REAL NOT NULL,
            p_draw REAL NOT NULL,
            p_away REAL NOT NULL,
            p_over25 REAL NOT NULL,
            p_under25 REAL NOT NULL,
            p_btts_yes REAL NOT NULL,
            p_btts_no REAL NOT NULL,
            most_likely_score TEXT NOT NULL,
            FOREIGN KEY(match_id) REFERENCES matches(match_id)
        )
        """)
        conn.commit()
