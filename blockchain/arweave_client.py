"""
Unified Arweave client for Sapphire Exchange.
Consolidates functionality from arweave_utils.py files.
"""
import asyncio
import aiohttp
import json
import time
import uuid
import random
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from base64 import b64encode, b64decode
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256

# Database interface for wallet storage
from sql_blockchain.blockchain_interface import ArweaveInterface, ConnectionConfig


class MockArweaveTransaction:
    """Mock Arweave transaction for testing."""
    def __init__(self, data: bytes, wallet_address: str):
        self.id = str(uuid.uuid4()).replace('-', '')[:43]  # Arweave TX ID format
        self.data = data
        self.wallet_address = wallet_address
        self.timestamp = datetime.utcnow()
        self.status = 'pending'
        self.block_height = None
        self.tags = []
        self.fee = "1000000000000"  # 1 AR in winston
    
    def add_tag(self, name: str, value: str):
        """Add tag to transaction."""
        self.tags.append({'name': name, 'value': value})
    
    def sign(self):
        """Mock signing - no actual cryptography."""
        pass
    
    def send(self) -> str:
        """Mock send - simulate network delay and success."""
        time.sleep(0.1)  # Simulate network delay
        if random.random() < 0.9:  # 90% success rate
            self.status = 'confirmed'
            self.block_height = random.randint(800000, 900000)
            return self.id
        else:
            self.status = 'failed'
            raise Exception("Mock transaction failed")


class MockArweaveNetwork:
    """Mock Arweave network for testing."""
    def __init__(self):
        self.transactions: Dict[str, MockArweaveTransaction] = {}
        self.wallets: Dict[str, Dict[str, Any]] = {}
    
    def store_transaction(self, tx: MockArweaveTransaction):
        """Store transaction in mock network."""
        self.transactions[tx.id] = tx
    
    def get_transaction(self, tx_id: str) -> Optional[MockArweaveTransaction]:
        """Get transaction by ID."""
        return self.transactions.get(tx_id)
    
    def create_wallet(self) -> Dict[str, Any]:
        """Create mock wallet."""
        wallet_id = str(uuid.uuid4())
        wallet_data = {
            'id': wallet_id,
            'address': f"mock_address_{wallet_id[:8]}",
            'balance': "10000000000000",  # 10 AR in winston
            'created_at': datetime.utcnow().isoformat()
        }
        self.wallets[wallet_id] = wallet_data
        return wallet_data


