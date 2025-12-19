import sqlite3
from typing import Dict, Optional
import time
import os
from config import DB_SCHEMA_SQL, DB_CONNECTION_TIMEOUT, DEFAULT_DB_PATH

def init_db(db_path: str = None):
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    first_time = not os.path.exists(db_path)
    conn = sqlite3.connect(db_path, timeout=DB_CONNECTION_TIMEOUT)
    cur = conn.cursor()
    cur.executescript(DB_SCHEMA_SQL)
    conn.commit()
    try:
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_url_unique ON articles(url);")
        conn.commit()
    except Exception:
        conn.rollback()
    return conn

def insert_article(conn, record: Dict):
    cur = conn.cursor()
    now_ts = int(time.time())
    try:
        cur.execute("""
        INSERT INTO articles
            (guid, title, description, url, published_at, comments_count, created_at_utc, rating)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record['guid'],
            record.get('title'),
            record.get('description'),
            record.get('url'),
            record.get('published_at'),
            record.get('comments_count'),
            now_ts,
            record.get('rating')
        ))
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        conn.rollback()
        return None

def exists_url(conn, url: str) -> bool:
    if not url:
        return False
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM articles WHERE url = ? LIMIT 1", (url,))
    return cur.fetchone() is not None
