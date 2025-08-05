"""
Performance optimization manager for Sapphire Exchange.
Implements caching, batch processing, and concurrent request management.
"""
import asyncio
import time
from typing import Any, List, Dict, Optional, Callable, Tuple
from dataclasses import dataclass, field
import json
import hashlib


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    data: Any
    timestamp: float
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    ttl_ms: int = 300000  # 5 minutes default


class PerformanceManager:
    """Performance optimization following robot_info.json specifications."""
    
    def __init__(self):
        # From performance_parameters section
        self.cache_ttl_ms = 300000  # 5 minutes
        self.batch_size = 50
        self.max_concurrent_requests = 10
        self.request_timeout_ms = 30000
        
        # Initialize cache
        self.cache = {}
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'total_requests': 0
        }
        
        # Performance metrics
        self.metrics = {
            'request_times': [],
            'cache_hit_rate': 0.0,
            'average_response_time': 0.0,
            'concurrent_requests': 0
        }
        
    def get_cached_data(self, key: str) -> Optional[Any]:
        """Get data from cache if not expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached data or None if not found/expired
        """
        self.cache_stats['total_requests'] += 1
        
        if key not in self.cache:
            self.cache_stats['misses'] += 1
            return None
            
        entry = self.cache[key]
        current_time = time.time() * 1000  # Convert to milliseconds
        
        # Check if cache entry has expired
        if current_time - entry.timestamp > entry.ttl_ms:
            # Cache expired, remove entry
            del self.cache[key]
            self.cache_stats['misses'] += 1
            self.cache_stats['evictions'] += 1
            return None
        
        # Update access statistics
        entry.access_count += 1
        entry.last_accessed = current_time
        self.cache_stats['hits'] += 1
        
        # Update hit rate
        self._update_cache_hit_rate()
        
        return entry.data
    
    def set_cached_data(self, key: str, data: Any, ttl_ms: int = None):
        """Store data in cache with timestamp.
        
        Args:
            key: Cache key
            data: Data to cache
            ttl_ms: Time to live in milliseconds (uses default if None)
        """
        if ttl_ms is None:
            ttl_ms = self.cache_ttl_ms
            
        entry = CacheEntry(
            data=data,
            timestamp=time.time() * 1000,
            ttl_ms=ttl_ms
        )
        
        self.cache[key] = entry
        
        # Perform cache cleanup if needed
        self._cleanup_cache_if_needed()
    
    def invalidate_cache(self, key: str = None, pattern: str = None):
        """Invalidate cache entries.
        
        Args:
            key: Specific key to invalidate (None for all)
            pattern: Pattern to match keys for invalidation
        """
        if key:
            if key in self.cache:
                del self.cache[key]
                self.cache_stats['evictions'] += 1
        elif pattern:
            keys_to_remove = [
                k for k in self.cache.keys() 
                if pattern in k
            ]
            for k in keys_to_remove:
                del self.cache[k]
                self.cache_stats['evictions'] += 1
        else:
            # Clear all cache
            evicted_count = len(self.cache)
            self.cache.clear()
            self.cache_stats['evictions'] += evicted_count
    
    def _cleanup_cache_if_needed(self, max_entries: int = 1000):
        """Clean up cache if it gets too large."""
        if len(self.cache) <= max_entries:
            return
            
        # Remove expired entries first
        current_time = time.time() * 1000
        expired_keys = []
        
        for key, entry in self.cache.items():
            if current_time - entry.timestamp > entry.ttl_ms:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
            self.cache_stats['evictions'] += 1
        
        # If still too many entries, remove least recently used
        if len(self.cache) > max_entries:
            # Sort by last accessed time
            sorted_entries = sorted(
                self.cache.items(),
                key=lambda x: x[1].last_accessed
            )
            
            # Remove oldest entries
            entries_to_remove = len(self.cache) - max_entries
            for i in range(entries_to_remove):
                key = sorted_entries[i][0]
                del self.cache[key]
                self.cache_stats['evictions'] += 1
    
    def _update_cache_hit_rate(self):
        """Update cache hit rate metric."""
        total = self.cache_stats['hits'] + self.cache_stats['misses']
        if total > 0:
            self.metrics['cache_hit_rate'] = self.cache_stats['hits'] / total
    
    async def batch_process(self, items: List, process_func: Callable, 
                          batch_size: int = None, timeout_ms: int = None) -> List:
        """Process items in batches to optimize performance.
        
        Args:
            items: List of items to process
            process_func: Async function to process each item
            batch_size: Batch size (uses default if None)
            timeout_ms: Timeout in milliseconds (uses default if None)
            
        Returns:
            List of results
        """
        if batch_size is None:
            batch_size = self.batch_size
        if timeout_ms is None:
            timeout_ms = self.request_timeout_ms
            
        results = []
        start_time = time.time()
        
        try:
            for i in range(0, len(items), batch_size):
                batch = items[i:i + batch_size]
                
                # Process batch with concurrency limit
                semaphore = asyncio.Semaphore(self.max_concurrent_requests)
                
                async def process_with_semaphore(item):
                    async with semaphore:
                        self.metrics['concurrent_requests'] += 1
                        try:
                            return await asyncio.wait_for(
                                process_func(item),
                                timeout=timeout_ms / 1000
                            )
                        finally:
                            self.metrics['concurrent_requests'] -= 1
                
                batch_results = await asyncio.gather(
                    *[process_with_semaphore(item) for item in batch],
                    return_exceptions=True
                )
                
                results.extend(batch_results)
                
        except Exception as e:
            # Log error and continue with partial results
            print(f"Batch processing error: {e}")
        
        # Update performance metrics
        end_time = time.time()
        processing_time = (end_time - start_time) * 1000  # Convert to ms
        self.metrics['request_times'].append(processing_time)
        self._update_average_response_time()
        
        return results
    
    def _update_average_response_time(self):
        """Update average response time metric."""
        if self.metrics['request_times']:
            # Keep only last 100 measurements
            if len(self.metrics['request_times']) > 100:
                self.metrics['request_times'] = self.metrics['request_times'][-100:]
            
            self.metrics['average_response_time'] = sum(
                self.metrics['request_times']
            ) / len(self.metrics['request_times'])
    
    async def concurrent_execute(self, tasks: List[Callable], 
                               max_concurrent: int = None) -> List:
        """Execute tasks concurrently with limit.
        
        Args:
            tasks: List of async callables to execute
            max_concurrent: Maximum concurrent tasks (uses default if None)
            
        Returns:
            List of results
        """
        if max_concurrent is None:
            max_concurrent = self.max_concurrent_requests
            
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def execute_with_semaphore(task):
            async with semaphore:
                self.metrics['concurrent_requests'] += 1
                try:
                    return await task()
                finally:
                    self.metrics['concurrent_requests'] -= 1
        
        return await asyncio.gather(
            *[execute_with_semaphore(task) for task in tasks],
            return_exceptions=True
        )
    
    def create_cache_key(self, *args, **kwargs) -> str:
        """Create a cache key from arguments.
        
        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            SHA-256 hash as cache key
        """
        # Create a deterministic string from arguments
        key_data = {
            'args': args,
            'kwargs': sorted(kwargs.items())  # Sort for consistency
        }
        
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    def get_performance_stats(self) -> Dict:
        """Get current performance statistics.
        
        Returns:
            Dict containing performance metrics
        """
        return {
            'cache_stats': self.cache_stats.copy(),
            'cache_size': len(self.cache),
            'metrics': self.metrics.copy(),
            'cache_hit_rate_percent': self.metrics['cache_hit_rate'] * 100,
            'average_response_time_ms': self.metrics['average_response_time'],
            'current_concurrent_requests': self.metrics['concurrent_requests']
        }
    
    def reset_stats(self):
        """Reset performance statistics."""
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'total_requests': 0
        }
        self.metrics = {
            'request_times': [],
            'cache_hit_rate': 0.0,
            'average_response_time': 0.0,
            'concurrent_requests': 0
        }


