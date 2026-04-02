from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
import structlog

from ..core.database import get_db
from ..services.correlation_service import CorrelationService

logger = structlog.get_logger()
router = APIRouter()
correlation_service = CorrelationService()

@router.post("/analyze/{cluster_id}")
async def analyze_incident_correlation(
    cluster_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze correlation for a specific incident
    """
    try:
        correlation_result = await correlation_service.analyze_incident_correlation(cluster_id, db)
        
        if "error" in correlation_result:
            raise HTTPException(status_code=404, detail=correlation_result["error"])
        
        logger.info(f"Correlation analysis completed for incident {cluster_id}")
        return correlation_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to analyze incident correlation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/insights")
async def get_correlation_insights(
    time_range_hours: int = 24,
    services: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get correlation insights across multiple incidents
    """
    try:
        service_list = services.split(",") if services else None
        
        insights = await correlation_service.get_correlation_insights(time_range_hours, service_list)
        
        if "error" in insights:
            raise HTTPException(status_code=500, detail=insights["error"])
        
        return insights
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get correlation insights: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/predict-risk")
async def predict_incident_risk(
    alert_data: Dict[str, Any],
    historical_data: Optional[List[Dict[str, Any]]] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Predict the risk level of an alert becoming an incident
    """
    try:
        risk_prediction = await correlation_service.predict_incident_risk(alert_data, historical_data)
        
        if "error" in risk_prediction:
            raise HTTPException(status_code=400, detail=risk_prediction["error"])
        
        return risk_prediction
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to predict incident risk: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rules")
async def add_correlation_rule(
    rule_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """
    Add a custom correlation rule
    """
    try:
        result = await correlation_service.add_custom_correlation_rule(rule_data)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add correlation rule: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/rules")
async def get_correlation_rules(db: AsyncSession = Depends(get_db)):
    """
    Get all correlation rules and their statistics
    """
    try:
        rules = await correlation_service.get_correlation_rules()
        
        if "error" in rules:
            raise HTTPException(status_code=500, detail=rules["error"])
        
        return rules
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get correlation rules: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/patterns")
async def get_correlation_patterns(
    days: int = 30,
    service: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get correlation patterns over time
    """
    try:
        # Get correlation insights for pattern analysis
        insights = await correlation_service.get_correlation_insights(days * 24, [service] if service else None)
        
        if "error" in insights:
            raise HTTPException(status_code=500, detail=insights["error"])
        
        # Extract patterns
        patterns = insights.get("correlation_patterns", {})
        summary = insights.get("summary", {})
        
        # Format response
        response = {
            "time_period_days": days,
            "service": service,
            "patterns": patterns,
            "summary": summary,
            "total_incidents_analyzed": insights.get("total_incidents", 0)
        }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get correlation patterns: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics")
async def get_correlation_metrics(
    hours: int = 24,
    db: AsyncSession = Depends(get_db)
):
    """
    Get correlation metrics and performance data
    """
    try:
        # Get insights for metrics calculation
        insights = await correlation_service.get_correlation_insights(hours, None)
        
        if "error" in insights:
            raise HTTPException(status_code=500, detail=insights["error"])
        
        # Calculate metrics
        total_incidents = insights.get("total_incidents", 0)
        correlation_patterns = insights.get("correlation_patterns", {})
        
        # Calculate correlation effectiveness
        total_patterns = sum(correlation_patterns.values())
        pattern_diversity = len(correlation_patterns)
        
        # Calculate average correlation score (would need actual data)
        avg_correlation_score = 0.75  # Placeholder - would calculate from actual data
        
        metrics = {
            "time_period_hours": hours,
            "total_incidents": total_incidents,
            "total_correlations": total_patterns,
            "pattern_diversity": pattern_diversity,
            "avg_correlation_score": avg_correlation_score,
            "correlation_effectiveness": min(total_patterns / max(1, total_incidents), 1.0),
            "top_correlation_types": sorted(
                correlation_patterns.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:5]
        }
        
        return metrics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get correlation metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def correlation_health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check for correlation service
    """
    try:
        # Test basic functionality
        rules = await correlation_service.get_correlation_rules()
        
        if "error" in rules:
            return {
                "status": "unhealthy",
                "error": rules["error"],
                "timestamp": structlog.processors.TimeStamper().get_timestamp()
            }
        
        return {
            "status": "healthy",
            "rules_loaded": len(rules.get("statistics", {}).get("total_rules", 0)),
            "timestamp": structlog.processors.TimeStamper().get_timestamp()
        }
        
    except Exception as e:
        logger.error(f"Correlation health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": structlog.processors.TimeStamper().get_timestamp()
        }
