"""
Enhanced data models for the Sapphire Exchange auction platform.
Supports DOGE integration, multi-currency transactions, and enhanced security.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
import uuid
import hashlib
import json

@dataclass
class User:
    """Enhanced user model with DOGE integration and security features."""
    # Core identification (from robot_info.json)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    username: str = ""  # 3-32 characters (ui_constants)
    email: str = ""  # User email address
    public_key: str = ""  # base58 format
    nano_address: str = ""  # nano_[a-z0-9]{60} format
    arweave_address: str = ""  # Arweave wallet address
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    # DOGE wallet integration (from More_Robot_info.json)
    doge_address: str = ""
    doge_private_key_encrypted: str = ""  # Encrypted with user's master key
    doge_mnemonic_hash: str = ""  # Hash of mnemonic for verification
    
    # Legacy fields for backward compatibility
    first_name: str = ""
    last_name: str = ""
    
    # Enhanced user data
    inventory: List[str] = field(default_factory=list)  # UUID list
    reputation_score: float = 0.0  # 0-100 range
    bid_credits: float = 0.0  # For bid escrow system
    is_active: bool = True  # Account status
    total_sales: int = 0  # Total number of sales
    total_purchases: int = 0  # Total number of purchases
    data_hash: str = ""  # Data integrity hash
    arweave_profile_uri: str = ""  # Arweave transaction ID for profile
    
    # Security & session management
    last_login: str = ""
    session_timeout: int = 7200  # 120 minutes (security_parameters)
    inactivity_timeout: int = 1800  # 30 minutes
    password_hash: str = ""  # PBKDF2-HMAC-SHA256 hash
    password_salt: str = ""  # Salt for password hashing
    
    # Metadata storage
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert user to dictionary for storage."""
        return {
            'id': self.id,
            'username': self.username,
            'public_key': self.public_key,
            'nano_address': self.nano_address,
            'created_at': self.created_at,
            'doge_address': self.doge_address,
            'doge_private_key_encrypted': self.doge_private_key_encrypted,
            'doge_mnemonic_hash': self.doge_mnemonic_hash,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'inventory': self.inventory,
            'reputation_score': self.reputation_score,
            'bid_credits': self.bid_credits,
            'last_login': self.last_login,
            'session_timeout': self.session_timeout,
            'inactivity_timeout': self.inactivity_timeout,
            'password_hash': self.password_hash,
            'password_salt': self.password_salt,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        """Create User from dictionary."""
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            username=data.get('username', ''),
            public_key=data.get('public_key', ''),
            nano_address=data.get('nano_address', ''),
            created_at=data.get('created_at', datetime.now(timezone.utc).isoformat()),
            doge_address=data.get('doge_address', ''),
            doge_private_key_encrypted=data.get('doge_private_key_encrypted', ''),
            doge_mnemonic_hash=data.get('doge_mnemonic_hash', ''),
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            inventory=data.get('inventory', []),
            reputation_score=data.get('reputation_score', 0.0),
            bid_credits=data.get('bid_credits', 0.0),
            last_login=data.get('last_login', ''),
            session_timeout=data.get('session_timeout', 7200),
            inactivity_timeout=data.get('inactivity_timeout', 1800),
            password_hash=data.get('password_hash', ''),
            password_salt=data.get('password_salt', ''),
            metadata=data.get('metadata', {})
        )
    
    def validate_username(self) -> bool:
        """Validate username according to ui_constants (3-32 characters)."""
        return 3 <= len(self.username) <= 32
    
    def calculate_data_hash(self) -> str:
        """Calculate SHA-256 hash for data integrity verification."""
        # Create a copy without sensitive data for hashing
        hash_data = {
            'id': self.id,
            'username': self.username,
            'public_key': self.public_key,
            'nano_address': self.nano_address,
            'doge_address': self.doge_address,
            'created_at': self.created_at,
            'reputation_score': self.reputation_score
        }
        data_str = json.dumps(hash_data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()

@dataclass
class Item:
    """Enhanced item model with multi-currency support and data integrity."""
    # Core item data (robot_info.json specifications)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    seller_id: str = ""  # UUID reference to User
    title: str = ""  # max 100 chars (ui_constants)
    description: str = ""  # max 2000 chars (ui_constants)
    
    # Legacy fields for backward compatibility
    item_id: str = ""  # Nano token ID (public key)
    name: str = ""
    owner_public_key: str = ""  # Current owner's Nano public key
    
    # Pricing in multiple formats
    starting_price_raw: str = "0"  # Nano raw units (nano_raw_amount format)
    starting_price_doge: str = "0.0"  # DOGE amount (primary currency)
    current_bid_raw: Optional[str] = None
    current_bid_doge: Optional[str] = None
    
    # Legacy pricing fields
    starting_price: float = 0.0
    current_bid: Optional[float] = None
    current_bidder: Optional[str] = None  # Bidder's public key
    
    # Auction timing
    auction_end: str = ""  # ISO 8601 timestamp
    auction_end_time: Optional[str] = None  # Legacy field
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    # Status management (from data_models.Item.status enum)
    status: str = "draft"  # draft/active/sold/expired/cancelled
    is_auction: bool = False  # Legacy field
    
    # Arweave integration
    arweave_metadata_uri: str = ""  # Arweave transaction ID
    
    # Enhanced bidding system
    bids: List[Dict] = field(default_factory=list)  # Bid references
    bid_history_arweave_id: str = ""  # Separate Arweave storage for bid history
    
    # Shipping integration (More_Robot_info.json mentions USPS integration)
    shipping_required: bool = False
    shipping_cost_doge: str = "0"
    usps_tracking_number: str = ""
    
    # Tags and categorization (ui_constants)
    tags: List[str] = field(default_factory=list)  # max 10 tags, 20 chars each
    category: str = ""
    
    # Data integrity
    data_hash: str = ""  # SHA-256 hash for verification
    arweave_confirmed: bool = False
    
    # Auction-specific wallet and RSA data
    auction_nano_address: str = ""  # Dedicated NANO address for this auction
    auction_nano_public_key: str = ""  # Public key for the auction wallet
    auction_nano_private_key: str = ""  # Private key for the auction wallet (encrypted)
    auction_nano_seed: str = ""  # Seed for the auction wallet (encrypted)
    auction_rsa_private_key: str = ""  # RSA private key (base64 encoded)
    auction_rsa_public_key: str = ""  # RSA public key (base64 encoded)
    auction_rsa_fingerprint: str = ""  # RSA key fingerprint
    auction_wallet_created_at: str = ""  # When the auction wallet was created
    
    # Additional metadata
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert item to dictionary for storage."""
        return {
            'id': self.id,
            'seller_id': self.seller_id,
            'title': self.title,
            'description': self.description,
            'item_id': self.item_id,
            'name': self.name,
            'owner_public_key': self.owner_public_key,
            'starting_price_raw': self.starting_price_raw,
            'starting_price_doge': self.starting_price_doge,
            'current_bid_raw': self.current_bid_raw,
            'current_bid_doge': self.current_bid_doge,
            'starting_price': self.starting_price,
            'current_bid': self.current_bid,
            'current_bidder': self.current_bidder,
            'auction_end': self.auction_end,
            'auction_end_time': self.auction_end_time,
            'created_at': self.created_at,
            'status': self.status,
            'is_auction': self.is_auction,
            'arweave_metadata_uri': self.arweave_metadata_uri,
            'bids': self.bids,
            'bid_history_arweave_id': self.bid_history_arweave_id,
            'shipping_required': self.shipping_required,
            'shipping_cost_doge': self.shipping_cost_doge,
            'usps_tracking_number': self.usps_tracking_number,
            'tags': self.tags,
            'category': self.category,
            'data_hash': self.data_hash,
            'arweave_confirmed': self.arweave_confirmed,
            'auction_nano_address': self.auction_nano_address,
            'auction_nano_public_key': self.auction_nano_public_key,
            'auction_nano_private_key': self.auction_nano_private_key,
            'auction_nano_seed': self.auction_nano_seed,
            'auction_rsa_private_key': self.auction_rsa_private_key,
            'auction_rsa_public_key': self.auction_rsa_public_key,
            'auction_rsa_fingerprint': self.auction_rsa_fingerprint,
            'auction_wallet_created_at': self.auction_wallet_created_at,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Item':
        """Create Item from dictionary."""
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            seller_id=data.get('seller_id', ''),
            title=data.get('title', ''),
            description=data.get('description', ''),
            item_id=data.get('item_id', ''),
            name=data.get('name', ''),
            owner_public_key=data.get('owner_public_key', ''),
            starting_price_raw=data.get('starting_price_raw', '0'),
            starting_price_doge=data.get('starting_price_doge', '0.0'),
            current_bid_raw=data.get('current_bid_raw'),
            current_bid_doge=data.get('current_bid_doge'),
            starting_price=data.get('starting_price', 0.0),
            current_bid=data.get('current_bid'),
            current_bidder=data.get('current_bidder'),
            auction_end=data.get('auction_end', ''),
            auction_end_time=data.get('auction_end_time'),
            created_at=data.get('created_at', datetime.now(timezone.utc).isoformat()),
            status=data.get('status', 'draft'),
            is_auction=data.get('is_auction', False),
            arweave_metadata_uri=data.get('arweave_metadata_uri', ''),
            bids=data.get('bids', []),
            bid_history_arweave_id=data.get('bid_history_arweave_id', ''),
            shipping_required=data.get('shipping_required', False),
            shipping_cost_doge=data.get('shipping_cost_doge', '0'),
            usps_tracking_number=data.get('usps_tracking_number', ''),
            tags=data.get('tags', []),
            category=data.get('category', ''),
            data_hash=data.get('data_hash', ''),
            arweave_confirmed=data.get('arweave_confirmed', False),
            auction_nano_address=data.get('auction_nano_address', ''),
            auction_nano_public_key=data.get('auction_nano_public_key', ''),
            auction_nano_private_key=data.get('auction_nano_private_key', ''),
            auction_nano_seed=data.get('auction_nano_seed', ''),
            auction_rsa_private_key=data.get('auction_rsa_private_key', ''),
            auction_rsa_public_key=data.get('auction_rsa_public_key', ''),
            auction_rsa_fingerprint=data.get('auction_rsa_fingerprint', ''),
            auction_wallet_created_at=data.get('auction_wallet_created_at', ''),
            metadata=data.get('metadata', {})
        )
    
    def validate_title(self) -> bool:
        """Validate title according to ui_constants (max 100 characters)."""
        return len(self.title) <= 100
    
    def validate_description(self) -> bool:
        """Validate description according to ui_constants (max 2000 characters)."""
        return len(self.description) <= 2000
    
    def validate_tags(self) -> bool:
        """Validate tags according to ui_constants (max 10 tags, 20 chars each)."""
        if len(self.tags) > 10:
            return False
        return all(len(tag) <= 20 for tag in self.tags)
    
    def calculate_data_hash(self) -> str:
        """Calculate SHA-256 hash for data integrity verification."""
        hash_data = {
            'id': self.id,
            'seller_id': self.seller_id,
            'title': self.title,
            'description': self.description,
            'starting_price_doge': self.starting_price_doge,
            'created_at': self.created_at,
            'status': self.status
        }
        data_str = json.dumps(hash_data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def is_ended(self) -> bool:
        """Check if the auction has ended."""
        if not self.auction_end:
            return False
        try:
            end_time = datetime.fromisoformat(self.auction_end.replace('Z', '+00:00'))
            return datetime.now(timezone.utc) > end_time
        except ValueError:
            return False

@dataclass
class Bid:
    """Enhanced bid model with multi-currency support and verification."""
    # Core bid identification
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    item_id: str = ""  # UUID reference
    bidder_id: str = ""  # UUID reference
    
    # Multi-currency amounts
    amount_raw: str = "0"  # Nano raw units
    amount_doge: str = "0.0"  # DOGE amount (primary display)
    amount_usd: Optional[str] = None  # USD equivalent via CoinGecko
    
    # Blockchain integration
    transaction_hash: str = ""  # 64-char hex pattern (from Bid model)
    nano_block_hash: str = ""
    arweave_tx_id: str = ""  # For bid metadata storage
    
    # Timing and status
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    confirmed_at: Optional[str] = None
    status: str = "pending"  # pending/confirmed/outbid/won/refunded
    
    # Verification and integrity
    rsa_signature: str = ""  # RSA-PSS signature for verification
    data_verified: bool = False
    confirmation_blocks: int = 0  # Track confirmation depth
    
    # Additional metadata
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert bid to dictionary for storage."""
        return {
            'id': self.id,
            'item_id': self.item_id,
            'bidder_id': self.bidder_id,
            'amount_raw': self.amount_raw,
            'amount_doge': self.amount_doge,
            'amount_usd': self.amount_usd,
            'transaction_hash': self.transaction_hash,
            'nano_block_hash': self.nano_block_hash,
            'arweave_tx_id': self.arweave_tx_id,
            'created_at': self.created_at,
            'confirmed_at': self.confirmed_at,
            'status': self.status,
            'rsa_signature': self.rsa_signature,
            'data_verified': self.data_verified,
            'confirmation_blocks': self.confirmation_blocks,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Bid':
        """Create Bid from dictionary."""
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            item_id=data.get('item_id', ''),
            bidder_id=data.get('bidder_id', ''),
            amount_raw=data.get('amount_raw', '0'),
            amount_doge=data.get('amount_doge', '0.0'),
            amount_usd=data.get('amount_usd'),
            transaction_hash=data.get('transaction_hash', ''),
            nano_block_hash=data.get('nano_block_hash', ''),
            arweave_tx_id=data.get('arweave_tx_id', ''),
            created_at=data.get('created_at', datetime.now(timezone.utc).isoformat()),
            confirmed_at=data.get('confirmed_at'),
            status=data.get('status', 'pending'),
            rsa_signature=data.get('rsa_signature', ''),
            data_verified=data.get('data_verified', False),
            confirmation_blocks=data.get('confirmation_blocks', 0),
            metadata=data.get('metadata', {})
        )
    
    def validate_transaction_hash(self) -> bool:
        """Validate transaction hash format (64-char hex)."""
        import re
        return bool(re.match(r'^[0-9A-F]{64}$', self.transaction_hash))
    
    def calculate_data_hash(self) -> str:
        """Calculate SHA-256 hash for data integrity verification."""
        hash_data = {
            'id': self.id,
            'item_id': self.item_id,
            'bidder_id': self.bidder_id,
            'amount_doge': self.amount_doge,
            'created_at': self.created_at
        }
        data_str = json.dumps(hash_data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()

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
