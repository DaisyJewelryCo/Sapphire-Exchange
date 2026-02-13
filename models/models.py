"""
Data models for the Sapphire Exchange auction platform.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import uuid

@dataclass
class User:
    """Represents a user in the system."""
    username: str
    password_hash: str
    nano_address: str
    arweave_address: str
    email: Optional[str] = None
    usdc_address: Optional[str] = None
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: Optional[str] = None
    last_login: Optional[str] = None
    
    is_active: bool = True
    reputation_score: float = 0.0
    total_sales: int = 0
    total_purchases: int = 0
    bid_credits: float = 0.0
    
    arweave_profile_uri: Optional[str] = None
    arweave_inventory_uri: Optional[str] = None
    data_hash: Optional[str] = None
    
    bio: str = ""
    location: str = ""
    website: str = ""
    avatar_url: Optional[str] = None
    
    inventory: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    preferences: Dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert user to dictionary for storage."""
        return {
            'id': self.id,
            'username': self.username,
            'password_hash': self.password_hash,
            'nano_address': self.nano_address,
            'arweave_address': self.arweave_address,
            'email': self.email,
            'usdc_address': self.usdc_address,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'last_login': self.last_login,
            'is_active': self.is_active,
            'reputation_score': self.reputation_score,
            'total_sales': self.total_sales,
            'total_purchases': self.total_purchases,
            'bid_credits': self.bid_credits,
            'arweave_profile_uri': self.arweave_profile_uri,
            'arweave_inventory_uri': self.arweave_inventory_uri,
            'data_hash': self.data_hash,
            'bio': self.bio,
            'location': self.location,
            'website': self.website,
            'avatar_url': self.avatar_url,
            'inventory': self.inventory,
            'metadata': self.metadata,
            'preferences': self.preferences
        }
    
    def calculate_data_hash(self) -> str:
        """Calculate hash of user data for integrity checking."""
        import hashlib
        data_str = f"{self.id}{self.username}{self.created_at}{self.reputation_score}"
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        """Create User from dictionary."""
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            username=data['username'],
            password_hash=data['password_hash'],
            nano_address=data['nano_address'],
            arweave_address=data['arweave_address'],
            email=data.get('email'),
            usdc_address=data.get('usdc_address'),
            created_at=data.get('created_at', datetime.now(timezone.utc).isoformat()),
            updated_at=data.get('updated_at'),
            last_login=data.get('last_login'),
            is_active=data.get('is_active', True),
            reputation_score=data.get('reputation_score', 0.0),
            total_sales=data.get('total_sales', 0),
            total_purchases=data.get('total_purchases', 0),
            bid_credits=data.get('bid_credits', 0.0),
            arweave_profile_uri=data.get('arweave_profile_uri'),
            arweave_inventory_uri=data.get('arweave_inventory_uri'),
            data_hash=data.get('data_hash'),
            bio=data.get('bio', ''),
            location=data.get('location', ''),
            website=data.get('website', ''),
            avatar_url=data.get('avatar_url'),
            inventory=data.get('inventory', []),
            metadata=data.get('metadata', {}),
            preferences=data.get('preferences', {})
        )

