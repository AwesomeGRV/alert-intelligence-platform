from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
import structlog
import asyncio
from dataclasses import dataclass, asdict
from enum import Enum
import json
import uuid

from ..core.database import Alert, Incident
from ..core.elasticsearch import es_client
from ..core.cache import cache_manager, cached
from ..core.monitoring import performance_monitor, monitor_operation
from ..core.scalability import scalability_manager, worker_pool_executed, rate_limited
from ..models.alert import NormalizedAlert, AlertSeverity, AlertStatus
from .alert_normalizer import AlertNormalizer
from .alert_deduplicator import AlertDeduplicator
from .alert_clusterer import AlertClusterer
from .correlation_service import CorrelationService

logger = structlog.get_logger()

class AlertPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class AlertImpact(str, Enum):
    BUSINESS = "business"
    TECHNICAL = "technical"
    USER_EXPERIENCE = "user_experience"
    SECURITY = "security"

@dataclass
class AlertEnrichment:
    """Enriched alert with additional context"""
    alert_id: str
    original_alert: Dict[str, Any]
    enriched_data: Dict[str, Any]
    metadata: Dict[str, Any]
    enrichment_timestamp: datetime
    enrichment_source: str
    confidence_score: float

@dataclass
class AlertRouting:
    """Alert routing configuration"""
    alert_id: str
    routing_rules: List[str]
    destinations: List[str]
    escalation_policy: str
    notification_channels: List[str]
    auto_actions: List[str]

