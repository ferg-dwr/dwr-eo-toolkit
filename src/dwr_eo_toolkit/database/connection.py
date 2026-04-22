"""Database connection and session management."""

import os
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Load environment variables from .env.phase4
load_dotenv(".env.phase4")

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL environment variable is not set. Please check your .env.phase4 file."
    )

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL debugging
    pool_pre_ping=True,  # Verify connections before using them
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """Get a database session (for FastAPI dependency injection)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize the database (create all tables)."""
    from .models import Base

    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    # Test the connection
    try:
        with engine.connect() as conn:
            print("Successfully connected to PostgreSQL!")
            print(
                f"   Database URL: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'localhost'}"
            )
    except Exception as e:
        print(f"Failed to connect: {e}")
