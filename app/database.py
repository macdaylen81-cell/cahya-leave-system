from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os

# Use the URL from Railway
DATABASE_URL = os.getenv("DATABASE_URL")

# Fallback (for safety)
if not DATABASE_URL:
    DATABASE_URL = "postgresql://postgres:kPcQBTNSuFpUOGGADQekfWvNuohowHJN@postgres.railway.internal:5432/railway"

print("✅ DATABASE_URL loaded successfully")

engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()