from __future__ import annotations
import json
from datetime import datetime
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Float, Text, DateTime
from config import DATABASE_URL


def _clean_db_url(url: str) -> tuple[str, dict]:
    if not url.startswith("postgresql"):
        return url, {}
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    params.pop("sslmode", None)
    params.pop("channel_binding", None)
    clean = parsed._replace(query=urlencode({k: v[0] for k, v in params.items()}))
    return urlunparse(clean), {"ssl": "require"}


_db_url, _connect_args = _clean_db_url(DATABASE_URL)
engine = create_async_engine(_db_url, echo=False, connect_args=_connect_args)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class ClaimRecord(Base):
    __tablename__ = "claims"

    claim_id: Mapped[str] = mapped_column(String, primary_key=True)
    member_id: Mapped[str] = mapped_column(String, index=True)
    policy_id: Mapped[str] = mapped_column(String)
    claim_category: Mapped[str] = mapped_column(String)
    claimed_amount: Mapped[float] = mapped_column(Float)
    decision: Mapped[str] = mapped_column(String)
    approved_amount: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_score: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(Text)
    trace_json: Mapped[str] = mapped_column(Text)
    result_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
