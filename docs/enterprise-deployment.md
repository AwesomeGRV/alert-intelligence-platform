# Enterprise Deployment Guide

## Overview

This guide covers enterprise-grade deployment of the Alert Intelligence Platform with production-ready features including high availability, security, monitoring, and scalability.

## Architecture

### Production Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Load Balancer Layer                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Nginx     │  │   HAProxy   │  │   Envoy     │        │
│  │ (Termination)│  │ (Load       │  │ (Service    │        │
│  │             │  │  Balancing) │  │  Mesh)     │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                    Application Layer                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   API       │  │   Workers   │  │   ChatOps   │        │
│  │  Servers    │  │   Pool      │  │   Bots      │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                    Data Layer                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ PostgreSQL  │  │Elasticsearch │  │    Redis    │        │
│  │ (Primary)   │  │ (Search)    │  │  (Cache)    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ PostgreSQL  │  │    Kafka    │  │  Prometheus │        │
│  │ (Replica)   │  │ (Events)    │  │(Metrics)    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

## Security

### Authentication & Authorization

#### JWT-Based Authentication
```python
# Configuration
JWT_SECRET_KEY = "your-secret-key"
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30
JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7

# Role-based access control (RBAC)
ROLES = {
    "admin": ["alerts:read", "alerts:write", "incidents:read", "incidents:write", "system:configure"],
    "operator": ["alerts:read", "alerts:write", "incidents:read", "incidents:write"],
    "viewer": ["alerts:read", "incidents:read"],
    "api_user": ["alerts:write"]
}
```

#### API Key Authentication
```python
# API Key Management
API_KEYS = {
    "prod-api-key": {
        "user_id": "api-user-prod",
        "permissions": ["alerts:write", "incidents:read"],
        "rate_limit": 1000  # requests per hour
    }
}
```

### Security Middleware

#### Request Validation
- IP whitelisting/blacklisting
- Rate limiting per user/IP
- Request size limits
- Header validation
- SQL injection prevention
- XSS protection

#### Security Headers
```python
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'",
    "Referrer-Policy": "strict-origin-when-cross-origin"
}
```

### Network Security

#### TLS Configuration
```nginx
server {
    listen 443 ssl http2;
    server_name alert-intelligence.company.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
    
    # HSTS
    add_header Strict-Transport-Security "max-age=63072000" always;
}
```

#### Firewall Rules
```bash
# Allow only necessary ports
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw allow 9090/tcp  # Prometheus
ufw allow 3001/tcp  # Grafana
```

## High Availability

### Database Replication

#### PostgreSQL Master-Slave Setup
```sql
-- Master configuration
wal_level = replica
max_wal_senders = 3
wal_keep_segments = 64
archive_mode = on
archive_command = 'cp %p /var/lib/postgresql/archive/%f'

-- Slave configuration
standby_mode = 'on'
primary_conninfo = 'host=master-db port=5432 user=replicator'
restore_command = 'cp /var/lib/postgresql/archive/%f %p'
```

#### Connection Pooling
```python
# PgBouncer configuration
DATABASES = {
    "alert_intelligence": {
        "host": "pgbouncer",
        "port": 6432,
        "user": "app_user",
        "password": "secure_password",
        "database": "alert_intelligence",
        "pool_size": 20,
        "max_overflow": 30
    }
}
```

### Load Balancing

#### Nginx Configuration
```nginx
upstream api_servers {
    least_conn;
    server api1:8000 max_fails=3 fail_timeout=30s;
    server api2:8000 max_fails=3 fail_timeout=30s;
    server api3:8000 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name api.alert-intelligence.company.com;
    
    location / {
        proxy_pass http://api_servers;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
}
```

### Health Checks

#### Application Health
```python
@app.get("/health")
async def health_check():
    checks = {
        "database": await check_database(),
        "elasticsearch": await check_elasticsearch(),
        "redis": await check_redis(),
        "kafka": await check_kafka()
    }
    
    overall_status = "healthy" if all(checks.values()) else "unhealthy"
    
    return {
        "status": overall_status,
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }
```

