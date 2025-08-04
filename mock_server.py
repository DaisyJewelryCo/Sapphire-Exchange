"""
Mock servers for Nano and Arweave to simulate blockchain operations.
"""
import json
import os
import asyncio
import time
import random
from typing import Dict, List, Optional, Any, Callable, Awaitable
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

# Import MOCK_MODE from nano_utils
from nano_utils import MOCK_MODE
import random
import string
import hashlib

# Simulate network latency (in seconds)
MIN_LATENCY = 0.1  # 100ms
MAX_LATENCY = 0.5  # 500ms

# Simulate blockchain confirmation times (in seconds)
CONFIRMATION_DELAY = 2.0

def simulate_latency():
    """Simulate network latency."""
    time.sleep(random.uniform(MIN_LATENCY, MAX_LATENCY))

async def async_simulate_latency():
    """Simulate async network latency."""
    await asyncio.sleep(random.uniform(MIN_LATENCY, MAX_LATENCY))

def generate_tx_id() -> str:
    """Generate a realistic-looking transaction ID."""
    return hashlib.sha256(os.urandom(32)).hexdigest()

def generate_nano_address() -> str:
    """Generate a realistic-looking Nano address."""
    prefix = 'nano_'
    chars = '13456789abcdefghijkmnopqrstuwxyz'
    return prefix + ''.join(random.choices(chars, k=60))

def generate_arweave_tx_id() -> str:
    """Generate a realistic-looking Arweave transaction ID."""
    chars = 'abcdefghijklmnopqrstuvwxyz0123456789_-'
    return ''.join(random.choices(chars, k=43))

