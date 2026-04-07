import asyncio
import time
from typing import Dict, Any, List, Optional, Callable, TypeVar, Generic
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import structlog
import queue
import threading
from abc import ABC, abstractmethod

logger = structlog.get_logger()

T = TypeVar('T')

@dataclass
class TaskResult:
    task_id: str
    status: str  # pending, running, completed, failed
    result: Any = None
    error: Optional[Exception] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    retry_count: int = 0

class WorkerPool:
    """Generic worker pool for async and sync tasks"""
    
    def __init__(
        self,
        max_workers: int = 10,
        worker_type: str = "thread",  # thread, process
        queue_size: int = 1000
    ):
        self.max_workers = max_workers
        self.worker_type = worker_type
        self.queue_size = queue_size
        self.task_queue = asyncio.Queue(maxsize=queue_size)
        self.results: Dict[str, TaskResult] = {}
        self.workers = []
        self.running = False
        self.executor = None
        
    async def start(self):
        """Start the worker pool"""
        if self.running:
            return
        
        self.running = True
        
        # Create executor
        if self.worker_type == "thread":
            self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        elif self.worker_type == "process":
            self.executor = ProcessPoolExecutor(max_workers=self.max_workers)
        
        # Start workers
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self.workers.append(worker)
        
        logger.info(f"Started {self.max_workers} {self.worker_type} workers")
    
    async def stop(self):
        """Stop the worker pool"""
        if not self.running:
            return
        
        self.running = False
        
        # Cancel workers
        for worker in self.workers:
            worker.cancel()
        
        # Wait for workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)
        
        # Shutdown executor
        if self.executor:
            self.executor.shutdown(wait=True)
        
        logger.info("Worker pool stopped")
    
    async def submit_task(
        self,
        task_id: str,
        func: Callable,
        *args,
        **kwargs
    ) -> TaskResult:
        """Submit a task to the worker pool"""
        if not self.running:
            raise RuntimeError("Worker pool is not running")
        
        # Create task result
        task_result = TaskResult(task_id=task_id, status="pending")
        self.results[task_id] = task_result
        
        # Submit to queue
        task_data = {
            "task_id": task_id,
            "func": func,
            "args": args,
            "kwargs": kwargs
        }
        
        await self.task_queue.put(task_data)
        return task_result
    
    async def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """Get task result"""
        return self.results.get(task_id)
    
    async def wait_for_task(self, task_id: str, timeout_seconds: float = 30.0) -> TaskResult:
        """Wait for task completion"""
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            result = self.results.get(task_id)
            if result and result.status in ["completed", "failed"]:
                return result
            
            await asyncio.sleep(0.1)
        
        raise TimeoutError(f"Task {task_id} did not complete within {timeout_seconds} seconds")
    
    async def _worker(self, worker_name: str):
        """Worker function"""
        logger.info(f"Worker {worker_name} started")
        
        while self.running:
            try:
                # Get task from queue
                task_data = await asyncio.wait_for(
                    self.task_queue.get(),
                    timeout=1.0
                )
                
                await self._process_task(task_data, worker_name)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Worker {worker_name} error: {str(e)}")
        
        logger.info(f"Worker {worker_name} stopped")
    
    async def _process_task(self, task_data: Dict[str, Any], worker_name: str):
        """Process a single task"""
        task_id = task_data["task_id"]
        func = task_data["func"]
        args = task_data["args"]
        kwargs = task_data["kwargs"]
        
        # Update task status
        task_result = self.results[task_id]
        task_result.status = "running"
        task_result.started_at = datetime.utcnow()
        
        try:
            # Execute function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                # Run in executor for sync functions
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    self.executor, func, *args, **kwargs
                )
            
            # Update result
            task_result.status = "completed"
            task_result.result = result
            task_result.completed_at = datetime.utcnow()
            task_result.duration_ms = (
                task_result.completed_at - task_result.started_at
            ).total_seconds() * 1000
            
            logger.debug(f"Task {task_id} completed by {worker_name}")
            
        except Exception as e:
            # Update error
            task_result.status = "failed"
            task_result.error = e
            task_result.completed_at = datetime.utcnow()
            task_result.duration_ms = (
                task_result.completed_at - task_result.started_at
            ).total_seconds() * 1000
            
            logger.error(f"Task {task_id} failed: {str(e)}")

class RateLimiter:
    """Rate limiter for API calls and operations"""
    
    def __init__(self, max_requests: int, time_window_seconds: int):
        self.max_requests = max_requests
        self.time_window = timedelta(seconds=time_window_seconds)
        self.requests = []
        self.lock = asyncio.Lock()
    
    async def acquire(self) -> bool:
        """Acquire a request slot"""
        async with self.lock:
            now = datetime.utcnow()
            
            # Remove old requests
            self.requests = [
                req_time for req_time in self.requests
                if now - req_time < self.time_window
            ]
            
            # Check if we can make a request
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True
            
            return False
    
    async def wait_for_slot(self, timeout_seconds: float = 30.0) -> bool:
        """Wait for an available slot"""
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            if await self.acquire():
                return True
            
            await asyncio.sleep(0.1)
        
        return False

