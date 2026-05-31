from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# === TEMPORARY HARDCODED URL ===
DATABASE_URL = "postgresql://postgres:kPcQBTNSuFpUOGGADQekfWvNuohowHJN@postgres.railway.internal:5432/railway"

print("✅ Using hardcoded DATABASE_URL")

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