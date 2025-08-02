import os
import json
import time
import uuid
import random
from datetime import datetime
from typing import Dict, Any, Optional
from base64 import b64encode, b64decode
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
from dotenv import load_dotenv

# Check if we should use the mock Arweave client
USE_MOCK_ARWEAVE = os.getenv('USE_MOCK_ARWEAVE', 'true').lower() == 'true'

if not USE_MOCK_ARWEAVE:
    from arweave import Wallet, Transaction, arql
else:
    print("Using MOCK Arweave client for testing")

load_dotenv()

# Mock transaction storage for simulation
class MockTransaction:
    def __init__(self, data: bytes, wallet_address: str):
        self.id = str(uuid.uuid4())
        self.data = data
        self.wallet_address = wallet_address
        self.timestamp = datetime.utcnow()
        self.status = 'pending'
        self.block_height = None
        self.tags = []
    
    def add_tag(self, name: str, value: str):
        self.tags.append({'name': name, 'value': value})
    
    def sign(self):
        pass  # No actual signing in mock
    
    def send(self) -> str:
        # Simulate network delay
        time.sleep(0.5)
        # 90% chance of success in simulation
        if random.random() < 0.9:
            self.status = 'mined'
            self.block_height = random.randint(1000000, 2000000)
        else:
            self.status = 'failed'
        return self.id

# Mock Wallet class for simulation
class MockWallet:
    def __init__(self, jwk_data: Optional[Dict] = None):
        self.address = f'mock_wallet_{random.randint(1000, 9999)}'
        self.balance = 10.0  # Default balance for testing
        self.jwk_data = jwk_data or {}
    
    @classmethod
    def generate(cls):
        return cls()
    
    @classmethod
    def from_data(cls, jwk_data: Dict):
        return cls(jwk_data)
    
    def to_dict(self) -> Dict:
        return {'kty': 'RSA', 'e': 'AQAB', 'n': 'mock_key'}

# Mock Transaction class for simulation
class MockArweaveTransaction:
    def __init__(self, wallet, data: bytes, **kwargs):
        self.wallet = wallet
        self.data = data
        self.quantity = kwargs.get('quantity', 0)
        self.target = kwargs.get('target', '')
        self.tags = []
    
    def add_tag(self, name: str, value: str):
        self.tags.append({'name': name, 'value': value})
    
    def sign(self):
        pass
    
    def send(self) -> str:
        # Simulate transaction submission
        time.sleep(0.5)
        # 90% chance of success in simulation
        if random.random() < 0.9:
            return f'tx_{uuid.uuid4().hex}'
        else:
            raise Exception("Simulated transaction failure")

