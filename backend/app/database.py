"""
database.py
-----------
Sets up the SQLite database connection using SQLAlchemy.

- create_engine: creates the connection to the .db file
- SessionLocal: a factory for database sessions (one per API request)
- Base: all your table models will inherit from this
- get_db: a FastAPI dependency — opens a DB session, yields it,
          then closes it automatically after the request finishes
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Path to the SQLite file. It auto-creates if it doesn't exist.
os.makedirs("db", exist_ok=True)
DATABASE_URL = "sqlite:///./db/anomaly_detection.db"

# connect_args is SQLite-specific: allows multiple threads to share one connection
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# Each request gets its own session (like a transaction)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# All ORM models inherit from Base so SQLAlchemy knows about them
Base = declarative_base()

def get_db():
    """
    FastAPI dependency injection pattern.
    Usage: db: Session = Depends(get_db)
    Opens a session, gives it to the route function,
    then closes it when the request is done — even if an error occurred.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()