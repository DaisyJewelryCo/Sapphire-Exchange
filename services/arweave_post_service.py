"""
Arweave Post Service for Sapphire Exchange.
Creates individual auction posts and aggregates data from Nano wallets.
"""
import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple

from models.models import Item, User
from blockchain.blockchain_manager import blockchain_manager
from utils.sequence_generator import SequenceGenerator


class AuctionPostData:
    """Data for a single auction entry."""
    
    def __init__(self, item: Item):
        """Initialize from Item model."""
        self.item_id = item.id
        self.sha_id = item.sha_id
        self.seller_id = item.seller_id
        self.title = item.title
        self.description = item.description
        self.starting_price_usdc = item.starting_price_usdc
        self.current_bid_usdc = item.current_bid_usdc or item.starting_price_usdc
        
        self.current_bidder = item.current_bidder_id
        self.auction_end = item.auction_end
        self.status = item.status
        
        self.auction_nano_address = item.auction_nano_address
        self.auction_nano_public_key = item.auction_nano_public_key
        
        self.created_at = item.created_at
        self.updated_at = item.updated_at
        self.winner = None
        self.winning_bid = None
        self.confirmed_winner = False
        self.confirmation_count = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'item_id': self.item_id,
            'sha_id': self.sha_id,
            'seller_id': self.seller_id,
            'title': self.title,
            'description': self.description,
            'starting_price_usdc': self.starting_price_usdc,
            'current_bid_usdc': self.current_bid_usdc,
            'current_bidder': self.current_bidder,
            'auction_end': self.auction_end,
            'status': self.status,
            'auction_nano_address': self.auction_nano_address,
            'auction_nano_public_key': self.auction_nano_public_key,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'winner': self.winner,
            'winning_bid': self.winning_bid,
            'confirmed_winner': self.confirmed_winner,
            'confirmation_count': self.confirmation_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AuctionPostData':
        """Create from dictionary."""
        obj = cls.__new__(cls)
        for key, value in data.items():
            setattr(obj, key, value)
        return obj


