from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import uuid

class IncidentSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class IncidentStatus(str, Enum):
    ACTIVE = "active"
    INVESTIGATING = "investigating"
    IDENTIFIED = "identified"
    MONITORING = "monitoring"
    RESOLVED = "resolved"
    CLOSED = "closed"

class RootCauseType(str, Enum):
    DEPLOYMENT = "deployment"
    INFRASTRUCTURE = "infrastructure"
    CODE_BUG = "code_bug"
    CONFIGURATION = "configuration"
    EXTERNAL_DEPENDENCY = "external_dependency"
    PERFORMANCE = "performance"
    UNKNOWN = "unknown"

class Incident(BaseModel):
    cluster_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    severity: IncidentSeverity
    status: IncidentStatus = IncidentStatus.ACTIVE
    service: str
    affected_services: List[str] = Field(default_factory=list)
    alert_count: int = 0
    first_alert_time: datetime
    last_alert_time: datetime
    tags: List[str] = Field(default_factory=list)
    metrics_impact: Dict[str, Any] = Field(default_factory=dict)
    
    # Correlation data
    related_deployments: List[Dict[str, Any]] = Field(default_factory=list)
    correlated_logs: List[Dict[str, Any]] = Field(default_factory=list)
    suggested_root_cause: Optional[str] = None
    root_cause_type: Optional[RootCauseType] = None
    confidence_score: float = 0.0
    
    # Resolution data
    resolved_root_cause: Optional[str] = None
    fix_applied: Optional[str] = None
    resolution_time: Optional[datetime] = None
    time_to_resolve: Optional[int] = None  # in minutes
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    assigned_to: Optional[str] = None
    sla_breach: bool = False

class IncidentCreate(BaseModel):
    title: str
    description: str
    severity: IncidentSeverity
    service: str
    affected_services: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)

class IncidentUpdate(BaseModel):
    status: Optional[IncidentStatus] = None
    severity: Optional[IncidentSeverity] = None
    description: Optional[str] = None
    assigned_to: Optional[str] = None
    resolved_root_cause: Optional[str] = None
    fix_applied: Optional[str] = None

class IncidentCluster(BaseModel):
    cluster_id: str
    alerts: List[Dict[str, Any]]
    cluster_score: float
    similarity_threshold: float
    clustering_method: str
    created_at: datetime

class IncidentResponse(Incident):
    cluster_analysis: Optional[Dict[str, Any]] = None
    related_incidents: List[str] = Field(default_factory=list)
    noise_score: float = 0.0
    business_impact: Optional[str] = None

class IncidentSummary(BaseModel):
    incident_id: str
    title: str
    severity: IncidentSeverity
    status: IncidentStatus
    service: str
    alert_count: int
    duration_minutes: int
    assigned_to: Optional[str] = None
