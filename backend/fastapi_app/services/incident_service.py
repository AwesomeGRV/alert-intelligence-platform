from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import structlog
import uuid

from ..models.incident import IncidentCreate, IncidentResponse, IncidentDB, IncidentStatus
from ..core.elasticsearch import es_client

logger = structlog.get_logger()

class IncidentService:
    def __init__(self):
        pass
    
    async def create_incident(self, incident: IncidentCreate, db: AsyncSession) -> IncidentDB:
        try:
            incident_data = {
                "cluster_id": str(uuid.uuid4()),
                "title": incident.title,
                "description": incident.description,
                "severity": incident.severity,
                "status": IncidentStatus.ACTIVE,
                "service": incident.service,
                "affected_services": incident.affected_services,
                "alert_count": 0,
                "first_alert_time": datetime.utcnow(),
                "last_alert_time": datetime.utcnow(),
                "tags": incident.tags,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            query = """
            INSERT INTO incidents (
                cluster_id, title, description, severity, status, service,
                affected_services, alert_count, first_alert_time, last_alert_time,
                tags, created_at, updated_at
            ) VALUES (
                :cluster_id, :title, :description, :severity, :status, :service,
                :affected_services, :alert_count, :first_alert_time, :last_alert_time,
                :tags, :created_at, :updated_at
            )
            """
            
            await db.execute(query, incident_data)
            await db.commit()
            
            return IncidentDB(**incident_data)
            
        except Exception as e:
            logger.error(f"Failed to create incident: {str(e)}")
            raise
    
    async def get_incidents(
        self, 
        db: AsyncSession, 
        skip: int = 0, 
        limit: int = 100,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        service: Optional[str] = None
    ) -> List[IncidentDB]:
        try:
            query = "SELECT * FROM incidents WHERE 1=1"
            params = {}
            
            if status:
                query += " AND status = :status"
                params['status'] = status
            
            if severity:
                query += " AND severity = :severity"
                params['severity'] = severity
            
            if service:
                query += " AND service = :service"
                params['service'] = service
            
            query += " ORDER BY created_at DESC LIMIT :limit OFFSET :skip"
            params.update({'limit': limit, 'skip': skip})
            
            result = await db.execute(text(query), params)
            incidents = result.fetchall()
            
            return [IncidentDB(**incident) for incident in incidents]
            
        except Exception as e:
            logger.error(f"Failed to get incidents: {str(e)}")
            raise
    
    async def get_incident(self, cluster_id: str, db: AsyncSession) -> Optional[IncidentDB]:
        try:
            result = await db.execute(
                "SELECT * FROM incidents WHERE cluster_id = :cluster_id",
                {"cluster_id": cluster_id}
            )
            incident = result.fetchone()
            
            if incident:
                return IncidentDB(**incident)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get incident {cluster_id}: {str(e)}")
            raise
    
    async def update_incident(
        self, 
        cluster_id: str, 
        update_data: Dict[str, Any], 
        db: AsyncSession
    ) -> Optional[IncidentDB]:
        try:
            # Check if incident exists
            existing = await self.get_incident(cluster_id, db)
            if not existing:
                return None
            
            # Update fields
            update_fields = []
            params = {"cluster_id": cluster_id}
            
            for field, value in update_data.items():
                if hasattr(existing, field) and value is not None:
                    update_fields.append(f"{field} = :{field}")
                    params[field] = value
            
            if update_fields:
                update_fields.append("updated_at = CURRENT_TIMESTAMP")
                query = f"UPDATE incidents SET {', '.join(update_fields)} WHERE cluster_id = :cluster_id"
                await db.execute(text(query), params)
                await db.commit()
            
            # Get updated incident
            return await self.get_incident(cluster_id, db)
            
        except Exception as e:
            logger.error(f"Failed to update incident {cluster_id}: {str(e)}")
            raise
    
    async def resolve_incident(
        self, 
        cluster_id: str, 
        resolution_data: Dict[str, Any], 
        db: AsyncSession
    ) -> Optional[IncidentDB]:
        try:
            incident = await self.get_incident(cluster_id, db)
            if not incident:
                return None
            
            # Calculate time to resolve
            time_to_resolve = int((datetime.utcnow() - incident.created_at).total_seconds() / 60)
            
            update_data = {
                "status": IncidentStatus.RESOLVED,
                "resolved_root_cause": resolution_data.get("root_cause"),
                "fix_applied": resolution_data.get("fix"),
                "resolution_time": datetime.utcnow(),
                "time_to_resolve": time_to_resolve
            }
            
            return await self.update_incident(cluster_id, update_data, db)
            
        except Exception as e:
            logger.error(f"Failed to resolve incident {cluster_id}: {str(e)}")
            raise
    
    async def get_incident_alerts(self, cluster_id: str, db: AsyncSession, limit: int = 100) -> List[Dict[str, Any]]:
        try:
            es_query = {
                "query": {"term": {"cluster_id": cluster_id}},
                "sort": [{"timestamp": {"order": "desc"}}],
                "size": limit
            }
            
            response = await es_client.search("alerts", es_query)
            hits = response.get('hits', {}).get('hits', [])
            
            return [hit['_source'] for hit in hits]
            
        except Exception as e:
            logger.error(f"Failed to get incident alerts: {str(e)}")
            return []
    
    async def get_active_incidents_summary(self, db: AsyncSession) -> Dict[str, Any]:
        try:
            # Get counts by severity
            severity_query = """
            SELECT severity, COUNT(*) as count
            FROM incidents 
            WHERE status IN ('active', 'investigating', 'identified', 'monitoring')
            GROUP BY severity
            """
            
            result = await db.execute(text(severity_query))
            severity_counts = {row.severity: row.count for row in result.fetchall()}
            
            # Get total active count
            total_query = """
            SELECT COUNT(*) as total
            FROM incidents 
            WHERE status IN ('active', 'investigating', 'identified', 'monitoring')
            """
            
            result = await db.execute(text(total_query))
            total_active = result.fetchone().total
            
            # Get recent incidents
            recent_query = """
            SELECT cluster_id, title, severity, service, created_at
            FROM incidents 
            WHERE status IN ('active', 'investigating', 'identified', 'monitoring')
            ORDER BY created_at DESC
            LIMIT 5
            """
            
            result = await db.execute(text(recent_query))
            recent_incidents = [dict(row) for row in result.fetchall()]
            
            return {
                "total_active": total_active,
                "severity_breakdown": severity_counts,
                "recent_incidents": recent_incidents
            }
            
        except Exception as e:
            logger.error(f"Failed to get active incidents summary: {str(e)}")
            return {}
    
    async def auto_create_incident_from_cluster(
        self, 
        cluster_id: str, 
        cluster_data: Dict[str, Any], 
        db: AsyncSession
    ) -> Optional[IncidentDB]:
        try:
            # Check if incident already exists for this cluster
            existing = await db.execute(
                "SELECT cluster_id FROM incidents WHERE cluster_id = :cluster_id",
                {"cluster_id": cluster_id}
            )
            
            if existing.fetchone():
                return None
            
            # Create incident from cluster data
            latest_alert = cluster_data.get('latest_alert', {})
            services = cluster_data.get('services', [])
            
            incident_data = IncidentCreate(
                title=f"Incident: {latest_alert.get('service', 'Unknown Service')} Alert Cluster",
                description=f"Cluster of {cluster_data.get('alert_count', 0)} related alerts",
                severity=self._map_severity_from_alerts(cluster_data.get('severities', [])),
                service=services[0] if services else 'unknown',
                affected_services=services,
                tags=latest_alert.get('tags', [])
            )
            
            return await self.create_incident(incident_data, db)
            
        except Exception as e:
            logger.error(f"Failed to auto-create incident from cluster: {str(e)}")
            return None
    
    def _map_severity_from_alerts(self, severities: List[str]) -> str:
        severity_priority = {
            'critical': 4,
            'high': 3,
            'medium': 2,
            'low': 1,
            'info': 0
        }
        
        if not severities:
            return 'medium'
        
        # Return the highest severity
        highest_severity = max(
            severities, 
            key=lambda s: severity_priority.get(s, 0)
        )
        
        return highest_severity
