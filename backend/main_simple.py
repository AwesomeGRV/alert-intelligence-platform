from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import asyncio
from collections import defaultdict

# Simple in-memory storage for demo
alerts_storage = []
incidents_storage = []
services_storage = defaultdict(dict)

# Simple models
class Alert(BaseModel):
    id: str = None
    source: str
    service: str
    severity: str
    description: str
    timestamp: str = None
    tags: List[str] = []

class Incident(BaseModel):
    id: str = None
    title: str
    description: str
    severity: str
    service: str
    status: str = "open"
    created_at: str = None

class Service(BaseModel):
    name: str
    health_score: float
    noise_score: float
    alert_count: int

# Create FastAPI app
app = FastAPI(
    title="Alert Intelligence Platform",
    description="Production-ready alert ingestion and intelligence platform",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "alert-intelligence-platform", "timestamp": datetime.utcnow().isoformat()}

@app.get("/")
async def root():
    return {"message": "Alert Intelligence Platform API", "version": "1.0.0"}

# Alert endpoints
@app.post("/api/v1/alerts")
async def ingest_alert(alert: Alert):
    alert.id = str(uuid.uuid4())
    alert.timestamp = datetime.utcnow().isoformat()
    alerts_storage.append(alert.dict())
    
    # Update service metrics
    services_storage[alert.service]['alert_count'] = services_storage[alert.service].get('alert_count', 0) + 1
    
    return {"message": "Alert ingested successfully", "alert_id": alert.id}

@app.get("/api/v1/alerts")
async def get_alerts():
    return {"alerts": alerts_storage, "total": len(alerts_storage)}

@app.get("/api/v1/alerts/{alert_id}")
async def get_alert(alert_id: str):
    alert = next((a for a in alerts_storage if a.get('id') == alert_id), None)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert

@app.delete("/api/v1/alerts/{alert_id}")
async def delete_alert(alert_id: str):
    global alerts_storage
    alerts_storage = [a for a in alerts_storage if a.get('id') != alert_id]
    return {"message": "Alert deleted successfully"}

# Incident endpoints
@app.post("/api/v1/incidents")
async def create_incident(incident: Incident):
    incident.id = str(uuid.uuid4())
    incident.created_at = datetime.utcnow().isoformat()
    incidents_storage.append(incident.dict())
    return {"message": "Incident created successfully", "incident_id": incident.id}

@app.get("/api/v1/incidents")
async def get_incidents():
    return {"incidents": incidents_storage, "total": len(incidents_storage)}

@app.get("/api/v1/incidents/{incident_id}")
async def get_incident(incident_id: str):
    incident = next((i for i in incidents_storage if i.get('id') == incident_id), None)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident

# Dashboard endpoints
@app.get("/api/v1/dashboard/overview")
async def get_dashboard_overview():
    total_alerts = len(alerts_storage)
    total_incidents = len(incidents_storage)
    
    # Calculate severity distribution
    severity_counts = defaultdict(int)
    for alert in alerts_storage:
        severity_counts[alert['severity']] += 1
    
    # Calculate service distribution
    service_counts = defaultdict(int)
    for alert in alerts_storage:
        service_counts[alert['service']] += 1
    
    return {
        "total_alerts": total_alerts,
        "total_incidents": total_incidents,
        "severity_distribution": dict(severity_counts),
        "service_distribution": dict(service_counts),
        "recent_alerts": alerts_storage[-10:] if alerts_storage else [],
        "active_incidents": [i for i in incidents_storage if i['status'] == 'open']
    }

@app.get("/api/v1/dashboard/services")
async def get_services():
    services = []
    for service_name, data in services_storage.items():
        services.append({
            "name": service_name,
            "health_score": 0.85,  # Mock health score
            "noise_score": 0.3,    # Mock noise score
            "alert_count": data.get('alert_count', 0)
        })
    
    return {"services": services}

# Sample data endpoints
@app.post("/api/v1/sample-data")
async def create_sample_data():
    # Sample alerts
    sample_alerts = [
        {
            "id": str(uuid.uuid4()),
            "source": "prometheus",
            "service": "api-gateway",
            "severity": "high",
            "description": "High error rate detected",
            "timestamp": datetime.utcnow().isoformat(),
            "tags": ["error", "api", "gateway"]
        },
        {
            "id": str(uuid.uuid4()),
            "source": "new-relic",
            "service": "database",
            "severity": "critical",
            "description": "Database connection timeout",
            "timestamp": datetime.utcnow().isoformat(),
            "tags": ["database", "timeout", "critical"]
        },
        {
            "id": str(uuid.uuid4()),
            "source": "cloudwatch",
            "service": "auth-service",
            "severity": "medium",
            "description": "High memory usage",
            "timestamp": datetime.utcnow().isoformat(),
            "tags": ["memory", "auth", "warning"]
        }
    ]
    
    alerts_storage.extend(sample_alerts)
    
    # Sample incidents
    sample_incidents = [
        {
            "id": str(uuid.uuid4()),
            "title": "API Gateway Performance Issues",
            "description": "Multiple alerts indicating performance degradation in API gateway",
            "severity": "high",
            "service": "api-gateway",
            "status": "open",
            "created_at": datetime.utcnow().isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Database Connectivity Problems",
            "description": "Database experiencing connection timeouts and slow queries",
            "severity": "critical",
            "service": "database",
            "status": "investigating",
            "created_at": datetime.utcnow().isoformat()
        }
    ]
    
    incidents_storage.extend(sample_incidents)
    
    return {"message": "Sample data created successfully"}

if __name__ == "__main__":
    import uvicorn
    print("Starting Alert Intelligence Platform...")
    print("Backend API: http://localhost:8000")
    print("API Documentation: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
