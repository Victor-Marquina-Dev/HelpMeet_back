from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from helpmeet_licenses.config import settings

# Railway a veces provee "postgres://" — SQLAlchemy 2.x requiere "postgresql://"
_db_url = settings.database_url.replace("postgres://", "postgresql://", 1)
engine = create_engine(_db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