## Monitoring & Observability

### Prometheus Metrics

#### Application Metrics
```python
from prometheus_client import Counter, Histogram, Gauge

# Metrics definitions
ALERTS_INGESTED = Counter('alerts_ingested_total', 'Total alerts ingested', ['source', 'severity'])
ALERT_PROCESSING_TIME = Histogram('alert_processing_seconds', 'Alert processing time')
ACTIVE_CONNECTIONS = Gauge('active_connections', 'Active database connections')

# Usage example
@ALERT_PROCESSING_TIME.time()
def process_alert(alert):
    # Process alert
    ALERTS_INGESTED.labels(source=alert.source, severity=alert.severity).inc()
```

#### System Metrics
```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'alert-intelligence'
    static_configs:
      - targets: ['api1:8000', 'api2:8000', 'api3:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
```

### Grafana Dashboards

#### Alert Monitoring Dashboard
- Alert ingestion rate
- Processing latency
- Error rates
- Queue depth
- Resource utilization

#### System Health Dashboard
- Database connections
- Elasticsearch cluster health
- Redis memory usage
- Kafka consumer lag
- Application response times

### Logging

#### Structured Logging
```python
import structlog

logger = structlog.get_logger()

logger.info(
    "Alert processed",
    alert_id=alert.id,
    source=alert.source,
    severity=alert.severity,
    processing_time_ms=processing_time,
    user_id=user.id
)
```

#### Log Aggregation
```yaml
# Filebeat configuration
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /var/log/alert-intelligence/*.log
  fields:
    service: alert-intelligence
    environment: production

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
  index: "alert-intelligence-logs-%{+yyyy.MM.dd}"
```

## Scalability

### Horizontal Scaling

#### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: alert-intelligence-api
spec:
  replicas: 5
  selector:
    matchLabels:
      app: alert-intelligence-api
  template:
    metadata:
      labels:
        app: alert-intelligence-api
    spec:
      containers:
      - name: api
        image: alert-intelligence:latest
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

#### Auto Scaling
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: alert-intelligence-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: alert-intelligence-api
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Caching Strategy

#### Multi-Tier Caching
```python
# L1 Cache (In-memory)
memory_cache = MemoryCache(max_size=10000, ttl_seconds=300)

# L2 Cache (Redis)
redis_cache = RedisCache(host='redis', port=6379, ttl_seconds=3600)

# Cache Manager
cache_manager = CacheManager(l1_cache=memory_cache, l2_cache=redis_cache)

# Usage
@cached(ttl_seconds=600)
async def get_alert(alert_id: str):
    return await fetch_alert_from_db(alert_id)
```

### Background Processing

#### Celery Configuration
```python
# celery_config.py
from celery import Celery

app = Celery('alert_intelligence')
app.conf.update(
    broker_url='redis://redis:6379/0',
    result_backend='redis://redis:6379/0',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000
)

# Task definition
@app.task(bind=True, max_retries=3)
def process_alert_async(self, alert_data):
    try:
        process_alert(alert_data)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
```

## Performance Optimization

### Database Optimization

#### Indexing Strategy
```sql
-- Alert table indexes
CREATE INDEX CONCURRENTLY idx_alerts_timestamp ON alerts(timestamp);
CREATE INDEX CONCURRENTLY idx_alerts_service ON alerts(service);
CREATE INDEX CONCURRENTLY idx_alerts_severity ON alerts(severity);
CREATE INDEX CONCURRENTLY idx_alerts_source ON alerts(source);

-- Composite indexes
CREATE INDEX CONCURRENTLY idx_alerts_service_timestamp ON alerts(service, timestamp);
CREATE INDEX CONCURRENTLY idx_alerts_severity_timestamp ON alerts(severity, timestamp);
```

