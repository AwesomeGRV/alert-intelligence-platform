import json
import pickle
import asyncio
from typing import Any, Optional, Dict, List, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
import hashlib
import structlog
from abc import ABC, abstractmethod

logger = structlog.get_logger()

@dataclass
class CacheEntry:
    key: str
    value: Any
    expires_at: Optional[datetime]
    created_at: datetime
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    size_bytes: int = 0

class CacheBackend(ABC):
    """Abstract base class for cache backends"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[CacheEntry]:
        """Get value from cache"""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Set value in cache"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        pass
    
    @abstractmethod
    async def clear(self) -> bool:
        """Clear all cache entries"""
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        pass

class MemoryCache(CacheBackend):
    """In-memory cache backend"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, CacheEntry] = {}
        self.lock = asyncio.Lock()
        self.hits = 0
        self.misses = 0
        self.sets = 0
    
    async def get(self, key: str) -> Optional[CacheEntry]:
        """Get value from memory cache"""
        async with self.lock:
            if key not in self.cache:
                self.misses += 1
                return None
            
            entry = self.cache[key]
            
            # Check if expired
            if entry.expires_at and datetime.utcnow() > entry.expires_at:
                del self.cache[key]
                self.misses += 1
                return None
            
            # Update access statistics
            entry.access_count += 1
            entry.last_accessed = datetime.utcnow()
            self.hits += 1
            
            return entry
    
    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Set value in memory cache"""
        async with self.lock:
            try:
                # Serialize value to estimate size
                serialized = pickle.dumps(value)
                size_bytes = len(serialized)
                
                # Check if we need to evict entries
                if len(self.cache) >= self.max_size:
                    await self._evict_lru()
                
                # Calculate expiration
                ttl = ttl_seconds or self.default_ttl
                expires_at = datetime.utcnow() + timedelta(seconds=ttl) if ttl > 0 else None
                
                # Create cache entry
                entry = CacheEntry(
                    key=key,
                    value=value,
                    expires_at=expires_at,
                    created_at=datetime.utcnow(),
                    size_bytes=size_bytes
                )
                
                self.cache[key] = entry
                self.sets += 1
                return True
                
            except Exception as e:
                logger.error(f"Failed to set cache entry: {str(e)}")
                return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from memory cache"""
        async with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    async def clear(self) -> bool:
        """Clear all cache entries"""
        async with self.lock:
            self.cache.clear()
            return True
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get memory cache statistics"""
        async with self.lock:
            total_size = sum(entry.size_bytes for entry in self.cache.values())
            expired_count = sum(
                1 for entry in self.cache.values()
                if entry.expires_at and datetime.utcnow() > entry.expires_at
            )
            
            return {
                "type": "memory",
                "entries": len(self.cache),
                "max_size": self.max_size,
                "hits": self.hits,
                "misses": self.misses,
                "sets": self.sets,
                "hit_rate": self.hits / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0,
                "total_size_bytes": total_size,
                "expired_entries": expired_count,
                "memory_usage_mb": total_size / (1024 * 1024)
            }
    
    async def _evict_lru(self):
        """Evict least recently used entries"""
        if not self.cache:
            return
        
        # Sort by last accessed time
        sorted_entries = sorted(
            self.cache.items(),
            key=lambda x: x[1].last_accessed or x[1].created_at
        )
        
        # Remove oldest 10% of entries
        evict_count = max(1, len(sorted_entries) // 10)
        for i in range(evict_count):
            key = sorted_entries[i][0]
            del self.cache[key]

class RedisCache(CacheBackend):
    """Redis cache backend"""
    
    def __init__(self, redis_client, default_ttl: int = 3600):
        self.redis = redis_client
        self.default_ttl = default_ttl
        self.key_prefix = "alert_intelligence:"
    
    def _make_key(self, key: str) -> str:
        """Create Redis key with prefix"""
        return f"{self.key_prefix}{key}"
    
    async def get(self, key: str) -> Optional[CacheEntry]:
        """Get value from Redis cache"""
        try:
            redis_key = self._make_key(key)
            data = await self.redis.get(redis_key)
            
            if not data:
                return None
            
            # Deserialize cache entry
            entry_data = pickle.loads(data)
            entry = CacheEntry(**entry_data)
            
            # Check if expired (Redis handles TTL, but double-check)
            if entry.expires_at and datetime.utcnow() > entry.expires_at:
                await self.delete(key)
                return None
            
            # Update access statistics
            entry.access_count += 1
            entry.last_accessed = datetime.utcnow()
            
            # Update access count in Redis
            await self.redis.hset(redis_key, "access_count", entry.access_count)
            
            return entry
            
        except Exception as e:
            logger.error(f"Failed to get from Redis cache: {str(e)}")
            return None
    
    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Set value in Redis cache"""
        try:
            redis_key = self._make_key(key)
            ttl = ttl_seconds or self.default_ttl
            
            # Serialize value to estimate size
            serialized = pickle.dumps(value)
            size_bytes = len(serialized)
            
            # Create cache entry
            entry = CacheEntry(
                key=key,
                value=value,
                expires_at=datetime.utcnow() + timedelta(seconds=ttl) if ttl > 0 else None,
                created_at=datetime.utcnow(),
                size_bytes=size_bytes
            )
            
            # Serialize entry
            entry_data = pickle.dumps(entry.__dict__)
            
            # Set in Redis with TTL
            await self.redis.setex(redis_key, ttl, entry_data)
            return True
            
        except Exception as e:
            logger.error(f"Failed to set in Redis cache: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from Redis cache"""
        try:
            redis_key = self._make_key(key)
            result = await self.redis.delete(redis_key)
            return result > 0
        except Exception as e:
            logger.error(f"Failed to delete from Redis cache: {str(e)}")
            return False
    
    async def clear(self) -> bool:
        """Clear all cache entries"""
        try:
            # Delete all keys with our prefix
            pattern = f"{self.key_prefix}*"
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
            return True
        except Exception as e:
            logger.error(f"Failed to clear Redis cache: {str(e)}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get Redis cache statistics"""
        try:
            info = await self.redis.info()
            pattern = f"{self.key_prefix}*"
            keys = await self.redis.keys(pattern)
            
            return {
                "type": "redis",
                "entries": len(keys),
                "memory_usage_bytes": info.get("used_memory", 0),
                "memory_usage_mb": info.get("used_memory", 0) / (1024 * 1024),
                "connected_clients": info.get("connected_clients", 0),
                "redis_version": info.get("redis_version"),
                "uptime_seconds": info.get("uptime_in_seconds", 0)
            }
        except Exception as e:
            logger.error(f"Failed to get Redis cache stats: {str(e)}")
            return {"type": "redis", "error": str(e)}

class CacheManager:
    """Multi-tier cache manager"""
    
    def __init__(self, l1_cache: CacheBackend, l2_cache: Optional[CacheBackend] = None):
        self.l1_cache = l1_cache  # Fast cache (memory)
        self.l2_cache = l2_cache  # Slower cache (Redis)
        self.lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache (L1 first, then L2)"""
        # Try L1 cache first
        entry = await self.l1_cache.get(key)
        if entry:
            return entry.value
        
        # Try L2 cache if available
        if self.l2_cache:
            entry = await self.l2_cache.get(key)
            if entry:
                # Promote to L1 cache
                await self.l1_cache.set(key, entry.value)
                return entry.value
        
        return None
    
    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Set value in both cache tiers"""
        success = True
        
        # Set in L1 cache
        l1_success = await self.l1_cache.set(key, value, ttl_seconds)
        success = success and l1_success
        
        # Set in L2 cache if available
        if self.l2_cache:
            l2_success = await self.l2_cache.set(key, value, ttl_seconds)
            success = success and l2_success
        
        return success
    
    async def delete(self, key: str) -> bool:
        """Delete from both cache tiers"""
        l1_success = await self.l1_cache.delete(key)
        l2_success = True
        
        if self.l2_cache:
            l2_success = await self.l2_cache.delete(key)
        
        return l1_success or l2_success
    
    async def clear(self) -> bool:
        """Clear both cache tiers"""
        l1_success = await self.l1_cache.clear()
        l2_success = True
        
        if self.l2_cache:
            l2_success = await self.l2_cache.clear()
        
        return l1_success and l2_success
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics from all cache tiers"""
        stats = {
            "timestamp": datetime.utcnow().isoformat(),
            "tiers": {}
        }
        
        # L1 cache stats
        l1_stats = await self.l1_cache.get_stats()
        stats["tiers"]["l1"] = l1_stats
        
        # L2 cache stats if available
        if self.l2_cache:
            l2_stats = await self.l2_cache.get_stats()
            stats["tiers"]["l2"] = l2_stats
        
        return stats

class CacheDecorator:
    """Decorator for caching function results"""
    
    def __init__(
        self,
        cache_manager: CacheManager,
        ttl_seconds: int = 3600,
        key_prefix: str = "",
        include_args: bool = True,
        include_kwargs: bool = True
    ):
        self.cache_manager = cache_manager
        self.ttl_seconds = ttl_seconds
        self.key_prefix = key_prefix
        self.include_args = include_args
        self.include_kwargs = include_kwargs
    
    def __call__(self, func):
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = self._generate_cache_key(func, args, kwargs)
            
            # Try to get from cache
            cached_result = await self.cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await self.cache_manager.set(cache_key, result, self.ttl_seconds)
            
            return result
        
        return wrapper
    
    def _generate_cache_key(self, func, args, kwargs) -> str:
        """Generate cache key for function call"""
        key_parts = [self.key_prefix, func.__module__, func.__name__]
        
        if self.include_args and args:
            # Convert args to string representation
            args_str = str(args[1:]) if args else ""  # Skip 'self' parameter
            key_parts.append(args_str)
        
        if self.include_kwargs and kwargs:
            # Sort kwargs for consistent key generation
            sorted_kwargs = sorted(kwargs.items())
            kwargs_str = str(sorted_kwargs)
            key_parts.append(kwargs_str)
        
        # Create hash of key parts
        key_string = ":".join(key_parts)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        
        return f"func:{key_hash}"

# Global cache instances
memory_cache = MemoryCache(max_size=1000, default_ttl=3600)
cache_manager = CacheManager(memory_cache)  # L1 only for now

# Cache decorators
def cached(ttl_seconds: int = 3600, key_prefix: str = ""):
    """Decorator for caching function results"""
    return CacheDecorator(cache_manager, ttl_seconds, key_prefix)

def cache_result(key: str, ttl_seconds: int = 3600):
    """Decorator for caching with specific key"""
    return CacheDecorator(cache_manager, ttl_seconds, key, include_args=False, include_kwargs=False)

# Utility functions for common caching patterns
async def cache_alert(alert_id: str, alert_data: Dict[str, Any], ttl_seconds: int = 3600):
    """Cache alert data"""
    key = f"alert:{alert_id}"
    await cache_manager.set(key, alert_data, ttl_seconds)

async def get_cached_alert(alert_id: str) -> Optional[Dict[str, Any]]:
    """Get cached alert data"""
    key = f"alert:{alert_id}"
    return await cache_manager.get(key)

async def cache_incident(incident_id: str, incident_data: Dict[str, Any], ttl_seconds: int = 3600):
    """Cache incident data"""
    key = f"incident:{incident_id}"
    await cache_manager.set(key, incident_data, ttl_seconds)

async def get_cached_incident(incident_id: str) -> Optional[Dict[str, Any]]:
    """Get cached incident data"""
    key = f"incident:{incident_id}"
    return await cache_manager.get(key)

async def cache_user_permissions(user_id: str, permissions: List[str], ttl_seconds: int = 1800):
    """Cache user permissions"""
    key = f"permissions:{user_id}"
    await cache_manager.set(key, permissions, ttl_seconds)

async def get_cached_user_permissions(user_id: str) -> Optional[List[str]]:
    """Get cached user permissions"""
    key = f"permissions:{user_id}"
    return await cache_manager.get(key)

async def invalidate_user_cache(user_id: str):
    """Invalidate all cache entries for a user"""
    patterns = [
        f"permissions:{user_id}",
        f"user:{user_id}",
        f"session:{user_id}"
    ]
    
    for pattern in patterns:
        await cache_manager.delete(pattern)
