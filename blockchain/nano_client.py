"""
Unified Nano client for Sapphire Exchange.
Consolidates functionality from multiple nano_utils files.
"""
import asyncio
import aiohttp
import base58
import hashlib
import ed25519_blake2b
import json
import time
from typing import Dict, Optional, Any, Union, List, Tuple
from datetime import datetime, timedelta


class MockNanoAccount:
    """Mock Nano account for testing."""
    def __init__(self, address: str, public_key: bytes):
        self.address = address
        self.public_key = public_key
        self.balance: int = 100 * 10**30  # 100 NANO in raw
        self.pending: int = 0
        self.frontier: Optional[str] = None
        self.representative: str = "nano_3t6k35gi95xu6tergt6p69ck76ogmitsa8mnijtpxm9fkcm736xtoncuohr3"


class MockNanoNetwork:
    """Mock Nano network for testing."""
    def __init__(self):
        self.accounts: Dict[str, MockNanoAccount] = {}
        self.blocks = {}
    
    def create_account(self, public_key: bytes, address: str):
        """Create a new mock account."""
        if address not in self.accounts:
            self.accounts[address] = MockNanoAccount(address, public_key)
    
    def get_account(self, address: str) -> Optional[MockNanoAccount]:
        """Get a mock account by address."""
        return self.accounts.get(address)
    
    def process_payment(self, source: str, destination: str, amount: int) -> bool:
        """Process a mock payment between accounts."""
        if source not in self.accounts or destination not in self.accounts:
            return False
        
        if self.accounts[source].balance < amount:
            return False
        
        self.accounts[source].balance -= amount
        self.accounts[destination].balance += amount
        return True


