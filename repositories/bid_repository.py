"""
Bid repository for Sapphire Exchange.
Handles bid data persistence and retrieval.
"""
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from models import Bid
from .base_repository import ArweaveRepository


class BidRepository(ArweaveRepository):
    """Repository for bid data management."""
    
    def __init__(self, database=None, performance_manager=None, blockchain_manager=None):
        """Initialize bid repository."""
        super().__init__(database, performance_manager, blockchain_manager)
        self.entity_type = "bid"
    
    async def create(self, bid: Bid) -> Optional[Bid]:
        """Create a new bid."""
        try:
            # Add timestamps
            self._add_timestamps(bid, is_update=False)
            
            # Store on Arweave
            tags = self._create_tags(
                "bid",
                bid.id,
                ItemID=bid.item_id,
                BidderID=bid.bidder_id,
                AmountDOGE=bid.amount_doge,
                Status=bid.status,
                Currency=getattr(bid, 'currency', 'DOGE')
            )
            
            tx_id = await self._store_on_arweave(bid.to_dict(), tags)
            if tx_id:
                bid.arweave_tx_id = tx_id
                
                # Store in local database
                if self.database:
                    await self.database.store_bid(bid)
                
                # Cache the bid
                cache_key = self._get_cache_key("bid", bid.id)
                self._cache_entity(cache_key, bid)
                
                return bid
            
            return None
        except Exception as e:
            print(f"Error creating bid: {e}")
            return None
    
    async def get_by_id(self, bid_id: str) -> Optional[Bid]:
        """Get bid by ID."""
        try:
            # Check cache first
            cache_key = self._get_cache_key("bid", bid_id)
            cached_bid = self._get_cached_entity(cache_key)
            if cached_bid:
                return cached_bid
            
            # Get from database
            if self.database:
                bid = await self.database.get_bid(bid_id)
                if bid:
                    # Cache the result
                    self._cache_entity(cache_key, bid)
                    return bid
            
            return None
        except Exception as e:
            print(f"Error getting bid by ID: {e}")
            return None
    
    async def update(self, bid: Bid) -> bool:
        """Update an existing bid."""
        try:
            # Add update timestamp
            self._add_timestamps(bid, is_update=True)
            
            # Update on Arweave
            tags = self._create_tags(
                "bid-update",
                bid.id,
                ItemID=bid.item_id,
                Status=bid.status,
                UpdatedAt=bid.updated_at
            )
            
            tx_id = await self._store_on_arweave(bid.to_dict(), tags)
            if tx_id:
                # Update database
                if self.database:
                    await self.database.update_bid(bid)
                
                # Update cache
                cache_key = self._get_cache_key("bid", bid.id)
                self._cache_entity(cache_key, bid)
                
                # Invalidate related caches
                self._invalidate_related_caches(bid)
                
                return True
            
            return False
        except Exception as e:
            print(f"Error updating bid: {e}")
            return False
    
    async def delete(self, bid_id: str) -> bool:
        """Delete a bid (soft delete)."""
        try:
            bid = await self.get_by_id(bid_id)
            if not bid:
                return False
            
            # Soft delete - mark as cancelled
            bid.status = 'cancelled'
            bid.deleted_at = datetime.now(timezone.utc).isoformat()
            
            # Update in database
            if self.database:
                await self.database.update_bid(bid)
            
            # Invalidate cache
            cache_key = self._get_cache_key("bid", bid_id)
            self._invalidate_cache(cache_key)
            
            # Invalidate related caches
            self._invalidate_related_caches(bid)
            
            return True
        except Exception as e:
            print(f"Error deleting bid: {e}")
            return False
    
    async def list(self, limit: int = 20, offset: int = 0, **filters) -> List[Bid]:
        """List bids with pagination and filters."""
        try:
            limit, offset = self._validate_pagination(limit, offset)
            
            if self.database:
                return await self.database.get_bids(limit, offset, **filters)
            return []
        except Exception as e:
            print(f"Error listing bids: {e}")
            return []
    
    async def get_by_item(self, item_id: str, limit: int = 50, offset: int = 0) -> List[Bid]:
        """Get bids for a specific item."""
        try:
            limit, offset = self._validate_pagination(limit, offset)
            
            # Cache bids for active items
            if offset == 0:
                cache_key = self._get_cache_key("bids_item", f"{item_id}_{limit}")
                cached_bids = self._get_cached_entity(cache_key)
                if cached_bids:
                    return cached_bids
            
            if self.database:
                bids = await self.database.get_bids_by_item(item_id, limit, offset)
                
                # Cache the results
                if offset == 0:
                    cache_key = self._get_cache_key("bids_item", f"{item_id}_{limit}")
                    self._cache_entity(cache_key, bids, ttl_seconds=60)  # Short TTL for active bidding
                
                return bids
            return []
        except Exception as e:
            print(f"Error getting bids by item: {e}")
            return []
    
    async def get_by_bidder(self, bidder_id: str, limit: int = 20, offset: int = 0, 
                           status: Optional[str] = None) -> List[Bid]:
        """Get bids by a specific bidder."""
        try:
            limit, offset = self._validate_pagination(limit, offset)
            
            if self.database:
                return await self.database.get_bids_by_bidder(bidder_id, limit, offset, status)
            return []
        except Exception as e:
            print(f"Error getting bids by bidder: {e}")
            return []
    
    async def get_by_status(self, status: str, limit: int = 20, offset: int = 0) -> List[Bid]:
        """Get bids by status."""
        try:
            limit, offset = self._validate_pagination(limit, offset)
            
            if self.database:
                return await self.database.get_bids_by_status(status, limit, offset)
            return []
        except Exception as e:
            print(f"Error getting bids by status: {e}")
            return []
    
    async def get_highest_bid(self, item_id: str) -> Optional[Bid]:
        """Get the highest bid for an item."""
        try:
            # Check cache first
            cache_key = self._get_cache_key("highest_bid", item_id)
            cached_bid = self._get_cached_entity(cache_key)
            if cached_bid:
                return cached_bid
            
            if self.database:
                bid = await self.database.get_highest_bid_by_item(item_id)
                if bid:
                    # Cache with short TTL since this changes frequently
                    self._cache_entity(cache_key, bid, ttl_seconds=30)
                return bid
            return None
        except Exception as e:
            print(f"Error getting highest bid: {e}")
            return None
    
    async def get_bid_history(self, item_id: str, limit: int = 20) -> List[Bid]:
        """Get bid history for an item (ordered by amount descending)."""
        try:
            limit, _ = self._validate_pagination(limit, 0)
            
            # Cache bid history
            cache_key = self._get_cache_key("bid_history", f"{item_id}_{limit}")
            cached_history = self._get_cached_entity(cache_key)
            if cached_history:
                return cached_history
            
            if self.database:
                bids = await self.database.get_bid_history_by_item(item_id, limit)
                
                # Cache with short TTL
                self._cache_entity(cache_key, bids, ttl_seconds=60)
                
                return bids
            return []
        except Exception as e:
            print(f"Error getting bid history: {e}")
            return []
    
    async def get_recent_bids(self, limit: int = 20, hours: int = 24) -> List[Bid]:
        """Get recent bids across all items."""
        try:
            limit, _ = self._validate_pagination(limit, 0)
            
            # Cache recent bids
            cache_key = self._get_cache_key("recent_bids", f"{hours}h_{limit}")
            cached_bids = self._get_cached_entity(cache_key)
            if cached_bids:
                return cached_bids
            
            if self.database:
                bids = await self.database.get_recent_bids(limit, hours)
                
                # Cache with short TTL
                self._cache_entity(cache_key, bids, ttl_seconds=120)
                
                return bids
            return []
        except Exception as e:
            print(f"Error getting recent bids: {e}")
            return []
    
    async def get_winning_bids(self, bidder_id: str, limit: int = 20) -> List[Bid]:
        """Get winning bids for a bidder."""
        try:
            limit, _ = self._validate_pagination(limit, 0)
            
            if self.database:
                return await self.database.get_winning_bids_by_bidder(bidder_id, limit)
            return []
        except Exception as e:
            print(f"Error getting winning bids: {e}")
            return []
    
    async def get_outbid_bids(self, bidder_id: str, limit: int = 20) -> List[Bid]:
        """Get outbid bids for a bidder."""
        try:
            limit, _ = self._validate_pagination(limit, 0)
            
            if self.database:
                return await self.database.get_outbid_bids_by_bidder(bidder_id, limit)
            return []
        except Exception as e:
            print(f"Error getting outbid bids: {e}")
            return []
    
    async def count_bids_by_item(self, item_id: str) -> int:
        """Count total bids for an item."""
        try:
            # Check cache first
            cache_key = self._get_cache_key("bid_count", item_id)
            cached_count = self._get_cached_entity(cache_key)
            if cached_count is not None:
                return cached_count
            
            if self.database:
                count = await self.database.count_bids_by_item(item_id)
                
                # Cache with short TTL
                self._cache_entity(cache_key, count, ttl_seconds=60)
                
                return count
            return 0
        except Exception as e:
            print(f"Error counting bids by item: {e}")
            return 0
    
    async def count_unique_bidders_by_item(self, item_id: str) -> int:
        """Count unique bidders for an item."""
        try:
            # Check cache first
            cache_key = self._get_cache_key("unique_bidders", item_id)
            cached_count = self._get_cached_entity(cache_key)
            if cached_count is not None:
                return cached_count
            
            if self.database:
                count = await self.database.count_unique_bidders_by_item(item_id)
                
                # Cache with short TTL
                self._cache_entity(cache_key, count, ttl_seconds=60)
                
                return count
            return 0
        except Exception as e:
            print(f"Error counting unique bidders: {e}")
            return 0
    
    async def get_bid_stats(self, item_id: str) -> Dict[str, Any]:
        """Get bid statistics for an item."""
        try:
            # Check cache first
            cache_key = self._get_cache_key("bid_stats", item_id)
            cached_stats = self._get_cached_entity(cache_key)
            if cached_stats:
                return cached_stats
            
            if self.database:
                stats = await self.database.get_bid_stats_by_item(item_id)
                
                # Cache with short TTL
                self._cache_entity(cache_key, stats, ttl_seconds=120)
                
                return stats
            return {}
        except Exception as e:
            print(f"Error getting bid stats: {e}")
            return {}
    
    async def get_bidder_stats(self, bidder_id: str) -> Dict[str, Any]:
        """Get bidding statistics for a user."""
        try:
            # Check cache first
            cache_key = self._get_cache_key("bidder_stats", bidder_id)
            cached_stats = self._get_cached_entity(cache_key)
            if cached_stats:
                return cached_stats
            
            if self.database:
                stats = await self.database.get_bidder_stats(bidder_id)
                
                # Cache with medium TTL
                self._cache_entity(cache_key, stats, ttl_seconds=300)
                
                return stats
            return {}
        except Exception as e:
            print(f"Error getting bidder stats: {e}")
            return {}
    
    async def mark_bids_outbid(self, item_id: str, winning_bid_id: str) -> bool:
        """Mark all other bids as outbid when a new highest bid is placed."""
        try:
            if self.database:
                success = await self.database.mark_bids_outbid(item_id, winning_bid_id)
                
                if success:
                    # Invalidate related caches
                    self._invalidate_item_bid_caches(item_id)
                
                return success
            return False
        except Exception as e:
            print(f"Error marking bids outbid: {e}")
            return False
    
    async def finalize_auction_bids(self, item_id: str, winning_bid_id: str) -> bool:
        """Finalize bids when auction ends."""
        try:
            if self.database:
                success = await self.database.finalize_auction_bids(item_id, winning_bid_id)
                
                if success:
                    # Invalidate related caches
                    self._invalidate_item_bid_caches(item_id)
                
                return success
            return False
        except Exception as e:
            print(f"Error finalizing auction bids: {e}")
            return False
    
    def _invalidate_related_caches(self, bid: Bid):
        """Invalidate caches related to a bid."""
        try:
            # Invalidate item-specific caches
            self._invalidate_item_bid_caches(bid.item_id)
            
            # Invalidate bidder-specific caches
            bidder_cache_key = self._get_cache_key("bidder_stats", bid.bidder_id)
            self._invalidate_cache(bidder_cache_key)
            
            # Invalidate recent bids cache
            self._invalidate_cache(self._get_cache_key("recent_bids", "*"))
            
        except Exception as e:
            print(f"Error invalidating related caches: {e}")
    
    def _invalidate_item_bid_caches(self, item_id: str):
        """Invalidate all bid-related caches for an item."""
        try:
            cache_keys = [
                self._get_cache_key("bids_item", f"{item_id}_*"),
                self._get_cache_key("highest_bid", item_id),
                self._get_cache_key("bid_history", f"{item_id}_*"),
                self._get_cache_key("bid_count", item_id),
                self._get_cache_key("unique_bidders", item_id),
                self._get_cache_key("bid_stats", item_id)
            ]
            
            for cache_key in cache_keys:
                self._invalidate_cache(cache_key)
                
        except Exception as e:
            print(f"Error invalidating item bid caches: {e}")
    
    async def batch_create_bids(self, bids: List[Bid]) -> List[Bid]:
        """Create multiple bids in batch."""
        try:
            operations = [self.create(bid) for bid in bids]
            results = await self._batch_operation(operations)
            return self._filter_exceptions(results)
        except Exception as e:
            print(f"Error in batch create bids: {e}")
            return []
    
    async def batch_update_bids(self, bids: List[Bid]) -> List[bool]:
        """Update multiple bids in batch."""
        try:
            operations = [self.update(bid) for bid in bids]
            results = await self._batch_operation(operations)
            return self._filter_exceptions(results)
        except Exception as e:
            print(f"Error in batch update bids: {e}")
            return []