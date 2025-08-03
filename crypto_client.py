"""
Unified cryptocurrency client for Sapphire Exchange.
Handles Dogecoin as the main currency with Nano/Arweave backend.
"""
import asyncio
import json
from typing import Dict, Any, Optional, List, Union
from dataclasses import asdict

from dogecoin_utils import DogecoinWallet, DogecoinRPC
from nano_utils_real import NanoWallet, NanoRPC
from arweave_utils_real import ArweaveClient
from blockchain_config import config
from models import User, Item, Auction

class CryptoClient:
    """
    Unified client for handling all cryptocurrency operations in Sapphire Exchange.
    Uses Dogecoin as the main currency with Nano/Arweave as backend.
    """
    
    def __init__(self, doge_wallet: Optional[DogecoinWallet] = None, 
                nano_wallet: Optional[NanoWallet] = None,
                arweave_client: Optional[ArweaveClient] = None):
        """Initialize the crypto client.
        
        Args:
            doge_wallet: Optional Dogecoin wallet instance
            nano_wallet: Optional Nano wallet instance
            arweave_client: Optional Arweave client instance
        """
        # Initialize Dogecoin (main currency)
        self.doge_wallet = doge_wallet or DogecoinWallet(network=config.dogecoin_network)
        self.doge_rpc = DogecoinRPC(
            rpc_user=config.dogecoin_rpc_user,
            rpc_password=config.dogecoin_rpc_password,
            rpc_host=config.dogecoin_rpc_host,
            rpc_port=config.dogecoin_rpc_port,
            network=config.dogecoin_network
        )
        
        # Initialize Nano (backend)
        self.nano_wallet = nano_wallet or NanoWallet(node_url=config.nano_node_url)
        self.nano_rpc = NanoRPC(node_url=config.nano_node_url)
        
        # Initialize Arweave (backend)
        self.arweave = arweave_client or ArweaveClient(node_url=config.arweave_node_url)
        
        # User data
        self.current_user = None
        self.user_data = None
    
    async def initialize(self, seed_phrase: str = None) -> bool:
        """Initialize the client with an optional seed phrase.
        
        Args:
            seed_phrase: Optional seed phrase for deterministic wallet generation
            
        Returns:
            bool: True if initialization was successful
        """
        try:
            # Initialize Dogecoin wallet from seed if provided
            if seed_phrase:
                self.doge_wallet = DogecoinWallet.from_seed(seed_phrase, network=config.dogecoin_network)
            
            # Initialize Nano wallet from the same seed for consistency
            self.nano_wallet = await self._get_or_create_nano_wallet(seed_phrase)
            
            # Load or create user data
            await self._load_user_data()
            
            return True
            
        except Exception as e:
            print(f"Failed to initialize crypto client: {e}")
            return False
    
    async def _get_or_create_nano_wallet(self, seed_phrase: str = None) -> NanoWallet:
        """Get or create a Nano wallet, optionally from a seed phrase."""
        if seed_phrase:
            return await NanoWallet.from_seed(seed_phrase, node_url=config.nano_node_url)
        return NanoWallet(node_url=config.nano_node_url)
    
    async def _load_user_data(self) -> bool:
        """Load user data from Arweave."""
        if not self.doge_wallet or not hasattr(self.doge_wallet, 'address'):
            return False
            
        try:
            # Try to load user data from Arweave using Dogecoin address as identifier
            user_data = await self.arweave.get_data(self.doge_wallet.address)
            
            if user_data:
                self.user_data = User.from_dict(user_data)
                self.current_user = self.user_data
                return True
                
            # Create new user data if none exists
            self.user_data = User(
                public_key=self.doge_wallet.address,
                username=f"user_{self.doge_wallet.address[:8]}",
                created_at=asdict(datetime.now(timezone.utc).isoformat())
            )
            
            # Save new user data
            await self._save_user_data()
            return True
            
        except Exception as e:
            print(f"Error loading user data: {e}")
            return False
    
    async def _save_user_data(self) -> bool:
        """Save user data to Arweave."""
        if not self.user_data or not self.doge_wallet:
            return False
            
        try:
            # Store user data on Arweave using Dogecoin address as key
            tx_id = await self.arweave.store_data(
                asdict(self.user_data),
                wallet=self.doge_wallet
            )
            return bool(tx_id)
            
        except Exception as e:
            print(f"Error saving user data: {e}")
            return False
    
    # Dogecoin methods (main currency)
    async def get_doge_balance(self) -> float:
        """Get the Dogecoin balance."""
        return await self.doge_rpc.get_balance()
    
    async def send_doge(self, address: str, amount: float) -> Optional[str]:
        """Send Dogecoin to an address."""
        return await self.doge_rpc.send_to_address(address, amount)
    
    async def get_doge_address(self) -> str:
        """Get the current Dogecoin address."""
        return self.doge_wallet.address
    
    # Nano methods (backend)
    async def get_nano_balance(self) -> int:
        """Get the Nano balance (used for backend operations)."""
        if not self.nano_wallet:
            return 0
        return await self.nano_wallet.get_balance()
    
    # Item and auction methods
    async def create_item(self, item_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new item for sale."""
        if not self.user_data:
            return None
            
        try:
            # Store item data on Arweave
            item = Item(
                **item_data,
                owner=self.doge_wallet.address,
                created_at=datetime.now(timezone.utc).isoformat(),
                status='active'
            )
            
            tx_id = await self.arweave.store_data(asdict(item), self.doge_wallet)
            if not tx_id:
                return None
                
            # Update user's inventory
            if not hasattr(self.user_data, 'inventory'):
                self.user_data.inventory = []
            self.user_data.inventory.append(tx_id)
            
            # Save updated user data
            await self._save_user_data()
            
            return {
                'id': tx_id,
                **asdict(item)
            }
            
        except Exception as e:
            print(f"Error creating item: {e}")
            return None
    
    async def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get an item by ID."""
        try:
            item_data = await self.arweave.get_data(item_id)
            if not item_data:
                return None
                
            # Convert to Item and back to dict to ensure all fields are present
            item = Item.from_dict(item_data)
            return {
                'id': item_id,
                **asdict(item)
            }
            
        except Exception as e:
            print(f"Error getting item: {e}")
            return None
    
    async def create_auction(self, item_id: str, starting_price: float, 
                           duration_hours: int = 24) -> Optional[Dict[str, Any]]:
        """Create a new auction for an item."""
        # Get the item
        item = await self.get_item(item_id)
        if not item or item['owner'] != self.doge_wallet.address:
            return None
            
        try:
            # Create auction
            auction = Auction(
                item_id=item_id,
                seller_public_key=self.doge_wallet.address,
                starting_price=starting_price,
                duration_hours=duration_hours,
                end_time=(datetime.now(timezone.utc) + 
                         timedelta(hours=duration_hours)).isoformat()
            )
            
            # Store auction on Arweave
            auction_data = asdict(auction)
            tx_id = await self.arweave.store_data(auction_data, self.doge_wallet)
            
            if not tx_id:
                return None
                
            return {
                'id': tx_id,
                **auction_data
            }
            
        except Exception as e:
            print(f"Error creating auction: {e}")
            return None
    
    async def place_bid(self, auction_id: str, amount: float) -> bool:
        """Place a bid on an auction."""
        # This is a simplified version - in a real app, you'd want to:
        # 1. Verify the auction is still active
        # 2. Check that the bid is higher than current bid
        # 3. Potentially lock funds in escrow
        try:
            # Get auction data
            auction_data = await self.arweave.get_data(auction_id)
            if not auction_data:
                return False
                
            # Create bid
            bid = {
                'bidder': self.doge_wallet.address,
                'amount': amount,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Add bid to auction
            if 'bids' not in auction_data:
                auction_data['bids'] = []
            auction_data['bids'].append(bid)
            
            # Update auction
            await self.arweave.store_data(auction_data, self.doge_wallet)
            return True
            
        except Exception as e:
            print(f"Error placing bid: {e}")
            return False
