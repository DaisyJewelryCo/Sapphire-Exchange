"""
Enhanced Database module for Sapphire Exchange using Arweave for decentralized storage.
Supports multi-currency data, performance optimization, and data integrity verification.
"""
import json
import hashlib
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Type, TypeVar, Generic, Any, Tuple
from dataclasses import asdict
from models.models import User, Item, Auction, Bid
from blockchain.arweave_client import ArweaveClient
from config.blockchain_config import blockchain_config
from security.performance_manager import PerformanceManager
from security.security_manager import SecurityManager, EncryptionManager

T = TypeVar('T', User, Item, Auction, Bid)

class EnhancedDatabase:
    """Enhanced database class with performance optimization and data integrity."""
    
    def __init__(self, arweave_client: Optional[ArweaveClient] = None,
                 performance_manager: Optional[PerformanceManager] = None,
                 security_manager: Optional[SecurityManager] = None):
        """Initialize the enhanced database."""
        self.arweave = arweave_client or ArweaveClient(blockchain_config.get_arweave_config())
        self.performance_manager = performance_manager or PerformanceManager()
        self.security_manager = security_manager or SecurityManager()
        self.encryption_manager = EncryptionManager()
        
        # Legacy cache for backward compatibility
        self._cache: Dict[str, dict] = {}
        
        # Enhanced indexing system
        self.indexes = {
            'users_by_address': {},  # nano_address -> user_id
            'users_by_username': {},  # username -> user_id
            'items_by_seller': {},  # seller_id -> [item_ids]
            'items_by_status': {},  # status -> [item_ids]
            'items_by_category': {},  # category -> [item_ids]
            'bids_by_item': {},  # item_id -> [bid_ids]
            'bids_by_bidder': {},  # bidder_id -> [bid_ids]
        }
        
        # Data integrity tracking
        self.data_hashes = {}  # object_id -> hash
        self.arweave_confirmations = {}  # object_id -> confirmation_status
        
        # Batch operations queue
        self.batch_queue = []
        self.batch_size = 50  # From performance_parameters
        
    def _get_key(self, prefix: str, key: str) -> str:
        """Generate a storage key with prefix."""
        return f"{prefix}:{key}"
    
    def _calculate_data_hash(self, data: dict) -> str:
        """Calculate SHA-256 hash of data for integrity verification."""
        # Remove volatile fields before hashing
        hash_data = data.copy()
        volatile_fields = ['last_login', 'session_timeout', 'metadata']
        for field in volatile_fields:
            hash_data.pop(field, None)
        
        data_str = json.dumps(hash_data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def _update_indexes(self, obj: T, operation: str = 'add'):
        """Update indexes when objects are added/removed."""
        if isinstance(obj, User):
            if operation == 'add':
                if obj.nano_address:
                    self.indexes['users_by_address'][obj.nano_address] = obj.id
                if obj.username:
                    self.indexes['users_by_username'][obj.username] = obj.id
            elif operation == 'remove':
                # Remove from indexes
                for addr, user_id in list(self.indexes['users_by_address'].items()):
                    if user_id == obj.id:
                        del self.indexes['users_by_address'][addr]
                for username, user_id in list(self.indexes['users_by_username'].items()):
                    if user_id == obj.id:
                        del self.indexes['users_by_username'][username]
        
        elif isinstance(obj, Item):
            if operation == 'add':
                # Index by seller
                if obj.seller_id not in self.indexes['items_by_seller']:
                    self.indexes['items_by_seller'][obj.seller_id] = []
                self.indexes['items_by_seller'][obj.seller_id].append(obj.id)
                
                # Index by status
                if obj.status not in self.indexes['items_by_status']:
                    self.indexes['items_by_status'][obj.status] = []
                self.indexes['items_by_status'][obj.status].append(obj.id)
                
                # Index by category
                if obj.category:
                    if obj.category not in self.indexes['items_by_category']:
                        self.indexes['items_by_category'][obj.category] = []
                    self.indexes['items_by_category'][obj.category].append(obj.id)
            
            elif operation == 'remove':
                # Remove from all indexes
                for seller_items in self.indexes['items_by_seller'].values():
                    if obj.id in seller_items:
                        seller_items.remove(obj.id)
                for status_items in self.indexes['items_by_status'].values():
                    if obj.id in status_items:
                        status_items.remove(obj.id)
                for category_items in self.indexes['items_by_category'].values():
                    if obj.id in category_items:
                        category_items.remove(obj.id)
        
        elif isinstance(obj, Bid):
            if operation == 'add':
                # Index by item
                if obj.item_id not in self.indexes['bids_by_item']:
                    self.indexes['bids_by_item'][obj.item_id] = []
                self.indexes['bids_by_item'][obj.item_id].append(obj.id)
                
                # Index by bidder
                if obj.bidder_id not in self.indexes['bids_by_bidder']:
                    self.indexes['bids_by_bidder'][obj.bidder_id] = []
                self.indexes['bids_by_bidder'][obj.bidder_id].append(obj.id)
            
            elif operation == 'remove':
                # Remove from indexes
                for item_bids in self.indexes['bids_by_item'].values():
                    if obj.id in item_bids:
                        item_bids.remove(obj.id)
                for bidder_bids in self.indexes['bids_by_bidder'].values():
                    if obj.id in bidder_bids:
                        bidder_bids.remove(obj.id)
    
    async def store(self, obj: T, encrypt_sensitive: bool = False) -> str:
        """Enhanced store method with data integrity and encryption."""
        # Determine object type and key
        if isinstance(obj, User):
            prefix = "user"
            key = obj.id or obj.public_key  # Use UUID if available
        elif isinstance(obj, Item):
            prefix = "item"
            key = obj.id or obj.item_id  # Use UUID if available
        elif isinstance(obj, Auction):
            prefix = "auction"
            key = obj.auction_id
        elif isinstance(obj, Bid):
            prefix = "bid"
            key = obj.id
        else:
            raise ValueError(f"Unsupported object type: {type(obj)}")
        
        # Convert to dictionary
        data = obj.to_dict() if hasattr(obj, 'to_dict') else asdict(obj)
        
        # Calculate and store data hash for integrity
        data_hash = self._calculate_data_hash(data)
        data['data_hash'] = data_hash
        self.data_hashes[key] = data_hash
        
        # Add timestamp
        data['stored_at'] = datetime.now(timezone.utc).isoformat()
        
        # Encrypt sensitive data if requested
        if encrypt_sensitive and isinstance(obj, User):
            sensitive_fields = ['doge_private_key_encrypted', 'password_hash', 'password_salt']
            encryption_key = self.encryption_manager.generate_encryption_key()
            
            for field in sensitive_fields:
                if field in data and data[field]:
                    encrypted_data = self.encryption_manager.encrypt_sensitive_data(
                        str(data[field]), encryption_key
                    )
                    data[f"{field}_encrypted"] = encrypted_data
                    del data[field]  # Remove plain text
        
        # Store in cache first
        storage_key = self._get_key(prefix, key)
        self._cache[storage_key] = data
        
        # Update indexes
        self._update_indexes(obj, 'add')
        
        # Add to batch queue for Arweave storage
        self.batch_queue.append({
            'key': storage_key,
            'data': data,
            'timestamp': datetime.now(timezone.utc)
        })
        
        # Process batch if queue is full
        if len(self.batch_queue) >= self.batch_size:
            await self._process_batch()
        
        return storage_key
    
    async def _process_batch(self):
        """Process batch operations to Arweave."""
        if not self.batch_queue:
            return
        
        try:
            # Group operations by type for efficient processing
            batch_data = {
                'operations': self.batch_queue.copy(),
                'batch_id': hashlib.sha256(
                    f"{datetime.now(timezone.utc).isoformat()}".encode()
                ).hexdigest()[:16],
                'processed_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Store batch to Arweave
            batch_json = json.dumps(batch_data)
            # TODO: Implement actual Arweave storage
            # arweave_tx_id = await self.arweave.store_data(batch_json)
            
            # Mark operations as confirmed (mock for now)
            for operation in self.batch_queue:
                self.arweave_confirmations[operation['key']] = {
                    'status': 'confirmed',
                    'tx_id': f"mock_tx_{operation['key'][-8:]}",
                    'confirmed_at': datetime.now(timezone.utc).isoformat()
                }
            
            # Clear batch queue
            self.batch_queue.clear()
            
        except Exception as e:
            print(f"Error processing batch: {e}")
            # Keep items in queue for retry
    
    async def get(self, obj_type: Type[T], key: str) -> Optional[T]:
        """Enhanced get method with caching and integrity verification."""
        if obj_type == User:
            prefix = "user"
        elif obj_type == Item:
            prefix = "item"
        elif obj_type == Auction:
            prefix = "auction"
        elif obj_type == Bid:
            prefix = "bid"
        else:
            raise ValueError(f"Unsupported object type: {obj_type}")
        
        storage_key = self._get_key(prefix, key)
        
        # Check cache first
        cached_data = self.performance_manager.get_cached_data(storage_key)
        if cached_data:
            return self._deserialize_object(obj_type, cached_data)
        
        # Check local cache
        if storage_key in self._cache:
            data = self._cache[storage_key]
            
            # Verify data integrity
            if 'data_hash' in data:
                stored_hash = data['data_hash']
                calculated_hash = self._calculate_data_hash(data)
                if stored_hash != calculated_hash:
                    print(f"Data integrity check failed for {storage_key}")
                    # Could implement recovery logic here
            
            # Cache the result
            self.performance_manager.set_cached_data(storage_key, data)
            
            return self._deserialize_object(obj_type, data)
        
        # TODO: Implement Arweave retrieval
        # data = await self.arweave.get_data(storage_key)
        
        return None
    
    def _deserialize_object(self, obj_type: Type[T], data: dict) -> T:
        """Deserialize dictionary data to object."""
        if obj_type == User:
            return User.from_dict(data)
        elif obj_type == Item:
            return Item.from_dict(data)
        elif obj_type == Auction:
            return Auction.from_dict(data) if hasattr(Auction, 'from_dict') else obj_type(**data)
        elif obj_type == Bid:
            return Bid.from_dict(data)
        else:
            raise ValueError(f"Unsupported object type: {obj_type}")
    
    async def query_users_by_address(self, nano_address: str) -> Optional[User]:
        """Query user by Nano address using index."""
        user_id = self.indexes['users_by_address'].get(nano_address)
        if user_id:
            return await self.get(User, user_id)
        return None
    
    async def query_users_by_username(self, username: str) -> Optional[User]:
        """Query user by username using index."""
        user_id = self.indexes['users_by_username'].get(username)
        if user_id:
            return await self.get(User, user_id)
        return None
    
    async def query_items_by_seller(self, seller_id: str) -> List[Item]:
        """Query items by seller ID using index."""
        item_ids = self.indexes['items_by_seller'].get(seller_id, [])
        items = []
        for item_id in item_ids:
            item = await self.get(Item, item_id)
            if item:
                items.append(item)
        return items
    
    async def query_items_by_status(self, status: str) -> List[Item]:
        """Query items by status using index."""
        item_ids = self.indexes['items_by_status'].get(status, [])
        items = []
        for item_id in item_ids:
            item = await self.get(Item, item_id)
            if item:
                items.append(item)
        return items
    
    async def query_items_by_category(self, category: str) -> List[Item]:
        """Query items by category using index."""
        item_ids = self.indexes['items_by_category'].get(category, [])
        items = []
        for item_id in item_ids:
            item = await self.get(Item, item_id)
            if item:
                items.append(item)
        return items
    
    async def query_bids_by_item(self, item_id: str) -> List[Bid]:
        """Query bids by item ID using index."""
        bid_ids = self.indexes['bids_by_item'].get(item_id, [])
        bids = []
        for bid_id in bid_ids:
            bid = await self.get(Bid, bid_id)
            if bid:
                bids.append(bid)
        return bids
    
    async def query_bids_by_bidder(self, bidder_id: str) -> List[Bid]:
        """Query bids by bidder ID using index."""
        bid_ids = self.indexes['bids_by_bidder'].get(bidder_id, [])
        bids = []
        for bid_id in bid_ids:
            bid = await self.get(Bid, bid_id)
            if bid:
                bids.append(bid)
        return bids
    
    async def search_items(self, query: str, filters: Dict = None) -> List[Item]:
        """Advanced item search with filters."""
        all_items = []
        
        # Get all items from all status indexes
        for status_items in self.indexes['items_by_status'].values():
            for item_id in status_items:
                item = await self.get(Item, item_id)
                if item:
                    all_items.append(item)
        
        # Apply text search
        if query:
            query_lower = query.lower()
            filtered_items = []
            for item in all_items:
                if (query_lower in (item.title or item.name or "").lower() or
                    query_lower in (item.description or "").lower() or
                    any(query_lower in tag.lower() for tag in item.tags)):
                    filtered_items.append(item)
            all_items = filtered_items
        
        # Apply filters
        if filters:
            if 'status' in filters:
                all_items = [item for item in all_items if item.status == filters['status']]
            
            if 'category' in filters:
                all_items = [item for item in all_items if item.category == filters['category']]
            
            if 'min_price' in filters:
                min_price = float(filters['min_price'])
                all_items = [item for item in all_items 
                           if float(item.starting_price_doge or item.starting_price or 0) >= min_price]
            
            if 'max_price' in filters:
                max_price = float(filters['max_price'])
                all_items = [item for item in all_items 
                           if float(item.starting_price_doge or item.starting_price or 0) <= max_price]
        
        return all_items
    
    async def update_item_status(self, item_id: str, new_status: str) -> bool:
        """Update item status and maintain indexes."""
        item = await self.get(Item, item_id)
        if not item:
            return False
        
        old_status = item.status
        item.status = new_status
        
        # Update indexes
        if old_status in self.indexes['items_by_status']:
            if item_id in self.indexes['items_by_status'][old_status]:
                self.indexes['items_by_status'][old_status].remove(item_id)
        
        if new_status not in self.indexes['items_by_status']:
            self.indexes['items_by_status'][new_status] = []
        self.indexes['items_by_status'][new_status].append(item_id)
        
        # Store updated item
        await self.store(item)
        return True
    
    def get_database_stats(self) -> Dict:
        """Get database statistics."""
        return {
            'cache_size': len(self._cache),
            'batch_queue_size': len(self.batch_queue),
            'indexes': {
                'users_by_address': len(self.indexes['users_by_address']),
                'users_by_username': len(self.indexes['users_by_username']),
                'items_by_seller': len(self.indexes['items_by_seller']),
                'items_by_status': len(self.indexes['items_by_status']),
                'items_by_category': len(self.indexes['items_by_category']),
                'bids_by_item': len(self.indexes['bids_by_item']),
                'bids_by_bidder': len(self.indexes['bids_by_bidder']),
            },
            'data_integrity': {
                'tracked_hashes': len(self.data_hashes),
                'arweave_confirmations': len(self.arweave_confirmations)
            },
            'performance_stats': self.performance_manager.get_performance_stats()
        }


# Legacy Database class for backward compatibility
class Database(EnhancedDatabase):
    """Legacy database class for backward compatibility."""
    
    def __init__(self, arweave_client: Optional[ArweaveClient] = None):
        super().__init__(arweave_client)
    
    async def store(self, obj: T) -> str:
        """Legacy store method."""
        return await super().store(obj, encrypt_sensitive=False)
    
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
