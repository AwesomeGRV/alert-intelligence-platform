from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
import structlog
from datetime import datetime, timedelta

from .correlation_engine import CorrelationEngine
from .root_cause_rules import RootCauseAnalyzer, RootCauseRule, RootCauseType, ConfidenceLevel
from ..core.elasticsearch import es_client

logger = structlog.get_logger()

class CorrelationService:
    def __init__(self):
        self.correlation_engine = CorrelationEngine()
        self.root_cause_analyzer = RootCauseAnalyzer()
    
    async def analyze_incident_correlation(
        self, 
        cluster_id: str, 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Perform comprehensive correlation analysis for an incident
        """
        try:
            # Get incident alerts
            alerts = await self._get_incident_alerts(cluster_id, db)
            
            if not alerts:
                return {"error": "No alerts found for incident"}
            
            # Create alert cluster for analysis
            alert_cluster = self._create_alert_cluster(alerts)
            
            # Perform correlation analysis
            correlation_result = await self.correlation_engine.correlate_alerts_with_incidents(
                alert_cluster, db
            )
            
            # Enhance with additional insights
            enhanced_result = await self._enhance_correlation_result(
                correlation_result, alert_cluster, cluster_id
            )
            
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Failed to analyze incident correlation: {str(e)}")
            return {"error": f"Correlation analysis failed: {str(e)}"}
    
    async def get_correlation_insights(
        self, 
        time_range_hours: int = 24,
        services: List[str] = None
    ) -> Dict[str, Any]:
        """
        Get correlation insights across multiple incidents
        """
        try:
            # Get recent incidents
            incidents = await self._get_recent_incidents(time_range_hours, services)
            
            if not incidents:
                return {"insights": [], "summary": "No incidents found in time range"}
            
            insights = []
            correlation_patterns = {}
            
            for incident in incidents:
                # Analyze each incident
                incident_insights = await self._analyze_single_incident(incident)
                insights.append(incident_insights)
                
                # Track correlation patterns
                root_cause_type = incident_insights.get("root_cause_analysis", {}).get("root_cause_type")
                if root_cause_type:
                    correlation_patterns[root_cause_type] = correlation_patterns.get(root_cause_type, 0) + 1
            
            # Generate summary
            summary = self._generate_correlation_summary(insights, correlation_patterns)
            
            return {
                "insights": insights,
                "summary": summary,
                "correlation_patterns": correlation_patterns,
                "time_range_hours": time_range_hours,
                "total_incidents": len(incidents)
            }
            
        except Exception as e:
            logger.error(f"Failed to get correlation insights: {str(e)}")
            return {"error": f"Failed to get insights: {str(e)}"}
    
    async def predict_incident_risk(
        self, 
        alert_data: Dict[str, Any],
        historical_data: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Predict the risk level of an alert becoming an incident
        """
        try:
            # Analyze alert characteristics
            risk_factors = await self._analyze_risk_factors(alert_data)
            
            # Compare with historical patterns
            historical_risk = await self._analyze_historical_risk(alert_data, historical_data)
            
            # Calculate overall risk score
            risk_score = self._calculate_risk_score(risk_factors, historical_risk)
            
            # Determine risk level and recommendations
            risk_level = self._determine_risk_level(risk_score)
            recommendations = self._generate_risk_recommendations(risk_factors, risk_level)
            
            return {
                "risk_score": risk_score,
                "risk_level": risk_level,
                "risk_factors": risk_factors,
                "historical_comparison": historical_risk,
                "recommendations": recommendations,
                "prediction_confidence": self._calculate_prediction_confidence(risk_factors, historical_risk)
            }
            
        except Exception as e:
            logger.error(f"Failed to predict incident risk: {str(e)}")
            return {"error": f"Risk prediction failed: {str(e)}"}
    
    async def add_custom_correlation_rule(
        self, 
        rule_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Add a custom correlation rule
        """
        try:
            # Validate rule data
            validation_result = self._validate_rule_data(rule_data)
            if not validation_result["valid"]:
                return {"error": validation_result["errors"]}
            
            # Create rule object
            rule = RootCauseRule(
                name=rule_data["name"],
                pattern=rule_data["pattern"],
                root_cause_type=RootCauseType(rule_data["root_cause_type"]),
                confidence=ConfidenceLevel(rule_data["confidence"]),
                description=rule_data["description"],
                suggested_action=rule_data["suggested_action"],
                priority=rule_data.get("priority", 1)
            )
            
            # Add rule to analyzer
            success = self.root_cause_analyzer.add_custom_rule(rule)
            
            if success:
                return {
                    "message": f"Custom rule '{rule.name}' added successfully",
                    "rule_id": rule.name,
                    "rule_type": rule.root_cause_type.value,
                    "confidence": rule.confidence.value
                }
            else:
                return {"error": "Failed to add custom rule"}
            
        except Exception as e:
            logger.error(f"Failed to add custom correlation rule: {str(e)}")
            return {"error": f"Failed to add rule: {str(e)}"}
    
    async def get_correlation_rules(self) -> Dict[str, Any]:
        """
        Get all correlation rules and their statistics
        """
        try:
            rule_stats = self.root_cause_analyzer.get_rule_statistics()
            
            return {
                "statistics": rule_stats,
                "message": "Correlation rules retrieved successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to get correlation rules: {str(e)}")
            return {"error": f"Failed to get rules: {str(e)}"}
    
    async def _get_incident_alerts(self, cluster_id: str, db: AsyncSession) -> List[Dict[str, Any]]:
        """Get all alerts for an incident"""
        try:
            es_query = {
                "query": {"term": {"cluster_id": cluster_id}},
                "sort": [{"timestamp": {"order": "desc"}}],
                "size": 1000
            }
            
            response = await es_client.search("alerts", es_query)
            hits = response.get('hits', {}).get('hits', [])
            
            return [hit['_source'] for hit in hits]
            
        except Exception as e:
            logger.error(f"Failed to get incident alerts: {str(e)}")
            return []
    
    def _create_alert_cluster(self, alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create alert cluster for analysis"""
        if not alerts:
            return {}
        
        # Extract cluster information
        services = list(set(alert.get('service') for alert in alerts if alert.get('service')))
        severities = list(set(alert.get('severity') for alert in alerts if alert.get('severity')))
        
        return {
            "alerts": alerts,
            "services": services,
            "severities": severities,
            "alert_count": len(alerts),
            "latest_alert": alerts[0] if alerts else {},
            "time_range": {
                "start": min(alert.get('timestamp') for alert in alerts if alert.get('timestamp')),
                "end": max(alert.get('timestamp') for alert in alerts if alert.get('timestamp'))
            }
        }
    
    async def _enhance_correlation_result(
        self, 
        correlation_result: Dict[str, Any], 
        alert_cluster: Dict[str, Any], 
        cluster_id: str
    ) -> Dict[str, Any]:
        """Enhance correlation result with additional insights"""
        try:
            # Add timeline analysis
            timeline_analysis = self._analyze_timeline(alert_cluster)
            
            # Add impact assessment
            impact_assessment = self._assess_impact(alert_cluster, correlation_result)
            
            # Add prevention recommendations
            prevention_recommendations = self._generate_prevention_recommendations(
                correlation_result, alert_cluster
            )
            
            enhanced_result = correlation_result.copy()
            enhanced_result.update({
                "timeline_analysis": timeline_analysis,
                "impact_assessment": impact_assessment,
                "prevention_recommendations": prevention_recommendations,
                "cluster_id": cluster_id,
                "analysis_timestamp": datetime.utcnow().isoformat()
            })
            
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Failed to enhance correlation result: {str(e)}")
            return correlation_result
    
    def _analyze_timeline(self, alert_cluster: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze alert timeline patterns"""
        alerts = alert_cluster.get('alerts', [])
        if not alerts:
            return {}
        
        # Sort alerts by timestamp
        sorted_alerts = sorted(alerts, key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # Calculate timeline metrics
        first_alert = sorted_alerts[-1]
        latest_alert = sorted_alerts[0]
        
        time_span = datetime.utcnow() - datetime.fromisoformat(
            first_alert.get('timestamp', '').replace('Z', '+00:00')
        )
        
        return {
            "first_alert_time": first_alert.get('timestamp'),
            "latest_alert_time": latest_alert.get('timestamp'),
            "time_span_minutes": int(time_span.total_seconds() / 60),
            "alert_frequency": len(alerts) / max(1, time_span.total_seconds() / 3600),  # alerts per hour
            "escalation_pattern": self._detect_escalation_pattern(sorted_alerts)
        }
    
    def _detect_escalation_pattern(self, sorted_alerts: List[Dict[str, Any]]) -> str:
        """Detect escalation pattern in alerts"""
        if len(sorted_alerts) < 2:
            return "insufficient_data"
        
        # Check if severity is increasing
        severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
        
        recent_alerts = sorted_alerts[:5]  # Check last 5 alerts
        severity_trend = [severity_order.get(alert.get('severity', 'low'), 0) for alert in recent_alerts]
        
        if all(severity_trend[i] <= severity_trend[i+1] for i in range(len(severity_trend)-1)):
            return "escalating"
        elif all(severity_trend[i] >= severity_trend[i+1] for i in range(len(severity_trend)-1)):
            return "de_escalating"
        else:
            return "fluctuating"
    
    def _assess_impact(self, alert_cluster: Dict[str, Any], correlation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Assess the impact of the incident"""
        alerts = alert_cluster.get('alerts', [])
        services = alert_cluster.get('services', [])
        
        # Calculate impact metrics
        critical_alerts = len([a for a in alerts if a.get('severity') == 'critical'])
        high_alerts = len([a for a in alerts if a.get('severity') == 'high'])
        
        # Determine impact level
        if critical_alerts > 0:
            impact_level = "critical"
        elif high_alerts > 2:
            impact_level = "high"
        elif len(services) > 3:
            impact_level = "medium"
        else:
            impact_level = "low"
        
        return {
            "impact_level": impact_level,
            "affected_services": len(services),
            "critical_alerts": critical_alerts,
            "high_alerts": high_alerts,
            "business_impact": self._estimate_business_impact(alert_cluster, correlation_result)
        }
    
    def _estimate_business_impact(self, alert_cluster: Dict[str, Any], correlation_result: Dict[str, Any]) -> str:
        """Estimate business impact based on correlation results"""
        root_cause_type = correlation_result.get("root_cause_analysis", {}).get("root_cause_type")
        
        impact_mapping = {
            "deployment": "Medium - Recent deployment may affect user experience",
            "infrastructure": "High - Infrastructure issues can affect multiple services",
            "database": "High - Database issues can cause data integrity problems",
            "network": "Medium - Network issues may cause connectivity problems",
            "performance": "Medium - Performance issues may affect user experience",
            "security": "Critical - Security issues require immediate attention",
            "external_dependency": "Low - External dependency issues may have limited impact"
        }
        
        return impact_mapping.get(root_cause_type, "Unknown impact")
    
    def _generate_prevention_recommendations(
        self, 
        correlation_result: Dict[str, Any], 
        alert_cluster: Dict[str, Any]
    ) -> List[str]:
        """Generate prevention recommendations based on correlation analysis"""
        recommendations = []
        
        root_cause_type = correlation_result.get("root_cause_analysis", {}).get("root_cause_type")
        correlation_score = correlation_result.get("correlation_score", 0)
        
        # General recommendations based on correlation score
        if correlation_score > 0.8:
            recommendations.append("Strong correlation detected - implement preventive monitoring")
        elif correlation_score > 0.6:
            recommendations.append("Moderate correlation - review and improve monitoring")
        else:
            recommendations.append("Weak correlation - enhance data collection and analysis")
        
        # Specific recommendations based on root cause type
        if root_cause_type == "deployment":
            recommendations.extend([
                "Implement canary deployments",
                "Add deployment health checks",
                "Improve rollback procedures"
            ])
        elif root_cause_type == "infrastructure":
            recommendations.extend([
                "Implement infrastructure monitoring",
                "Add capacity planning",
                "Improve resource management"
            ])
        elif root_cause_type == "database":
            recommendations.extend([
                "Implement database monitoring",
                "Add query performance tracking",
                "Improve connection pooling"
            ])
        
        return recommendations
    
    async def _get_recent_incidents(self, time_range_hours: int, services: List[str] = None) -> List[Dict[str, Any]]:
        """Get recent incidents for analysis"""
        try:
            es_query = {
                "query": {
                    "bool": {
                        "must": [
                            {"range": {"created_at": {"gte": f"now-{time_range_hours}h"}}}
                        ]
                    }
                },
                "sort": [{"created_at": {"order": "desc"}}],
                "size": 50
            }
            
            if services:
                es_query["query"]["bool"]["must"].append({"terms": {"service": services}})
            
            response = await es_client.search("incidents", es_query)
            hits = response.get('hits', {}).get('hits', [])
            
            return [hit['_source'] for hit in hits]
            
        except Exception as e:
            logger.error(f"Failed to get recent incidents: {str(e)}")
            return []
    
    async def _analyze_single_incident(self, incident: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single incident for correlation insights"""
        return {
            "incident_id": incident.get("cluster_id"),
            "title": incident.get("title"),
            "severity": incident.get("severity"),
            "service": incident.get("service"),
            "created_at": incident.get("created_at"),
            "alert_count": incident.get("alert_count", 0),
            "root_cause_type": incident.get("suggested_root_cause", "unknown"),
            "resolution_time": incident.get("time_to_resolve"),
            "correlation_score": 0.0  # Would be calculated from actual correlation analysis
        }
    
    def _generate_correlation_summary(
        self, 
        insights: List[Dict[str, Any]], 
        patterns: Dict[str, int]
    ) -> Dict[str, Any]:
        """Generate summary of correlation insights"""
        total_incidents = len(insights)
        
        if total_incidents == 0:
            return {"message": "No incidents to analyze"}
        
        # Calculate statistics
        severity_distribution = {}
        for insight in insights:
            severity = insight.get("severity", "unknown")
            severity_distribution[severity] = severity_distribution.get(severity, 0) + 1
        
        # Find most common root cause
        most_common_cause = max(patterns.items(), key=lambda x: x[1]) if patterns else ("unknown", 0)
        
        return {
            "total_incidents": total_incidents,
            "severity_distribution": severity_distribution,
            "most_common_root_cause": {
                "type": most_common_cause[0],
                "count": most_common_cause[1],
                "percentage": round((most_common_cause[1] / total_incidents) * 100, 2)
            },
            "correlation_patterns": patterns
        }
    
    async def _analyze_risk_factors(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze risk factors for an alert"""
        risk_factors = {}
        
        # Severity risk
        severity = alert_data.get("severity", "low")
        severity_risk = {"critical": 0.9, "high": 0.7, "medium": 0.5, "low": 0.3, "info": 0.1}
        risk_factors["severity"] = severity_risk.get(severity, 0.3)
        
        # Service risk (based on historical noise)
        service = alert_data.get("service", "")
        # This would integrate with service noise scoring
        risk_factors["service"] = 0.5  # Default value
        
        # Time pattern risk
        timestamp = alert_data.get("timestamp")
        if timestamp:
            hour = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).hour
            # Higher risk during business hours (9-17)
            risk_factors["time_pattern"] = 0.7 if 9 <= hour <= 17 else 0.3
        else:
            risk_factors["time_pattern"] = 0.5
        
        return risk_factors
    
    async def _analyze_historical_risk(
        self, 
        alert_data: Dict[str, Any], 
        historical_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze historical risk patterns"""
        if not historical_data:
            return {"historical_risk": 0.5, "similar_incidents": 0}
        
        # Find similar historical alerts
        service = alert_data.get("service", "")
        severity = alert_data.get("severity", "")
        
        similar_alerts = [
            alert for alert in historical_data
            if alert.get("service") == service and alert.get("severity") == severity
        ]
        
        # Calculate historical risk based on similar alerts
        if len(similar_alerts) > 5:
            historical_risk = 0.8
        elif len(similar_alerts) > 2:
            historical_risk = 0.6
        else:
            historical_risk = 0.4
        
        return {
            "historical_risk": historical_risk,
            "similar_incidents": len(similar_alerts),
            "total_historical_alerts": len(historical_data)
        }
    
    def _calculate_risk_score(self, risk_factors: Dict[str, Any], historical_risk: Dict[str, Any]) -> float:
        """Calculate overall risk score"""
        # Weight different risk factors
        weights = {
            "severity": 0.4,
            "service": 0.2,
            "time_pattern": 0.2,
            "historical": 0.2
        }
        
        score = 0.0
        score += risk_factors.get("severity", 0.3) * weights["severity"]
        score += risk_factors.get("service", 0.5) * weights["service"]
        score += risk_factors.get("time_pattern", 0.5) * weights["time_pattern"]
        score += historical_risk.get("historical_risk", 0.5) * weights["historical"]
        
        return min(score, 1.0)
    
    def _determine_risk_level(self, risk_score: float) -> str:
        """Determine risk level based on score"""
        if risk_score >= 0.8:
            return "critical"
        elif risk_score >= 0.6:
            return "high"
        elif risk_score >= 0.4:
            return "medium"
        else:
            return "low"
    
    def _generate_risk_recommendations(
        self, 
        risk_factors: Dict[str, Any], 
        risk_level: str
    ) -> List[str]:
        """Generate risk-based recommendations"""
        recommendations = []
        
        if risk_level == "critical":
            recommendations.extend([
                "Immediate investigation required",
                "Escalate to on-call team",
                "Consider emergency procedures"
            ])
        elif risk_level == "high":
            recommendations.extend([
                "Investigate within 30 minutes",
                "Monitor closely for escalation",
                "Prepare contingency plans"
            ])
        elif risk_level == "medium":
            recommendations.extend([
                "Investigate within 2 hours",
                "Monitor for patterns",
                "Document findings"
            ])
        else:
            recommendations.extend([
                "Monitor for changes",
                "Investigate if patterns emerge",
                "Consider preventive measures"
            ])
        
        # Add specific recommendations based on risk factors
        if risk_factors.get("severity", 0) > 0.7:
            recommendations.append("Review alert severity thresholds")
        
        if risk_factors.get("service", 0) > 0.6:
            recommendations.append("Review service health and noise levels")
        
        return recommendations
    
    def _calculate_prediction_confidence(
        self, 
        risk_factors: Dict[str, Any], 
        historical_risk: Dict[str, Any]
    ) -> float:
        """Calculate confidence in risk prediction"""
        confidence = 0.5  # Base confidence
        
        # Increase confidence with more data
        if historical_risk.get("similar_incidents", 0) > 0:
            confidence += 0.2
        
        if len(risk_factors) >= 3:
            confidence += 0.1
        
        if historical_risk.get("total_historical_alerts", 0) > 10:
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def _validate_rule_data(self, rule_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate rule data"""
        errors = []
        
        required_fields = ["name", "pattern", "root_cause_type", "confidence", "description", "suggested_action"]
        
        for field in required_fields:
            if field not in rule_data:
                errors.append(f"Missing required field: {field}")
        
        # Validate pattern
        if "pattern" in rule_data:
            try:
                import re
                re.compile(rule_data["pattern"])
            except re.error as e:
                errors.append(f"Invalid regex pattern: {str(e)}")
        
        # Validate root_cause_type
        if "root_cause_type" in rule_data:
            try:
                RootCauseType(rule_data["root_cause_type"])
            except ValueError:
                errors.append(f"Invalid root_cause type: {rule_data['root_cause_type']}")
        
        # Validate confidence
        if "confidence" in rule_data:
            try:
                ConfidenceLevel(rule_data["confidence"])
            except ValueError:
                errors.append(f"Invalid confidence level: {rule_data['confidence']}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
