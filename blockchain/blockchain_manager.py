"""
Unified blockchain manager for Sapphire Exchange.
Provides a single interface for all blockchain operations.
"""
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

from config.blockchain_config import blockchain_config
from utils.qasync_compat import async_sleep
from .nano_client import NanoClient
from .arweave_client import ArweaveClient
from .solana_usdc_client import SolanaUsdcClient
# from .dogecoin_client import DogecoinClient  # Foundation code for real DOGE blockchain


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
        # Real Solana USDC implementation
        self.solana_usdc_client = SolanaUsdcClient(blockchain_config.get_usdc_config())
        # self.dogecoin_client = DogecoinClient(blockchain_config.get_dogecoin_config())  # Foundation code for real DOGE blockchain
        
        # Connection status tracking
        self.connection_status: Dict[str, ConnectionStatus] = {
            'nano': ConnectionStatus('Nano', BlockchainStatus.DISCONNECTED),
            'arweave': ConnectionStatus('Arweave', BlockchainStatus.DISCONNECTED),
            'solana_usdc': ConnectionStatus('Solana USDC', BlockchainStatus.DISCONNECTED)
            # 'dogecoin': ConnectionStatus('DOGE Wallet', BlockchainStatus.DISCONNECTED)  # Foundation code for real DOGE blockchain
        }
        
        # Lock for serializing blockchain operations to avoid database pool exhaustion
        self._blockchain_op_lock: Optional[asyncio.Lock] = None
        
        # Event callbacks
        self.status_change_callbacks = []
    
    async def initialize(self) -> bool:
        """Initialize all blockchain clients."""
        try:
            # Initialize lock for blockchain operations
            # Try to create the lock, but handle the case where event loop might not be fully ready
            try:
                self._blockchain_op_lock = asyncio.Lock()
            except RuntimeError as e:
                print(f"Warning: Could not create async lock immediately: {e}")
                # Lock will be created lazily when first needed
                self._blockchain_op_lock = None
            
            # Initialize clients with staggered timing to avoid pool contention
            self.connection_status['nano'].status = BlockchainStatus.DISCONNECTED
            self.connection_status['arweave'].status = BlockchainStatus.DISCONNECTED
            self.connection_status['solana_usdc'].status = BlockchainStatus.DISCONNECTED
            
            # Initialize Nano first
            nano_result = await self._initialize_nano()
            await async_sleep(0.1)  # Small delay to avoid pool contention
            
            # Initialize Arweave
            arweave_result = await self._initialize_arweave()
            await async_sleep(0.1)  # Small delay to avoid pool contention
            
            # Initialize Solana USDC
            solana_usdc_result = await self._initialize_solana_usdc()
            
            results = [nano_result, arweave_result, solana_usdc_result]
            
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
            import traceback
            traceback.print_exc()
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
    
    async def _initialize_solana_usdc(self) -> bool:
        """Initialize Solana USDC client."""
        try:
            success = await self.solana_usdc_client.initialize()
            if success:
                self.connection_status['solana_usdc'] = ConnectionStatus(
                    'Solana USDC', BlockchainStatus.CONNECTED, "Connected to Solana USDC"
                )
            else:
                error_msg = self.solana_usdc_client.last_error or "Failed to connect to Solana RPC"
                details = self.solana_usdc_client.last_error_details
                if details:
                    full_msg = f"{error_msg}. Details: {details}"
                else:
                    full_msg = error_msg
                self.connection_status['solana_usdc'] = ConnectionStatus(
                    'Solana USDC', BlockchainStatus.RPC_ERROR, full_msg
                )
            return success
        except Exception as e:
            self.connection_status['solana_usdc'] = ConnectionStatus(
                'Solana USDC', BlockchainStatus.ERROR, f"Solana USDC initialization error: {e}"
            )
            return False

    # Legacy USDC implementation (kept for reference, replaced by Solana USDC)
    async def _initialize_usdc(self) -> bool:
        """Initialize USDC client. (Legacy - use Solana USDC instead)"""
        # This method is kept for backward compatibility but is no longer used
        return False

    # Foundation code for real DOGE blockchain (commented out)
    """
    async def _initialize_dogecoin(self) -> bool:
        # Initialize Dogecoin client.
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
    """
    
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
    
    def get_solana_error_details(self) -> Dict[str, Any]:
        """Get detailed Solana USDC error information for debugging."""
        return {
            "status": self.connection_status['solana_usdc'].status.value,
            "message": self.connection_status['solana_usdc'].message,
            "client_errors": self.solana_usdc_client.get_error_details()
        }
    
    async def check_health(self) -> Dict[str, bool]:
        """Check health of all blockchain services."""
        health_checks = {
            'nano': self.nano_client.check_health(),
            'arweave': self.arweave_client.check_health(),
            'solana_usdc': self.solana_usdc_client.check_health()
            # 'dogecoin': self.dogecoin_client.check_health()  # Foundation code for real DOGE blockchain
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
    
    async def send_nano(self, from_address: str, to_address: str, amount_raw: str, 
                       memo: Optional[str] = None) -> Optional[str]:
        """Send Nano transaction with optional memo."""
        try:
            return await self.nano_client.send_payment(from_address, to_address, amount_raw, memo=memo)
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
    
    # USDC operations (Testing database implementation)
    async def get_usdc_balance(self, address: str) -> Optional[Dict[str, Any]]:
        """Get USDC balance on Solana."""
        try:
            return await self.solana_usdc_client.get_balance(address)
        except Exception as e:
            print(f"Error getting USDC balance: {e}")
            return None
    
    async def send_usdc(self, from_address: str, to_address: str, amount: float, 
                       keypair_bytes: Optional[bytes] = None) -> Optional[str]:
        """Send USDC transaction on Solana."""
        try:
            return await self.solana_usdc_client.send_usdc(from_address, to_address, amount, keypair_bytes)
        except Exception as e:
            print(f"Error sending USDC: {e}")
            return None
    
    async def create_usdc_wallet(self, chain: str = None, wallet_name: str = None, user_id: int = None) -> Optional[str]:
        """Create new USDC wallet. (Legacy method - Solana USDC wallets are managed separately)"""
        try:
            return None
        except Exception as e:
            print(f"Error creating USDC wallet: {e}")
            return None

    # Foundation code for real DOGE blockchain operations (commented out)
    """
    # Dogecoin operations
    async def get_doge_balance(self, address: Optional[str] = None) -> Optional[float]:
        # Get Dogecoin balance.
        try:
            return await self.dogecoin_client.get_balance(address)
        except Exception as e:
            print(f"Error getting DOGE balance: {e}")
            return None
    
    async def send_doge(self, to_address: str, amount: float) -> Optional[str]:
        # Send Dogecoin transaction.
        try:
            return await self.dogecoin_client.send_payment(to_address, amount)
        except Exception as e:
            print(f"Error sending DOGE: {e}")
            return None
    
    async def generate_doge_address(self) -> Optional[str]:
        # Generate new Dogecoin address.
        try:
            return await self.dogecoin_client.generate_address()
        except Exception as e:
            print(f"Error generating DOGE address: {e}")
            return None
    """
    
    async def generate_nano_address(self) -> Optional[str]:
        """Generate new Nano address."""
        try:
            if self._blockchain_op_lock is None:
                self._blockchain_op_lock = asyncio.Lock()
            async with self._blockchain_op_lock:
                return await self.nano_client.generate_address()
        except Exception as e:
            print(f"Error generating Nano address: {e}")
            return None
    
    async def generate_arweave_address(self) -> Optional[str]:
        """Generate new Arweave address."""
        try:
            if self._blockchain_op_lock is None:
                self._blockchain_op_lock = asyncio.Lock()
            async with self._blockchain_op_lock:
                return await self.arweave_client.generate_address()
        except Exception as e:
            print(f"Error generating Arweave address: {e}")
            return None
    
    async def generate_usdc_address(self) -> Optional[str]:
        """Generate new USDC address. Returns a mock Solana address."""
        try:
            import uuid
            import base58
            
            # Generate a mock Solana address using base58 encoding
            # Solana addresses are 32-byte public keys encoded in base58
            unique_bytes = uuid.uuid4().bytes + uuid.uuid4().bytes[:8]
            solana_address = base58.b58encode(unique_bytes).decode('ascii')
            
            return solana_address
        except Exception as e:
            print(f"Error generating USDC address: {e}")
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
            blockchain_lower = blockchain.lower()
            if blockchain_lower == 'nano':
                tasks.append(('nano', self.get_nano_balance(address)))
            elif blockchain_lower == 'usdc':
                # For USDC, check if it's a Solana address (string) or database ID (int)
                if isinstance(address, str) and address.startswith('nano_'):
                    # Skip Nano addresses
                    continue
                # Try to get USDC balance from Solana
                tasks.append(('usdc', self._get_usdc_balance_solana(address)))
            elif blockchain_lower == 'sol':
                # Get native SOL balance
                tasks.append(('sol', self._get_sol_balance(address)))
            elif blockchain_lower == 'arweave':
                # Arweave doesn't have balance tracking in the same way
                # Skip for now
                continue
        
        if tasks:
            task_results = await asyncio.gather(*[task[1] for task in tasks], return_exceptions=True)
            
            for blockchain, result in zip([task[0] for task in tasks], task_results):
                if isinstance(result, Exception):
                    print(f"Error getting {blockchain} balance: {result}")
                    results[blockchain] = None
                else:
                    if blockchain == 'nano' and result:
                        # Convert raw to NANO for display
                        results[blockchain] = float(result.get('balance', '0')) / (10**30)
                    elif blockchain == 'sol' and isinstance(result, dict):
                        # Result is dict with sol_balance key
                        results[blockchain] = result.get('sol_balance', 0)
                    elif blockchain == 'usdc' and isinstance(result, dict):
                        # Result is dict with usdc_balance key
                        results[blockchain] = result.get('usdc_balance', 0)
                    else:
                        results[blockchain] = result
        
        return results
    
    async def _get_sol_balance(self, address: str) -> Optional[Dict[str, float]]:
        """Get native SOL balance for a Solana address."""
        try:
            if not self.solana_usdc_client:
                return None
            
            balance_info = await self.solana_usdc_client.get_balance(address)
            if balance_info:
                return {
                    'sol_balance': balance_info.get('sol_balance', 0),
                    'address': address
                }
            return None
        except Exception as e:
            print(f"Error getting SOL balance: {e}")
            return None
    
    async def _get_usdc_balance_solana(self, address: str) -> Optional[Dict[str, float]]:
        """Get USDC token balance from Solana for a given address."""
        try:
            if not self.solana_usdc_client:
                return None
            
            balance_info = await self.solana_usdc_client.get_balance(address)
            if balance_info:
                return {
                    'usdc_balance': balance_info.get('usdc_balance', 0),
                    'address': address
                }
            return None
        except Exception as e:
            print(f"Error getting USDC balance from Solana: {e}")
            return None
    
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
                # Add USDC network info when needed
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, (blockchain, result) in enumerate(zip(['nano', 'arweave'], results)):
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