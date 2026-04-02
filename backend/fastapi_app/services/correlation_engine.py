from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import structlog
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from ..core.elasticsearch import es_client
from ..core.config import settings
from .root_cause_rules import RootCauseAnalyzer

logger = structlog.get_logger()

class CorrelationEngine:
    def __init__(self):
        self.correlation_window_hours = 24
        self.similarity_threshold = 0.7
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        self.root_cause_analyzer = RootCauseAnalyzer()
    
    async def correlate_alerts_with_incidents(
        self, 
        alert_cluster: Dict[str, Any], 
        db: AsyncSession
    ) -> Dict[str, Any]:
        try:
            correlations = {
                "recent_deployments": await self._find_recent_deployments(alert_cluster),
                "log_patterns": await self._find_correlated_logs(alert_cluster),
                "metric_anomalies": await self._find_metric_anomalies(alert_cluster),
                "similar_incidents": await self._find_similar_incidents(alert_cluster),
                "service_dependencies": await self._analyze_service_dependencies(alert_cluster)
            }
            
            # Calculate correlation score
            correlation_score = self._calculate_correlation_score(correlations)
            
            # Enhanced root cause analysis with rule-based system
            root_cause_analysis = await self._analyze_root_cause_with_rules(
                alert_cluster, correlations
            )
            
            return {
                "correlations": correlations,
                "correlation_score": correlation_score,
                "root_cause_analysis": root_cause_analysis,
                "confidence": self._calculate_confidence(correlations, correlation_score)
            }
            
        except Exception as e:
            logger.error(f"Failed to correlate alerts with incidents: {str(e)}")
            return {}
    
    async def _find_recent_deployments(self, alert_cluster: Dict[str, Any]) -> List[Dict[str, Any]]:
        try:
            services = alert_cluster.get('services', [])
            cluster_time = alert_cluster.get('latest_alert', {}).get('timestamp')
            
            if not cluster_time or not services:
                return []
            
            # Look for deployments in the last 2 hours for affected services
            deployment_window = datetime.fromisoformat(cluster_time.replace('Z', '+00:00')) - timedelta(hours=2)
            
            # This would integrate with deployment systems like Jenkins, GitHub Actions, etc.
            # For now, we'll simulate with Elasticsearch
            es_query = {
                "query": {
                    "bool": {
                        "must": [
                            {"terms": {"service": services}},
                            {"range": {"deployment_time": {"gte": deployment_window.isoformat()}}},
                            {"term": {"type": "deployment"}}
                        ]
                    }
                },
                "sort": [{"deployment_time": {"order": "desc"}}],
                "size": 10
            }
            
            # Mock deployment data for demonstration
            mock_deployments = []
            for service in services[:3]:  # Limit to top 3 services
                mock_deployments.append({
                    "service": service,
                    "deployment_time": (datetime.utcnow() - timedelta(minutes=30)).isoformat(),
                    "version": "v1.2.3",
                    "commit_hash": "abc123def",
                    "deployer": "ci-cd-system",
                    "environment": "production"
                })
            
            return mock_deployments
            
        except Exception as e:
            logger.error(f"Failed to find recent deployments: {str(e)}")
            return []
    
    async def _find_correlated_logs(self, alert_cluster: Dict[str, Any]) -> List[Dict[str, Any]]:
        try:
            services = alert_cluster.get('services', [])
            cluster_time = alert_cluster.get('latest_alert', {}).get('timestamp')
            
            if not cluster_time or not services:
                return []
            
            # Look for error patterns in logs around the time of alerts
            search_window = timedelta(minutes=15)
            cluster_datetime = datetime.fromisoformat(cluster_time.replace('Z', '+00:00'))
            
            # This would integrate with ELK/OpenSearch
            # Mock log data for demonstration
            mock_logs = []
            error_patterns = [
                "OutOfMemoryError",
                "ConnectionTimeoutException",
                "DatabaseConnectionException",
                "ServiceUnavailableException"
            ]
            
            for i, service in enumerate(services[:2]):  # Limit to top 2 services
                for pattern in error_patterns[:2]:  # Limit patterns
                    mock_logs.append({
                        "service": service,
                        "timestamp": (cluster_datetime - timedelta(minutes=i*5)).isoformat(),
                        "level": "ERROR",
                        "message": f"{pattern} occurred in {service}",
                        "pattern": pattern,
                        "count": np.random.randint(1, 10)
                    })
            
            return mock_logs
            
        except Exception as e:
            logger.error(f"Failed to find correlated logs: {str(e)}")
            return []
    
    async def _find_metric_anomalies(self, alert_cluster: Dict[str, Any]) -> List[Dict[str, Any]]:
        try:
            services = alert_cluster.get('services', [])
            
            # Look for metric anomalies in affected services
            mock_anomalies = []
            metrics = ["cpu_usage", "memory_usage", "response_time", "error_rate", "throughput"]
            
            for service in services[:3]:  # Limit to top 3 services
                for metric in metrics[:3]:  # Limit metrics
                    mock_anomalies.append({
                        "service": service,
                        "metric": metric,
                        "current_value": np.random.uniform(80, 99),
                        "threshold": np.random.uniform(70, 80),
                        "deviation": np.random.uniform(2, 5),
                        "time_window": "5m",
                        "severity": "high" if np.random.random() > 0.5 else "medium"
                    })
            
            return mock_anomalies
            
        except Exception as e:
            logger.error(f"Failed to find metric anomalies: {str(e)}")
            return []
    
    async def _find_similar_incidents(self, alert_cluster: Dict[str, Any]) -> List[Dict[str, Any]]:
        try:
            services = alert_cluster.get('services', [])
            severities = alert_cluster.get('severities', [])
            
            # Search for similar historical incidents
            es_query = {
                "query": {
                    "bool": {
                        "should": [
                            {"terms": {"service": services}},
                            {"terms": "severity": severities}
                        ],
                        "minimum_should_match": 1,
                        "range": {
                            "created_at": {
                                "gte": (datetime.utcnow() - timedelta(days=30)).isoformat()
                            }
                        }
                    }
                },
                "sort": [{"created_at": {"order": "desc"}}],
                "size": 5
            }
            
            response = await es_client.search("incidents", es_query)
            hits = response.get('hits', {}).get('hits', [])
            
            similar_incidents = []
            for hit in hits:
                incident = hit['_source']
                similarity_score = self._calculate_incident_similarity(alert_cluster, incident)
                
                if similarity_score >= self.similarity_threshold:
                    incident['similarity_score'] = similarity_score
                    similar_incidents.append(incident)
            
            return similar_incidents
            
        except Exception as e:
            logger.error(f"Failed to find similar incidents: {str(e)}")
            return []
    
    async def _analyze_service_dependencies(self, alert_cluster: Dict[str, Any]) -> Dict[str, Any]:
        try:
            services = alert_cluster.get('services', [])
            
            # Analyze service dependencies and impact
            # This would integrate with service mesh or dependency tracking systems
            mock_dependencies = {
                "upstream_services": [f"upstream-{s}" for s in services[:2]],
                "downstream_services": [f"downstream-{s}" for s in services[:2]],
                "impact_score": np.random.uniform(0.5, 1.0),
                "critical_path": services[0] if services else None,
                "dependency_graph": {
                    "nodes": [{"id": s, "type": "service"} for s in services],
                    "edges": []
                }
            }
            
            return mock_dependencies
            
        except Exception as e:
            logger.error(f"Failed to analyze service dependencies: {str(e)}")
            return {}
    
    def _calculate_incident_similarity(self, alert_cluster: Dict[str, Any], incident: Dict[str, Any]) -> float:
        try:
            score = 0.0
            
            # Service similarity (40% weight)
            cluster_services = set(alert_cluster.get('services', []))
            incident_services = {incident.get('service')} | set(incident.get('affected_services', []))
            
            if cluster_services and incident_services:
                service_similarity = len(cluster_services.intersection(incident_services)) / len(cluster_services.union(incident_services))
                score += 0.4 * service_similarity
            
            # Severity similarity (20% weight)
            cluster_severities = set(alert_cluster.get('severities', []))
            incident_severity = incident.get('severity')
            
            if cluster_severities and incident_severity:
                if incident_severity in cluster_severities:
                    score += 0.2
            
            # Description similarity (40% weight)
            cluster_description = " ".join(alert_cluster.get('services', []))
            incident_description = incident.get('description', '')
            
            if cluster_description and incident_description:
                descriptions = [cluster_description, incident_description]
                try:
                    tfidf_matrix = self.vectorizer.fit_transform(descriptions)
                    similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
                    score += 0.4 * similarity
                except:
                    score += 0.1  # Small default score if text processing fails
            
            return score
            
        except Exception as e:
            logger.error(f"Failed to calculate incident similarity: {str(e)}")
            return 0.0
    
    def _calculate_correlation_score(self, correlations: Dict[str, Any]) -> float:
        try:
            score = 0.0
            
            # Recent deployments (30% weight)
            deployments = correlations.get("recent_deployments", [])
            if deployments:
                score += 0.3 * min(len(deployments) / 3.0, 1.0)
            
            # Log patterns (25% weight)
            logs = correlations.get("log_patterns", [])
            if logs:
                score += 0.25 * min(len(logs) / 5.0, 1.0)
            
            # Metric anomalies (25% weight)
            anomalies = correlations.get("metric_anomalies", [])
            if anomalies:
                score += 0.25 * min(len(anomalies) / 5.0, 1.0)
            
            # Similar incidents (20% weight)
            similar_incidents = correlations.get("similar_incidents", [])
            if similar_incidents:
                score += 0.2 * min(len(similar_incidents) / 3.0, 1.0)
            
            return min(score, 1.0)
            
        except Exception as e:
            logger.error(f"Failed to calculate correlation score: {str(e)}")
            return 0.0
    
    async def _analyze_root_cause_with_rules(
        self, 
        alert_cluster: Dict[str, Any], 
        correlations: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enhanced root cause analysis using rule-based system"""
        try:
            # Perform rule-based analysis
            root_cause_analysis = await self.root_cause_analyzer.analyze_root_cause(
                alert_cluster, 
                correlations,
                correlations.get("log_patterns", []),
                correlations.get("metric_anomalies", [])
            )
            
            # Convert to dictionary format
            return {
                "root_cause_type": root_cause_analysis.root_cause_type.value,
                "confidence": root_cause_analysis.confidence.value,
                "description": root_cause_analysis.description,
                "suggested_action": root_cause_analysis.suggested_action,
                "supporting_evidence": root_cause_analysis.supporting_evidence,
                "related_rules": root_cause_analysis.related_rules,
                "confidence_score": root_cause_analysis.confidence_score
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze root cause with rules: {str(e)}")
            return {
                "root_cause_type": "unknown",
                "confidence": "low",
                "description": "Root cause analysis failed",
                "suggested_action": "Manual investigation required",
                "supporting_evidence": [],
                "related_rules": [],
                "confidence_score": 0.0
            }
    
    def _suggest_root_cause(self, correlations: Dict[str, Any]) -> str:
        try:
            deployments = correlations.get("recent_deployments", [])
            logs = correlations.get("log_patterns", [])
            anomalies = correlations.get("metric_anomalies", [])
            
            # Rule-based root cause suggestion
            if deployments and len(deployments) > 0:
                return "Recent deployment likely caused the issue. Consider rollback or hotfix."
            
            if logs:
                error_patterns = [log.get("pattern") for log in logs]
                if "OutOfMemoryError" in error_patterns:
                    return "Memory leak or insufficient memory allocation detected."
                elif "ConnectionTimeoutException" in error_patterns:
                    return "Network connectivity or timeout issues detected."
                elif "DatabaseConnectionException" in error_patterns:
                    return "Database connectivity or performance issues detected."
            
            if anomalies:
                high_cpu = any(a.get("metric") == "cpu_usage" and a.get("current_value", 0) > 90 for a in anomalies)
                high_memory = any(a.get("metric") == "memory_usage" and a.get("current_value", 0) > 90 for a in anomalies)
                
                if high_cpu:
                    return "High CPU usage detected. Check for infinite loops or resource-intensive processes."
                elif high_memory:
                    return "High memory usage detected. Check for memory leaks or increase memory allocation."
            
            return "Unknown cause. Further investigation required."
            
        except Exception as e:
            logger.error(f"Failed to suggest root cause: {str(e)}")
            return "Unable to determine root cause."
    
    def _calculate_confidence(self, correlations: Dict[str, Any], correlation_score: float) -> float:
        try:
            # Base confidence from correlation score
            confidence = correlation_score
            
            # Boost confidence if we have strong indicators
            if correlations.get("recent_deployments"):
                confidence += 0.1
            
            if correlations.get("similar_incidents"):
                confidence += 0.1
            
            # Ensure confidence is between 0 and 1
            return min(confidence, 1.0)
            
        except Exception as e:
            logger.error(f"Failed to calculate confidence: {str(e)}")
            return 0.0