class NetworkErrorHandler:
    """Robust network error handling with retry logic."""
    
    def __init__(self):
        # From error_handling section in robot_info.json
        self.timeout_ms = 10000
        self.max_retries = 3
        self.backoff_factor = 2
        
    async def execute_with_retry(self, operation: Callable, *args, **kwargs):
        """Execute operation with exponential backoff retry.
        
        Args:
            operation: Async operation to execute
            *args: Positional arguments for operation
            **kwargs: Keyword arguments for operation
            
        Returns:
            Operation result
            
        Raises:
            Last exception if all retries fail
        """
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                return await asyncio.wait_for(
                    operation(*args, **kwargs),
                    timeout=self.timeout_ms / 1000
                )
            except asyncio.TimeoutError as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = (self.backoff_factor ** attempt)
                    await asyncio.sleep(delay)
                    continue
                break
            except Exception as e:
                last_exception = e
                if self._is_retryable_error(e) and attempt < self.max_retries - 1:
                    delay = (self.backoff_factor ** attempt)
                    await asyncio.sleep(delay)
                    continue
                break
        
        raise last_exception
    
    def _is_retryable_error(self, error: Exception) -> bool:
        """Determine if error is retryable.
        
        Args:
            error: Exception to check
            
        Returns:
            True if error should be retried
        """
        retryable_errors = [
            'ConnectionError',
            'TimeoutError',
            'HTTPError',
            'NetworkError',
            'aiohttp.ClientError'
        ]
        return any(err in str(type(error)) for err in retryable_errors)


