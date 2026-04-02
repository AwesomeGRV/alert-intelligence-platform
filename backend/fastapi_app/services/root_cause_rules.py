from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import structlog
import re
from dataclasses import dataclass
from enum import Enum

logger = structlog.get_logger()

class RootCauseType(str, Enum):
    DEPLOYMENT = "deployment"
    INFRASTRUCTURE = "infrastructure"
    CODE_BUG = "code_bug"
    CONFIGURATION = "configuration"
    EXTERNAL_DEPENDENCY = "external_dependency"
    PERFORMANCE = "performance"
    NETWORK = "network"
    DATABASE = "database"
    SECURITY = "security"
    UNKNOWN = "unknown"

class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class RootCauseRule:
    name: str
    pattern: str
    root_cause_type: RootCauseType
    confidence: ConfidenceLevel
    description: str
    suggested_action: str
    priority: int = 1  # Lower number = higher priority
    
@dataclass
class RootCauseAnalysis:
    root_cause_type: RootCauseType
    confidence: ConfidenceLevel
    description: str
    suggested_action: str
    supporting_evidence: List[str]
    related_rules: List[str]
    confidence_score: float

class RootCauseAnalyzer:
    def __init__(self):
        self.rules = self._initialize_rules()
        self.logger = structlog.get_logger()
    
    def _initialize_rules(self) -> List[RootCauseRule]:
        """Initialize comprehensive rule-based root cause analysis rules"""
        rules = [
            # Deployment-related rules
            RootCauseRule(
                name="recent_deployment_correlation",
                pattern=r"deployment|deploy|version|commit|release",
                root_cause_type=RootCauseType.DEPLOYMENT,
                confidence=ConfidenceLevel.HIGH,
                description="Recent deployment likely caused the issue",
                suggested_action="Consider rollback or hotfix. Review deployment logs and recent changes.",
                priority=1
            ),
            
            # Infrastructure rules
            RootCauseRule(
                name="high_cpu_usage",
                pattern=r"cpu.*high|high.*cpu|cpu.*overload|cpu.*exhausted",
                root_cause_type=RootCauseType.INFRASTRUCTURE,
                confidence=ConfidenceLevel.HIGH,
                description="High CPU usage detected",
                suggested_action="Scale horizontally or optimize code. Check for infinite loops or resource-intensive processes.",
                priority=2
            ),
            
            RootCauseRule(
                name="high_memory_usage",
                pattern=r"memory.*high|high.*memory|out.*of.*memory|memory.*leak",
                root_cause_type=RootCauseType.INFRASTRUCTURE,
                confidence=ConfidenceLevel.HIGH,
                description="Memory exhaustion or leak detected",
                suggested_action="Increase memory allocation or fix memory leaks. Check for memory-intensive operations.",
                priority=2
            ),
            
            RootCauseRule(
                name="disk_space_exhausted",
                pattern=r"disk.*full|no.*space|insufficient.*disk|disk.*exhausted",
                root_cause_type=RootCauseType.INFRASTRUCTURE,
                confidence=ConfidenceLevel.HIGH,
                description="Disk space exhaustion",
                suggested_action="Clean up disk space or increase storage. Check log rotation and temporary files.",
                priority=1
            ),
            
            # Database rules
            RootCauseRule(
                name="database_connection_timeout",
                pattern=r"database.*timeout|connection.*timeout|db.*timeout",
                root_cause_type=RootCauseType.DATABASE,
                confidence=ConfidenceLevel.HIGH,
                description="Database connection timeout",
                suggested_action="Check database performance, connection pool, and network connectivity. Optimize queries.",
                priority=2
            ),
            
            RootCauseRule(
                name="database_deadlock",
                pattern=r"deadlock|lock.*timeout|transaction.*deadlock",
                root_cause_type=RootCauseType.DATABASE,
                confidence=ConfidenceLevel.HIGH,
                description="Database deadlock detected",
                suggested_action="Review transaction ordering and optimize database queries. Consider shorter transactions.",
                priority=1
            ),
            
            RootCauseRule(
                name="slow_database_queries",
                pattern=r"slow.*query|query.*slow|db.*slow|database.*slow",
                root_cause_type=RootCauseType.DATABASE,
                confidence=ConfidenceLevel.MEDIUM,
                description="Slow database queries detected",
                suggested_action="Optimize database queries, add indexes, or consider query caching.",
                priority=3
            ),
            
            # Network rules
            RootCauseRule(
                name="network_timeout",
                pattern=r"network.*timeout|connection.*timeout|timeout.*network",
                root_cause_type=RootCauseType.NETWORK,
                confidence=ConfidenceLevel.HIGH,
                description="Network connectivity issues",
                suggested_action="Check network connectivity, firewall rules, and service availability.",
                priority=2
            ),
            
            RootCauseRule(
                name="dns_resolution_failure",
                pattern=r"dns.*fail|name.*resolution|host.*not.*found",
                root_cause_type=RootCauseType.NETWORK,
                confidence=ConfidenceLevel.HIGH,
                description="DNS resolution failure",
                suggested_action="Check DNS configuration and network connectivity to DNS servers.",
                priority=2
            ),
            
            # Code/Configuration rules
            RootCauseRule(
                name="null_pointer_exception",
                pattern=r"null.*pointer|nullpointer|null.*exception",
                root_cause_type=RootCauseType.CODE_BUG,
                confidence=ConfidenceLevel.HIGH,
                description="Null pointer exception in code",
                suggested_action="Review code for null checks and proper error handling. Add null safety checks.",
                priority=2
            ),
            
            RootCauseRule(
                name="configuration_error",
                pattern=r"config.*error|configuration.*error|invalid.*config",
                root_cause_type=RootCauseType.CONFIGURATION,
                confidence=ConfidenceLevel.HIGH,
                description="Configuration error detected",
                suggested_action="Review and fix configuration settings. Validate configuration files.",
                priority=1
            ),
            
            # Performance rules
            RootCauseRule(
                name="response_time_high",
                pattern=r"response.*time.*high|slow.*response|latency.*high",
                root_cause_type=RootCauseType.PERFORMANCE,
                confidence=ConfidenceLevel.MEDIUM,
                description="High response time detected",
                suggested_action="Optimize application performance, check for bottlenecks, and consider caching.",
                priority=3
            ),
            
            RootCauseRule(
                name="throughput_degradation",
                pattern=r"throughput.*low|low.*throughput|performance.*degradation",
                root_cause_type=RootCauseType.PERFORMANCE,
                confidence=ConfidenceLevel.MEDIUM,
                description="Performance degradation detected",
                suggested_action="Investigate performance bottlenecks and optimize resource utilization.",
                priority=3
            ),
            
            # External dependency rules
            RootCauseRule(
                name="external_api_failure",
                pattern=r"api.*fail|external.*fail|third.*party.*fail",
                root_cause_type=RootCauseType.EXTERNAL_DEPENDENCY,
                confidence=ConfidenceLevel.HIGH,
                description="External API or service failure",
                suggested_action="Check external service status and implement circuit breakers. Consider fallback mechanisms.",
                priority=2
            ),
            
            RootCauseRule(
                name="rate_limit_exceeded",
                pattern=r"rate.*limit|too.*many.*requests|quota.*exceeded",
                root_cause_type=RootCauseType.EXTERNAL_DEPENDENCY,
                confidence=ConfidenceLevel.HIGH,
                description="Rate limit or quota exceeded",
                suggested_action="Implement rate limiting and request throttling. Check API quotas.",
                priority=2
            ),
            
            # Security rules
            RootCauseRule(
                name="authentication_failure",
                pattern=r"auth.*fail|authentication.*fail|login.*fail",
                root_cause_type=RootCauseType.SECURITY,
                confidence=ConfidenceLevel.MEDIUM,
                description="Authentication failure",
                suggested_action="Check authentication configuration and credentials. Review security logs.",
                priority=3
            ),
            
            RootCauseRule(
                name="authorization_failure",
                pattern=r"access.*denied|permission.*denied|unauthorized",
                root_cause_type=RootCauseType.SECURITY,
                confidence=ConfidenceLevel.MEDIUM,
                description="Authorization failure",
                suggested_action="Review user permissions and access controls. Check role-based access configuration.",
                priority=3
            )
        ]
        
        return sorted(rules, key=lambda x: x.priority)
    
    async def analyze_root_cause(
        self, 
        alert_cluster: Dict[str, Any],
        correlations: Dict[str, Any],
        logs: List[Dict[str, Any]] = None,
        metrics: List[Dict[str, Any]] = None
    ) -> RootCauseAnalysis:
        """
        Analyze alerts and correlations to determine root cause using rule-based approach
        """
        try:
            # Collect evidence from different sources
            evidence = self._collect_evidence(alert_cluster, correlations, logs, metrics)
            
            # Apply rules to determine root cause
            matched_rules = self._apply_rules(evidence)
            
            # Determine most likely root cause
            root_cause = self._determine_root_cause(matched_rules, evidence)
            
            return root_cause
            
        except Exception as e:
            self.logger.error(f"Failed to analyze root cause: {str(e)}")
            return RootCauseAnalysis(
                root_cause_type=RootCauseType.UNKNOWN,
                confidence=ConfidenceLevel.LOW,
                description="Unable to determine root cause due to analysis error",
                suggested_action="Manual investigation required",
                supporting_evidence=[],
                related_rules=[],
                confidence_score=0.0
            )
    
    def _collect_evidence(
        self, 
        alert_cluster: Dict[str, Any],
        correlations: Dict[str, Any],
        logs: List[Dict[str, Any]] = None,
        metrics: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Collect evidence from various sources for analysis"""
        evidence = {
            "alerts": alert_cluster.get("latest_alert", {}),
            "services": alert_cluster.get("services", []),
            "severities": alert_cluster.get("severities", []),
            "descriptions": [],
            "tags": [],
            "recent_deployments": correlations.get("recent_deployments", []),
            "log_patterns": correlations.get("log_patterns", []),
            "metric_anomalies": correlations.get("metric_anomalies", []),
            "similar_incidents": correlations.get("similar_incidents", []),
            "service_dependencies": correlations.get("service_dependencies", {})
        }
        
        # Collect alert descriptions and tags
        for alert in alert_cluster.get("alerts", []):
            if alert.get("description"):
                evidence["descriptions"].append(alert["description"])
            if alert.get("tags"):
                evidence["tags"].extend(alert["tags"])
        
        # Add log evidence
        if logs:
            evidence["log_entries"] = logs
            evidence["log_messages"] = [log.get("message", "") for log in logs]
            evidence["log_levels"] = [log.get("level", "") for log in logs]
        
        # Add metric evidence
        if metrics:
            evidence["metric_data"] = metrics
            evidence["metric_names"] = [metric.get("metric", "") for metric in metrics]
            evidence["metric_values"] = [metric.get("current_value", 0) for metric in metrics]
        
        return evidence
    
    def _apply_rules(self, evidence: Dict[str, Any]) -> List[Tuple[RootCauseRule, float]]:
        """Apply rules to evidence and return matched rules with scores"""
        matched_rules = []
        
        # Combine all text evidence for pattern matching
        text_evidence = " ".join([
            " ".join(evidence.get("descriptions", [])),
            " ".join(evidence.get("tags", [])),
            " ".join([log.get("message", "") for log in evidence.get("log_patterns", [])]),
            " ".join([metric.get("metric", "") for metric in evidence.get("metric_anomalies", [])])
        ]).lower()
        
        for rule in self.rules:
            # Check if rule pattern matches evidence
            pattern_matches = bool(re.search(rule.pattern, text_evidence, re.IGNORECASE))
            
            if pattern_matches:
                # Calculate rule score based on evidence strength
                rule_score = self._calculate_rule_score(rule, evidence)
                matched_rules.append((rule, rule_score))
        
        # Sort by score (descending) and priority
        matched_rules.sort(key=lambda x: (-x[1], x[0].priority))
        
        return matched_rules
    
    def _calculate_rule_score(self, rule: RootCauseRule, evidence: Dict[str, Any]) -> float:
        """Calculate confidence score for a matched rule"""
        base_score = 0.5  # Base score for pattern match
        
        # Boost score based on confidence level
        confidence_boost = {
            ConfidenceLevel.HIGH: 0.3,
            ConfidenceLevel.MEDIUM: 0.2,
            ConfidenceLevel.LOW: 0.1
        }
        base_score += confidence_boost.get(rule.confidence, 0.1)
        
        # Boost score based on supporting evidence
        evidence_boost = 0.0
        
        # Check for recent deployments
        if rule.root_cause_type == RootCauseType.DEPLOYMENT and evidence.get("recent_deployments"):
            evidence_boost += 0.2
        
        # Check for log patterns
        if evidence.get("log_patterns"):
            evidence_boost += 0.1
        
        # Check for metric anomalies
        if evidence.get("metric_anomalies"):
            evidence_boost += 0.1
        
        # Check for similar incidents
        if evidence.get("similar_incidents"):
            evidence_boost += 0.1
        
        return min(base_score + evidence_boost, 1.0)
    
    def _determine_root_cause(
        self, 
        matched_rules: List[Tuple[RootCauseRule, float]], 
        evidence: Dict[str, Any]
    ) -> RootCauseAnalysis:
        """Determine the most likely root cause from matched rules"""
        
        if not matched_rules:
            return RootCauseAnalysis(
                root_cause_type=RootCauseType.UNKNOWN,
                confidence=ConfidenceLevel.LOW,
                description="No specific root cause patterns detected",
                suggested_action="Manual investigation required. Review all available logs and metrics.",
                supporting_evidence=["No rule matches found"],
                related_rules=[],
                confidence_score=0.0
            )
        
        # Get the highest scoring rule
        best_rule, best_score = matched_rules[0]
        
        # Collect supporting evidence
        supporting_evidence = []
        related_rules = [best_rule.name]
        
        # Add evidence from different sources
        if evidence.get("recent_deployments") and best_rule.root_cause_type == RootCauseType.DEPLOYMENT:
            supporting_evidence.append(f"Recent deployments found: {len(evidence['recent_deployments'])}")
        
        if evidence.get("log_patterns"):
            supporting_evidence.append(f"Log patterns detected: {len(evidence['log_patterns'])}")
        
        if evidence.get("metric_anomalies"):
            supporting_evidence.append(f"Metric anomalies detected: {len(evidence['metric_anomalies'])}")
        
        if evidence.get("similar_incidents"):
            supporting_evidence.append(f"Similar historical incidents: {len(evidence['similar_incidents'])}")
        
        # Determine confidence level based on score
        if best_score >= 0.8:
            confidence = ConfidenceLevel.HIGH
        elif best_score >= 0.6:
            confidence = ConfidenceLevel.MEDIUM
        else:
            confidence = ConfidenceLevel.LOW
        
        return RootCauseAnalysis(
            root_cause_type=best_rule.root_cause_type,
            confidence=confidence,
            description=best_rule.description,
            suggested_action=best_rule.suggested_action,
            supporting_evidence=supporting_evidence,
            related_rules=related_rules,
            confidence_score=best_score
        )
    
    def get_rule_statistics(self) -> Dict[str, Any]:
        """Get statistics about rule usage and effectiveness"""
        rule_stats = {
            "total_rules": len(self.rules),
            "rules_by_type": {},
            "rules_by_confidence": {},
            "rules_by_priority": {}
        }
        
        for rule in self.rules:
            # Count by type
            rule_type = rule.root_cause_type.value
            rule_stats["rules_by_type"][rule_type] = rule_stats["rules_by_type"].get(rule_type, 0) + 1
            
            # Count by confidence
            confidence = rule.confidence.value
            rule_stats["rules_by_confidence"][confidence] = rule_stats["rules_by_confidence"].get(confidence, 0) + 1
            
            # Count by priority
            priority = rule.priority
            rule_stats["rules_by_priority"][priority] = rule_stats["rules_by_priority"].get(priority, 0) + 1
        
        return rule_stats
    
    def add_custom_rule(self, rule: RootCauseRule) -> bool:
        """Add a custom rule to the analyzer"""
        try:
            # Validate rule pattern
            re.compile(rule.pattern)
            
            # Add to rules list
            self.rules.append(rule)
            
            # Re-sort rules by priority
            self.rules.sort(key=lambda x: x.priority)
            
            self.logger.info(f"Added custom rule: {rule.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add custom rule {rule.name}: {str(e)}")
            return False
    
    def remove_rule(self, rule_name: str) -> bool:
        """Remove a rule by name"""
        try:
            original_count = len(self.rules)
            self.rules = [rule for rule in self.rules if rule.name != rule_name]
            
            if len(self.rules) < original_count:
                self.logger.info(f"Removed rule: {rule_name}")
                return True
            else:
                self.logger.warning(f"Rule not found: {rule_name}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to remove rule {rule_name}: {str(e)}")
            return False