@dataclass
class Item:
    """Represents an item in the system."""
    seller_id: str
    title: str
    description: str
    starting_price_usdc: str = "0.0"
    auction_end: Optional[str] = None
    status: str = "draft"
    tags: List[str] = field(default_factory=list)
    category: str = ""
    shipping_required: bool = False
    shipping_cost_usdc: str = "0.0"
    
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    item_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    sha_id: str = ""
    
    current_bid_usdc: Optional[str] = None
    current_bidder_id: Optional[str] = None
    
    auction_nano_address: str = ""
    auction_nano_public_key: str = ""
    auction_nano_private_key: str = ""
    auction_nano_seed: str = ""
    auction_wallet_created_at: Optional[str] = None
    
    arweave_metadata_uri: Optional[str] = None
    arweave_confirmed: bool = False
    
    data_hash: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        """Generate SHA hash-based secondary ID and data hash."""
        if not self.sha_id:
            self.sha_id = self._generate_sha_id()
        self.data_hash = self.calculate_data_hash()
    
    def _generate_sha_id(self) -> str:
        """Generate SHA256 hash-based secondary ID from item information.
        
        This serves as the item's second ID for integrity verification and deduplication.
        """
        import hashlib
        hash_data = f"{self.seller_id}{self.title}{self.description}{self.created_at}"
        return hashlib.sha256(hash_data.encode()).hexdigest()
    
    @property
    def id(self) -> str:
        """Alias for item_id for backward compatibility."""
        return self.item_id
    
    def is_ended(self) -> bool:
        """Check if auction has ended."""
        if not self.auction_end:
            return False
        from datetime import datetime, timezone
        try:
            end_time = datetime.fromisoformat(self.auction_end.replace('Z', '+00:00'))
            return datetime.now(timezone.utc) > end_time
        except:
            return False
    
    def calculate_data_hash(self) -> str:
        """Calculate hash of item data for integrity checking.
        Uses the same data as item_id generation for verification.
        """
        import hashlib
        data_str = f"{self.seller_id}{self.title}{self.description}{self.created_at}"
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def verify_integrity(self) -> Tuple[bool, str]:
        """Verify item integrity by checking if sha_id matches the hash of item information.
        
        Returns:
            Tuple of (is_valid, message)
        """
        calculated_hash = self.calculate_data_hash()
        if self.sha_id == calculated_hash:
            return True, "Item integrity verified: SHA ID matches data hash"
        else:
            return False, f"Item integrity check failed: SHA ID {self.sha_id} does not match calculated hash {calculated_hash}"
    
    def to_dict(self) -> dict:
        """Convert item to dictionary for storage."""
        return {
            'item_id': self.item_id,
            'sha_id': self.sha_id,
            'seller_id': self.seller_id,
            'title': self.title,
            'description': self.description,
            'starting_price_usdc': self.starting_price_usdc,
            'auction_end': self.auction_end,
            'status': self.status,
            'tags': self.tags,
            'category': self.category,
            'shipping_required': self.shipping_required,
            'shipping_cost_usdc': self.shipping_cost_usdc,
            'created_at': self.created_at,
            'current_bid_usdc': self.current_bid_usdc,
            'current_bidder_id': self.current_bidder_id,
            'auction_nano_address': self.auction_nano_address,
            'auction_nano_public_key': self.auction_nano_public_key,
            'auction_nano_private_key': self.auction_nano_private_key,
            'auction_nano_seed': self.auction_nano_seed,
            'auction_wallet_created_at': self.auction_wallet_created_at,
            'arweave_metadata_uri': self.arweave_metadata_uri,
            'arweave_confirmed': self.arweave_confirmed,
            'data_hash': self.data_hash,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Item':
        """Create Item from dictionary."""
        return cls(
            item_id=data.get('item_id', str(uuid.uuid4())),
            sha_id=data.get('sha_id', ''),
            seller_id=data.get('seller_id', ''),
            title=data.get('title', data.get('name', '')),
            description=data.get('description', ''),
            starting_price_usdc=str(data.get('starting_price_usdc', data.get('starting_price', '0.0'))),
            auction_end=data.get('auction_end', data.get('auction_end_time')),
            status=data.get('status', 'draft'),
            tags=data.get('tags', []),
            category=data.get('category', ''),
            shipping_required=data.get('shipping_required', False),
            shipping_cost_usdc=str(data.get('shipping_cost_usdc', '0.0')),
            created_at=data.get('created_at', datetime.now(timezone.utc).isoformat()),
            current_bid_usdc=data.get('current_bid_usdc', data.get('current_bid')),
            current_bidder_id=data.get('current_bidder_id', data.get('current_bidder')),
            auction_nano_address=data.get('auction_nano_address', ''),
            auction_nano_public_key=data.get('auction_nano_public_key', ''),
            auction_nano_private_key=data.get('auction_nano_private_key', ''),
            auction_nano_seed=data.get('auction_nano_seed', ''),
            auction_wallet_created_at=data.get('auction_wallet_created_at'),
            arweave_metadata_uri=data.get('arweave_metadata_uri'),
            arweave_confirmed=data.get('arweave_confirmed', False),
            data_hash=data.get('data_hash'),
            metadata=data.get('metadata', {})
        )

@dataclass
class Bid:
    """Represents a bid on an auction item."""
    bid_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    item_id: str = ""
    bidder_public_key: str = ""
    amount: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> dict:
        """Convert bid to dictionary for storage."""
        return {
            'bid_id': self.bid_id,
            'item_id': self.item_id,
            'bidder_public_key': self.bidder_public_key,
            'amount': self.amount,
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Bid':
        """Create Bid from dictionary."""
        return cls(
            bid_id=data.get('bid_id', str(uuid.uuid4())),
            item_id=data.get('item_id', ''),
            bidder_public_key=data.get('bidder_public_key', ''),
            amount=data.get('amount', 0.0),
            timestamp=data.get('timestamp', datetime.now(timezone.utc).isoformat())
        )

@dataclass
class Auction:
    """Represents an auction in the system."""
    auction_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    item_id: str = ""
    seller_public_key: str = ""
    starting_price: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    duration_hours: float = 24.0
    end_time: Optional[str] = None
    
    current_bid: Optional[float] = None
    current_bidder: Optional[str] = None
    bids: List[dict] = field(default_factory=list)
    
    is_active: bool = True
    winner_public_key: Optional[str] = None
    settled: bool = False
    
    def to_dict(self) -> dict:
        """Convert auction to dictionary for storage."""
        return {
            'auction_id': self.auction_id,
            'item_id': self.item_id,
            'seller_public_key': self.seller_public_key,
            'starting_price': self.starting_price,
            'created_at': self.created_at,
            'duration_hours': self.duration_hours,
            'end_time': self.end_time,
            'current_bid': self.current_bid,
            'current_bidder': self.current_bidder,
            'bids': self.bids,
            'is_active': self.is_active,
            'winner_public_key': self.winner_public_key,
            'settled': self.settled
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Auction':
        """Create Auction from dictionary."""
        return cls(
            auction_id=data.get('auction_id', str(uuid.uuid4())),
            item_id=data.get('item_id', ''),
            seller_public_key=data.get('seller_public_key', ''),
            starting_price=data.get('starting_price', 0.0),
            created_at=data.get('created_at', datetime.now(timezone.utc).isoformat()),
            duration_hours=data.get('duration_hours', 24.0),
            end_time=data.get('end_time'),
            current_bid=data.get('current_bid'),
            current_bidder=data.get('current_bidder'),
            bids=data.get('bids', []),
            is_active=data.get('is_active', True),
            winner_public_key=data.get('winner_public_key'),
            settled=data.get('settled', False)
        )
    
    def is_ended(self) -> bool:
        """Check if the auction has ended."""
        if not self.end_time:
            return False
        end_time = datetime.fromisoformat(self.end_time.replace('Z', '+00:00'))
        return datetime.now(timezone.utc) > end_time
