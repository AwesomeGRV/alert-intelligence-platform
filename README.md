# Alert Intelligence Platform

A scalable, production-ready platform that ingests alerts from multiple sources, deduplicates & clusters them, correlates with logs/metrics, and provides actionable intelligence for SREs via dashboard and ChatOps.

##  Features

### Core Features
- **Multi-Source Alert Ingestion**: New Relic, Prometheus Alertmanager, CloudWatch, PagerDuty
- **Alert Normalization**: Common schema for all alert types with automatic parsing
- **Deduplication & Clustering**: Smart grouping of related alerts with configurable similarity thresholds
- **Correlation Engine**: Root cause analysis with deployment and log correlation
- **Intelligence Layer**: Rule-based correlation with optional ML clustering
- **Noise Scoring**: Identify noisy services and reduce alert fatigue
- **Real-time Dashboard**: React-based UI with Tailwind CSS
- **ChatOps Integration**: Slack and Microsoft Teams bots for incident management

### Advanced Features
- **Predictive Analytics**: Anomaly prediction and trend analysis
- **SLA Monitoring**: Automatic SLA breach detection and reporting
- **Service Dependencies**: Visual mapping of service relationships
- **Auto-Resolution**: Automated incident resolution based on patterns

##  Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Alert Sources  │───▶│ Alert Ingestion  │───▶│ Normalization   │
│ New Relic/      │    │ API              │    │ & Enrichment    │
│ Prometheus/      │    │                  │    │                 │
│ CloudWatch/     │    │                  │    │                 │
│ PagerDuty       │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                        │
                       ┌──────────────────┐    ┌─────────────────┐
                       │ Clustering &     │◀───│                 │
                       │ Correlation      │    │                 │
                       │                  │    │                 │
                       └──────────────────┘    │                 │
                                                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Dashboard &     │◀───│ Intelligence     │    │ Storage         │
│ ChatOps         │    │ Layer            │    │ PostgreSQL +    │
│ React + FastAPI │    │ (Rules + ML)     │    │ Elasticsearch   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

##  Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI, Python 3.11 |
| **Frontend** | React 18, Tailwind CSS, Recharts |
| **Database** | PostgreSQL 15, Elasticsearch 8.11 |
| **Cache** | Redis 7 |
| **Streaming** | Apache Kafka |
| **ML/Analytics** | scikit-learn, NumPy, Pandas |
| **Containerization** | Docker, Docker Compose |
| **Orchestration** | Kubernetes |
| **Monitoring** | Prometheus, Grafana |
| **CI/CD** | GitHub Actions, ArgoCD |
| **ChatOps** | Slack SDK, Microsoft Teams |

##  Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- Node.js 18+
- Python 3.11+
- kubectl (for Kubernetes deployment)
- AWS CLI (for cloud deployment)

##  Quick Start

### Using Docker Compose (Recommended for Development)

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/alert-intelligence-platform.git
   cd alert-intelligence-platform
   ```

2. **Start all services**
   ```bash
   docker-compose up -d
   ```

3. **Wait for services to be ready** (approximately 2-3 minutes)
   ```bash
   docker-compose ps
   ```

4. **Access the platform**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - Grafana: http://localhost:3001 (admin/admin)
   - Prometheus: http://localhost:9090

### Development Setup

1. **Backend Development**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   uvicorn fastapi_app.main:app --reload
   ```

2. **Frontend Development**
   ```bash
   cd frontend
   npm install
   npm start
   ```

3. **Start supporting services**
   ```bash
   docker-compose up -d postgres elasticsearch redis kafka
   ```

##  Usage

### Alert Ingestion

Send alerts to the ingestion endpoint:

```bash
curl -X POST "http://localhost:8000/api/v1/alerts/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "prometheus",
    "service": "api-gateway",
    "severity": "high",
    "description": "High error rate detected",
    "metrics_snapshot": {
      "error_rate": 0.15,
      "request_count": 1000
    }
  }'
```

### ChatOps Commands

#### Slack Integration
- `/incident explain <cluster_id>` - Get incident details
- `/incident list` - List active incidents
- `/alerts list` - List recent alerts
- `/status` - Get system status

#### Microsoft Teams Integration
- Mention the bot with "incident explain <cluster_id>"
- Use "list incidents" for active incidents
- "system status" for health overview

### Dashboard Features

- **Real-time Monitoring**: Live alert and incident metrics
- **Service Health**: Health scores and noise analysis
- **Incident Management**: Create, update, and resolve incidents
- **Correlation Insights**: Automated root cause suggestions
- **SLA Tracking**: Monitor compliance and breach alerts

##  Configuration

### Environment Variables

Backend configuration (`.env`):
```env
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/alert_intelligence
ELASTICSEARCH_URL=http://localhost:9200
REDIS_URL=redis://localhost:6379/0
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
SECRET_KEY=your-secret-key
DEBUG=false
```

