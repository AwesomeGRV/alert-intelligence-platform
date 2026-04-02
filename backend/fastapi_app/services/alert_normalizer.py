from typing import Dict, Any, Optional
import hashlib
import structlog
from datetime import datetime

from ..models.alert import (
    NormalizedAlert, NewRelicAlert, PrometheusAlert, 
    CloudWatchAlert, PagerDutyAlert, AlertSource
)

logger = structlog.get_logger()

class AlertNormalizer:
    def __init__(self):
        self.source_parsers = {
            AlertSource.NEW_RELIC: self._parse_new_relic,
            AlertSource.PROMETHEUS: self._parse_prometheus,
            AlertSource.CLOUDWATCH: self._parse_cloudwatch,
            AlertSource.PAGERDUTY: self._parse_pagerduty,
        }
    
    async def normalize(self, raw_alert: Dict[str, Any]) -> NormalizedAlert:
        try:
            # Determine source
            source = self._determine_source(raw_alert)
            
            # Parse based on source
            if source in self.source_parsers:
                normalized = await self.source_parsers[source](raw_alert)
            else:
                normalized = await self._parse_generic(raw_alert, source)
            
            # Generate fingerprint for deduplication
            normalized.fingerprint = self._generate_fingerprint(normalized)
            
            # Set timestamps
            if not normalized.first_seen:
                normalized.first_seen = normalized.timestamp
            normalized.last_seen = normalized.timestamp
            
            logger.info(f"Normalized alert from {source}: {normalized.alert_id}")
            return normalized
            
        except Exception as e:
            logger.error(f"Failed to normalize alert: {str(e)}")
            raise
    
    def _determine_source(self, raw_alert: Dict[str, Any]) -> AlertSource:
        # Check for source-specific fields
        if 'new_relic_account_id' in raw_alert or 'new_relic' in raw_alert.get('source', '').lower():
            return AlertSource.NEW_RELIC
        elif 'prometheus_labels' in raw_alert or 'prometheus' in raw_alert.get('source', '').lower():
            return AlertSource.PROMETHEUS
        elif 'aws_account_id' in raw_alert or 'cloudwatch' in raw_alert.get('source', '').lower():
            return AlertSource.CLOUDWATCH
        elif 'pagerduty_incident_key' in raw_alert or 'pagerduty' in raw_alert.get('source', '').lower():
            return AlertSource.PAGERDUTY
        else:
            return AlertSource.CUSTOM
    
    async def _parse_new_relic(self, raw_alert: Dict[str, Any]) -> NormalizedAlert:
        return NormalizedAlert(
            source=AlertSource.NEW_RELIC,
            service=raw_alert.get('application_name', raw_alert.get('service', 'unknown')),
            severity=self._normalize_severity(raw_alert.get('severity', 'medium')),
            timestamp=self._parse_timestamp(raw_alert.get('timestamp')),
            description=raw_alert.get('description', raw_alert.get('message', '')),
            tags=raw_alert.get('tags', []),
            metrics_snapshot=raw_alert.get('metrics', {}),
            raw_data=raw_alert
        )
    
    async def _parse_prometheus(self, raw_alert: Dict[str, Any]) -> NormalizedAlert:
        labels = raw_alert.get('prometheus_labels', raw_alert.get('labels', {}))
        
        return NormalizedAlert(
            source=AlertSource.PROMETHEUS,
            service=labels.get('service', labels.get('job', 'unknown')),
            severity=self._normalize_severity(raw_alert.get('severity', 'medium')),
            timestamp=self._parse_timestamp(raw_alert.get('timestamp')),
            description=raw_alert.get('description', raw_alert.get('summary', '')),
            tags=list(labels.values()),
            metrics_snapshot={
                'value': raw_alert.get('value'),
                'labels': labels
            },
            raw_data=raw_alert
        )
    
    async def _parse_cloudwatch(self, raw_alert: Dict[str, Any]) -> NormalizedAlert:
        return NormalizedAlert(
            source=AlertSource.CLOUDWATCH,
            service=raw_alert.get('service', raw_alert.get('trigger_namespace', 'unknown')),
            severity=self._normalize_severity(raw_alert.get('severity', 'medium')),
            timestamp=self._parse_timestamp(raw_alert.get('timestamp')),
            description=raw_alert.get('description', raw_alert.get('message', '')),
            tags=raw_alert.get('tags', []),
            metrics_snapshot={
                'threshold': raw_alert.get('threshold'),
                'value': raw_alert.get('value'),
                'metric_name': raw_alert.get('cloudwatch_metric_name')
            },
            raw_data=raw_alert
        )
    
    async def _parse_pagerduty(self, raw_alert: Dict[str, Any]) -> NormalizedAlert:
        return NormalizedAlert(
            source=AlertSource.PAGERDUTY,
            service=raw_alert.get('service', raw_alert.get('summary', 'unknown')),
            severity=self._normalize_severity(raw_alert.get('severity', 'medium')),
            timestamp=self._parse_timestamp(raw_alert.get('timestamp')),
            description=raw_alert.get('description', raw_alert.get('summary', '')),
            tags=raw_alert.get('tags', []),
            metrics_snapshot=raw_alert.get('details', {}),
            raw_data=raw_alert
        )
    
    async def _parse_generic(self, raw_alert: Dict[str, Any], source: AlertSource) -> NormalizedAlert:
        return NormalizedAlert(
            source=source,
            service=raw_alert.get('service', 'unknown'),
            severity=self._normalize_severity(raw_alert.get('severity', 'medium')),
            timestamp=self._parse_timestamp(raw_alert.get('timestamp')),
            description=raw_alert.get('description', raw_alert.get('message', '')),
            tags=raw_alert.get('tags', []),
            metrics_snapshot=raw_alert.get('metrics', {}),
            raw_data=raw_alert
        )
    
    def _normalize_severity(self, severity: str) -> str:
        severity_mapping = {
            'critical': 'critical',
            'crit': 'critical',
            'high': 'high',
            'warning': 'high',
            'warn': 'high',
            'medium': 'medium',
            'info': 'low',
            'low': 'low',
            'debug': 'info'
        }
        
        return severity_mapping.get(severity.lower(), 'medium')
    
    def _parse_timestamp(self, timestamp: Any) -> datetime:
        if timestamp is None:
            return datetime.utcnow()
        
        if isinstance(timestamp, datetime):
            return timestamp
        
        if isinstance(timestamp, str):
            try:
                # Try ISO format first
                return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except ValueError:
                try:
                    # Try Unix timestamp
                    return datetime.fromtimestamp(float(timestamp))
                except ValueError:
                    logger.warning(f"Could not parse timestamp: {timestamp}")
                    return datetime.utcnow()
        
        if isinstance(timestamp, (int, float)):
            return datetime.fromtimestamp(timestamp)
        
        return datetime.utcnow()
    
    def _generate_fingerprint(self, alert: NormalizedAlert) -> str:
        # Create a fingerprint based on service, severity, and description pattern
        fingerprint_data = {
            'source': alert.source,
            'service': alert.service,
            'severity': alert.severity,
            'description_pattern': self._extract_description_pattern(alert.description)
        }
        
        fingerprint_str = str(sorted(fingerprint_data.items()))
        return hashlib.md5(fingerprint_str.encode()).hexdigest()
    
    def _extract_description_pattern(self, description: str) -> str:
        # Extract key pattern from description (remove numbers, specific values)
        import re
        pattern = re.sub(r'\d+', 'NUM', description.lower())
        pattern = re.sub(r'\b\d+\.\d+\b', 'FLOAT', pattern)
        pattern = re.sub(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', 'UUID', pattern)
        return pattern
