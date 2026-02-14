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
from security.account_backup_manager import account_backup_manager
from blockchain.unified_wallet_generator import UnifiedWalletGenerator


class UserService:
    """Service for managing users and authentication."""
    
    def __init__(self, database=None, security_manager: SecurityManager = None, blockchain=None):
        """Initialize user service."""
        self.database = database
        self.blockchain = blockchain or blockchain_manager
        self.security = security_manager or SecurityManager()
        self.wallet_generator = UnifiedWalletGenerator()
        
        # Active sessions
        self.active_sessions = {}
        
        # Event callbacks
        self.user_created_callbacks = []
        self.user_login_callbacks = []
        self.user_logout_callbacks = []
    
    async def create_user(self, username: str, password: str, 
                         nano_address: str = None, arweave_address: str = None, 
                         usdc_address: str = None) -> Optional[User]:
        """Create a new user account.
        
        Args:
            username: Username for the account
            password: Password for the account
            nano_address: Optional pre-generated Nano address
            arweave_address: Optional pre-generated Arweave address
            usdc_address: Optional pre-generated USDC address
        
        Returns:
            User object if successful, None otherwise
        """
        try:
            # Validate input
            if not self._validate_user_data(username, password):
                return None
            
            # Check if user already exists by username
            if await self.get_user_by_username(username):
                print(f"User {username} already exists")
                return None
            
            # Use provided addresses or generate new ones
            try:
                if not nano_address or not arweave_address:
                    # Generate blockchain addresses sequentially with delays to avoid pool contention
                    if not nano_address:
                        nano_address = await self.blockchain.generate_nano_address()
                        if not nano_address:
                            raise RuntimeError("Failed to generate Nano address")
                        print(f"Generated Nano address: {nano_address}")
                    else:
                        print(f"[CREATE_USER] Using provided Nano address: {nano_address}")
                
                    # Delay to ensure pool connection is fully released
                    try:
                        await asyncio.sleep(0.5)
                    except RuntimeError:
                        pass
                    
                    # Generate Arweave address
                    if not arweave_address:
                        arweave_address = await self.blockchain.generate_arweave_address()
                        if not arweave_address:
                            raise RuntimeError("Failed to generate Arweave address")
                        print(f"Generated Arweave address: {arweave_address}")
                    else:
                        print(f"[CREATE_USER] Using provided Arweave address: {arweave_address}")
                    
                    # Delay to ensure pool connection is fully released
                    try:
                        await asyncio.sleep(0.5)
                    except RuntimeError:
                        pass
                    
                    # Generate USDC address (optional)
                    if not usdc_address:
                        usdc_address = await self.blockchain.generate_usdc_address()
                        if usdc_address:
                            print(f"Generated USDC address: {usdc_address}")
                    else:
                        print(f"[CREATE_USER] Using provided USDC address: {usdc_address}")
                
            except Exception as e:
                print(f"Failed to generate blockchain addresses: {e}")
                print(f"  Nano: {nano_address}")
                print(f"  Arweave: {arweave_address}")
                print(f"  USDC: {usdc_address}")
                return None
            
            print(f"Generated addresses - Nano: {nano_address}, Arweave: {arweave_address}, USDC: {usdc_address}")
            
            # Hash password
            password_hash = self.security.hash_password(password)
            
            # Create user
            user = User(
                username=username,
                password_hash=password_hash,
                nano_address=nano_address,
                arweave_address=arweave_address,
                usdc_address=usdc_address,
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
                
                # Create encrypted account backup using Nano mnemonic (placeholder - will be set during login)
                try:
                    print(f"Account backup will be created after user sets up their wallet")
                except Exception as e:
                    print(f"Error preparing account backup: {e}")
                
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
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        try:
            if self.database:
                return await self.database.get_user_by_email(email)
            return None
        except Exception as e:
            print(f"Error getting user by email: {e}")
            return None
    
    async def recover_user_from_mnemonic(self, nano_mnemonic: str) -> Optional[Tuple[User, str, Dict[str, Any]]]:
        """
        Recover user account from Nano mnemonic.
        Derives Nano address from mnemonic and retrieves encrypted backup.
        
        Args:
            nano_mnemonic: BIP39 Nano mnemonic phrase
        
        Returns:
            Tuple of (user, session_token, wallet_data) or None if recovery fails
        """
        try:
            # Validate mnemonic
            is_valid, message = self.wallet_generator.validate_mnemonic(nano_mnemonic)
            if not is_valid:
                print(f"❌ [RECOVERY] Invalid mnemonic: {message}")
                return None
            
            print(f"✓ [RECOVERY] Mnemonic validated")
            print(f"[RECOVERY] Mnemonic word count: {len(nano_mnemonic.split())}")
            
            # Generate wallets from mnemonic to get Nano address
            success, wallet_data = self.wallet_generator.generate_from_mnemonic(nano_mnemonic)
            print(f"[RECOVERY] Wallet generation: success={success}, wallets_present={list(wallet_data.keys()) if wallet_data else 'None'}")
            
            # Log the derived address
            if success and wallet_data and 'nano' in wallet_data:
                derived_nano = wallet_data['nano'].get('address')
                print(f"[RECOVERY] Derived Nano address: {derived_nano}")
            
            if not success:
                print(f"❌ [RECOVERY] Wallet generation failed (success=False)")
                return None
            
            if not wallet_data:
                print(f"❌ [RECOVERY] Wallet generation returned empty data")
                return None
                
            if 'nano' not in wallet_data:
                print(f"❌ [RECOVERY] Nano wallet not in generated data. Available: {list(wallet_data.keys())}")
                return None
            
            nano_address = wallet_data['nano'].get('address')
            if not nano_address:
                print(f"❌ [RECOVERY] Failed to derive Nano address from wallet data")
                return None
            
            print(f"✓ [RECOVERY] Recovered Nano address: {nano_address}")
            
            # Try to restore account from backup
            print(f"\n{'='*60}")
            print(f"[RECOVERY] Attempting to restore backup for address: {nano_address}")
            print(f"[RECOVERY] Backup directory: {account_backup_manager.backup_dir}")
            
            # List all available backups
            try:
                all_backups = list(account_backup_manager.backup_dir.glob("*.account.enc"))
                print(f"[RECOVERY] Total backups in directory: {len(all_backups)}")
                if all_backups:
                    print(f"[RECOVERY] Available backups:")
                    for backup in all_backups[:10]:  # Show first 10
                        print(f"  • {backup.name}")
                    if len(all_backups) > 10:
                        print(f"  ... and {len(all_backups) - 10} more")
            except Exception as e:
                print(f"[RECOVERY] Error listing backups: {e}")
            
            print(f"{'='*60}\n")
            
            success, account_data = await account_backup_manager.restore_account_from_backup(
                nano_address, nano_mnemonic
            )
            
            if not success:
                print(f"❌ [RECOVERY] Backup restoration failed (success=False)")
                return None
            
            if account_data is None:
                print(f"❌ [RECOVERY] Backup restoration returned None")
                return None
            
            print(f"✓ [RECOVERY] Account backup found for user: {account_data.get('username')}")
            
            # Reconstruct User object from account data
            user = User.from_dict({
                'id': account_data.get('user_id'),
                'username': account_data.get('username'),
                'password_hash': '',
                'nano_address': account_data.get('nano_address'),
                'arweave_address': account_data.get('arweave_address'),
                'usdc_address': account_data.get('usdc_address'),
                'email': account_data.get('email'),
                'created_at': account_data.get('created_at'),
                'updated_at': account_data.get('updated_at'),
                'is_active': True,
                'reputation_score': account_data.get('reputation_score', 0.0),
                'total_sales': account_data.get('total_sales', 0),
                'total_purchases': account_data.get('total_purchases', 0),
                'bio': account_data.get('bio', ''),
                'location': account_data.get('location', ''),
                'website': account_data.get('website', ''),
                'avatar_url': account_data.get('avatar_url'),
                'preferences': account_data.get('preferences', {}),
                'inventory': account_data.get('inventory', []),
                'metadata': account_data.get('metadata', {}),
                'arweave_profile_uri': account_data.get('arweave_profile_uri'),
            })
            
            # Create session token
            session_token = self._create_session(user)
            
            # Update last login
            user.last_login = datetime.now(timezone.utc).isoformat()
            if self.database:
                await self.database.update_user(user)
            
            # Notify callbacks
            self._notify_user_login(user)
            
            # Regenerate all wallets from mnemonic for display during recovery
            # (This ensures all supported chains are available, not just what was backed up)
            print(f"\n[RECOVERY] Regenerating all wallets from mnemonic for recovery display...")
            full_wallet_success, full_wallet_data = self.wallet_generator.generate_from_mnemonic(
                nano_mnemonic,
                assets=['nano', 'arweave', 'solana']
            )
            
            if full_wallet_success and full_wallet_data:
                print(f"[RECOVERY] Regenerated wallets: {list(full_wallet_data.keys())}")
                # Use regenerated wallets which include all chains
                recovered_wallet_data = full_wallet_data
            else:
                # Fallback to backed up wallets if regeneration fails
                recovered_wallet_data = account_data.get('wallets', wallet_data)
                print(f"[RECOVERY] Using backed up wallets: {list(recovered_wallet_data.keys()) if isinstance(recovered_wallet_data, dict) else 'N/A'}")
            
            return user, session_token, recovered_wallet_data
        
        except Exception as e:
            print(f"Error recovering user from mnemonic: {e}")
            return None
    
    async def create_account_backup_for_user(self, user: User, nano_mnemonic: str, 
                                            wallet_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Create encrypted account backup after user setup.
        Called after Arweave profile post and wallet creation.
        Includes all private keys for full account recovery.
        
        Args:
            user: User object
            nano_mnemonic: Nano mnemonic (used as encryption key)
            wallet_data: Wallet information for all blockchains
        
        Returns:
            Tuple of (success, message)
        """
        try:
            print(f"\n{'='*60}")
            print(f"[BACKUP_CREATE] Starting backup creation for user: {user.username}")
            print(f"[BACKUP_CREATE] Nano address: {user.nano_address}")
            print(f"[BACKUP_CREATE] Wallet data type: {type(wallet_data)}")
            print(f"[BACKUP_CREATE] Wallet data keys: {list(wallet_data.keys()) if isinstance(wallet_data, dict) else 'N/A'}")
            
            # Extract private keys from wallet_data for backup
            private_keys = {}
            
            # Wallet data format from unified_wallet_generator
            if isinstance(wallet_data, dict):
                # If it's the new format with chain/address structure
                for chain, chain_data in wallet_data.items():
                    if isinstance(chain_data, dict):
                        if 'private_key' in chain_data:
                            private_keys[chain] = chain_data['private_key']
                        if 'seed' in chain_data:
                            private_keys[f'{chain}_seed'] = chain_data['seed']
            
            print(f"[BACKUP_CREATE] Extracted {len(private_keys)} private keys: {list(private_keys.keys())}")
            
            success, backup_path = await account_backup_manager.create_account_backup(
                user, user.nano_address, nano_mnemonic, wallet_data, private_keys, user.arweave_profile_uri
            )
            
            if success:
                print(f"✓ [BACKUP_CREATE] Account backup created successfully: {backup_path}")
            else:
                print(f"❌ [BACKUP_CREATE] Failed to create account backup: {backup_path}")
            
            print(f"{'='*60}\n")
            return success, backup_path
        
        except Exception as e:
            print(f"❌ [BACKUP_CREATE] Error creating account backup: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return False, str(e)
    
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