class NanoClient:
    """Unified Nano blockchain client."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Nano client with configuration."""
        self.config = config
        self.rpc_endpoint = config.get('rpc_endpoint', 'http://[::1]:7076')
        self.default_representative = config.get('default_representative')
        self.mock_mode = config.get('mock_mode', False)
        
        # Mock network for testing
        self.mock_network = MockNanoNetwork() if self.mock_mode else None
        
        # Session for HTTP requests
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Conversion constants
        self.NANO_TO_RAW = 10**30
        self.RAW_TO_NANO = 1 / (10**30)
    
    async def initialize(self) -> bool:
        """Initialize the Nano client."""
        try:
            if not self.mock_mode:
                self.session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=30)
                )
                # Test connection
                return await self.check_health()
            else:
                print("Nano client initialized in mock mode")
                return True
        except Exception as e:
            print(f"Error initializing Nano client: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown the Nano client."""
        if self.session:
            await self.session.close()
    
    async def check_health(self) -> bool:
        """Check if Nano node is healthy."""
        try:
            if self.mock_mode:
                return True
            
            response = await self._make_rpc_call({
                "action": "version"
            })
            return response is not None and "node_vendor" in response
        except Exception:
            return False
    
    async def _make_rpc_call(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Make RPC call to Nano node."""
        if self.mock_mode:
            return self._handle_mock_rpc(data)
        
        try:
            if not self.session:
                return None
            
            async with self.session.post(
                self.rpc_endpoint,
                json=data,
                headers={'Content-Type': 'application/json'}
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"RPC call failed with status {response.status}")
                    return None
        except Exception as e:
            print(f"Error making RPC call: {e}")
            return None
    
    def _handle_mock_rpc(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle mock RPC calls for testing."""
        action = data.get("action")
        
        if action == "version":
            return {
                "rpc_version": "1",
                "store_version": "21",
                "protocol_version": "18",
                "node_vendor": "Nano 25.0",
                "store_vendor": "LMDB 0.9.70",
                "network": "live",
                "network_identifier": "991CF190094C00F0B68E2E5F75F6BEE95A2E0BD93CEAA4A6734DB9F19B728948",
                "build_info": "Mock Nano Node"
            }
        
        elif action == "account_balance":
            address = data.get("account")
            if address and self.mock_network:
                account = self.mock_network.get_account(address)
                if account:
                    return {
                        "balance": str(account.balance),
                        "pending": str(account.pending)
                    }
            return {"balance": "0", "pending": "0"}
        
        elif action == "account_info":
            address = data.get("account")
            if address and self.mock_network:
                account = self.mock_network.get_account(address)
                if account:
                    return {
                        "frontier": account.frontier or "0000000000000000000000000000000000000000000000000000000000000000",
                        "open_block": "0000000000000000000000000000000000000000000000000000000000000000",
                        "representative_block": "0000000000000000000000000000000000000000000000000000000000000000",
                        "balance": str(account.balance),
                        "modified_timestamp": str(int(time.time())),
                        "block_count": "1",
                        "account_version": "1",
                        "confirmation_height": "1",
                        "confirmation_height_frontier": "0000000000000000000000000000000000000000000000000000000000000000",
                        "representative": account.representative
                    }
            return {"error": "Account not found"}
        
        elif action == "account_create":
            wallet = data.get("wallet")
            if wallet and self.mock_network:
                # Generate a mock account
                public_key = b'mock_public_key_32_bytes_long_'
                address = self.public_key_to_address(public_key)
                self.mock_network.create_account(public_key, address)
                return {"account": address}
            return {"error": "Wallet not found"}
        
        elif action == "send":
            source = data.get("source")
            destination = data.get("destination")
            amount = int(data.get("amount", "0"))
            
            if source and destination and self.mock_network:
                if self.mock_network.process_payment(source, destination, amount):
                    block_hash = hashlib.sha256(f"{source}{destination}{amount}{time.time()}".encode()).hexdigest().upper()
                    return {"block": block_hash}
            return {"error": "Insufficient balance or invalid accounts"}
        
        return {"error": "Unknown action"}
    
    def generate_seed(self) -> bytes:
        """Generate a random 32-byte seed."""
        import secrets
        return secrets.token_bytes(32)
    
    def seed_to_private_key(self, seed: bytes, index: int = 0) -> bytes:
        """Derive private key from seed and index."""
        return hashlib.blake2b(seed + index.to_bytes(4, 'big'), digest_size=32).digest()
    
    def private_key_to_public_key(self, private_key: bytes) -> bytes:
        """Derive public key from private key."""
        return ed25519_blake2b.public_from_secret(private_key)
    
    def public_key_to_address(self, public_key: bytes) -> str:
        """Convert public key to Nano address."""
        # Blake2b hash of public key
        h = hashlib.blake2b(public_key, digest_size=5).digest()
        # Reverse for checksum
        checksum = h[::-1]
        # Encode with base32
        encoded = base58.b58encode(public_key + checksum).decode('utf-8')
        return f"nano_{encoded}"
    
    def address_to_public_key(self, address: str) -> Optional[bytes]:
        """Convert Nano address to public key."""
        try:
            if not address.startswith('nano_'):
                return None
            
            encoded = address[5:]  # Remove 'nano_' prefix
            decoded = base58.b58decode(encoded)
            
            if len(decoded) != 37:  # 32 bytes public key + 5 bytes checksum
                return None
            
            public_key = decoded[:32]
            checksum = decoded[32:]
            
            # Verify checksum
            expected_checksum = hashlib.blake2b(public_key, digest_size=5).digest()[::-1]
            if checksum != expected_checksum:
                return None
            
            return public_key
        except Exception:
            return None
    
    def nano_to_raw(self, nano_amount: Union[float, str]) -> str:
        """Convert Nano to raw units."""
        try:
            nano_float = float(nano_amount)
            raw_amount = int(nano_float * self.NANO_TO_RAW)
            return str(raw_amount)
        except (ValueError, OverflowError):
            return "0"
    
    def raw_to_nano(self, raw_amount: Union[str, int]) -> float:
        """Convert raw units to Nano."""
        try:
            raw_int = int(raw_amount)
            nano_amount = raw_int * self.RAW_TO_NANO
            return nano_amount
        except (ValueError, OverflowError):
            return 0.0
    
    async def create_account(self, wallet_id: str) -> Optional[str]:
        """Create a new Nano account."""
        try:
            response = await self._make_rpc_call({
                "action": "account_create",
                "wallet": wallet_id
            })
            
            if response and "account" in response:
                return response["account"]
            return None
        except Exception as e:
            print(f"Error creating account: {e}")
            return None
    
    async def get_balance(self, address: str) -> Optional[Dict[str, str]]:
        """Get account balance."""
        try:
            # Create mock account if in mock mode and doesn't exist
            if self.mock_mode and self.mock_network:
                if address not in self.mock_network.accounts:
                    public_key = self.address_to_public_key(address)
                    if public_key:
                        self.mock_network.create_account(public_key, address)
            
            response = await self._make_rpc_call({
                "action": "account_balance",
                "account": address
            })
            
            if response and "balance" in response:
                return {
                    "balance": response["balance"],
                    "pending": response.get("pending", "0")
                }
            return None
        except Exception as e:
            print(f"Error getting balance: {e}")
            return None
    
    async def get_account_info(self, address: str) -> Optional[Dict[str, Any]]:
        """Get detailed account information."""
        try:
            response = await self._make_rpc_call({
                "action": "account_info",
                "account": address,
                "representative": True,
                "weight": True,
                "pending": True
            })
            
            if response and "error" not in response:
                return response
            return None
        except Exception as e:
            print(f"Error getting account info: {e}")
            return None
    
    async def send_payment(self, source: str, destination: str, amount_raw: str, 
                          wallet_id: Optional[str] = None) -> Optional[str]:
        """Send Nano payment."""
        try:
            rpc_data = {
                "action": "send",
                "source": source,
                "destination": destination,
                "amount": amount_raw
            }
            
            if wallet_id:
                rpc_data["wallet"] = wallet_id
            
            response = await self._make_rpc_call(rpc_data)
            
            if response and "block" in response:
                return response["block"]
            return None
        except Exception as e:
            print(f"Error sending payment: {e}")
            return None
    
    async def confirm_block(self, block_hash: str) -> Optional[Dict[str, Any]]:
        """Get block confirmation status."""
        try:
            response = await self._make_rpc_call({
                "action": "block_confirm",
                "hash": block_hash
            })
            
            if response:
                return response
            return None
        except Exception as e:
            print(f"Error confirming block: {e}")
            return None
    
    def validate_address(self, address: str) -> bool:
        """Validate Nano address format."""
        try:
            if not address.startswith('nano_'):
                return False
            
            if len(address) != 65:  # nano_ + 60 characters
                return False
            
            # Try to decode and verify checksum
            public_key = self.address_to_public_key(address)
            return public_key is not None
        except Exception:
            return False
    
    def format_balance(self, raw_amount: Union[str, int], decimals: int = 6) -> str:
        """Format raw balance for display."""
        try:
            nano_amount = self.raw_to_nano(raw_amount)
            return f"{nano_amount:.{decimals}f}"
        except Exception:
            return "0.000000"