@dataclass
class ArweaveTransaction:
    """Mock Arweave transaction class for testing purposes."""
    id: str
    data: Dict[str, Any]
    status: str = 'pending'
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    block_height: Optional[int] = None
    confirmations: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert transaction to dictionary."""
        return {
            'id': self.id,
            'data': self.data,
            'status': self.status,
            'timestamp': self.timestamp,
            'block_height': self.block_height,
            'confirmations': self.confirmations
        }
        
    @classmethod
    def get_transaction(cls, transaction_id: str) -> 'ArweaveTransaction':
        """
        Retrieve a transaction by its ID from the mock database.
        
        Args:
            transaction_id: The ID of the transaction to retrieve
            
        Returns:
            ArweaveTransaction: The transaction object if found, None otherwise
        """
        # Import here to avoid circular imports
        from mock_server import arweave_db
        
        # Check pending transactions first
        if transaction_id in arweave_db.pending_transactions:
            tx_data = arweave_db.pending_transactions[transaction_id]
            return cls(
                id=tx_data['id'],
                data=tx_data['data'],
                status=tx_data['status'],
                timestamp=tx_data['timestamp'],
                block_height=tx_data['block_height'],
                confirmations=tx_data['confirmations']
            )
            
        # Check confirmed items
        if transaction_id in arweave_db.items:
            item_data = arweave_db.items[transaction_id]
            return cls(
                id=transaction_id,
                data=item_data,
                status='confirmed',
                block_height=1,  # Mock block height
                confirmations=6  # Mock confirmations
            )
            
        # If not found in either, return None
        return None

@dataclass
class MockArweaveDB:
    """Mock Arweave database for storing items and user data with realistic behavior."""
    items: Dict[str, dict] = field(default_factory=dict)  # tx_id -> item_data
    user_data: Dict[str, dict] = field(default_factory=dict)  # public_key -> user_data
    pending_transactions: Dict[str, dict] = field(default_factory=dict)  # tx_id -> tx_data
    _background_tasks: set = field(default_factory=set, init=False)
    
    def __post_init__(self):
        # Initialize with some test data
        # The actual test data is initialized by the global initialize_test_data() function
        pass
        
    def __del__(self):
        # Cancel all background tasks when the instance is destroyed
        for task in self._background_tasks:
            if not task.done():
                task.cancel()
        self._background_tasks.clear()
    
    def _simulate_network(self):
        """Simulate network operations."""
        simulate_latency()
    
    def store_data(self, data: dict) -> str:
        """Store data and return a mock transaction ID with simulated confirmation."""
        self._simulate_network()
        
        # Create a pending transaction
        tx_id = f"arweave_{generate_arweave_tx_id()}"
        self.pending_transactions[tx_id] = {
            'id': tx_id,
            'data': data,
            'status': 'pending',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'block_height': None,
            'confirmations': 0
        }
        
        # Simulate confirmation after delay
        task = asyncio.create_task(self._confirm_transaction(tx_id))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        
        return tx_id
    
    async def _confirm_transaction(self, tx_id: str) -> None:
        """Simulate transaction confirmation after a delay."""
        await asyncio.sleep(CONFIRMATION_DELAY)
        if tx_id in self.pending_transactions:
            tx = self.pending_transactions[tx_id]
            tx['status'] = 'confirmed'
            tx['block_height'] = random.randint(1_000_000, 2_000_000)
            tx['confirmations'] = 1
            
            # Move to confirmed items if it's an item
            if 'name' in tx['data']:  # This is an item
                self.items[tx_id] = tx['data']
                print(f"[MOCK] Item {tx_id} confirmed and added to marketplace")
    
    async def get_data(self, tx_id: str) -> Optional[dict]:
        """Retrieve data by transaction ID with simulated latency."""
        self._simulate_network()
        
        # Check pending transactions first
        if tx_id in self.pending_transactions:
            tx = self.pending_transactions[tx_id]
            # In mock mode, return data immediately even if not confirmed
            if MOCK_MODE or tx['status'] == 'confirmed':
                if 'name' in tx['data']:  # This is an item
                    return tx['data']
        
        # Then check confirmed items
        if tx_id in self.items:
            return self.items[tx_id]
            
        # If we got here, the item wasn't found
        print(f"[MOCK] Item {tx_id} not found in pending or confirmed items")
        return None
    
    def store_user_data(self, public_key: str, user_data: dict) -> str:
        """Store user data with simulated confirmation."""
        self._simulate_network()
        
        # In a real Arweave implementation, this would be a transaction
        self.user_data[public_key] = user_data
        
        # Return a fake transaction ID
        return f"user_tx_{generate_arweave_tx_id()}"
        
    async def get_items_by_owner(self, public_key) -> List[dict]:
        """Get all items owned by a specific public key.
        
        Args:
            public_key: The public key of the owner (can be a string or VerifyingKey object)
            
        Returns:
            List[dict]: List of items owned by the public key
        """
        await asyncio.sleep(0.1)  # Simulate network delay
        
        # Convert public_key to string if it's a VerifyingKey object
        if hasattr(public_key, 'to_string'):
            public_key_str = public_key.to_string().hex()
        else:
            public_key_str = str(public_key)
        
        # Get items from both pending and confirmed transactions
        all_items = []
        
        # Check pending transactions
        for tx_id, tx in self.pending_transactions.items():
            tx_data = tx.get('data', {})
            # Check both 'owner' and 'owner_public_key' fields for compatibility
            owner_key = tx_data.get('owner') or tx_data.get('owner_public_key')
            if owner_key is not None:
                # Convert owner_key to string for comparison
                owner_key_str = owner_key.to_string().hex() if hasattr(owner_key, 'to_string') else str(owner_key)
                if owner_key_str == public_key_str:
                    all_items.append(tx_data)
        
        # Check confirmed items
        for tx_id, item_data in self.items.items():
            # Check both 'owner' and 'owner_public_key' fields for compatibility
            owner_key = item_data.get('owner') or item_data.get('owner_public_key')
            if owner_key is not None:
                # Convert owner_key to string for comparison
                owner_key_str = owner_key.to_string().hex() if hasattr(owner_key, 'to_string') else str(owner_key)
                if owner_key_str == public_key_str:
                    all_items.append(item_data)
        
        # Safely format the public key for logging
        log_key = public_key_str[:8] if isinstance(public_key_str, str) and len(public_key_str) > 8 else public_key_str
        print(f"[MOCK] Found {len(all_items)} items for public key {log_key}...")
        print(f"[DEBUG] Items found: {all_items}")
        return all_items
    
    async def get_user_data(self, public_key: str) -> Optional[dict]:
        """Retrieve user data by public key with simulated latency."""
        self._simulate_network()
        return self.user_data.get(public_key)
    
    async def query_items(self, owner: str = None) -> List[dict]:
        """Query items with optional owner filter."""
        self._simulate_network()
        
        # Get all confirmed items
        items = list(self.items.values())
        
        # Filter by owner if specified
        if owner:
            items = [item for item in items if item.get('owner') == owner]
        
        # Sort by timestamp (newest first)
        items.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return items

@dataclass
class MockNanoDB:
    """Mock Nano database for tracking balances and transactions with realistic behavior."""
    accounts: Dict[str, float] = field(default_factory=dict)  # address -> balance
    pending_blocks: Dict[str, dict] = field(default_factory=dict)  # block_hash -> block_data
    confirmed_blocks: Dict[str, dict] = field(default_factory=dict)  # block_hash -> block_data
    accounts_pending: Dict[str, List[dict]] = field(default_factory=dict)  # account -> [pending_receives]
    
    def _simulate_network(self):
        """Simulate network operations."""
        simulate_latency()
    
    def create_account(self) -> str:
        """Create a new Nano account and return its address with simulated latency."""
        self._simulate_network()
        
        address = generate_nano_address()
        self.accounts[address] = 0.0
        self.accounts_pending[address] = []
        print(f"[MOCK] Created new Nano account: {address}")
        return address
    
    async def get_balance(self, address: str) -> dict:
        """Get balance information for an account with simulated latency."""
        await async_simulate_latency()
        
        if address not in self.accounts:
            raise ValueError(f"Account {address} not found")
            
        pending_balance = sum(tx['amount'] for tx in self.accounts_pending.get(address, []))
        
        return {
            'balance': str(self.accounts[address]),
            'pending': str(pending_balance),
            'receivable': str(pending_balance)
        }
    
    async def send(self, source: str, destination: str, amount: float) -> str:
        """Send Nano from one account to another with simulated confirmation."""
        await async_simulate_latency()
        
        if source not in self.accounts:
            raise ValueError(f"Source account {source} not found")
        if destination not in self.accounts:
            raise ValueError(f"Destination account {destination} not found")
        
        # Check balance (including pending)
        balance = float(await self.get_balance(source))['balance']
        if balance < amount:
            raise ValueError("Insufficient balance")
        
        # Create a pending block
        block_hash = f"{generate_arweave_tx_id()[:64]}"
        block = {
            'hash': block_hash,
            'source': source,
            'destination': destination,
            'amount': amount,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'status': 'pending',
            'subtype': 'send',
            'block_account': source,
            'contents': {
                'type': 'state',
                'account': source,
                'previous': '0' * 64,
                'representative': 'nano_3arg3asgtigerg3fnp8qt6of8fsbq1x7zad8m6f6e3qkmtm6x3qkmtm6x3qkmtm',
                'balance': str(balance - amount),
                'link': destination,
                'link_as_account': destination,
                'signature': '0' * 128,
                'work': '0' * 16
            }
        }
        
        self.pending_blocks[block_hash] = block
        
        # Add to destination's pending transactions
        if destination not in self.accounts_pending:
            self.accounts_pending[destination] = []
        
        self.accounts_pending[destination].append({
            'source': source,
            'amount': amount,
            'hash': block_hash
        })
        
        # Simulate confirmation after delay
        asyncio.create_task(self._confirm_block(block_hash))
        
        return block_hash
    
    async def _confirm_block(self, block_hash: str) -> None:
        """Simulate block confirmation after a delay."""
        await asyncio.sleep(CONFIRMATION_DELAY)
        
        if block_hash in self.pending_blocks:
            block = self.pending_blocks[block_hash]
            block['status'] = 'confirmed'
            block['confirmed_at'] = datetime.now(timezone.utc).isoformat()
            
            # Move to confirmed blocks
            self.confirmed_blocks[block_hash] = block
            del self.pending_blocks[block_hash]
            
            # Update balances
            if block['subtype'] == 'send':
                # In a real node, the receiver would need to publish a receive block
                # Here we'll simulate that automatically
                await self._auto_receive(block)
    
    async def _auto_receive(self, send_block: dict) -> None:
        """Automatically create and confirm receive blocks for testing."""
        source = send_block['source']
        destination = send_block['destination']
        amount = send_block['amount']
        
        # Remove from pending
        self.accounts_pending[destination] = [
            tx for tx in self.accounts_pending.get(destination, [])
            if tx['hash'] != send_block['hash']
        ]
        
        # Update balances
        self.accounts[source] -= amount
        self.accounts[destination] = self.accounts.get(destination, 0) + amount
        
        # Create receive block
        receive_hash = f"{generate_arweave_tx_id()[:64]}"
        receive_block = {
            'hash': receive_hash,
            'source': destination,
            'destination': destination,
            'amount': amount,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'status': 'confirmed',
            'subtype': 'receive',
            'link': send_block['hash'],
            'block_account': destination,
            'contents': {
                'type': 'state',
                'account': destination,
                'previous': '0' * 64,
                'representative': 'nano_3arg3asgtigerg3fnp8qt6of8fsbq1x7zad8m6f6e3qkmtm6x3qkmtm6x3qkmtm',
                'balance': str(self.accounts[destination]),
                'link': send_block['hash'],
                'signature': '0' * 128,
                'work': '0' * 16
            }
        }
        
        self.confirmed_blocks[receive_hash] = receive_block
        print(f"[MOCK] Auto-received {amount} NANO from {source} to {destination}")
    
    async def get_account_history(self, account: str, count: int = 10) -> List[dict]:
        """Get transaction history for an account with simulated latency."""
        await async_simulate_latency()
        
        history = []
        
        # Add pending receives
        for tx in self.accounts_pending.get(account, []):
            history.append({
                'type': 'pending',
                'account': tx['source'],
                'amount': str(tx['amount']),
                'hash': tx['hash'],
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        
        # Add confirmed transactions
        for block in self.confirmed_blocks.values():
            if block['source'] == account or block['destination'] == account:
                history.append({
                    'type': 'send' if block['source'] == account else 'receive',
                    'account': block['destination'] if block['source'] == account else block['source'],
                    'amount': str(block['amount']),
                    'hash': block['hash'],
                    'timestamp': block['timestamp']
                })
        
        # Sort by timestamp (newest first) and limit to count
        history.sort(key=lambda x: x['timestamp'], reverse=True)
        return history[:count]

# Global instances with some initial test data
arweave_db = MockArweaveDB()
nano_db = MockNanoDB()

# Initialize with some test data for demo purposes
async def initialize_test_data_async():
    """Initialize the mock databases with test data asynchronously."""
    # Create some test users
    test_users = [
        {
            'username': 'alice',
            'first_name': 'Alice',
            'last_name': 'Smith',
            'inventory': [],
            'created_at': datetime.now(timezone.utc).isoformat()
        },
        {
            'username': 'bob',
            'first_name': 'Bob',
            'last_name': 'Johnson',
            'inventory': [],
            'created_at': datetime.now(timezone.utc).isoformat()
        }
    ]
    
    # Create some test items
    test_items = [
        {
            'name': 'Rare Collectible',
            'description': 'A very rare collectible item',
            'starting_price': '10.5',
            'current_price': '10.5',
            'owner': 'user_pubkey_0',
            'owner_username': 'alice',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'end_time': (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
            'status': 'active',
            'bids': [],
            'image_url': 'https://via.placeholder.com/300x200?text=Rare+Collectible'
        },
        {
            'name': 'Digital Art',
            'description': 'A unique digital artwork',
            'starting_price': '5.0',
            'current_price': '5.0',
            'owner': 'user_pubkey_1',
            'owner_username': 'bob',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'end_time': (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
            'status': 'active',
            'bids': [],
            'image_url': 'https://via.placeholder.com/300x200?text=Digital+Art'
        },
        {
            'name': 'Vintage Watch',
            'description': 'A beautiful vintage wristwatch',
            'starting_price': '25.0',
            'current_price': '25.0',
            'owner': 'user_pubkey_0',
            'owner_username': 'alice',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'end_time': (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
            'status': 'active',
            'bids': [],
            'image_url': 'https://via.placeholder.com/300x200?text=Vintage+Watch'
        },
        {
            'name': 'Designer Handbag',
            'description': 'Luxury designer handbag',
            'starting_price': '50.0',
            'current_price': '50.0',
            'owner': 'user_pubkey_1',
            'owner_username': 'bob',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'end_time': (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
            'status': 'active',
            'bids': [],
            'image_url': 'https://via.placeholder.com/300x200?text=Designer+Handbag'
        }
    ]
    
    # Store test items
    for item in test_items:
        arweave_db.store_data(item)
        
    # Add test users and items
    for i, user in enumerate(test_users):
        public_key = f"user_pubkey_{i}"
        arweave_db.store_user_data(public_key, user)
        
        # Give each user some Nano
        address = nano_db.create_account()
        nano_db.accounts[address] = 100.0  # 100 NANO starting balance
        
        for j in range(2):  # 2 items per user
            item = test_items[(i * 2 + j) % len(test_items)].copy()
            item['owner'] = public_key
            item['owner_username'] = user['username']
            arweave_db.store_data(item)
            
    print("[MOCK] Initialized test data")

def initialize_test_data():
    """Synchronous wrapper for initializing test data."""
    if __name__ != "__main__":
        # Create a new event loop for initialization
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(initialize_test_data_async())
        finally:
            loop.close()

# Initialize test data when module loads
initialize_test_data()
