from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
import structlog

from ..core.database import get_db
from ..core.elasticsearch import es_client
from ..models.alert import AlertCreate, AlertResponse, NormalizedAlert, AlertSource
from ..services.alert_normalizer import AlertNormalizer
from ..services.alert_deduplicator import AlertDeduplicator
from ..services.alert_clusterer import AlertClusterer
from ..services.kafka_producer import KafkaProducerService

logger = structlog.get_logger()
router = APIRouter()
alert_normalizer = AlertNormalizer()
alert_deduplicator = AlertDeduplicator()
alert_clusterer = AlertClusterer()
kafka_producer = KafkaProducerService()

@router.post("/ingest", response_model=AlertResponse)
async def ingest_alert(
    alert_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    try:
        # Normalize the alert based on source
        normalized_alert = await alert_normalizer.normalize(alert_data)
        
        # Check for duplicates
        existing_alert = await alert_deduplicator.check_duplicate(normalized_alert, db)
        if existing_alert:
            logger.info(f"Duplicate alert found: {existing_alert.alert_id}")
            return existing_alert
        
        # Save to database
        await save_alert_to_db(normalized_alert, db)
        
        # Index in Elasticsearch
        background_tasks.add_task(
            es_client.index_document,
            "alerts",
            normalized_alert.alert_id,
            normalized_alert.dict()
        )
        
        # Send to Kafka for processing
        background_tasks.add_task(
            kafka_producer.send_alert,
            normalized_alert.dict()
        )
        
        # Trigger clustering in background
        background_tasks.add_task(
            process_alert_clustering,
            normalized_alert
        )
        
        logger.info(f"Alert ingested successfully: {normalized_alert.alert_id}")
        return AlertResponse(**normalized_alert.dict())
        
    except Exception as e:
        logger.error(f"Failed to ingest alert: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[AlertResponse])
async def get_alerts(
    skip: int = 0,
    limit: int = 100,
    service: str = None,
    severity: str = None,
    status: str = None,
    db: AsyncSession = Depends(get_db)
):
    try:
        query = "SELECT * FROM alerts WHERE 1=1"
        params = {}
        
        if service:
            query += " AND service = :service"
            params['service'] = service
        
        if severity:
            query += " AND severity = :severity"
            params['severity'] = severity
            
        if status:
            query += " AND status = :status"
            params['status'] = status
        
        query += " ORDER BY timestamp DESC LIMIT :limit OFFSET :skip"
        params.update({'limit': limit, 'skip': skip})
        
        result = await db.execute(query, params)
        alerts = result.fetchall()
        
        return [AlertResponse(**alert) for alert in alerts]
        
    except Exception as e:
        logger.error(f"Failed to get alerts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: str, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(
            "SELECT * FROM alerts WHERE alert_id = :alert_id",
            {"alert_id": alert_id}
        )
        alert = result.fetchone()
        
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        return AlertResponse(**alert)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get alert {alert_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: str,
    alert_update: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    try:
        # Check if alert exists
        existing = await db.execute(
            "SELECT * FROM alerts WHERE alert_id = :alert_id",
            {"alert_id": alert_id}
        )
        alert = existing.fetchone()
        
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        # Update alert
        update_fields = []
        params = {"alert_id": alert_id}
        
        for field, value in alert_update.items():
            if hasattr(alert, field) and value is not None:
                update_fields.append(f"{field} = :{field}")
                params[field] = value
        
        if update_fields:
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            query = f"UPDATE alerts SET {', '.join(update_fields)} WHERE alert_id = :alert_id"
            await db.execute(query, params)
            await db.commit()
        
        # Get updated alert
        result = await db.execute(
            "SELECT * FROM alerts WHERE alert_id = :alert_id",
            {"alert_id": alert_id}
        )
        updated_alert = result.fetchone()
        
        return AlertResponse(**updated_alert)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update alert {alert_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{alert_id}")
async def delete_alert(alert_id: str, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(
            "DELETE FROM alerts WHERE alert_id = :alert_id",
            {"alert_id": alert_id}
        )
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        await db.commit()
        
        # Delete from Elasticsearch
        await es_client.client.delete(
            index=f"alerts",
            id=alert_id,
            ignore=[404]
        )
        
        return {"message": "Alert deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete alert {alert_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search/fulltext")
async def search_alerts(
    q: str,
    size: int = 50,
    db: AsyncSession = Depends(get_db)
):
    try:
        es_query = {
            "query": {
                "multi_match": {
                    "query": q,
                    "fields": ["description", "service", "tags", "source"]
                }
            },
            "sort": [{"timestamp": {"order": "desc"}}]
        }
        
        response = await es_client.search("alerts", es_query, size)
        hits = response.get('hits', {}).get('hits', [])
        
        alerts = [hit['_source'] for hit in hits]
        return {"alerts": alerts, "total": len(alerts)}
        
    except Exception as e:
        logger.error(f"Failed to search alerts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Helper functions
async def save_alert_to_db(alert: NormalizedAlert, db: AsyncSession):
    query = """
    INSERT INTO alerts (
        alert_id, source, service, severity, status, timestamp, 
        description, tags, metrics_snapshot, raw_data, fingerprint,
        cluster_id, dedup_count, first_seen, last_seen, created_at, updated_at
    ) VALUES (
        :alert_id, :source, :service, :severity, :status, :timestamp,
        :description, :tags, :metrics_snapshot, :raw_data, :fingerprint,
        :cluster_id, :dedup_count, :first_seen, :last_seen, :created_at, :updated_at
    )
    """
    
    await db.execute(query, alert.dict())
    await db.commit()

async def process_alert_clustering(alert: NormalizedAlert):
    try:
        # Check if this alert should be clustered
        cluster_id = await alert_clusterer.cluster_alert(alert)
        
        if cluster_id:
            logger.info(f"Alert {alert.alert_id} clustered into {cluster_id}")
            # Trigger incident creation/update if needed
            # This would be handled by the incident service
            
    except Exception as e:
        logger.error(f"Failed to process alert clustering: {str(e)}")
