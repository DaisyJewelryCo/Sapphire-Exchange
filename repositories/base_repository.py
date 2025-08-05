"""
Base repository pattern for Sapphire Exchange data access.
Provides common functionality for all repository implementations.
"""
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Type, TypeVar
from datetime import datetime, timezone

from security.performance_manager import PerformanceManager

T = TypeVar('T')


class BaseRepository(ABC):
    """Abstract base repository with common functionality."""
    
    def __init__(self, database=None, performance_manager: PerformanceManager = None):
        """Initialize base repository."""
        self.database = database
        self.performance_manager = performance_manager or PerformanceManager()
        self.cache_ttl = 300  # 5 minutes default
    
    @abstractmethod
    async def create(self, entity: T) -> Optional[T]:
        """Create a new entity."""
        pass
    
    @abstractmethod
    async def get_by_id(self, entity_id: str) -> Optional[T]:
        """Get entity by ID."""
        pass
    
    @abstractmethod
    async def update(self, entity: T) -> bool:
        """Update an existing entity."""
        pass
    
    @abstractmethod
    async def delete(self, entity_id: str) -> bool:
        """Delete an entity."""
        pass
    
    @abstractmethod
    async def list(self, limit: int = 20, offset: int = 0, **filters) -> List[T]:
        """List entities with pagination and filters."""
        pass
    
    def _get_cache_key(self, prefix: str, key: str) -> str:
        """Generate cache key."""
        return f"{prefix}_{key}"
    
    def _cache_entity(self, cache_key: str, entity: T, ttl_seconds: int = None):
        """Cache an entity."""
        try:
            ttl = ttl_seconds or self.cache_ttl
            self.performance_manager.set_cached_data(
                cache_key, entity, ttl_ms=ttl * 1000
            )
        except Exception as e:
            print(f"Error caching entity: {e}")
    
    def _get_cached_entity(self, cache_key: str) -> Optional[T]:
        """Get cached entity."""
        try:
            return self.performance_manager.get_cached_data(cache_key)
        except Exception as e:
            print(f"Error getting cached entity: {e}")
            return None
    
    def _invalidate_cache(self, cache_key: str):
        """Invalidate cached entity."""
        try:
            # Performance manager doesn't have explicit invalidation,
            # so we'll set with 0 TTL
            self.performance_manager.set_cached_data(cache_key, None, ttl_ms=0)
        except Exception as e:
            print(f"Error invalidating cache: {e}")
    
    def _validate_pagination(self, limit: int, offset: int) -> tuple[int, int]:
        """Validate and normalize pagination parameters."""
        limit = max(1, min(limit, 100))  # Between 1 and 100
        offset = max(0, offset)
        return limit, offset
    
    def _add_timestamps(self, entity: T, is_update: bool = False):
        """Add or update timestamps on entity."""
        try:
            current_time = datetime.now(timezone.utc).isoformat()
            
            if not is_update and hasattr(entity, 'created_at'):
                if not entity.created_at:
                    entity.created_at = current_time
            
            if hasattr(entity, 'updated_at'):
                entity.updated_at = current_time
        except Exception as e:
            print(f"Error adding timestamps: {e}")
    
    async def _batch_operation(self, operations: List[callable], batch_size: int = 10) -> List[Any]:
        """Execute operations in batches."""
        results = []
        
        for i in range(0, len(operations), batch_size):
            batch = operations[i:i + batch_size]
            batch_results = await asyncio.gather(*[op() for op in batch], return_exceptions=True)
            results.extend(batch_results)
        
        return results
    
    def _filter_exceptions(self, results: List[Any]) -> List[Any]:
        """Filter out exceptions from batch results."""
        return [result for result in results if not isinstance(result, Exception)]
    
    async def health_check(self) -> Dict[str, Any]:
        """Check repository health."""
        try:
            # Basic health check - try to access database
            if self.database:
                # This would be implemented based on the specific database
                return {
                    'status': 'healthy',
                    'database_connected': True,
                    'cache_available': self.performance_manager is not None,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            else:
                return {
                    'status': 'degraded',
                    'database_connected': False,
                    'cache_available': self.performance_manager is not None,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }


class ArweaveRepository(BaseRepository):
    """Repository implementation using Arweave for storage."""
    
    def __init__(self, database=None, performance_manager: PerformanceManager = None, 
                 blockchain_manager=None):
        """Initialize Arweave repository."""
        super().__init__(database, performance_manager)
        self.blockchain = blockchain_manager
        self.app_name = "Sapphire-Exchange"
    
    async def _store_on_arweave(self, data: Dict[str, Any], tags: List[tuple]) -> Optional[str]:
        """Store data on Arweave blockchain."""
        try:
            if self.blockchain:
                return await self.blockchain.store_data(data, tags)
            return None
        except Exception as e:
            print(f"Error storing on Arweave: {e}")
            return None
    
    async def _get_from_arweave(self, tx_id: str) -> Optional[Dict[str, Any]]:
        """Get data from Arweave blockchain."""
        try:
            if self.blockchain:
                return await self.blockchain.get_data(tx_id)
            return None
        except Exception as e:
            print(f"Error getting from Arweave: {e}")
            return None
    
    def _create_tags(self, data_type: str, entity_id: str, **extra_tags) -> List[tuple]:
        """Create Arweave tags for data."""
        tags = [
            ("Content-Type", "application/json"),
            ("App-Name", self.app_name),
            ("Data-Type", data_type),
            ("Entity-ID", entity_id),
            ("Timestamp", datetime.now(timezone.utc).isoformat())
        ]
        
        # Add extra tags
        for key, value in extra_tags.items():
            if value is not None:
                tags.append((key, str(value)))
        
        return tags