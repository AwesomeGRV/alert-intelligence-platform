from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List
import structlog
from datetime import datetime, timedelta

from ..services.incident_service import IncidentService
from ..core.elasticsearch import es_client

logger = structlog.get_logger()

class ChatOpsService:
    def __init__(self):
        self.incident_service = IncidentService()
    
    async def explain_incident(self, incident_id: str, db: AsyncSession) -> Dict[str, Any]:
        try:
            incident = await self.incident_service.get_incident(incident_id, db)
            if not incident:
                return {
                    "response_type": "ephemeral",
                    "text": f"Incident {incident_id} not found"
                }
            
            # Get incident alerts
            alerts = await self.incident_service.get_incident_alerts(incident_id, db, 10)
            
            # Format response
            response = {
                "response_type": "in_channel",
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"Incident: {incident.title}"
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Severity:* {incident.severity}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Status:* {incident.status}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Service:* {incident.service}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Alerts:* {incident.alert_count}"
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Description:* {incident.description}"
                        }
                    }
                ]
            }
            
            # Add affected services if any
            if incident.affected_services:
                response["blocks"].append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Affected Services:* {', '.join(incident.affected_services)}"
                    }
                })
            
            # Add recent alerts
            if alerts:
                alert_fields = []
                for alert in alerts[:5]:
                    alert_fields.append({
                        "type": "mrkdwn",
                        "text": f"• {alert.get('description', 'N/A')} ({alert.get('severity', 'unknown')})"
                    })
                
                response["blocks"].append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Recent Alerts:*"
                    },
                    "fields": alert_fields
                })
            
            # Add root cause if resolved
            if incident.resolved_root_cause:
                response["blocks"].extend([
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Root Cause:* {incident.resolved_root_cause}"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Fix Applied:* {incident.fix_applied}"
                        }
                    }
                ])
            
            # Add suggested actions if active
            if incident.status in ['active', 'investigating']:
                suggestions = self._generate_suggested_actions(incident)
                response["blocks"].append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Suggested Actions:* {suggestions}"
                    }
                })
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to explain incident {incident_id}: {str(e)}")
            return {
                "response_type": "ephemeral",
                "text": f"Error retrieving incident: {str(e)}"
            }
    
    async def list_incidents(self, db: AsyncSession, limit: int = 10) -> Dict[str, Any]:
        try:
            incidents = await self.incident_service.get_incidents(
                db, skip=0, limit=limit, status="active"
            )
            
            if not incidents:
                return {
                    "response_type": "in_channel",
                    "text": "No active incidents found"
                }
            
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "Active Incidents"
                    }
                }
            ]
            
            for incident in incidents:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{incident.title}*\n• ID: {incident.cluster_id}\n• Service: {incident.service}\n• Severity: {incident.severity}\n• Alerts: {incident.alert_count}\n• Created: {incident.created_at.strftime('%Y-%m-%d %H:%M')}"
                    }
                })
            
            return {
                "response_type": "in_channel",
                "blocks": blocks
            }
            
        except Exception as e:
            logger.error(f"Failed to list incidents: {str(e)}")
            return {
                "response_type": "ephemeral",
                "text": f"Error retrieving incidents: {str(e)}"
            }
    
    async def resolve_incident(self, incident_id: str, db: AsyncSession) -> Dict[str, Any]:
        try:
            incident = await self.incident_service.get_incident(incident_id, db)
            if not incident:
                return {
                    "response_type": "ephemeral",
                    "text": f"Incident {incident_id} not found"
                }
            
            if incident.status == 'resolved':
                return {
                    "response_type": "ephemeral",
                    "text": f"Incident {incident_id} is already resolved"
                }
            
            # Quick resolution with minimal info
            resolution_data = {
                "root_cause": "Resolved via ChatOps",
                "fix": "Manual resolution through chat interface"
            }
            
            resolved = await self.incident_service.resolve_incident(incident_id, resolution_data, db)
            
            if resolved:
                return {
                    "response_type": "in_channel",
                    "text": f"Incident {incident_id} has been marked as resolved"
                }
            else:
                return {
                    "response_type": "ephemeral",
                    "text": f"Failed to resolve incident {incident_id}"
                }
                
        except Exception as e:
            logger.error(f"Failed to resolve incident {incident_id}: {str(e)}")
            return {
                "response_type": "ephemeral",
                "text": f"Error resolving incident: {str(e)}"
            }
    
    async def list_alerts(self, db: AsyncSession, filter_value: str = None) -> Dict[str, Any]:
        try:
            # Search for recent alerts
            es_query = {
                "query": {
                    "bool": {
                        "must": [
                            {"range": {"timestamp": {"gte": (datetime.utcnow() - timedelta(hours=24)).isoformat()}}}
                        ]
                    }
                },
                "sort": [{"timestamp": {"order": "desc"}}],
                "size": 10
            }
            
            if filter_value:
                es_query["query"]["bool"]["must"].append({
                    "term": {"service": filter_value}
                })
            
            response = await es_client.search("alerts", es_query)
            hits = response.get('hits', {}).get('hits', [])
            
            if not hits:
                return {
                    "response_type": "in_channel",
                    "text": "No recent alerts found"
                }
            
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"Recent Alerts{f' for {filter_value}' if filter_value else ''}"
                    }
                }
            ]
            
            for hit in hits[:10]:
                alert = hit['_source']
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{alert.get('description', 'N/A')}*\n• Service: {alert.get('service', 'unknown')}\n• Severity: {alert.get('severity', 'unknown')}\n• Time: {alert.get('timestamp', 'unknown')}"
                    }
                })
            
            return {
                "response_type": "in_channel",
                "blocks": blocks
            }
            
        except Exception as e:
            logger.error(f"Failed to list alerts: {str(e)}")
            return {
                "response_type": "ephemeral",
                "text": f"Error retrieving alerts: {str(e)}"
            }
    
    async def recent_alerts(self, db: AsyncSession) -> Dict[str, Any]:
        return await self.list_alerts(db)
    
    async def service_alerts(self, service: str, db: AsyncSession) -> Dict[str, Any]:
        return await self.list_alerts(db, service)
    
    async def get_system_status(self, db: AsyncSession) -> Dict[str, Any]:
        try:
            # Get system overview
            overview = await self.incident_service.get_active_incidents_summary(db)
            
            # Get recent alert count
            es_query = {
                "query": {
                    "range": {"timestamp": {"gte": (datetime.utcnow() - timedelta(hours=1)).isoformat()}}
                },
                "size": 0
            }
            
            response = await es_client.search("alerts", es_query)
            recent_alerts = response.get('hits', {}).get('total', {}).get('value', 0)
            
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "System Status"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Active Incidents:* {overview.get('total_active', 0)}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Recent Alerts (1h):* {recent_alerts}"
                        }
                    ]
                }
            ]
            
            # Add severity breakdown
            severity_breakdown = overview.get('severity_breakdown', {})
            if severity_breakdown:
                severity_fields = []
                for severity, count in severity_breakdown.items():
                    severity_fields.append({
                        "type": "mrkdwn",
                        "text": f"*{severity.title()}:* {count}"
                    })
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Incident Severity Breakdown:*"
                    },
                    "fields": severity_fields
                })
            
            # Add system health indicator
            health_score = self._calculate_system_health(overview, recent_alerts)
            health_emoji = "🟢" if health_score >= 90 else "🟡" if health_score >= 70 else "🔴"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{health_emoji} *System Health:* {health_score}%"
                }
            })
            
            return {
                "response_type": "in_channel",
                "blocks": blocks
            }
            
        except Exception as e:
            logger.error(f"Failed to get system status: {str(e)}")
            return {
                "response_type": "ephemeral",
                "text": f"Error retrieving system status: {str(e)}"
            }
    
    async def process_message(self, message: str, db: AsyncSession) -> Dict[str, Any]:
        try:
            # Simple keyword-based processing
            message_lower = message.lower()
            
            if "incident" in message_lower and "explain" in message_lower:
                # Try to extract incident ID
                words = message_lower.split()
                for word in words:
                    if len(word) == 36 and '-' in word:  # UUID format
                        return await self.explain_incident(word, db)
            
            elif "incident" in message_lower and "list" in message_lower:
                return await self.list_incidents(db)
            
            elif "alert" in message_lower and "list" in message_lower:
                return await self.list_alerts(db)
            
            elif "status" in message_lower:
                return await self.get_system_status(db)
            
            else:
                return {
                    "response_type": "ephemeral",
                    "text": "I can help you with:\n• `/incident explain <id>` - Get incident details\n• `/incident list` - List active incidents\n• `/alerts list` - List recent alerts\n• `/status` - Get system status"
                }
                
        except Exception as e:
            logger.error(f"Failed to process message: {str(e)}")
            return {
                "response_type": "ephemeral",
                "text": f"Error processing message: {str(e)}"
            }
    
    def _generate_suggested_actions(self, incident) -> str:
        actions = []
        
        if incident.severity == 'critical':
            actions.extend([
                "🚨 Escalate to on-call engineer",
                "📞 Consider incident response team activation"
            ])
        
        if incident.alert_count > 10:
            actions.append("📊 Review alert patterns for noise reduction")
        
        if not incident.assigned_to:
            actions.append("👤 Assign incident to appropriate team")
        
        actions.extend([
            "🔍 Investigate root cause",
            "📝 Document findings",
            "🔄 Monitor for recurrence"
        ])
        
        return "\n".join(actions)
    
    def _calculate_system_health(self, overview: Dict[str, Any], recent_alerts: int) -> int:
        try:
            # Simple health calculation based on active incidents and recent alerts
            active_incidents = overview.get('total_active', 0)
            critical_incidents = overview.get('severity_breakdown', {}).get('critical', 0)
            
            # Base score starts at 100
            health_score = 100
            
            # Deduct points for active incidents
            health_score -= active_incidents * 10
            
            # Deduct more points for critical incidents
            health_score -= critical_incidents * 20
            
            # Deduct points for high alert volume
            if recent_alerts > 100:
                health_score -= 20
            elif recent_alerts > 50:
                health_score -= 10
            elif recent_alerts > 20:
                health_score -= 5
            
            # Ensure score is between 0 and 100
            return max(0, min(100, health_score))
            
        except Exception:
            return 75  # Default to 75% if calculation fails
