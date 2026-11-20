"""Database configuration and session management for Supabase PostgreSQL."""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

logger = logging.getLogger(__name__)

# Explicitly load .env from backend directory
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()  # Fallback to current working directory

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    logger.warning("DATABASE_URL is not set in backend/.env. Supabase PostgreSQL connection requires DATABASE_URL.")
    DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/postgres"

# Supabase / Heroku sometimes provide 'postgres://' which SQLAlchemy 2.0 deprecated in favor of 'postgresql://'
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Check if SQLite or PostgreSQL
is_sqlite = DATABASE_URL.startswith("sqlite")

if is_sqlite:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
else:
    # Test if PostgreSQL is reachable; fallback to local sqlite if Supabase is offline/paused
    try:
        test_engine = create_engine(
            DATABASE_URL,
            pool_size=5,
            max_overflow=5,
            pool_pre_ping=True,
            pool_recycle=300,
            connect_args={"connect_timeout": 5},
        )
        with test_engine.connect() as test_conn:
            pass
        engine = test_engine
        logger.info("Successfully established connection to PostgreSQL (Supabase).")
    except Exception as db_conn_err:
        logger.warning(
            f"Remote PostgreSQL connection failed ({db_conn_err}). "
            "Falling back to local SQLite database (backend/qc_web.db) so the platform remains fully functional."
        )
        sqlite_path = Path(__file__).resolve().parent.parent.parent / "qc_web.db"
        DATABASE_URL = f"sqlite:///{sqlite_path.as_posix()}"
        is_sqlite = True
        engine = create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False},
            pool_pre_ping=True,
        )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables in database and ensure constraints and columns are up to date."""
    try:
        # Import models so all tables are registered with Base.metadata
        from . import models  # noqa: F401
        Base.metadata.create_all(bind=engine)

        if not is_sqlite:
            # PostgreSQL schema adjustments
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE test_cases ADD COLUMN IF NOT EXISTS original_test_id VARCHAR;"))
                conn.execute(text("ALTER TABLE test_cases ADD COLUMN IF NOT EXISTS app_version_id INTEGER REFERENCES application_versions(id) ON DELETE SET NULL;"))
                conn.execute(text("ALTER TABLE execution_results ADD COLUMN IF NOT EXISTS failure_category VARCHAR;"))
                conn.execute(text("ALTER TABLE history ADD COLUMN IF NOT EXISTS failure_category VARCHAR;"))
                conn.execute(text("ALTER TABLE test_cases DROP CONSTRAINT IF EXISTS test_cases_test_id_key;"))
                conn.execute(text("DROP INDEX IF EXISTS ix_test_cases_test_id;"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_test_cases_test_id ON test_cases (test_id);"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_test_cases_app_version_id ON test_cases (app_version_id);"))
            logger.info("Successfully connected to Supabase PostgreSQL and ensured all tables and constraints exist.")
        else:
            logger.info(f"Initialized SQLite database at {DATABASE_URL}.")
    except Exception as e:
        logger.error(f"Failed to initialize database schema: {e}")
        raise
