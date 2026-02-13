"""
Unified Application Service for Sapphire Exchange.
Orchestrates all components and provides a single interface for the UI.
"""
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone

from models.models import User, Item, Bid
from services import AuctionService, WalletService, UserService, user_service
from repositories import UserRepository, ItemRepository, BidRepository
from blockchain.blockchain_manager import blockchain_manager, BlockchainStatus
from repositories.database_adapter import database_adapter
from security.security_manager import SecurityManager
from security.performance_manager import PerformanceManager
from services.price_service import PriceConversionService
from utils.validation_utils import Validator
from utils.conversion_utils import conversion_utils
from config.app_config import app_config


class ApplicationService:
    """
    Unified application service that orchestrates all components.
    Provides a clean interface for the UI layer.
    """
    
    def __init__(self):
        """Initialize the application service."""
        # Core managers
        self.blockchain = blockchain_manager
        self.database = database_adapter
        self.security = SecurityManager()
        self.performance = PerformanceManager()
        self.price_service = PriceConversionService(self.performance)
        
        # Repositories
        self.user_repo = self.database.get_user_repository()
        self.item_repo = self.database.get_item_repository()
        self.bid_repo = self.database.get_bid_repository()
        
        # Services
        self.user_service = user_service
        self.auction_service = AuctionService(database=self.database)
        self.wallet_service = WalletService()
        
        # Application state
        self.current_user: Optional[User] = None
        self.current_session: Optional[str] = None
        self.is_initialized = False
        
        # Event callbacks
        self.status_change_callbacks = []
        self.user_change_callbacks = []
        self.auction_update_callbacks = []
        
        # Setup service connections
        self._setup_service_connections()
    
    def _setup_service_connections(self):
        """Setup connections between services."""
        # Connect user service to database
        self.user_service.database = self.database
        
        # Connect auction service to blockchain
        self.auction_service.blockchain = self.blockchain
        
        # Setup event callbacks
        self.blockchain.add_status_change_callback(self._on_blockchain_status_change)
        self.user_service.add_user_login_callback(self._on_user_login)
        self.user_service.add_user_logout_callback(self._on_user_logout)
        self.auction_service.add_bid_placed_callback(self._on_bid_placed)
        self.auction_service.add_auction_ended_callback(self._on_auction_ended)
    
    async def initialize(self) -> bool:
        """Initialize the application service."""
        try:
            print("[APP_INIT] Initializing Sapphire Exchange...")
            
            # Initialize blockchain manager
            print("[APP_INIT] Initializing blockchain manager...")
            blockchain_success = await self.blockchain.initialize()
            print(f"[APP_INIT] Blockchain manager initialization: {blockchain_success}")
            if not blockchain_success:
                print("[APP_INIT] Warning: Some blockchain services failed to initialize")
            
            # Initialize price service
            # Price service initialization is handled internally
            
            # Mark as initialized
            self.is_initialized = True
            
            print("[APP_INIT] Application service initialized successfully")
            return True
            
        except Exception as e:
            print(f"[APP_INIT] Error initializing application service: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # User Management
    async def register_user(self, username: str, password: str) -> Tuple[bool, str, Optional[User]]:
        """Register a new user."""
        try:
            # Validate input
            validation = Validator.validate_user_data({
                'username': username,
                'password': password
            })
            
            if not validation['valid']:
                return False, '; '.join(validation['errors']), None
            
            # Create user
            user = await self.user_service.create_user(username, password)
            if user:
                return True, "User registered successfully", user
            else:
                return False, "Failed to create user account", None
                
        except Exception as e:
            return False, f"Registration error: {str(e)}", None
    
    async def register_user_with_seed(self, seed_phrase: str, wallet_data: Dict[str, Any] = None) -> Tuple[bool, str, Optional[User]]:
        """
        Register a new user with a seed phrase.
        Creates account and encrypted backup using Nano mnemonic.
        
        Args:
            seed_phrase: BIP39 Nano mnemonic phrase
            wallet_data: Pre-generated wallet data (optional)
        
        Returns:
            Tuple of (success, message, user)
        """
        try:
            print(f"[DEBUG] register_user_with_seed called with seed_phrase length: {len(seed_phrase) if seed_phrase else 0}")
            # For now, we'll create a simple username based on the seed phrase
            # In a real implementation, you would derive the user's identity from the seed
            # Ensure username meets requirements: 3-30 chars, alphanumeric with _ and - only
            username_hash = hash(seed_phrase) % 1000000
            username = f"user_{username_hash:06d}"
            print(f"[DEBUG] Generated username for registration: {username}")
            
            # Generate a proper password that meets requirements
            # Using a combination of the seed phrase and some fixed characters
            password = f"Pw1@{seed_phrase[:20]}"  # Add uppercase, digit, special char prefix
            
            # Validate input
            validation = Validator.validate_user_data({
                'username': username,
                'password': password
            })
            
            if not validation['valid']:
                print(f"[DEBUG] Validation failed: {validation['errors']}")
                return False, '; '.join(validation['errors']), None
            
            # Create user
            user = await self.user_service.create_user(username, password)
            if user:
                print(f"[DEBUG] User registered successfully: {user.username}")
                
                # Create encrypted account backup after Arweave post
                if wallet_data:
                    backup_success, backup_path = await self.user_service.create_account_backup_for_user(
                        user, seed_phrase, wallet_data
                    )
                    if backup_success:
                        print(f"[DEBUG] Account backup created: {backup_path}")
                
                # Automatically log in the newly registered user
                self.current_user = user
                # Note: We don't have a session token from registration, but we'll set the user
                print(f"[DEBUG] Auto-login after registration, current_user set to: {self.current_user}")
                return True, "User registered successfully", user
            else:
                print(f"[DEBUG] Failed to create user account")
                return False, "Failed to create user account", None
                
        except Exception as e:
            print(f"[DEBUG] Registration error: {str(e)}")
            return False, f"Registration error: {str(e)}", None
    
    async def login_user(self, username: str, password: str) -> Tuple[bool, str, Optional[User]]:
        """Login a user."""
        try:
            result = await self.user_service.authenticate_user(username, password)
            if result:
                user, session_token = result
                self.current_user = user
                self.current_session = session_token
                return True, "Login successful", user
            else:
                return False, "Invalid username or password", None
                
        except Exception as e:
            return False, f"Login error: {str(e)}", None
    
    async def login_user_with_seed(self, seed_phrase: str) -> Tuple[bool, str, Optional[User]]:
        """Login a user with a seed phrase."""
        try:
            print(f"[DEBUG] login_user_with_seed called with seed_phrase length: {len(seed_phrase) if seed_phrase else 0}")
            # For now, we'll try to authenticate using the seed as a password
            # In a real implementation, you would derive the user's identity from the seed
            # Use the same username generation as in registration
            username_hash = hash(seed_phrase) % 1000000
            username = f"user_{username_hash:06d}"
            print(f"[DEBUG] Generated username: {username}")
            
            # Generate the same password that was used during registration
            password = f"Pw1@{seed_phrase[:20]}"  # Add uppercase, digit, special char prefix
            
            result = await self.user_service.authenticate_user(username, password)
            if result:
                user, session_token = result
                self.current_user = user
                self.current_session = session_token
                print(f"[DEBUG] Login successful, current_user set to: {self.current_user}")
                print(f"[DEBUG] User ID: {user.id if user else None}, Username: {user.username if user else None}")
                return True, "Login successful", user
            else:
                print(f"[DEBUG] Authentication failed for username: {username}")
                return False, "Invalid seed phrase", None
                
        except Exception as e:
            print(f"[DEBUG] Login error: {str(e)}")
            return False, f"Login error: {str(e)}", None
    
    async def recover_user_from_mnemonic(self, nano_mnemonic: str) -> Optional[Tuple[User, str, Dict[str, Any]]]:
        """
        Recover user account from Nano mnemonic.
        Delegates to user_service which handles backup retrieval and decryption.
        
        Args:
            nano_mnemonic: BIP39 Nano mnemonic phrase
        
        Returns:
            Tuple of (user, session_token, wallet_data) or None if no backup found
        """
        try:
            result = await self.user_service.recover_user_from_mnemonic(nano_mnemonic)
            if result:
                user, session_token, wallet_data = result
                self.current_user = user
                self.current_session = session_token
                print(f"User recovered from backup: {user.username}")
                return user, session_token, wallet_data
            return None
        except Exception as e:
            print(f"Error recovering user from mnemonic: {e}")
            return None
    
    async def logout_user(self) -> bool:
        """Logout the current user."""
        try:
            if self.current_session:
                success = await self.user_service.logout_user(self.current_session)
                if success:
                    self.current_user = None
                    self.current_session = None
                return success
            return True
        except Exception as e:
            print(f"Logout error: {e}")
            return False
    
    async def update_username(self, new_username: str) -> bool:
        """Update the current user's username."""
        try:
            print(f"[DEBUG] update_username called with: {new_username}")
            if not self.current_user:
                print(f"[DEBUG] No current user found")
                return False
            
            old_username = self.current_user.username
            print(f"[DEBUG] Current username: {old_username}")
            
            # Validate username
            if not new_username or len(new_username) < 3 or len(new_username) > 32:
                print(f"[DEBUG] Username validation failed")
                return False
            
            # Update the user object
            self.current_user.username = new_username
            print(f"[DEBUG] Updated user object username to: {self.current_user.username}")
            
            # Save to database
            success = await self.user_repo.update(self.current_user)
            print(f"[DEBUG] Database update success: {success}")
            
            if success:
                # Notify callbacks about user change
                print(f"[DEBUG] Notifying callbacks about profile update")
                self._notify_user_change('profile_updated', self.current_user)
                print(f"[DEBUG] Username successfully updated from {old_username} to {new_username}")
                return True
            
            return False
        except Exception as e:
            print(f"Error updating username: {e}")
            return False
    
    def get_current_user(self) -> Optional[User]:
        """Get the currently logged in user."""
        return self.current_user
    
    def is_user_logged_in(self) -> bool:
        """Check if a user is logged in."""
        return self.current_user is not None
    
    # Auction Management
    async def create_auction(self, item_data: Dict[str, Any]) -> Tuple[bool, str, Optional[Item]]:
        """Create a new auction."""
        try:
            print(f"[APP] create_auction called, current_user: {self.current_user}")
            print(f"[APP] is_user_logged_in(): {self.is_user_logged_in()}")
            print(f"[APP] item_data keys: {list(item_data.keys())}")
            print(f"[APP] SHA ID: {item_data.get('sha_id', 'NOT PROVIDED')}")
            print(f"[APP] Auction Nano Address: {item_data.get('auction_nano_address', 'NOT PROVIDED')}")
            if not self.current_user:
                print(f"[APP] No current user found, returning error")
                return False, "Must be logged in to create auction", None
            
            # Convert auction_duration_hours to auction_end if needed
            if 'auction_duration_hours' in item_data and 'auction_end' not in item_data:
                from datetime import datetime, timezone, timedelta
                duration_hours = item_data.get('auction_duration_hours', 168)  # Default to 7 days
                auction_end = datetime.now(timezone.utc) + timedelta(hours=duration_hours)
                item_data['auction_end'] = auction_end.isoformat()
                print(f"[APP] Converted duration {duration_hours}h to auction_end: {item_data['auction_end']}")
            
            # Validate item data
            validation = Validator.validate_item_data(item_data)
            if not validation['valid']:
                print(f"[APP] Validation errors: {validation['errors']}")
                return False, '; '.join(validation['errors']), None
            
            # Create auction
            print(f"[APP] Calling auction_service.create_auction for user {self.current_user.id}")
            item = await self.auction_service.create_auction(self.current_user, item_data)
            if item:
                print(f"[APP] Auction created successfully: {item.id} with status {item.status}")
                return True, "Auction created successfully", item
            else:
                print(f"[APP] auction_service.create_auction returned None")
                return False, "Failed to create auction", None
                
        except Exception as e:
            print(f"[APP] Auction creation error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False, f"Auction creation error: {str(e)}", None
    
    async def place_bid(self, item_id: str, amount: float, currency: str = "USDC") -> Tuple[bool, str, Optional[Bid]]:
        """Place a bid on an auction."""
        try:
            if not self.current_user:
                return False, "Must be logged in to place bid", None
            
            # Get item
            item = await self.item_repo.get_by_id(item_id)
            if not item:
                return False, "Auction not found", None
            
            # Validate bid
            current_highest = float(item.current_bid_usdc or item.starting_price_usdc or "0")
            bid_validation = Validator.validate_bid_data({
                'item_id': item_id,
                'bidder_id': self.current_user.id,
                'amount_usdc': amount
            }, current_highest)
            
            if not bid_validation['valid']:
                return False, '; '.join(bid_validation['errors']), None
            
            # Place bid
            bid = await self.auction_service.place_bid(self.current_user, item, amount, currency)
            if bid:
                return True, "Bid placed successfully", bid
            else:
                return False, "Failed to place bid", None
                
        except Exception as e:
            return False, f"Bid placement error: {str(e)}", None
    
    async def get_active_auctions(self, limit: int = 20, offset: int = 0) -> List[Item]:
        """Get active auctions."""
        try:
            return await self.auction_service.get_active_auctions(limit, offset)
        except Exception as e:
            print(f"Error getting active auctions: {e}")
            return []
    
    async def get_auction_details(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed auction information."""
        try:
            item = await self.item_repo.get_by_id(item_id)
            if not item:
                return None
            
            # Get bids
            bids = await self.bid_repo.get_by_item(item_id, limit=10)
            
            # Get seller info
            seller = await self.user_repo.get_by_id(item.seller_id)
            
            # Get item stats
            stats = await self.item_repo.get_item_stats(item_id)
            
            return {
                'item': item,
                'bids': bids,
                'seller': seller,
                'stats': stats,
                'time_remaining': conversion_utils.format_time_remaining(item.auction_end)
            }
        except Exception as e:
            print(f"Error getting auction details: {e}")
            return None
    
    async def search_auctions(self, query: str, category: Optional[str] = None, 
                             tags: Optional[List[str]] = None, limit: int = 20) -> List[Item]:
        """Search auctions."""
        try:
            return await self.auction_service.search_auctions(query, category, tags)
        except Exception as e:
            print(f"Error searching auctions: {e}")
            return []
    
    async def get_user_items(self, limit: int = 50, offset: int = 0) -> List[Item]:
        """Get items belonging to the current user."""
        try:
            if not self.current_user:
                return []
            
            return await self.item_repo.get_by_seller(self.current_user.id, limit=limit, offset=offset)
        except Exception as e:
            print(f"Error getting user items: {e}")
            return []
    
    # Wallet Management
    async def get_wallet_balances(self) -> Dict[str, Optional[float]]:
        """Get wallet balances for current user."""
        try:
            if not self.current_user:
                return {}
            
            addresses = {
                'nano': self.current_user.nano_address,
                'arweave': self.current_user.arweave_address
            }
            
            if getattr(self.current_user, 'usdc_address', None):
                addresses['usdc'] = self.current_user.usdc_address
            
            return await self.blockchain.batch_get_balances(addresses)
        except Exception as e:
            print(f"Error getting wallet balances: {e}")
            return {}
    
    async def get_wallet_transactions(self, currency: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get wallet transaction history."""
        try:
            if not self.current_user:
                return []
            
            # This would be implemented based on the specific blockchain client
            # For now, return empty list
            return []
        except Exception as e:
            print(f"Error getting wallet transactions: {e}")
            return []
    
    def get_wallet_addresses(self) -> Dict[str, str]:
        """Get wallet addresses for current user."""
        try:
            if not self.current_user:
                return {}
            
            addresses = {}
            if getattr(self.current_user, 'nano_address', None):
                addresses['NANO'] = self.current_user.nano_address
            if getattr(self.current_user, 'usdc_address', None):
                addresses['USDC'] = self.current_user.usdc_address
            if getattr(self.current_user, 'arweave_address', None):
                addresses['ARWEAVE'] = self.current_user.arweave_address
            
            return addresses
        except Exception as e:
            print(f"Error getting wallet addresses: {e}")
            return {}
    
    # Price Information
    async def get_current_prices(self, currencies: List[str] = None) -> Dict[str, Any]:
        """Get current cryptocurrency prices."""
        try:
            if currencies is None:
                currencies = ['nano', 'dogecoin', 'arweave', 'bitcoin', 'ethereum']
            
            prices = await self.price_service.get_multiple_prices(currencies)
            return {currency: price.to_dict() if price else None for currency, price in prices.items()}
        except Exception as e:
            print(f"Error getting current prices: {e}")
            return {}
    
    async def convert_currency(self, amount: float, from_currency: str, to_currency: str) -> Optional[float]:
        """Convert amount between currencies."""
        try:
            return await self.price_service.convert_amount(amount, from_currency, to_currency)
        except Exception as e:
            print(f"Error converting currency: {e}")
            return None
    
    # System Status
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status."""
        try:
            blockchain_status = self.blockchain.get_status_summary()
            
            return {
                'initialized': self.is_initialized,
                'user_logged_in': self.is_user_logged_in(),
                'current_user': self.current_user.username if self.current_user else None,
                'blockchain': blockchain_status,
                'database': 'connected',  # Simplified
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            print(f"Error getting system status: {e}")
            return {'error': str(e)}
    
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get dashboard data for the main UI."""
        try:
            # Get active auctions
            active_auctions = await self.get_active_auctions(limit=10)
            
            # Get ending soon auctions
            ending_soon = await self.item_repo.get_ending_soon(hours=24, limit=5)
            
            # Get popular auctions
            popular = await self.item_repo.get_popular_items(limit=5)
            
            # Get current prices
            prices = await self.get_current_prices(['nano', 'dogecoin'])
            
            # Get user-specific data if logged in
            user_data = {}
            if self.current_user:
                user_data = {
                    'balances': await self.get_wallet_balances(),
                    'my_auctions': await self.item_repo.get_by_seller(self.current_user.id, limit=5),
                    'my_bids': await self.bid_repo.get_by_bidder(self.current_user.id, limit=5)
                }
            
            return {
                'active_auctions': active_auctions,
                'ending_soon': ending_soon,
                'popular': popular,
                'prices': prices,
                'user_data': user_data,
                'system_status': self.get_system_status()
            }
        except Exception as e:
            print(f"Error getting dashboard data: {e}")
            return {}
    
    # Event Callbacks
    def add_status_change_callback(self, callback):
        """Add callback for status changes."""
        self.status_change_callbacks.append(callback)
    
    def add_user_change_callback(self, callback):
        """Add callback for user changes."""
        self.user_change_callbacks.append(callback)
    
    def add_auction_update_callback(self, callback):
        """Add callback for auction updates."""
        self.auction_update_callbacks.append(callback)
    
    def _on_blockchain_status_change(self, status):
        """Handle blockchain status changes."""
        for callback in self.status_change_callbacks:
            try:
                callback('blockchain', status)
            except Exception as e:
                print(f"Error in status change callback: {e}")
    
    def _on_user_login(self, user: User):
        """Handle user login."""
        for callback in self.user_change_callbacks:
            try:
                callback('login', user)
            except Exception as e:
                print(f"Error in user change callback: {e}")
    
    def _on_user_logout(self, user: User):
        """Handle user logout."""
        for callback in self.user_change_callbacks:
            try:
                callback('logout', user)
            except Exception as e:
                print(f"Error in user change callback: {e}")
    
    def _notify_user_change(self, event_type: str, user: User):
        """Notify callbacks about user changes."""
        print(f"[DEBUG] _notify_user_change called with event: {event_type}, user: {user.username if user else None}")
        print(f"[DEBUG] Number of callbacks registered: {len(self.user_change_callbacks)}")
        for i, callback in enumerate(self.user_change_callbacks):
            try:
                print(f"[DEBUG] Calling callback {i}: {callback}")
                callback(event_type, user)
                print(f"[DEBUG] Callback {i} completed successfully")
            except Exception as e:
                print(f"Error in user change callback {i}: {e}")
    
    def _on_bid_placed(self, item: Item, bid: Bid):
        """Handle bid placed."""
        for callback in self.auction_update_callbacks:
            try:
                callback('bid_placed', {'item': item, 'bid': bid})
            except Exception as e:
                print(f"Error in auction update callback: {e}")
    
    def _on_auction_ended(self, item: Item):
        """Handle auction ended."""
        for callback in self.auction_update_callbacks:
            try:
                callback('auction_ended', {'item': item})
            except Exception as e:
                print(f"Error in auction update callback: {e}")
    
    async def post_pending_inventory(self) -> Tuple[bool, str]:
        """
        Post pending inventory to Arweave when user is ready.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            if not self.current_user:
                return False, "Must be logged in to post inventory"
            
            # Get pending inventory from service
            from services.arweave_post_service import arweave_post_service
            pending_post = arweave_post_service.get_pending_inventory(self.current_user.id)
            
            if not pending_post:
                return False, "No pending inventory to post"
            
            print(f"[POST_INVENTORY] Posting pending inventory for user {self.current_user.id}")
            
            # Post to Arweave
            tx_id = await arweave_post_service.post_inventory_to_arweave(pending_post, self.current_user)
            
            if tx_id:
                # Update user's inventory post URI
                self.current_user.arweave_inventory_uri = tx_id
                if self.database:
                    await self.database.update_user(self.current_user)
                
                # Clear pending inventory
                arweave_post_service.clear_pending_inventory(self.current_user.id)
                
                print(f"[POST_INVENTORY] Inventory posted successfully: {tx_id}")
                return True, f"Inventory posted to Arweave: {tx_id}"
            else:
                return False, "Failed to post inventory to Arweave (check AR balance)"
                
        except Exception as e:
            print(f"Error posting pending inventory: {e}")
            import traceback
            traceback.print_exc()
            return False, f"Error posting inventory: {str(e)}"
    
    async def shutdown(self):
        """Shutdown the application service."""
        try:
            print("Shutting down application service...")
            
            # Logout current user
            if self.current_user:
                await self.logout_user()
            
            # Shutdown blockchain manager
            await self.blockchain.shutdown()
            
            print("Application service shutdown complete")
        except Exception as e:
            print(f"Error during shutdown: {e}")


# Global application service instance
app_service = ApplicationService()