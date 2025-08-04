import os
import base58
import hashlib
import ed25519_blake2b
import requests
import json
import time
from typing import Dict, Optional, Any, Union, List, Tuple
from datetime import datetime, timedelta

# Configuration
MOCK_MODE = True  # Set to False to use real Nano network
NANO_NODE_URL = "http://[::1]:7076"  # Default local node URL
NANO_REPRESENTATIVE = "nano_3t6k35gi95xu6tergt6p69ck76ogmitsa8mnijtpxm9fkcm736xtoncuohr3"  # Official representative

class MockAccount:
    """Mock Nano account for testing purposes."""
    def __init__(self, address: str, public_key: bytes):
        self.address = address
        self.public_key = public_key
        self.balance: int = 0
        self.pending: int = 0
        self.frontier: Optional[str] = None
        self.representative: Optional[str] = None

class MockNanoNetwork:
    """Mock Nano network for testing without making real network calls."""
    def __init__(self):
        self.accounts: Dict[str, MockAccount] = {}
        self.blocks = {}
    
    def create_account(self, public_key: bytes, address: str):
        """Create a new mock account."""
        if address not in self.accounts:
            self.accounts[address] = MockAccount(address, public_key)
            self.accounts[address].balance = 100 * 10**30  # 100 NANO in raw
            self.accounts[address].representative = NANO_REPRESENTATIVE
    
    def get_account(self, address: str) -> Optional[MockAccount]:
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

# Global mock network instance for testing
MOCK_NETWORK = MockNanoNetwork() if MOCK_MODE else None

