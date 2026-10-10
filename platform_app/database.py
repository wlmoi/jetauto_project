from datetime import timedelta
from pathlib import Path
from threading import Lock

from sqlalchemy import JSON, DateTime, Index, Integer, String, create_engine, delete, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from .contracts import utcnow


class Base(DeclarativeBase):
    pass


class Sample(Base):
    __tablename__ = "telemetry_samples"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    robot_id: Mapped[str] = mapped_column(String(64))
    received_at: Mapped[object] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict] = mapped_column(JSON)
    __table_args__ = (Index("ix_telemetry_robot_time", "robot_id", "received_at"),)


class CommandRow(Base):
    __tablename__ = "commands"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    robot_id: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict] = mapped_column(JSON)
    detail: Mapped[str | None] = mapped_column(String(256), nullable=True)


class Audit(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True))
    actor: Mapped[str] = mapped_column(String(64))
    event: Mapped[str] = mapped_column(String(64))
    detail: Mapped[str] = mapped_column(String(512))


class Store:
    def __init__(self, url):
        if url.startswith("sqlite"):
            Path("runtime").mkdir(exist_ok=True)
        self.engine = create_engine(url, pool_pre_ping=True, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {})
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)
        self.lock = Lock()

    def sample(self, payload):
        with self.lock, self.sessions.begin() as db:
            db.add(Sample(robot_id=payload["robot_id"], received_at=utcnow(), payload=payload))

    def command(self, payload):
        with self.lock, self.sessions.begin() as db:
            db.add(CommandRow(id=payload["id"], robot_id=payload["robot_id"], created_at=utcnow(), status="accepted_backend", payload=payload))

    def ack(self, command_id, status, detail=None):
        with self.lock, self.sessions.begin() as db:
            row = db.get(CommandRow, command_id)
            if row:
                row.status = status
                row.detail = detail

    def audit(self, actor, event, detail=""):
        with self.lock, self.sessions.begin() as db:
            db.add(Audit(created_at=utcnow(), actor=actor, event=event, detail=detail[:512]))

    def history(self, robot_id, limit=100):
        with self.sessions() as db:
            rows = db.scalars(select(Sample).where(Sample.robot_id == robot_id).order_by(Sample.id.desc()).limit(limit)).all()
            return [dict(row.payload, received_at=row.received_at.isoformat()) for row in reversed(rows)]

    def commands(self, limit=40):
        with self.sessions() as db:
            return [{"id": r.id, "created_at": r.created_at.isoformat(), "status": r.status, "detail": r.detail, "payload": r.payload} for r in db.scalars(select(CommandRow).order_by(CommandRow.created_at.desc()).limit(limit))]

    def audits(self, limit=40):
        with self.sessions() as db:
            return [{"id": r.id, "at": r.created_at.isoformat(), "actor": r.actor, "event": r.event, "detail": r.detail} for r in db.scalars(select(Audit).order_by(Audit.id.desc()).limit(limit))]

    def prune(self, days=7):
        with self.lock, self.sessions.begin() as db:
            db.execute(delete(Sample).where(Sample.received_at < utcnow() - timedelta(days=days)))

    def close(self):
        self.engine.dispose()
