"""SQLite + SQLAlchemy engine/session management.

The database URL defaults to a project-relative file (storage/contractiq.db)
and can be overridden with CONTRACTIQ_DB_URL. Sessions use an explicit
commit/rollback context manager so a mid-analysis failure never leaves
partial rows behind.
"""
from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from ..core.config import load_settings
from ..core.exceptions import DatabaseFailure


def get_engine(database_url: str | None = None):
    url = database_url or load_settings().database_url
    kwargs: dict = {"future": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    try:
        engine = create_engine(url, **kwargs)
        # enabling SQLite foreign keys per connection
        if url.startswith("sqlite"):

            @event.listens_for(engine, "connect")
            def _fk_on(dbapi_conn, _):  # pragma: no cover - driver hook
                cur = dbapi_conn.cursor()
                cur.execute("PRAGMA foreign_keys=ON")
                cur.close()

        engine.connect().close()
        return engine
    except Exception as exc:
        raise DatabaseFailure(f"Could not create database engine: {type(exc).__name__}") from exc


def make_session_factory(engine) -> sessionmaker:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def init_db(engine) -> None:
    """Create all tables (idempotent)."""
    from . import models  # noqa: F401  (register mappings)

    try:
        models.Base.metadata.create_all(bind=engine)
    except Exception as exc:
        raise DatabaseFailure(f"Could not create database schema: {type(exc).__name__}") from exc


@contextmanager
def session_scope(factory) -> Session:
    """Transactional session: commit on success, rollback on any error."""
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