class NanoWallet:
    """A wallet for Nano cryptocurrency."""
    
    def __init__(self, seed=None, mock_mode: bool = MOCK_MODE):
        """
        Initialize a Nano wallet with an optional seed.
        
        Args:
            seed: Seed for the wallet (None generates a new one). Can be:
                  - None: Generates a new random seed
                  - str: A seed phrase that will be hashed
                  - bytes: Raw 32-byte seed
            mock_mode: If True, use mock network for testing
            
        Raises:
            ValueError: If wallet initialization fails
        """
        print("\n=== Initializing NanoWallet ===")
        self.mock_mode = mock_mode
        
        try:
            # 1. Process the seed
            if seed is None:
                print("Generating new random seed...")
                seed_bytes = os.urandom(32)  # 32 bytes for ed25519
                print(f"Generated random seed: {seed_bytes.hex()}")
            elif isinstance(seed, str):
                print(f"Using provided seed phrase (length: {len(seed)} chars)")
                seed_bytes = hashlib.sha256(seed.encode('utf-8')).digest()
                print(f"Hashed seed to bytes: {seed_bytes.hex()}")
            elif isinstance(seed, bytes):
                print(f"Using provided seed bytes (length: {len(seed)})")
                seed_bytes = seed
            else:
                raise ValueError("Seed must be None, a string, or bytes")
            
            # Ensure the seed is exactly 32 bytes
            if len(seed_bytes) != 32:
                print(f"Adjusting seed length to 32 bytes (was {len(seed_bytes)})")
                seed_bytes = hashlib.sha256(seed_bytes).digest()[:32]
            
            # 2. Create private key
            print("Creating private key from seed...")
            try:
                self.private_key = ed25519_blake2b.SigningKey(seed_bytes)
                print("Private key created successfully")
            except Exception as e:
                raise ValueError(f"Failed to create private key: {str(e)}")
            
            # 3. Derive public key
            print("Deriving public key...")
            try:
                self.public_key = self.private_key.get_verifying_key()
                if not self.public_key:
                    raise ValueError("get_verifying_key() returned None")
                print(f"Public key derived: {self.public_key.to_ascii(encoding='hex').decode()}")
            except Exception as e:
                raise ValueError(f"Failed to derive public key: {str(e)}")
            
            # 4. Generate address
            print("Generating address...")
            self.address = self._public_key_to_address(self.public_key)
            if not self.address or not isinstance(self.address, str) or not self.address.startswith('nano_'):
                raise ValueError(f"Invalid address generated: {self.address}")
            print(f"Address generated: {self.address}")
            
            # 5. Initialize mock network if needed
            if self.mock_mode:
                self._initialize_mock_network()
                
            print("=== Wallet initialization successful ===\n")
            
        except Exception as e:
            error_msg = f"Wallet initialization failed: {str(e)}"
            print(f"[ERROR] {error_msg}")
            import traceback
            traceback.print_exc()
            raise ValueError(error_msg) from e
    
    def _initialize_mock_network(self):
        """Initialize the wallet with the mock network and database."""
        if not self.mock_mode or MOCK_NETWORK is None:
            return
            
        print("Initializing mock network...")
        try:
            from mock_server import nano_db
            
            # Register with mock network
            print("Registering with mock network...")
            MOCK_NETWORK.create_account(self.public_key, self.address)
            
            # Initialize mock database if needed
            if not hasattr(nano_db, 'accounts'):
                nano_db.accounts = {}
            if not hasattr(nano_db, 'accounts_pending'):
                nano_db.accounts_pending = {}
            
            # Ensure account exists in the mock database with initial balance
            if self.address not in nano_db.accounts:
                print(f"Creating new mock account with balance")
                nano_db.accounts[self.address] = 100.0  # Initial balance for new accounts
                nano_db.accounts_pending[self.address] = []
                print(f"[MOCK] Registered Nano account in mock DB: {self.address}")
            else:
                print(f"[MOCK] Using existing Nano account in mock DB: {self.address}")
                
        except ImportError as e:
            print(f"[WARNING] Failed to import mock_server: {e}")
        except Exception as e:
            print(f"[WARNING] Error initializing mock network: {e}")
    
    @staticmethod
    def _public_key_to_address(public_key) -> str:
        """Convert a public key to a Nano address."""
        # Nano address format: xrb_ + account + checksum
        account = public_key.to_bytes()
        account_hash = hashlib.blake2b(account, digest_size=32).digest()
        account_encoded = base58.b58encode_check(account_hash).decode('ascii')
        return f"nano_{account_encoded}"
    
    def sign(self, message: bytes) -> bytes:
        """Sign a message with the wallet's private key."""
        return self.private_key.sign(message)
    
    def verify(self, message: bytes, signature: bytes) -> bool:
        """Verify a signature with the wallet's public key."""
        try:
            self.public_key.verify(signature, message)
            return True
        except Exception as e:
            print(f"Signature verification failed: {e}")
            return False
            
    @classmethod
    def from_seed(cls, seed_phrase: str, mock_mode: bool = MOCK_MODE) -> 'NanoWallet':
        """
        Create a wallet from a seed phrase.
        
        Args:
            seed_phrase: The seed phrase as a string (will be hashed to create the seed)
            mock_mode: If True, use mock network for testing
            
        Returns:
            NanoWallet: A new wallet instance
            
        Raises:
            ValueError: If seed_phrase is invalid or wallet initialization fails
            
        Example:
            >>> wallet = NanoWallet.from_seed("my secret seed phrase")
        """
        print("\n=== Creating wallet from seed phrase ===")
        
        # Validate input
        if not seed_phrase or not isinstance(seed_phrase, str):
            error_msg = "Seed phrase must be a non-empty string"
            print(f"[ERROR] {error_msg}")
            raise ValueError(error_msg)
            
        print(f"Seed phrase length: {len(seed_phrase)} characters")
        print(f"Mock mode: {mock_mode}")
        
        try:
            # 1. Convert seed phrase to bytes using UTF-8 encoding
            try:
                seed_bytes = seed_phrase.encode('utf-8')
                print(f"Seed phrase encoded to {len(seed_bytes)} bytes")
            except Exception as e:
                error_msg = f"Failed to encode seed phrase: {str(e)}"
                print(f"[ERROR] {error_msg}")
                raise ValueError(error_msg) from e
            
            # 2. Hash the seed bytes to get a consistent 32-byte value
            try:
                seed_hash = hashlib.sha256(seed_bytes).digest()
                print(f"SHA-256 hash of seed: {seed_hash.hex()}")
            except Exception as e:
                error_msg = f"Failed to hash seed: {str(e)}"
                print(f"[ERROR] {error_msg}")
                raise ValueError(error_msg) from e
            
            # 3. Create a new wallet with the hashed seed
            print("Creating wallet instance...")
            try:
                wallet = cls(seed=seed_hash, mock_mode=mock_mode)
            except Exception as e:
                error_msg = f"Failed to create wallet: {str(e)}"
                print(f"[ERROR] {error_msg}")
                raise ValueError(error_msg) from e
            
            # 4. Verify the wallet was properly initialized with all required attributes
            required_attrs = ['public_key', 'private_key', 'address']
            missing_attrs = [attr for attr in required_attrs 
                           if not hasattr(wallet, attr) or not getattr(wallet, attr, None)]
            
            if missing_attrs:
                error_msg = f"Wallet missing required attributes: {', '.join(missing_attrs)}"
                print(f"[ERROR] {error_msg}")
                print(f"Wallet attributes: {', '.join(dir(wallet))}")
                raise ValueError(error_msg)
            
            print(f"Successfully created wallet from seed phrase")
            print(f"Address: {wallet.address}")
            print(f"Public key: {wallet.public_key.to_ascii(encoding='hex').decode()}")
            print("=== Wallet creation complete ===\n")
            
            return wallet
            
        except Exception as e:
            error_msg = f"Failed to create wallet from seed phrase: {str(e)}"
            print(f"[ERROR] {error_msg}")
            import traceback
            traceback.print_exc()
            raise ValueError(error_msg) from e
    
    @property
    def seed_hex(self) -> str:
        """Get the seed/private key as a hex string."""
        return self.private_key.to_seed().hex()
    
    def to_dict(self) -> dict:
        """Convert the wallet to a dictionary for serialization."""
        return {
            'private_key': self.private_key.to_seed().hex(),
            'public_key': self.public_key.to_bytes().hex(),
            'address': self.address
        }
    
    @classmethod
    def from_dict(cls, data: dict, mock_mode: bool = MOCK_MODE) -> 'NanoWallet':
        """Create a wallet from a dictionary."""
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary")
        
        wallet = cls(mock_mode=mock_mode)
        wallet.private_key = ed25519_blake2b.SigningKey(bytes.fromhex(data['private_key']))
        wallet.public_key = ed25519_blake2b.VerifyingKey(bytes.fromhex(data['public_key']))
        wallet.address = data.get('address', wallet._public_key_to_address(wallet.public_key))
        return wallet
    
    @classmethod
    def from_seed(cls, seed_phrase: str, mock_mode: bool = MOCK_MODE) -> 'NanoWallet':
        """
        Create a wallet from a seed phrase.
        
        Args:
            seed_phrase: The seed phrase as a string
            mock_mode: If True, use mock network for testing
            
        Returns:
            NanoWallet: A new wallet instance
            
        Raises:
            ValueError: If seed_phrase is not a non-empty string or if wallet initialization fails
        """
        if not seed_phrase or not isinstance(seed_phrase, str):
            raise ValueError("Seed phrase must be a non-empty string")
            
        try:
            # Convert seed phrase to bytes and ensure it's 32 bytes
            seed = hashlib.sha256(seed_phrase.encode('utf-8')).digest()
            if len(seed) < 32:
                seed = hashlib.sha256(seed).digest()
            seed = seed[:32]
            
            # Create a new wallet with the seed and mock mode
            wallet = cls(seed=seed, mock_mode=mock_mode)
            
            # Verify the wallet was properly initialized
            if not hasattr(wallet, 'public_key') or wallet.public_key is None:
                raise ValueError("Failed to initialize wallet with the provided seed phrase")
                
            return wallet
            
        except Exception as e:
            # Clean up any partially created wallet
            if 'wallet' in locals():
                del wallet
            raise ValueError(f"Failed to create wallet from seed: {str(e)}")

