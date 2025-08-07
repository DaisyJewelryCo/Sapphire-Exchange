"""
Auction service for Sapphire Exchange business logic.
Handles auction creation, bidding, and management.
"""
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import asdict

from models.models import Item, Bid, User
from blockchain.blockchain_manager import blockchain_manager
from config.app_config import app_config


class AuctionService:
    """Service for managing auctions and bidding."""
    
    def __init__(self, database=None):
        """Initialize auction service."""
        self.database = database
        self.blockchain = blockchain_manager
        
        # Event callbacks
        self.bid_placed_callbacks = []
        self.auction_ended_callbacks = []
        self.status_change_callbacks = []
    
    async def create_auction(self, seller: User, item_data: Dict[str, Any]) -> Optional[Item]:
        """Create a new auction item."""
        try:
            # Validate item data
            if not self._validate_item_data(item_data):
                return None
            
            # Create item
            item = Item(
                seller_id=seller.id,
                title=item_data.get('title', ''),
                description=item_data.get('description', ''),
                starting_price_doge=str(item_data.get('starting_price_doge', 0.0)),
                auction_end=item_data.get('auction_end', ''),
                status='draft',
                tags=item_data.get('tags', []),
                category=item_data.get('category', ''),
                shipping_required=item_data.get('shipping_required', False),
                shipping_cost_doge=str(item_data.get('shipping_cost_doge', 0.0))
            )
            
            # Calculate data hash for integrity
            item.data_hash = item.calculate_data_hash()
            
            # Store on Arweave
            arweave_tags = [
                ("Content-Type", "application/json"),
                ("App-Name", "Sapphire-Exchange"),
                ("Data-Type", "auction-item"),
                ("Seller-ID", seller.id),
                ("Item-ID", item.id)
            ]
            
            tx_id = await self.blockchain.store_data(item.to_dict(), arweave_tags)
            if tx_id:
                item.arweave_metadata_uri = tx_id
                item.arweave_confirmed = True
                item.status = 'active'
                
                # Store in database
                if self.database:
                    await self.database.store_item(item)
                
                return item
            
            return None
        except Exception as e:
            print(f"Error creating auction: {e}")
            return None
    
    async def place_bid(self, bidder: User, item: Item, bid_amount_doge: float, 
                       currency: str = "DOGE") -> Optional[Bid]:
        """Place a bid on an auction item."""
        try:
            # Validate bid
            if not self._validate_bid(item, bid_amount_doge, currency):
                return None
            
            # Check if auction is still active
            if item.is_ended() or item.status != 'active':
                print("Auction has ended or is not active")
                return None
            
            # Convert amounts
            amount_raw = "0"  # Will be set based on currency
            amount_usd = None
            
            if currency == "NANO":
                # Convert DOGE to NANO (simplified conversion)
                nano_amount = bid_amount_doge * 0.1  # Mock conversion rate
                amount_raw = self.blockchain.nano_client.nano_to_raw(nano_amount)
            elif currency == "DOGE":
                # Primary currency
                pass
            
            # Create bid
            bid = Bid(
                item_id=item.id,
                bidder_id=bidder.id,
                amount_doge=str(bid_amount_doge),
                amount_raw=amount_raw,
                amount_usd=amount_usd,
                status='pending'
            )
            
            # Process payment based on currency
            if currency == "NANO":
                # Send Nano transaction
                tx_hash = await self.blockchain.send_nano(
                    bidder.nano_address,
                    item.seller_id,  # Simplified - should be escrow address
                    amount_raw
                )
                if tx_hash:
                    bid.nano_block_hash = tx_hash
                    bid.transaction_hash = tx_hash
                else:
                    print("Failed to send Nano transaction")
                    return None
            
            elif currency == "DOGE":
                # Send DOGE transaction (simplified)
                tx_hash = await self.blockchain.send_doge(
                    item.seller_id,  # Simplified - should be escrow address
                    bid_amount_doge
                )
                if tx_hash:
                    bid.transaction_hash = tx_hash
                else:
                    print("Failed to send DOGE transaction")
                    return None
            
            # Store bid on Arweave
            bid_tags = [
                ("Content-Type", "application/json"),
                ("App-Name", "Sapphire-Exchange"),
                ("Data-Type", "bid"),
                ("Item-ID", item.id),
                ("Bidder-ID", bidder.id),
                ("Currency", currency)
            ]
            
            arweave_tx_id = await self.blockchain.store_data(bid.to_dict(), bid_tags)
            if arweave_tx_id:
                bid.arweave_tx_id = arweave_tx_id
                bid.status = 'confirmed'
                bid.confirmed_at = datetime.now(timezone.utc).isoformat()
                
                # Update item with new bid
                await self._update_item_with_bid(item, bid)
                
                # Store in database
                if self.database:
                    await self.database.store_bid(bid)
                
                # Notify callbacks
                self._notify_bid_placed(item, bid)
                
                return bid
            
            return None
        except Exception as e:
            print(f"Error placing bid: {e}")
            return None
    
    async def get_active_auctions(self, limit: int = 20, offset: int = 0) -> List[Item]:
        """Get list of active auctions."""
        try:
            if self.database:
                return await self.database.get_items_by_status('active', limit, offset)
            return []
        except Exception as e:
            print(f"Error getting active auctions: {e}")
            return []
    
    async def get_auction_by_id(self, item_id: str) -> Optional[Item]:
        """Get auction item by ID."""
        try:
            if self.database:
                return await self.database.get_item(item_id)
            return None
        except Exception as e:
            print(f"Error getting auction: {e}")
            return None
    
    async def get_bids_for_item(self, item_id: str) -> List[Bid]:
        """Get all bids for an auction item."""
        try:
            if self.database:
                return await self.database.get_bids_by_item(item_id)
            return []
        except Exception as e:
            print(f"Error getting bids: {e}")
            return []
    
    async def end_auction(self, item: Item) -> bool:
        """End an auction and determine winner."""
        try:
            if item.status != 'active':
                return False
            
            # Get all bids
            bids = await self.get_bids_for_item(item.id)
            if not bids:
                item.status = 'expired'
            else:
                # Find highest bid
                highest_bid = max(bids, key=lambda b: float(b.amount_doge))
                highest_bid.status = 'won'
                
                # Mark other bids as outbid
                for bid in bids:
                    if bid.id != highest_bid.id:
                        bid.status = 'outbid'
                
                item.status = 'sold'
                item.current_bid_doge = highest_bid.amount_doge
                item.current_bidder = highest_bid.bidder_id
            
            # Update item on Arweave
            arweave_tags = [
                ("Content-Type", "application/json"),
                ("App-Name", "Sapphire-Exchange"),
                ("Data-Type", "auction-ended"),
                ("Item-ID", item.id),
                ("Final-Status", item.status)
            ]
            
            tx_id = await self.blockchain.store_data(item.to_dict(), arweave_tags)
            if tx_id:
                # Update database
                if self.database:
                    await self.database.update_item(item)
                    for bid in bids:
                        await self.database.update_bid(bid)
                
                # Notify callbacks
                self._notify_auction_ended(item)
                
                return True
            
            return False
        except Exception as e:
            print(f"Error ending auction: {e}")
            return False
    
    async def search_auctions(self, query: str, category: Optional[str] = None, 
                            tags: Optional[List[str]] = None) -> List[Item]:
        """Search auctions by query, category, and tags."""
        try:
            if self.database:
                return await self.database.search_items(query, category, tags)
            return []
        except Exception as e:
            print(f"Error searching auctions: {e}")
            return []
    
    def _validate_item_data(self, item_data: Dict[str, Any]) -> bool:
        """Validate auction item data."""
        try:
            # Check required fields
            if not item_data.get('title'):
                return False
            
            if not item_data.get('auction_end'):
                return False
            
            # Validate title length
            if len(item_data['title']) > app_config.ui.max_title_length:
                return False
            
            # Validate description length
            description = item_data.get('description', '')
            if len(description) > app_config.ui.max_description_length:
                return False
            
            # Validate tags
            tags = item_data.get('tags', [])
            if len(tags) > app_config.ui.max_tags_per_item:
                return False
            
            for tag in tags:
                if len(tag) > app_config.ui.max_tag_length:
                    return False
            
            # Validate auction end time
            try:
                end_time = datetime.fromisoformat(item_data['auction_end'].replace('Z', '+00:00'))
                if end_time <= datetime.now(timezone.utc):
                    return False
            except ValueError:
                return False
            
            return True
        except Exception:
            return False
    
    def _validate_bid(self, item: Item, amount: float, currency: str) -> bool:
        """Validate bid amount and currency."""
        try:
            # Check minimum bid amount
            if amount <= 0:
                return False
            
            # Check if bid is higher than current bid
            current_bid = float(item.current_bid_doge or item.starting_price_doge or "0")
            if amount <= current_bid:
                return False
            
            # Validate currency
            if currency not in ["DOGE", "NANO"]:
                return False
            
            return True
        except Exception:
            return False
    
    async def _update_item_with_bid(self, item: Item, bid: Bid):
        """Update item with new bid information."""
        try:
            item.current_bid_doge = bid.amount_doge
            item.current_bidder = bid.bidder_id
            
            # Add bid to item's bid list
            if not item.bids:
                item.bids = []
            item.bids.append(bid.id)
            
            # Update database
            if self.database:
                await self.database.update_item(item)
        except Exception as e:
            print(f"Error updating item with bid: {e}")
    
    # Event handling
    def add_bid_placed_callback(self, callback):
        """Add callback for bid placed events."""
        self.bid_placed_callbacks.append(callback)
    
    def add_auction_ended_callback(self, callback):
        """Add callback for auction ended events."""
        self.auction_ended_callbacks.append(callback)
    
    def _notify_bid_placed(self, item: Item, bid: Bid):
        """Notify all callbacks of bid placed event."""
        for callback in self.bid_placed_callbacks:
            try:
                callback(item, bid)
            except Exception as e:
                print(f"Error in bid placed callback: {e}")
    
    def _notify_auction_ended(self, item: Item):
        """Notify all callbacks of auction ended event."""
        for callback in self.auction_ended_callbacks:
            try:
                callback(item)
            except Exception as e:
                print(f"Error in auction ended callback: {e}")


# Global auction service instance
auction_service = AuctionService()