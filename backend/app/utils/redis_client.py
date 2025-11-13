import redis
import json
from typing import Any, Optional
from app.config import settings
import structlog

logger = structlog.get_logger()


class RedisClient:
    """Redis client wrapper"""
    
    def __init__(self):
        self._client: Optional[redis.Redis] = None
    
    def connect(self):
        """Connect to Redis"""
        try:
            self._client = redis.from_url(
                settings.redis_url,
                password=settings.redis_password if settings.redis_password else None,
                db=settings.redis_db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            self._client.ping()
            logger.info("Connected to Redis successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._client = None
    
    def disconnect(self):
        """Disconnect from Redis"""
        if self._client:
            self._client.close()
            logger.info("Disconnected from Redis")
    
    @property
    def client(self) -> Optional[redis.Redis]:
        """Get Redis client"""
        if not self._client:
            self.connect()
        return self._client
    
    def get(self, key: str) -> Optional[str]:
        """Get value from Redis"""
        try:
            if self.client:
                return self.client.get(key)
        except Exception as e:
            logger.error(f"Redis GET error: {e}", key=key)
        return None
    
    def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """Set value in Redis"""
        try:
            if self.client:
                if ttl:
                    self.client.setex(key, ttl, value)
                else:
                    self.client.set(key, value)
                return True
        except Exception as e:
            logger.error(f"Redis SET error: {e}", key=key)
        return False
    
    def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        try:
            if self.client:
                self.client.delete(key)
                return True
        except Exception as e:
            logger.error(f"Redis DELETE error: {e}", key=key)
        return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            if self.client:
                return bool(self.client.exists(key))
        except Exception as e:
            logger.error(f"Redis EXISTS error: {e}", key=key)
        return False
    
    def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern"""
        try:
            if self.client:
                keys = self.client.keys(pattern)
                if keys:
                    return self.client.delete(*keys)
                return 0
        except Exception as e:
            logger.error(f"Redis DELETE_PATTERN error: {e}", pattern=pattern)
        return 0


# Global Redis client instance
redis_client = RedisClient()


def cache_get(key: str) -> Optional[Any]:
    """Get cached value and deserialize"""
    value = redis_client.get(key)
    if value:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return None


def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """Serialize and cache value"""
    try:
        if ttl is None:
            ttl = settings.cache_ttl
        
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        elif not isinstance(value, str):
            value = str(value)
        
        return redis_client.set(key, value, ttl)
    except Exception as e:
        logger.error(f"Cache SET error: {e}", key=key)
        return False


def cache_delete(key: str) -> bool:
    """Delete cached value"""
    return redis_client.delete(key)


def cache_key(prefix: str, *args) -> str:
    """Generate cache key"""
    return f"{prefix}:{':'.join(map(str, args))}"