class ArweavePostService:
    """Service for creating individual auction posts on Arweave."""
    
    def __init__(self):
        """Initialize Arweave post service."""
        self.blockchain = blockchain_manager
        self.sequence_generator = SequenceGenerator(blockchain_manager.nano_client)
        
        # Local auction cache
        self.local_auctions: Dict[str, Item] = {}
        
        # Cached Arweave post data
        self.cached_posts: Dict[str, Dict[str, Any]] = {}
        
        # Pending inventory posts (user_id -> post_data) - waiting for user to post to Arweave
        self.pending_inventory_posts: Dict[str, Dict[str, Any]] = {}
    
    async def create_auction_post(self, item: Item, user: User, 
                                 expiring_auctions: Optional[List[Item]] = None,
                                 sequence_wallet: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Create an Arweave post for a new auction.
        
        Post structure:
        - Top section: Current auction details (title, description, prices, SHA ID)
        - Bottom section: All auctions expiring in next 24 hours + top bidders
        
        Args:
            item: The Item/auction being created
            user: The user creating the auction
            expiring_auctions: List of auctions about to expire
            sequence_wallet: Nano wallet for sequence validation
            
        Returns:
            Post data dictionary or None on failure
        """
        try:
            if not item.sha_id:
                print(f"Error: Item must have SHA ID (got: '{item.sha_id}')")
                return None
            if not item.auction_nano_address:
                print(f"Error: Item must have Nano address (got: '{item.auction_nano_address}')")
                return None
            
            # Generate sequence number
            sequence = await self.sequence_generator.get_next_available_sequence(
                user.id, 
                sequence_wallet or item.auction_nano_address
            )
            
            if sequence is None:
                print("Error: Could not generate sequence number")
                return None
            
            # Build post data
            now = datetime.now(timezone.utc)
            post_data = {
                'version': '1.0',
                'sequence': sequence,  # Unique identifier for this post
                'created_at': now.isoformat(),
                'posted_by': user.id,
                
                # Top section: Current auction details
                'auction': {
                    'item_id': item.id,
                    'sha_id': item.sha_id,
                    'seller_id': item.seller_id,
                    'title': item.title,
                    'description': item.description,
                    'starting_price_usdc': item.starting_price_usdc,  # Testing database implementation
                    'current_bid_usdc': item.current_bid_usdc or item.starting_price_usdc,  # Testing database implementation
                    'current_bidder': item.current_bidder_id,
                    'auction_end': item.auction_end,
                    'status': item.status,
                    'auction_nano_address': item.auction_nano_address,
                    'auction_nano_public_key': item.auction_nano_public_key,
                },
                
                # Bottom section: Expiring auctions list
                'expiring_auctions': []
            }
            
            # Add expiring auctions (auctions ending in next 24 hours)
            if expiring_auctions:
                for expiring_item in expiring_auctions:
                    post_data['expiring_auctions'].append({
                        'item_id': expiring_item.id,
                        'sha_id': expiring_item.sha_id,
                        'title': expiring_item.title,
                        'auction_end': expiring_item.auction_end,
                        'current_bid_usdc': expiring_item.current_bid_usdc or expiring_item.starting_price_usdc,  # Testing database implementation
                        'current_bidder': expiring_item.current_bidder_id,
                        'top_bidder_nano_address': expiring_item.auction_nano_address,
                    })
            
            return post_data
            
        except Exception as e:
            print(f"Error creating auction post: {e}")
            return None
    
    async def post_auction_to_arweave(self, post_data: Dict[str, Any], 
                                     user: User) -> Optional[str]:
        """
        Post auction data to Arweave.
        
        Args:
            post_data: The post data to post
            user: The user posting (for AR balance check)
            
        Returns:
            Arweave transaction ID or None on failure
        """
        try:
            # Validate user has Arweave address
            if not user.arweave_address:
                print(f"Error: User {user.id} does not have an Arweave address")
                return None
            
            # Check AR balance
            balance_winston = await self.blockchain.arweave_client.get_balance(user.arweave_address)
            if balance_winston is None:
                print(f"Could not get Arweave balance for address {user.arweave_address}")
                return None
            
            balance_ar = self.blockchain.arweave_client.winston_to_ar(balance_winston)
            
            if balance_ar < 0.05:
                print(f"Insufficient AR balance: {balance_ar:.6f} AR (need >= 0.05 AR for auction post)")
                return None
            
            # Create Arweave tags
            tags = [
                ("Content-Type", "application/json"),
                ("App-Name", "Sapphire-Exchange"),
                ("Data-Type", "auction-post"),
                ("Posted-By", user.id),
                ("Sequence", str(post_data.get('sequence', 0))),
                ("SHA-ID", post_data['auction'].get('sha_id', '')),
                ("Item-ID", post_data['auction'].get('item_id', '')),
                ("Auction-Status", post_data['auction'].get('status', 'active')),
            ]
            
            # Store on Arweave
            print(f"Posting auction {post_data.get('auction', {}).get('item_id')} to Arweave...")
            tx_id = await self.blockchain.arweave_client.store_data(post_data, tags)
            
            if tx_id:
                # Cache the post
                self.cached_posts[tx_id] = post_data
                print(f"Auction post posted to Arweave: {tx_id}")
                return tx_id
            
            print(f"Arweave store_data returned None for auction {post_data.get('auction', {}).get('item_id')}")
            return None
        except Exception as e:
            print(f"Error posting to Arweave: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def search_auction_posts(self, sequence_start: int, sequence_end: int,
                                  date_start: Optional[str] = None,
                                  date_end: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for auction posts by sequence number and date range.
        
        Args:
            sequence_start: Minimum sequence number
            sequence_end: Maximum sequence number
            date_start: ISO 8601 start date (optional)
            date_end: ISO 8601 end date (optional)
            
        Returns:
            List of matching post data
        """
        try:
            matching_posts = []
            
            # In a real implementation, would query Arweave with tags
            # For now, search cached posts
            for tx_id, post_data in self.cached_posts.items():
                sequence = post_data.get('sequence', 0)
                
                if not (sequence_start <= sequence <= sequence_end):
                    continue
                
                if date_start or date_end:
                    created_at = post_data.get('created_at', '')
                    if date_start and created_at < date_start:
                        continue
                    if date_end and created_at > date_end:
                        continue
                
                matching_posts.append(post_data)
            
            return matching_posts
        except Exception as e:
            print(f"Error searching auction posts: {e}")
            return []
    
    async def aggregate_auction_data(self, posts: List[Dict[str, Any]]) -> List[AuctionPostData]:
        """
        Aggregate auction data from multiple Arweave posts.
        Fetches current bid info from Nano wallets.
        
        Args:
            posts: List of Arweave post data
            
        Returns:
            List of aggregated AuctionPostData
        """
        try:
            aggregated = []
            
            for post in posts:
                auction = post.get('auction', {})
                
                if not auction:
                    continue
                
                nano_address = auction.get('auction_nano_address')
                
                # Fetch current bid info from Nano wallet
                if nano_address:
                    try:
                        account_info = await self.blockchain.nano_client.get_account_info(nano_address)
                        if account_info:
                            auction['nano_wallet_balance'] = account_info.get('balance', '0')
                            auction['nano_block_count'] = account_info.get('block_count', '0')
                    except Exception as e:
                        print(f"Error fetching Nano wallet info: {e}")
                
                # Create AuctionPostData from post
                post_data = AuctionPostData.from_dict(auction)
                aggregated.append(post_data)
            
            return aggregated
        except Exception as e:
            print(f"Error aggregating auction data: {e}")
            return []
    
    def get_expiring_auctions(self, hours_until_expiry: int = 24) -> List[Item]:
        """
        Get auctions that will expire within specified hours.
        
        Args:
            hours_until_expiry: Number of hours in future to check (default 24)
            
        Returns:
            List of items expiring soon
        """
        try:
            expiring = []
            now = datetime.now(timezone.utc)
            cutoff = now + timedelta(hours=hours_until_expiry)
            
            for item in self.local_auctions.values():
                if item.status != 'active':
                    continue
                
                try:
                    end_time = datetime.fromisoformat(
                        item.auction_end.replace('Z', '+00:00')
                    )
                    if now < end_time <= cutoff:
                        expiring.append(item)
                except ValueError:
                    continue
            
            return sorted(expiring, key=lambda x: x.auction_end)
        except Exception as e:
            print(f"Error getting expiring auctions: {e}")
            return []
    
    async def verify_winner_from_nano(self, nano_address: str, 
                                     auction_end_time: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Verify auction winner by checking Nano wallet transactions.
        Winner is the bidder who deposited Nano after auction end.
        
        Args:
            nano_address: Auction's Nano wallet address
            auction_end_time: ISO 8601 auction end time
            
        Returns:
            Tuple of (winner_bidder_id, winning_bid_amount) or (None, None)
        """
        try:
            account_info = await self.blockchain.nano_client.get_account_info(nano_address)
            
            if not account_info:
                return None, None
            
            # In real implementation, parse transaction history
            # For now, use placeholder
            return None, None
        except Exception as e:
            print(f"Error verifying winner: {e}")
            return None, None
    
    def add_local_auction(self, item: Item) -> None:
        """Cache auction locally for aggregation."""
        try:
            self.local_auctions[item.id] = item
        except Exception as e:
            print(f"Error adding local auction: {e}")
    
    def remove_local_auction(self, item_id: str) -> None:
        """Remove auction from local cache."""
        try:
            if item_id in self.local_auctions:
                del self.local_auctions[item_id]
        except Exception as e:
            print(f"Error removing local auction: {e}")
    
    async def create_inventory_post(self, user: User, items: List[Item]) -> Optional[Dict[str, Any]]:
        """
        Create an Arweave inventory post for all user items.
        
        Used when a user creates their first item to consolidate all items
        into a single Arweave post instead of creating individual posts.
        
        Args:
            user: The user/seller
            items: List of items to include in inventory
            
        Returns:
            Inventory post data or None on failure
        """
        try:
            if not items:
                print("Error: Cannot create inventory post with no items")
                return None
            
            # Generate sequence number for inventory post
            sequence = await self.sequence_generator.get_next_available_sequence(
                user.id, 
                user.nano_address
            )
            
            if sequence is None:
                print("Error: Could not generate sequence number for inventory post")
                return None
            
            now = datetime.now(timezone.utc)
            
            # Build inventory post data with all items
            post_data = {
                'version': '1.0',
                'type': 'inventory',
                'sequence': sequence,
                'created_at': now.isoformat(),
                'posted_by': user.id,
                'seller_nano_address': user.nano_address,
                'seller_arweave_address': user.arweave_address,
                'items': [item.to_dict() for item in items],
                'item_count': len(items)
            }
            
            return post_data
            
        except Exception as e:
            print(f"Error creating inventory post: {e}")
            return None
    
    async def post_inventory_to_arweave(self, post_data: Dict[str, Any], 
                                        user: User) -> Optional[str]:
        """
        Post inventory data to Arweave.
        
        Args:
            post_data: The inventory post data
            user: The user posting (for AR balance check)
            
        Returns:
            Arweave transaction ID or None on failure
        """
        try:
            # Validate user has Arweave address
            if not user.arweave_address:
                print(f"Error: User {user.id} does not have an Arweave address")
                return None
            
            # Check AR balance
            balance_winston = await self.blockchain.arweave_client.get_balance(user.arweave_address)
            if balance_winston is None:
                print(f"Could not get Arweave balance for address {user.arweave_address}")
                return None
            
            balance_ar = self.blockchain.arweave_client.winston_to_ar(balance_winston)
            
            if balance_ar < 0.05:
                print(f"Insufficient AR balance: {balance_ar:.6f} AR (need >= 0.05 AR for inventory post)")
                return None
            
            # Create Arweave tags
            tags = [
                ("Content-Type", "application/json"),
                ("App-Name", "Sapphire-Exchange"),
                ("Data-Type", "inventory"),
                ("Posted-By", user.id),
                ("Sequence", str(post_data.get('sequence', 0))),
                ("Item-Count", str(post_data.get('item_count', 0))),
            ]
            
            # Store on Arweave
            print(f"Posting inventory post for {user.username} to Arweave...")
            tx_id = await self.blockchain.arweave_client.store_data(post_data, tags)
            
            if tx_id:
                # Cache the post
                self.cached_posts[tx_id] = post_data
                print(f"Inventory post posted to Arweave: {tx_id}")
                return tx_id
            
            print(f"Arweave store_data returned None for inventory post")
            return None
        except Exception as e:
            print(f"Error posting inventory to Arweave: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def update_inventory_post(self, user: User, items: List[Item], 
                                    inventory_post_uri: str) -> Optional[Dict[str, Any]]:
        """
        Update an existing inventory post by creating a new one with all current items.
        
        Arweave is immutable, so updates are done by posting a new transaction
        that references the previous one. The client can follow the chain to get
        the latest inventory.
        
        Args:
            user: The user/seller
            items: List of current items to include
            inventory_post_uri: TX ID of the previous inventory post
            
        Returns:
            Updated inventory post data or None on failure
        """
        try:
            if not items:
                print("Error: Cannot update inventory post with no items")
                return None
            
            # Generate sequence number for updated inventory
            sequence = await self.sequence_generator.get_next_available_sequence(
                user.id, 
                user.nano_address
            )
            
            if sequence is None:
                print("Error: Could not generate sequence number for inventory post update")
                return None
            
            now = datetime.now(timezone.utc)
            
            # Build updated inventory post
            post_data = {
                'version': '1.0',
                'type': 'inventory',
                'sequence': sequence,
                'created_at': now.isoformat(),
                'posted_by': user.id,
                'seller_nano_address': user.nano_address,
                'seller_arweave_address': user.arweave_address,
                'previous_inventory_uri': inventory_post_uri,
                'items': [item.to_dict() for item in items],
                'item_count': len(items)
            }
            
            return post_data
            
        except Exception as e:
            print(f"Error updating inventory post: {e}")
            return None
    
    def store_pending_inventory(self, user_id: str, post_data: Dict[str, Any]) -> None:
        """
        Store inventory post as pending (waiting for user to post to Arweave).
        
        Args:
            user_id: The user's ID
            post_data: The inventory post data
        """
        try:
            self.pending_inventory_posts[user_id] = post_data
            print(f"[PENDING] Inventory post stored for user {user_id}")
        except Exception as e:
            print(f"Error storing pending inventory: {e}")
    
    def get_pending_inventory(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get pending inventory post for user.
        
        Args:
            user_id: The user's ID
            
        Returns:
            Pending inventory post data or None
        """
        return self.pending_inventory_posts.get(user_id)
    
    def clear_pending_inventory(self, user_id: str) -> None:
        """
        Clear pending inventory post after successful posting.
        
        Args:
            user_id: The user's ID
        """
        try:
            if user_id in self.pending_inventory_posts:
                del self.pending_inventory_posts[user_id]
                print(f"[PENDING] Cleared pending inventory for user {user_id}")
        except Exception as e:
            print(f"Error clearing pending inventory: {e}")


# Global Arweave post service instance
arweave_post_service = ArweavePostService()
