import os
import base58
import hashlib
import ed25519_blake2b
import requests
import random
import string
from typing import Dict, Optional, Tuple, Union
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Global flag to enable/disable mock mode
MOCK_MODE = os.getenv('MOCK_NANO', 'true').lower() == 'true'

@dataclass
class MockAccount:
    """Mock Nano account for testing purposes."""
    address: str
    public_key: bytes
    balance: int = 0
    pending: int = 0
    frontier: Optional[str] = None
    representative: Optional[str] = None

class MockNanoNetwork:
    """Mock Nano network for testing without making real network calls."""
    def __init__(self):
        self.accounts: Dict[str, MockAccount] = {}
        self.blocks = {}
        
    def create_account(self, public_key: bytes, address: str) -> MockAccount:
        """Create a new mock account."""
        account = MockAccount(
            address=address,
            public_key=public_key,
            balance=0,
            pending=0,
            frontier=None,
            representative=None
        )
        self.accounts[address] = account
        return account
    
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
    def __init__(self, seed=None, mock_mode: bool = MOCK_MODE):
        """
        Initialize a Nano wallet with an optional seed.
        
        Args:
            seed: Seed for the wallet (None generates a new one)
            mock_mode: If True, use mock network for testing
        """
        self.mock_mode = mock_mode
        
        if seed is None:
            # Generate a random seed
            seed = os.urandom(32)  # 32 bytes for ed25519
        elif isinstance(seed, str):
            # If seed is a string, encode it to bytes
            seed = hashlib.sha256(seed.encode('utf-8')).digest()
        elif not isinstance(seed, bytes):
            raise ValueError("Seed must be either None, a string, or bytes")
            
        # Ensure the seed is 32 bytes
        if len(seed) != 32:
            seed = hashlib.sha256(seed).digest()[:32]
        
        # Create the signing key from the seed
        self.private_key = ed25519_blake2b.SigningKey(seed)
        self.public_key = self.private_key.get_verifying_key()
        self.address = self._public_key_to_address(self.public_key)
        
        # Register with mock network and database if in mock mode
        if self.mock_mode:
            from mock_servers import nano_db
            
            # Register with mock network
            if MOCK_NETWORK:
                MOCK_NETWORK.create_account(self.public_key, self.address)
                
            # Ensure account exists in the mock database with initial balance
            if self.address not in nano_db.accounts:
                nano_db.accounts[self.address] = 100.0  # Initial balance for new accounts
                nano_db.accounts_pending[self.address] = []
                print(f"[MOCK] Registered Nano account in mock DB: {self.address}")
            else:
                print(f"[MOCK] Using existing Nano account in mock DB: {self.address}")
    
    @staticmethod
    def _public_key_to_address(public_key):
        """Convert a public key to a Nano address."""
        # Get the raw bytes of the public key
        public_key_bytes = public_key.to_bytes()
        
        # Create a checksum of the public key
        blake2b_hash = hashlib.blake2b(public_key_bytes, digest_size=5).digest()
        
        # Combine public key and checksum
        account_bytes = public_key_bytes + blake2b_hash
        
        # Encode as base58
        return 'nano_' + base58.b58encode(account_bytes).decode('utf-8')
    
    def sign(self, message):
        """Sign a message with the wallet's private key."""
        if isinstance(message, str):
            message = message.encode('utf-8')
        return self.private_key.sign(message)
    
    def verify(self, message, signature):
        """Verify a signature with the wallet's public key."""
        if isinstance(message, str):
            message = message.encode('utf-8')
        try:
            self.public_key.verify(signature, message)
            return True
        except ed25519_blake2b.BadSignatureError:
            return False
    
    @property
    def seed(self):
        """Get the seed/private key as a hex string."""
        return self.private_key.to_ascii(encoding='hex').decode('utf-8')
    
    def to_dict(self):
        """Convert the wallet to a dictionary for serialization."""
        return {
            'private_key': self.seed,
            'public_key': self.public_key.to_ascii(encoding='hex').decode('utf-8'),
            'address': self.address
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create a wallet from a dictionary."""
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary")
        
        wallet = cls()
        wallet.private_key = ed25519_blake2b.SigningKey(data['private_key'], encoding='hex')
        wallet.public_key = ed25519_blake2b.VerifyingKey(data['public_key'], encoding='hex')
        wallet.address = data.get('address')
        
        # If address is not provided, generate it from the public key
        if not wallet.address:
            wallet.address = wallet._public_key_to_address(wallet.public_key)
            
        return wallet
        
    @classmethod
    def from_seed(cls, seed_phrase):
        """
        Create a wallet from a seed phrase.
        
        Args:
            seed_phrase: The seed phrase as a string
            
        Returns:
            NanoWallet: A new wallet instance
        """
        return cls(seed=seed_phrase.encode('utf-8'))

class NanoRPC:
    """Client for interacting with the Nano network."""
    def __init__(self, node_url: str = None, mock_mode: bool = MOCK_MODE):
        """
        Initialize the Nano RPC client.
        
        Args:
            node_url: URL of the Nano node RPC endpoint
            mock_mode: If True, use mock network for testing
        """
        self.mock_mode = mock_mode
        self.node_url = node_url or os.getenv('NANO_NODE_URL', 'https://mynano.ninja/api')
    
    def send_rpc(self, action: str, **params) -> dict:
        """
        Send a JSON-RPC request to the Nano node or mock network.
        
        Args:
            action: The RPC action to perform
            **params: Additional parameters for the action
            
        Returns:
            dict: The JSON response from the node or mock data
        """
        if self.mock_mode and MOCK_NETWORK:
            return self._mock_rpc(action, **params)
            
        # Real network call (disabled by default in mock mode)
        if self.mock_mode:
            print("WARNING: Making real Nano network call in mock mode. Set MOCK_NANO=true to enable mock network.")
            
        payload = {
            "action": action,
            **params
        }
        try:
            response = requests.post(self.node_url, json=payload, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error calling Nano RPC: {e}")
            return {"error": str(e)}
    
    def _mock_rpc(self, action: str, **params) -> dict:
        """Handle RPC calls in mock mode."""
        if action == "account_balance":
            return self._mock_account_balance(**params)
        elif action == "account_info":
            return self._mock_account_info(**params)
        elif action == "account_create":
            return self._mock_account_create(**params)
        elif action == "send":
            return self._mock_send(**params)
        else:
            return {"error": f"Unsupported mock action: {action}"}
    
    def _mock_account_balance(self, account: str, **kwargs) -> dict:
        """Mock implementation of account_balance RPC."""
        mock_account = MOCK_NETWORK.get_account(account)
        if not mock_account:
            return {"error": "Account not found"}
        return {
            "balance": str(mock_account.balance),
            "pending": str(mock_account.pending)
        }
    
    def _mock_account_info(self, account: str, **kwargs) -> dict:
        """Mock implementation of account_info RPC."""
        mock_account = MOCK_NETWORK.get_account(account)
        if not mock_account:
            return {"error": "Account not found"}
        return {
            "frontier": mock_account.frontier or "0" * 64,
            "open_block": mock_account.frontier or "0" * 64,
            "representative_block": "0" * 64,
            "balance": str(mock_account.balance),
            "modified_timestamp": str(int(time.time())),
            "block_count": "1",
            "account_version": "1",
            "confirmation_height": "1",
            "confirmation_height_frontier": "0" * 64
        }
    
    def _mock_account_create(self, wallet: str, **kwargs) -> dict:
        """Mock implementation of account_create RPC."""
        # In a real implementation, this would create a new account in the wallet
        return {
            "account": f"nano_{''.join(random.choices('13456789abcdefghijkmnopqrstuwxyz', k=60))}"
        }
    
    def _mock_send(self, wallet: str, source: str, destination: str, amount: str, **kwargs) -> dict:
        """Mock implementation of send RPC."""
        try:
            amount_raw = int(amount)
        except (ValueError, TypeError):
            return {"error": "Invalid amount"}
            
        if MOCK_NETWORK.process_payment(source, destination, amount_raw):
            return {"block": "0" * 64}
        return {"error": "Payment failed"}
    
    def get_account_balance(self, account: str) -> int:
        """
        Get the balance of a Nano account.
        
        Args:
            account: The Nano account address
            
        Returns:
            int: The account balance in raw units
        """
        response = self.send_rpc("account_balance", account=account)
        return int(response.get("balance", 0)) if response and "error" not in response else 0
    
    def send_payment(self, wallet: 'NanoWallet', destination: str, amount: int) -> dict:
        """
        Send a payment from one account to another.
        
        Args:
            wallet: The source wallet
            destination: The destination account address
            amount: The amount to send in raw units
            
        Returns:
            dict: The transaction result
        """
        if self.mock_mode and MOCK_NETWORK:
            if MOCK_NETWORK.process_payment(wallet.address, destination, amount):
                return {"block": "0" * 64}
            return {"error": "Payment failed"}
            
        # In a real implementation, this would create and sign a block
        # and broadcast it to the network
        return {"block": "mock_block_hash"}
        # 3. Sign the block
        # 4. Publish the block
        raise NotImplementedError("This is a placeholder. Implement proper block creation and signing.")

def encode_item_data(item_id):
    """Encode an item ID into 32 bits for Nano coin representation."""
    if isinstance(item_id, str):
        item_id = int(item_id)
    return item_id & 0xFFFFFFFF  # Ensure it's 32 bits
