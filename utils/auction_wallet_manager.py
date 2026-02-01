"""
Auction wallet manager for Sapphire Exchange.
Generates deterministic Nano wallets for each auction based on user's seed.
"""
import hashlib
from typing import Dict, Optional, Any
from blockchain.nano_client import NanoClient


class AuctionWalletManager:
    """Manages generation and tracking of auction-specific Nano wallets."""
    
    def __init__(self, nano_client: NanoClient):
        """Initialize auction wallet manager."""
        self.nano_client = nano_client
    
    def generate_auction_wallet_index(self, item_id: str) -> int:
        """
        Generate deterministic wallet index from item ID.
        Uses SHA-256 hash of item_id to create a consistent, unique index.
        
        Args:
            item_id: The unique item/auction ID
            
        Returns:
            32-bit integer index derived from item_id
        """
        try:
            hash_bytes = hashlib.sha256(item_id.encode()).digest()
            index = int.from_bytes(hash_bytes[:4], 'big')
            return index
        except Exception as e:
            print(f"Error generating wallet index: {e}")
            return 0
    
    def create_auction_wallet(self, user_seed: bytes, item_id: str) -> Optional[Dict[str, Any]]:
        """
        Create a new auction wallet derived from user's master seed.
        
        The user has a master seed (index 0 for account, index 1+ for items).
        For each item, we derive a wallet using a deterministic index from the item ID.
        
        Args:
            user_seed: User's master Nano seed (32 bytes)
            item_id: The unique item/auction ID
            
        Returns:
            Dictionary with wallet details or None on failure
        """
        try:
            # Generate deterministic index from item_id
            wallet_index = self.generate_auction_wallet_index(item_id)
            
            # Derive private key from user's seed and wallet index
            private_key = self.nano_client.seed_to_private_key(user_seed, wallet_index)
            
            # Derive public key from private key
            public_key = self.nano_client.private_key_to_public_key(private_key)
            
            # Convert public key to Nano address
            address = self.nano_client.public_key_to_address(public_key)
            
            return {
                'nano_address': address,
                'nano_public_key': public_key.hex() if isinstance(public_key, bytes) else public_key,
                'nano_private_key': private_key.hex() if isinstance(private_key, bytes) else private_key,
                'nano_seed': user_seed.hex() if isinstance(user_seed, bytes) else user_seed,
                'wallet_index': wallet_index,
                'item_id': item_id
            }
        except Exception as e:
            print(f"Error creating auction wallet: {e}")
            return None
    
    def validate_auction_wallet(self, wallet_data: Dict[str, Any]) -> bool:
        """
        Validate that auction wallet data is correctly formed.
        
        Args:
            wallet_data: Wallet data dictionary to validate
            
        Returns:
            True if wallet data is valid, False otherwise
        """
        try:
            required_fields = [
                'nano_address', 'nano_public_key', 'nano_private_key',
                'nano_seed', 'wallet_index', 'item_id'
            ]
            
            # Check all required fields exist
            if not all(field in wallet_data for field in required_fields):
                return False
            
            # Validate address format
            address = wallet_data['nano_address']
            if not self.nano_client.validate_address(address):
                return False
            
            return True
        except Exception:
            return False
    
    def recreate_auction_wallet_from_seed(self, user_seed: bytes, item_id: str) -> Optional[Dict[str, Any]]:
        """
        Recreate an auction wallet from the user's seed and item ID.
        This allows users to recover their auction wallets from their master seed.
        
        Args:
            user_seed: User's master Nano seed (32 bytes)
            item_id: The unique item/auction ID
            
        Returns:
            Recreated wallet data or None on failure
        """
        return self.create_auction_wallet(user_seed, item_id)


# Global auction wallet manager instance (will be initialized with nano_client)
auction_wallet_manager: Optional[AuctionWalletManager] = None


def initialize_auction_wallet_manager(nano_client: NanoClient):
    """Initialize the global auction wallet manager."""
    global auction_wallet_manager
    auction_wallet_manager = AuctionWalletManager(nano_client)
    return auction_wallet_manager
