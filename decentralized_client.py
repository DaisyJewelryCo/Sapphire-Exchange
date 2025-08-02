"""
Sapphire Exchange - Decentralized Client

This client interacts directly with Arweave and Nano networks without relying on a centralized API.
"""
import json
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

from .arweave_utils import ArweaveClient
from .nano_utils import NanoWallet, verify_message, sign_message
from .models import User, Item, Auction

class DecentralizedClient:
    """Client for interacting with the decentralized Sapphire Exchange."""
    
    def __init__(self, arweave_client: Optional[ArweaveClient] = None):
        self.arweave = arweave_client or ArweaveClient()
        self.user_wallet = None
        self.user_data = None
        
    async def initialize_user(self, seed_phrase: str = None, wallet_data: dict = None):
        """Initialize or load user wallet and data."""
        self.user_wallet = NanoWallet(seed_phrase) if seed_phrase else NanoWallet.from_dict(wallet_data)
        self.user_data = await self._load_user_data()
        
        if not self.user_data:
            # Create new user if not found
            self.user_data = User(
                public_key=self.user_wallet.public_key,
                username=f"user_{self.user_wallet.public_key[:8]}",
                created_at=datetime.now(timezone.utc).isoformat()
            )
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
            'nano_address': item_wallet.public_key,
            'nano_seed': item_wallet.seed,  # In a real implementation, this would be encrypted
            **(metadata or {})
        }
        
        # Store item data on Arweave
        tx_id = await self.arweave.store_data(item_metadata)
        
        # Create local item object
        item = Item(
            item_id=tx_id,  # Use Arweave TX ID as item ID
            name=name,
            description=description,
            owner_public_key=self.user_wallet.public_key,
            starting_price=starting_price,
            is_auction=True,
            auction_end_time=item_metadata['auction_end_time'],
            metadata={
                'nano_address': item_wallet.public_key,
                'arweave_tx': tx_id,
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

# Example usage
async def example_usage():
    # Initialize client
    client = DecentralizedClient()
    
    # Initialize user (creates new or loads existing)
    await client.initialize_user()
    
    # Create a new item
    item, tx_id = await client.create_item(
        name="Rare Digital Art",
        description="A unique digital artwork",
        starting_price=1.0,
        duration_hours=24
    )
    print(f"Created item with TX ID: {tx_id}")
    
    # Get item data
    item_data = await client.get_item(tx_id)
    print(f"Item data: {json.dumps(item_data, indent=2)}")

if __name__ == "__main__":
    asyncio.run(example_usage())