#### Query Optimization
```python
# Efficient pagination
async def get_alerts_paginated(
    offset: int = 0,
    limit: int = 100,
    filters: Dict[str, Any] = None
):
    query = select(Alert).order_by(Alert.timestamp.desc())
    
    if filters:
        if filters.get('service'):
            query = query.where(Alert.service == filters['service'])
        if filters.get('severity'):
            query = query.where(Alert.severity == filters['severity'])
    
    query = query.offset(offset).limit(limit)
    
    result = await session.execute(query)
    return result.scalars().all()
```

### Elasticsearch Optimization

#### Index Templates
```json
{
  "index_patterns": ["alerts-*"],
  "template": {
    "settings": {
      "number_of_shards": 3,
      "number_of_replicas": 1,
      "refresh_interval": "5s",
      "index.codec": "best_compression"
    },
    "mappings": {
      "properties": {
        "timestamp": {
          "type": "date",
          "format": "strict_date_optional_time||epoch_millis"
        },
        "service": {
          "type": "keyword"
        },
        "severity": {
          "type": "keyword"
        },
        "description": {
          "type": "text",
          "analyzer": "standard"
        }
      }
    }
  }
}
```

## Disaster Recovery

### Backup Strategy

#### Database Backups
```bash
#!/bin/bash
# Daily backup script
BACKUP_DIR="/backups/postgres"
DATE=$(date +%Y%m%d)
DB_NAME="alert_intelligence"

# Create backup
pg_dump -h postgres -U postgres -d $DB_NAME | gzip > $BACKUP_DIR/backup_$DATE.sql.gz

# Retention policy (keep 30 days)
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +30 -delete

# Upload to cloud storage
aws s3 cp $BACKUP_DIR/backup_$DATE.sql.gz s3://backups/postgres/
```

#### Elasticsearch Snapshots
```json
{
  "type": "s3",
  "settings": {
    "bucket": "elasticsearch-backups",
    "region": "us-east-1",
    "base_path": "snapshots"
  }
}
```

### High Availability Setup

#### Multi-Region Deployment
```yaml
# Primary region (us-east-1)
apiVersion: v1
kind: ConfigMap
metadata:
  name: region-config
data:
  REGION: "us-east-1"
  DATABASE_URL: "postgres://primary-db:5432/alert_intelligence"
  REDIS_URL: "redis://primary-redis:6379"

# Disaster recovery region (us-west-2)
apiVersion: v1
kind: ConfigMap
metadata:
  name: region-config-dr
data:
  REGION: "us-west-2"
  DATABASE_URL: "postgres://dr-db:5432/alert_intelligence"
  REDIS_URL: "redis://dr-redis:6379"
```

## Deployment Automation

### CI/CD Pipeline

#### GitHub Actions
```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Run tests
      run: |
        pytest tests/
        flake8 backend/
        mypy backend/

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Build Docker image
      run: |
        docker build -t alert-intelligence:${{ github.sha }} .
        docker tag alert-intelligence:${{ github.sha }} alert-intelligence:latest
    
    - name: Push to registry
      run: |
        docker push alert-intelligence:${{ github.sha }}
        docker push alert-intelligence:latest

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
    - name: Deploy to Kubernetes
      run: |
        kubectl set image deployment/alert-intelligence api=alert-intelligence:${{ github.sha }}
        kubectl rollout status deployment/alert-intelligence
```

### Infrastructure as Code

#### Terraform Configuration
```hcl
# EKS Cluster
resource "aws_eks_cluster" "alert_intelligence" {
  name     = "alert-intelligence"
  role_arn = aws_iam_role.eks_cluster.arn
  version  = "1.28"

  vpc_config {
    subnet_ids = [
      aws_subnet.private_1.id,
      aws_subnet.private_2.id,
      aws_subnet.private_3.id
    ]
  }
}

# RDS PostgreSQL
resource "aws_db_instance" "postgres" {
  identifier = "alert-intelligence-db"
  engine     = "postgres"
  instance_class = "db.r5.large"
  
  allocated_storage     = 500
  max_allocated_storage = 1000
  storage_encrypted     = true
  
  backup_retention_period = 30
  backup_window      = "03:00-04:00"
  maintenance_window = "sun:04:00-sun:05:00"
  
  skip_final_snapshot = false
  final_snapshot_identifier = "alert-intelligence-final-snapshot"
}
```