class ArweaveClient:
    def __init__(self, wallet_file=None, gateway_url=None, use_mock=True):
        """
        Initialize the Arweave client with wallet and gateway URL.
        
        Args:
            wallet_file: Path to wallet file (optional)
            gateway_url: Arweave gateway URL (optional)
            use_mock: Whether to use the mock client (default: True)
        """
        self.gateway_url = gateway_url or os.getenv('ARWEAVE_GATEWAY_URL', 'https://arweave.net')
        self.wallet_file = wallet_file or os.getenv('ARWEAVE_WALLET_FILE', 'wallet.json')
        self.use_mock = use_mock
        
        if self.use_mock:
            print("Using MOCK Arweave client - no real blockchain transactions will occur")
            self.wallet = MockWallet()
            self.session = None
            self._mock_transactions = {}
        else:
            try:
                from arweave import Wallet, Transaction, arql
                self.Wallet = Wallet
                self.Transaction = Transaction
                self.wallet = self._load_or_create_wallet()
                import requests
                self.session = requests.Session()
            except ImportError:
                print("Warning: arweave-python-client not found. Falling back to mock client.")
                self.use_mock = True
                self.wallet = MockWallet()
                self.session = None
                self._mock_transactions = {}
        
        # Check wallet balance on initialization
        self._check_wallet_balance()
        
    def _check_wallet_balance(self):
        """Check the wallet balance and warn if it's too low."""
        try:
            if self.use_mock:
                print("\n=== MOCK ARWEAVE WALLET ===")
                print(f"Address: {self.wallet.address}")
                print("Balance: 10.0 AR (simulated)")
                print("==========================\n")
                return
                
            # Only try to check real balance if not using mock
            balance = self.get_wallet_balance()
            print(f"\n=== ARWEAVE WALLET ===")
            print(f"Address: {self.wallet.address}")
            print(f"Balance: {balance} AR")
            print("====================\n")
            
            # Minimum balance needed for a basic transaction (0.5 AR for safety)
            min_balance = 0.5
            if balance < min_balance:
                print(f"WARNING: Wallet balance is low ({balance} AR). Please add more AR to your wallet to make transactions.")
                print(f"You can get test AR from the Arweave faucet: https://faucet.arweave.net/")
                print(f"Your wallet address: {self.wallet.address}")
        except Exception as e:
            print(f"Warning: Could not check wallet balance: {e}")
            if not self.use_mock:
                print("Falling back to mock wallet")
                self.use_mock = True
                self.wallet = MockWallet()
                self._check_wallet_balance()  # Retry with mock wallet
    
    def get_wallet_balance(self):
        """Get the wallet balance in AR."""
        if self.use_mock:
            return 10.0  # Simulated balance for testing
            
        winston_balance = self.wallet.balance
        # Convert winston to AR (1 AR = 10^12 winston)
        ar_balance = winston_balance / 10**12
        return ar_balance
    
    def _generate_wallet(self):
        """Generate a new Arweave wallet with a new RSA key pair."""
        try:
            # Generate a new RSA key pair
            key = RSA.generate(4096)
            
            # Helper function to safely convert RSA components to base64
            def int_to_b64(i):
                if not i:
                    return "AQAB"  # Default public exponent if not provided
                # Convert to bytes and encode as base64url without padding
                return b64encode(i.to_bytes((i.bit_length() + 7) // 8, byteorder='big')).decode('utf-8').rstrip('=').replace('+', '-').replace('/', '_')
            
            # Get the private key components
            private_key = key.export_key('PEM')
            key_components = RSA.import_key(private_key)
            
            # Generate a new RSA key pair using cryptography library
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.backends import default_backend
            import base64
            import json
            
            # Generate a new RSA private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=4096,
                backend=default_backend()
            )
            
            # Get the private key numbers
            private_numbers = private_key.private_numbers()
            public_numbers = private_numbers.public_numbers
            
            # Convert numbers to base64url encoded strings
            def int_to_base64url(number):
                # Convert to bytes
                number_bytes = number.to_bytes((number.bit_length() + 7) // 8, byteorder='big')
                # Encode to base64url
                return base64.urlsafe_b64encode(number_bytes).decode('utf-8').rstrip('=')
            
            # Create the JWK structure
            wallet_data = {
                'kty': 'RSA',  # Key Type
                'n': int_to_base64url(public_numbers.n),  # Modulus
                'e': int_to_base64url(public_numbers.e),  # Public Exponent
                'd': int_to_base64url(private_numbers.d),  # Private Exponent
                'p': int_to_base64url(private_numbers.p),  # First Prime Factor
                'q': int_to_base64url(private_numbers.q),  # Second Prime Factor
                'dp': int_to_base64url(private_numbers.dmp1),  # First Factor CRT Exponent
                'dq': int_to_base64url(private_numbers.dmq1),  # Second Factor CRT Exponent
                'qi': int_to_base64url(private_numbers.iqmp),  # First CRT Coefficient
                'ext': True
            }
            
            # Create a temporary file with the JWK data
            with open(self.wallet_file, 'w') as f:
                json.dump(wallet_data, f, indent=2)
            
            # Now load the wallet from the file
            wallet = Wallet(self.wallet_file)
            
            # Save the wallet data to a file
            with open(self.wallet_file, 'w') as f:
                json.dump(wallet_data, f, indent=2)
            
            print(f"New wallet created and saved to {self.wallet_file}")
            
            # Now load the wallet from the file we just created
            wallet = Wallet(self.wallet_file)
            print(f"Wallet address: {wallet.address}")
            print("Please fund this wallet with some AR tokens to make transactions.")
            return wallet
            
        except Exception as e:
            print(f"Error generating wallet: {e}")
            raise
    
    def _load_or_create_wallet(self):
        """Load an existing Arweave wallet or create a new one if it doesn't exist."""
        if os.path.exists(self.wallet_file):
            try:
                with open(self.wallet_file, 'r') as f:
                    wallet_data = json.load(f)
                wallet = Wallet(wallet_data)
                print(f"Loaded existing wallet: {wallet.address}")
                return wallet
            except Exception as e:
                print(f"Error loading wallet: {e}")
                print("Generating a new wallet...")
                return self._generate_wallet()
        else:
            print("No existing wallet found. Generating a new one...")
            return self._generate_wallet()
    
    async def store_data(self, data: dict, tx_id: str = None, tags: Optional[dict] = None) -> Optional[str]:
        """
        Store data on Arweave with optional tags for querying.
        
        Args:
            data: The data to store (must be JSON-serializable)
            tx_id: Optional transaction ID to update existing data
            tags: Optional dictionary of tags to include with the transaction
            
        Returns:
            str: The transaction ID if successful, None otherwise
        """
        try:
            if self.use_mock:
                # Generate a mock transaction ID
                mock_id = f"mock_tx_{len(str(data))}_{hash(str(data)) % 10000}"
                print(f"[MOCK] Stored data with ID: {mock_id}")
                print(f"[MOCK] Data: {json.dumps(data, indent=2)}")
                if tags:
                    print(f"[MOCK] Tags: {tags}")
                return mock_id
                
            # In a real implementation, create and send a transaction
            # transaction = Transaction(self.wallet, data=json.dumps(data).encode())
            # transaction.add_tag('Content-Type', 'application/json')
            # 
            # # Add custom tags if provided
            # if tags:
            #     for key, value in tags.items():
            #         transaction.add_tag(key, str(value))
            # 
            # await transaction.sign()
            # response = await transaction.send()
            # return response.id
                
                # Convert data to bytes if it's a dictionary or string
                if isinstance(data, dict):
                    data_str = json.dumps(data, indent=2)
                    data_bytes = data_str.encode('utf-8')
                elif isinstance(data, str):
                    data_str = data
                    data_bytes = data.encode('utf-8')
                else:
                    data_bytes = data
                    data_str = data_bytes.decode('utf-8', errors='replace')
                
                # Create a mock transaction
                tx = MockArweaveTransaction(self.wallet, data_bytes)
                
                # Add all tags
                for tag in tags:
                    tx.add_tag(tag['name'], tag['value'])
                
                # Simulate transaction submission
                try:
                    print("\n=== SIMULATING ARWEAVE TRANSACTION ===")
                    print(f"From: {self.wallet.address}")
                    print(f"Data size: {len(data_bytes)} bytes")
                    print("Tags:", json.dumps(tags, indent=2))
                    print("\nData preview:")
                    print("-" * 40)
                    print(data_str[:500] + ('...' if len(data_str) > 500 else ''))
                    print("-" * 40)
                    
                    tx_id = tx.send()
                    print(f"\n✅ Transaction simulated successfully!")
                    print(f"Transaction ID: {tx_id}")
                    print("=" * 50 + "\n")
                    return tx_id
                except Exception as e:
                    print(f"\n❌ Simulated transaction failed: {e}")
                    print("=" * 50 + "\n")
                    raise Exception(f"Simulated transaction failed: {e}")
            
            else:
                # Real Arweave transaction
                if isinstance(data, dict):
                    data = json.dumps(data).encode('utf-8')
                elif isinstance(data, str):
                    data = data.encode('utf-8')
                
                # Convert tags to the format expected by arweave-python-client
                if tags is None:
                    tags = [
                        {'name': 'Content-Type', 'value': 'application/json'},
                        {'name': 'App-Name', 'value': 'SapphireExchange'}
                    ]
                
                # Create transaction
                transaction = self.Transaction(
                    wallet=self.wallet,
                    data=data,
                    quantity=0,
                    target=''
                )
                
                # Add all tags
                for tag in tags:
                    transaction.add_tag(tag['name'], tag['value'])
                
                # Sign and submit
                print("\n=== SUBMITTING TO ARWEAVE NETWORK ===")
                print(f"From: {self.wallet.address}")
                print(f"Data size: {len(data)} bytes")
                print("Tags:", json.dumps(tags, indent=2))
                print("\nSigning and submitting transaction...")
                
                transaction.sign()
                tx_id = transaction.send()
                
                print(f"\n✅ Transaction submitted successfully!")
                print(f"Transaction ID: {tx_id}")
                print(f"View on Arweave: https://viewblock.io/arweave/tx/{tx_id}")
                print("=" * 50 + "\n")
                
                return tx_id
                
        except Exception as e:
            print(f"Error storing data on Arweave: {e}")
            raise
    
    def get_data(self, transaction_id):
        """Retrieve data from Arweave using a transaction ID."""
        try:
            transaction = ArweaveTransaction.get_transaction(transaction_id)
            data = transaction.data
            
            # Try to parse as JSON, return raw data if not JSON
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return data.decode('utf-8')
        except Exception as e:
            print(f"Error retrieving data: {e}")
            return None

# Example usage
if __name__ == "__main__":
    # Initialize client
    client = ArweaveClient()
    
    # Example data to store
    data = {
        "item_id": "123",
        "name": "Test Item",
        "description": "This is a test item stored on Arweave",
        "price": "1.5"
    }
    
    # Store the data
    tx_id = client.store_data(data)
    print(f"Data stored with transaction ID: {tx_id}")
    
    # Retrieve the data
    if tx_id:
        retrieved_data = client.get_data(tx_id)
        print("Retrieved data:", retrieved_data)