class CircuitBreaker:
    """Circuit breaker for external service calls"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout_seconds: int = 60,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = timedelta(seconds=recovery_timeout_seconds)
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open
        self.lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Call function with circuit breaker protection"""
        async with self.lock:
            if self.state == "open":
                if self._should_attempt_reset():
                    self.state = "half_open"
                else:
                    raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            
            async with self.lock:
                if self.state == "half_open":
                    self.state = "closed"
                    self.failure_count = 0
                
            return result
            
        except self.expected_exception as e:
            async with self.lock:
                self.failure_count += 1
                self.last_failure_time = datetime.utcnow()
                
                if self.failure_count >= self.failure_threshold:
                    self.state = "open"
            
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit breaker"""
        return (
            self.last_failure_time and
            datetime.utcnow() - self.last_failure_time >= self.recovery_timeout
        )

class LoadBalancer:
    """Simple load balancer for multiple service instances"""
    
    def __init__(self, instances: List[str]):
        self.instances = instances
        self.current_index = 0
        self.health_status = {instance: True for instance in instances}
        self.lock = asyncio.Lock()
    
    async def get_next_instance(self) -> Optional[str]:
        """Get next healthy instance"""
        async with self.lock:
            # Find healthy instances
            healthy_instances = [
                instance for instance in self.instances
                if self.health_status.get(instance, True)
            ]
            
            if not healthy_instances:
                return None
            
            # Round-robin selection
            instance = healthy_instances[self.current_index % len(healthy_instances)]
            self.current_index += 1
            
            return instance
    
    async def mark_unhealthy(self, instance: str):
        """Mark instance as unhealthy"""
        async with self.lock:
            self.health_status[instance] = False
    
    async def mark_healthy(self, instance: str):
        """Mark instance as healthy"""
        async with self.lock:
            self.health_status[instance] = True

class BatchProcessor:
    """Batch processor for efficient bulk operations"""
    
    def __init__(
        self,
        batch_size: int = 100,
        flush_interval_seconds: int = 5,
        max_wait_seconds: int = 30
    ):
        self.batch_size = batch_size
        self.flush_interval = timedelta(seconds=flush_interval_seconds)
        self.max_wait = timedelta(seconds=max_wait_seconds)
        
        self.items = []
        self.last_flush = datetime.utcnow()
        self.lock = asyncio.Lock()
        self.running = False
        self.flush_task = None
    
    async def start(self):
        """Start the batch processor"""
        if self.running:
            return
        
        self.running = True
        self.flush_task = asyncio.create_task(self._flush_loop())
        logger.info("Batch processor started")
    
    async def stop(self):
        """Stop the batch processor"""
        if not self.running:
            return
        
        self.running = False
        
        # Cancel flush task
        if self.flush_task:
            self.flush_task.cancel()
            try:
                await self.flush_task
            except asyncio.CancelledError:
                pass
        
        # Flush remaining items
        await self.flush()
        
        logger.info("Batch processor stopped")
    
    async def add_item(self, item: Any):
        """Add item to batch"""
        async with self.lock:
            self.items.append(item)
            
            # Check if we should flush
            if len(self.items) >= self.batch_size:
                await self.flush()
    
    async def flush(self):
        """Flush current batch"""
        async with self.lock:
            if not self.items:
                return
            
            items_to_process = self.items.copy()
            self.items.clear()
            self.last_flush = datetime.utcnow()
        
        # Process items outside of lock
        try:
            await self._process_batch(items_to_process)
            logger.debug(f"Processed batch of {len(items_to_process)} items")
        except Exception as e:
            logger.error(f"Failed to process batch: {str(e)}")
    
    async def _flush_loop(self):
        """Background flush loop"""
        while self.running:
            try:
                await asyncio.sleep(1)
                
                async with self.lock:
                    time_since_flush = datetime.utcnow() - self.last_flush
                    
                    if self.items and (
                        time_since_flush >= self.flush_interval or
                        time_since_flush >= self.max_wait
                    ):
                        items_to_process = self.items.copy()
                        self.items.clear()
                        self.last_flush = datetime.utcnow()
                    
                    else:
                        continue
                
                # Process items outside of lock
                try:
                    await self._process_batch(items_to_process)
                    logger.debug(f"Processed batch of {len(items_to_process)} items")
                except Exception as e:
                    logger.error(f"Failed to process batch: {str(e)}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Flush loop error: {str(e)}")
    
    async def _process_batch(self, items: List[Any]):
        """Override this method in subclasses"""
        raise NotImplementedError("Subclasses must implement _process_batch")

class ScalabilityManager:
    """Main scalability manager"""
    
    def __init__(self):
        self.worker_pools = {}
        self.rate_limiters = {}
        self.circuit_breakers = {}
        self.load_balancers = {}
        self.batch_processors = {}
    
    def create_worker_pool(
        self,
        name: str,
        max_workers: int = 10,
        worker_type: str = "thread",
        queue_size: int = 1000
    ) -> WorkerPool:
        """Create a worker pool"""
        pool = WorkerPool(max_workers, worker_type, queue_size)
        self.worker_pools[name] = pool
        return pool
    
    def create_rate_limiter(
        self,
        name: str,
        max_requests: int,
        time_window_seconds: int
    ) -> RateLimiter:
        """Create a rate limiter"""
        limiter = RateLimiter(max_requests, time_window_seconds)
        self.rate_limiters[name] = limiter
        return limiter
    
    def create_circuit_breaker(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout_seconds: int = 60,
        expected_exception: type = Exception
    ) -> CircuitBreaker:
        """Create a circuit breaker"""
        breaker = CircuitBreaker(failure_threshold, recovery_timeout_seconds, expected_exception)
        self.circuit_breakers[name] = breaker
        return breaker
    
    def create_load_balancer(self, name: str, instances: List[str]) -> LoadBalancer:
        """Create a load balancer"""
        balancer = LoadBalancer(instances)
        self.load_balancers[name] = balancer
        return balancer
    
    def create_batch_processor(
        self,
        name: str,
        batch_size: int = 100,
        flush_interval_seconds: int = 5,
        max_wait_seconds: int = 30
    ) -> BatchProcessor:
        """Create a batch processor"""
        processor = BatchProcessor(batch_size, flush_interval_seconds, max_wait_seconds)
        self.batch_processors[name] = processor
        return processor
    
    async def start_all(self):
        """Start all components"""
        for pool in self.worker_pools.values():
            await pool.start()
        
        for processor in self.batch_processors.values():
            await processor.start()
    
    async def stop_all(self):
        """Stop all components"""
        for pool in self.worker_pools.values():
            await pool.stop()
        
        for processor in self.batch_processors.values():
            await processor.stop()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics from all components"""
        stats = {
            "timestamp": datetime.utcnow().isoformat(),
            "worker_pools": {},
            "rate_limiters": {},
            "circuit_breakers": {},
            "load_balancers": {},
            "batch_processors": {}
        }
        
        # Worker pool stats
        for name, pool in self.worker_pools.items():
            stats["worker_pools"][name] = {
                "max_workers": pool.max_workers,
                "queue_size": pool.queue_size,
                "running": pool.running,
                "pending_tasks": pool.task_queue.qsize(),
                "active_tasks": len([r for r in pool.results.values() if r.status == "running"])
            }
        
        # Rate limiter stats
        for name, limiter in self.rate_limiters.items():
            stats["rate_limiters"][name] = {
                "max_requests": limiter.max_requests,
                "current_requests": len(limiter.requests),
                "time_window_seconds": limiter.time_window.total_seconds()
            }
        
        # Circuit breaker stats
        for name, breaker in self.circuit_breakers.items():
            stats["circuit_breakers"][name] = {
                "state": breaker.state,
                "failure_count": breaker.failure_count,
                "failure_threshold": breaker.failure_threshold
            }
        
        # Load balancer stats
        for name, balancer in self.load_balancers.items():
            stats["load_balancers"][name] = {
                "total_instances": len(balancer.instances),
                "healthy_instances": len([
                    i for i in balancer.instances
                    if balancer.health_status.get(i, True)
                ])
            }
        
        # Batch processor stats
        for name, processor in self.batch_processors.items():
            stats["batch_processors"][name] = {
                "batch_size": processor.batch_size,
                "current_items": len(processor.items),
                "running": processor.running
            }
        
        return stats

# Global scalability manager
scalability_manager = ScalabilityManager()

# Decorators for common patterns
def rate_limited(limiter_name: str):
    """Decorator for rate limiting"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            limiter = scalability_manager.rate_limiters.get(limiter_name)
            if limiter:
                if not await limiter.wait_for_slot():
                    raise Exception("Rate limit exceeded")
            
            return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
        return wrapper
    return decorator

def circuit_breaker_protected(breaker_name: str):
    """Decorator for circuit breaker protection"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            breaker = scalability_manager.circuit_breakers.get(breaker_name)
            if breaker:
                return await breaker.call(func, *args, **kwargs)
            else:
                return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
        return wrapper
    return decorator

def worker_pool_executed(pool_name: str):
    """Decorator for executing in worker pool"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            pool = scalability_manager.worker_pools.get(pool_name)
            if pool:
                task_id = f"{func.__name__}_{int(time.time() * 1000)}"
                task_result = await pool.submit_task(task_id, func, *args, **kwargs)
                result = await pool.wait_for_task(task_id)
                
                if result.status == "completed":
                    return result.result
                else:
                    raise result.error
            else:
                return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
        return wrapper
    return decorator
