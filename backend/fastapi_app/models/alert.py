from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import uuid

class AlertSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class AlertSource(str, Enum):
    NEW_RELIC = "new_relic"
    PROMETHEUS = "prometheus"
    CLOUDWATCH = "cloudwatch"
    PAGERDUTY = "pagerduty"
    DATADOG = "datadog"
    CUSTOM = "custom"

class AlertStatus(str, Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"

class BaseAlert(BaseModel):
    alert_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: AlertSource
    service: str
    severity: AlertSeverity
    timestamp: datetime
    tags: List[str] = Field(default_factory=list)
    description: str
    metrics_snapshot: Dict[str, Any] = Field(default_factory=dict)
    status: AlertStatus = AlertStatus.ACTIVE
    
    @validator('timestamp', pre=True)
    def parse_timestamp(cls, v):
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace('Z', '+00:00'))
        return v

class NewRelicAlert(BaseAlert):
    source: AlertSource = AlertSource.NEW_RELIC
    new_relic_account_id: Optional[str] = None
    new_relic_policy_name: Optional[str] = None
    new_relic_condition_name: Optional[str] = None

class PrometheusAlert(BaseAlert):
    source: AlertSource = AlertSource.PROMETHEUS
    prometheus_labels: Dict[str, str] = Field(default_factory=dict)
    prometheus_fingerprint: Optional[str] = None
    prometheus_generator_url: Optional[str] = None

class CloudWatchAlert(BaseAlert):
    source: AlertSource = AlertSource.CLOUDWATCH
    aws_account_id: Optional[str] = None
    aws_region: Optional[str] = None
    cloudwatch_alarm_name: Optional[str] = None
    cloudwatch_metric_name: Optional[str] = None

class PagerDutyAlert(BaseAlert):
    source: AlertSource = AlertSource.PAGERDUTY
    pagerduty_incident_key: Optional[str] = None
    pagerduty_service_id: Optional[str] = None
    pagerduty_escalation_policy: Optional[str] = None

class NormalizedAlert(BaseAlert):
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    fingerprint: Optional[str] = None
    cluster_id: Optional[str] = None
    dedup_count: int = 0
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None

class AlertCreate(BaseModel):
    source: AlertSource
    service: str
    severity: AlertSeverity
    description: str
    tags: List[str] = Field(default_factory=list)
    metrics_snapshot: Dict[str, Any] = Field(default_factory=dict)
    raw_data: Dict[str, Any] = Field(default_factory=dict)

class AlertUpdate(BaseModel):
    severity: Optional[AlertSeverity] = None
    status: Optional[AlertStatus] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None

class AlertResponse(NormalizedAlert):
    created_at: datetime
    updated_at: datetime
