"""UrbanRoadAI database helper.

Supports two backends:
  - PostgreSQL + PostGIS  (production, via DATABASE_URL env var)
  - SQLite                (offline demo, default when DATABASE_URL is absent)

Usage:
    from src.db.db import get_db
    db = get_db()                         # auto-detects backend
    db.execute("SELECT 1")
    rows = db.fetch_all("SELECT * FROM damage_classes")
    db.close()
"""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SQLITE_PATH = ROOT / "data" / "roads_demo.db"
SQLITE_SCHEMA = Path(__file__).parent / "schema_sqlite.sql"

# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def get_db(url: str | None = None):
    """Return a DB wrapper.  Reads DATABASE_URL from env if *url* is None."""
    url = url or os.getenv("DATABASE_URL", "")
    if url.startswith("postgresql"):
        return _PostgresDB(url)
    return _SQLiteDB(str(SQLITE_PATH))


def is_postgres() -> bool:
    """True when we are configured for PostgreSQL."""
    return os.getenv("DATABASE_URL", "").startswith("postgresql")


# ---------------------------------------------------------------------------
# SQLite backend (offline / demo)
# ---------------------------------------------------------------------------

class _SQLiteDB:
    """Thin wrapper around sqlite3 for the demo database."""

    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._ensure_schema()

    def _ensure_schema(self):
        """Create tables if they don't already exist."""
        if SQLITE_SCHEMA.exists():
            self.conn.executescript(SQLITE_SCHEMA.read_text())
            self.conn.commit()

    # -- query helpers -------------------------------------------------------

    def execute(self, sql: str, params=()) -> sqlite3.Cursor:
        cur = self.conn.execute(sql, params)
        self.conn.commit()
        return cur

    def fetch_one(self, sql: str, params=()):
        row = self.conn.execute(sql, params).fetchone()
        return dict(row) if row else None

    def fetch_all(self, sql: str, params=()):
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def executemany(self, sql: str, seq):
        self.conn.executemany(sql, seq)
        self.conn.commit()

    @contextmanager
    def transaction(self):
        """Context manager for an explicit transaction."""
        try:
            yield self.conn
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def close(self):
        self.conn.close()


# ---------------------------------------------------------------------------
# PostgreSQL backend (production)
# ---------------------------------------------------------------------------

class _PostgresDB:
    """Thin wrapper around psycopg + connection pool."""

    def __init__(self, dsn: str):
        try:
            from psycopg.rows import dict_row
            from psycopg_pool import ConnectionPool
        except ImportError as exc:
            raise ImportError(
                "psycopg[binary,pool] is required for PostgreSQL mode. "
                "Install it with: pip install 'psycopg[binary,pool]'"
            ) from exc
        self.pool = ConnectionPool(
            dsn, kwargs={"row_factory": dict_row},
            min_size=1, max_size=5, open=True,
        )

    def execute(self, sql: str, params=()):
        with self.pool.connection() as conn:
            return conn.execute(sql, params)

    def fetch_one(self, sql: str, params=()):
        with self.pool.connection() as conn:
            return conn.execute(sql, params).fetchone()

    def fetch_all(self, sql: str, params=()):
        with self.pool.connection() as conn:
            return conn.execute(sql, params).fetchall()

    def executemany(self, sql: str, seq):
        with self.pool.connection() as conn:
            conn.executemany(sql, seq)

    @contextmanager
    def transaction(self):
        with self.pool.connection() as conn:
            with conn.transaction():
                yield conn

    def close(self):
        self.pool.close()

