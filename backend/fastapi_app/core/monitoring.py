import time
import psutil
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import structlog
import json
from contextlib import asynccontextmanager

logger = structlog.get_logger()

@dataclass
class MetricPoint:
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str]
    metric_type: str = "gauge"  # gauge, counter, histogram

@dataclass
class HealthCheck:
    name: str
    status: str  # healthy, unhealthy, degraded
    message: str
    timestamp: datetime
    response_time_ms: float
    details: Dict[str, Any] = None

class MetricsCollector:
    def __init__(self, max_points: int = 10000):
        self.max_points = max_points
        self.metrics = defaultdict(lambda: deque(maxlen=max_points))
        self.counters = defaultdict(float)
        self.histograms = defaultdict(lambda: defaultdict(int))
        self.start_time = datetime.utcnow()
        
    def increment_counter(self, name: str, value: float = 1.0, tags: Dict[str, str] = None):
        """Increment counter metric"""
        tags = tags or {}
        key = f"{name}:{json.dumps(tags, sort_keys=True)}"
        self.counters[key] += value
        
        metric = MetricPoint(
            name=name,
            value=self.counters[key],
            timestamp=datetime.utcnow(),
            tags=tags,
            metric_type="counter"
        )
        self.metrics[name].append(metric)
    
    def set_gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """Set gauge metric"""
        tags = tags or {}
        
        metric = MetricPoint(
            name=name,
            value=value,
            timestamp=datetime.utcnow(),
            tags=tags,
            metric_type="gauge"
        )
        self.metrics[name].append(metric)
    
    def record_histogram(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record histogram metric"""
        tags = tags or {}
        key = f"{name}:{json.dumps(tags, sort_keys=True)}"
        
        # Create buckets for histogram
        buckets = [0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 25.0, 50.0, 100.0, float('inf')]
        for bucket in buckets:
            if value <= bucket:
                self.histograms[key][f"le_{bucket}"] += 1
        
        self.histograms[key]["count"] += 1
        self.histograms[key]["sum"] += value
        
        metric = MetricPoint(
            name=name,
            value=value,
            timestamp=datetime.utcnow(),
            tags=tags,
            metric_type="histogram"
        )
        self.metrics[name].append(metric)
    
    def get_metrics_summary(self, name: str, minutes: int = 5) -> Dict[str, Any]:
        """Get metrics summary for the last N minutes"""
        if name not in self.metrics:
            return {}
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        recent_metrics = [
            m for m in self.metrics[name] 
            if m.timestamp >= cutoff_time
        ]
        
        if not recent_metrics:
            return {}
        
        values = [m.value for m in recent_metrics]
        return {
            "name": name,
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "latest": values[-1] if values else None,
            "timestamp": recent_metrics[-1].timestamp.isoformat()
        }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all current metrics"""
        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds(),
            "metrics": {}
        }
        
        for name in self.metrics:
            result["metrics"][name] = self.get_metrics_summary(name)
        
        return result

class HealthChecker:
    def __init__(self):
        self.checks = {}
        self.results = {}
        
    def register_check(self, name: str, check_func, interval_seconds: int = 30):
        """Register a health check function"""
        self.checks[name] = {
            "func": check_func,
            "interval": interval_seconds,
            "last_run": None
        }
    
    async def run_check(self, name: str) -> HealthCheck:
        """Run a specific health check"""
        if name not in self.checks:
            return HealthCheck(
                name=name,
                status="unhealthy",
                message="Health check not found",
                timestamp=datetime.utcnow(),
                response_time_ms=0.0
            )
        
        check_config = self.checks[name]
        start_time = time.time()
        
        try:
            result = await check_config["func"]()
            response_time = (time.time() - start_time) * 1000
            
            health_check = HealthCheck(
                name=name,
                status=result.get("status", "healthy"),
                message=result.get("message", "Check passed"),
                timestamp=datetime.utcnow(),
                response_time_ms=response_time,
                details=result.get("details", {})
            )
            
            self.results[name] = health_check
            return health_check
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            health_check = HealthCheck(
                name=name,
                status="unhealthy",
                message=f"Health check failed: {str(e)}",
                timestamp=datetime.utcnow(),
                response_time_ms=response_time
            )
            
            self.results[name] = health_check
            return health_check
    
    async def run_all_checks(self) -> Dict[str, HealthCheck]:
        """Run all registered health checks"""
        tasks = []
        for name in self.checks:
            tasks.append(self.run_check(name))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        health_results = {}
        for i, name in enumerate(self.checks.keys()):
            if isinstance(results[i], Exception):
                health_results[name] = HealthCheck(
                    name=name,
                    status="unhealthy",
                    message=f"Check error: {str(results[i])}",
                    timestamp=datetime.utcnow(),
                    response_time_ms=0.0
                )
            else:
                health_results[name] = results[i]
        
        return health_results
    
    def get_overall_status(self) -> str:
        """Get overall system status"""
        if not self.results:
            return "unknown"
        
        statuses = [check.status for check in self.results.values()]
        
        if all(status == "healthy" for status in statuses):
            return "healthy"
        elif any(status == "unhealthy" for status in statuses):
            return "unhealthy"
        else:
            return "degraded"

