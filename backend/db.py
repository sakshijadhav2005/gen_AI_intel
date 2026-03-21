from sqlalchemy import create_engine, Column, Integer, String, Text, Date
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from pgvector.sqlalchemy import Vector
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://dbuser:dbpass@localhost:5432/vericheck")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Fact(Base):
    __tablename__ = "facts"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, index=True)
    source = Column(String)
    date = Column(Date)
    embedding = Column(Vector(384)) # matching sentence-transformers miniLM output dimension

from sqlalchemy import text

def init_db():
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
