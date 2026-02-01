"""
Transaction broadcaster for submitting signed transactions to blockchain networks.
Handles RPC communication, retries, and transaction status polling.
Supports Solana (USDC), Nano, and Arweave.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import asyncio
import time
import aiohttp
import json
from datetime import datetime


class BroadcastStatus(Enum):
    """Transaction broadcast status."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    REVERTED = "reverted"


@dataclass
class BroadcastResult:
    """Result of transaction broadcast."""
    transaction_id: str
    broadcast_hash: str
    status: BroadcastStatus
    confirmations: int = 0
    timestamp: float = 0.0
    error: Optional[str] = None
    raw_response: Optional[str] = None
    block_height: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "transaction_id": self.transaction_id,
            "broadcast_hash": self.broadcast_hash,
            "status": self.status.value,
            "confirmations": self.confirmations,
            "timestamp": self.timestamp,
            "error": self.error,
            "block_height": self.block_height,
        }


class Broadcaster(ABC):
    """Base class for blockchain broadcasters."""
    
    def __init__(self, chain: str, rpc_url: str = None):
        """
        Initialize broadcaster.
        
        Args:
            chain: Blockchain type
            rpc_url: RPC endpoint URL
        """
        self.chain = chain
        self.rpc_url = rpc_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.max_retries = 3
        self.retry_delay = 1.0
        self.backoff_multiplier = 2.0
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    @abstractmethod
    async def broadcast(self, signed_transaction: str) -> BroadcastResult:
        """
        Broadcast signed transaction to network.
        
        Args:
            signed_transaction: Signed transaction (JSON or encoded)
        
        Returns:
            BroadcastResult instance
        """
        pass
    
    @abstractmethod
    async def get_status(self, transaction_hash: str) -> BroadcastResult:
        """
        Get transaction status.
        
        Args:
            transaction_hash: Transaction hash/ID
        
        Returns:
            BroadcastResult with current status
        """
        pass
    
    @abstractmethod
    async def wait_confirmation(self, transaction_hash: str,
                               timeout: int = 120,
                               target_confirmations: int = 1) -> BroadcastResult:
        """
        Wait for transaction confirmation.
        
        Args:
            transaction_hash: Transaction hash/ID
            timeout: Maximum wait time in seconds
            target_confirmations: Target confirmation count
        
        Returns:
            BroadcastResult with final status
        """
        pass
    
    async def retry_with_backoff(self, coroutine, max_retries: int = None) -> Any:
        """
        Execute coroutine with exponential backoff retry.
        
        Args:
            coroutine: Async function to execute
            max_retries: Maximum retry attempts
        
        Returns:
            Result of coroutine execution
        
        Raises:
            Exception: If all retries fail
        """
        max_retries = max_retries or self.max_retries
        current_delay = self.retry_delay
        
        for attempt in range(max_retries):
            try:
                return await coroutine()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                
                await asyncio.sleep(current_delay)
                current_delay *= self.backoff_multiplier
        
        raise RuntimeError("Retry exhausted")
    
    async def _make_rpc_call(self, method: str, params: list = None,
                            headers: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Make JSON-RPC call to blockchain node.
        
        Args:
            method: RPC method name
            params: RPC parameters
            headers: HTTP headers
        
        Returns:
            RPC response data
        
        Raises:
            Exception: If RPC call fails
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        payload = {
            "jsonrpc": "2.0",
            "id": int(time.time() * 1000),
            "method": method,
            "params": params or [],
        }
        
        if headers is None:
            headers = {"Content-Type": "application/json"}
        
        async with self.session.post(self.rpc_url, json=payload, headers=headers) as response:
            data = await response.json()
            
            if "error" in data:
                raise RuntimeError(f"RPC error: {data['error']}")
            
            return data.get("result", {})


class SolanaBroadcaster(Broadcaster):
    """Solana transaction broadcaster."""
    
    def __init__(self, rpc_url: str = None):
        """
        Initialize Solana broadcaster.
        
        Args:
            rpc_url: Solana RPC endpoint
        """
        rpc_url = rpc_url or "https://api.mainnet-beta.solana.com"
        super().__init__("solana", rpc_url)
        self.commitment = "confirmed"
    
    async def broadcast(self, signed_transaction: str) -> BroadcastResult:
        """Broadcast signed Solana transaction."""
        try:
            start_time = time.time()
            
            result = await self.retry_with_backoff(
                lambda: self._send_transaction(signed_transaction)
            )
            
            signature = result.get("signature", "")
            
            return BroadcastResult(
                transaction_id=signature,
                broadcast_hash=signature,
                status=BroadcastStatus.SUBMITTED,
                timestamp=start_time,
            )
        
        except Exception as e:
            return BroadcastResult(
                transaction_id="",
                broadcast_hash="",
                status=BroadcastStatus.FAILED,
                timestamp=time.time(),
                error=f"Broadcast failed: {str(e)}",
            )
    
    async def _send_transaction(self, signed_transaction: str) -> Dict[str, Any]:
        """Send transaction via Solana RPC."""
        return await self._make_rpc_call(
            "sendTransaction",
            [signed_transaction, {"encoding": "base64", "preflightCommitment": self.commitment}],
        )
    
    async def get_status(self, transaction_hash: str) -> BroadcastResult:
        """Get Solana transaction status."""
        try:
            result = await self._make_rpc_call(
                "getSignatureStatuses",
                [[transaction_hash]],
            )
            
            if not result or not result.get("value"):
                return BroadcastResult(
                    transaction_id=transaction_hash,
                    broadcast_hash=transaction_hash,
                    status=BroadcastStatus.PENDING,
                    timestamp=time.time(),
                )
            
            status_info = result["value"][0]
            
            if status_info is None:
                status = BroadcastStatus.PENDING
                confirmations = 0
            elif status_info.get("err"):
                status = BroadcastStatus.FAILED
                confirmations = 0
            else:
                confirmations = status_info.get("confirmations", 0)
                status = BroadcastStatus.CONFIRMED if confirmations > 0 else BroadcastStatus.SUBMITTED
            
            return BroadcastResult(
                transaction_id=transaction_hash,
                broadcast_hash=transaction_hash,
                status=status,
                confirmations=confirmations,
                timestamp=time.time(),
            )
        
        except Exception as e:
            return BroadcastResult(
                transaction_id=transaction_hash,
                broadcast_hash=transaction_hash,
                status=BroadcastStatus.PENDING,
                timestamp=time.time(),
                error=str(e),
            )
    
    async def wait_confirmation(self, transaction_hash: str,
                               timeout: int = 120,
                               target_confirmations: int = 1) -> BroadcastResult:
        """Wait for Solana transaction confirmation."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            result = await self.get_status(transaction_hash)
            
            if result.status == BroadcastStatus.CONFIRMED:
                return result
            
            if result.status == BroadcastStatus.FAILED:
                return result
            
            await asyncio.sleep(2.0)
        
        return BroadcastResult(
            transaction_id=transaction_hash,
            broadcast_hash=transaction_hash,
            status=BroadcastStatus.TIMEOUT,
            timestamp=time.time(),
            error=f"Confirmation timeout after {timeout}s",
        )


class NanoBroadcaster(Broadcaster):
    """Nano transaction broadcaster."""
    
    def __init__(self, rpc_url: str = None):
        """
        Initialize Nano broadcaster.
        
        Args:
            rpc_url: Nano node RPC endpoint
        """
        rpc_url = rpc_url or "https://mynano.ninja/api"
        super().__init__("nano", rpc_url)
    
    async def broadcast(self, signed_transaction: str) -> BroadcastResult:
        """Broadcast signed Nano state block."""
        try:
            start_time = time.time()
            
            block_data = json.loads(signed_transaction)
            
            result = await self.retry_with_backoff(
                lambda: self._process_block(block_data)
            )
            
            block_hash = result.get("hash", "")
            
            return BroadcastResult(
                transaction_id=block_hash,
                broadcast_hash=block_hash,
                status=BroadcastStatus.SUBMITTED,
                timestamp=start_time,
                raw_response=str(result),
            )
        
        except Exception as e:
            return BroadcastResult(
                transaction_id="",
                broadcast_hash="",
                status=BroadcastStatus.FAILED,
                timestamp=time.time(),
                error=f"Broadcast failed: {str(e)}",
            )
    
    async def _process_block(self, block: Dict[str, Any]) -> Dict[str, Any]:
        """Process Nano block via RPC."""
        return await self._make_rpc_call("process", [{"block": json.dumps(block)}])
    
    async def get_status(self, transaction_hash: str) -> BroadcastResult:
        """Get Nano block status."""
        try:
            result = await self._make_rpc_call("block_info", [{"hash": transaction_hash}])
            
            confirmations = 1
            if "confirmed" in result:
                confirmations = 2 if result["confirmed"] == "true" else 1
            
            return BroadcastResult(
                transaction_id=transaction_hash,
                broadcast_hash=transaction_hash,
                status=BroadcastStatus.CONFIRMED,
                confirmations=confirmations,
                timestamp=time.time(),
            )
        
        except Exception as e:
            if "not found" in str(e).lower():
                return BroadcastResult(
                    transaction_id=transaction_hash,
                    broadcast_hash=transaction_hash,
                    status=BroadcastStatus.PENDING,
                    timestamp=time.time(),
                )
            
            return BroadcastResult(
                transaction_id=transaction_hash,
                broadcast_hash=transaction_hash,
                status=BroadcastStatus.PENDING,
                timestamp=time.time(),
                error=str(e),
            )
    
    async def wait_confirmation(self, transaction_hash: str,
                               timeout: int = 120,
                               target_confirmations: int = 1) -> BroadcastResult:
        """Wait for Nano block confirmation."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            result = await self.get_status(transaction_hash)
            
            if result.status == BroadcastStatus.CONFIRMED:
                return result
            
            await asyncio.sleep(1.0)
        
        return BroadcastResult(
            transaction_id=transaction_hash,
            broadcast_hash=transaction_hash,
            status=BroadcastStatus.TIMEOUT,
            timestamp=time.time(),
            error=f"Confirmation timeout after {timeout}s",
        )


class ArweaveBroadcaster(Broadcaster):
    """Arweave transaction broadcaster."""
    
    def __init__(self, gateway_url: str = None):
        """
        Initialize Arweave broadcaster.
        
        Args:
            gateway_url: Arweave gateway URL
        """
        gateway_url = gateway_url or "https://arweave.net"
        super().__init__("arweave", gateway_url)
    
    async def broadcast(self, signed_transaction: str) -> BroadcastResult:
        """Broadcast signed Arweave transaction."""
        try:
            start_time = time.time()
            
            tx_data = json.loads(signed_transaction)
            tx_id = tx_data.get("id", "")
            
            result = await self.retry_with_backoff(
                lambda: self._submit_transaction(tx_data)
            )
            
            return BroadcastResult(
                transaction_id=tx_id,
                broadcast_hash=tx_id,
                status=BroadcastStatus.SUBMITTED,
                timestamp=start_time,
                raw_response=str(result),
            )
        
        except Exception as e:
            return BroadcastResult(
                transaction_id="",
                broadcast_hash="",
                status=BroadcastStatus.FAILED,
                timestamp=time.time(),
                error=f"Broadcast failed: {str(e)}",
            )
    
    async def _submit_transaction(self, tx_data: Dict[str, Any]) -> Dict[str, Any]:
        """Submit Arweave transaction."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        url = f"{self.rpc_url}/tx"
        headers = {"Content-Type": "application/json"}
        
        async with self.session.post(url, json=tx_data, headers=headers) as response:
            if response.status not in [200, 202]:
                error = await response.text()
                raise RuntimeError(f"Failed to submit transaction: {error}")
            
            return {"ok": True, "status": response.status}
    
    async def get_status(self, transaction_hash: str) -> BroadcastResult:
        """Get Arweave transaction status."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            url = f"{self.rpc_url}/tx/{transaction_hash}/status"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    block_height = data.get("block_height", 0)
                    
                    status = BroadcastStatus.CONFIRMED if block_height > 0 else BroadcastStatus.PENDING
                    
                    return BroadcastResult(
                        transaction_id=transaction_hash,
                        broadcast_hash=transaction_hash,
                        status=status,
                        block_height=block_height,
                        timestamp=time.time(),
                    )
                else:
                    return BroadcastResult(
                        transaction_id=transaction_hash,
                        broadcast_hash=transaction_hash,
                        status=BroadcastStatus.PENDING,
                        timestamp=time.time(),
                    )
        
        except Exception as e:
            return BroadcastResult(
                transaction_id=transaction_hash,
                broadcast_hash=transaction_hash,
                status=BroadcastStatus.PENDING,
                timestamp=time.time(),
                error=str(e),
            )
    
    async def wait_confirmation(self, transaction_hash: str,
                               timeout: int = 600,
                               target_confirmations: int = 1) -> BroadcastResult:
        """Wait for Arweave transaction confirmation (10+ minutes typical)."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            result = await self.get_status(transaction_hash)
            
            if result.status == BroadcastStatus.CONFIRMED:
                return result
            
            await asyncio.sleep(10.0)
        
        return BroadcastResult(
            transaction_id=transaction_hash,
            broadcast_hash=transaction_hash,
            status=BroadcastStatus.TIMEOUT,
            timestamp=time.time(),
            error=f"Confirmation timeout after {timeout}s",
        )


class BroadcasterFactory:
    """Factory for creating broadcasters."""
    
    BROADCASTERS = {
        "solana": SolanaBroadcaster,
        "nano": NanoBroadcaster,
        "arweave": ArweaveBroadcaster,
    }
    
    @classmethod
    def create(cls, chain: str, **kwargs) -> Broadcaster:
        """
        Create broadcaster for specified chain.
        
        Args:
            chain: Blockchain type (solana, nano, arweave)
            **kwargs: Additional arguments for broadcaster initialization
        
        Returns:
            Broadcaster instance
        
        Raises:
            ValueError: If chain is not supported
        """
        if chain not in cls.BROADCASTERS:
            raise ValueError(f"Unsupported chain: {chain}. Supported: {list(cls.BROADCASTERS.keys())}")
        
        broadcaster_class = cls.BROADCASTERS[chain]
        return broadcaster_class(**kwargs)
    
    @classmethod
    def get_supported_chains(cls) -> list:
        """Get list of supported chains."""
        return list(cls.BROADCASTERS.keys())
