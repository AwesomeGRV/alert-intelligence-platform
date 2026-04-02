from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, String, DateTime, Integer, Float, Text, Boolean, JSON
from datetime import datetime
import structlog

from .config import settings

logger = structlog.get_logger()
Base = declarative_base()

class AlertDB(Base):
    __tablename__ = "alerts"
    
    alert_id = Column(String, primary_key=True)
    source = Column(String, nullable=False)
    service = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    status = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    description = Column(Text, nullable=False)
    tags = Column(JSON, default=list)
    metrics_snapshot = Column(JSON, default=dict)
    raw_data = Column(JSON, default=dict)
    fingerprint = Column(String, nullable=True)
    cluster_id = Column(String, nullable=True)
    dedup_count = Column(Integer, default=0)
    first_seen = Column(DateTime, nullable=True)
    last_seen = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class IncidentDB(Base):
    __tablename__ = "incidents"
    
    cluster_id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String, nullable=False)
    status = Column(String, nullable=False)
    service = Column(String, nullable=False)
    affected_services = Column(JSON, default=list)
    alert_count = Column(Integer, default=0)
    first_alert_time = Column(DateTime, nullable=False)
    last_alert_time = Column(DateTime, nullable=False)
    tags = Column(JSON, default=list)
    metrics_impact = Column(JSON, default=dict)
    related_deployments = Column(JSON, default=list)
    correlated_logs = Column(JSON, default=list)
    suggested_root_cause = Column(Text, nullable=True)
    root_cause_type = Column(String, nullable=True)
    confidence_score = Column(Float, default=0.0)
    resolved_root_cause = Column(Text, nullable=True)
    fix_applied = Column(Text, nullable=True)
    resolution_time = Column(DateTime, nullable=True)
    time_to_resolve = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    assigned_to = Column(String, nullable=True)
    sla_breach = Column(Boolean, default=False)

class ServiceNoiseScore(Base):
    __tablename__ = "service_noise_scores"
    
    service = Column(String, primary_key=True)
    total_alerts = Column(Integer, default=0)
    noisy_alerts = Column(Integer, default=0)
    noise_score = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=datetime.utcnow)

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    echo=settings.DEBUG
)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise
