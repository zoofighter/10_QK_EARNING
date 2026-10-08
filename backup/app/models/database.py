import sqlite3
from contextlib import contextmanager
from app.config import DB_PATH

def get_connection():
    """Create and return an SQLite connection with Row factory and foreign keys enabled."""
    conn = sqlite3.connect(str(DB_PATH), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

@contextmanager
def get_db():
    """Context manager for database transactions."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def query_db(query, args=(), one=False):
    """Execute a read query and return list of dicts (or single dict if one=True)."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(query, args)
        r = cur.fetchall()
        cur.close()
        if not r:
            return None if one else []
        return dict(r[0]) if one else [dict(row) for row in r]

def execute_db(query, args=(), commit=True):
    """Execute an INSERT/UPDATE/DELETE query and return cursor.lastrowid."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(query, args)
        last_id = cur.lastrowid
        row_count = cur.rowcount
        if commit:
            conn.commit()
        cur.close()
        return last_id if last_id else row_count
    finally:
        conn.close()

def execute_many(query, seq_of_args):
    """Execute multiple statements in batch."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.executemany(query, seq_of_args)
        conn.commit()
        row_count = cur.rowcount
        cur.close()
        return row_count
    finally:
        conn.close()
