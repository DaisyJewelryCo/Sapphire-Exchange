"""
Nano Cloudflare Worker Service for Sapphire Exchange.
Handles Nano funding requests through Cloudflare Workers endpoint with robust retry logic.
"""

import asyncio
import aiohttp
import logging
from typing import Dict, Optional, Any, List
from datetime import datetime
from enum import Enum
from decimal import Decimal, InvalidOperation

from utils.validation_utils import Validator


logger = logging.getLogger(__name__)


class NanoRequestStatus(Enum):
    """Status of Nano request."""
    PENDING = "pending"
    RETRYING = "retrying"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


class NanoCloudflareService:
    """Service for requesting Nano funds via Cloudflare Worker."""
    
    def __init__(self, worker_url: Optional[str] = None, api_key: Optional[str] = None,
                 max_retries: int = 3, retry_delay: int = 2,
                 max_amount_nano: Optional[float] = None, min_amount_nano: Optional[float] = None,
                 request_timeout: Optional[int] = None):
        """
        Initialize Nano Cloudflare service.
        
        Args:
            worker_url: URL of the Cloudflare Worker endpoint
            api_key: API key for authenticating with the worker
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.worker_url = worker_url or "https://nano-sender.yourdomain.workers.dev/sendNano"
        self.api_key = api_key or "your-app-api-key"
        self.http_session: Optional[aiohttp.ClientSession] = None
        
        self.request_timeout = request_timeout or 30
        self.max_amount_raw = self._nano_to_raw(max_amount_nano) if max_amount_nano is not None else self._nano_to_raw(1.0)
        self.min_amount_raw = self._nano_to_raw(min_amount_nano) if min_amount_nano is not None else 1
        
        # Retry configuration
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Request tracking
        self.request_history: List[Dict[str, Any]] = []
        self.last_request_time: Optional[datetime] = None
    
    def _nano_to_raw(self, amount_nano: Optional[float]) -> int:
        try:
            if amount_nano is None:
                return 0
            raw_value = (Decimal(str(amount_nano)) * Decimal("1e30")).to_integral_value()
            return max(int(raw_value), 1)
        except (InvalidOperation, ValueError, TypeError):
            return 0
    
    async def initialize(self) -> bool:
        """Initialize the service."""
        try:
            if not self.http_session:
                self.http_session = aiohttp.ClientSession()
            return True
        except Exception as e:
            print(f"Error initializing Nano Cloudflare service: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown the service."""
        try:
            if self.http_session:
                await self.http_session.close()
        except Exception as e:
            print(f"Error shutting down Nano Cloudflare service: {e}")
    
    async def request_nano(self, to_address: str, amount_raw: str, retry_count: int = 0) -> Optional[Dict[str, Any]]:
        """
        Request Nano to be sent to an address via Cloudflare Worker with automatic retries.
        
        Args:
            to_address: Destination Nano address
            amount_raw: Amount in raw (smallest unit)
            retry_count: Internal counter for retry attempts
        
        Returns:
            Dict with success status, transaction hash, and retry info
        """
        try:
            if not self.http_session:
                await self.initialize()
            
            # Validate amount
            validation_error = self._validate_amount(amount_raw)
            if validation_error:
                return {
                    "success": False,
                    "error": validation_error,
                    "retry_count": retry_count
                }
            
            # Validate address
            address_error = self._validate_address(to_address)
            if address_error:
                return {
                    "success": False,
                    "error": address_error,
                    "retry_count": retry_count
                }
            
            # Build request
            request_payload = {
                "to": to_address,
                "amount_raw": amount_raw,
                "api_key": self.api_key
            }
            
            # Send request to Cloudflare Worker
            try:
                async with self.http_session.post(
                    self.worker_url,
                    json=request_payload,
                    timeout=aiohttp.ClientTimeout(total=self.request_timeout)
                ) as response:
                    result = await self._handle_response(response, retry_count)
                    
                    # Log request
                    self._log_request(to_address, amount_raw, result, retry_count)
                    
                    if result.get("retryable") and retry_count < self.max_retries:
                        await asyncio.sleep(self.retry_delay)
                        return await self.request_nano(to_address, amount_raw, retry_count + 1)
                    
                    return result
            
            except asyncio.TimeoutError:
                return await self._handle_timeout(to_address, amount_raw, retry_count)
            except aiohttp.ClientError as e:
                return await self._handle_client_error(to_address, amount_raw, str(e), retry_count)
        
        except Exception as e:
            logger.error(f"Error requesting Nano: {e}")
            self._log_request(to_address, amount_raw, {"success": False, "error": str(e)}, retry_count)
            return {
                "success": False,
                "error": f"Error: {str(e)[:100]}",
                "retry_count": retry_count
            }
    
    def _validate_amount(self, amount_raw: str) -> Optional[str]:
        """Validate Nano amount. Returns error message if invalid."""
        try:
            amount_int = int(amount_raw)
            if amount_int < self.min_amount_raw:
                return f"Amount must be at least {self.min_amount_raw} raw"
            if amount_int > self.max_amount_raw:
                return f"Amount must not exceed {self.max_amount_raw} raw"
        except (ValueError, TypeError):
            return "amount_raw must be a valid integer string"
        return None
    
    def _validate_address(self, address: str) -> Optional[str]:
        """Validate Nano address. Returns error message if invalid."""
        if not address or not isinstance(address, str):
            return "Invalid destination address"
        if not Validator.validate_nano_address(address):
            return "Invalid Nano address format"
        return None
    
    async def _handle_response(self, response, retry_count: int) -> Dict[str, Any]:
        """Handle Cloudflare Worker response."""
        if response.status == 200:
            data = await response.json()
            if data.get("success"):
                return {
                    "success": True,
                    "hash": data.get("hash"),
                    "timestamp": datetime.now().isoformat(),
                    "retry_count": retry_count,
                    "status": NanoRequestStatus.SUCCESS.value
                }
            else:
                return {
                    "success": False,
                    "error": data.get("error", "Unknown error from worker"),
                    "retry_count": retry_count,
                    "status": NanoRequestStatus.FAILED.value
                }
        elif response.status == 401:
            return {
                "success": False,
                "error": "Unauthorized - Invalid API key",
                "retry_count": retry_count,
                "status": NanoRequestStatus.FAILED.value
            }
        elif response.status == 429:
            # Rate limited - should retry
            return {
                "success": False,
                "error": "Rate limited - please try again later",
                "retry_count": retry_count,
                "status": NanoRequestStatus.RETRYING.value,
                "retryable": True
            }
        elif response.status == 400:
            data = await response.json()
            return {
                "success": False,
                "error": data.get("error", "Bad request"),
                "retry_count": retry_count,
                "status": NanoRequestStatus.FAILED.value
            }
        elif response.status >= 500:
            # Server error - retryable
            return {
                "success": False,
                "error": f"Server error ({response.status}) - retrying...",
                "retry_count": retry_count,
                "status": NanoRequestStatus.RETRYING.value,
                "retryable": True
            }
        else:
            return {
                "success": False,
                "error": f"Unexpected status {response.status}",
                "retry_count": retry_count,
                "status": NanoRequestStatus.FAILED.value
            }
    
    async def _handle_timeout(self, to_address: str, amount_raw: str, retry_count: int) -> Dict[str, Any]:
        """Handle request timeout with retry logic."""
        if retry_count < self.max_retries:
            logger.warning(f"Request timeout, retrying... (attempt {retry_count + 1}/{self.max_retries})")
            await asyncio.sleep(self.retry_delay)
            return await self.request_nano(to_address, amount_raw, retry_count + 1)
        
        return {
            "success": False,
            "error": "Request timed out after all retries",
            "retry_count": retry_count,
            "status": NanoRequestStatus.TIMEOUT.value
        }
    
    async def _handle_client_error(self, to_address: str, amount_raw: str, error: str, retry_count: int) -> Dict[str, Any]:
        """Handle client error with retry logic."""
        # Only retry on specific transient errors
        retryable_errors = ['Connection reset', 'Connection refused', 'Network unreachable']
        is_retryable = any(err in error for err in retryable_errors)
        
        if is_retryable and retry_count < self.max_retries:
            logger.warning(f"Retryable connection error, retrying... (attempt {retry_count + 1}/{self.max_retries})")
            await asyncio.sleep(self.retry_delay)
            return await self.request_nano(to_address, amount_raw, retry_count + 1)
        
        return {
            "success": False,
            "error": f"Connection error: {error[:100]}",
            "retry_count": retry_count,
            "status": NanoRequestStatus.FAILED.value
        }
    
    def _log_request(self, to_address: str, amount_raw: str, result: Dict[str, Any], retry_count: int):
        """Log request details."""
        self.last_request_time = datetime.now()
        log_entry = {
            "timestamp": self.last_request_time.isoformat(),
            "to_address": to_address,
            "amount_raw": amount_raw,
            "success": result.get("success", False),
            "hash": result.get("hash"),
            "error": result.get("error"),
            "retry_count": retry_count
        }
        self.request_history.append(log_entry)
        
        if result.get("success"):
            logger.info(f"Nano request successful: {to_address} - {amount_raw} raw - Hash: {result.get('hash')}")
        else:
            logger.warning(f"Nano request failed: {to_address} - {result.get('error')}")
    
    def get_request_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent request history."""
        return self.request_history[-limit:]
    
    async def validate_worker_connection(self) -> bool:
        """
        Validate that the Cloudflare Worker is reachable.
        
        Returns:
            True if worker is reachable, False otherwise
        """
        try:
            if not self.http_session:
                await self.initialize()
            
            # Try a small request with minimal amount to test connectivity
            test_payload = {
                "to": "nano_3t6k35gi95xu6tergt6p69ck76ogmitsa8mnijtpxm9fkcm736xtoncuohr3",
                "amount_raw": "1",
                "api_key": self.api_key
            }
            
            async with self.http_session.post(
                self.worker_url,
                json=test_payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                return response.status in (200, 400, 401)
        
        except Exception as e:
            print(f"Worker validation failed: {e}")
            return False
    
    def get_worker_status(self) -> Dict[str, Any]:
        """Get worker configuration status."""
        return {
            "worker_url": self.worker_url,
            "api_key_set": bool(self.api_key),
            "max_amount_raw": self.max_amount_raw,
            "min_amount_raw": self.min_amount_raw,
            "timeout_seconds": self.request_timeout
        }


# Global service instance
nano_cloudflare_service = None


async def get_nano_cloudflare_service(
    worker_url: Optional[str] = None,
    api_key: Optional[str] = None
) -> NanoCloudflareService:
    """Get or create the global Nano Cloudflare service."""
    global nano_cloudflare_service
    
    from services.funding_manager_service import get_funding_manager_service
    
    funding_service = get_funding_manager_service()
    config = funding_service.config
    resolved_worker_url = worker_url or config.cloudflare_worker_url
    resolved_api_key = api_key or config.cloudflare_api_key
    max_retries = config.max_retries
    retry_delay = config.retry_delay
    request_timeout = config.request_timeout
    max_amount_nano = config.nano_max_amount
    min_amount_nano = config.nano_min_amount
    
    if not nano_cloudflare_service:
        nano_cloudflare_service = NanoCloudflareService(
            worker_url=resolved_worker_url,
            api_key=resolved_api_key,
            max_retries=max_retries,
            retry_delay=retry_delay,
            max_amount_nano=max_amount_nano,
            min_amount_nano=min_amount_nano,
            request_timeout=request_timeout
        )
        await nano_cloudflare_service.initialize()
    else:
        nano_cloudflare_service.worker_url = resolved_worker_url
        nano_cloudflare_service.api_key = resolved_api_key
        nano_cloudflare_service.max_retries = max_retries
        nano_cloudflare_service.retry_delay = retry_delay
        nano_cloudflare_service.request_timeout = request_timeout
        nano_cloudflare_service.max_amount_raw = nano_cloudflare_service._nano_to_raw(max_amount_nano)
        nano_cloudflare_service.min_amount_raw = nano_cloudflare_service._nano_to_raw(min_amount_nano)
    
    return nano_cloudflare_service
