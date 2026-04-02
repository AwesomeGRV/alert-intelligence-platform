from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
import structlog

from ..core.database import get_db
from ..core.elasticsearch import es_client
from ..models.incident import IncidentCreate, IncidentResponse, IncidentSummary
from ..services.incident_service import IncidentService

logger = structlog.get_logger()
router = APIRouter()
incident_service = IncidentService()

@router.post("/", response_model=IncidentResponse)
async def create_incident(
    incident: IncidentCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    try:
        created_incident = await incident_service.create_incident(incident, db)
        
        # Index in Elasticsearch
        background_tasks.add_task(
            es_client.index_document,
            "incidents",
            created_incident.cluster_id,
            created_incident.dict()
        )
        
        logger.info(f"Incident created: {created_incident.cluster_id}")
        return IncidentResponse(**created_incident.dict())
        
    except Exception as e:
        logger.error(f"Failed to create incident: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[IncidentResponse])
async def get_incidents(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    service: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    try:
        incidents = await incident_service.get_incidents(
            db, skip=skip, limit=limit, 
            status=status, severity=severity, service=service
        )
        
        return [IncidentResponse(**incident) for incident in incidents]
        
    except Exception as e:
        logger.error(f"Failed to get incidents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{cluster_id}", response_model=IncidentResponse)
async def get_incident(cluster_id: str, db: AsyncSession = Depends(get_db)):
    try:
        incident = await incident_service.get_incident(cluster_id, db)
        
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")
        
        return IncidentResponse(**incident)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get incident {cluster_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{cluster_id}", response_model=IncidentResponse)
async def update_incident(
    cluster_id: str,
    incident_update: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    try:
        updated_incident = await incident_service.update_incident(
            cluster_id, incident_update, db
        )
        
        if not updated_incident:
            raise HTTPException(status_code=404, detail="Incident not found")
        
        # Update in Elasticsearch
        background_tasks.add_task(
            es_client.index_document,
            "incidents",
            updated_incident.cluster_id,
            updated_incident.dict()
        )
        
        return IncidentResponse(**updated_incident.dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update incident {cluster_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{cluster_id}/resolve")
async def resolve_incident(
    cluster_id: str,
    resolution_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    try:
        resolved_incident = await incident_service.resolve_incident(
            cluster_id, resolution_data, db
        )
        
        if not resolved_incident:
            raise HTTPException(status_code=404, detail="Incident not found")
        
        # Update in Elasticsearch
        background_tasks.add_task(
            es_client.index_document,
            "incidents",
            resolved_incident.cluster_id,
            resolved_incident.dict()
        )
        
        logger.info(f"Incident resolved: {cluster_id}")
        return {"message": "Incident resolved successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resolve incident {cluster_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{cluster_id}/alerts")
async def get_incident_alerts(
    cluster_id: str,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    try:
        alerts = await incident_service.get_incident_alerts(cluster_id, db, limit)
        return {"alerts": alerts, "total": len(alerts)}
        
    except Exception as e:
        logger.error(f"Failed to get incident alerts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summary/active")
async def get_active_incidents_summary(db: AsyncSession = Depends(get_db)):
    try:
        summary = await incident_service.get_active_incidents_summary(db)
        return summary
        
    except Exception as e:
        logger.error(f"Failed to get active incidents summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search/fulltext")
async def search_incidents(
    q: str,
    size: int = 50,
    db: AsyncSession = Depends(get_db)
):
    try:
        es_query = {
            "query": {
                "multi_match": {
                    "query": q,
                    "fields": ["title", "description", "service", "tags"]
                }
            },
            "sort": [{"created_at": {"order": "desc"}}]
        }
        
        response = await es_client.search("incidents", es_query, size)
        hits = response.get('hits', {}).get('hits', [])
        
        incidents = [hit['_source'] for hit in hits]
        return {"incidents": incidents, "total": len(incidents)}
        
    except Exception as e:
        logger.error(f"Failed to search incidents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