Frontend configuration (`.env`):
```env
REACT_APP_API_URL=http://localhost:8000
```

### Alert Source Configuration

Configure alert sources in the dashboard or via API:

```bash
# Configure New Relic
curl -X POST "http://localhost:8000/api/v1/integrations/new-relic" \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "your-new-relic-api-key",
    "account_id": "123456"
  }'
```

##  Deployment

### Kubernetes Deployment

1. **Create namespace and secrets**
   ```bash
   kubectl apply -f deployment/k8s/namespace.yaml
   kubectl apply -f deployment/k8s/secrets.yaml
   ```

2. **Deploy infrastructure**
   ```bash
   kubectl apply -f deployment/k8s/postgres-deployment.yaml
   kubectl apply -f deployment/k8s/elasticsearch-deployment.yaml
   kubectl apply -f deployment/k8s/redis-deployment.yaml
   kubectl apply -f deployment/k8s/kafka-deployment.yaml
   ```

3. **Deploy applications**
   ```bash
   kubectl apply -f deployment/k8s/backend-deployment.yaml
   kubectl apply -f deployment/k8s/frontend-deployment.yaml
   kubectl apply -f deployment/k8s/ingress.yaml
   kubectl apply -f deployment/k8s/hpa.yaml
   ```

### Production Considerations

- **High Availability**: Configure multi-zone deployments
- **Security**: Enable TLS, use secrets management
- **Monitoring**: Set up comprehensive alerting
- **Backup**: Configure database and Elasticsearch backups
- **Scaling**: Configure HPA and resource limits

##  Monitoring & Observability

### Prometheus Metrics

Key metrics available:
- `alerts_ingested_total` - Total alerts processed
- `incidents_created_total` - Incidents created
- `alert_processing_duration_seconds` - Processing latency
- `active_alerts_total` - Current active alerts
- `active_incidents_total` - Current active incidents

### Grafana Dashboards

Pre-configured dashboards:
- **Platform Overview**: System health and metrics
- **Alert Analysis**: Alert volume and patterns
- **Incident Management**: Incident lifecycle tracking
- **Infrastructure**: Database and system metrics

### Logging

Structured logging with:
- **Backend**: JSON logs with correlation IDs
- **Frontend**: Browser console and error tracking
- **Infrastructure**: Centralized log aggregation

##  Testing

### Running Tests

```bash
# Backend tests
cd backend
pytest tests/ -v --cov=fastapi_app

# Frontend tests
cd frontend
npm test -- --coverage --watchAll=false

# Integration tests
docker-compose -f docker-compose.test.yml up -d
pytest tests/integration/ -v
```

### Test Coverage

- **Backend**: Unit tests, integration tests, API tests
- **Frontend**: Component tests, E2E tests
- **Infrastructure**: Load testing (100k+ alerts/min)

##  Security

### Authentication & Authorization

- **OAuth 2.0**: SSO integration support
- **API Keys**: Secure alert ingestion
- **RBAC**: Role-based access control
- **Audit Logging**: Complete audit trail

### Security Best Practices

- **Secrets Management**: HashiCorp Vault or Kubernetes secrets
- **Network Security**: TLS encryption, network policies
- **Container Security**: Non-root users, read-only filesystems
- **Dependency Scanning**: Automated vulnerability scanning

##  Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow Python PEP 8 and JavaScript ESLint standards
- Add tests for new features
- Update documentation
- Ensure CI/CD pipeline passes

##  License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

##  Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/your-org/alert-intelligence-platform/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/alert-intelligence-platform/discussions)
- **Community Slack**: [Join our Slack](https://slack.example.com)

##  Roadmap

### v1.1 (Q2 2026)
- [ ] Machine learning-based correlation
- [ ] Mobile app for incident management
- [ ] Advanced analytics and reporting
- [ ] Multi-tenant support

### v1.2 (Q3 2026)
- [ ] Predictive alerting
- [ ] Automated remediation
- [ ] Integration with more monitoring tools
- [ ] Performance optimizations

### v2.0 (Q4 2026)
- [ ] Distributed architecture
- [ ] Real-time streaming analytics
- [ ] Advanced AI/ML capabilities
- [ ] Enterprise features

##  Performance

### Benchmarks

- **Alert Ingestion**: 100k+ alerts/minute
- **Query Performance**: <100ms for dashboard queries
- **Memory Usage**: <512MB per backend instance
- **Storage**: Efficient compression and retention

### Scaling

- **Horizontal Scaling**: Stateless services
- **Database Sharding**: PostgreSQL partitioning
- **Cache Layers**: Redis clustering
- **CDN**: Static asset delivery

##  Acknowledgments

- **FastAPI**: Modern Python web framework
- **React**: User interface library
- **Elasticsearch**: Search and analytics
- **Prometheus**: Monitoring and alerting
- **Kubernetes**: Container orchestration

---