class EnterpriseAlertService:
    """Enterprise-grade alert service with advanced features"""
    
    def __init__(self):
        self.normalizer = AlertNormalizer()
        self.deduplicator = AlertDeduplicator()
        self.clusterer = AlertClusterer()
        self.correlation_service = CorrelationService()
        
        # Initialize scalability components
        self._init_scalability_components()
    
    def _init_scalability_components(self):
        """Initialize scalability components"""
        # Alert processing worker pool
        scalability_manager.create_worker_pool(
            "alert_processing",
            max_workers=20,
            worker_type="thread",
            queue_size=5000
        )
        
        # Rate limiters
        scalability_manager.create_rate_limiter(
            "alert_ingestion",
            max_requests=1000,
            time_window_seconds=60
        )
        
        scalability_manager.create_rate_limiter(
            "alert_enrichment",
            max_requests=500,
            time_window_seconds=60
        )
        
        # Circuit breakers for external services
        scalability_manager.create_circuit_breaker(
            "elasticsearch",
            failure_threshold=5,
            recovery_timeout_seconds=30
        )
        
        scalability_manager.create_circuit_breaker(
            "external_enrichment",
            failure_threshold=3,
            recovery_timeout_seconds=60
        )
    
    @monitor_operation("ingest_alert")
    @rate_limited("alert_ingestion")
    async def ingest_alert(
        self,
        raw_alert: Dict[str, Any],
        source: str,
        enrichment_enabled: bool = True,
        routing_enabled: bool = True
    ) -> Dict[str, Any]:
        """
        Ingest and process an alert with full enterprise features
        """
        try:
            # Generate unique alert ID
            alert_id = str(uuid.uuid4())
            
            # Normalize alert
            normalized_alert = await self.normalizer.normalize_alert(raw_alert, source)
            normalized_alert.alert_id = alert_id
            
            # Check for duplicates
            duplicate = await self.deduplicator.check_duplicate(normalized_alert)
            if duplicate:
                await self._handle_duplicate_alert(normalized_alert, duplicate)
                return {
                    "alert_id": alert_id,
                    "status": "duplicate",
                    "duplicate_of": duplicate.alert_id,
                    "message": "Alert marked as duplicate"
                }
            
            # Store in database
            await self._store_alert(normalized_alert)
            
            # Index in Elasticsearch
            await self._index_alert(normalized_alert)
            
            # Enrich alert data
            if enrichment_enabled:
                await self._enrich_alert(normalized_alert)
            
            # Route alert
            if routing_enabled:
                await self._route_alert(normalized_alert)
            
            # Cluster alert
            cluster_id = await self.clusterer.cluster_alert(normalized_alert)
            
            # Check for incident creation
            await self._check_incident_creation(normalized_alert, cluster_id)
            
            # Record metrics
            performance_monitor.record_alert_metric(source, normalized_alert.severity, "ingested")
            
            return {
                "alert_id": alert_id,
                "status": "processed",
                "cluster_id": cluster_id,
                "severity": normalized_alert.severity,
                "message": "Alert processed successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to ingest alert: {str(e)}")
            performance_monitor.record_alert_metric(source, "unknown", "failed")
            raise
    
    @worker_pool_executed("alert_processing")
    async def _store_alert(self, alert: NormalizedAlert, db: AsyncSession = None) -> bool:
        """Store alert in database"""
        try:
            # This would integrate with your database session
            # For now, simulate storage
            await asyncio.sleep(0.01)  # Simulate database write
            return True
        except Exception as e:
            logger.error(f"Failed to store alert: {str(e)}")
            return False
    
    @worker_pool_executed("alert_processing")
    @scalability_manager.circuit_breakers["elasticsearch"].call
    async def _index_alert(self, alert: NormalizedAlert) -> bool:
        """Index alert in Elasticsearch"""
        try:
            alert_data = alert.dict()
            alert_data["indexed_at"] = datetime.utcnow().isoformat()
            
            await es_client.index_document("alerts", alert.alert_id, alert_data)
            return True
        except Exception as e:
            logger.error(f"Failed to index alert: {str(e)}")
            return False
    
    @worker_pool_executed("alert_processing")
    async def _enrich_alert(self, alert: NormalizedAlert) -> bool:
        """Enrich alert with additional context"""
        try:
            enrichment_tasks = [
                self._enrich_with_service_topology(alert),
                self._enrich_with_business_context(alert),
                self._enrich_with_historical_data(alert),
                self._enrich_with_external_sources(alert)
            ]
            
            # Run enrichment tasks in parallel
            enrichment_results = await asyncio.gather(*enrichment_tasks, return_exceptions=True)
            
            # Combine enrichment data
            enriched_data = {}
            for result in enrichment_results:
                if isinstance(result, dict):
                    enriched_data.update(result)
                elif isinstance(result, Exception):
                    logger.warning(f"Enrichment task failed: {str(result)}")
            
            # Store enriched data
            if enriched_data:
                await self._store_enrichment(alert.alert_id, enriched_data)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to enrich alert: {str(e)}")
            return False
    
    async def _enrich_with_service_topology(self, alert: NormalizedAlert) -> Dict[str, Any]:
        """Enrich alert with service topology information"""
        try:
            # This would integrate with service discovery and topology systems
            service = alert.service
            
            # Mock enrichment data
            topology_data = {
                "service_owner": "platform-team",
                "service_tier": "critical",
                "dependencies": ["database", "cache", "auth-service"],
                "consumers": ["frontend", "mobile-app"],
                "sla_requirement": "99.9%",
                "business_criticality": "high"
            }
            
            return {"topology": topology_data}
            
        except Exception as e:
            logger.error(f"Failed to enrich with topology: {str(e)}")
            return {}
    
    async def _enrich_with_business_context(self, alert: NormalizedAlert) -> Dict[str, Any]:
        """Enrich alert with business context"""
        try:
            # This would integrate with CMDB and business systems
            service = alert.service
            
            # Mock business context
            business_data = {
                "business_service": "user-authentication",
                "business_impact": "high",
                "affected_users": "all_users",
                "revenue_impact": "high",
                "compliance_impact": "gdpr",
                "stakeholders": ["product-team", "security-team", "compliance-team"]
            }
            
            return {"business": business_data}
            
        except Exception as e:
            logger.error(f"Failed to enrich with business context: {str(e)}")
            return {}
    
    async def _enrich_with_historical_data(self, alert: NormalizedAlert) -> Dict[str, Any]:
        """Enrich alert with historical data"""
        try:
            # Search for similar historical alerts
            similar_alerts = await self._find_similar_historical_alerts(alert)
            
            # Calculate statistics
            if similar_alerts:
                avg_resolution_time = sum(
                    alert.get("resolution_time", 0) for alert in similar_alerts
                ) / len(similar_alerts)
                
                common_solutions = [
                    alert.get("solution") for alert in similar_alerts
                    if alert.get("solution")
                ]
                
                historical_data = {
                    "similar_alerts_count": len(similar_alerts),
                    "avg_resolution_time_minutes": avg_resolution_time,
                    "common_solutions": list(set(common_solutions))[:5],
                    "first_occurrence": min(
                        alert.get("timestamp") for alert in similar_alerts
                    ),
                    "frequency_trend": "increasing" if len(similar_alerts) > 5 else "stable"
                }
            else:
                historical_data = {
                    "similar_alerts_count": 0,
                    "first_occurrence": alert.timestamp,
                    "frequency_trend": "new"
                }
            
            return {"historical": historical_data}
            
        except Exception as e:
            logger.error(f"Failed to enrich with historical data: {str(e)}")
            return {}
    
    @worker_pool_executed("alert_processing")
    @scalability_manager.circuit_breakers["external_enrichment"].call
    async def _enrich_with_external_sources(self, alert: NormalizedAlert) -> Dict[str, Any]:
        """Enrich alert with external data sources"""
        try:
            # This would integrate with external systems like:
            # - CMDB for asset information
            # - Monitoring tools for additional metrics
            # - Ticketing systems for related incidents
            # - Knowledge bases for solutions
            
            external_data = {
                "cmdb": {
                    "asset_type": "virtual_machine",
                    "environment": "production",
                    "datacenter": "us-east-1",
                    "cost_center": "engineering"
                },
                "monitoring": {
                    "cpu_usage": 85.2,
                    "memory_usage": 78.5,
                    "disk_usage": 45.1,
                    "network_io": 1024.5
                },
                "knowledge_base": {
                    "related_articles": 3,
                    "suggested_solutions": ["restart_service", "check_logs"],
                    "confidence": 0.85
                }
            }
            
            return {"external": external_data}
            
        except Exception as e:
            logger.error(f"Failed to enrich with external sources: {str(e)}")
            return {}
    
    async def _store_enrichment(self, alert_id: str, enrichment_data: Dict[str, Any]):
        """Store alert enrichment data"""
        try:
            enrichment = {
                "alert_id": alert_id,
                "enrichment_data": enrichment_data,
                "enrichment_timestamp": datetime.utcnow().isoformat(),
                "enrichment_version": "1.0"
            }
            
            # Store in Elasticsearch
            await es_client.index_document("alert_enrichments", alert_id, enrichment)
            
            # Cache enrichment data
            await cache_manager.set(
                f"enrichment:{alert_id}",
                enrichment_data,
                ttl_seconds=3600
            )
            
        except Exception as e:
            logger.error(f"Failed to store enrichment: {str(e)}")
    
    async def _route_alert(self, alert: NormalizedAlert):
        """Route alert based on rules and policies"""
        try:
            routing_rules = await self._get_routing_rules(alert)
            
            for rule in routing_rules:
                await self._apply_routing_rule(alert, rule)
                
        except Exception as e:
            logger.error(f"Failed to route alert: {str(e)}")
    
    async def _get_routing_rules(self, alert: NormalizedAlert) -> List[Dict[str, Any]]:
        """Get applicable routing rules for alert"""
        # This would integrate with your routing rules engine
        # For now, return mock rules
        
        rules = []
        
        # Severity-based routing
        if alert.severity in ["critical", "high"]:
            rules.append({
                "type": "escalation",
                "destination": "on-call-engineer",
                "notification_channels": ["sms", "call", "slack"],
                "escalation_delay_minutes": 5
            })
        
        # Service-based routing
        if "database" in alert.service.lower():
            rules.append({
                "type": "team_routing",
                "destination": "database-team",
                "notification_channels": ["slack", "email"],
                "auto_assignment": True
            })
        
        # Business impact routing
        if "business" in alert.tags:
            rules.append({
                "type": "stakeholder_notification",
                "destination": "business-stakeholders",
                "notification_channels": ["email"],
                "summary_only": True
            })
        
        return rules
    
    async def _apply_routing_rule(self, alert: NormalizedAlert, rule: Dict[str, Any]):
        """Apply a single routing rule"""
        try:
            rule_type = rule.get("type")
            
            if rule_type == "escalation":
                await self._handle_escalation(alert, rule)
            elif rule_type == "team_routing":
                await self._handle_team_routing(alert, rule)
            elif rule_type == "stakeholder_notification":
                await self._handle_stakeholder_notification(alert, rule)
            
        except Exception as e:
            logger.error(f"Failed to apply routing rule: {str(e)}")
    
    async def _handle_escalation(self, alert: NormalizedAlert, rule: Dict[str, Any]):
        """Handle alert escalation"""
        # This would integrate with your escalation system
        logger.info(f"Escalating alert {alert.alert_id} to {rule.get('destination')}")
    
    async def _handle_team_routing(self, alert: NormalizedAlert, rule: Dict[str, Any]):
        """Handle team-based routing"""
        # This would integrate with your team assignment system
        logger.info(f"Routing alert {alert.alert_id} to team {rule.get('destination')}")
    
    async def _handle_stakeholder_notification(self, alert: NormalizedAlert, rule: Dict[str, Any]):
        """Handle stakeholder notification"""
        # This would integrate with your notification system
        logger.info(f"Notifying stakeholders for alert {alert.alert_id}")
    
    async def _check_incident_creation(self, alert: NormalizedAlert, cluster_id: str):
        """Check if an incident should be created"""
        try:
            # Get cluster information
            cluster_info = await self._get_cluster_info(cluster_id)
            
            # Check incident creation criteria
            should_create = await self._evaluate_incident_creation_criteria(alert, cluster_info)
            
            if should_create:
                await self._create_incident_from_cluster(alert, cluster_id)
                
        except Exception as e:
            logger.error(f"Failed to check incident creation: {str(e)}")
    
    async def _evaluate_incident_creation_criteria(
        self, alert: NormalizedAlert, cluster_info: Dict[str, Any]
    ) -> bool:
        """Evaluate if incident should be created"""
        criteria = {
            "severity_threshold": alert.severity in ["critical", "high"],
            "alert_count_threshold": cluster_info.get("alert_count", 0) >= 3,
            "service_count_threshold": len(cluster_info.get("services", [])) >= 2,
            "time_threshold": cluster_info.get("duration_minutes", 0) >= 10
        }
        
        # Create incident if any criteria is met
        return any(criteria.values())
    
    async def _create_incident_from_cluster(self, alert: NormalizedAlert, cluster_id: str):
        """Create incident from alert cluster"""
        try:
            incident_data = {
                "cluster_id": cluster_id,
                "title": f"Incident: {alert.service} - {alert.description[:50]}",
                "description": f"Automatically created incident from alert cluster {cluster_id}",
                "severity": alert.severity,
                "service": alert.service,
                "status": "open",
                "created_at": datetime.utcnow().isoformat(),
                "auto_created": True,
                "triggering_alert_id": alert.alert_id
            }
            
            # This would integrate with your incident service
            logger.info(f"Creating incident from cluster {cluster_id}")
            
        except Exception as e:
            logger.error(f"Failed to create incident: {str(e)}")
    
    async def _handle_duplicate_alert(self, alert: NormalizedAlert, duplicate: Alert):
        """Handle duplicate alert"""
        try:
            # Update duplicate alert
            duplicate.last_seen = datetime.utcnow()
            duplicate.count += 1
            
            # Log duplicate
            logger.info(f"Duplicate alert detected: {alert.alert_id} -> {duplicate.alert_id}")
            
            # Update metrics
            performance_monitor.record_alert_metric(alert.source, alert.severity, "duplicate")
            
        except Exception as e:
            logger.error(f"Failed to handle duplicate alert: {str(e)}")
    
    @cached(ttl_seconds=300)
    async def _find_similar_historical_alerts(self, alert: NormalizedAlert) -> List[Dict[str, Any]]:
        """Find similar historical alerts"""
        try:
            es_query = {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"service": alert.service}},
                            {"term": {"severity": alert.severity}},
                            {"range": {"timestamp": {"gte": "now-30d"}}}
                        ]
                    }
                },
                "sort": [{"timestamp": {"order": "desc"}}],
                "size": 10
            }
            
            response = await es_client.search("alerts", es_query)
            hits = response.get('hits', {}).get('hits', [])
            
            return [hit['_source'] for hit in hits]
            
        except Exception as e:
            logger.error(f"Failed to find similar alerts: {str(e)}")
            return []
    
    @cached(ttl_seconds=60)
    async def _get_cluster_info(self, cluster_id: str) -> Dict[str, Any]:
        """Get cluster information"""
        try:
            # This would integrate with your clustering service
            # For now, return mock data
            return {
                "cluster_id": cluster_id,
                "alert_count": 5,
                "services": ["api-service", "database"],
                "duration_minutes": 15,
                "severity_distribution": {"high": 3, "medium": 2}
            }
        except Exception as e:
            logger.error(f"Failed to get cluster info: {str(e)}")
            return {}
    
    async def get_alert_with_enrichment(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """Get alert with full enrichment data"""
        try:
            # Get alert from cache or database
            alert_data = await cache_manager.get(f"alert:{alert_id}")
            
            if not alert_data:
                # Fetch from database
                alert_data = await self._fetch_alert_from_db(alert_id)
                if alert_data:
                    await cache_manager.set(f"alert:{alert_id}", alert_data, ttl_seconds=300)
            
            if not alert_data:
                return None
            
            # Get enrichment data
            enrichment_data = await cache_manager.get(f"enrichment:{alert_id}")
            
            if not enrichment_data:
                enrichment_data = await self._fetch_enrichment_from_es(alert_id)
                if enrichment_data:
                    await cache_manager.set(f"enrichment:{alert_id}", enrichment_data, ttl_seconds=300)
            
            # Combine data
            result = {
                "alert": alert_data,
                "enrichment": enrichment_data or {},
                "retrieved_at": datetime.utcnow().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get alert with enrichment: {str(e)}")
            return None
    
    async def _fetch_alert_from_db(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """Fetch alert from database"""
        # This would integrate with your database
        return None
    
    async def _fetch_enrichment_from_es(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """Fetch enrichment from Elasticsearch"""
        try:
            response = await es_client.get_document("alert_enrichments", alert_id)
            return response.get("_source", {}).get("enrichment_data", {})
        except Exception:
            return None
    
    async def get_alert_analytics(
        self,
        time_range_hours: int = 24,
        service: Optional[str] = None,
        severity: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get alert analytics and insights"""
        try:
            # Build query
            query = {
                "query": {
                    "bool": {
                        "must": [
                            {"range": {"timestamp": {"gte": f"now-{time_range_hours}h"}}}
                        ]
                    }
                },
                "aggs": {
                    "services": {"terms": {"field": "service"}},
                    "severities": {"terms": {"field": "severity"}},
                    "sources": {"terms": {"field": "source"}},
                    "timeline": {
                        "date_histogram": {
                            "field": "timestamp",
                            "interval": "1h"
                        }
                    }
                },
                "size": 0
            }
            
            if service:
                query["query"]["bool"]["must"].append({"term": {"service": service}})
            
            if severity:
                query["query"]["bool"]["must"].append({"term": {"severity": severity}})
            
            # Execute query
            response = await es_client.search("alerts", query)
            aggregations = response.get("aggregations", {})
            
            # Process analytics
            analytics = {
                "time_range_hours": time_range_hours,
                "total_alerts": response.get("hits", {}).get("total", {}).get("value", 0),
                "service_distribution": self._process_bucket_aggregation(aggregations.get("services", {})),
                "severity_distribution": self._process_bucket_aggregation(aggregations.get("severities", {})),
                "source_distribution": self._process_bucket_aggregation(aggregations.get("sources", {})),
                "timeline": self._process_timeline_aggregation(aggregations.get("timeline", {}))
            }
            
            # Calculate additional metrics
            analytics["alert_rate_per_hour"] = analytics["total_alerts"] / time_range_hours
            analytics["top_services"] = analytics["service_distribution"][:5]
            analytics["critical_alerts"] = analytics["severity_distribution"].get("critical", 0)
            
            return analytics
            
        except Exception as e:
            logger.error(f"Failed to get alert analytics: {str(e)}")
            return {}
    
    def _process_bucket_aggregation(self, aggregation: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process bucket aggregation results"""
        buckets = aggregation.get("buckets", [])
        return [
            {"key": bucket["key"], "count": bucket["doc_count"]}
            for bucket in buckets
        ]
    
    def _process_timeline_aggregation(self, aggregation: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process timeline aggregation results"""
        buckets = aggregation.get("buckets", [])
        return [
            {
                "timestamp": bucket["key_as_string"],
                "count": bucket["doc_count"]
            }
            for bucket in buckets
        ]

# Global enterprise alert service instance
enterprise_alert_service = EnterpriseAlertService()
