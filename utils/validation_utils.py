"""
Validation utilities for Sapphire Exchange.
Provides data validation functions for various entities and inputs.
"""
import re
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from decimal import Decimal, InvalidOperation

from config.app_config import app_config


class ValidationError(Exception):
    """Custom validation error."""
    pass


class Validator:
    """Main validation class with various validation methods."""
    
    # Regular expressions for validation
    EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    USERNAME_REGEX = re.compile(r'^[a-zA-Z0-9_-]{3,30}$')
    NANO_ADDRESS_REGEX = re.compile(r'^nano_[13][13456789abcdefghijkmnopqrstuwxyz]{59}$')
    ARWEAVE_ADDRESS_REGEX = re.compile(r'^[a-zA-Z0-9_-]{43}$')
    DOGE_ADDRESS_REGEX = re.compile(r'^D[5-9A-HJ-NP-U][1-9A-HJ-NP-Za-km-z]{32}$')
    TRANSACTION_HASH_REGEX = re.compile(r'^[a-fA-F0-9]{64}$')
    UUID_REGEX = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email address format."""
        if not email or not isinstance(email, str):
            return False
        
        if len(email) > 100:
            return False
        
        return bool(Validator.EMAIL_REGEX.match(email))
    
    @staticmethod
    def validate_username(username: str) -> bool:
        """Validate username format."""
        if not username or not isinstance(username, str):
            return False
        
        return bool(Validator.USERNAME_REGEX.match(username))
    
    @staticmethod
    def validate_password(password: str) -> Dict[str, Any]:
        """Validate password strength."""
        result = {
            'valid': False,
            'errors': [],
            'strength': 'weak'
        }
        
        if not password or not isinstance(password, str):
            result['errors'].append('Password is required')
            return result
        
        # Length check
        if len(password) < 8:
            result['errors'].append('Password must be at least 8 characters long')
        
        if len(password) > 128:
            result['errors'].append('Password must be less than 128 characters')
        
        # Character requirements
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password)
        
        strength_score = sum([has_upper, has_lower, has_digit, has_special])
        
        if strength_score < 2:
            result['errors'].append('Password must contain at least 2 of: uppercase, lowercase, digit, special character')
        
        # Determine strength
        if len(password) >= 12 and strength_score >= 3:
            result['strength'] = 'strong'
        elif len(password) >= 10 and strength_score >= 2:
            result['strength'] = 'medium'
        
        result['valid'] = len(result['errors']) == 0
        return result
    
    @staticmethod
    def validate_nano_address(address: str) -> bool:
        """Validate Nano address format."""
        if not address or not isinstance(address, str):
            return False
        
        return bool(Validator.NANO_ADDRESS_REGEX.match(address))
    
    @staticmethod
    def validate_arweave_address(address: str) -> bool:
        """Validate Arweave address format."""
        if not address or not isinstance(address, str):
            return False
        
        return bool(Validator.ARWEAVE_ADDRESS_REGEX.match(address))
    
    @staticmethod
    def validate_doge_address(address: str) -> bool:
        """Validate Dogecoin address format."""
        if not address or not isinstance(address, str):
            return False
        
        return bool(Validator.DOGE_ADDRESS_REGEX.match(address))
    
    @staticmethod
    def validate_transaction_hash(tx_hash: str) -> bool:
        """Validate transaction hash format."""
        if not tx_hash or not isinstance(tx_hash, str):
            return False
        
        return bool(Validator.TRANSACTION_HASH_REGEX.match(tx_hash))
    
    @staticmethod
    def validate_uuid(uuid_str: str) -> bool:
        """Validate UUID format."""
        if not uuid_str or not isinstance(uuid_str, str):
            return False
        
        return bool(Validator.UUID_REGEX.match(uuid_str))
    
    @staticmethod
    def validate_amount(amount: Union[str, float, Decimal], min_amount: float = 0.0, 
                       max_amount: Optional[float] = None) -> Dict[str, Any]:
        """Validate monetary amount."""
        result = {
            'valid': False,
            'errors': [],
            'normalized_amount': None
        }
        
        try:
            # Convert to Decimal for precise arithmetic
            if isinstance(amount, str):
                decimal_amount = Decimal(amount)
            else:
                decimal_amount = Decimal(str(amount))
            
            # Check if positive
            if decimal_amount < 0:
                result['errors'].append('Amount cannot be negative')
            
            # Check minimum
            if decimal_amount < Decimal(str(min_amount)):
                result['errors'].append(f'Amount must be at least {min_amount}')
            
            # Check maximum
            if max_amount is not None and decimal_amount > Decimal(str(max_amount)):
                result['errors'].append(f'Amount cannot exceed {max_amount}')
            
            # Check decimal places (max 8 for crypto)
            if decimal_amount.as_tuple().exponent < -8:
                result['errors'].append('Amount cannot have more than 8 decimal places')
            
            result['normalized_amount'] = float(decimal_amount)
            result['valid'] = len(result['errors']) == 0
            
        except (InvalidOperation, ValueError, TypeError):
            result['errors'].append('Invalid amount format')
        
        return result
    
    @staticmethod
    def validate_datetime(dt_str: str) -> bool:
        """Validate ISO datetime string."""
        if not dt_str or not isinstance(dt_str, str):
            return False
        
        try:
            # Try parsing with timezone
            if dt_str.endswith('Z'):
                dt_str = dt_str[:-1] + '+00:00'
            
            datetime.fromisoformat(dt_str)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_future_datetime(dt_str: str, min_future_minutes: int = 5) -> Dict[str, Any]:
        """Validate that datetime is in the future."""
        result = {
            'valid': False,
            'errors': []
        }
        
        if not Validator.validate_datetime(dt_str):
            result['errors'].append('Invalid datetime format')
            return result
        
        try:
            # Parse datetime
            if dt_str.endswith('Z'):
                dt_str = dt_str[:-1] + '+00:00'
            
            target_dt = datetime.fromisoformat(dt_str)
            current_dt = datetime.now(timezone.utc)
            
            # Ensure timezone aware
            if target_dt.tzinfo is None:
                target_dt = target_dt.replace(tzinfo=timezone.utc)
            
            # Check if in future
            time_diff = (target_dt - current_dt).total_seconds()
            min_seconds = min_future_minutes * 60
            
            if time_diff < min_seconds:
                result['errors'].append(f'Datetime must be at least {min_future_minutes} minutes in the future')
            
            result['valid'] = len(result['errors']) == 0
            
        except Exception as e:
            result['errors'].append(f'Error validating datetime: {str(e)}')
        
        return result
    
    @staticmethod
    def validate_item_data(item_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate auction item data."""
        result = {
            'valid': False,
            'errors': []
        }
        
        required_fields = ['title', 'description', 'auction_end']
        for field in required_fields:
            if field not in item_data or not item_data[field]:
                result['errors'].append(f'{field} is required')
        
        has_starting_price = (
            item_data.get('starting_price_doge') is not None or
            item_data.get('starting_price_usdc') is not None or
            item_data.get('starting_price') is not None
        )
        if not has_starting_price:
            result['errors'].append('Starting price is required')
        
        title = item_data.get('title', '')
        if title:
            if len(title) < 3:
                result['errors'].append('Title must be at least 3 characters')
            elif len(title) > app_config.ui.max_title_length:
                result['errors'].append(f'Title cannot exceed {app_config.ui.max_title_length} characters')
        
        description = item_data.get('description', '')
        if description and len(description) > app_config.ui.max_description_length:
            result['errors'].append(f'Description cannot exceed {app_config.ui.max_description_length} characters')
        
        starting_price = (
            item_data.get('starting_price_doge') or
            item_data.get('starting_price_usdc') or
            item_data.get('starting_price')
        )
        if starting_price is not None:
            price_validation = Validator.validate_amount(starting_price, min_amount=0.0)
            if not price_validation['valid']:
                result['errors'].extend(price_validation['errors'])
        
        auction_end = item_data.get('auction_end')
        if auction_end:
            end_validation = Validator.validate_future_datetime(auction_end, min_future_minutes=30)
            if not end_validation['valid']:
                result['errors'].extend(end_validation['errors'])
        
        tags = item_data.get('tags', [])
        if tags:
            if len(tags) > app_config.ui.max_tags_per_item:
                result['errors'].append(f'Cannot have more than {app_config.ui.max_tags_per_item} tags')
            
            for tag in tags:
                if not isinstance(tag, str):
                    result['errors'].append('All tags must be strings')
                elif len(tag) > app_config.ui.max_tag_length:
                    result['errors'].append(f'Tag "{tag}" exceeds maximum length of {app_config.ui.max_tag_length}')
        
        category = item_data.get('category', '')
        if category and len(category) > 50:
            result['errors'].append('Category cannot exceed 50 characters')
        
        shipping_cost = (
            item_data.get('shipping_cost_doge') or
            item_data.get('shipping_cost_usdc') or
            item_data.get('shipping_cost')
        )
        if shipping_cost is not None:
            shipping_validation = Validator.validate_amount(shipping_cost, min_amount=0.0)
            if not shipping_validation['valid']:
                result['errors'].extend([f'Shipping cost: {error}' for error in shipping_validation['errors']])
        
        result['valid'] = len(result['errors']) == 0
        return result
    
    @staticmethod
    def validate_bid_data(bid_data: Dict[str, Any], current_highest_bid: float = 0.0) -> Dict[str, Any]:
        """Validate bid data."""
        result = {
            'valid': False,
            'errors': []
        }
        
        # Required fields
        required_fields = ['item_id', 'bidder_id', 'amount_doge']
        for field in required_fields:
            if field not in bid_data or not bid_data[field]:
                result['errors'].append(f'{field} is required')
        
        # Item ID validation
        item_id = bid_data.get('item_id')
        if item_id and not Validator.validate_uuid(item_id):
            result['errors'].append('Invalid item ID format')
        
        # Bidder ID validation
        bidder_id = bid_data.get('bidder_id')
        if bidder_id and not Validator.validate_uuid(bidder_id):
            result['errors'].append('Invalid bidder ID format')
        
        # Amount validation
        amount = bid_data.get('amount_doge')
        if amount is not None:
            amount_validation = Validator.validate_amount(amount, min_amount=0.01)
            if not amount_validation['valid']:
                result['errors'].extend(amount_validation['errors'])
            elif amount_validation['normalized_amount'] <= current_highest_bid:
                result['errors'].append(f'Bid must be higher than current highest bid of {current_highest_bid}')
        
        result['valid'] = len(result['errors']) == 0
        return result
    
    @staticmethod
    def validate_user_data(user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate user registration data."""
        result = {
            'valid': False,
            'errors': []
        }
        
        # Required fields
        required_fields = ['username', 'password']
        for field in required_fields:
            if field not in user_data or not user_data[field]:
                result['errors'].append(f'{field} is required')
        
        # Username validation
        username = user_data.get('username')
        if username and not Validator.validate_username(username):
            result['errors'].append('Username must be 3-30 characters and contain only letters, numbers, hyphens, and underscores')
        
        # Password validation
        password = user_data.get('password')
        if password:
            password_validation = Validator.validate_password(password)
            if not password_validation['valid']:
                result['errors'].extend(password_validation['errors'])
        
        # Optional fields validation
        bio = user_data.get('bio')
        if bio and len(bio) > app_config.ui.max_bio_length:
            result['errors'].append(f'Bio cannot exceed {app_config.ui.max_bio_length} characters')
        
        location = user_data.get('location')
        if location and len(location) > 100:
            result['errors'].append('Location cannot exceed 100 characters')
        
        website = user_data.get('website')
        if website and len(website) > 200:
            result['errors'].append('Website URL cannot exceed 200 characters')
        
        result['valid'] = len(result['errors']) == 0
        return result
    
    @staticmethod
    def sanitize_string(input_str: str, max_length: Optional[int] = None) -> str:
        """Sanitize string input."""
        if not isinstance(input_str, str):
            return ''
        
        # Remove null bytes and control characters
        sanitized = ''.join(char for char in input_str if ord(char) >= 32 or char in '\n\r\t')
        
        # Strip whitespace
        sanitized = sanitized.strip()
        
        # Truncate if needed
        if max_length and len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized
    
    @staticmethod
    def validate_data_hash(data: Dict[str, Any], expected_hash: str) -> bool:
        """Validate data integrity using hash."""
        try:
            # Create a consistent string representation
            data_str = str(sorted(data.items()))
            calculated_hash = hashlib.sha256(data_str.encode()).hexdigest()
            return calculated_hash == expected_hash
        except Exception:
            return False


# Convenience functions
def validate_email(email: str) -> bool:
    """Validate email address."""
    return Validator.validate_email(email)


def validate_username(username: str) -> bool:
    """Validate username."""
    return Validator.validate_username(username)


def validate_password(password: str) -> Dict[str, Any]:
    """Validate password strength."""
    return Validator.validate_password(password)


def validate_amount(amount: Union[str, float, Decimal], min_amount: float = 0.0, 
                   max_amount: Optional[float] = None) -> Dict[str, Any]:
    """Validate monetary amount."""
    return Validator.validate_amount(amount, min_amount, max_amount)


def sanitize_string(input_str: str, max_length: Optional[int] = None) -> str:
    """Sanitize string input."""
    return Validator.sanitize_string(input_str, max_length)