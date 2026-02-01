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
from services.arweave_post_service import arweave_post_service
from services.auction_verification_service import auction_verification_service
from utils.auction_wallet_manager import auction_wallet_manager
from utils.rsa_utils import generate_auction_rsa_keys


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
    
    async def create_auction(self, seller: User, item_data: Dict[str, Any], 
                           user_seed: Optional[bytes] = None) -> Optional[Item]:
        """Create a new auction item with Nano wallet and Arweave integration."""
        try:
            # Validate item data
            if not self._validate_item_data(item_data):
                return None
            
            # Create item
            item = Item(
                seller_id=seller.id,
                title=item_data.get('title', ''),
                description=item_data.get('description', ''),
                starting_price_usdc=str(item_data.get('starting_price_usdc', 0.0)),
                auction_end=item_data.get('auction_end', ''),
                status='draft',
                tags=item_data.get('tags', []),
                category=item_data.get('category', ''),
                shipping_required=item_data.get('shipping_required', False),
                shipping_cost_usdc=str(item_data.get('shipping_cost_usdc', 0.0))
            )
            
            # Calculate data hash for integrity
            item.data_hash = item.calculate_data_hash()
            
            # Check if wallet and RSA data were pre-generated (from dialog)
            if item_data.get('auction_rsa_fingerprint'):
                print(f"[DEBUG] Using pre-generated wallet/RSA data from item_data")
                item.auction_rsa_private_key = item_data.get('auction_rsa_private_key', '')
                item.auction_rsa_public_key = item_data.get('auction_rsa_public_key', '')
                item.auction_rsa_fingerprint = item_data.get('auction_rsa_fingerprint', '')
                item.auction_nano_address = item_data.get('auction_nano_address', '')
                item.auction_nano_public_key = item_data.get('auction_nano_public_key', '')
                item.auction_nano_private_key = item_data.get('auction_nano_private_key', '')
                item.auction_nano_seed = item_data.get('auction_nano_seed', '')
                item.auction_wallet_created_at = item_data.get('auction_wallet_created_at', datetime.now(timezone.utc).isoformat())
                print(f"RSA fingerprint: {item.auction_rsa_fingerprint}")
                print(f"Nano address: {item.auction_nano_address}")
            else:
                # Generate RSA keys for the auction if not provided
                rsa_data = generate_auction_rsa_keys(seller.id, item.id)
                if rsa_data:
                    item.auction_rsa_private_key = rsa_data['private_key_base64']
                    item.auction_rsa_public_key = rsa_data['public_key_base64']
                    item.auction_rsa_fingerprint = rsa_data['fingerprint']
                    print(f"RSA key pair generated for auction: {item.auction_rsa_fingerprint}")
                
                # Create auction-specific Nano wallet if user seed provided
                if user_seed and auction_wallet_manager:
                    wallet_data = auction_wallet_manager.create_auction_wallet(user_seed, item.id)
                    if wallet_data:
                        item.auction_nano_address = wallet_data['nano_address']
                        item.auction_nano_public_key = wallet_data['nano_public_key']
                        item.auction_nano_private_key = wallet_data['nano_private_key']
                        item.auction_nano_seed = wallet_data['nano_seed']
                        item.auction_wallet_created_at = datetime.now(timezone.utc).isoformat()
                        print(f"Auction wallet created: {wallet_data['nano_address']}")
                        
                        # Send first transaction to auction wallet with RSA fingerprint as memo
                        # This announces the item to the blockchain using the RSA fingerprint as the ID
                        try:
                            if seller.nano_address and item.auction_nano_address and item.auction_rsa_fingerprint:
                                # Send minimal amount (0.000001 NANO) with RSA fingerprint as memo
                                minimal_amount = self.blockchain.nano_client.nano_to_raw(0.000001)
                                announcement_tx = await self.blockchain.send_nano(
                                    seller.nano_address,
                                    item.auction_nano_address,
                                    minimal_amount,
                                    memo=item.auction_rsa_fingerprint[:32].replace(':', '')
                                )
                                if announcement_tx:
                                    print(f"Item announcement sent to auction wallet: {announcement_tx}")
                                else:
                                    print("Warning: Failed to send item announcement transaction")
                        except Exception as e:
                            print(f"Warning: Could not send item announcement transaction: {e}")
            
            # Store on Arweave
            arweave_tags = [
                ("Content-Type", "application/json"),
                ("App-Name", "Sapphire-Exchange"),
                ("Data-Type", "auction-item"),
                ("Seller-ID", seller.id),
                ("Item-ID", item.id)
            ]
            
            # Tag auction with RSA fingerprint as the primary ID
            if item.auction_rsa_fingerprint:
                arweave_tags.append(("RSA-Fingerprint", item.auction_rsa_fingerprint))
            
            if item.auction_nano_address:
                arweave_tags.append(("Auction-Nano-Address", item.auction_nano_address))
            
            tx_id = await self.blockchain.store_data(item.to_dict(), arweave_tags)
            if tx_id:
                item.arweave_metadata_uri = tx_id
                item.arweave_confirmed = True
                item.status = 'active'
                
                # Store in database
                if self.database:
                    await self.database.store_item(item)
                
                # Add auction to local cache and create Arweave post
                if arweave_post_service:
                    arweave_post_service.add_local_auction(item)
                    
                    # Get expiring auctions to include in post
                    expiring = arweave_post_service.get_expiring_auctions(hours_until_expiry=24)
                    
                    # Create individual auction post
                    post_data = await arweave_post_service.create_auction_post(
                        item, 
                        seller, 
                        expiring_auctions=expiring
                    )
                    
                    if post_data:
                        # Post to Arweave
                        tx_id = await arweave_post_service.post_auction_to_arweave(post_data, seller)
                        if tx_id:
                            print(f"Auction posted to Arweave: {tx_id}")
                        else:
                            print("Warning: Failed to post auction to Arweave")
                    else:
                        print("Warning: Failed to create auction post")
                
                return item
            
            return None
        except Exception as e:
            print(f"Error creating auction: {e}")
            return None
    
    async def place_bid(self, bidder: User, item: Item, bid_amount_usdc: float, 
                       currency: str = "USDC") -> Optional[Bid]:
        """Place a bid on an auction item with USDC integration. (Testing database implementation)"""
        try:
            # Validate bid
            if not self._validate_bid(item, bid_amount_usdc, currency):
                return None
            
            # Check if auction is still active
            if item.is_ended() or item.status != 'active':
                print("Auction has ended or is not active")
                return None
            
            # Convert amounts
            amount_raw = "0"  # Will be set based on currency
            amount_usd = None
            
            if currency == "NANO":
                # Convert USDC to NANO (simplified conversion)
                nano_amount = bid_amount_usdc * 0.1  # Mock conversion rate
                amount_raw = self.blockchain.nano_client.nano_to_raw(nano_amount)
            elif currency == "USDC":
                # Primary currency (Testing database implementation)
                pass
                
            # Foundation code for real DOGE currency (commented out)
            """
            elif currency == "DOGE":
                # Foundation code for real DOGE blockchain
                pass
            """
            
            # Create bid
            bid = Bid(
                item_id=item.id,
                bidder_id=bidder.id,
                amount_usdc=str(bid_amount_usdc),  # Testing database implementation
                amount_raw=amount_raw,
                amount_usd=amount_usd,
                status='pending'
            )
            
            # Process payment based on currency
            if currency == "NANO":
                # Send Nano transaction to auction wallet with bid info in memo
                tx_hash = None
                
                if item.auction_nano_address and item.auction_rsa_fingerprint:
                    # Send to auction wallet with RSA fingerprint and bid amount in memo
                    # Format: rsa_fp:bid_amount (limited to 32 chars)
                    memo_data = f"{item.auction_rsa_fingerprint[:16]}:{bid_amount_usdc}".replace(':', '')[:32]
                    tx_hash = await self.blockchain.send_nano(
                        bidder.nano_address,
                        item.auction_nano_address,  # Send to auction wallet
                        amount_raw,
                        memo=memo_data
                    )
                else:
                    # Fallback: send to seller
                    memo_data = f"bid:{bid_amount_usdc}"[:32]
                    tx_hash = await self.blockchain.send_nano(
                        bidder.nano_address,
                        item.seller_id,
                        amount_raw,
                        memo=memo_data
                    )
                
                if tx_hash:
                    bid.nano_block_hash = tx_hash
                    bid.transaction_hash = tx_hash
                else:
                    print("Failed to send Nano transaction")
                    return None
            
            elif currency == "USDC":
                # Send USDC transaction (Testing database implementation)
                # For testing, we'll create a mock transaction
                # In real implementation, this would interact with actual blockchain
                try:
                    # Mock USDC transaction for testing database
                    tx_hash = f"usdc_tx_{bidder.id}_{item.id}_{bid_amount_usdc}"
                    bid.transaction_hash = tx_hash
                    print(f"USDC transaction created (testing): {tx_hash}")
                except Exception as e:
                    print(f"Failed to create USDC transaction: {e}")
                    return None
                    
            # Foundation code for real DOGE blockchain (commented out)
            """
            elif currency == "DOGE":
                # Send DOGE transaction (simplified)
                tx_hash = await self.blockchain.send_doge(
                    item.seller_id,  # Simplified - should be escrow address
                    bid_amount_usdc
                )
                if tx_hash:
                    bid.transaction_hash = tx_hash
                else:
                    print("Failed to send DOGE transaction")
                    return None
            """
            
            # Store bid on Arweave
            bid_tags = [
                ("Content-Type", "application/json"),
                ("App-Name", "Sapphire-Exchange"),
                ("Data-Type", "bid"),
                ("Item-ID", item.id),
                ("Bidder-ID", bidder.id),
                ("Currency", currency)
            ]
            
            # Tag bid with RSA fingerprint for master post correlation
            if item.auction_rsa_fingerprint:
                bid_tags.append(("RSA-Fingerprint", item.auction_rsa_fingerprint))
            
            if item.auction_nano_address:
                bid_tags.append(("Nano-Address", item.auction_nano_address))
            else:
                bid_tags.append(("Seller-ID", item.seller_id))
            
            arweave_tx_id = await self.blockchain.store_data(bid.to_dict(), bid_tags)
            if arweave_tx_id:
                bid.arweave_tx_id = arweave_tx_id
                bid.status = 'confirmed'
                bid.confirmed_at = datetime.now(timezone.utc).isoformat()
                
                # Update item with new bid
                await self._update_item_with_bid(item, bid)
                
                # Update local auction cache with new bid
                if arweave_post_service:
                    arweave_post_service.add_local_auction(item)
                
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
        """End an auction and determine winner with verification."""
        try:
            if item.status != 'active':
                return False
            
            # Get all bids
            bids = await self.get_bids_for_item(item.id)
            if not bids:
                item.status = 'expired'
            else:
                # Find highest bid
                highest_bid = max(bids, key=lambda b: float(b.amount_usdc))  # Testing database implementation
                highest_bid.status = 'won'
                
                # Mark other bids as outbid
                for bid in bids:
                    if bid.id != highest_bid.id:
                        bid.status = 'outbid'
                
                item.status = 'sold'
                item.current_bid_usdc = highest_bid.amount_usdc  # Testing database implementation
                item.current_bidder = highest_bid.bidder_id
            
            # Verify winner from Nano wallet if available
            if item.auction_nano_address and arweave_post_service:
                verified, winner_id, winning_amount = await arweave_post_service.verify_auction_winner(
                    item.id,
                    item.auction_nano_address
                )
                if verified:
                    print(f"Auction winner verified: {winner_id} with bid {winning_amount}")
            
            # Update item on Arweave
            arweave_tags = [
                ("Content-Type", "application/json"),
                ("App-Name", "Sapphire-Exchange"),
                ("Data-Type", "auction-ended"),
                ("Item-ID", item.id),
                ("Final-Status", item.status)
            ]
            
            if item.current_bidder:
                arweave_tags.append(("Winner-ID", item.current_bidder))
            
            tx_id = await self.blockchain.store_data(item.to_dict(), arweave_tags)
            if tx_id:
                # Update master post
                if arweave_post_service:
                    await arweave_post_service.update_auction_bid(
                        item.id,
                        item.current_bid_doge or item.starting_price_doge,
                        item.current_bidder or ""
                    )
                
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
            
            # Check if bid is higher than current bid (Testing database implementation)
            current_bid = float(item.current_bid_usdc or item.starting_price_usdc or "0")
            if amount <= current_bid:
                return False
            
            # Validate currency (Testing database implementation)
            if currency not in ["USDC", "NANO"]:  # Testing database implementation
                return False
                
            # Foundation code for real DOGE blockchain (commented out)
            """
            # Check if bid is higher than current bid
            current_bid = float(item.current_bid_doge or item.starting_price_doge or "0")
            if amount <= current_bid:
                return False
            
            # Validate currency
            if currency not in ["DOGE", "NANO"]:
                return False
            """
            
            return True
        except Exception:
            return False
    
    async def _update_item_with_bid(self, item: Item, bid: Bid):
        """Update item with new bid information."""
        try:
            item.current_bid_usdc = bid.amount_usdc  # Testing database implementation
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
    
    async def post_auction_database_to_arweave(self, user: User, ar_cost: float = 0.05) -> Tuple[bool, str, Optional[str]]:
        """
        Post the master auction database to Arweave with AR balance check.
        
        Args:
            user: The user posting (for AR balance verification)
            ar_cost: Cost in AR for posting (0.05 AR for auction post)
            
        Returns:
            Tuple of (success, message, tx_id)
        """
        try:
            if not arweave_post_service:
                return False, "Arweave post service not initialized", None
            
            # Check AR balance
            if not user.arweave_address:
                return False, "User has no Arweave address", None
            
            balance_winston = await self.blockchain.arweave_client.get_balance(user.arweave_address)
            if balance_winston is None:
                return False, "Could not retrieve Arweave balance", None
            
            balance_ar = self.blockchain.arweave_client.winston_to_ar(balance_winston)
            
            # Validate sufficient balance
            if balance_ar < ar_cost:
                return False, f"Insufficient AR balance. Required: {ar_cost} AR, Available: {balance_ar:.6f} AR", None
            
            # Check for finished auctions before posting
            finished_auctions = await arweave_post_service.check_finished_auctions()
            if finished_auctions:
                print(f"Found {len(finished_auctions)} finished auctions for verification")
            
            # Post master post to Arweave
            tx_id = await arweave_post_service.post_master_to_arweave(user, ar_cost)
            
            if tx_id:
                return True, f"Auction database posted to Arweave: {tx_id}", tx_id
            else:
                return False, "Failed to post auction database to Arweave", None
        
        except Exception as e:
            print(f"Error posting auction database to Arweave: {e}")
            return False, f"Error: {str(e)}", None
    
    async def get_master_post_summary(self) -> Optional[Dict[str, Any]]:
        """Get summary of current master Arweave post."""
        try:
            if arweave_post_service:
                return arweave_post_service.get_master_post_summary()
            return None
        except Exception as e:
            print(f"Error getting master post summary: {e}")
            return None
    
    async def add_user_to_master_post(self, user: User) -> bool:
        """
        Add user information to master post when they create their first auction.
        Users are registered on the same post as their first auction.
        
        Args:
            user: The user to add
            
        Returns:
            True if added successfully
        """
        try:
            if not arweave_post_service:
                return False
            
            # Initialize users list in master post if needed
            if 'users' not in arweave_post_service.master_post_data:
                arweave_post_service.master_post_data['users'] = {}
            
            # Add user data
            user_data = {
                'id': user.id,
                'username': user.username,
                'nano_address': user.nano_address,
                'arweave_address': user.arweave_address,
                'public_key': user.public_key,
                'reputation_score': user.reputation_score,
                'total_sales': user.total_sales,
                'total_purchases': user.total_purchases,
                'created_at': user.created_at,
                'registered_on_arweave': datetime.now(timezone.utc).isoformat()
            }
            
            arweave_post_service.master_post_data['users'][user.id] = user_data
            print(f"User {user.username} added to master post")
            return True
        except Exception as e:
            print(f"Error adding user to master post: {e}")
            return False
    
    async def start_background_verification(self) -> None:
        """Start background verification service if not already running."""
        try:
            if auction_verification_service:
                # Start in background (non-blocking)
                asyncio.create_task(auction_verification_service.start_background_verification())
                print("Background auction verification service started")
        except Exception as e:
            print(f"Error starting background verification: {e}")
    
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