from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import structlog
import uuid
import json

from ..models.alert import NormalizedAlert
from ..core.config import settings
from ..core.elasticsearch import es_client

logger = structlog.get_logger()

class AlertClusterer:
    def __init__(self):
        self.similarity_threshold = settings.CLUSTERING_SIMILARITY_THRESHOLD
        self.max_alerts_per_cluster = settings.MAX_ALERTS_PER_CLUSTER
        self.clustering_window_minutes = 30
    
    async def cluster_alert(self, alert: NormalizedAlert) -> Optional[str]:
        try:
            # Find similar recent alerts
            similar_alerts = await self._find_similar_alerts(alert)
            
            if similar_alerts:
                # Find existing cluster or create new one
                cluster_id = await self._find_or_create_cluster(alert, similar_alerts)
                return cluster_id
            else:
                # Create new cluster for this alert
                cluster_id = await self._create_new_cluster(alert)
                return cluster_id
                
        except Exception as e:
            logger.error(f"Failed to cluster alert: {str(e)}")
            return None
    
    async def _find_similar_alerts(self, alert: NormalizedAlert) -> List[Dict[str, Any]]:
        try:
            # Search for alerts in the last 30 minutes
            cutoff_time = datetime.utcnow() - timedelta(minutes=self.clustering_window_minutes)
            
            es_query = {
                "query": {
                    "bool": {
                        "must": [
                            {"range": {"timestamp": {"gte": cutoff_time.isoformat()}}},
                            {"term": {"status": "active"}}
                        ],
                        "should": [
                            {"term": {"service": alert.service}},
                            {"terms": {"tags": alert.tags}},
                            {"match": {"description": alert.description}}
                        ],
                        "minimum_should_match": 1
                    }
                },
                "size": 100
            }
            
            response = await es_client.search("alerts", es_query)
            hits = response.get('hits', {}).get('hits', [])
            
            similar_alerts = []
            for hit in hits:
                alert_data = hit['_source']
                similarity_score = self._calculate_similarity(alert, alert_data)
                
                if similarity_score >= self.similarity_threshold:
                    alert_data['similarity_score'] = similarity_score
                    similar_alerts.append(alert_data)
            
            # Sort by similarity score
            similar_alerts.sort(key=lambda x: x['similarity_score'], reverse=True)
            return similar_alerts[:10]  # Top 10 similar alerts
            
        except Exception as e:
            logger.error(f"Failed to find similar alerts: {str(e)}")
            return []
    
    def _calculate_similarity(self, alert1: NormalizedAlert, alert2: Dict[str, Any]) -> float:
        try:
            score = 0.0
            
            # Service similarity (40% weight)
            if alert1.service == alert2.get('service'):
                score += 0.4
            
            # Severity similarity (20% weight)
            if alert1.severity == alert2.get('severity'):
                score += 0.2
            
            # Tags similarity (25% weight)
            tags1 = set(alert1.tags)
            tags2 = set(alert2.get('tags', []))
            if tags1 and tags2:
                tag_similarity = len(tags1.intersection(tags2)) / len(tags1.union(tags2))
                score += 0.25 * tag_similarity
            
            # Description similarity (15% weight)
            desc_similarity = self._text_similarity(alert1.description, alert2.get('description', ''))
            score += 0.15 * desc_similarity
            
            return score
            
        except Exception as e:
            logger.error(f"Failed to calculate similarity: {str(e)}")
            return 0.0
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        # Simple text similarity using Jaccard similarity on word sets
        try:
            words1 = set(text1.lower().split())
            words2 = set(text2.lower().split())
            
            if not words1 or not words2:
                return 0.0
            
            intersection = words1.intersection(words2)
            union = words1.union(words2)
            
            return len(intersection) / len(union)
            
        except Exception:
            return 0.0
    
    async def _find_or_create_cluster(self, alert: NormalizedAlert, similar_alerts: List[Dict[str, Any]]) -> str:
        try:
            # Check if any similar alerts already belong to a cluster
            for similar_alert in similar_alerts:
                existing_cluster_id = similar_alert.get('cluster_id')
                if existing_cluster_id:
                    # Check if cluster is not full
                    cluster_size = await self._get_cluster_size(existing_cluster_id)
                    if cluster_size < self.max_alerts_per_cluster:
                        return existing_cluster_id
            
            # Create new cluster
            return await self._create_new_cluster(alert, similar_alerts)
            
        except Exception as e:
            logger.error(f"Failed to find or create cluster: {str(e)}")
            return await self._create_new_cluster(alert)
    
    async def _create_new_cluster(self, alert: NormalizedAlert, similar_alerts: List[Dict[str, Any]] = None) -> str:
        try:
            cluster_id = str(uuid.uuid4())
            
            # Update the alert with cluster ID
            alert.cluster_id = cluster_id
            
            # Update similar alerts if provided
            if similar_alerts:
                for similar_alert in similar_alerts[:5]:  # Limit to 5 alerts per cluster
                    await self._update_alert_cluster(similar_alert['alert_id'], cluster_id)
            
            logger.info(f"Created new cluster: {cluster_id}")
            return cluster_id
            
        except Exception as e:
            logger.error(f"Failed to create new cluster: {str(e)}")
            return str(uuid.uuid4())
    
    async def _get_cluster_size(self, cluster_id: str) -> int:
        try:
            es_query = {
                "query": {"term": {"cluster_id": cluster_id}},
                "size": 0
            }
            
            response = await es_client.search("alerts", es_query)
            return response.get('hits', {}).get('total', {}).get('value', 0)
            
        except Exception:
            return 0
    
    async def _update_alert_cluster(self, alert_id: str, cluster_id: str):
        try:
            # This would update the database - for now we'll use Elasticsearch
            await es_client.client.update(
                index="alerts",
                id=alert_id,
                body={"doc": {"cluster_id": cluster_id}}
            )
            
        except Exception as e:
            logger.error(f"Failed to update alert cluster: {str(e)}")
    
    async def get_clusters(self, hours: int = 24) -> List[Dict[str, Any]]:
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            es_query = {
                "query": {
                    "bool": {
                        "must": [
                            {"range": {"timestamp": {"gte": cutoff_time.isoformat()}}},
                            {"exists": {"field": "cluster_id"}}
                        ]
                    }
                },
                "aggs": {
                    "clusters": {
                        "terms": {"field": "cluster_id", "size": 100},
                        "aggs": {
                            "latest_alert": {"top_hits": {"sort": [{"timestamp": {"order": "desc"}}], "size": 1}},
                            "alert_count": {"value_count": {"field": "alert_id"}},
                            "services": {"terms": {"field": "service", "size": 10}},
                            "severities": {"terms": {"field": "severity", "size": 5}}
                        }
                    }
                }
            }
            
            response = await es_client.search("alerts", es_query)
            clusters = []
            
            for bucket in response.get('aggregations', {}).get('clusters', {}).get('buckets', []):
                cluster_data = {
                    'cluster_id': bucket['key'],
                    'alert_count': bucket['alert_count']['value'],
                    'services': [service['key'] for service in bucket['services']['buckets']],
                    'severities': [severity['key'] for severity in bucket['severities']['buckets']],
                    'latest_alert': bucket['latest_alert']['hits']['hits'][0]['_source']
                }
                clusters.append(cluster_data)
            
            return clusters
            
        except Exception as e:
            logger.error(f"Failed to get clusters: {str(e)}")
            return []
    
    async def resolve_cluster(self, cluster_id: str):
        try:
            # Update all alerts in the cluster to resolved status
            es_query = {
                "query": {"term": {"cluster_id": cluster_id}}
            }
            
            await es_client.client.update_by_query(
                index="alerts",
                body={
                    "query": es_query["query"],
                    "script": {
                        "source": "ctx._source.status = 'resolved'; ctx._source.updated_at = params.timestamp",
                        "params": {"timestamp": datetime.utcnow().isoformat()}
                    }
                }
            )
            
            logger.info(f"Resolved cluster: {cluster_id}")
            
        except Exception as e:
            logger.error(f"Failed to resolve cluster: {str(e)}")
            raise