class PerformanceMonitor:
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.health_checker = HealthChecker()
        self.setup_system_checks()
        
    def setup_system_checks(self):
        """Setup system health checks"""
        self.health_checker.register_check("database", self.check_database_health)
        self.health_checker.register_check("elasticsearch", self.check_elasticsearch_health)
        self.health_checker.register_check("redis", self.check_redis_health)
        self.health_checker.register_check("disk_space", self.check_disk_space)
        self.health_checker.register_check("memory", self.check_memory_usage)
        self.health_checker.register_check("cpu", self.check_cpu_usage)
    
    async def check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity and performance"""
        try:
            # This would be implemented with actual database connection
            # For now, simulate health check
            await asyncio.sleep(0.1)  # Simulate query time
            
            return {
                "status": "healthy",
                "message": "Database connection successful",
                "details": {
                    "connection_time_ms": 100,
                    "active_connections": 15,
                    "max_connections": 100
                }
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Database health check failed: {str(e)}"
            }
    
    async def check_elasticsearch_health(self) -> Dict[str, Any]:
        """Check Elasticsearch cluster health"""
        try:
            # This would be implemented with actual ES client
            await asyncio.sleep(0.05)  # Simulate query time
            
            return {
                "status": "healthy",
                "message": "Elasticsearch cluster healthy",
                "details": {
                    "cluster_status": "green",
                    "nodes": 3,
                    "active_shards": 12
                }
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Elasticsearch health check failed: {str(e)}"
            }
    
    async def check_redis_health(self) -> Dict[str, Any]:
        """Check Redis connectivity"""
        try:
            # This would be implemented with actual Redis client
            await asyncio.sleep(0.02)  # Simulate query time
            
            return {
                "status": "healthy",
                "message": "Redis connection successful",
                "details": {
                    "ping_ms": 20,
                    "memory_usage": "45MB",
                    "connected_clients": 5
                }
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Redis health check failed: {str(e)}"
            }
    
    async def check_disk_space(self) -> Dict[str, Any]:
        """Check disk space usage"""
        try:
            disk_usage = psutil.disk_usage('/')
            usage_percent = (disk_usage.used / disk_usage.total) * 100
            
            if usage_percent > 90:
                status = "unhealthy"
                message = f"Disk usage critical: {usage_percent:.1f}%"
            elif usage_percent > 80:
                status = "degraded"
                message = f"Disk usage high: {usage_percent:.1f}%"
            else:
                status = "healthy"
                message = f"Disk usage normal: {usage_percent:.1f}%"
            
            return {
                "status": status,
                "message": message,
                "details": {
                    "usage_percent": usage_percent,
                    "free_gb": disk_usage.free / (1024**3),
                    "total_gb": disk_usage.total / (1024**3)
                }
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Disk space check failed: {str(e)}"
            }
    
    async def check_memory_usage(self) -> Dict[str, Any]:
        """Check memory usage"""
        try:
            memory = psutil.virtual_memory()
            usage_percent = memory.percent
            
            if usage_percent > 90:
                status = "unhealthy"
                message = f"Memory usage critical: {usage_percent:.1f}%"
            elif usage_percent > 80:
                status = "degraded"
                message = f"Memory usage high: {usage_percent:.1f}%"
            else:
                status = "healthy"
                message = f"Memory usage normal: {usage_percent:.1f}%"
            
            return {
                "status": status,
                "message": message,
                "details": {
                    "usage_percent": usage_percent,
                    "available_gb": memory.available / (1024**3),
                    "total_gb": memory.total / (1024**3)
                }
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Memory usage check failed: {str(e)}"
            }
    
    async def check_cpu_usage(self) -> Dict[str, Any]:
        """Check CPU usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            
            if cpu_percent > 90:
                status = "unhealthy"
                message = f"CPU usage critical: {cpu_percent:.1f}%"
            elif cpu_percent > 80:
                status = "degraded"
                message = f"CPU usage high: {cpu_percent:.1f}%"
            else:
                status = "healthy"
                message = f"CPU usage normal: {cpu_percent:.1f}%"
            
            return {
                "status": status,
                "message": message,
                "details": {
                    "usage_percent": cpu_percent,
                    "cpu_count": psutil.cpu_count()
                }
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"CPU usage check failed: {str(e)}"
            }
    
    def record_request_metric(self, endpoint: str, method: str, status_code: int, duration_ms: float):
        """Record API request metrics"""
        tags = {
            "endpoint": endpoint,
            "method": method,
            "status_code": str(status_code)
        }
        
        self.metrics_collector.increment_counter("http_requests_total", tags=tags)
        self.metrics_collector.record_histogram("http_request_duration_ms", duration_ms, tags=tags)
        
        # Record error rate
        if status_code >= 400:
            self.metrics_collector.increment_counter("http_errors_total", tags=tags)
    
    def record_alert_metric(self, source: str, severity: str, action: str):
        """Record alert processing metrics"""
        tags = {
            "source": source,
            "severity": severity,
            "action": action
        }
        
        self.metrics_collector.increment_counter("alerts_processed_total", tags=tags)
    
    def record_incident_metric(self, action: str, severity: str):
        """Record incident metrics"""
        tags = {
            "action": action,
            "severity": severity
        }
        
        self.metrics_collector.increment_counter("incidents_processed_total", tags=tags)
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get comprehensive system metrics"""
        # System resource metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Application metrics
        app_metrics = self.metrics_collector.get_all_metrics()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "system": {
                "cpu_percent": cpu_percent,
                "memory": {
                    "total_gb": memory.total / (1024**3),
                    "available_gb": memory.available / (1024**3),
                    "usage_percent": memory.percent
                },
                "disk": {
                    "total_gb": disk.total / (1024**3),
                    "free_gb": disk.free / (1024**3),
                    "usage_percent": (disk.used / disk.total) * 100
                },
                "load_average": list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else None
            },
            "application": app_metrics
        }

# Global performance monitor instance
performance_monitor = PerformanceMonitor()

# Decorator for monitoring function performance
def monitor_performance(func_name: str = None):
    """Decorator to monitor function performance"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            name = func_name or f"{func.__module__}.{func.__name__}"
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                performance_monitor.metrics_collector.record_histogram(
                    f"function_duration_ms", duration_ms, {"function": name}
                )
                
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                
                performance_monitor.metrics_collector.record_histogram(
                    f"function_duration_ms", duration_ms, {"function": name, "status": "error"}
                )
                performance_monitor.metrics_collector.increment_counter(
                    "function_errors_total", {"function": name}
                )
                
                raise
        
        return wrapper
    return decorator

# Context manager for monitoring operations
@asynccontextmanager
async def monitor_operation(operation_name: str, tags: Dict[str, str] = None):
    """Context manager for monitoring operations"""
    tags = tags or {}
    start_time = time.time()
    
    try:
        performance_monitor.metrics_collector.increment_counter(
            "operations_started", {"operation": operation_name, **tags}
        )
        
        yield
        
        duration_ms = (time.time() - start_time) * 1000
        performance_monitor.metrics_collector.record_histogram(
            "operation_duration_ms", duration_ms, {"operation": operation_name, **tags}
        )
        performance_monitor.metrics_collector.increment_counter(
            "operations_completed", {"operation": operation_name, **tags}
        )
        
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        performance_monitor.metrics_collector.record_histogram(
            "operation_duration_ms", duration_ms, {"operation": operation_name, **tags, "status": "error"}
        )
        performance_monitor.metrics_collector.increment_counter(
            "operations_failed", {"operation": operation_name, **tags}
        )
        raise
