"""Sapphire Exchange - Decentralized Client

This client interacts directly with Arweave and Nano networks without relying on a centralized API.
"""
import json
import asyncio
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any

from arweave_utils import ArweaveClient
from nano_utils import NanoWallet, NanoRPC, MOCK_MODE
from models import User, Item, Auction
from mock_servers import arweave_db, nano_db

class DecentralizedClient:
    """Client for interacting with the decentralized Sapphire Exchange."""
    
    def __init__(self, arweave_client: Optional[ArweaveClient] = None, mock_mode: bool = MOCK_MODE):
        """Initialize the DecentralizedClient.
        
        Args:
            arweave_client: Optional ArweaveClient instance
            mock_mode: If True, use mock implementations for testing
        """
        self.mock_mode = mock_mode
        self.user_wallet = None
        self.arweave = ArweaveClient()
        self.nano_rpc = NanoRPC()
        self.user_data = None
        self.current_user = None  # Track the current user
        
    def get_seed_phrase(self) -> Optional[str]:
        """Get the seed phrase for the current wallet.
        
        Returns:
            Optional[str]: The seed phrase as a string, or None if not available
        """
        if not self.user_wallet or not hasattr(self.user_wallet, 'private_key'):
            return None
            
        try:
            # Get the private key as bytes and convert to hex string
            private_key_bytes = self.user_wallet.private_key.to_ascii(encoding='hex')
            return private_key_bytes.decode('utf-8')
        except Exception as e:
            print(f"Error getting seed phrase: {e}")
            return None
            
    async def login(self, seed_phrase: str, username: str = None, 
                   first_name: str = None, last_name: str = None) -> bool:
        """Login with a seed phrase or create a new user.
        
        Args:
            seed_phrase: The seed phrase for the wallet
            username: Username for new user (optional for login, required for new user)
            first_name: User's first name (optional, for new users)
            last_name: User's last name (optional, for new users)
            
        Returns:
            bool: True if login/signup was successful, False otherwise
        """
        try:
            # Derive wallet from seed phrase
            self.user_wallet = NanoWallet.from_seed(seed_phrase, mock_mode=self.mock_mode)
            if not self.user_wallet or not hasattr(self.user_wallet, 'public_key') or not self.user_wallet.public_key:
                raise ValueError("Failed to initialize wallet from seed phrase - missing public key")
                
            # Convert public key to hex string for storage
            public_key_hex = self.user_wallet.public_key.to_ascii(encoding='hex').decode('utf-8')
                
            # Load or create user data
            self.user_data = await self._load_user_data()
            
            if self.user_data is None:
                # New user - create user data
                if not username:
                    raise ValueError("Username is required for new users")
                    
                self.user_data = User(
                    public_key=public_key_hex,  # Store public key as hex string
                    username=username,
                    first_name=first_name or "",
                    last_name=last_name or "",
                    created_at=datetime.now(timezone.utc).isoformat()
                )
                
                # Save new user data
                await self._save_user_data()
                
            # Set current user
            self.current_user = self.user_data
            return True
            
        except Exception as e:
            print(f"Login error: {e}")
            return False
            
    async def initialize_user(self, seed_phrase: str = None, wallet_data: dict = None, 
                           username: str = None, first_name: str = "", last_name: str = "") -> Optional[User]:
        """Initialize a new user or load an existing one.
        
        Args:
            seed_phrase: Optional seed phrase (generates new if not provided)
            wallet_data: Optional wallet data for initialization
            username: User's username (required for new users)
            first_name: User's first name (optional, for new users)
            last_name: User's last name (optional, for new users)
            
        Returns:
            User: The loaded or created user object, or None if failed
            
        Raises:
            ValueError: If neither seed_phrase nor wallet_data is provided and mock mode is off,
                       or if username is not provided for new user
        """
        if seed_phrase is not None:
            # Create a new wallet from the seed phrase
            print(f"Initializing wallet from seed phrase (mock_mode={self.mock_mode}")
            self.user_wallet = NanoWallet.from_seed(seed_phrase)
            
            # Register the wallet in the mock Nano DB if in mock mode
            if self.mock_mode:
                from mock_servers import nano_db
                if self.user_wallet.address not in nano_db.accounts:
                    nano_db.accounts[self.user_wallet.address] = 100.0  # Give new users 100 NANO for testing
                    nano_db.accounts_pending[self.user_wallet.address] = []
                    print(f"[MOCK] Registered Nano account in mock DB: {self.user_wallet.address}")
                    
        elif wallet_data is not None:
            # Initialize wallet from wallet data
            self.user_wallet = NanoWallet.from_dict(wallet_data)
            
            # Ensure the wallet is registered in the mock DB if in mock mode
            if self.mock_mode and hasattr(self.user_wallet, 'address'):
                from mock_servers import nano_db
                if self.user_wallet.address not in nano_db.accounts:
                    nano_db.accounts[self.user_wallet.address] = 0.0
                    nano_db.accounts_pending[self.user_wallet.address] = []
                    print(f"[MOCK] Registered existing Nano account in mock DB: {self.user_wallet.address}")
                    
        elif not self.mock_mode:
            raise ValueError("Either seed_phrase or wallet_data must be provided when not in mock mode")
            
        # Load or create user data
        self.user_data = await self._load_user_data()
        
        if self.user_data is None:
            # New user - create user data
            if not username:
                raise ValueError("Username is required for new users")
                
            self.user_data = User(
                public_key=self.user_wallet.public_key,
                username=username,
                first_name=first_name or "",
                last_name=last_name or "",
                created_at=datetime.now(timezone.utc).isoformat()
            )
            
            # Save new user data
            await self._save_user_data()
            
        # Set current user
        self.current_user = self.user_data
        return self.current_user
        
    async def create_item(
        self,
        name: str,
        description: str,
        starting_price: float,
        duration_hours: int = 24,
        image_data: Optional[bytes] = None,
        metadata: Optional[dict] = None
    ) -> str:
        """Create a new item for auction.
        
        Args:
            name: Name of the item
            description: Description of the item
            starting_price: Starting price in Nano
            duration_hours: Duration of the auction in hours
            image_data: Optional image data for the item
            metadata: Optional additional metadata
            
        Returns:
            str: Transaction ID of the created item
            
        Raises:
            ValueError: If user is not logged in
        """
        if not self.user_wallet or not self.user_data:
            raise ValueError("User not logged in")
            
        # Create item data
        item_data = {
            'name': name,
            'description': description,
            'starting_price': str(starting_price),
            'current_price': str(starting_price),
            'owner': self.user_wallet.public_key.to_ascii(encoding='hex').decode('utf-8'),
            'owner_username': self.user_data.username,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'end_time': (datetime.now(timezone.utc) + timedelta(hours=duration_hours)).isoformat(),
            'status': 'active',
            'bids': [],
            'metadata': metadata or {},
            'image_url': 'https://via.placeholder.com/300x200?text=' + name.replace(' ', '+')
        }
        
        if self.mock_mode:
            # In mock mode, store in the mock database
            tx_id = await arweave_db.store_data(item_data)
            print(f"[MOCK] Created item {name} with ID {tx_id}")
            # Return both the item data and transaction ID
            return item_data, tx_id
            
        # In a real implementation, we would store the item data in Arweave
        tx_id = await self.arweave.store_data(item_data, self.user_wallet)
        # Return both the item data and transaction ID
        return item_data, tx_id
        
    async def place_bid(self, item_tx_id: str, amount: float) -> bool:
        """Place a bid on an item.
        
        Args:
            item_tx_id: Transaction ID of the item
            amount: Bid amount in Nano
            
        Returns:
            bool: True if bid was successful, False otherwise
            
        Raises:
            ValueError: If user is not logged in or item not found
        """
        print(f"[DEBUG] Starting place_bid for item {item_tx_id} with amount {amount}")
        
        if not self.user_wallet or not self.current_user:
            error_msg = "User not logged in"
            print(f"[DEBUG] {error_msg}")
            raise ValueError(error_msg)
            
        # Get item data from Arweave
        print(f"[DEBUG] Fetching item data for {item_tx_id}")
        item_data = await self.arweave.get_data(item_tx_id)
        print(f"[DEBUG] Retrieved item data: {item_data}")
        
        if not item_data:
            error_msg = f"Item not found with ID: {item_tx_id}"
            print(f"[DEBUG] {error_msg}")
            raise ValueError(error_msg)
            
        # Verify auction is still active
        print("[DEBUG] Verifying auction status...")
        try:
            auction_end = datetime.fromisoformat(item_data['end_time'].replace('Z', '+00:00'))
            current_time = datetime.now(timezone.utc)
            print(f"[DEBUG] Current time: {current_time}, Auction end: {auction_end}")
            
            if current_time > auction_end:
                error_msg = "Auction has ended"
                print(f"[DEBUG] {error_msg}")
                raise ValueError(error_msg)
                
            # Verify bid amount is higher than current bid
            current_bid = item_data.get('current_price', item_data['starting_price'])
            current_bid_float = float(current_bid) if isinstance(current_bid, (str, int, float)) else 0.0
            print(f"[DEBUG] Current bid: {current_bid_float}, New bid: {amount}")
            
            if amount <= current_bid_float:
                error_msg = f"Bid must be higher than {current_bid_float}"
                print(f"[DEBUG] {error_msg}")
                raise ValueError(error_msg)
                
            # Create bid transaction
            bid_data = {
                'type': 'bid',
                'item_tx': item_tx_id,
                'bidder': self.user_wallet.public_key,
                'amount': str(amount),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'signature': 'mock_signature'  # In a real implementation, this would be signed
            }
            
            print(f"[DEBUG] Created bid data: {bid_data}")
            
            if self.mock_mode:
                print("[DEBUG] Running in mock mode")
                # In mock mode, update the item in the mock database
                if 'bids' not in item_data:
                    print("[DEBUG] Initializing bids list for item")
                    item_data['bids'] = []
                    
                item_data['bids'].append(bid_data)
                item_data['current_price'] = str(amount)
                item_data['current_bidder'] = self.user_wallet.public_key
                
                # Extend auction time if it's about to end (sniping protection)
                time_remaining = auction_end - datetime.now(timezone.utc)
                print(f"[DEBUG] Time remaining: {time_remaining}")
                
                if time_remaining < timedelta(minutes=5):
                    print("[DEBUG] Extending auction time (sniping protection)")
                    new_end_time = datetime.now(timezone.utc) + timedelta(minutes=10)
                    item_data['end_time'] = new_end_time.isoformat()
                
                # Store the updated item data in the mock database
                print("[DEBUG] Updating item in mock database...")
                
                # Import arweave_db here to avoid circular imports
                from mock_servers import arweave_db
                
                if item_tx_id in arweave_db.pending_transactions:
                    print(f"[DEBUG] Updating pending transaction for {item_tx_id}")
                    arweave_db.pending_transactions[item_tx_id]['data'] = item_data
                    
                if item_tx_id in arweave_db.items:
                    print(f"[DEBUG] Updating confirmed item for {item_tx_id}")
                    arweave_db.items[item_tx_id] = item_data
                    
                print(f"[MOCK] Successfully placed bid of {amount} NANO on item {item_tx_id}")
                return True
                
        except Exception as e:
            print(f"[DEBUG] Error in place_bid: {str(e)}")
            print(f"[DEBUG] Item data: {item_data}")
            import traceback
            traceback.print_exc()
            raise
            
        # In a real implementation, we would store the bid in Arweave
        bid_tx_id = await self.arweave.store_data(bid_data, self.user_wallet)
        
        # Update item with new bid
        if 'bids' not in item_data:
            item_data['bids'] = []
            
        item_data['bids'].append({
            'tx_id': bid_tx_id,
            'bidder': self.user_wallet.public_key,
            'amount': str(amount),
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        item_data['current_price'] = str(amount)
        item_data['current_bidder'] = self.user_wallet.public_key
        
        # Update the item in Arweave with the new bid
        await self.arweave.store_data(item_data, self.user_wallet)
        
        # Extend auction time if it's about to end (sniping protection)
        time_remaining = auction_end - datetime.now(timezone.utc)
        if time_remaining < timedelta(minutes=5):
            new_end_time = datetime.now(timezone.utc) + timedelta(minutes=10)
            item_data['end_time'] = new_end_time.isoformat()
        
        # Update item on Arweave
        await self.arweave.store_data(item_data, item_tx_id)
        
        return True
        
    async def get_item(self, tx_id: str) -> Optional[dict]:
        """Get item data from Arweave.
        
        Args:
            tx_id: Transaction ID of the item
            
        Returns:
            dict: Item data or None if not found
        """
        if self.mock_mode:
            return await arweave_db.get_data(tx_id)
            
        return await self.arweave.get_data(tx_id)
        
    async def get_user_inventory(self, public_key: str = None) -> List[dict]:
        """Get all items owned by a user.
        
        Args:
            public_key: Public key of the user (defaults to current user)
            
        Returns:
            List[dict]: List of items owned by the user
        """
        public_key = public_key or (self.user_wallet.public_key if self.user_wallet else None)
        if not public_key:
            raise ValueError("No public key provided")
            
        if self.mock_mode:
            # In mock mode, get all items from the mock database
            items = await arweave_db.get_items_by_owner(public_key)
            print(f"[DEBUG] Found {len(items)} items for public key {public_key}")
            if not items:
                print(f"[DEBUG] No items found for public key {public_key}")
                print(f"[DEBUG] All items in DB: {arweave_db.items}")
                print(f"[DEBUG] Pending transactions: {arweave_db.pending_transactions}")
            return items
            
        # In a real implementation, you would query Arweave for items owned by this public key
        # This is a simplified version that would need to be expanded with proper Arweave querying
        return []
        
    async def get_balance(self) -> float:
        """Get the current user's Nano balance.
        
        Returns:
            float: The user's current Nano balance
        """
        if not self.user_wallet:
            return 0.0
            
        if self.mock_mode:
            # Get balance from mock Nano DB
            balance_info = await nano_db.get_balance(self.user_wallet.address)
            return float(balance_info['balance'])
            
        # In a real implementation, we would query the Nano network
        return await self.nano_rpc.get_balance(self.user_wallet.address)
        
    async def _load_user_data(self) -> Optional[User]:
        """Load user data from Arweave.
        
        Returns:
            Optional[User]: User object if found, None otherwise
        """
        if not self.user_wallet:
            return None
            
        if self.mock_mode:
            # Convert public key to string for use as dictionary key
            public_key_str = self.user_wallet.public_key.to_ascii(encoding='hex').decode('utf-8')
            user_data = await arweave_db.get_user_data(public_key_str)
            if user_data:
                print(f"[MOCK] Loaded user data for {public_key_str}")
                return User.from_dict(user_data)
            print(f"[MOCK] No user data found for {public_key_str}")
            return None
            
        # In a real implementation, we would query Arweave for the user's data
        # For now, return None to indicate new user
        return None
        
    async def _save_user_data(self) -> str:
        """Save user data to Arweave.
        
        Returns:
            str: Transaction ID of the saved data
            
        Raises:
            ValueError: If user_wallet or user_data is not initialized
        """
        if not self.user_wallet or not self.user_data:
            raise ValueError("User wallet or user data not initialized")
            
        # Ensure public key is set in user_data
        if not self.user_data.public_key and hasattr(self.user_wallet, 'public_key'):
            self.user_data.public_key = self.user_wallet.public_key.to_ascii(encoding='hex').decode('utf-8')
            
        user_dict = self.user_data.to_dict()
        
        if self.mock_mode:
            # Convert public key to string for use as dictionary key
            public_key_str = self.user_wallet.public_key.to_ascii(encoding='hex').decode('utf-8')
            # Store user data in mock Arweave
            tx_id = await arweave_db.store_user_data(public_key_str, user_dict)
            print(f"[MOCK] Saved user data for {public_key_str} (TX: {tx_id})")
            return tx_id
            
        # In a real implementation, we would store the user data in Arweave
        tx_id = await self.arweave.store_data(user_dict, self.user_wallet)
        return tx_id
        
    def get_seed_phrase(self) -> str:
        """Get the seed phrase of the user's wallet.
        
        Returns:
            str: The seed phrase
            
        Raises:
            ValueError: If wallet is not initialized
        """
        if not self.user_wallet:
            raise ValueError("Wallet not initialized")
            
        return self.user_wallet.seed


async def example_usage():
    """Example usage of the DecentralizedClient."""
    client = DecentralizedClient(mock_mode=True)
    
    # Create a new user
    seed_phrase = "test seed phrase"
    username = "testuser"
    first_name = "Test"
    last_name = "User"
    
    # Login or create user
    success = await client.login(seed_phrase, username, first_name, last_name)
    if success:
        print(f"Logged in as {client.current_user.username}")
        
        # Get balance
        balance = await client.get_balance()
        print(f"Balance: {balance} NANO")
        
        # Create an item
        item_id = await client.create_item(
            name="Test Item",
            description="A test item for the Sapphire Exchange",
            starting_price=1.0,
            duration_hours=24
        )
        print(f"Created item with ID: {item_id}")
        
        # Get item details
        item = await client.get_item(item_id)
        print(f"Item details: {item}")
        
        # Get user inventory
        inventory = await client.get_user_inventory()
        print(f"User inventory: {inventory}")
    else:
        print("Login failed")


if __name__ == "__main__":
    asyncio.run(example_usage())
