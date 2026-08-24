import os
import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# ទាញយក DATABASE_URL ពី Railway, បើគ្មាន (ឧ. Run លើកុំព្យូទ័រខ្លួនឯង) វានឹងប្រើ SQLite
DB_URL = os.getenv("DATABASE_URL", "sqlite:///BlackMagicAI_bot.db")

# ចំណាំសំខាន់៖ URL របស់ Railway ផ្តើមដោយ postgres:// តែ SQLAlchemy ត្រូវការ postgresql://
if DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DB_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

# សូមរក្សាកូដ Models ផ្សេងៗទៀតរបស់អ្នក (SignalRecord, TradeJournal...) ឲ្យនៅដដែល

# -------------------- Models --------------------

class SignalRecord(Base):
    __tablename__ = "signals"
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False)
    direction = Column(String(10), nullable=False)  # BUY, SELL, NEUTRAL
    entry_price = Column(Float, nullable=False)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    confidence = Column(Integer)
    timeframe = Column(String(10))
    indicators = Column(Text)  # JSON string of indicator signals
    notes = Column(Text)
    result = Column(String(10), nullable=True)  # WIN, LOSS, BREAKEVEN, PENDING
    exit_price = Column(Float, nullable=True)
    pnl_pct = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)


class TradeJournal(Base):
    __tablename__ = "trade_journal"
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False)
    direction = Column(String(10), nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    quantity = Column(Float, default=1.0)
    pnl = Column(Float, nullable=True)
    pnl_pct = Column(Float, nullable=True)
    reason = Column(Text)
    screenshot_id = Column(String(100))
    tags = Column(String(200))
    rating = Column(Integer)  # 1-5 self-rating
    status = Column(String(10), default="OPEN")  # OPEN, CLOSED
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)


class AlertConfig(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(String(30), nullable=False)
    symbol = Column(String(20), nullable=False)
    condition = Column(String(10), nullable=False)  # ABOVE, BELOW
    price = Column(Float, nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class UserSettings(Base):
    __tablename__ = "user_settings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(String(30), unique=True, nullable=False)
    default_timeframe = Column(String(10), default="1h")
    language = Column(String(5), default="km")  # km, en
    auto_alert = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------- Helper Functions --------------------

def save_signal(db, symbol: str, direction: str, entry_price: float,
                stop_loss: float, take_profit: float, confidence: int,
                timeframe: str, indicators: str, notes: str = "") -> SignalRecord:
    record = SignalRecord(
        symbol=symbol,
        direction=direction,
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        confidence=confidence,
        timeframe=timeframe,
        indicators=indicators,
        notes=notes,
        result="PENDING"
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_track_record(db) -> dict:
    from sqlalchemy import func
    total = db.query(SignalRecord).filter(SignalRecord.result != "PENDING").count()
    wins = db.query(SignalRecord).filter(SignalRecord.result == "WIN").count()
    losses = db.query(SignalRecord).filter(SignalRecord.result == "LOSS").count()
    breakeven = db.query(SignalRecord).filter(SignalRecord.result == "BREAKEVEN").count()

    # By symbol
    by_symbol = {}
    for symbol in db.query(SignalRecord.symbol).distinct():
        sym = symbol[0]
        total_s = db.query(SignalRecord).filter(
            SignalRecord.symbol == sym, SignalRecord.result != "PENDING"
        ).count()
        wins_s = db.query(SignalRecord).filter(
            SignalRecord.symbol == sym, SignalRecord.result == "WIN"
        ).count()
        if total_s > 0:
            by_symbol[sym] = {"total": total_s, "wins": wins_s, "win_rate": round(wins_s / total_s * 100, 1)}

    return {
        "total": total,
        "wins": wins,
        "losses": losses,
        "breakeven": breakeven,
        "win_rate": round(wins / total * 100, 1) if total > 0 else 0,
        "by_symbol": by_symbol
    }


def update_signal_result(db, signal_id: int, result: str, exit_price: float, pnl_pct: float):
    record = db.query(SignalRecord).filter(SignalRecord.id == signal_id).first()
    if record:
        record.result = result
        record.exit_price = exit_price
        record.pnl_pct = pnl_pct
        record.closed_at = datetime.datetime.utcnow()
        db.commit()
    return record