class NanoRPC:
    """Client for interacting with the Nano network."""
    
    def __init__(self, node_url: str = NANO_NODE_URL, mock_mode: bool = MOCK_MODE):
        """
        Initialize the Nano RPC client.
        
        Args:
            node_url: URL of the Nano node RPC endpoint
            mock_mode: If True, use mock data instead of making real RPC calls
        """
        self.node_url = node_url
        self.mock_mode = mock_mode
        self.session = requests.Session()
    
    def _rpc_request(self, action: str, **params) -> dict:
        """
        Make an RPC request to the Nano node.
        
        Args:
            action: The RPC action to perform
            **params: Additional parameters for the RPC call
            
        Returns:
            dict: The JSON response from the node or mock data
        """
        if self.mock_mode:
            return self._mock_rpc(action, **params)
            
        payload = {
            "action": action,
            **params
        }
        
        try:
            response = self.session.post(self.node_url, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"RPC request failed: {e}")
            return {"error": str(e)}
    
    def _mock_rpc(self, action: str, **params) -> dict:
        """Handle RPC calls in mock mode."""
        handler_name = f"_mock_{action}"
        if hasattr(self, handler_name):
            return getattr(self, handler_name)(**params)
        return {"error": f"Unsupported action in mock mode: {action}"}
    
    def _mock_account_balance(self, account: str) -> dict:
        """Mock implementation of account_balance RPC."""
        from mock_server import nano_db
        
        balance = nano_db.accounts.get(account, 0.0)
        pending = sum(tx['amount'] for tx in nano_db.accounts_pending.get(account, []))
        
        return {
            "balance": str(int(balance * 10**30)),  # Convert to raw
            "pending": str(int(pending * 10**30)),
            "receivable": str(int(pending * 10**30))
        }
    
    def _mock_account_info(self, account: str, representative: bool = True) -> dict:
        """Mock implementation of account_info RPC."""
        from mock_server import nano_db
        
        if account not in nano_db.accounts:
            return {"error": "Account not found"}
            
        balance = nano_db.accounts[account]
        pending = sum(tx['amount'] for tx in nano_db.accounts_pending.get(account, []))
        
        result = {
            "frontier": "mock_frontier_hash",
            "open_block": "mock_open_block_hash",
            "representative_block": "mock_rep_block_hash",
            "balance": str(int(balance * 10**30)),  # Convert to raw
            "modified_timestamp": str(int(time.time())),
            "block_count": "1",
            "account_version": "1",
            "confirmation_height": "1",
            "confirmation_height_frontier": "mock_confirmation_hash"
        }
        
        if representative:
            result["representative"] = NANO_REPRESENTATIVE
            
        return result
    
    def _mock_account_create(self, wallet: str, count: int = 1) -> dict:
        """Mock implementation of account_create RPC."""
        # In a real implementation, this would create new accounts in the wallet
        # For mock purposes, we'll just return some fake account addresses
        from mock_server import nano_db
        
        accounts = []
        for _ in range(count):
            # Generate a fake address
            address = f"nano_{'a' * 60}"
            accounts.append(address)
            
            # Add to mock database with initial balance
            if address not in nano_db.accounts:
                nano_db.accounts[address] = 100.0  # Initial balance
                nano_db.accounts_pending[address] = []
        
        return {"accounts": accounts}
    
    def _mock_block_confirm(self, hash: str) -> dict:
        """Mock implementation of block_confirm RPC."""
        # In a real implementation, this would confirm a block
        return {"started": "1"}
    
    def get_account_balance(self, account: str) -> dict:
        """
        Get the balance of a Nano account.
        
        Args:
            account: The Nano account address
            
        Returns:
            dict: The account balance information
        """
        return self._rpc_request("account_balance", account=account)
    
    def get_account_info(self, account: str, representative: bool = True) -> dict:
        """
        Get information about a Nano account.
        
        Args:
            account: The Nano account address
            representative: Whether to include representative information
            
        Returns:
            dict: The account information
        """
        return self._rpc_request("account_info", account=account, representative=representative)
    
    def create_account(self, wallet: str, count: int = 1) -> dict:
        """
        Create new Nano accounts.
        
        Args:
            wallet: The wallet ID to create accounts in
            count: Number of accounts to create
            
        Returns:
            dict: The created account information
        """
        return self._rpc_request("account_create", wallet=wallet, count=count)
    
    def send_payment(self, wallet_id: str, source: str, destination: str, amount: int) -> dict:
        """
        Send a payment from one account to another.
        
        Args:
            wallet_id: The wallet ID containing the source account
            source: The source account address
            destination: The destination account address
            amount: The amount to send in raw
            
        Returns:
            dict: The transaction result
        """
        # In a real implementation, this would:
        # 1. Get the account info to get the current block
        # 2. Create a new block with the transaction
        # 3. Sign the block
        # 4. Publish the block
        # For now, return a mock block hash
        return {"block": "mock_block_hash"}

def encode_item_data(item_id):
    """Encode an item ID into 32 bits for Nano coin representation.
    
    Args:
        item_id: The item ID as an integer or string
        
    Returns:
        int: A 32-bit encoded version of the item ID
    """
    if isinstance(item_id, str):
        item_id = int(item_id)
    return item_id & 0xFFFFFFFF  # Ensure it's 32 bits
