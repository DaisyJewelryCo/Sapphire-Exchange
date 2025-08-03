"""
Sapphire Exchange - Decentralized Client

This client interacts directly with Arweave and Nano networks without relying on a centralized API.
"""
import json
import asyncio
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any

from arweave_utils import ArweaveClient
from nano_utils import NanoWallet, NanoRPC, MOCK_MODE
from models import User, Item, Auction

class DecentralizedClient:
    """Client for interacting with the decentralized Sapphire Exchange."""
    
    def __init__(self, arweave_client: Optional[ArweaveClient] = None, mock_mode: bool = MOCK_MODE):
        """
        Initialize the decentralized client.
        
        Args:
            arweave_client: Optional Arweave client instance
            mock_mode: If True, use mock network for testing
        """
        self.arweave = arweave_client or ArweaveClient(mock_mode=mock_mode)
        self.mock_mode = mock_mode
        self.user_wallet = None
        self.user_data = None
        self.nano_rpc = NanoRPC(mock_mode=mock_mode)
        
    def get_seed_phrase(self) -> Optional[str]:
        """
        Get the seed phrase for the current wallet.
        
        Returns:
            Optional[str]: The seed phrase as a string, or None if not available
        """
        if not self.user_wallet or not hasattr(self.user_wallet, 'private_key'):
            return None
            
        try:
            # Get the private key as bytes and convert to hex string
            private_key_bytes = self.user_wallet.private_key.to_ascii(encoding='hex')
            return private_key_bytes.decode('utf-8')
        except Exception as e:
            print(f"Error getting seed phrase: {e}")
            return None
            
    async def initialize_user(self, seed_phrase: str = None, wallet_data: dict = None) -> Optional[User]:
        """
        Initialize or load user wallet and data.
        
        Args:
            seed_phrase: Optional seed phrase to initialize the wallet
            wallet_data: Optional wallet data dictionary to load from
            
        Returns:
            User: The loaded or created user data
            
        Raises:
            ValueError: If neither seed_phrase nor wallet_data is provided and mock mode is off
        """
        if seed_phrase is not None:
            # Create a new wallet from the seed phrase
            print(f"Initializing wallet from seed phrase (mock_mode={self.mock_mode})")
            self.user_wallet = NanoWallet(seed_phrase, mock_mode=self.mock_mode)
        elif wallet_data and isinstance(wallet_data, dict):
            # Load existing wallet from dictionary
            print(f"Initializing wallet from wallet data (mock_mode={self.mock_mode})")
            self.user_wallet = NanoWallet.from_dict(wallet_data)
            self.user_wallet.mock_mode = self.mock_mode
        elif self.mock_mode:
            # In mock mode, generate a new wallet with a random seed
            print(f"Generating new wallet in mock mode")
            self.user_wallet = NanoWallet(mock_mode=True)
            print(f"Generated new wallet with address: {self.user_wallet.address}")
        else:
            raise ValueError("Either seed_phrase or wallet_data must be provided in non-mock mode")
            
        self.user_data = await self._load_user_data()
        
        if not self.user_data:
            # Create new user if not found
            # Get the public key as a string
            public_key_str = self.user_wallet.public_key.to_ascii(encoding='hex').decode('utf-8')
            
            self.user_data = User(
                public_key=public_key_str,
                username=f"user_{public_key_str[:8]}",
                created_at=datetime.now(timezone.utc).isoformat()
            )
            print(f"Created new user with public key: {public_key_str}")
            await self._save_user_data()
            
        return self.user_data
    
    async def create_item(
        self, 
        name: str, 
        description: str,
        starting_price: float,
        duration_hours: float = 24.0,
        image_data: Optional[bytes] = None,
        metadata: Optional[dict] = None
    ) -> Tuple[Item, str]:
        """Create a new item for auction."""
        if not self.user_wallet:
            raise ValueError("User wallet not initialized")
            
        # Generate a new Nano wallet for the item
        item_wallet = NanoWallet.generate()
        
        # Generate realistic-looking mock IDs
        import random
        import string
        
        def generate_mock_tx_id():
            return 'tx_' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=43))
            
        def generate_mock_nano_address():
            prefix = 'nano_'
            chars = '13456789abcdefghijkmnopqrstuwxyz'
            return prefix + ''.join(random.choices(chars, k=60))
        
        # Generate mock IDs
        tx_id = generate_mock_tx_id()
        nano_address = generate_mock_nano_address()
        
        # Prepare item data
        item_metadata = {
            'name': name,
            'description': description,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'starting_price': starting_price,
            'duration_hours': duration_hours,
            'original_owner': self.user_wallet.public_key,
            'current_owner': self.user_wallet.public_key,
            'is_auction': True,
            'auction_end_time': (datetime.now(timezone.utc) + timedelta(hours=duration_hours)).isoformat(),
            'nano_address': nano_address,
            'nano_seed': item_wallet.seed,  # In a real implementation, this would be encrypted
            'transaction_id': tx_id,  # Add transaction ID for reference
            **(metadata or {})
        }
        
        # In mock mode, we'll use our generated IDs
        if self.mock_mode:
            print(f"[MOCK] Stored item data with ID: {tx_id}")
            print(f"[MOCK] Item Nano address: {nano_address}")
        else:
            # Store item data on Arweave in non-mock mode
            tx_id = await self.arweave.store_data(item_metadata)
            
        # Create local item object
        item = Item(
            item_id=tx_id,  # Use transaction ID as item ID
            name=name,
            description=description,
            owner_public_key=self.user_wallet.public_key,
            starting_price=starting_price,
            is_auction=True,
            auction_end_time=item_metadata['auction_end_time'],
            metadata={
                'nano_address': nano_address,
                'arweave_tx': tx_id,
                'transaction_id': tx_id,
                **(metadata or {})
            }
        )
        
        # Add to user's inventory
        self.user_data.inventory.append(tx_id)
        await self._save_user_data()
        
        return item, tx_id
    
    async def place_bid(self, item_tx_id: str, amount: float) -> bool:
        """Place a bid on an item."""
        if not self.user_wallet:
            raise ValueError("User wallet not initialized")
            
        # Get item data from Arweave
        item_data = await self.arweave.get_data(item_tx_id)
        if not item_data:
            raise ValueError("Item not found")
            
        # Verify auction is still active
        auction_end = datetime.fromisoformat(item_data['auction_end_time'].replace('Z', '+00:00'))
        if datetime.now(timezone.utc) > auction_end:
            raise ValueError("Auction has ended")
            
        # Verify bid amount is higher than current bid
        current_bid = item_data.get('current_bid', item_data['starting_price'])
        if amount <= current_bid:
            raise ValueError(f"Bid must be higher than {current_bid}")
            
        # Create bid transaction
        bid_data = {
            'type': 'bid',
            'item_tx': item_tx_id,
            'bidder': self.user_wallet.public_key,
            'amount': amount,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'signature': sign_message(f"{item_tx_id}:{amount}", self.user_wallet.private_key)
        }
        
        # Store bid on Arweave
        bid_tx_id = await self.arweave.store_data(bid_data)
        
        # Update item with new bid
        item_data['current_bid'] = amount
        item_data['current_bidder'] = self.user_wallet.public_key
        
        # Extend auction time if it's about to end (sniping protection)
        time_remaining = auction_end - datetime.now(timezone.utc)
        if time_remaining < timedelta(minutes=5):
            new_end_time = datetime.now(timezone.utc) + timedelta(minutes=10)
            item_data['auction_end_time'] = new_end_time.isoformat()
        
        # Update item on Arweave
        await self.arweave.store_data(item_data, item_tx_id)
        
        return bid_tx_id
    
    async def get_item(self, tx_id: str) -> Optional[dict]:
        """Get item data from Arweave."""
        return await self.arweave.get_data(tx_id)
    
    async def get_user_inventory(self, public_key: str = None) -> List[dict]:
        """Get all items owned by a user."""
        public_key = public_key or (self.user_wallet.public_key if self.user_wallet else None)
        if not public_key:
            raise ValueError("No public key provided")
            
        # In a real implementation, you would query Arweave for items owned by this public key
        # This is a simplified version that would need to be expanded with proper Arweave querying
        return []
    
    async def _load_user_data(self) -> Optional[User]:
        """Load user data from Arweave."""
        if not self.user_wallet:
            return None
            
        # In a real implementation, you would query Arweave for user data
        # This is a simplified version
        return None
    
    async def _save_user_data(self) -> str:
        """Save user data to Arweave."""
        if not self.user_wallet or not self.user_data:
            raise ValueError("User wallet or data not initialized")
            
        # Convert user data to dict
        user_dict = self.user_data.to_dict()
        
        # Store on Arweave
        tx_id = await self.arweave.store_data(user_dict)
        
        return tx_id

    def get_seed_phrase(self) -> str:
        """Get the seed phrase of the user's wallet."""
        if not self.user_wallet:
            raise ValueError("User wallet not initialized")
        return self.user_wallet.seed