## Security Best Practices

### Secrets Management

#### Kubernetes Secrets
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: alert-intelligence-secrets
type: Opaque
data:
  DATABASE_URL: <base64-encoded-url>
  SECRET_KEY: <base64-encoded-key>
  REDIS_URL: <base64-encoded-url>
```

#### Environment Variables
```bash
# .env.production
DATABASE_URL=postgresql://user:password@db:5432/alert_intelligence
SECRET_KEY=your-secret-key
REDIS_URL=redis://redis:6379/0
ELASTICSEARCH_URL=http://elasticsearch:9200
KAFKA_BOOTSTRAP_SERVERS=kafka:9092

# Security settings
ALLOWED_ORIGINS=https://alert-intelligence.company.com
CORS_ORIGINS=https://app.company.com
SECURITY_HEADERS_ENABLED=true
RATE_LIMIT_ENABLED=true
```

### Compliance

#### GDPR Compliance
```python
# Data retention policies
DATA_RETENTION_DAYS = {
    "alerts": 365,
    "incidents": 2555,  # 7 years
    "audit_logs": 2555,
    "user_data": 2555
}

# Data anonymization
def anonymize_user_data(user_data):
    return {
        "user_id": hash(user_data["id"]),
        "email": anonymize_email(user_data["email"]),
        "ip_address": anonymize_ip(user_data["ip_address"])
    }
```

#### SOC 2 Controls
```python
# Audit logging
audit_logger.log_event(
    event_type="data_access",
    user_id=user.id,
    resource=f"alert/{alert_id}",
    action="read",
    success=True
)

# Access control
@require_permission("alerts:read")
async def get_alert(alert_id: str):
    # Implementation
    pass
```

## Troubleshooting

### Common Issues

#### High Memory Usage
```python
# Monitor memory usage
import psutil
import gc

def monitor_memory():
    process = psutil.Process()
    memory_info = process.memory_info()
    
    logger.info(
        "Memory usage",
        rss_mb=memory_info.rss / 1024 / 1024,
        vms_mb=memory_info.vms / 1024 / 1024
    )
    
    # Force garbage collection if needed
    if memory_info.rss > 1024 * 1024 * 1024:  # 1GB
        gc.collect()
```

#### Database Connection Issues
```python
# Connection pool monitoring
async def monitor_connections():
    pool = get_database_pool()
    
    logger.info(
        "Connection pool status",
        size=pool.size,
        checked_in=pool.checkedin,
        checked_out=pool.checkedout,
        overflow=pool.overflow
    )
```

#### Performance Bottlenecks
```python
# Performance profiling
import cProfile
import pstats

def profile_function(func):
    profiler = cProfile.Profile()
    profiler.enable()
    
    result = func()
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)
    
    return result
```

## Maintenance

### Rolling Updates

#### Kubernetes Rolling Update
```bash
# Update deployment with zero downtime
kubectl set image deployment/alert-intelligence api=alert-intelligence:v2.0.0
kubectl rollout status deployment/alert-intelligence

# Rollback if needed
kubectl rollout undo deployment/alert-intelligence
```

### Database Maintenance

#### Index Maintenance
```sql
-- Rebuild indexes
REINDEX INDEX CONCURRENTLY idx_alerts_timestamp;

-- Update statistics
ANALYZE alerts;

-- Vacuum old data
VACUUM FULL alerts;
```

This enterprise deployment guide provides comprehensive instructions for deploying the Alert Intelligence Platform in a production environment with high availability, security, monitoring, and scalability considerations.
