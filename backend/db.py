from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./smc_trader.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
class Signal(Base):
    __tablename__ = "signals"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    timeframe = Column(String, index=True)
    side = Column(String)
    entry = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    rr = Column(Float)
    confidence = Column(Float)
    explanation = Column(String)
    raw = Column(JSON)
    created_at = Column(DateTime)
class Execution(Base):
    __tablename__ = "executions"
    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(Integer)
    status = Column(String)
    price = Column(Float)
    size = Column(Float)
    created_at = Column(DateTime)
def init_db():
    Base.metadata.create_all(bind=engine)
