"""
Redis cache layer for MES API responses and LLM results.
"""
import os
import json
import hashlib
import logging
from typing import Any, Optional
from datetime import timedelta
import redis.asyncio as redis

logger = logging.getLogger(__name__)

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_ENABLED = os.getenv("REDIS_ENABLED", "true").lower() in ("true", "1", "yes")

# TTL defaults (in seconds)
DEFAULT_TTL = 300  # 5 minutes
MES_DATA_TTL = 600  # 10 minutes
LLM_RESULT_TTL = 1800  # 30 minutes
SESSION_TTL = 3600  # 1 hour


class RedisCache:
    """Redis cache manager."""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.enabled = REDIS_ENABLED
    
    async def connect(self):
        """Initialize Redis connection."""
        if not self.enabled:
            logger.info("Redis cache disabled")
            return
        
        try:
            self.redis_client = await redis.from_url(
                REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            await self.redis_client.ping()
            logger.info("Redis cache connected successfully")
        except Exception as e:
            logger.warning(f"Redis connection failed, cache disabled: {e}")
            self.enabled = False
            self.redis_client = None
    
    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
    
    def _make_key(self, prefix: str, data: dict) -> str:
        """Generate cache key from data."""
        # Sort keys for consistent hashing
        sorted_data = json.dumps(data, sort_keys=True, ensure_ascii=False)
        hash_val = hashlib.sha256(sorted_data.encode()).hexdigest()[:16]
        return f"{prefix}:{hash_val}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.enabled or not self.redis_client:
            return None
        
        try:
            value = await self.redis_client.get(key)
            if value:
                logger.debug(f"Cache HIT: {key}")
                return json.loads(value)
            logger.debug(f"Cache MISS: {key}")
            return None
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = DEFAULT_TTL):
        """Set value in cache with TTL."""
        if not self.enabled or not self.redis_client:
            return
        
        try:
            serialized = json.dumps(value, ensure_ascii=False)
            await self.redis_client.setex(key, ttl, serialized)
            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
    
    async def delete(self, key: str):
        """Delete key from cache."""
        if not self.enabled or not self.redis_client:
            return
        
        try:
            await self.redis_client.delete(key)
            logger.debug(f"Cache DEL: {key}")
        except Exception as e:
            logger.warning(f"Cache delete error: {e}")
    
    async def get_mes_data(self, execution_plan: dict) -> Optional[Any]:
        """Get cached MES API response."""
        key = self._make_key("mes_data", execution_plan)
        return await self.get(key)
    
    async def set_mes_data(self, execution_plan: dict, data: Any):
        """Cache MES API response."""
        key = self._make_key("mes_data", execution_plan)
        await self.set(key, data, ttl=MES_DATA_TTL)
    
    async def get_llm_result(self, prompt: str, model: str = "qwen2-7b") -> Optional[str]:
        """Get cached LLM response."""
        key = self._make_key("llm_result", {"prompt": prompt, "model": model})
        result = await self.get(key)
        return result.get("response") if result else None
    
    async def set_llm_result(self, prompt: str, response: str, model: str = "qwen2-7b"):
        """Cache LLM response."""
        key = self._make_key("llm_result", {"prompt": prompt, "model": model})
        await self.set(key, {"response": response, "model": model}, ttl=LLM_RESULT_TTL)
    
    async def get_session_context(self, session_id: str) -> Optional[dict]:
        """Get session context."""
        key = f"session:{session_id}"
        return await self.get(key)
    
    async def set_session_context(self, session_id: str, context: dict):
        """Cache session context."""
        key = f"session:{session_id}"
        await self.set(key, context, ttl=SESSION_TTL)
    
    async def extend_session(self, session_id: str):
        """Extend session TTL."""
        if not self.enabled or not self.redis_client:
            return
        
        try:
            key = f"session:{session_id}"
            await self.redis_client.expire(key, SESSION_TTL)
        except Exception as e:
            logger.warning(f"Session extend error: {e}")


# Global cache instance
cache = RedisCache()


async def init_cache():
    """Initialize cache connection."""
    await cache.connect()


async def cleanup_cache():
    """Cleanup cache connection."""
    await cache.close()
