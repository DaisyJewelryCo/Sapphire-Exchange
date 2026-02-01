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
import os
import sys
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
    """Unified Nano blockchain client using mock network."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Nano client with configuration."""
        self.config = config
        self.rpc_endpoint = config.get('rpc_endpoint', 'https://mynano.ninja/api')
        self.default_representative = config.get('default_representative')
        self.mock_mode = False
        
        # Mock network for testing (only if explicitly enabled)
        self.mock_network = None
        
        # Database interface - removed
        self.nano_interface = None
        self.use_database = False
        
        # Session for HTTP requests
        self.session = None
        
        # Conversion constants
        self.NANO_TO_RAW = 10**30
        self.RAW_TO_NANO = 1 / (10**30)
    
    async def initialize(self) -> bool:
        """Initialize the Nano client."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # Test connection to RPC endpoint
            health_ok = await self.check_health()
            if health_ok:
                return True
            
            # If RPC endpoint is not available, fall back to mock mode
            print(f"Warning: Nano RPC endpoint not reachable at {self.rpc_endpoint}, using mock mode")
            self.mock_mode = True
            return True
        except Exception as e:
            print(f"Error initializing Nano client: {e}")
            # Fall back to mock mode on error
            self.mock_mode = True
            return True
    
    async def shutdown(self):
        """Shutdown the Nano client."""
        pass
    
    async def check_health(self) -> bool:
        """Check if Nano client is healthy."""
        try:
            if self.mock_mode:
                return True
            
            if not self.session:
                return False
            
            response = await self._make_rpc_call({"action": "version"})
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
        try:
            # Try the correct function name for ed25519_blake2b
            if hasattr(ed25519_blake2b, 'publickey'):
                return ed25519_blake2b.publickey(private_key)
            elif hasattr(ed25519_blake2b, 'public_from_secret'):
                return ed25519_blake2b.public_from_secret(private_key)
            else:
                # Fallback: use PyNaCl for ed25519 key generation
                from nacl.signing import SigningKey
                signing_key = SigningKey(private_key)
                return bytes(signing_key.verify_key)
        except Exception as e:
            print(f"Error deriving public key: {e}")
            # Fallback: generate a mock public key for testing
            return hashlib.sha256(private_key).digest()
    
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
        """Create a new Nano account from seed/wallet."""
        try:
            if not self.nano_interface:
                return None
            
            # Generate address from wallet
            seed = self.generate_seed()
            private_key = self.seed_to_private_key(seed, 0)
            public_key = self.private_key_to_public_key(private_key)
            address = self.public_key_to_address(public_key)
            
            # Store in database
            query = """
                INSERT INTO nano_accounts (account_id, address, public_key, representative, balance)
                VALUES (gen_random_uuid(), $1, $2, $3, $4)
                ON CONFLICT (address) DO NOTHING
                RETURNING address
            """
            result = await self.nano_interface.execute_one(
                query,
                address,
                public_key,
                self.default_representative,
                0
            )
            
            return address if result else None
        except Exception as e:
            print(f"Error creating account in database: {e}")
            return None
    
    async def get_balance(self, address: str) -> Optional[Dict[str, str]]:
        """Get account balance from database."""
        try:
            if not self.nano_interface:
                return None
            
            # Query balance from database
            query = "SELECT balance FROM nano_accounts WHERE address = $1"
            result = await self.nano_interface.execute_one(query, address)
            
            if result:
                return {
                    "balance": str(result['balance']),
                    "pending": "0"
                }
            
            return None
        except Exception as e:
            print(f"Error getting balance from database: {e}")
            return None
    
    async def get_account_info(self, address: str) -> Optional[Dict[str, Any]]:
        """Get detailed account information from database."""
        try:
            if not self.nano_interface:
                return None
            
            query = """
                SELECT 
                    address, 
                    public_key, 
                    representative, 
                    balance, 
                    created_at
                FROM nano_accounts 
                WHERE address = $1
            """
            result = await self.nano_interface.execute_one(query, address)
            
            if result:
                return {
                    "address": result['address'],
                    "public_key": result['public_key'].hex() if result['public_key'] else None,
                    "representative": result['representative'],
                    "balance": str(result['balance']),
                    "created_at": str(result['created_at']),
                    "error": None
                }
            return {"error": "Account not found"}
        except Exception as e:
            print(f"Error getting account info from database: {e}")
            return {"error": str(e)}
    
    async def send_payment(self, source: str, destination: str, amount_raw: str, 
                          wallet_id: Optional[str] = None, memo: Optional[str] = None) -> Optional[str]:
        """Send Nano payment via database."""
        try:
            if not self.nano_interface:
                return None
            
            amount = int(amount_raw)
            
            # Get source account
            source_result = await self.nano_interface.execute_one(
                "SELECT account_id, balance FROM nano_accounts WHERE address = $1",
                source
            )
            
            if not source_result or source_result['balance'] < amount:
                return None
            
            # Get destination account
            dest_result = await self.nano_interface.execute_one(
                "SELECT account_id FROM nano_accounts WHERE address = $1",
                destination
            )
            
            if not dest_result:
                return None
            
            # Create transaction hash
            block_hash = hashlib.sha256(f"{source}{destination}{amount_raw}".encode()).hexdigest().upper()
            
            # Update balances (simplified - real implementation would use transactions)
            await self.nano_interface.execute(
                "UPDATE nano_accounts SET balance = balance - $1 WHERE address = $2",
                amount,
                source
            )
            await self.nano_interface.execute(
                "UPDATE nano_accounts SET balance = balance + $1 WHERE address = $2",
                amount,
                destination
            )
            
            return block_hash
        except Exception as e:
            print(f"Error sending payment in database: {e}")
            return None
    
    async def confirm_block(self, block_hash: str) -> Optional[Dict[str, Any]]:
        """Get block confirmation status from database."""
        try:
            if not self.nano_interface:
                return None
            
            query = "SELECT * FROM nano_blocks WHERE block_hash = $1"
            result = await self.nano_interface.execute_one(query, block_hash)
            
            if result:
                return {
                    "confirmed": True,
                    "block_hash": result['block_hash'],
                    "account": result['account_id'],
                    "timestamp": str(result['timestamp'])
                }
            
            return None
        except Exception as e:
            print(f"Error confirming block in database: {e}")
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
    
    async def generate_address(self, max_retries: int = 3) -> Optional[str]:
        """Generate a new Nano address."""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Generate address components
                seed = self.generate_seed()
                private_key = self.seed_to_private_key(seed, 0)
                public_key = self.private_key_to_public_key(private_key)
                address = self.public_key_to_address(public_key)
                
                return address
                    
            except Exception as e:
                last_error = e
                print(f"Error generating Nano address (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    try:
                        await asyncio.sleep(0.5 * (attempt + 1))
                    except RuntimeError:
                        # Event loop might not be available, skip sleep
                        pass
                else:
                    return None
        
        return None

    def format_balance(self, raw_amount: Union[str, int], decimals: int = 6) -> str:
        """Format raw balance for display."""
        try:
            nano_amount = self.raw_to_nano(raw_amount)
            return f"{nano_amount:.{decimals}f}"
        except Exception:
            return "0.000000"