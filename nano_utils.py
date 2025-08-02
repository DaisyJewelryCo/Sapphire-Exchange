import os
import base58
import hashlib
import ed25519_blake2b
import requests
from dotenv import load_dotenv

load_dotenv()

class NanoWallet:
    def __init__(self, seed=None):
        """Initialize a Nano wallet with an optional seed."""
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

class NanoRPC:
    def __init__(self, node_url=None):
        self.node_url = node_url or os.getenv('NANO_NODE_URL', 'https://mynano.ninja/api')
    
    def send_rpc(self, action, **params):
        """Send a JSON-RPC request to the Nano node."""
        payload = {
            "action": action,
            **params
        }
        response = requests.post(self.node_url, json=payload)
        return response.json()
    
    def get_account_balance(self, account):
        """Get the balance of a Nano account."""
        return self.send_rpc("account_balance", account=account)
    
    def send_payment(self, wallet, destination, amount):
        """Send a payment from one account to another."""
        # This is a simplified version. In a real implementation, you would need to:
        # 1. Get the account info
        # 2. Create a block
        # 3. Sign the block
        # 4. Publish the block
        raise NotImplementedError("This is a placeholder. Implement proper block creation and signing.")

def encode_item_data(item_id):
    """Encode an item ID into 32 bits for Nano coin representation."""
    if isinstance(item_id, str):
        item_id = int(item_id)
    return item_id & 0xFFFFFFFF  # Ensure it's 32 bits
