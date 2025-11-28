from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool, StaticPool
from app.config import settings
import os

Base = declarative_base()

# Create database engine with serverless-friendly configuration
if settings.DATABASE_URL.startswith("sqlite"):
    # For SQLite, use StaticPool in serverless to avoid connection issues
    # Note: SQLite is NOT recommended for production serverless environments
    # Use PostgreSQL or another cloud database instead
    if os.getenv("VERCEL"):
        # Use NullPool or StaticPool for serverless (read-only filesystem anyway)
        engine = create_engine(
            settings.DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool if ":memory:" in settings.DATABASE_URL else NullPool,
            echo=False
        )
    else:
        engine = create_engine(
            settings.DATABASE_URL,
            connect_args={"check_same_thread": False}
        )
else:
    # For PostgreSQL and other databases, configure for serverless
    engine_kwargs = {
        "echo": False,
        "pool_pre_ping": True,  # Verify connections before using
        "pool_recycle": 300,    # Recycle connections after 5 minutes
    }
    
    if os.getenv("VERCEL"):
        # In serverless, use NullPool to avoid connection pooling issues
        engine_kwargs["poolclass"] = NullPool
    
    engine = create_engine(settings.DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

