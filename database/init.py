"""
Database initialization and setup utilities.
"""

from database.models import Base
from database.session import engine


def init_db() -> None:
    """
    Initialize the database by creating all tables.
    
    Creates all SQLAlchemy tables defined in models.Base.
    Safe to call multiple times - idempotent operation.
    """
    Base.metadata.create_all(bind=engine)


def drop_db() -> None:
    """
    Drop all database tables.
    
    WARNING: This deletes all data. Use only for testing.
    """
    Base.metadata.drop_all(bind=engine)


def reset_db() -> None:
    """
    Reset the database by dropping and recreating all tables.
    
    WARNING: This deletes all data. Use only for testing.
    """
    drop_db()
    init_db()
