"""
CockroachDB Connection Pool & Transaction Retry Manager
Provides connection handling and automatic retry wrappers for CockroachDB SERIALIZABLE isolation.
Supports ARBITER_MODE=CLOUD enforcement.
"""

import os
import time
import random
import logging
import sqlite3
from typing import Callable, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("db_connection")

PSYCOPG_AVAILABLE = False
try:
    import psycopg
    from psycopg.rows import dict_row
    PSYCOPG_AVAILABLE = True
    logger.info("psycopg3 available for CockroachDB connectivity.")
except ImportError:
    try:
        import psycopg2
        import psycopg2.extras
        PSYCOPG_AVAILABLE = True
        logger.info("psycopg2 available for CockroachDB connectivity.")
    except ImportError:
        logger.info("psycopg unavailable. Falling back to sqlite3 if CLOUD mode not enforced.")


def _load_dotenv(env_path=".env"):
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip("\"'"))

_load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
ARBITER_MODE = os.getenv("ARBITER_MODE", "LOCAL").upper()


class SerializationError(Exception):
    """Raised when a SERIALIZABLE transaction encounters a conflict after max retries."""
    pass


class BusinessValidationError(Exception):
    """Raised when business logic rules (e.g. overlapping temporal reservation) fail inside a transaction."""
    pass


def get_db_connection(db_url: Optional[str] = None):
    """
    Establishes a connection to CockroachDB (or SQLite fallback if specified and NOT in CLOUD mode).
    """
    mode = os.getenv("ARBITER_MODE", "LOCAL").upper()
    url = db_url or os.getenv("DATABASE_URL")
    
    if mode == "CLOUD" and db_url is None:
        if not url or url.startswith("sqlite"):
            if not os.getenv("DATABASE_URL"):
                raise RuntimeError("[MODE: CLOUD] SQLite fallback is DISABLED in CLOUD mode. A valid CockroachDB DATABASE_URL is mandatory!")
            url = os.getenv("DATABASE_URL")
            
        if "postgresql" not in url and "postgres" not in url:
            raise RuntimeError(f"[MODE: CLOUD] Invalid DATABASE_URL for CLOUD mode: '{url}'. Must be a valid CockroachDB PostgreSQL connection string!")

        try:
            import psycopg
            from psycopg.rows import dict_row
            sslrootcert = os.getenv("PGSSLROOTCERT")
            conn_kwargs = {"row_factory": dict_row}
            if sslrootcert and os.path.exists(sslrootcert):
                conn_kwargs["sslrootcert"] = sslrootcert
            elif "sslmode=verify-full" in url and not os.path.exists(os.path.expanduser("~/.postgresql/root.crt")):
                url = url.replace("sslmode=verify-full", "sslmode=require")
                
            conn = psycopg.connect(url, connect_timeout=30, **conn_kwargs)
            conn.autocommit = False
            return conn
        except Exception as e:
            try:
                import psycopg2
                import psycopg2.extras
                conn = psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)
                conn.autocommit = False
                return conn
            except Exception as ex:
                raise RuntimeError(f"[MODE: CLOUD] Failed to connect to CockroachDB Cloud: {e} | {ex}")

    # LOCAL / TEST fallback mode
    url = url or "sqlite3:///:memory:"
    if url.startswith("sqlite") or not PSYCOPG_AVAILABLE:
        if "memory" in url:
            conn = sqlite3.connect("file:arbiter_test_db?mode=memory&cache=shared", uri=True, check_same_thread=False, isolation_level=None)
        else:
            db_file = url.replace("sqlite:///", "") if url.startswith("sqlite:///") else "local_test.db"
            conn = sqlite3.connect(db_file, check_same_thread=False, isolation_level=None)
            
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn
    
    try:
        import psycopg
        from psycopg.rows import dict_row
        conn = psycopg.connect(url, row_factory=dict_row)
        conn.autocommit = False
        return conn
    except Exception:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)
        conn.autocommit = False
        return conn


def execute_transaction_with_retry(
    conn_factory: Callable[[], Any],
    tx_fn: Callable[[Any], Any],
    max_retries: int = 10,
    initial_backoff_sec: float = 0.02
) -> Any:
    """
    Executes tx_fn(conn) inside an explicit SERIALIZABLE / IMMEDIATE transaction retry loop.
    
    Handles CockroachDB SQLSTATE 40001 (SerializationFailureError) and SQLite lock contentions.
    If tx_fn raises BusinessValidationError, transaction rolls back immediately without retry.
    """
    retries = 0
    backoff = initial_backoff_sec

    while True:
        conn = conn_factory()
        is_sqlite = isinstance(conn, sqlite3.Connection)
        try:
            # Begin transaction block
            if is_sqlite:
                conn.execute("BEGIN IMMEDIATE;")
                result = tx_fn(conn)
                conn.execute("COMMIT;")
            else:
                conn.rollback()
                result = tx_fn(conn)
                conn.commit()
            return result
        except Exception as err:
            try:
                if is_sqlite:
                    conn.execute("ROLLBACK;")
                else:
                    conn.rollback()
            except Exception:
                pass
            
            # Check for SQLSTATE 40001 (serialization_failure) or SQLite locked error
            err_str = str(err).lower()
            sqlstate = getattr(err, "sqlstate", None)
            
            is_serialization_failure = (
                sqlstate == "40001" or 
                "serialization_failure" in err_str or
                "restart transaction" in err_str or
                "database is locked" in err_str or
                "operationalerror" in err_str or
                "cannot start a transaction within a transaction" in err_str
            )
            
            if is_serialization_failure:
                retries += 1
                if retries > max_retries:
                    logger.error(f"Transaction failed after {max_retries} serialization retries: {err}")
                    raise SerializationError(f"Max retries ({max_retries}) exceeded due to serialization conflict: {err}")
                
                # Exponential backoff with jitter
                sleep_time = backoff * (2 ** (retries - 1)) + random.uniform(0.01, 0.03)
                time.sleep(sleep_time)
            else:
                # Non-retryable error (e.g. BusinessValidationError)
                raise err
        finally:
            try:
                conn.close()
            except Exception:
                pass