# Example usage
async def example_usage():
    # Enable mock mode for testing
    os.environ["MOCK_NANO"] = "true"
    os.environ["MOCK_ARWEAVE"] = "true"
    
    print("Starting example with mock networks...")
    
    # Create a client with mock networks
    client = DecentralizedClient(mock_mode=True)
    
    try:
        # Initialize a new user (will generate a new wallet)
        print("Initializing new user...")
        user = await client.initialize_user()
        print(f"Initialized user: {user.username} (Public Key: {user.public_key[:12]}...)")
        
        # Get and display the seed phrase (for testing purposes only!)
        seed_phrase = client.get_seed_phrase()
        print(f"Wallet Seed Phrase (SAVE THIS SECURELY): {seed_phrase}")
        
        # List items (empty at first)
        print("\nListing items...")
        items = await client.get_user_inventory()
        print(f"Found {len(items)} items")
        
        # Create a new item
        print("\nCreating a test item...")
        item = await client.create_item(
            name="Test Item",
            description="This is a test item created in mock mode",
            starting_price=1000000000000000000000000,  # 1 NANO
            duration_hours=24,
            image_url="https://example.com/image.jpg"
        )
        print(f"Created item: {item.name} (ID: {item.id})")
        
        # List items again (should show the new item)
        print("\nListing items again...")
        items = await client.get_user_inventory()
        print(f"Found {len(items)} items")
        
    except Exception as e:
        print(f"Error in example: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nExample completed. No real Nano or Arweave transactions were made.")

if __name__ == "__main__":
    asyncio.run(example_usage())
