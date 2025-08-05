"""
User repository for Sapphire Exchange.
Handles user data persistence and retrieval.
"""
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from models import User
from .base_repository import ArweaveRepository


class UserRepository(ArweaveRepository):
    """Repository for user data management."""
    
    def __init__(self, database=None, performance_manager=None, blockchain_manager=None):
        """Initialize user repository."""
        super().__init__(database, performance_manager, blockchain_manager)
        self.entity_type = "user"
    
    async def create(self, user: User) -> Optional[User]:
        """Create a new user."""
        try:
            # Add timestamps
            self._add_timestamps(user, is_update=False)
            
            # Store on Arweave (public profile only)
            public_data = self._get_public_profile(user)
            tags = self._create_tags(
                "user-profile",
                user.id,
                Username=user.username,
                CreatedAt=user.created_at
            )
            
            tx_id = await self._store_on_arweave(public_data, tags)
            if tx_id:
                user.arweave_profile_uri = tx_id
                
                # Store in local database (full data including private fields)
                if self.database:
                    await self.database.store_user(user)
                
                # Cache the user
                cache_key = self._get_cache_key("user", user.id)
                self._cache_entity(cache_key, user)
                
                # Cache by username for quick lookup
                username_cache_key = self._get_cache_key("user_username", user.username.lower())
                self._cache_entity(username_cache_key, user)
                
                return user
            
            return None
        except Exception as e:
            print(f"Error creating user: {e}")
            return None
    
    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        try:
            # Check cache first
            cache_key = self._get_cache_key("user", user_id)
            cached_user = self._get_cached_entity(cache_key)
            if cached_user:
                return cached_user
            
            # Get from database
            if self.database:
                user = await self.database.get_user(user_id)
                if user:
                    # Cache the result
                    self._cache_entity(cache_key, user)
                    return user
            
            return None
        except Exception as e:
            print(f"Error getting user by ID: {e}")
            return None
    
    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        try:
            # Check cache first
            cache_key = self._get_cache_key("user_username", username.lower())
            cached_user = self._get_cached_entity(cache_key)
            if cached_user:
                return cached_user
            
            # Get from database
            if self.database:
                user = await self.database.get_user_by_username(username)
                if user:
                    # Cache the result
                    self._cache_entity(cache_key, user)
                    
                    # Also cache by ID
                    id_cache_key = self._get_cache_key("user", user.id)
                    self._cache_entity(id_cache_key, user)
                    
                    return user
            
            return None
        except Exception as e:
            print(f"Error getting user by username: {e}")
            return None
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        try:
            # Email lookups are not cached for privacy
            if self.database:
                return await self.database.get_user_by_email(email)
            return None
        except Exception as e:
            print(f"Error getting user by email: {e}")
            return None
    
    async def update(self, user: User) -> bool:
        """Update an existing user."""
        try:
            # Add update timestamp
            self._add_timestamps(user, is_update=True)
            
            # Update public profile on Arweave
            public_data = self._get_public_profile(user)
            tags = self._create_tags(
                "user-profile-update",
                user.id,
                Username=user.username,
                UpdatedAt=user.updated_at
            )
            
            tx_id = await self._store_on_arweave(public_data, tags)
            if tx_id:
                # Update database
                if self.database:
                    await self.database.update_user(user)
                
                # Invalidate and update cache
                cache_key = self._get_cache_key("user", user.id)
                self._cache_entity(cache_key, user)
                
                username_cache_key = self._get_cache_key("user_username", user.username.lower())
                self._cache_entity(username_cache_key, user)
                
                return True
            
            return False
        except Exception as e:
            print(f"Error updating user: {e}")
            return False
    
    async def delete(self, user_id: str) -> bool:
        """Delete a user (soft delete)."""
        try:
            user = await self.get_by_id(user_id)
            if not user:
                return False
            
            # Soft delete - mark as inactive
            user.is_active = False
            user.deleted_at = datetime.now(timezone.utc).isoformat()
            
            # Update in database
            if self.database:
                await self.database.update_user(user)
            
            # Invalidate cache
            cache_key = self._get_cache_key("user", user_id)
            self._invalidate_cache(cache_key)
            
            username_cache_key = self._get_cache_key("user_username", user.username.lower())
            self._invalidate_cache(username_cache_key)
            
            return True
        except Exception as e:
            print(f"Error deleting user: {e}")
            return False
    
    async def list(self, limit: int = 20, offset: int = 0, **filters) -> List[User]:
        """List users with pagination and filters."""
        try:
            limit, offset = self._validate_pagination(limit, offset)
            
            if self.database:
                return await self.database.get_users(limit, offset, **filters)
            return []
        except Exception as e:
            print(f"Error listing users: {e}")
            return []
    
    async def search_users(self, query: str, limit: int = 20) -> List[User]:
        """Search users by username or bio."""
        try:
            limit, _ = self._validate_pagination(limit, 0)
            
            if self.database:
                return await self.database.search_users(query, limit)
            return []
        except Exception as e:
            print(f"Error searching users: {e}")
            return []
    
    async def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get user statistics."""
        try:
            # Check cache first
            cache_key = self._get_cache_key("user_stats", user_id)
            cached_stats = self._get_cached_entity(cache_key)
            if cached_stats:
                return cached_stats
            
            user = await self.get_by_id(user_id)
            if not user:
                return {}
            
            stats = {
                'user_id': user_id,
                'username': user.username,
                'reputation_score': user.reputation_score,
                'total_sales': user.total_sales,
                'total_purchases': user.total_purchases,
                'member_since': user.created_at,
                'last_active': user.last_login or user.created_at,
                'is_active': user.is_active
            }
            
            # Get additional stats from database
            if self.database:
                # Get auction counts
                active_auctions = await self.database.count_items_by_seller(user_id, status='active')
                completed_auctions = await self.database.count_items_by_seller(user_id, status='sold')
                
                stats.update({
                    'active_auctions': active_auctions,
                    'completed_auctions': completed_auctions,
                    'success_rate': completed_auctions / max(1, active_auctions + completed_auctions)
                })
            
            # Cache stats for 5 minutes
            self._cache_entity(cache_key, stats, ttl_seconds=300)
            
            return stats
        except Exception as e:
            print(f"Error getting user stats: {e}")
            return {}
    
    async def update_reputation(self, user_id: str, change: float, reason: str) -> bool:
        """Update user reputation score."""
        try:
            user = await self.get_by_id(user_id)
            if not user:
                return False
            
            old_score = user.reputation_score
            user.reputation_score = max(0.0, user.reputation_score + change)
            
            # Log reputation change on Arweave
            reputation_log = {
                'user_id': user_id,
                'old_score': old_score,
                'new_score': user.reputation_score,
                'change': change,
                'reason': reason,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            tags = self._create_tags(
                "reputation-change",
                user_id,
                Change=str(change),
                Reason=reason
            )
            
            await self._store_on_arweave(reputation_log, tags)
            
            # Update user
            await self.update(user)
            
            # Invalidate stats cache
            stats_cache_key = self._get_cache_key("user_stats", user_id)
            self._invalidate_cache(stats_cache_key)
            
            return True
        except Exception as e:
            print(f"Error updating reputation: {e}")
            return False
    
    async def get_top_users(self, limit: int = 10, metric: str = 'reputation') -> List[User]:
        """Get top users by specified metric."""
        try:
            limit, _ = self._validate_pagination(limit, 0)
            
            if self.database:
                return await self.database.get_top_users(limit, metric)
            return []
        except Exception as e:
            print(f"Error getting top users: {e}")
            return []
    
    def _get_public_profile(self, user: User) -> Dict[str, Any]:
        """Get public profile data (excluding sensitive information)."""
        profile = user.to_dict()
        
        # Remove sensitive fields
        sensitive_fields = ['password_hash', 'email', 'private_key', 'seed_phrase']
        for field in sensitive_fields:
            profile.pop(field, None)
        
        return profile
    
    async def batch_create_users(self, users: List[User]) -> List[User]:
        """Create multiple users in batch."""
        try:
            operations = [self.create(user) for user in users]
            results = await self._batch_operation(operations)
            return self._filter_exceptions(results)
        except Exception as e:
            print(f"Error in batch create users: {e}")
            return []
    
    async def batch_update_users(self, users: List[User]) -> List[bool]:
        """Update multiple users in batch."""
        try:
            operations = [self.update(user) for user in users]
            results = await self._batch_operation(operations)
            return self._filter_exceptions(results)
        except Exception as e:
            print(f"Error in batch update users: {e}")
            return []