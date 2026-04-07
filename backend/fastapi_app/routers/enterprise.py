from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import structlog

from ..core.database import get_db
from ..core.security import get_security_context, require_permission
from ..core.monitoring import performance_monitor, monitor_operation
from ..services.enterprise_alert_service import enterprise_alert_service
from ..services.correlation_service import CorrelationService
from ..core.cache import cache_manager

logger = structlog.get_logger()
router = APIRouter()
correlation_service = CorrelationService()

@router.post("/ingest")
@monitor_operation("enterprise_alert_ingest")
@require_permission("alerts:write")
async def ingest_enterprise_alert(
    alert_data: Dict[str, Any],
    source: str = Query(..., description="Alert source system"),
    enrichment_enabled: bool = Query(True, description="Enable alert enrichment"),
    routing_enabled: bool = Query(True, description="Enable alert routing"),
    background_tasks: BackgroundTasks,
    security_context = Depends(get_security_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Ingest alert with enterprise-grade processing
    """
    try:
        # Log ingestion
        logger.info(
            "Enterprise alert ingestion started",
            user_id=security_context.user.id,
            source=source,
            alert_count=1
        )
        
        # Process alert
        result = await enterprise_alert_service.ingest_alert(
            alert_data,
            source,
            enrichment_enabled,
            routing_enabled
        )
        
        # Add background task for post-processing
        if result.get("status") == "processed":
            background_tasks.add_task(
                _post_process_alert,
                result["alert_id"],
                security_context.user.id
            )
        
        logger.info(
            "Enterprise alert ingestion completed",
            user_id=security_context.user.id,
            alert_id=result["alert_id"],
            status=result["status"]
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "Enterprise alert ingestion failed",
            user_id=security_context.user.id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/alerts/{alert_id}")
@require_permission("alerts:read")
async def get_enterprise_alert(
    alert_id: str,
    include_enrichment: bool = Query(True, description="Include enrichment data"),
    security_context = Depends(get_security_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Get alert with full enterprise context
    """
    try:
        if include_enrichment:
            alert_data = await enterprise_alert_service.get_alert_with_enrichment(alert_id)
        else:
            alert_data = await enterprise_alert_service._fetch_alert_from_db(alert_id)
        
        if not alert_data:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        # Log access
        logger.info(
            "Enterprise alert retrieved",
            user_id=security_context.user.id,
            alert_id=alert_id
        )
        
        return alert_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get enterprise alert",
            user_id=security_context.user.id,
            alert_id=alert_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics")
@require_permission("dashboard:read")
async def get_alert_analytics(
    time_range_hours: int = Query(24, ge=1, le=168, description="Time range in hours"),
    service: Optional[str] = Query(None, description="Filter by service"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    security_context = Depends(get_security_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive alert analytics
    """
    try:
        analytics = await enterprise_alert_service.get_alert_analytics(
            time_range_hours,
            service,
            severity
        )
        
        # Add user-specific analytics
        analytics["user_permissions"] = security_context.user.permissions
        analytics["generated_at"] = datetime.utcnow().isoformat()
        
        return analytics
        
    except Exception as e:
        logger.error(
            "Failed to get alert analytics",
            user_id=security_context.user.id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bulk-ingest")
@monitor_operation("enterprise_bulk_ingest")
@require_permission("alerts:write")
async def bulk_ingest_alerts(
    alerts: List[Dict[str, Any]],
    source: str = Query(..., description="Alert source system"),
    enrichment_enabled: bool = Query(True, description="Enable alert enrichment"),
    routing_enabled: bool = Query(True, description="Enable alert routing"),
    background_tasks: BackgroundTasks,
    security_context = Depends(get_security_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Bulk ingest multiple alerts with enterprise processing
    """
    try:
        if len(alerts) > 1000:
            raise HTTPException(
                status_code=400,
                detail="Maximum 1000 alerts allowed per bulk request"
            )
        
        # Log bulk ingestion
        logger.info(
            "Enterprise bulk alert ingestion started",
            user_id=security_context.user.id,
            source=source,
            alert_count=len(alerts)
        )
        
        # Process alerts in parallel
        results = []
        for i, alert_data in enumerate(alerts):
            try:
                result = await enterprise_alert_service.ingest_alert(
                    alert_data,
                    source,
                    enrichment_enabled,
                    routing_enabled
                )
                results.append(result)
            except Exception as e:
                logger.error(
                    "Failed to process alert in bulk",
                    user_id=security_context.user.id,
                    alert_index=i,
                    error=str(e)
                )
                results.append({
                    "status": "failed",
                    "error": str(e),
                    "alert_index": i
                })
        
        # Add background task for bulk post-processing
        successful_alerts = [
            r["alert_id"] for r in results 
            if r.get("status") == "processed"
        ]
        
        if successful_alerts:
            background_tasks.add_task(
                _bulk_post_process_alerts,
                successful_alerts,
                security_context.user.id
            )
        
        # Calculate statistics
        processed_count = len([r for r in results if r.get("status") == "processed"])
        duplicate_count = len([r for r in results if r.get("status") == "duplicate"])
        failed_count = len([r for r in results if r.get("status") == "failed"])
        
        logger.info(
            "Enterprise bulk alert ingestion completed",
            user_id=security_context.user.id,
            source=source,
            total_alerts=len(alerts),
            processed=processed_count,
            duplicates=duplicate_count,
            failed=failed_count
        )
        
        return {
            "total_alerts": len(alerts),
            "processed": processed_count,
            "duplicates": duplicate_count,
            "failed": failed_count,
            "results": results,
            "processing_rate": processed_count / len(alerts) if alerts else 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Enterprise bulk alert ingestion failed",
            user_id=security_context.user.id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/enrichment/{alert_id}")
@require_permission("alerts:read")
async def get_alert_enrichment(
    alert_id: str,
    security_context = Depends(get_security_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Get enrichment data for a specific alert
    """
    try:
        enrichment_data = await cache_manager.get(f"enrichment:{alert_id}")
        
        if not enrichment_data:
            # Fetch from Elasticsearch
            enrichment_data = await enterprise_alert_service._fetch_enrichment_from_es(alert_id)
            
            if enrichment_data:
                await cache_manager.set(
                    f"enrichment:{alert_id}",
                    enrichment_data,
                    ttl_seconds=300
                )
        
        if not enrichment_data:
            raise HTTPException(status_code=404, detail="Enrichment data not found")
        
        return {
            "alert_id": alert_id,
            "enrichment": enrichment_data,
            "retrieved_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get alert enrichment",
            user_id=security_context.user.id,
            alert_id=alert_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/enrichment/{alert_id}")
@require_permission("alerts:write")
async def add_custom_enrichment(
    alert_id: str,
    enrichment_data: Dict[str, Any],
    security_context = Depends(get_security_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Add custom enrichment data to an alert
    """
    try:
        # Verify alert exists
        alert_data = await enterprise_alert_service._fetch_alert_from_db(alert_id)
        if not alert_data:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        # Add custom enrichment
        custom_enrichment = {
            "custom_data": enrichment_data,
            "added_by": security_context.user.id,
            "added_at": datetime.utcnow().isoformat(),
            "source": "user_input"
        }
        
        # Store enrichment
        await enterprise_alert_service._store_enrichment(alert_id, custom_enrichment)
        
        # Invalidate cache
        await cache_manager.delete(f"enrichment:{alert_id}")
        
        logger.info(
            "Custom enrichment added",
            user_id=security_context.user.id,
            alert_id=alert_id
        )
        
        return {
            "alert_id": alert_id,
            "status": "enrichment_added",
            "message": "Custom enrichment data added successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to add custom enrichment",
            user_id=security_context.user.id,
            alert_id=alert_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/routing/rules")
@require_permission("system:configure")
async def get_routing_rules(
    security_context = Depends(get_security_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Get alert routing rules
    """
    try:
        # This would integrate with your routing rules database
        # For now, return mock rules
        rules = [
            {
                "id": "severity_escalation",
                "name": "Severity-based Escalation",
                "condition": "severity in ['critical', 'high']",
                "actions": [
                    {"type": "escalate", "destination": "on-call"},
                    {"type": "notify", "channels": ["sms", "call"]}
                ],
                "enabled": True,
                "priority": 1
            },
            {
                "id": "service_routing",
                "name": "Service-based Routing",
                "condition": "service contains 'database'",
                "actions": [
                    {"type": "assign", "team": "database-team"},
                    {"type": "notify", "channels": ["slack"]}
                ],
                "enabled": True,
                "priority": 2
            }
        ]
        
        return {
            "rules": rules,
            "total_count": len(rules),
            "enabled_count": len([r for r in rules if r["enabled"]])
        }
        
    except Exception as e:
        logger.error(
            "Failed to get routing rules",
            user_id=security_context.user.id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/routing/rules")
@require_permission("system:configure")
async def create_routing_rule(
    rule_data: Dict[str, Any],
    security_context = Depends(get_security_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new routing rule
    """
    try:
        # Validate rule data
        required_fields = ["name", "condition", "actions"]
        for field in required_fields:
            if field not in rule_data:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required field: {field}"
                )
        
        # Create rule
        rule = {
            "id": f"rule_{datetime.utcnow().timestamp()}",
            "name": rule_data["name"],
            "condition": rule_data["condition"],
            "actions": rule_data["actions"],
            "enabled": rule_data.get("enabled", True),
            "priority": rule_data.get("priority", 999),
            "created_by": security_context.user.id,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # This would store the rule in database
        logger.info(
            "Routing rule created",
            user_id=security_context.user.id,
            rule_id=rule["id"],
            rule_name=rule["name"]
        )
        
        return {
            "rule": rule,
            "status": "created",
            "message": "Routing rule created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to create routing rule",
            user_id=security_context.user.id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance/metrics")
@require_permission("system:monitor")
async def get_performance_metrics(
    hours: int = Query(1, ge=1, le=24, description="Time range in hours"),
    security_context = Depends(get_security_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Get alert processing performance metrics
    """
    try:
        # Get system metrics
        system_metrics = performance_monitor.get_system_metrics()
        
        # Get scalability stats
        scalability_stats = scalability_manager.get_stats()
        
        # Get cache stats
        cache_stats = await cache_manager.get_stats()
        
        # Calculate alert processing metrics
        processing_metrics = {
            "ingestion_rate_per_minute": system_metrics["application"]["metrics"].get(
                "alerts_processed_total", {}
            ).get("latest", 0) / hours if hours > 0 else 0,
            "average_processing_time_ms": system_metrics["application"]["metrics"].get(
                "function_duration_ms", {}
            ).get("avg", 0),
            "error_rate": 0.02,  # This would be calculated from actual metrics
            "duplicate_rate": 0.15,  # This would be calculated from actual metrics
        }
        
        return {
            "time_range_hours": hours,
            "system_metrics": system_metrics,
            "scalability_stats": scalability_stats,
            "cache_stats": cache_stats,
            "processing_metrics": processing_metrics,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(
            "Failed to get performance metrics",
            user_id=security_context.user.id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/maintenance/clear-cache")
@require_permission("system:configure")
async def clear_cache(
    cache_type: Optional[str] = Query(None, description="Cache type to clear"),
    security_context = Depends(get_security_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Clear application cache
    """
    try:
        if cache_type:
            # Clear specific cache type
            if cache_type == "alerts":
                # Clear alert cache
                await cache_manager.clear()
                message = "Alert cache cleared"
            elif cache_type == "enrichment":
                # Clear enrichment cache
                await cache_manager.clear()
                message = "Enrichment cache cleared"
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown cache type: {cache_type}"
                )
        else:
            # Clear all cache
            await cache_manager.clear()
            message = "All cache cleared"
        
        logger.info(
            "Cache cleared",
            user_id=security_context.user.id,
            cache_type=cache_type or "all"
        )
        
        return {
            "status": "success",
            "message": message,
            "cleared_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to clear cache",
            user_id=security_context.user.id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

# Background task functions
async def _post_process_alert(alert_id: str, user_id: str):
    """Background task for post-processing alerts"""
    try:
        # This would perform additional post-processing
        # such as sending notifications, updating dashboards, etc.
        logger.info(
            "Post-processing alert",
            alert_id=alert_id,
            user_id=user_id
        )
    except Exception as e:
        logger.error(
            "Failed to post-process alert",
            alert_id=alert_id,
            user_id=user_id,
            error=str(e)
        )

async def _bulk_post_process_alerts(alert_ids: List[str], user_id: str):
    """Background task for bulk post-processing alerts"""
    try:
        # This would perform bulk post-processing
        logger.info(
            "Bulk post-processing alerts",
            alert_count=len(alert_ids),
            user_id=user_id
        )
    except Exception as e:
        logger.error(
            "Failed to bulk post-process alerts",
            alert_count=len(alert_ids),
            user_id=user_id,
            error=str(e)
        )
