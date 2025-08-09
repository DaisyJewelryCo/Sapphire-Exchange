"""
User service for Sapphire Exchange.
Handles user management, authentication, and profile operations.
"""
import asyncio
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import asdict

from models.models import User
from blockchain.blockchain_manager import blockchain_manager
from config.app_config import app_config
from security.security_manager import SecurityManager


class UserService:
    """Service for managing users and authentication."""
    
    def __init__(self, database=None, security_manager: SecurityManager = None):
        """Initialize user service."""
        self.database = database
        self.blockchain = blockchain_manager
        self.security = security_manager or SecurityManager()
        
        # Active sessions
        self.active_sessions = {}
        
        # Event callbacks
        self.user_created_callbacks = []
        self.user_login_callbacks = []
        self.user_logout_callbacks = []
    
    async def create_user(self, username: str, password: str) -> Optional[User]:
        """Create a new user account."""
        try:
            # Validate input
            if not self._validate_user_data(username, password):
                return None
            
            # Check if user already exists
            if await self.get_user_by_username(username):
                print(f"User {username} already exists")
                return None
            
            # Generate blockchain addresses
            nano_address = await self.blockchain.generate_nano_address()
            arweave_address = await self.blockchain.generate_arweave_address()
            doge_address = await self.blockchain.generate_doge_address()
            
            if not all([nano_address, arweave_address, doge_address]):
                print("Failed to generate blockchain addresses")
                return None
            
            print(f"Generated addresses - Nano: {nano_address}, Arweave: {arweave_address}, DOGE: {doge_address}")
            
            # Hash password
            password_hash = self.security.hash_password(password)
            
            # Create user
            user = User(
                username=username,
                password_hash=password_hash,
                nano_address=nano_address,
                arweave_address=arweave_address,
                doge_address=doge_address,
                created_at=datetime.now(timezone.utc).isoformat(),
                is_active=True,
                reputation_score=0.0,
                total_sales=0,
                total_purchases=0
            )
            
            # Calculate data hash for integrity
            user.data_hash = user.calculate_data_hash()
            
            # Store user profile on Arweave
            user_tags = [
                ("Content-Type", "application/json"),
                ("App-Name", "Sapphire-Exchange"),
                ("Data-Type", "user-profile"),
                ("User-ID", user.id),
                ("Username", username)
            ]
            
            # Remove sensitive data for Arweave storage
            public_profile = user.to_dict()
            del public_profile['password_hash']
            
            tx_id = await self.blockchain.store_data(public_profile, user_tags)
            if tx_id:
                user.arweave_profile_uri = tx_id
                
                # Store in database
                if self.database:
                    await self.database.store_user(user)
                
                # Create wallet structures for the user
                try:
                    from services.wallet_service import wallet_service
                    wallet_created = await wallet_service.create_wallet(user)
                    if wallet_created:
                        print(f"Wallet created successfully for user {user.username}")
                    else:
                        print(f"Warning: Failed to create wallet for user {user.username}")
                except Exception as e:
                    print(f"Error creating wallet for user {user.username}: {e}")
                
                # Notify callbacks
                self._notify_user_created(user)
                
                return user
            
            return None
        except Exception as e:
            print(f"Error creating user: {e}")
            return None
    
    async def authenticate_user(self, username: str, password: str) -> Optional[Tuple[User, str]]:
        """Authenticate user and create session."""
        try:
            # Get user
            user = await self.get_user_by_username(username)
            if not user or not user.is_active:
                return None
            
            # Verify password
            if not self.security.verify_password(password, user.password_hash):
                return None
            
            # Create session
            session_token = self._create_session(user)
            
            # Update last login
            user.last_login = datetime.now(timezone.utc).isoformat()
            if self.database:
                await self.database.update_user(user)
            
            # Notify callbacks
            self._notify_user_login(user)
            
            return user, session_token
        except Exception as e:
            print(f"Error authenticating user: {e}")
            return None
    
    async def logout_user(self, session_token: str) -> bool:
        """Logout user and invalidate session."""
        try:
            if session_token in self.active_sessions:
                user_id = self.active_sessions[session_token]['user_id']
                del self.active_sessions[session_token]
                
                # Get user for callback
                user = await self.get_user_by_id(user_id)
                if user:
                    self._notify_user_logout(user)
                
                return True
            return False
        except Exception as e:
            print(f"Error logging out user: {e}")
            return False
    
    async def get_user_by_session(self, session_token: str) -> Optional[User]:
        """Get user by session token."""
        try:
            if session_token not in self.active_sessions:
                return None
            
            session = self.active_sessions[session_token]
            
            # Check session expiry
            if datetime.now(timezone.utc) > session['expires_at']:
                del self.active_sessions[session_token]
                return None
            
            return await self.get_user_by_id(session['user_id'])
        except Exception as e:
            print(f"Error getting user by session: {e}")
            return None
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        try:
            if self.database:
                return await self.database.get_user(user_id)
            return None
        except Exception as e:
            print(f"Error getting user by ID: {e}")
            return None
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        try:
            if self.database:
                return await self.database.get_user_by_username(username)
            return None
        except Exception as e:
            print(f"Error getting user by username: {e}")
            return None
    

    
    async def update_user_profile(self, user: User, updates: Dict[str, Any]) -> bool:
        """Update user profile."""
        try:
            # Validate updates
            allowed_fields = ['bio', 'location', 'website', 'avatar_url', 'preferences']
            
            for field, value in updates.items():
                if field not in allowed_fields:
                    continue
                
                if field == 'bio' and len(str(value)) > app_config.ui.max_bio_length:
                    continue
                
                setattr(user, field, value)
            
            # Update data hash
            user.data_hash = user.calculate_data_hash()
            user.updated_at = datetime.now(timezone.utc).isoformat()
            
            # Update on Arweave
            public_profile = user.to_dict()
            del public_profile['password_hash']
            
            user_tags = [
                ("Content-Type", "application/json"),
                ("App-Name", "Sapphire-Exchange"),
                ("Data-Type", "user-profile-update"),
                ("User-ID", user.id)
            ]
            
            tx_id = await self.blockchain.store_data(public_profile, user_tags)
            if tx_id:
                # Update database
                if self.database:
                    await self.database.update_user(user)
                return True
            
            return False
        except Exception as e:
            print(f"Error updating user profile: {e}")
            return False
    
    async def update_reputation(self, user_id: str, change: float, reason: str) -> bool:
        """Update user reputation score."""
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                return False
            
            # Update reputation
            old_score = user.reputation_score
            user.reputation_score = max(0.0, user.reputation_score + change)
            
            # Log reputation change
            reputation_log = {
                'user_id': user_id,
                'old_score': old_score,
                'new_score': user.reputation_score,
                'change': change,
                'reason': reason,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Store reputation change on Arweave
            rep_tags = [
                ("Content-Type", "application/json"),
                ("App-Name", "Sapphire-Exchange"),
                ("Data-Type", "reputation-change"),
                ("User-ID", user_id)
            ]
            
            await self.blockchain.store_data(reputation_log, rep_tags)
            
            # Update user
            if self.database:
                await self.database.update_user(user)
            
            return True
        except Exception as e:
            print(f"Error updating reputation: {e}")
            return False
    
    async def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get user statistics."""
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                return {}
            
            # Get additional stats from database
            stats = {
                'user_id': user_id,
                'username': user.username,
                'reputation_score': user.reputation_score,
                'total_sales': user.total_sales,
                'total_purchases': user.total_purchases,
                'member_since': user.created_at,
                'last_active': user.last_login or user.created_at
            }
            
            if self.database:
                # Get auction stats
                active_auctions = await self.database.get_items_by_seller(user_id, status='active')
                completed_auctions = await self.database.get_items_by_seller(user_id, status='sold')
                
                stats.update({
                    'active_auctions': len(active_auctions),
                    'completed_auctions': len(completed_auctions),
                    'success_rate': len(completed_auctions) / max(1, len(active_auctions) + len(completed_auctions))
                })
            
            return stats
        except Exception as e:
            print(f"Error getting user stats: {e}")
            return {}
    
    def _validate_user_data(self, username: str, password: str) -> bool:
        """Validate user registration data."""
        try:
            # Username validation
            if not username or len(username) < 3 or len(username) > 30:
                return False
            
            if not username.replace('_', '').replace('-', '').isalnum():
                return False
            
            # Password validation
            if not password or len(password) < 8:
                return False
            
            return True
        except Exception:
            return False
    
    def _create_session(self, user: User) -> str:
        """Create a new user session."""
        session_token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        
        self.active_sessions[session_token] = {
            'user_id': user.id,
            'username': user.username,
            'created_at': datetime.now(timezone.utc),
            'expires_at': expires_at
        }
        
        return session_token
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions."""
        try:
            current_time = datetime.now(timezone.utc)
            expired_tokens = [
                token for token, session in self.active_sessions.items()
                if current_time > session['expires_at']
            ]
            
            for token in expired_tokens:
                del self.active_sessions[token]
        except Exception as e:
            print(f"Error cleaning up sessions: {e}")
    
    # Event handling
    def add_user_created_callback(self, callback):
        """Add callback for user created events."""
        self.user_created_callbacks.append(callback)
    
    def add_user_login_callback(self, callback):
        """Add callback for user login events."""
        self.user_login_callbacks.append(callback)
    
    def add_user_logout_callback(self, callback):
        """Add callback for user logout events."""
        self.user_logout_callbacks.append(callback)
    
    def _notify_user_created(self, user: User):
        """Notify all callbacks of user created event."""
        for callback in self.user_created_callbacks:
            try:
                callback(user)
            except Exception as e:
                print(f"Error in user created callback: {e}")
    
    def _notify_user_login(self, user: User):
        """Notify all callbacks of user login event."""
        for callback in self.user_login_callbacks:
            try:
                callback(user)
            except Exception as e:
                print(f"Error in user login callback: {e}")
    
    def _notify_user_logout(self, user: User):
        """Notify all callbacks of user logout event."""
        for callback in self.user_logout_callbacks:
            try:
                callback(user)
            except Exception as e:
                print(f"Error in user logout callback: {e}")


# Global user service instance
user_service = UserService()