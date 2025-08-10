"""
Auction wallet utilities for Sapphire Exchange.
Provides wallet generation specifically for auction items.
"""
import asyncio
from typing import Dict, Optional, Tuple
from blockchain.nano_client import NanoClient
from blockchain.blockchain_manager import blockchain_manager
from utils.rsa_utils import generate_auction_rsa_keys


class AuctionWalletGenerator:
    """Generate wallets and RSA keys for auction items."""
    
    def __init__(self, nano_client: Optional[NanoClient] = None):
        """Initialize with optional nano client."""
        self.nano_client = nano_client or blockchain_manager.nano_client
    
    async def generate_auction_wallet_and_rsa(self, user_id: str, auction_id: str) -> Dict[str, str]:
        """
        Generate a new NANO wallet and RSA key pair for an auction item.
        
        Args:
            user_id: ID of the user creating the auction
            auction_id: ID of the auction/item
            
        Returns:
            Dictionary containing wallet and RSA data
        """
        try:
            # Generate new NANO wallet
            seed = self.nano_client.generate_seed()
            private_key = self.nano_client.seed_to_private_key(seed, 0)
            public_key = self.nano_client.private_key_to_public_key(private_key)
            nano_address = self.nano_client.public_key_to_address(public_key)
            
            # Generate RSA key pair
            rsa_data = generate_auction_rsa_keys(user_id, auction_id)
            
            # Create wallet data structure
            wallet_data = {
                # NANO wallet data
                'nano_address': nano_address,
                'nano_public_key': public_key.hex(),
                'nano_private_key': private_key.hex(),
                'nano_seed': seed.hex(),
                
                # RSA key data
                'rsa_private_key': rsa_data['private_key_base64'],
                'rsa_public_key': rsa_data['public_key_base64'],
                'rsa_fingerprint': rsa_data['fingerprint'],
                
                # Metadata
                'user_id': user_id,
                'auction_id': auction_id,
                'created_at': rsa_data['created_at'],
                'wallet_type': 'auction_item'
            }
            
            return wallet_data
            
        except Exception as e:
            print(f"Error generating auction wallet and RSA: {e}")
            return {}
    
    def create_nano_transaction_memo(self, user_id: str, rsa_fingerprint: str) -> str:
        """
        Create a memo for the first NANO transaction that includes user ID and RSA fingerprint.
        
        Args:
            user_id: User ID
            rsa_fingerprint: RSA key fingerprint
            
        Returns:
            32-character string for NANO transaction memo
        """
        try:
            # Combine user ID and RSA fingerprint
            combined = f"{user_id}:{rsa_fingerprint}"
            
            # Hash to create consistent 32-character string
            import hashlib
            hash_obj = hashlib.sha256(combined.encode('utf-8'))
            memo = hash_obj.hexdigest()[:32]  # Take first 32 characters
            
            return memo
            
        except Exception as e:
            print(f"Error creating transaction memo: {e}")
            return "00000000000000000000000000000000"  # Fallback 32-char string
    
    def validate_auction_wallet_data(self, wallet_data: Dict[str, str]) -> bool:
        """
        Validate auction wallet data structure.
        
        Args:
            wallet_data: Wallet data dictionary
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = [
            'nano_address', 'nano_public_key', 'nano_private_key', 'nano_seed',
            'rsa_private_key', 'rsa_public_key', 'rsa_fingerprint',
            'user_id', 'auction_id', 'created_at', 'wallet_type'
        ]
        
        for field in required_fields:
            if field not in wallet_data or not wallet_data[field]:
                return False
        
        # Validate NANO address format
        if not wallet_data['nano_address'].startswith('nano_'):
            return False
        
        # Validate wallet type
        if wallet_data['wallet_type'] != 'auction_item':
            return False
        
        return True


# Global instance
auction_wallet_generator = AuctionWalletGenerator()


# Convenience functions
async def generate_auction_wallet_and_rsa(user_id: str, auction_id: str) -> Dict[str, str]:
    """Generate wallet and RSA keys for an auction item."""
    return await auction_wallet_generator.generate_auction_wallet_and_rsa(user_id, auction_id)


def create_nano_memo(user_id: str, rsa_fingerprint: str) -> str:
    """Create NANO transaction memo with user ID and RSA fingerprint."""
    return auction_wallet_generator.create_nano_transaction_memo(user_id, rsa_fingerprint)