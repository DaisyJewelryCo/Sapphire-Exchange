"""
Database Adapter for Sapphire Exchange.
Bridges the legacy database interface with the new repository pattern.
"""
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from models.models import User, Item, Bid
from repositories import UserRepository, ItemRepository, BidRepository
from repositories.database import EnhancedDatabase
from blockchain.blockchain_manager import blockchain_manager
from security.performance_manager import PerformanceManager


class DatabaseAdapter:
    """
    Adapter that provides a unified interface between legacy database code
    and the new repository pattern.
    """
    
    def __init__(self, performance_manager: PerformanceManager = None):
        """Initialize the database adapter."""
        self.performance_manager = performance_manager or PerformanceManager()
        
        # Initialize repositories
        self.user_repo = UserRepository(
            database=self,
            performance_manager=self.performance_manager,
            blockchain_manager=blockchain_manager
        )
        
        self.item_repo = ItemRepository(
            database=self,
            performance_manager=self.performance_manager,
            blockchain_manager=blockchain_manager
        )
        
        self.bid_repo = BidRepository(
            database=self,
            performance_manager=self.performance_manager,
            blockchain_manager=blockchain_manager
        )
        
        # Legacy database for backward compatibility
        self.legacy_db = EnhancedDatabase(
            performance_manager=self.performance_manager
        )
        
        # In-memory storage for mock mode
        self._users = {}
        self._items = {}
        self._bids = {}
        
        # Indexes for efficient queries
        self._user_username_index = {}
        self._user_email_index = {}
        self._items_by_seller_index = {}
        self._items_by_status_index = {}
        self._items_by_category_index = {}
        self._bids_by_item_index = {}
        self._bids_by_bidder_index = {}
    
    # User operations
    async def store_user(self, user: User) -> bool:
        """Store a user."""
        try:
            self._users[user.id] = user
            self._user_username_index[user.username.lower()] = user.id
            self._user_email_index[user.email.lower()] = user.id
            return True
        except Exception as e:
            print(f"Error storing user: {e}")
            return False
    
    async def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self._users.get(user_id)
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        user_id = self._user_username_index.get(username.lower())
        return self._users.get(user_id) if user_id else None
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        user_id = self._user_email_index.get(email.lower())
        return self._users.get(user_id) if user_id else None
    
    async def update_user(self, user: User) -> bool:
        """Update a user."""
        try:
            if user.id in self._users:
                self._users[user.id] = user
                return True
            return False
        except Exception as e:
            print(f"Error updating user: {e}")
            return False
    
    async def get_users(self, limit: int = 20, offset: int = 0, **filters) -> List[User]:
        """Get users with pagination."""
        try:
            users = list(self._users.values())
            
            # Apply filters
            if filters.get('is_active') is not None:
                users = [u for u in users if u.is_active == filters['is_active']]
            
            # Sort by created_at
            users.sort(key=lambda u: u.created_at or '', reverse=True)
            
            # Apply pagination
            return users[offset:offset + limit]
        except Exception as e:
            print(f"Error getting users: {e}")
            return []
    
    async def search_users(self, query: str, limit: int = 20) -> List[User]:
        """Search users by username or bio."""
        try:
            query_lower = query.lower()
            matching_users = []
            
            for user in self._users.values():
                if (query_lower in user.username.lower() or 
                    (user.bio and query_lower in user.bio.lower())):
                    matching_users.append(user)
            
            return matching_users[:limit]
        except Exception as e:
            print(f"Error searching users: {e}")
            return []
    
    async def get_top_users(self, limit: int = 10, metric: str = 'reputation') -> List[User]:
        """Get top users by metric."""
        try:
            users = list(self._users.values())
            
            if metric == 'reputation':
                users.sort(key=lambda u: u.reputation_score, reverse=True)
            elif metric == 'sales':
                users.sort(key=lambda u: u.total_sales, reverse=True)
            elif metric == 'purchases':
                users.sort(key=lambda u: u.total_purchases, reverse=True)
            
            return users[:limit]
        except Exception as e:
            print(f"Error getting top users: {e}")
            return []
    
    # Item operations
    async def store_item(self, item: Item) -> bool:
        """Store an item."""
        try:
            is_new = item.id not in self._items
            self._items[item.id] = item
            
            # Update seller index (only add if new)
            if is_new:
                if item.seller_id not in self._items_by_seller_index:
                    self._items_by_seller_index[item.seller_id] = []
                self._items_by_seller_index[item.seller_id].append(item.id)
            
            # Update status index
            if is_new:
                if item.status not in self._items_by_status_index:
                    self._items_by_status_index[item.status] = []
                self._items_by_status_index[item.status].append(item.id)
            
            # Update category index (only add if new)
            if is_new and item.category:
                if item.category not in self._items_by_category_index:
                    self._items_by_category_index[item.category] = []
                self._items_by_category_index[item.category].append(item.id)
            
            return True
        except Exception as e:
            print(f"Error storing item: {e}")
            return False
    
    async def get_item(self, item_id: str) -> Optional[Item]:
        """Get item by ID."""
        return self._items.get(item_id)
    
    async def update_item(self, item: Item) -> bool:
        """Update an item."""
        try:
            if item.id in self._items:
                old_item = self._items[item.id]
                self._items[item.id] = item
                
                # Update status index if changed
                if old_item.status != item.status:
                    # Remove from old status
                    if old_item.status in self._items_by_status_index:
                        if item.id in self._items_by_status_index[old_item.status]:
                            self._items_by_status_index[old_item.status].remove(item.id)
                    
                    # Add to new status
                    if item.status not in self._items_by_status_index:
                        self._items_by_status_index[item.status] = []
                    self._items_by_status_index[item.status].append(item.id)
                
                return True
            return False
        except Exception as e:
            print(f"Error updating item: {e}")
            return False
    
    async def get_items(self, limit: int = 20, offset: int = 0, **filters) -> List[Item]:
        """Get items with pagination and filters."""
        try:
            items = list(self._items.values())
            
            # Apply filters
            if filters.get('status'):
                items = [i for i in items if i.status == filters['status']]
            if filters.get('category'):
                items = [i for i in items if i.category == filters['category']]
            if filters.get('seller_id'):
                items = [i for i in items if i.seller_id == filters['seller_id']]
            
            # Sort by created_at
            items.sort(key=lambda i: i.created_at or '', reverse=True)
            
            # Apply pagination
            return items[offset:offset + limit]
        except Exception as e:
            print(f"Error getting items: {e}")
            return []
    
    async def get_items_by_status(self, status: str, limit: int = 20, offset: int = 0) -> List[Item]:
        """Get items by status."""
        try:
            item_ids = self._items_by_status_index.get(status, [])
            items = [self._items[item_id] for item_id in item_ids if item_id in self._items]
            
            # Sort by created_at
            items.sort(key=lambda i: i.created_at or '', reverse=True)
            
            return items[offset:offset + limit]
        except Exception as e:
            print(f"Error getting items by status: {e}")
            return []
    
    async def get_items_by_seller(self, seller_id: str, limit: int = 20, offset: int = 0, 
                                 status: Optional[str] = None) -> List[Item]:
        """Get items by seller."""
        try:
            item_ids = self._items_by_seller_index.get(seller_id, [])
            items = [self._items[item_id] for item_id in item_ids if item_id in self._items]
            
            # Filter by status if provided
            if status:
                items = [i for i in items if i.status == status]
            
            # Sort by created_at
            items.sort(key=lambda i: i.created_at or '', reverse=True)
            
            return items[offset:offset + limit]
        except Exception as e:
            print(f"Error getting items by seller: {e}")
            return []
    
    async def get_items_by_category(self, category: str, limit: int = 20, offset: int = 0) -> List[Item]:
        """Get items by category."""
        try:
            item_ids = self._items_by_category_index.get(category, [])
            items = [self._items[item_id] for item_id in item_ids if item_id in self._items]
            
            # Sort by created_at
            items.sort(key=lambda i: i.created_at or '', reverse=True)
            
            return items[offset:offset + limit]
        except Exception as e:
            print(f"Error getting items by category: {e}")
            return []
    
    async def search_items(self, query: str, category: Optional[str] = None, 
                          tags: Optional[List[str]] = None, limit: int = 20) -> List[Item]:
        """Search items."""
        try:
            query_lower = query.lower()
            matching_items = []
            
            for item in self._items.values():
                # Search in title and description
                if (query_lower in item.title.lower() or 
                    query_lower in item.description.lower()):
                    
                    # Filter by category if provided
                    if category and item.category != category:
                        continue
                    
                    # Filter by tags if provided
                    if tags and not any(tag in item.tags for tag in tags):
                        continue
                    
                    matching_items.append(item)
            
            # Sort by relevance (simplified)
            matching_items.sort(key=lambda i: i.created_at or '', reverse=True)
            
            return matching_items[:limit]
        except Exception as e:
            print(f"Error searching items: {e}")
            return []
    
    async def count_items_by_seller(self, seller_id: str, status: Optional[str] = None) -> int:
        """Count items by seller."""
        try:
            item_ids = self._items_by_seller_index.get(seller_id, [])
            items = [self._items[item_id] for item_id in item_ids if item_id in self._items]
            
            if status:
                items = [i for i in items if i.status == status]
            
            return len(items)
        except Exception as e:
            print(f"Error counting items by seller: {e}")
            return 0
    
    # Bid operations
    async def store_bid(self, bid: Bid) -> bool:
        """Store a bid."""
        try:
            self._bids[bid.id] = bid
            
            # Update indexes
            if bid.item_id not in self._bids_by_item_index:
                self._bids_by_item_index[bid.item_id] = []
            self._bids_by_item_index[bid.item_id].append(bid.id)
            
            if bid.bidder_id not in self._bids_by_bidder_index:
                self._bids_by_bidder_index[bid.bidder_id] = []
            self._bids_by_bidder_index[bid.bidder_id].append(bid.id)
            
            return True
        except Exception as e:
            print(f"Error storing bid: {e}")
            return False
    
    async def get_bid(self, bid_id: str) -> Optional[Bid]:
        """Get bid by ID."""
        return self._bids.get(bid_id)
    
    async def update_bid(self, bid: Bid) -> bool:
        """Update a bid."""
        try:
            if bid.id in self._bids:
                self._bids[bid.id] = bid
                return True
            return False
        except Exception as e:
            print(f"Error updating bid: {e}")
            return False
    
    async def get_bids_by_item(self, item_id: str, limit: int = 50, offset: int = 0) -> List[Bid]:
        """Get bids for an item."""
        try:
            bid_ids = self._bids_by_item_index.get(item_id, [])
            bids = [self._bids[bid_id] for bid_id in bid_ids if bid_id in self._bids]
            
            # Sort by amount (highest first)
            bids.sort(key=lambda b: float(b.amount_doge), reverse=True)
            
            return bids[offset:offset + limit]
        except Exception as e:
            print(f"Error getting bids by item: {e}")
            return []
    
    async def get_bids_by_bidder(self, bidder_id: str, limit: int = 20, offset: int = 0, 
                                status: Optional[str] = None) -> List[Bid]:
        """Get bids by bidder."""
        try:
            bid_ids = self._bids_by_bidder_index.get(bidder_id, [])
            bids = [self._bids[bid_id] for bid_id in bid_ids if bid_id in self._bids]
            
            # Filter by status if provided
            if status:
                bids = [b for b in bids if b.status == status]
            
            # Sort by created_at
            bids.sort(key=lambda b: b.created_at or '', reverse=True)
            
            return bids[offset:offset + limit]
        except Exception as e:
            print(f"Error getting bids by bidder: {e}")
            return []
    
    async def count_bids_by_item(self, item_id: str) -> int:
        """Count bids for an item."""
        try:
            bid_ids = self._bids_by_item_index.get(item_id, [])
            return len([bid_id for bid_id in bid_ids if bid_id in self._bids])
        except Exception as e:
            print(f"Error counting bids by item: {e}")
            return 0
    
    async def count_unique_bidders_by_item(self, item_id: str) -> int:
        """Count unique bidders for an item."""
        try:
            bid_ids = self._bids_by_item_index.get(item_id, [])
            bids = [self._bids[bid_id] for bid_id in bid_ids if bid_id in self._bids]
            unique_bidders = set(bid.bidder_id for bid in bids)
            return len(unique_bidders)
        except Exception as e:
            print(f"Error counting unique bidders: {e}")
            return 0
    
    async def get_highest_bid_by_item(self, item_id: str) -> Optional[Bid]:
        """Get highest bid for an item."""
        try:
            bid_ids = self._bids_by_item_index.get(item_id, [])
            bids = [self._bids[bid_id] for bid_id in bid_ids if bid_id in self._bids]
            
            if not bids:
                return None
            
            # Return highest bid
            return max(bids, key=lambda b: float(b.amount_doge))
        except Exception as e:
            print(f"Error getting highest bid: {e}")
            return None
    
    # Repository access methods
    def get_user_repository(self) -> UserRepository:
        """Get user repository."""
        return self.user_repo
    
    def get_item_repository(self) -> ItemRepository:
        """Get item repository."""
        return self.item_repo
    
    def get_bid_repository(self) -> BidRepository:
        """Get bid repository."""
        return self.bid_repo
    
    async def health_check(self) -> Dict[str, Any]:
        """Check database health."""
        return {
            'status': 'healthy',
            'users_count': len(self._users),
            'items_count': len(self._items),
            'bids_count': len(self._bids),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }


# Global database adapter instance
database_adapter = DatabaseAdapter()