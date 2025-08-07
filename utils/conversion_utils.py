"""
Conversion utilities for Sapphire Exchange.
Handles currency conversions, unit conversions, and data format conversions.
"""
import asyncio
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional, Union, Any
from datetime import datetime, timezone

from services.price_service import PriceConversionService


class ConversionUtils:
    """Utility class for various conversions."""
    
    def __init__(self, price_service: PriceConversionService = None):
        """Initialize conversion utils."""
        self.price_service = price_service or PriceConversionService()
        
        # Nano conversion constants
        self.NANO_RAW_RATIO = 10**30  # 1 NANO = 10^30 raw
        
        # DOGE conversion constants
        self.DOGE_SATOSHI_RATIO = 10**8  # 1 DOGE = 10^8 satoshis
    
    # Currency conversions
    async def convert_currency(self, amount: float, from_currency: str, 
                              to_currency: str) -> Optional[float]:
        """Convert amount between currencies."""
        try:
            if from_currency.upper() == to_currency.upper():
                return amount
            
            return await self.price_service.convert_amount(amount, from_currency, to_currency)
        except Exception as e:
            print(f"Error converting currency: {e}")
            return None
    
    async def get_usd_value(self, amount: float, currency: str) -> Optional[float]:
        """Get USD value of amount in specified currency."""
        try:
            return await self.convert_currency(amount, currency, 'USD')
        except Exception as e:
            print(f"Error getting USD value: {e}")
            return None
    
    async def convert_to_primary_currency(self, amount: float, from_currency: str) -> Optional[float]:
        """Convert amount to primary currency (DOGE)."""
        try:
            return await self.convert_currency(amount, from_currency, 'DOGE')
        except Exception as e:
            print(f"Error converting to primary currency: {e}")
            return None
    
    # Nano conversions
    def nano_to_raw(self, nano_amount: Union[str, float, Decimal]) -> str:
        """Convert NANO to raw units."""
        try:
            if isinstance(nano_amount, str):
                nano_decimal = Decimal(nano_amount)
            else:
                nano_decimal = Decimal(str(nano_amount))
            
            raw_amount = nano_decimal * self.NANO_RAW_RATIO
            return str(int(raw_amount))
        except Exception as e:
            print(f"Error converting NANO to raw: {e}")
            return "0"
    
    def raw_to_nano(self, raw_amount: Union[str, int]) -> str:
        """Convert raw units to NANO."""
        try:
            raw_decimal = Decimal(str(raw_amount))
            nano_amount = raw_decimal / self.NANO_RAW_RATIO
            
            # Round to 6 decimal places for display
            return str(nano_amount.quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP))
        except Exception as e:
            print(f"Error converting raw to NANO: {e}")
            return "0.000000"
    
    # DOGE conversions
    def doge_to_satoshi(self, doge_amount: Union[str, float, Decimal]) -> int:
        """Convert DOGE to satoshis."""
        try:
            if isinstance(doge_amount, str):
                doge_decimal = Decimal(doge_amount)
            else:
                doge_decimal = Decimal(str(doge_amount))
            
            satoshi_amount = doge_decimal * self.DOGE_SATOSHI_RATIO
            return int(satoshi_amount)
        except Exception as e:
            print(f"Error converting DOGE to satoshi: {e}")
            return 0
    
    def satoshi_to_doge(self, satoshi_amount: Union[str, int]) -> str:
        """Convert satoshis to DOGE."""
        try:
            satoshi_decimal = Decimal(str(satoshi_amount))
            doge_amount = satoshi_decimal / self.DOGE_SATOSHI_RATIO
            
            # Round to 8 decimal places
            return str(doge_amount.quantize(Decimal('0.00000001'), rounding=ROUND_HALF_UP))
        except Exception as e:
            print(f"Error converting satoshi to DOGE: {e}")
            return "0.00000000"
    
    # Formatting utilities
    def format_currency(self, amount: Union[str, float, Decimal], currency: str, 
                       decimal_places: Optional[int] = None) -> str:
        """Format currency amount for display."""
        try:
            if isinstance(amount, str):
                amount_decimal = Decimal(amount)
            else:
                amount_decimal = Decimal(str(amount))
            
            # Default decimal places by currency
            if decimal_places is None:
                decimal_places = {
                    'USD': 2,
                    'DOGE': 8,
                    'NANO': 6,
                    'BTC': 8,
                    'ETH': 6
                }.get(currency.upper(), 8)
            
            # Create format string
            format_str = '0.' + '0' * decimal_places
            formatted_amount = amount_decimal.quantize(
                Decimal(format_str), rounding=ROUND_HALF_UP
            )
            
            # Add currency symbol/code
            currency_symbols = {
                'USD': '$',
                'DOGE': 'Ð',
                'NANO': 'Ӿ',
                'BTC': '₿',
                'ETH': 'Ξ'
            }
            
            symbol = currency_symbols.get(currency.upper(), currency.upper())
            
            if currency.upper() == 'USD':
                return f"{symbol}{formatted_amount:,}"
            else:
                return f"{formatted_amount:,} {symbol}"
                
        except Exception as e:
            print(f"Error formatting currency: {e}")
            return f"0 {currency.upper()}"
    
    def format_large_number(self, number: Union[str, float, int], precision: int = 2) -> str:
        """Format large numbers with K, M, B suffixes."""
        try:
            if isinstance(number, str):
                num = float(number)
            else:
                num = float(number)
            
            if abs(num) >= 1_000_000_000:
                return f"{num / 1_000_000_000:.{precision}f}B"
            elif abs(num) >= 1_000_000:
                return f"{num / 1_000_000:.{precision}f}M"
            elif abs(num) >= 1_000:
                return f"{num / 1_000:.{precision}f}K"
            else:
                return f"{num:.{precision}f}"
                
        except Exception as e:
            print(f"Error formatting large number: {e}")
            return "0"
    
    def format_percentage(self, value: Union[str, float], precision: int = 2) -> str:
        """Format percentage value."""
        try:
            if isinstance(value, str):
                num = float(value)
            else:
                num = float(value)
            
            formatted = f"{num:.{precision}f}%"
            
            # Add color indicators
            if num > 0:
                return f"+{formatted}"
            else:
                return formatted
                
        except Exception as e:
            print(f"Error formatting percentage: {e}")
            return "0.00%"
    
    # Time conversions
    def format_time_remaining(self, end_time: str) -> str:
        """Format time remaining until end time."""
        try:
            # Parse end time
            if end_time.endswith('Z'):
                end_time = end_time[:-1] + '+00:00'
            
            end_dt = datetime.fromisoformat(end_time)
            current_dt = datetime.now(timezone.utc)
            
            # Ensure timezone aware
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=timezone.utc)
            
            time_diff = end_dt - current_dt
            
            if time_diff.total_seconds() <= 0:
                return "Ended"
            
            days = time_diff.days
            hours, remainder = divmod(time_diff.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            
            if days > 0:
                return f"{days}d {hours}h {minutes}m"
            elif hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
                
        except Exception as e:
            print(f"Error formatting time remaining: {e}")
            return "Unknown"
    
    def format_datetime(self, dt_str: str, format_type: str = 'short') -> str:
        """Format datetime string for display."""
        try:
            # Parse datetime
            if dt_str.endswith('Z'):
                dt_str = dt_str[:-1] + '+00:00'
            
            dt = datetime.fromisoformat(dt_str)
            
            # Ensure timezone aware
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            
            # Convert to local time (simplified - using UTC for now)
            local_dt = dt
            
            if format_type == 'short':
                return local_dt.strftime('%m/%d/%Y %H:%M')
            elif format_type == 'long':
                return local_dt.strftime('%B %d, %Y at %I:%M %p')
            elif format_type == 'date_only':
                return local_dt.strftime('%m/%d/%Y')
            elif format_type == 'time_only':
                return local_dt.strftime('%H:%M')
            else:
                return local_dt.strftime('%m/%d/%Y %H:%M')
                
        except Exception as e:
            print(f"Error formatting datetime: {e}")
            return "Unknown"
    
    # Data conversions
    def dict_to_query_string(self, data: Dict[str, Any]) -> str:
        """Convert dictionary to query string."""
        try:
            params = []
            for key, value in data.items():
                if value is not None:
                    params.append(f"{key}={value}")
            return "&".join(params)
        except Exception as e:
            print(f"Error converting dict to query string: {e}")
            return ""
    
    def bytes_to_human_readable(self, bytes_size: int) -> str:
        """Convert bytes to human readable format."""
        try:
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if bytes_size < 1024.0:
                    return f"{bytes_size:.1f} {unit}"
                bytes_size /= 1024.0
            return f"{bytes_size:.1f} PB"
        except Exception as e:
            print(f"Error converting bytes: {e}")
            return "0 B"
    
    def truncate_string(self, text: str, max_length: int, suffix: str = "...") -> str:
        """Truncate string to maximum length."""
        try:
            if len(text) <= max_length:
                return text
            
            truncated_length = max_length - len(suffix)
            if truncated_length <= 0:
                return suffix[:max_length]
            
            return text[:truncated_length] + suffix
        except Exception as e:
            print(f"Error truncating string: {e}")
            return text
    
    def normalize_search_query(self, query: str) -> str:
        """Normalize search query."""
        try:
            # Convert to lowercase
            normalized = query.lower().strip()
            
            # Remove extra whitespace
            normalized = ' '.join(normalized.split())
            
            # Remove special characters (keep alphanumeric and spaces)
            normalized = ''.join(c for c in normalized if c.isalnum() or c.isspace())
            
            return normalized
        except Exception as e:
            print(f"Error normalizing search query: {e}")
            return ""
    
    # Validation helpers
    def is_valid_decimal(self, value: str, max_decimal_places: int = 8) -> bool:
        """Check if string is a valid decimal with max decimal places."""
        try:
            decimal_value = Decimal(value)
            
            # Check decimal places
            if decimal_value.as_tuple().exponent < -max_decimal_places:
                return False
            
            return True
        except Exception:
            return False
    
    def clamp_value(self, value: Union[int, float], min_val: Union[int, float], 
                   max_val: Union[int, float]) -> Union[int, float]:
        """Clamp value between min and max."""
        return max(min_val, min(value, max_val))


# Global conversion utils instance
conversion_utils = ConversionUtils()


# Convenience functions
async def convert_currency(amount: float, from_currency: str, to_currency: str) -> Optional[float]:
    """Convert amount between currencies."""
    return await conversion_utils.convert_currency(amount, from_currency, to_currency)


def format_currency(amount: Union[str, float, Decimal], currency: str, 
                   decimal_places: Optional[int] = None) -> str:
    """Format currency amount for display."""
    return conversion_utils.format_currency(amount, currency, decimal_places)


def format_time_remaining(end_time: str) -> str:
    """Format time remaining until end time."""
    return conversion_utils.format_time_remaining(end_time)


def nano_to_raw(nano_amount: Union[str, float, Decimal]) -> str:
    """Convert NANO to raw units."""
    return conversion_utils.nano_to_raw(nano_amount)


def raw_to_nano(raw_amount: Union[str, int]) -> str:
    """Convert raw units to NANO."""
    return conversion_utils.raw_to_nano(raw_amount)