class TransactionConfirmationManager:
    """Manage transaction confirmations with depth tracking."""
    
    def __init__(self):
        # From transaction_errors in robot_info.json
        self.max_confirm_attempts = 10
        self.confirmation_delay_ms = 3000
        
    async def wait_for_confirmation(self, tx_hash: str, 
                                  blockchain: str = 'nano',
                                  check_func: Callable = None) -> Dict:
        """Wait for transaction confirmation with attempt limits.
        
        Args:
            tx_hash: Transaction hash to monitor
            blockchain: Blockchain type ('nano', 'arweave', 'doge')
            check_func: Custom function to check confirmation status
            
        Returns:
            Dict containing confirmation result
        """
        for attempt in range(self.max_confirm_attempts):
            try:
                if check_func:
                    confirmation_data = await check_func(tx_hash)
                else:
                    confirmation_data = await self._check_confirmation(
                        tx_hash, blockchain
                    )
                
                if confirmation_data.get('confirmed', False):
                    return {
                        'status': 'confirmed',
                        'attempts': attempt + 1,
                        'confirmation_data': confirmation_data
                    }
                
                # Wait before next attempt
                await asyncio.sleep(self.confirmation_delay_ms / 1000)
                
            except Exception as e:
                if attempt == self.max_confirm_attempts - 1:
                    return {
                        'status': 'failed',
                        'attempts': attempt + 1,
                        'error': str(e)
                    }
                await asyncio.sleep(self.confirmation_delay_ms / 1000)
        
        return {
            'status': 'timeout',
            'attempts': self.max_confirm_attempts
        }
    
    async def _check_confirmation(self, tx_hash: str, 
                                blockchain: str) -> Dict:
        """Check confirmation status for specific blockchain.
        
        Args:
            tx_hash: Transaction hash
            blockchain: Blockchain type
            
        Returns:
            Dict containing confirmation status
        """
        if blockchain == 'nano':
            return await self._check_nano_confirmation(tx_hash)
        elif blockchain == 'arweave':
            return await self._check_arweave_confirmation(tx_hash)
        elif blockchain == 'doge':
            return await self._check_doge_confirmation(tx_hash)
        else:
            raise ValueError(f"Unsupported blockchain: {blockchain}")
    
    async def _check_nano_confirmation(self, tx_hash: str) -> Dict:
        """Check Nano transaction confirmation."""
        # Placeholder - implement actual Nano confirmation check
        return {'confirmed': True, 'blocks': 1}
    
    async def _check_arweave_confirmation(self, tx_hash: str) -> Dict:
        """Check Arweave transaction confirmation."""
        # Placeholder - implement actual Arweave confirmation check
        return {'confirmed': True, 'confirmations': 1}
    
    async def _check_doge_confirmation(self, tx_hash: str) -> Dict:
        """Check Dogecoin transaction confirmation."""
        # Placeholder - implement actual DOGE confirmation check
        return {'confirmed': True, 'confirmations': 1}