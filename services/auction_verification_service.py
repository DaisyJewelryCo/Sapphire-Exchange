"""
Auction Verification Service for Sapphire Exchange.
Handles background verification of expired auctions and winner confirmations.
Uses cross-posting algorithm to gather all AR posts for master list consensus.
"""
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any

from models.models import Item, User
from blockchain.blockchain_manager import blockchain_manager
from services.arweave_post_service import arweave_post_service


class AuctionVerificationService:
    """Service for verifying expired auctions and winner confirmations."""
    
    def __init__(self):
        """Initialize verification service."""
        self.blockchain = blockchain_manager
        self.arweave_posts: Dict[str, Dict[str, Any]] = {}  # Cache of loaded posts
        self.confirmation_records: Dict[str, Dict[str, Any]] = {}  # item_id -> confirmation data
        self.verification_window_hours = 24  # Look at auctions ended in last 24 hours
    
    async def start_background_verification(self, interval_seconds: int = 300):
        """
        Start background verification service.
        
        Args:
            interval_seconds: How often to check for expired auctions (default 5 minutes)
        """
        print(f"Starting auction verification service (check every {interval_seconds}s)")
        
        while True:
            try:
                await self.verify_recent_auctions()
                await asyncio.sleep(interval_seconds)
            except Exception as e:
                print(f"Error in background verification: {e}")
                await asyncio.sleep(interval_seconds)
    
    async def verify_recent_auctions(self) -> List[str]:
        """
        Verify auctions that ended in the last 24 hours.
        
        Returns:
            List of item IDs that were verified
        """
        try:
            verified_items = []
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.verification_window_hours)
            
            # Get finished auctions from master post
            finished = arweave_post_service.get_finished_auctions()
            
            for auction in finished:
                try:
                    end_time = datetime.fromisoformat(
                        auction.auction_end.replace('Z', '+00:00')
                    )
                    
                    # Only verify recent auctions
                    if end_time < cutoff_time:
                        continue
                    
                    # Skip if already confirmed
                    if auction.confirmed_winner:
                        continue
                    
                    # Verify from Nano wallet
                    if auction.auction_nano_address:
                        verified = await self._verify_from_nano_wallet(
                            auction.item_id,
                            auction.auction_nano_address
                        )
                        if verified:
                            verified_items.append(auction.item_id)
                
                except Exception as e:
                    print(f"Error verifying auction {auction.item_id}: {e}")
            
            return verified_items
        except Exception as e:
            print(f"Error in verify_recent_auctions: {e}")
            return []
    
    async def _verify_from_nano_wallet(self, item_id: str, nano_address: str) -> bool:
        """
        Verify auction winner from Nano wallet transaction history.
        
        Args:
            item_id: The auction item ID
            nano_address: The auction's Nano wallet address
            
        Returns:
            True if verified successfully
        """
        try:
            account_info = await self.blockchain.nano_client.get_account_info(nano_address)
            
            if not account_info:
                return False
            
            # Parse transaction history to find highest bid
            # In real implementation, would parse frontier blocks
            # For now, use data from master post
            
            auction = arweave_post_service.master_post_data['auctions'].get(item_id)
            if not auction or not auction.current_bidder:
                return False
            
            # Increment confirmation count
            if item_id not in self.confirmation_records:
                self.confirmation_records[item_id] = {
                    'confirmations': 0,
                    'last_verified': None,
                    'winner': auction.current_bidder,
                    'winning_bid': auction.current_bid_usdc  # Testing database implementation
                }
            
            record = self.confirmation_records[item_id]
            record['confirmations'] += 1
            record['last_verified'] = datetime.now(timezone.utc).isoformat()
            
            # Mark as confirmed after 3 confirmations across posts
            if record['confirmations'] >= 3:
                auction.confirmed_winner = True
                auction.confirmation_count = record['confirmations']
                print(f"Auction {item_id} confirmed with {record['confirmations']} verifications")
                return True
            
            return True
        except Exception as e:
            print(f"Error verifying from Nano wallet: {e}")
            return False
    
    async def discover_and_aggregate_posts(self, user: User, 
                                          search_tags: Optional[Dict[str, str]] = None) -> List[str]:
        """
        Discover all Arweave posts matching criteria and aggregate into master list.
        Uses algorithm to recursively gather posts and link them together.
        
        Args:
            user: User whose posts to discover
            search_tags: Optional tags to filter posts (e.g., {'Data-Type': 'auction-master-post'})
            
        Returns:
            List of discovered post transaction IDs
        """
        try:
            if not user.arweave_address:
                return []
            
            discovered_posts = []
            visited_posts: Set[str] = set()
            to_visit: List[str] = []
            
            # If we have a known master post, start from there
            if arweave_post_service.master_post_tx_id:
                to_visit.append(arweave_post_service.master_post_tx_id)
            
            # Iteratively visit posts and find references to other posts
            while to_visit:
                tx_id = to_visit.pop(0)
                
                if tx_id in visited_posts:
                    continue
                
                visited_posts.add(tx_id)
                
                # Load post data
                post_data = await self.blockchain.arweave_client.retrieve_data(tx_id)
                if not post_data:
                    continue
                
                discovered_posts.append(tx_id)
                self.arweave_posts[tx_id] = post_data
                
                # Look for references to other posts in the data
                referenced_posts = self._extract_post_references(post_data)
                for ref_tx_id in referenced_posts:
                    if ref_tx_id not in visited_posts:
                        to_visit.append(ref_tx_id)
            
            print(f"Discovered {len(discovered_posts)} Arweave posts")
            return discovered_posts
        except Exception as e:
            print(f"Error discovering posts: {e}")
            return []
    
    def _extract_post_references(self, data: Dict[str, Any]) -> List[str]:
        """
        Extract references to other Arweave posts from post data.
        Looks for transaction IDs in the format of 43-char base64url strings.
        
        Args:
            data: The post data to search
            
        Returns:
            List of found transaction IDs
        """
        import re
        
        refs = []
        tx_id_pattern = r'[A-Za-z0-9_-]{43}'
        
        # Serialize to string and search
        data_str = str(data)
        matches = re.findall(tx_id_pattern, data_str)
        
        for match in matches:
            if self.blockchain.arweave_client.validate_transaction_id(match):
                refs.append(match)
        
        return refs
    
    async def aggregate_posts_into_master(self, discovered_posts: List[str]) -> bool:
        """
        Aggregate all discovered posts into a unified master view.
        Merges auction data from all posts, handling conflicts by using latest data.
        
        Args:
            discovered_posts: List of post transaction IDs to aggregate
            
        Returns:
            True if aggregation successful
        """
        try:
            aggregated_auctions = {}
            
            # Process posts in order (oldest to newest if we can determine)
            for tx_id in discovered_posts:
                if tx_id not in self.arweave_posts:
                    continue
                
                post_data = self.arweave_posts[tx_id]
                auctions = post_data.get('auctions', {})
                
                for item_id, auction_data in auctions.items():
                    if item_id not in aggregated_auctions:
                        aggregated_auctions[item_id] = auction_data
                    else:
                        # Merge: use newer data based on updated_at
                        existing = aggregated_auctions[item_id]
                        
                        try:
                            existing_time = datetime.fromisoformat(
                                existing.get('updated_at', '').replace('Z', '+00:00')
                            )
                            new_time = datetime.fromisoformat(
                                auction_data.get('updated_at', '').replace('Z', '+00:00')
                            )
                            
                            if new_time > existing_time:
                                aggregated_auctions[item_id] = auction_data
                        except (ValueError, KeyError):
                            # If can't compare times, keep existing
                            pass
            
            # Update master post with aggregated data
            arweave_post_service.master_post_data['auctions'] = aggregated_auctions
            arweave_post_service.master_post_data['aggregated_from'] = discovered_posts
            arweave_post_service.master_post_data['aggregation_time'] = datetime.now(timezone.utc).isoformat()
            
            print(f"Aggregated {len(aggregated_auctions)} auctions from {len(discovered_posts)} posts")
            return True
        except Exception as e:
            print(f"Error aggregating posts: {e}")
            return False
    
    async def build_master_post_from_chain(self, user: User) -> Optional[str]:
        """
        Build and post a complete master post by discovering and aggregating all auctions.
        This handles the case where Arweave posts can't be appended to.
        
        Args:
            user: User creating the master post
            
        Returns:
            New master post transaction ID or None
        """
        try:
            print("Starting chain discovery and aggregation...")
            
            # Discover all posts
            discovered = await self.discover_and_aggregate_posts(user)
            if not discovered:
                print("No posts discovered, using current master post")
            else:
                print(f"Discovered {len(discovered)} posts")
                
                # Aggregate all data
                await self.aggregate_posts_into_master(discovered)
            
            # Post aggregated data to Arweave
            success, message, tx_id = await self._post_aggregated_master(user)
            
            if success and tx_id:
                print(f"New master post created: {tx_id}")
                return tx_id
            else:
                print(f"Failed to post master: {message}")
                return None
        except Exception as e:
            print(f"Error building master post: {e}")
            return None
    
    async def _post_aggregated_master(self, user: User, ar_cost: float = 0.05) -> Tuple[bool, str, Optional[str]]:
        """
        Post the aggregated master post to Arweave.
        
        Args:
            user: User posting
            ar_cost: AR cost for posting
            
        Returns:
            Tuple of (success, message, tx_id)
        """
        try:
            if not user.arweave_address:
                return False, "User has no Arweave address", None
            
            balance_winston = await self.blockchain.arweave_client.get_balance(user.arweave_address)
            if balance_winston is None:
                return False, "Could not retrieve AR balance", None
            
            balance_ar = self.blockchain.arweave_client.winston_to_ar(balance_winston)
            
            if balance_ar < ar_cost:
                return False, f"Insufficient AR. Need {ar_cost}, have {balance_ar:.6f}", None
            
            # Post to Arweave
            tx_id = await arweave_post_service.post_master_to_arweave(user, ar_cost)
            
            if tx_id:
                return True, f"Master post aggregated and posted: {tx_id}", tx_id
            else:
                return False, "Failed to post aggregated master", None
        except Exception as e:
            return False, f"Error posting: {str(e)}", None
    
    def get_confirmation_status(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get confirmation status for an auction."""
        return self.confirmation_records.get(item_id)
    
    def get_all_confirmations(self) -> Dict[str, Dict[str, Any]]:
        """Get all confirmation records."""
        return self.confirmation_records


# Global verification service instance
auction_verification_service = AuctionVerificationService()
