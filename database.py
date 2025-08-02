"""
Database module for Sapphire Exchange using Arweave for storage.
"""
import json
from typing import Dict, List, Optional, Type, TypeVar, Generic
from dataclasses import asdict
from .models import User, Item, Auction
from .arweave_utils import ArweaveClient

T = TypeVar('T', User, Item, Auction)

class Database:
    """Database class for storing and retrieving data from Arweave."""
    
    def __init__(self, arweave_client: Optional[ArweaveClient] = None):
        """Initialize the database with an Arweave client."""
        self.arweave = arweave_client or ArweaveClient()
        self._cache: Dict[str, dict] = {}
        
    def _get_key(self, prefix: str, key: str) -> str:
        """Generate a storage key with prefix."""
        return f"{prefix}:{key}"
    
    async def store(self, obj: T) -> str:
        """Store an object in the database."""
        if isinstance(obj, User):
            prefix = "user"
            key = obj.public_key
        elif isinstance(obj, Item):
            prefix = "item"
            key = obj.item_id
        elif isinstance(obj, Auction):
            prefix = "auction"
            key = obj.auction_id
        else:
            raise ValueError(f"Unsupported object type: {type(obj)}")
        
        # Convert to dictionary and store
        data = asdict(obj)
        storage_key = self._get_key(prefix, key)
        
        # Store in Arweave
        tx_id = self.arweave.store_data({
            "type": prefix,
            "data": data,
            "timestamp": data.get('created_at')
        })
        
        # Cache the data
        self._cache[storage_key] = data
        
        return tx_id
    
    async def get_user(self, public_key: str) -> Optional[User]:
        """Get a user by public key."""
        storage_key = self._get_key("user", public_key)
        data = await self._get_data(storage_key, User)
        if data:
            return User.from_dict(data)
        return None
    
    async def get_item(self, item_id: str) -> Optional[Item]:
        """Get an item by ID."""
        storage_key = self._get_key("item", item_id)
        data = await self._get_data(storage_key, Item)
        if data:
            return Item.from_dict(data)
        return None
    
    async def get_auction(self, auction_id: str) -> Optional[Auction]:
        """Get an auction by ID."""
        storage_key = self._get_key("auction", auction_id)
        data = await self._get_data(storage_key, Auction)
        if data:
            return Auction.from_dict(data)
        return None
    
    async def get_user_items(self, public_key: str) -> List[Item]:
        """Get all items owned by a user."""
        # This is a simplified version - in a real app, you'd want to index items by owner
        # For now, we'll just scan all items (not efficient for large datasets)
        # TODO: Implement proper indexing
        items = []
        # This would be replaced with a proper query in a real implementation
        # For now, we'll return an empty list as a placeholder
        return items
    
    async def get_active_auctions(self) -> List[Auction]:
        """Get all active auctions."""
        # Similar to get_user_items, this would query an index in a real implementation
        # For now, return an empty list
        return []
    
    async def _get_data(self, storage_key: str, model_type: Type[T]) -> Optional[dict]:
        """Get data from cache or Arweave."""
        # Check cache first
        if storage_key in self._cache:
            return self._cache[storage_key]
        
        # If not in cache, try to get from Arweave
        # In a real implementation, you would query Arweave here
        # For now, we'll return None as a placeholder
        return None

    async def update_auction_status(self, auction: Auction) -> bool:
        """Update an auction's status based on current time."""
        if not auction.is_active:
            return False
            
        if auction.is_ended() and not auction.settled:
            auction.is_active = False
            auction.winner_public_key = auction.current_bidder
            await self.store(auction)
            return True
            
        return False

    async def transfer_item(self, item_id: str, from_public_key: str, to_public_key: str) -> bool:
        """Transfer an item from one user to another."""
        item = await self.get_item(item_id)
        if not item or item.owner_public_key != from_public_key:
            return False
            
        # Update item ownership
        item.owner_public_key = to_public_key
        
        # Update user inventories
        from_user = await self.get_user(from_public_key)
        to_user = await self.get_user(to_public_key)
        
        if from_user and item_id in from_user.inventory:
            from_user.inventory.remove(item_id)
            await self.store(from_user)
            
        if to_user and item_id not in to_user.inventory:
            to_user.inventory.append(item_id)
            await self.store(to_user)
            
        # Save the item with new owner
        await self.store(item)
        return True

# Global database instance
db = Database()