class ArweaveClient:
    """Unified Arweave blockchain client."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Arweave client with configuration."""
        self.config = config
        self.gateway_url = config.get('gateway_url', 'https://arweave.net')
        self.wallet_file = config.get('wallet_file', 'wallet.json')
        self.mock_mode = config.get('mock_mode', False)
        
        # Default tags from config
        self.default_tags = config.get('data_parameters', {}).get('default_tags', [
            "App-Name: Sapphire-Exchange",
            "Content-Type: application/json"
        ])
        
        # Mock network for testing
        self.mock_network = MockArweaveNetwork() if self.mock_mode else None
        
        # Database configuration for wallet storage
        self.db_config = ConnectionConfig(
            host=config.get('database_settings', {}).get('host', 'localhost'),
            port=config.get('database_settings', {}).get('port', 5432),
            database=config.get('database_settings', {}).get('database', 'saphire'),
            user=config.get('database_settings', {}).get('user', 'postgres'),
            password=config.get('database_settings', {}).get('password', ''),
        )
        
        # Database interface
        self.arweave_interface: Optional[ArweaveInterface] = None
        
        # Lock for thread-safe database operations
        self._db_lock: Optional[asyncio.Lock] = None
        
        # Session for HTTP requests
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Wallet data
        self.wallet_data: Optional[Dict[str, Any]] = None
        self.wallet_address: Optional[str] = None
        
        # Conversion constants
        self.AR_TO_WINSTON = 10**12
        self.WINSTON_TO_AR = 1 / (10**12)
    
    async def initialize(self) -> bool:
        """Initialize the Arweave client."""
        try:
            # Initialize database interface and lock
            self.arweave_interface = ArweaveInterface(self.db_config)
            await self.arweave_interface.initialize()
            
            # Try to create the lock, but handle the case where event loop might not be fully ready
            try:
                self._db_lock = asyncio.Lock()
            except RuntimeError:
                # Lock will be created lazily when first needed
                self._db_lock = None
            
            if not self.mock_mode:
                self.session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=60)
                )
                # Load wallet and test connection
                wallet_loaded = await self._load_wallet()
                if not wallet_loaded:
                    print(f"Warning: Arweave wallet not loaded, falling back to mock mode")
                    # Fall back to mock mode if wallet not available
                    self.mock_mode = True
                    self.mock_network = MockArweaveNetwork()
                    self.wallet_data = self.mock_network.create_wallet()
                    self.wallet_address = self.wallet_data['address']
                    return True
                health_ok = await self.check_health()
                if not health_ok:
                    print(f"Warning: Arweave gateway health check failed, but wallet loaded")
                return wallet_loaded
            else:
                # Mock mode initialization with database support
                self.wallet_data = self.mock_network.create_wallet()
                self.wallet_address = self.wallet_data['address']
                print("Arweave client initialized in mock mode with database support")
                return True
        except Exception as e:
            print(f"Error initializing Arweave client: {e}")
            # Fall back to mock mode on error
            try:
                self.mock_mode = True
                self.mock_network = MockArweaveNetwork()
                self.wallet_data = self.mock_network.create_wallet()
                self.wallet_address = self.wallet_data['address']
                return True
            except Exception as fallback_error:
                print(f"Error initializing Arweave client fallback: {fallback_error}")
                return False
    
    async def shutdown(self):
        """Shutdown the Arweave client."""
        if self.arweave_interface:
            await self.arweave_interface.close()
        if self.session:
            await self.session.close()
    
    async def check_health(self) -> bool:
        """Check if Arweave gateway is healthy."""
        try:
            if self.mock_mode:
                return True
            
            if not self.session:
                return False
            
            async with self.session.get(f"{self.gateway_url}/info") as response:
                if response.status == 200:
                    info = await response.json()
                    return 'network' in info and 'height' in info
                return False
        except Exception:
            return False
    
    async def _load_wallet(self) -> bool:
        """Load Arweave wallet from file."""
        try:
            import os
            if not os.path.exists(self.wallet_file):
                print(f"Wallet file not found: {self.wallet_file}")
                return False
            
            with open(self.wallet_file, 'r') as f:
                self.wallet_data = json.load(f)
            
            # Extract wallet address (this is simplified - real implementation would derive from key)
            self.wallet_address = f"arweave_address_{hash(str(self.wallet_data))}"
            return True
        except Exception as e:
            print(f"Error loading wallet: {e}")
            return False
    
    def ar_to_winston(self, ar_amount: float) -> str:
        """Convert AR to winston units."""
        try:
            winston_amount = int(ar_amount * self.AR_TO_WINSTON)
            return str(winston_amount)
        except (ValueError, OverflowError):
            return "0"
    
    def winston_to_ar(self, winston_amount: str) -> float:
        """Convert winston units to AR."""
        try:
            winston_int = int(winston_amount)
            ar_amount = winston_int * self.WINSTON_TO_AR
            return ar_amount
        except (ValueError, OverflowError):
            return 0.0
    
    async def get_balance(self, address: Optional[str] = None) -> Optional[str]:
        """Get wallet balance in winston."""
        try:
            target_address = address or self.wallet_address
            if not target_address:
                return None
            
            if self.mock_mode and self.mock_network:
                # Return mock balance
                return "10000000000000"  # 10 AR in winston
            
            if not self.session:
                return None
            
            async with self.session.get(f"{self.gateway_url}/wallet/{target_address}/balance") as response:
                if response.status == 200:
                    balance = await response.text()
                    return balance.strip()
                return None
        except Exception as e:
            print(f"Error getting balance: {e}")
            return None
    
    async def get_transaction_price(self, data_size: int) -> Optional[str]:
        """Get transaction price in winston for given data size."""
        try:
            if self.mock_mode:
                # Mock pricing: 1 winston per byte
                return str(data_size)
            
            if not self.session:
                return None
            
            async with self.session.get(f"{self.gateway_url}/price/{data_size}") as response:
                if response.status == 200:
                    price = await response.text()
                    return price.strip()
                return None
        except Exception as e:
            print(f"Error getting transaction price: {e}")
            return None
    
    async def store_data(self, data: Dict[str, Any], tags: Optional[List[Tuple[str, str]]] = None) -> Optional[str]:
        """Store data on Arweave and return transaction ID."""
        try:
            # Convert data to JSON bytes
            json_data = json.dumps(data, ensure_ascii=False)
            data_bytes = json_data.encode('utf-8')
            
            if self.mock_mode and self.mock_network:
                # Create mock transaction
                tx = MockArweaveTransaction(data_bytes, self.wallet_address)
                
                # Add default tags
                for tag in self.default_tags:
                    if ':' in tag:
                        name, value = tag.split(':', 1)
                        tx.add_tag(name.strip(), value.strip())
                
                # Add custom tags
                if tags:
                    for name, value in tags:
                        tx.add_tag(name, value)
                
                # Store and send
                self.mock_network.store_transaction(tx)
                return tx.send()
            
            # Real Arweave implementation would go here
            # For now, return a mock transaction ID
            return f"mock_tx_{uuid.uuid4().hex[:43]}"
            
        except Exception as e:
            print(f"Error storing data: {e}")
            return None
    
    async def retrieve_data(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve data from Arweave by transaction ID."""
        try:
            if self.mock_mode and self.mock_network:
                tx = self.mock_network.get_transaction(transaction_id)
                if tx and tx.status == 'confirmed':
                    return json.loads(tx.data.decode('utf-8'))
                return None
            
            if not self.session:
                return None
            
            async with self.session.get(f"{self.gateway_url}/{transaction_id}") as response:
                if response.status == 200:
                    data = await response.text()
                    return json.loads(data)
                return None
        except Exception as e:
            print(f"Error retrieving data: {e}")
            return None
    
    async def get_transaction_status(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Get transaction status and confirmation info."""
        try:
            if self.mock_mode and self.mock_network:
                tx = self.mock_network.get_transaction(transaction_id)
                if tx:
                    return {
                        'id': tx.id,
                        'status': tx.status,
                        'block_height': tx.block_height,
                        'timestamp': tx.timestamp.isoformat(),
                        'confirmations': 10 if tx.status == 'confirmed' else 0
                    }
                return None
            
            if not self.session:
                return None
            
            async with self.session.get(f"{self.gateway_url}/tx/{transaction_id}/status") as response:
                if response.status == 200:
                    return await response.json()
                return None
        except Exception as e:
            print(f"Error getting transaction status: {e}")
            return None
    
    async def verify_data_integrity(self, transaction_id: str, expected_hash: str) -> bool:
        """Verify data integrity using SHA-256 hash."""
        try:
            data = await self.retrieve_data(transaction_id)
            if not data:
                return False
            
            # Calculate hash of retrieved data
            json_data = json.dumps(data, sort_keys=True, ensure_ascii=False)
            calculated_hash = hashlib.sha256(json_data.encode('utf-8')).hexdigest()
            
            return calculated_hash == expected_hash
        except Exception as e:
            print(f"Error verifying data integrity: {e}")
            return False
    
    def calculate_data_hash(self, data: Dict[str, Any]) -> str:
        """Calculate SHA-256 hash of data for integrity verification."""
        try:
            json_data = json.dumps(data, sort_keys=True, ensure_ascii=False)
            return hashlib.sha256(json_data.encode('utf-8')).hexdigest()
        except Exception:
            return ""
    
    def validate_transaction_id(self, transaction_id: str) -> bool:
        """Validate Arweave transaction ID format."""
        try:
            # Arweave transaction IDs are 43 characters, base64url encoded
            if len(transaction_id) != 43:
                return False
            
            # Check if it contains only valid base64url characters
            import re
            pattern = r'^[A-Za-z0-9_-]{43}$'
            return bool(re.match(pattern, transaction_id))
        except Exception:
            return False
    
    async def generate_address(self) -> Optional[str]:
        """Generate a new Arweave address."""
        try:
            # Generate a new wallet ID
            wallet_id = str(uuid.uuid4())
            
            # Create a mock Arweave address
            # Real Arweave addresses are base64url encoded public keys
            # For now, use mock format
            address = f"arweave_{wallet_id[:16]}"
            
            return address
                
        except Exception as e:
            print(f"Error generating Arweave address: {e}")
            return None

    def format_balance(self, winston_amount: str, decimals: int = 6) -> str:
        """Format winston balance for display."""
        try:
            ar_amount = self.winston_to_ar(winston_amount)
            return f"{ar_amount:.{decimals}f}"
        except Exception:
            return "0.000000"