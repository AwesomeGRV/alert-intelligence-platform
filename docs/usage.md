# Usage Guide

This guide covers how to use the Alert Intelligence Platform effectively, from basic setup to advanced features.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Alert Management](#alert-management)
3. [Incident Management](#incident-management)
4. [Dashboard Usage](#dashboard-usage)
5. [ChatOps Integration](#chatops-integration)
6. [Advanced Features](#advanced-features)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

## Getting Started

### Initial Setup

1. **Access the Platform**
   - Navigate to your platform URL
   - Log in with your credentials
   - Complete your profile setup

2. **Configure Alert Sources**
   - Go to Settings → Integrations
   - Configure your monitoring tools
   - Test connections

3. **Set Up Notifications**
   - Configure Slack/Teams integration
   - Set up email notifications
   - Define notification preferences

### Basic Navigation

- **Dashboard**: Overview of system health and metrics
- **Alerts**: View and manage individual alerts
- **Incidents**: Track and resolve incidents
- **Services**: Monitor service health and noise scores
- **Settings**: Configure platform settings

## Alert Management

### Viewing Alerts

1. **Access Alerts Page**
   - Click "Alerts" in the navigation
   - View all recent alerts

2. **Filter and Search**
   - Use filters for service, severity, status
   - Search by description or tags
   - Sort by timestamp or severity

3. **Alert Details**
   - Click on any alert to view details
   - See metadata, metrics, and related alerts
   - View alert history and deduplication info

### Alert Actions

#### Viewing Alert Details
```bash
# Get alert by ID
curl "http://localhost:8000/api/v1/alerts/{alert_id}"
```

#### Updating Alert Status
```bash
# Acknowledge alert
curl -X PUT "http://localhost:8000/api/v1/alerts/{alert_id}" \
  -H "Content-Type: application/json" \
  -d '{"status": "acknowledged"}'
```

#### Deleting Alerts
```bash
# Delete alert
curl -X DELETE "http://localhost:8000/api/v1/alerts/{alert_id}"
```

### Alert Ingestion

#### Manual Alert Creation
```bash
curl -X POST "http://localhost:8000/api/v1/alerts/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "custom",
    "service": "api-gateway",
    "severity": "high",
    "description": "API response time exceeded threshold",
    "tags": ["performance", "api"],
    "metrics_snapshot": {
      "response_time": 1500,
      "error_rate": 0.05
    }
  }'
```

#### Prometheus Alert Format
```bash
curl -X POST "http://localhost:8000/api/v1/alerts/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "prometheus",
    "prometheus_labels": {
      "alertname": "HighErrorRate",
      "instance": "api-server-1",
      "job": "api-server"
    },
    "service": "api-server",
    "severity": "critical",
    "description": "Error rate is above 5%",
    "value": 0.08
  }'
```

#### New Relic Alert Format
```bash
curl -X POST "http://localhost:8000/api/v1/alerts/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "new_relic",
    "new_relic_account_id": "123456",
    "application_name": "Web Application",
    "new_relic_policy_name": "High Error Rate",
    "severity": "high",
    "description": "Error rate exceeded threshold",
    "service": "web-app"
  }'
```

## Incident Management

### Creating Incidents

#### Manual Creation
1. Go to Incidents page
2. Click "Create Incident"
3. Fill in incident details:
   - Title
   - Description
   - Severity
   - Affected services
   - Tags

#### Automatic Creation
- Incidents are automatically created when alert clusters reach thresholds
- Configure clustering settings in Settings → Alerts

#### API Creation
```bash
curl -X POST "http://localhost:8000/api/v1/incidents/" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Database Performance Degradation",
    "description": "Database response times have increased significantly",
    "severity": "high",
    "service": "database",
    "affected_services": ["api-server", "web-app"],
    "tags": ["performance", "database"]
  }'
```

### Managing Incidents

#### Viewing Incidents
1. **Incident List**
   - View all active and recent incidents
   - Filter by status, severity, service
   - Sort by creation time or severity

2. **Incident Details**
   - Click incident to view full details
   - See timeline of events
   - View related alerts
   - Check correlation insights

#### Updating Incidents
```bash
# Update incident status
curl -X PUT "http://localhost:8000/api/v1/incidents/{cluster_id}" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "investigating",
    "assigned_to": "oncall-engineer"
  }'
```

#### Resolving Incidents
```bash
# Mark incident as resolved
curl -X POST "http://localhost:8000/api/v1/incidents/{cluster_id}/resolve" \
  -H "Content-Type: application/json" \
  -d '{
    "root_cause": "Database connection pool exhaustion",
    "fix": "Increased connection pool size and added connection timeout"
  }'
```

### Incident Workflows

#### Standard Response Process
1. **Acknowledge**: Incident is acknowledged within 5 minutes
2. **Investigate**: Root cause analysis begins
3. **Communicate**: Stakeholders are notified
4. **Resolve**: Fix is implemented and verified
5. **Post-mortem**: Lessons learned are documented

#### Escalation Rules
- Critical incidents auto-escalate after 15 minutes
- High severity incidents escalate after 30 minutes
- Custom escalation rules can be configured

## Dashboard Usage

### Main Dashboard

#### Overview Metrics
- **Active Alerts**: Current number of active alerts
- **Active Incidents**: Current number of active incidents
- **System Health**: Overall platform health score
- **Services Monitored**: Number of services being monitored

#### Real-time Charts
- **Alert Trends**: 24-hour alert volume trends
- **Incident Severity**: Distribution by severity level
- **Service Health**: Health scores for top services
- **Noise Analysis**: Services with highest noise scores

### Alert Dashboard

#### Alert Management
- **List View**: All alerts with filtering and sorting
- **Details View**: Comprehensive alert information
- **Bulk Actions**: Select and act on multiple alerts
- **Export**: Export alerts to CSV/JSON

#### Alert Analytics
- **Volume Trends**: Alert volume over time
- **Severity Distribution**: Breakdown by severity
- **Service Breakdown**: Alerts per service
- **Source Analysis**: Alerts by source system

### Incident Dashboard

#### Incident Tracking
- **Active Incidents**: Currently open incidents
- **Incident Timeline**: Chronological view of events
- **Resolution Metrics**: Time to resolution trends
- **SLA Compliance**: SLA breach tracking

#### Incident Analytics
- **MTTR Analysis**: Mean time to resolution
- **Severity Trends**: Incident severity patterns
- **Service Impact**: Most affected services
- **Root Cause Analysis**: Common causes

### Service Dashboard

#### Service Health
- **Health Scores**: Overall service health
- **Alert Volume**: Alert count per service
- **Noise Scores**: Service noise analysis
- **Dependencies**: Service relationship map

#### Service Metrics
- **Performance**: Response times and error rates
- **Availability**: Uptime and downtime tracking
- **Capacity**: Resource utilization
- **Trends**: Historical performance data

## ChatOps Integration

### Slack Integration

#### Setup
1. Create Slack app
2. Configure bot permissions
3. Set up webhook URL
4. Add bot to channels

#### Commands
```
/incident explain <cluster_id>    # Get incident details
/incident list                    # List active incidents
/incident resolve <cluster_id>    # Resolve incident
/alerts list                      # List recent alerts
/alerts service <service_name>    # Alerts for specific service
/status                           # System health status
```

#### Examples
```
/incident explain 123e4567-e89b-12d3-a456-426614174000
/incident list
/alerts list
/status
```

### Microsoft Teams Integration

#### Setup
1. Create Teams bot
2. Configure bot permissions
3. Set up webhook URL
4. Add bot to teams

#### Commands
```
incident explain <cluster_id>    # Get incident details
incident list                    # List active incidents
alerts list                      # List recent alerts
status                           # System health status
```

#### Usage Examples
```
@AlertBot incident explain 123e4567-e89b-12d3-a456-426614174000
@AlertBot incident list
@AlertBot status
```

## Advanced Features

### Correlation Engine

#### Automatic Correlation
The platform automatically correlates:
- **Deployments**: Recent deployments with alert spikes
- **Logs**: Error patterns in log data
- **Metrics**: Anomalous metric behavior
- **Historical**: Similar past incidents

#### Manual Correlation
1. Go to incident details
2. Click "Correlation Insights"
3. Review suggested correlations
4. Accept or modify correlations

### Noise Scoring

#### Understanding Noise Scores
- **0-30%**: Low noise (healthy service)
- **31-60%**: Moderate noise (monitor closely)
- **61-80%**: High noise (investigate)
- **81-100%**: Critical noise (immediate action)

#### Reducing Noise
1. **Alert Tuning**: Adjust alert thresholds
2. **Deduplication**: Improve deduplication settings
3. **Clustering**: Fine-tune clustering parameters
4. **Source Optimization**: Work with source teams

### SLA Management

#### SLA Configuration
1. Go to Settings → SLA
2. Configure SLA targets:
   - Default: 60 minutes
   - Critical: 15 minutes
   - High: 30 minutes
   - Medium: 120 minutes
   - Low: 240 minutes

#### SLA Monitoring
- Real-time SLA compliance tracking
- Automated breach notifications
- SLA performance reports
- Trend analysis

### Predictive Analytics

#### Alert Prediction
- **Pattern Recognition**: Identify alert patterns
- **Anomaly Detection**: Spot unusual behavior
- **Trend Analysis**: Predict future alert volume
- **Capacity Planning**: Plan for resource needs

#### Incident Prediction
- **Risk Scoring**: Assess incident risk
- **Proactive Alerts**: Warn before incidents occur
- **Resource Allocation**: Plan response resources
- **Prevention Strategies**: Implement preventive measures

## Best Practices

### Alert Management

#### Alert Design
- **Meaningful Messages**: Clear, actionable descriptions
- **Appropriate Severity**: Use severity levels correctly
- **Proper Tagging**: Use consistent tagging conventions
- **Context Information**: Include relevant metrics and context

#### Alert Lifecycle
- **Quick Acknowledgment**: Acknowledge alerts promptly
- **Regular Review**: Review and update alert rules
- **Noise Reduction**: Continuously reduce alert noise
- **Documentation**: Document alert procedures

### Incident Management

#### Response Process
- **Standard Operating Procedures**: Document response procedures
- **Clear Roles**: Define incident response roles
- **Communication Plans**: Establish communication protocols
- **Post-mortems**: Conduct thorough post-mortems

#### Incident Prevention
- **Root Cause Analysis**: Find and fix root causes
- **Preventive Measures**: Implement preventive actions
- **Monitoring Enhancement**: Improve monitoring coverage
- **Automation**: Automate repetitive tasks

### Platform Usage

#### Dashboard Usage
- **Regular Monitoring**: Check dashboards regularly
- **Custom Views**: Create custom dashboard views
- **Alert Thresholds**: Set appropriate alert thresholds
- **Performance Tracking**: Monitor platform performance

#### Integration Management
- **Source Configuration**: Keep source configurations updated
- **Testing**: Regularly test integrations
- **Documentation**: Document integration procedures
- **Backup Plans**: Have backup integration methods

## Troubleshooting

### Common Issues

#### Alert Ingestion Problems
```
Issue: Alerts not appearing
Solution: Check source configuration and API keys
```

```
Issue: Duplicate alerts
Solution: Adjust deduplication settings
```

#### Performance Issues
```
Issue: Slow dashboard loading
Solution: Check database performance and indexing
```

```
Issue: High memory usage
Solution: Review alert volume and retention policies
```

#### Integration Issues
```
Issue: Slack bot not responding
Solution: Check webhook URL and bot permissions
```

```
Issue: Prometheus alerts not ingesting
Solution: Verify Alertmanager configuration
```

### Debugging Tools

#### Log Analysis
```bash
# Check backend logs
docker-compose logs backend

# Check specific service logs
docker-compose logs postgres
```

#### API Testing
```bash
# Test API health
curl http://localhost:8000/health

# Test alert ingestion
curl -X POST "http://localhost:8000/api/v1/alerts/ingest" \
  -H "Content-Type: application/json" \
  -d '{"test": "alert"}'
```

#### Database Checks
```bash
# Check database connectivity
docker-compose exec postgres psql -U postgres -d alert_intelligence

# Check alert count
SELECT COUNT(*) FROM alerts;
```

### Performance Tuning

#### Database Optimization
- Add appropriate indexes
- Optimize slow queries
- Monitor connection pools
- Regular maintenance tasks

#### Caching Strategy
- Optimize Redis usage
- Implement application caching
- Monitor cache hit rates
- Configure cache expiration

#### Resource Management
- Monitor resource utilization
- Adjust container limits
- Optimize memory usage
- Scale based on demand

### Getting Help

#### Support Channels
- **Documentation**: Check platform documentation
- **Community**: Join community discussions
- **Issues**: Report bugs and feature requests
- **Support**: Contact support team

#### Self-Service
- **Health Checks**: Use built-in health checks
- **Diagnostics**: Run diagnostic tools
- **Logs**: Check application logs
- **Metrics**: Review performance metrics

This comprehensive usage guide should help you get the most out of the Alert Intelligence Platform. For specific questions or issues, refer to the troubleshooting section or reach out to the support team.
