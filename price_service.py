"""
Real-time Price Conversion Service for Sapphire Exchange.
Integrates with CoinGecko API for live cryptocurrency prices with caching and fallback.
"""
import asyncio
import aiohttp
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, field

from performance_manager import PerformanceManager


@dataclass
class PriceData:
    """Price data structure."""
    symbol: str
    usd_price: float
    change_24h: float
    last_updated: datetime
    source: str = "coingecko"
    volume_24h: Optional[float] = None
    market_cap: Optional[float] = None


class PriceConversionService:
    """Real-time cryptocurrency price conversion service."""
    
    def __init__(self, performance_manager: PerformanceManager = None):
        self.performance_manager = performance_manager or PerformanceManager()
        
        # CoinGecko API configuration
        self.coingecko_base_url = "https://api.coingecko.com/api/v3"
        self.request_timeout = 10
        self.cache_duration = 300  # 5 minutes
        
        # Currency mapping
        self.currency_map = {
            'nano': 'nano',
            'doge': 'dogecoin',
            'dogecoin': 'dogecoin',
            'arweave': 'arweave',
            'ar': 'arweave',
            'bitcoin': 'bitcoin',
            'btc': 'bitcoin',
            'ethereum': 'ethereum',
            'eth': 'ethereum'
        }
        
        # Fallback prices (updated periodically)
        self.fallback_prices = {
            'nano': 1.20,
            'dogecoin': 0.08,
            'arweave': 8.50,
            'bitcoin': 43000.00,
            'ethereum': 2600.00
        }
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0  # 1 second between requests
        
        # Price history for trend analysis
        self.price_history = {}
        
    async def get_price(self, currency: str, vs_currency: str = 'usd') -> Optional[PriceData]:
        """Get current price for a cryptocurrency.
        
        Args:
            currency: Cryptocurrency symbol (nano, doge, arweave, etc.)
            vs_currency: Target currency (default: usd)
            
        Returns:
            PriceData object or None if failed
        """
        currency_lower = currency.lower()
        coin_id = self.currency_map.get(currency_lower)
        
        if not coin_id:
            return None
        
        # Check cache first
        cache_key = f"price_{coin_id}_{vs_currency}"
        cached_price = self.performance_manager.get_cached_data(cache_key)
        
        if cached_price and isinstance(cached_price, PriceData):
            # Check if cache is still valid
            age = (datetime.now(timezone.utc) - cached_price.last_updated).total_seconds()
            if age < self.cache_duration:
                return cached_price
        
        # Fetch from API
        try:
            price_data = await self._fetch_from_coingecko(coin_id, vs_currency)
            if price_data:
                # Cache the result
                self.performance_manager.set_cached_data(
                    cache_key, price_data, ttl_ms=self.cache_duration * 1000
                )
                
                # Update price history
                self._update_price_history(coin_id, price_data.usd_price)
                
                return price_data
        except Exception as e:
            print(f"Error fetching price for {currency}: {e}")
        
        # Fallback to stored prices
        fallback_price = self.fallback_prices.get(coin_id)
        if fallback_price:
            return PriceData(
                symbol=currency_lower,
                usd_price=fallback_price,
                change_24h=0.0,
                last_updated=datetime.now(timezone.utc),
                source="fallback"
            )
        
        return None
    
    async def get_multiple_prices(self, currencies: List[str], 
                                vs_currency: str = 'usd') -> Dict[str, PriceData]:
        """Get prices for multiple cryptocurrencies.
        
        Args:
            currencies: List of cryptocurrency symbols
            vs_currency: Target currency (default: usd)
            
        Returns:
            Dict mapping currency to PriceData
        """
        # Filter valid currencies
        valid_currencies = [c for c in currencies if c.lower() in self.currency_map]
        coin_ids = [self.currency_map[c.lower()] for c in valid_currencies]
        
        if not coin_ids:
            return {}
        
        # Check cache for all currencies
        results = {}
        uncached_coins = []
        
        for currency, coin_id in zip(valid_currencies, coin_ids):
            cache_key = f"price_{coin_id}_{vs_currency}"
            cached_price = self.performance_manager.get_cached_data(cache_key)
            
            if cached_price and isinstance(cached_price, PriceData):
                age = (datetime.now(timezone.utc) - cached_price.last_updated).total_seconds()
                if age < self.cache_duration:
                    results[currency.lower()] = cached_price
                    continue
            
            uncached_coins.append((currency, coin_id))
        
        # Fetch uncached prices
        if uncached_coins:
            try:
                coin_ids_to_fetch = [coin_id for _, coin_id in uncached_coins]
                fetched_prices = await self._fetch_multiple_from_coingecko(
                    coin_ids_to_fetch, vs_currency
                )
                
                for currency, coin_id in uncached_coins:
                    if coin_id in fetched_prices:
                        price_data = fetched_prices[coin_id]
                        results[currency.lower()] = price_data
                        
                        # Cache the result
                        cache_key = f"price_{coin_id}_{vs_currency}"
                        self.performance_manager.set_cached_data(
                            cache_key, price_data, ttl_ms=self.cache_duration * 1000
                        )
                        
                        # Update price history
                        self._update_price_history(coin_id, price_data.usd_price)
                    else:
                        # Use fallback
                        fallback_price = self.fallback_prices.get(coin_id)
                        if fallback_price:
                            results[currency.lower()] = PriceData(
                                symbol=currency.lower(),
                                usd_price=fallback_price,
                                change_24h=0.0,
                                last_updated=datetime.now(timezone.utc),
                                source="fallback"
                            )
                            
            except Exception as e:
                print(f"Error fetching multiple prices: {e}")
                
                # Use fallback for all uncached
                for currency, coin_id in uncached_coins:
                    fallback_price = self.fallback_prices.get(coin_id)
                    if fallback_price:
                        results[currency.lower()] = PriceData(
                            symbol=currency.lower(),
                            usd_price=fallback_price,
                            change_24h=0.0,
                            last_updated=datetime.now(timezone.utc),
                            source="fallback"
                        )
        
        return results
    
    async def convert_amount(self, amount: float, from_currency: str, 
                           to_currency: str = 'usd') -> Optional[float]:
        """Convert amount from one currency to another.
        
        Args:
            amount: Amount to convert
            from_currency: Source currency
            to_currency: Target currency (default: usd)
            
        Returns:
            Converted amount or None if conversion failed
        """
        if from_currency.lower() == to_currency.lower():
            return amount
        
        # Get price data
        price_data = await self.get_price(from_currency, to_currency)
        if price_data:
            return amount * price_data.usd_price
        
        return None
    
    async def get_price_trend(self, currency: str, hours: int = 24) -> Dict:
        """Get price trend data for a currency.
        
        Args:
            currency: Cryptocurrency symbol
            hours: Number of hours to look back
            
        Returns:
            Dict containing trend information
        """
        currency_lower = currency.lower()
        coin_id = self.currency_map.get(currency_lower)
        
        if not coin_id or coin_id not in self.price_history:
            return {'trend': 'unknown', 'change_percent': 0.0}
        
        history = self.price_history[coin_id]
        if len(history) < 2:
            return {'trend': 'insufficient_data', 'change_percent': 0.0}
        
        # Calculate trend from recent history
        recent_prices = [entry['price'] for entry in history[-10:]]  # Last 10 entries
        
        if len(recent_prices) >= 2:
            start_price = recent_prices[0]
            end_price = recent_prices[-1]
            change_percent = ((end_price - start_price) / start_price) * 100
            
            if change_percent > 5:
                trend = 'strong_up'
            elif change_percent > 1:
                trend = 'up'
            elif change_percent < -5:
                trend = 'strong_down'
            elif change_percent < -1:
                trend = 'down'
            else:
                trend = 'stable'
            
            return {
                'trend': trend,
                'change_percent': change_percent,
                'start_price': start_price,
                'end_price': end_price,
                'data_points': len(recent_prices)
            }
        
        return {'trend': 'unknown', 'change_percent': 0.0}
    
    async def _fetch_from_coingecko(self, coin_id: str, vs_currency: str) -> Optional[PriceData]:
        """Fetch price from CoinGecko API."""
        await self._rate_limit()
        
        url = f"{self.coingecko_base_url}/simple/price"
        params = {
            'ids': coin_id,
            'vs_currencies': vs_currency,
            'include_24hr_change': 'true',
            'include_24hr_vol': 'true',
            'include_market_cap': 'true'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, 
                                 timeout=aiohttp.ClientTimeout(total=self.request_timeout)) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if coin_id in data:
                        coin_data = data[coin_id]
                        return PriceData(
                            symbol=coin_id,
                            usd_price=coin_data.get(vs_currency, 0.0),
                            change_24h=coin_data.get(f'{vs_currency}_24h_change', 0.0),
                            volume_24h=coin_data.get(f'{vs_currency}_24h_vol'),
                            market_cap=coin_data.get(f'{vs_currency}_market_cap'),
                            last_updated=datetime.now(timezone.utc),
                            source="coingecko"
                        )
                
                return None
    
    async def _fetch_multiple_from_coingecko(self, coin_ids: List[str], 
                                           vs_currency: str) -> Dict[str, PriceData]:
        """Fetch multiple prices from CoinGecko API."""
        await self._rate_limit()
        
        url = f"{self.coingecko_base_url}/simple/price"
        params = {
            'ids': ','.join(coin_ids),
            'vs_currencies': vs_currency,
            'include_24hr_change': 'true',
            'include_24hr_vol': 'true',
            'include_market_cap': 'true'
        }
        
        results = {}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params,
                                 timeout=aiohttp.ClientTimeout(total=self.request_timeout)) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for coin_id in coin_ids:
                        if coin_id in data:
                            coin_data = data[coin_id]
                            results[coin_id] = PriceData(
                                symbol=coin_id,
                                usd_price=coin_data.get(vs_currency, 0.0),
                                change_24h=coin_data.get(f'{vs_currency}_24h_change', 0.0),
                                volume_24h=coin_data.get(f'{vs_currency}_24h_vol'),
                                market_cap=coin_data.get(f'{vs_currency}_market_cap'),
                                last_updated=datetime.now(timezone.utc),
                                source="coingecko"
                            )
        
        return results
    
    async def _rate_limit(self):
        """Implement rate limiting for API requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - time_since_last)
        
        self.last_request_time = time.time()
    
    def _update_price_history(self, coin_id: str, price: float):
        """Update price history for trend analysis."""
        if coin_id not in self.price_history:
            self.price_history[coin_id] = []
        
        history = self.price_history[coin_id]
        
        # Add new price point
        history.append({
            'price': price,
            'timestamp': datetime.now(timezone.utc)
        })
        
        # Keep only last 100 entries
        if len(history) > 100:
            self.price_history[coin_id] = history[-100:]
    
    def update_fallback_prices(self, prices: Dict[str, float]):
        """Update fallback prices manually."""
        for currency, price in prices.items():
            currency_lower = currency.lower()
            coin_id = self.currency_map.get(currency_lower)
            if coin_id:
                self.fallback_prices[coin_id] = price
    
    def get_supported_currencies(self) -> List[str]:
        """Get list of supported currencies."""
        return list(self.currency_map.keys())
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        return self.performance_manager.get_performance_stats()


class PriceAlertService:
    """Service for price alerts and notifications."""
    
    def __init__(self, price_service: PriceConversionService):
        self.price_service = price_service
        self.alerts = {}  # user_id -> list of alerts
        self.alert_id_counter = 0
    
    def create_alert(self, user_id: str, currency: str, target_price: float,
                    condition: str = 'above', enabled: bool = True) -> str:
        """Create a price alert.
        
        Args:
            user_id: User identifier
            currency: Cryptocurrency symbol
            target_price: Target price in USD
            condition: 'above' or 'below'
            enabled: Whether alert is active
            
        Returns:
            Alert ID
        """
        alert_id = str(self.alert_id_counter)
        self.alert_id_counter += 1
        
        alert = {
            'id': alert_id,
            'user_id': user_id,
            'currency': currency.lower(),
            'target_price': target_price,
            'condition': condition,
            'enabled': enabled,
            'created_at': datetime.now(timezone.utc),
            'triggered': False,
            'triggered_at': None
        }
        
        if user_id not in self.alerts:
            self.alerts[user_id] = []
        
        self.alerts[user_id].append(alert)
        return alert_id
    
    async def check_alerts(self) -> List[Dict]:
        """Check all active alerts and return triggered ones."""
        triggered_alerts = []
        
        # Get all unique currencies from alerts
        currencies = set()
        for user_alerts in self.alerts.values():
            for alert in user_alerts:
                if alert['enabled'] and not alert['triggered']:
                    currencies.add(alert['currency'])
        
        if not currencies:
            return triggered_alerts
        
        # Get current prices
        prices = await self.price_service.get_multiple_prices(list(currencies))
        
        # Check each alert
        for user_id, user_alerts in self.alerts.items():
            for alert in user_alerts:
                if not alert['enabled'] or alert['triggered']:
                    continue
                
                currency = alert['currency']
                if currency not in prices:
                    continue
                
                current_price = prices[currency].usd_price
                target_price = alert['target_price']
                condition = alert['condition']
                
                triggered = False
                if condition == 'above' and current_price >= target_price:
                    triggered = True
                elif condition == 'below' and current_price <= target_price:
                    triggered = True
                
                if triggered:
                    alert['triggered'] = True
                    alert['triggered_at'] = datetime.now(timezone.utc)
                    alert['triggered_price'] = current_price
                    
                    triggered_alerts.append({
                        'alert_id': alert['id'],
                        'user_id': user_id,
                        'currency': currency,
                        'target_price': target_price,
                        'current_price': current_price,
                        'condition': condition,
                        'message': f"{currency.upper()} is now ${current_price:.4f} ({condition} ${target_price:.4f})"
                    })
        
        return triggered_alerts
    
    def get_user_alerts(self, user_id: str) -> List[Dict]:
        """Get all alerts for a user."""
        return self.alerts.get(user_id, [])
    
    def delete_alert(self, user_id: str, alert_id: str) -> bool:
        """Delete a price alert."""
        if user_id not in self.alerts:
            return False
        
        user_alerts = self.alerts[user_id]
        for i, alert in enumerate(user_alerts):
            if alert['id'] == alert_id:
                del user_alerts[i]
                return True
        
        return False
    
    def toggle_alert(self, user_id: str, alert_id: str) -> bool:
        """Toggle alert enabled/disabled state."""
        if user_id not in self.alerts:
            return False
        
        for alert in self.alerts[user_id]:
            if alert['id'] == alert_id:
                alert['enabled'] = not alert['enabled']
                if alert['enabled']:
                    alert['triggered'] = False  # Reset trigger state
                return True
        
        return False


# Global price service instance
_price_service_instance = None

def get_price_service() -> PriceConversionService:
    """Get global price service instance."""
    global _price_service_instance
    if _price_service_instance is None:
        _price_service_instance = PriceConversionService()
    return _price_service_instance