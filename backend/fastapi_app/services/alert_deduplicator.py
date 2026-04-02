from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime, timedelta
import structlog

from ..models.alert import NormalizedAlert, AlertResponse
from ..core.config import settings

logger = structlog.get_logger()

class AlertDeduplicator:
    def __init__(self):
        self.dedup_window_minutes = settings.ALERT_DEDUP_WINDOW_MINUTES
    
    async def check_duplicate(self, alert: NormalizedAlert, db: AsyncSession) -> Optional[NormalizedAlert]:
        try:
            # Check for existing alert with same fingerprint within dedup window
            cutoff_time = datetime.utcnow() - timedelta(minutes=self.dedup_window_minutes)
            
            query = """
            SELECT * FROM alerts 
            WHERE fingerprint = :fingerprint 
            AND timestamp >= :cutoff_time
            AND status != 'resolved'
            ORDER BY timestamp DESC
            LIMIT 1
            """
            
            result = await db.execute(
                query,
                {
                    "fingerprint": alert.fingerprint,
                    "cutoff_time": cutoff_time
                }
            )
            
            existing_alert = result.fetchone()
            
            if existing_alert:
                # Update the existing alert
                await self._update_existing_alert(existing_alert.alert_id, alert, db)
                
                # Return the updated alert
                updated_result = await db.execute(
                    "SELECT * FROM alerts WHERE alert_id = :alert_id",
                    {"alert_id": existing_alert.alert_id}
                )
                updated_alert = updated_result.fetchone()
                
                logger.info(f"Found duplicate alert: {existing_alert.alert_id}")
                return NormalizedAlert(**updated_alert)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to check for duplicate alert: {str(e)}")
            raise
    
    async def _update_existing_alert(self, alert_id: str, new_alert: NormalizedAlert, db: AsyncSession):
        try:
            update_query = """
            UPDATE alerts SET 
                dedup_count = dedup_count + 1,
                last_seen = :last_seen,
                updated_at = CURRENT_TIMESTAMP,
                metrics_snapshot = :metrics_snapshot
            WHERE alert_id = :alert_id
            """
            
            await db.execute(
                update_query,
                {
                    "alert_id": alert_id,
                    "last_seen": new_alert.timestamp,
                    "metrics_snapshot": new_alert.metrics_snapshot
                }
            )
            
            await db.commit()
            
        except Exception as e:
            logger.error(f"Failed to update existing alert: {str(e)}")
            raise
    
    async def get_duplicate_groups(self, db: AsyncSession, hours: int = 24) -> List[dict]:
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            query = """
            SELECT 
                fingerprint,
                service,
                severity,
                COUNT(*) as alert_count,
                MIN(timestamp) as first_seen,
                MAX(timestamp) as last_seen,
                MAX(dedup_count) as max_dedup_count
            FROM alerts 
            WHERE timestamp >= :cutoff_time
            AND dedup_count > 0
            GROUP BY fingerprint, service, severity
            ORDER BY alert_count DESC
            """
            
            result = await db.execute(query, {"cutoff_time": cutoff_time})
            groups = result.fetchall()
            
            return [dict(group) for group in groups]
            
        except Exception as e:
            logger.error(f"Failed to get duplicate groups: {str(e)}")
            raise
    
    async def resolve_duplicate_group(self, fingerprint: str, db: AsyncSession):
        try:
            update_query = """
            UPDATE alerts 
            SET status = 'resolved', updated_at = CURRENT_TIMESTAMP
            WHERE fingerprint = :fingerprint
            """
            
            await db.execute(update_query, {"fingerprint": fingerprint})
            await db.commit()
            
            logger.info(f"Resolved duplicate group: {fingerprint}")
            
        except Exception as e:
            logger.error(f"Failed to resolve duplicate group: {str(e)}")
            raise
