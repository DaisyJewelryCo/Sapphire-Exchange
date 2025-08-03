"""
Data models for the Sapphire Exchange auction platform.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
import uuid

@dataclass
class User:
    """Represents a user in the system."""
    # Required fields
    public_key: str  # Nano public key as user ID
    username: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    # Optional fields
    inventory: List[str] = field(default_factory=list)  # List of item IDs
    metadata: Dict = field(default_factory=dict)  # Additional user data
    
    def to_dict(self) -> dict:
        """Convert user to dictionary for storage."""
        return {
            'public_key': self.public_key,
            'username': self.username,
            'created_at': self.created_at,
            'inventory': self.inventory,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        """Create User from dictionary."""
        return cls(
            public_key=data['public_key'],
            username=data['username'],
            created_at=data.get('created_at', datetime.now(timezone.utc).isoformat()),
            inventory=data.get('inventory', []),
            metadata=data.get('metadata', {})
        )

@dataclass
class Item:
    """Represents an item in the system."""
    # Required fields
    item_id: str  # Nano token ID (public key)
    name: str
    description: str
    owner_public_key: str  # Current owner's Nano public key
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    # Auction-related fields
    is_auction: bool = False
    auction_end_time: Optional[str] = None
    starting_price: float = 0.0
    current_bid: Optional[float] = None
    current_bidder: Optional[str] = None  # Bidder's public key
    
    # Additional metadata
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert item to dictionary for storage."""
        return {
            'item_id': self.item_id,
            'name': self.name,
            'description': self.description,
            'owner_public_key': self.owner_public_key,
            'created_at': self.created_at,
            'is_auction': self.is_auction,
            'auction_end_time': self.auction_end_time,
            'starting_price': self.starting_price,
            'current_bid': self.current_bid,
            'current_bidder': self.current_bidder,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Item':
        """Create Item from dictionary."""
        return cls(
            item_id=data['item_id'],
            name=data['name'],
            description=data['description'],
            owner_public_key=data['owner_public_key'],
            created_at=data.get('created_at', datetime.now(timezone.utc).isoformat()),
            is_auction=data.get('is_auction', False),
            auction_end_time=data.get('auction_end_time'),
            starting_price=data.get('starting_price', 0.0),
            current_bid=data.get('current_bid'),
            current_bidder=data.get('current_bidder'),
            metadata=data.get('metadata', {})
        )

@dataclass
class Auction:
    """Represents an auction in the system."""
    # Required fields (no default values)
    item_id: str
    seller_public_key: str
    starting_price: float
    
    # Fields with default values
    auction_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    # Auction timing
    duration_hours: float = 24.0  # Default 24-hour auction
    end_time: Optional[str] = None
    
    # Bidding
    current_bid: Optional[float] = None
    current_bidder: Optional[str] = None
    bids: List[dict] = field(default_factory=list)  # List of {'bidder_public_key', 'amount', 'timestamp'}
    
    # Status
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
            item_id=data['item_id'],
            seller_public_key=data['seller_public_key'],
            starting_price=data['starting_price'],
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
