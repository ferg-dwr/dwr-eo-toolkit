"""Database connection and session management."""

import os
from collections.abc import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()

DATABASE_URL: str | None = os.getenv("DATABASE_URL")

engine: Engine | None = None
SessionLocal: sessionmaker | None = None

if DATABASE_URL:
    engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Get a database session (for FastAPI dependency injection)."""
    if SessionLocal is None:
        raise RuntimeError("Database not configured. Set DATABASE_URL environment variable.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize the database (create all tables)."""
    from .models import Base

    if engine is None:
        raise RuntimeError("Database not configured. Set DATABASE_URL environment variable.")
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    if not DATABASE_URL or engine is None:
        print("DATABASE_URL not set.")
    else:
        try:
            with engine.connect() as conn:
                print("Successfully connected to PostgreSQL!")
                print(
                    f"   Database URL: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'localhost'}"
                )
        except Exception as e:
            print(f"Failed to connect: {e}")
