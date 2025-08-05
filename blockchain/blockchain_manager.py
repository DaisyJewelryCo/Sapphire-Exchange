"""
Unified blockchain manager for Sapphire Exchange.
Provides a single interface for all blockchain operations.
"""
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

from config.blockchain_config import blockchain_config
from .nano_client import NanoClient
from .arweave_client import ArweaveClient
from .dogecoin_client import DogecoinClient


class BlockchainStatus(Enum):
    """Blockchain connection status."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    SIGNATURE_ERROR = "signature_error"
    RPC_ERROR = "rpc_error"
    LOW_CONFIRMATION = "low_confirmation"
    LOCKED = "locked"
    INVALID_SEED = "invalid_seed"


@dataclass
class ConnectionStatus:
    """Connection status for a blockchain service."""
    service: str
    status: BlockchainStatus
    message: str = ""
    last_check: Optional[str] = None
    
    def is_healthy(self) -> bool:
        """Check if the connection is healthy."""
        return self.status == BlockchainStatus.CONNECTED


class BlockchainManager:
    """Unified manager for all blockchain operations."""
    
    def __init__(self):
        """Initialize blockchain manager with all clients."""
        self.nano_client = NanoClient(blockchain_config.get_nano_config())
        self.arweave_client = ArweaveClient(blockchain_config.get_arweave_config())
        self.dogecoin_client = DogecoinClient(blockchain_config.get_dogecoin_config())
        
        # Connection status tracking
        self.connection_status: Dict[str, ConnectionStatus] = {
            'nano': ConnectionStatus('Nano', BlockchainStatus.DISCONNECTED),
            'arweave': ConnectionStatus('Arweave', BlockchainStatus.DISCONNECTED),
            'dogecoin': ConnectionStatus('DOGE Wallet', BlockchainStatus.DISCONNECTED)
        }
        
        # Event callbacks
        self.status_change_callbacks = []
    
    async def initialize(self) -> bool:
        """Initialize all blockchain clients."""
        try:
            # Initialize clients concurrently
            tasks = [
                self._initialize_nano(),
                self._initialize_arweave(),
                self._initialize_dogecoin()
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check results and update status
            success_count = 0
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"Failed to initialize client {i}: {result}")
                elif result:
                    success_count += 1
            
            # Return True if at least one client initialized successfully
            return success_count > 0
            
        except Exception as e:
            print(f"Error initializing blockchain manager: {e}")
            return False
    
    async def _initialize_nano(self) -> bool:
        """Initialize Nano client."""
        try:
            success = await self.nano_client.initialize()
            if success:
                self.connection_status['nano'] = ConnectionStatus(
                    'Nano', BlockchainStatus.CONNECTED, "Connected to Nano RPC"
                )
            else:
                self.connection_status['nano'] = ConnectionStatus(
                    'Nano', BlockchainStatus.RPC_ERROR, "Failed to connect to Nano RPC"
                )
            return success
        except Exception as e:
            self.connection_status['nano'] = ConnectionStatus(
                'Nano', BlockchainStatus.ERROR, f"Nano initialization error: {e}"
            )
            return False
    
    async def _initialize_arweave(self) -> bool:
        """Initialize Arweave client."""
        try:
            success = await self.arweave_client.initialize()
            if success:
                self.connection_status['arweave'] = ConnectionStatus(
                    'Arweave', BlockchainStatus.CONNECTED, "Connected to Arweave gateway"
                )
            else:
                self.connection_status['arweave'] = ConnectionStatus(
                    'Arweave', BlockchainStatus.SIGNATURE_ERROR, "Arweave wallet or signature error"
                )
            return success
        except Exception as e:
            self.connection_status['arweave'] = ConnectionStatus(
                'Arweave', BlockchainStatus.ERROR, f"Arweave initialization error: {e}"
            )
            return False
    
    async def _initialize_dogecoin(self) -> bool:
        """Initialize Dogecoin client."""
        try:
            success = await self.dogecoin_client.initialize()
            if success:
                self.connection_status['dogecoin'] = ConnectionStatus(
                    'DOGE Wallet', BlockchainStatus.CONNECTED, "DOGE wallet unlocked and ready"
                )
            else:
                self.connection_status['dogecoin'] = ConnectionStatus(
                    'DOGE Wallet', BlockchainStatus.LOCKED, "DOGE wallet locked or invalid seed"
                )
            return success
        except Exception as e:
            self.connection_status['dogecoin'] = ConnectionStatus(
                'DOGE Wallet', BlockchainStatus.ERROR, f"DOGE wallet error: {e}"
            )
            return False
    
    def get_overall_status(self) -> BlockchainStatus:
        """Get overall system status based on all connections."""
        connected_count = sum(1 for status in self.connection_status.values() if status.is_healthy())
        total_count = len(self.connection_status)
        
        if connected_count == total_count:
            return BlockchainStatus.CONNECTED  # All connections healthy (green)
        elif connected_count > 0:
            return BlockchainStatus.RPC_ERROR  # Partial connection issues (orange)
        else:
            return BlockchainStatus.ERROR  # All services offline (red)
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get detailed status summary for UI display."""
        overall_status = self.get_overall_status()
        
        # Map status to colors for UI
        status_colors = {
            BlockchainStatus.CONNECTED: "green",
            BlockchainStatus.RPC_ERROR: "orange", 
            BlockchainStatus.ERROR: "red",
            BlockchainStatus.SIGNATURE_ERROR: "red",
            BlockchainStatus.LOW_CONFIRMATION: "orange",
            BlockchainStatus.LOCKED: "red",
            BlockchainStatus.INVALID_SEED: "red",
            BlockchainStatus.DISCONNECTED: "red"
        }
        
        return {
            "overall_status": overall_status.value,
            "overall_color": status_colors.get(overall_status, "red"),
            "services": [
                {
                    "name": status.service,
                    "status": status.status.value,
                    "message": status.message,
                    "color": status_colors.get(status.status, "red"),
                    "healthy": status.is_healthy()
                }
                for status in self.connection_status.values()
            ]
        }
    
    async def check_health(self) -> Dict[str, bool]:
        """Check health of all blockchain services."""
        health_checks = {
            'nano': self.nano_client.check_health(),
            'arweave': self.arweave_client.check_health(),
            'dogecoin': self.dogecoin_client.check_health()
        }
        
        results = {}
        for service, check in health_checks.items():
            try:
                results[service] = await check
                # Update connection status based on health check
                if results[service]:
                    self.connection_status[service].status = BlockchainStatus.CONNECTED
                else:
                    self.connection_status[service].status = BlockchainStatus.ERROR
            except Exception as e:
                results[service] = False
                self.connection_status[service].status = BlockchainStatus.ERROR
                self.connection_status[service].message = str(e)
        
        return results
    
    # Nano operations
    async def get_nano_balance(self, address: str) -> Optional[Dict[str, str]]:
        """Get Nano account balance."""
        try:
            return await self.nano_client.get_balance(address)
        except Exception as e:
            print(f"Error getting Nano balance: {e}")
            return None
    
    async def send_nano(self, from_address: str, to_address: str, amount_raw: str) -> Optional[str]:
        """Send Nano transaction."""
        try:
            return await self.nano_client.send_payment(from_address, to_address, amount_raw)
        except Exception as e:
            print(f"Error sending Nano: {e}")
            return None
    
    # Arweave operations
    async def store_data(self, data: Dict[str, Any], tags: Optional[List[Tuple[str, str]]] = None) -> Optional[str]:
        """Store data on Arweave."""
        try:
            return await self.arweave_client.store_data(data, tags)
        except Exception as e:
            print(f"Error storing data on Arweave: {e}")
            return None
    
    async def retrieve_data(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve data from Arweave."""
        try:
            return await self.arweave_client.retrieve_data(transaction_id)
        except Exception as e:
            print(f"Error retrieving data from Arweave: {e}")
            return None
    
    # Dogecoin operations
    async def get_doge_balance(self, address: Optional[str] = None) -> Optional[float]:
        """Get Dogecoin balance."""
        try:
            return await self.dogecoin_client.get_balance(address)
        except Exception as e:
            print(f"Error getting DOGE balance: {e}")
            return None
    
    async def send_doge(self, to_address: str, amount: float) -> Optional[str]:
        """Send Dogecoin transaction."""
        try:
            return await self.dogecoin_client.send_payment(to_address, amount)
        except Exception as e:
            print(f"Error sending DOGE: {e}")
            return None
    
    async def generate_doge_address(self) -> Optional[str]:
        """Generate new Dogecoin address."""
        try:
            return await self.dogecoin_client.generate_address()
        except Exception as e:
            print(f"Error generating DOGE address: {e}")
            return None
    
    async def generate_nano_address(self) -> Optional[str]:
        """Generate new Nano address."""
        try:
            return await self.nano_client.generate_address()
        except Exception as e:
            print(f"Error generating Nano address: {e}")
            return None
    
    async def generate_arweave_address(self) -> Optional[str]:
        """Generate new Arweave address."""
        try:
            return await self.arweave_client.generate_address()
        except Exception as e:
            print(f"Error generating Arweave address: {e}")
            return None
    
    # Unified transaction methods
    async def get_transaction_status(self, tx_hash: str, blockchain: str) -> Optional[Dict[str, Any]]:
        """Get transaction status from specified blockchain."""
        try:
            if blockchain.lower() == 'nano':
                return await self.nano_client.get_transaction_status(tx_hash)
            elif blockchain.lower() == 'arweave':
                return await self.arweave_client.get_transaction_status(tx_hash)
            elif blockchain.lower() == 'dogecoin':
                return await self.dogecoin_client.get_transaction_status(tx_hash)
            else:
                print(f"Unknown blockchain: {blockchain}")
                return None
        except Exception as e:
            print(f"Error getting transaction status: {e}")
            return None
    
    async def wait_for_confirmation(self, tx_hash: str, blockchain: str, 
                                   timeout_seconds: int = 300) -> bool:
        """Wait for transaction confirmation."""
        try:
            if blockchain.lower() == 'nano':
                return await self.nano_client.wait_for_confirmation(tx_hash, timeout_seconds)
            elif blockchain.lower() == 'arweave':
                return await self.arweave_client.wait_for_confirmation(tx_hash, timeout_seconds)
            elif blockchain.lower() == 'dogecoin':
                return await self.dogecoin_client.wait_for_confirmation(tx_hash, timeout_seconds)
            else:
                print(f"Unknown blockchain: {blockchain}")
                return False
        except Exception as e:
            print(f"Error waiting for confirmation: {e}")
            return False
    
    # Batch operations
    async def batch_get_balances(self, addresses: Dict[str, str]) -> Dict[str, Optional[float]]:
        """Get balances for multiple addresses across different blockchains.
        
        Args:
            addresses: Dict mapping blockchain name to address
            
        Returns:
            Dict mapping blockchain name to balance
        """
        results = {}
        tasks = []
        
        for blockchain, address in addresses.items():
            if blockchain.lower() == 'nano':
                tasks.append(('nano', self.get_nano_balance(address)))
            elif blockchain.lower() == 'dogecoin':
                tasks.append(('dogecoin', self.get_doge_balance(address)))
        
        if tasks:
            task_results = await asyncio.gather(*[task[1] for task in tasks], return_exceptions=True)
            
            for i, (blockchain, result) in enumerate(zip([task[0] for task in tasks], task_results)):
                if isinstance(result, Exception):
                    results[blockchain] = None
                else:
                    if blockchain == 'nano' and result:
                        # Convert raw to NANO for display
                        results[blockchain] = float(result.get('balance', '0')) / (10**30)
                    else:
                        results[blockchain] = result
        
        return results
    
    # Data integrity methods
    async def verify_data_integrity(self, tx_id: str, expected_hash: str) -> bool:
        """Verify data integrity on Arweave."""
        try:
            data = await self.retrieve_data(tx_id)
            if not data:
                return False
            
            # Calculate hash of retrieved data
            import hashlib
            import json
            data_str = json.dumps(data, sort_keys=True)
            calculated_hash = hashlib.sha256(data_str.encode()).hexdigest()
            
            return calculated_hash == expected_hash
        except Exception as e:
            print(f"Error verifying data integrity: {e}")
            return False
    
    # Network information
    async def get_network_info(self) -> Dict[str, Any]:
        """Get network information for all blockchains."""
        info = {
            'nano': {},
            'arweave': {},
            'dogecoin': {}
        }
        
        try:
            # Get network info concurrently
            tasks = [
                self.nano_client.get_network_info(),
                self.arweave_client.get_network_info(),
                self.dogecoin_client.get_network_info()
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, (blockchain, result) in enumerate(zip(['nano', 'arweave', 'dogecoin'], results)):
                if not isinstance(result, Exception):
                    info[blockchain] = result or {}
                else:
                    info[blockchain] = {'error': str(result)}
        
        except Exception as e:
            print(f"Error getting network info: {e}")
        
        return info
    
    # Fee estimation
    async def estimate_fees(self, blockchain: str, amount: float = None) -> Optional[float]:
        """Estimate transaction fees for a blockchain."""
        try:
            if blockchain.lower() == 'nano':
                return 0.0  # Nano is feeless
            elif blockchain.lower() == 'arweave':
                return await self.arweave_client.estimate_fee(amount)
            elif blockchain.lower() == 'dogecoin':
                return await self.dogecoin_client.estimate_fee(amount)
            else:
                print(f"Unknown blockchain: {blockchain}")
                return None
        except Exception as e:
            print(f"Error estimating fees: {e}")
            return None
    
    # Utility methods
    def add_status_change_callback(self, callback):
        """Add callback for status changes."""
        self.status_change_callbacks.append(callback)
    
    def remove_status_change_callback(self, callback):
        """Remove status change callback."""
        if callback in self.status_change_callbacks:
            self.status_change_callbacks.remove(callback)
    
    def _notify_status_change(self):
        """Notify all callbacks of status change."""
        for callback in self.status_change_callbacks:
            try:
                callback(self.get_status_summary())
            except Exception as e:
                print(f"Error in status change callback: {e}")
    
    async def shutdown(self):
        """Shutdown all blockchain clients."""
        try:
            await asyncio.gather(
                self.nano_client.shutdown(),
                self.arweave_client.shutdown(),
                self.dogecoin_client.shutdown(),
                return_exceptions=True
            )
        except Exception as e:
            print(f"Error during blockchain manager shutdown: {e}")


# Global blockchain manager instance
blockchain_manager = BlockchainManager()