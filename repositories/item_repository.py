"""
Item repository for Sapphire Exchange.
Handles auction item data persistence and retrieval.
"""
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from models import Item
from .base_repository import ArweaveRepository


class ItemRepository(ArweaveRepository):
    """Repository for auction item data management."""
    
    def __init__(self, database=None, performance_manager=None, blockchain_manager=None):
        """Initialize item repository."""
        super().__init__(database, performance_manager, blockchain_manager)
        self.entity_type = "item"
    
    async def create(self, item: Item) -> Optional[Item]:
        """Create a new auction item."""
        try:
            # Add timestamps
            self._add_timestamps(item, is_update=False)
            
            # Store on Arweave
            tags = self._create_tags(
                "auction-item",
                item.id,
                SellerID=item.seller_id,
                Category=item.category,
                Status=item.status,
                StartingPrice=item.starting_price_doge,
                AuctionEnd=item.auction_end
            )
            
            tx_id = await self._store_on_arweave(item.to_dict(), tags)
            if tx_id:
                item.arweave_metadata_uri = tx_id
                item.arweave_confirmed = True
                
                # Store in local database
                if self.database:
                    await self.database.store_item(item)
                
                # Cache the item
                cache_key = self._get_cache_key("item", item.id)
                self._cache_entity(cache_key, item)
                
                return item
            
            return None
        except Exception as e:
            print(f"Error creating item: {e}")
            return None
    
    async def get_by_id(self, item_id: str) -> Optional[Item]:
        """Get item by ID."""
        try:
            # Check cache first
            cache_key = self._get_cache_key("item", item_id)
            cached_item = self._get_cached_entity(cache_key)
            if cached_item:
                return cached_item
            
            # Get from database
            if self.database:
                item = await self.database.get_item(item_id)
                if item:
                    # Cache the result
                    self._cache_entity(cache_key, item)
                    return item
            
            return None
        except Exception as e:
            print(f"Error getting item by ID: {e}")
            return None
    
    async def update(self, item: Item) -> bool:
        """Update an existing item."""
        try:
            # Add update timestamp
            self._add_timestamps(item, is_update=True)
            
            # Update on Arweave
            tags = self._create_tags(
                "auction-item-update",
                item.id,
                SellerID=item.seller_id,
                Status=item.status,
                CurrentBid=item.current_bid_doge or "0",
                UpdatedAt=item.updated_at
            )
            
            tx_id = await self._store_on_arweave(item.to_dict(), tags)
            if tx_id:
                # Update database
                if self.database:
                    await self.database.update_item(item)
                
                # Update cache
                cache_key = self._get_cache_key("item", item.id)
                self._cache_entity(cache_key, item)
                
                # Invalidate related caches
                self._invalidate_related_caches(item)
                
                return True
            
            return False
        except Exception as e:
            print(f"Error updating item: {e}")
            return False
    
    async def delete(self, item_id: str) -> bool:
        """Delete an item (soft delete)."""
        try:
            item = await self.get_by_id(item_id)
            if not item:
                return False
            
            # Soft delete - mark as deleted
            item.status = 'deleted'
            item.deleted_at = datetime.now(timezone.utc).isoformat()
            
            # Update in database
            if self.database:
                await self.database.update_item(item)
            
            # Invalidate cache
            cache_key = self._get_cache_key("item", item_id)
            self._invalidate_cache(cache_key)
            
            # Invalidate related caches
            self._invalidate_related_caches(item)
            
            return True
        except Exception as e:
            print(f"Error deleting item: {e}")
            return False
    
    async def list(self, limit: int = 20, offset: int = 0, **filters) -> List[Item]:
        """List items with pagination and filters."""
        try:
            limit, offset = self._validate_pagination(limit, offset)
            
            if self.database:
                return await self.database.get_items(limit, offset, **filters)
            return []
        except Exception as e:
            print(f"Error listing items: {e}")
            return []
    
    async def get_by_status(self, status: str, limit: int = 20, offset: int = 0) -> List[Item]:
        """Get items by status."""
        try:
            limit, offset = self._validate_pagination(limit, offset)
            
            # Check cache for active items (most frequently accessed)
            if status == 'active' and offset == 0:
                cache_key = self._get_cache_key("items_active", f"{limit}_{offset}")
                cached_items = self._get_cached_entity(cache_key)
                if cached_items:
                    return cached_items
            
            if self.database:
                items = await self.database.get_items_by_status(status, limit, offset)
                
                # Cache active items
                if status == 'active' and offset == 0:
                    cache_key = self._get_cache_key("items_active", f"{limit}_{offset}")
                    self._cache_entity(cache_key, items, ttl_seconds=60)  # Short TTL for active items
                
                return items
            return []
        except Exception as e:
            print(f"Error getting items by status: {e}")
            return []
    
    async def get_by_seller(self, seller_id: str, limit: int = 20, offset: int = 0, 
                           status: Optional[str] = None) -> List[Item]:
        """Get items by seller."""
        try:
            limit, offset = self._validate_pagination(limit, offset)
            
            if self.database:
                return await self.database.get_items_by_seller(seller_id, limit, offset, status)
            return []
        except Exception as e:
            print(f"Error getting items by seller: {e}")
            return []
    
    async def get_by_category(self, category: str, limit: int = 20, offset: int = 0) -> List[Item]:
        """Get items by category."""
        try:
            limit, offset = self._validate_pagination(limit, offset)
            
            # Cache popular categories
            cache_key = self._get_cache_key("items_category", f"{category}_{limit}_{offset}")
            cached_items = self._get_cached_entity(cache_key)
            if cached_items:
                return cached_items
            
            if self.database:
                items = await self.database.get_items_by_category(category, limit, offset)
                
                # Cache the results
                self._cache_entity(cache_key, items, ttl_seconds=300)
                
                return items
            return []
        except Exception as e:
            print(f"Error getting items by category: {e}")
            return []
    
    async def search_items(self, query: str, category: Optional[str] = None, 
                          tags: Optional[List[str]] = None, limit: int = 20) -> List[Item]:
        """Search items by query, category, and tags."""
        try:
            limit, _ = self._validate_pagination(limit, 0)
            
            if self.database:
                return await self.database.search_items(query, category, tags, limit)
            return []
        except Exception as e:
            print(f"Error searching items: {e}")
            return []
    
    async def get_ending_soon(self, hours: int = 24, limit: int = 20) -> List[Item]:
        """Get items ending soon."""
        try:
            limit, _ = self._validate_pagination(limit, 0)
            
            # Cache ending soon items
            cache_key = self._get_cache_key("items_ending_soon", f"{hours}_{limit}")
            cached_items = self._get_cached_entity(cache_key)
            if cached_items:
                return cached_items
            
            if self.database:
                items = await self.database.get_items_ending_soon(hours, limit)
                
                # Cache with short TTL since these change frequently
                self._cache_entity(cache_key, items, ttl_seconds=300)
                
                return items
            return []
        except Exception as e:
            print(f"Error getting items ending soon: {e}")
            return []
    
    async def get_popular_items(self, limit: int = 20, time_period: str = '24h') -> List[Item]:
        """Get popular items based on bid activity."""
        try:
            limit, _ = self._validate_pagination(limit, 0)
            
            # Cache popular items
            cache_key = self._get_cache_key("items_popular", f"{time_period}_{limit}")
            cached_items = self._get_cached_entity(cache_key)
            if cached_items:
                return cached_items
            
            if self.database:
                items = await self.database.get_popular_items(limit, time_period)
                
                # Cache with medium TTL
                self._cache_entity(cache_key, items, ttl_seconds=600)
                
                return items
            return []
        except Exception as e:
            print(f"Error getting popular items: {e}")
            return []
    
    async def get_featured_items(self, limit: int = 10) -> List[Item]:
        """Get featured items."""
        try:
            limit, _ = self._validate_pagination(limit, 0)
            
            # Cache featured items
            cache_key = self._get_cache_key("items_featured", str(limit))
            cached_items = self._get_cached_entity(cache_key)
            if cached_items:
                return cached_items
            
            if self.database:
                items = await self.database.get_featured_items(limit)
                
                # Cache with longer TTL since featured items change less frequently
                self._cache_entity(cache_key, items, ttl_seconds=1800)
                
                return items
            return []
        except Exception as e:
            print(f"Error getting featured items: {e}")
            return []
    
    async def get_categories(self) -> List[Dict[str, Any]]:
        """Get all categories with item counts."""
        try:
            # Cache categories
            cache_key = self._get_cache_key("categories", "all")
            cached_categories = self._get_cached_entity(cache_key)
            if cached_categories:
                return cached_categories
            
            if self.database:
                categories = await self.database.get_categories_with_counts()
                
                # Cache with long TTL since categories don't change often
                self._cache_entity(cache_key, categories, ttl_seconds=3600)
                
                return categories
            return []
        except Exception as e:
            print(f"Error getting categories: {e}")
            return []
    
    async def get_item_stats(self, item_id: str) -> Dict[str, Any]:
        """Get item statistics."""
        try:
            # Check cache first
            cache_key = self._get_cache_key("item_stats", item_id)
            cached_stats = self._get_cached_entity(cache_key)
            if cached_stats:
                return cached_stats
            
            item = await self.get_by_id(item_id)
            if not item:
                return {}
            
            stats = {
                'item_id': item_id,
                'title': item.title,
                'status': item.status,
                'starting_price_doge': item.starting_price_doge,
                'current_bid_doge': item.current_bid_doge,
                'created_at': item.created_at,
                'auction_end': item.auction_end,
                'view_count': getattr(item, 'view_count', 0),
                'watch_count': getattr(item, 'watch_count', 0)
            }
            
            # Get additional stats from database
            if self.database:
                bid_count = await self.database.count_bids_by_item(item_id)
                unique_bidders = await self.database.count_unique_bidders_by_item(item_id)
                
                stats.update({
                    'bid_count': bid_count,
                    'unique_bidders': unique_bidders,
                    'has_bids': bid_count > 0
                })
            
            # Cache stats for 5 minutes
            self._cache_entity(cache_key, stats, ttl_seconds=300)
            
            return stats
        except Exception as e:
            print(f"Error getting item stats: {e}")
            return {}
    
    async def increment_view_count(self, item_id: str) -> bool:
        """Increment item view count."""
        try:
            item = await self.get_by_id(item_id)
            if not item:
                return False
            
            # Increment view count
            current_views = getattr(item, 'view_count', 0)
            item.view_count = current_views + 1
            
            # Update in database (don't update Arweave for view counts)
            if self.database:
                await self.database.update_item_views(item_id, item.view_count)
            
            # Update cache
            cache_key = self._get_cache_key("item", item_id)
            self._cache_entity(cache_key, item)
            
            # Invalidate stats cache
            stats_cache_key = self._get_cache_key("item_stats", item_id)
            self._invalidate_cache(stats_cache_key)
            
            return True
        except Exception as e:
            print(f"Error incrementing view count: {e}")
            return False
    
    def _invalidate_related_caches(self, item: Item):
        """Invalidate caches related to an item."""
        try:
            # Invalidate category cache
            if item.category:
                category_pattern = f"items_category_{item.category}_*"
                # Note: This would need implementation in performance manager
                
            # Invalidate seller cache
            seller_pattern = f"items_seller_{item.seller_id}_*"
            
            # Invalidate status cache
            status_pattern = f"items_{item.status}_*"
            
            # Invalidate popular/featured caches
            self._invalidate_cache(self._get_cache_key("items_popular", "*"))
            self._invalidate_cache(self._get_cache_key("items_featured", "*"))
            self._invalidate_cache(self._get_cache_key("items_ending_soon", "*"))
            
        except Exception as e:
            print(f"Error invalidating related caches: {e}")
    
    async def batch_create_items(self, items: List[Item]) -> List[Item]:
        """Create multiple items in batch."""
        try:
            operations = [self.create(item) for item in items]
            results = await self._batch_operation(operations)
            return self._filter_exceptions(results)
        except Exception as e:
            print(f"Error in batch create items: {e}")
            return []
    
    async def batch_update_items(self, items: List[Item]) -> List[bool]:
        """Update multiple items in batch."""
        try:
            operations = [self.update(item) for item in items]
            results = await self._batch_operation(operations)
            return self._filter_exceptions(results)
        except Exception as e:
            print(f"Error in batch update items: {e}")
            return []