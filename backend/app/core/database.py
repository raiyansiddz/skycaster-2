from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Create PostgreSQL engine
engine = create_engine(
    settings.DATABASE_URL.replace("+asyncpg", "").replace("?ssl=require", "?sslmode=require"),
    pool_pre_ping=True,
    echo=False,
    pool_size=20,
    max_overflow=30,
    pool_recycle=3600,
    connect_args={"options": "-csearch_path=public"}
)

# Create session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class
Base = declarative_base()

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()