from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os

# Get DATABASE_URL from Railway environment variable
DATABASE_URL = os.getenv("postgresql://postgres:kPcQBTNSuFpUOGGADQekfWvNuohowHJN@ballast.proxy.rlwy.net:56249/railway")

if not DATABASE_URL:
    raise Exception("❌ DATABASE_URL environment variable is not set!")

# Create engine
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