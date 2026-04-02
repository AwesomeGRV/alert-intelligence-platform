from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
import structlog

from ..core.database import get_db
from ..core.elasticsearch import es_client
from ..services.dashboard_service import DashboardService

logger = structlog.get_logger()
router = APIRouter()
dashboard_service = DashboardService()

@router.get("/overview")
async def get_dashboard_overview(db: AsyncSession = Depends(get_db)):
    try:
        overview = await dashboard_service.get_overview_stats(db)
        return overview
        
    except Exception as e:
        logger.error(f"Failed to get dashboard overview: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/alerts/trends")
async def get_alert_trends(
    hours: int = 24,
    service: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    try:
        trends = await dashboard_service.get_alert_trends(db, hours, service)
        return trends
        
    except Exception as e:
        logger.error(f"Failed to get alert trends: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/incidents/trends")
async def get_incident_trends(
    days: int = 7,
    service: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    try:
        trends = await dashboard_service.get_incident_trends(db, days, service)
        return trends
        
    except Exception as e:
        logger.error(f"Failed to get incident trends: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/services/noise-score")
async def get_service_noise_scores(db: AsyncSession = Depends(get_db)):
    try:
        noise_scores = await dashboard_service.get_service_noise_scores(db)
        return {"services": noise_scores}
        
    except Exception as e:
        logger.error(f"Failed to get service noise scores: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/services/health")
async def get_services_health(db: AsyncSession = Depends(get_db)):
    try:
        health = await dashboard_service.get_services_health(db)
        return {"services": health}
        
    except Exception as e:
        logger.error(f"Failed to get services health: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics/realtime")
async def get_realtime_metrics(db: AsyncSession = Depends(get_db)):
    try:
        metrics = await dashboard_service.get_realtime_metrics(db)
        return metrics
        
    except Exception as e:
        logger.error(f"Failed to get realtime metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/top/services")
async def get_top_services(
    metric: str = "alerts",
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    try:
        top_services = await dashboard_service.get_top_services(db, metric, limit)
        return {"services": top_services}
        
    except Exception as e:
        logger.error(f"Failed to get top services: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sla/compliance")
async def get_sla_compliance(
    days: int = 30,
    service: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    try:
        compliance = await dashboard_service.get_sla_compliance(db, days, service)
        return compliance
        
    except Exception as e:
        logger.error(f"Failed to get SLA compliance: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/correlation/insights")
async def get_correlation_insights(db: AsyncSession = Depends(get_db)):
    try:
        insights = await dashboard_service.get_correlation_insights(db)
        return {"insights": insights}
        
    except Exception as e:
        logger.error(f"Failed to get correlation insights: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
