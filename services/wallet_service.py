"""
Wallet service for Sapphire Exchange.
Handles multi-currency wallet operations and management.
"""
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import asdict
from datetime import datetime, timezone

from models.models import User
from blockchain.blockchain_manager import blockchain_manager
from config.app_config import app_config
from services.transaction_tracker import get_transaction_tracker


class WalletService:
    """Service for managing multi-currency wallets."""
    
    def __init__(self, database=None):
        """Initialize wallet service."""
        self.database = database
        self.blockchain = blockchain_manager
        
        # Event callbacks
        self.balance_change_callbacks = []
        self.transaction_callbacks = []
    
    async def create_wallet(self, user: User, mnemonic: Optional[str] = None) -> bool:
        """Create multi-currency wallet for user."""
        try:
            print(f"Creating wallet for user {user.username}")
            print(f"User addresses - Nano: {user.nano_address}, Arweave: {user.arweave_address}")
            
            # If addresses are already set, we just need to ensure wallet structures exist
            # For Nano, ensure we have the public key if we have an address
            if user.nano_address and not hasattr(user, 'public_key'):
                try:
                    # Generate Nano key pair (simplified - in real implementation would derive from seed)
                    seed = self.blockchain.nano_client.generate_seed()
                    private_key = self.blockchain.nano_client.seed_to_private_key(seed, 0)
                    public_key = self.blockchain.nano_client.private_key_to_public_key(private_key)
                    
                    # Verify the generated address matches the existing one
                    generated_address = self.blockchain.nano_client.public_key_to_address(public_key)
                    if generated_address == user.nano_address:
                        user.public_key = public_key.hex()
                        print(f"Nano public key generated for address: {user.nano_address}")
                    else:
                        print(f"Nano address mismatch, keeping existing: {user.nano_address}")
                except Exception as e:
                    print(f"Error generating Nano public key: {e}, continuing with existing address")
            
            # Store updated user data
            if self.database:
                await self.database.store_user(user)
            
            print(f"Wallet creation completed for user {user.username}")
            return True
        except Exception as e:
            print(f"Error creating wallet: {e}")
            return False
    
    async def get_balances(self, user: User) -> Dict[str, Any]:
        """Get balances for all currencies."""
        try:
            balances = {}
            
            # Get Nano balance
            if user.nano_address:
                nano_balance_data = await self.blockchain.get_nano_balance(user.nano_address)
                if nano_balance_data:
                    raw_balance = nano_balance_data.get('balance', '0')
                    nano_balance = self.blockchain.nano_client.raw_to_nano(raw_balance)
                    balances['NANO'] = {
                        'balance': nano_balance,
                        'balance_raw': raw_balance,
                        'formatted': f"{nano_balance:.6f} NANO",
                        'usd_value': await self._get_usd_value('NANO', nano_balance)
                    }
            
            # Calculate total USD value
            total_usd = sum(
                balance.get('usd_value', 0.0) 
                for balance in balances.values()
            )
            balances['total_usd'] = total_usd
            
            return balances
        except Exception as e:
            print(f"Error getting balances: {e}")
            return {}
    
    async def send_payment(self, user: User, to_address: str, amount: float, 
                          currency: str, memo: str = "") -> Optional[str]:
        """Send payment in specified currency."""
        try:
            if currency == "NANO":
                if not user.nano_address:
                    return None
                
                # Validate Nano address
                if not self.blockchain.nano_client.validate_address(to_address):
                    return None
                
                # Convert to raw
                amount_raw = self.blockchain.nano_client.nano_to_raw(amount)
                
                # Send Nano payment
                tx_id = await self.blockchain.send_nano(user.nano_address, to_address, amount_raw)
                if tx_id:
                    self._notify_transaction(user, currency, amount, to_address, tx_id)
                return tx_id
            
            return None
        except Exception as e:
            print(f"Error sending payment: {e}")
            return None
    
    async def generate_receive_address(self, user: User, currency: str) -> Optional[str]:
        """Generate new receiving address for specified currency."""
        try:
            if currency == "NANO":
                # Nano uses account-based model, return existing address
                return user.nano_address
            return None
        except Exception as e:
            print(f"Error generating address: {e}")
            return None
    
    async def get_transaction_history(self, user: User, currency: str, 
                                    limit: int = 50) -> List[Dict[str, Any]]:
        """Get transaction history for specified currency."""
        try:
            # This would typically query blockchain or database for transaction history
            # For now, return empty list as this requires more complex implementation
            return []
        except Exception as e:
            print(f"Error getting transaction history: {e}")
            return []
    
    async def validate_address(self, address: str, currency: str) -> bool:
        """Validate address for specified currency."""
        try:
            if currency == "NANO":
                return self.blockchain.nano_client.validate_address(address)
            return False
        except Exception as e:
            print(f"Error validating address: {e}")
            return False
    
    async def estimate_fee(self, currency: str, amount: float) -> float:
        """Estimate transaction fee for specified currency and amount."""
        try:
            if currency == "NANO":
                # Nano is feeless
                return 0.0
            return 0.0
        except Exception as e:
            print(f"Error estimating fee: {e}")
            return 0.0
    
    async def _get_usd_value(self, currency: str, amount: float) -> float:
        """Get USD value for currency amount."""
        try:
            # Mock conversion rates (in real implementation, use CoinGecko API)
            rates = {
                "NANO": 1.20   # $1.20 per NANO
            }
            
            rate = rates.get(currency, 0.0)
            return amount * rate
        except Exception:
            return 0.0
    
    def format_balance(self, amount: float, currency: str, decimals: Optional[int] = None) -> str:
        """Format balance for display."""
        try:
            if decimals is None:
                decimals = 6
            
            return f"{amount:.{decimals}f} {currency}"
        except Exception:
            return f"0.00 {currency}"
    
    def format_usd_value(self, usd_amount: float) -> str:
        """Format USD value for display."""
        try:
            return f"${usd_amount:.2f}"
        except Exception:
            return "$0.00"
    
    # Event handling
    def add_balance_change_callback(self, callback):
        """Add callback for balance change events."""
        self.balance_change_callbacks.append(callback)
    
    def add_transaction_callback(self, callback):
        """Add callback for transaction events."""
        self.transaction_callbacks.append(callback)
    
    def _notify_balance_change(self, user: User, currency: str, new_balance: float):
        """Notify callbacks of balance change."""
        for callback in self.balance_change_callbacks:
            try:
                callback(user, currency, new_balance)
            except Exception as e:
                print(f"Error in balance change callback: {e}")
    
    def _notify_transaction(self, user: User, currency: str, amount: float, 
                          to_address: str, tx_id: str):
        """Notify callbacks of transaction."""
        for callback in self.transaction_callbacks:
            try:
                callback(user, currency, amount, to_address, tx_id)
            except Exception as e:
                print(f"Error in transaction callback: {e}")
    
    async def track_outgoing_transaction(
        self,
        user: User,
        currency: str,
        amount: str,
        to_address: str,
        tx_hash: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Optional[str]:
        """Track an outgoing transaction."""
        try:
            tracker = await get_transaction_tracker()
            
            tx = tracker.create_transaction(
                user_id=user.id,
                currency=currency,
                tx_type="send",
                amount=amount,
                from_address=self._get_user_address(user, currency),
                to_address=to_address,
                tx_hash=tx_hash,
                metadata=metadata
            )
            
            # Start monitoring
            await tracker.track_pending_transaction(tx)
            
            print(f"Tracking outgoing {currency} transaction: {tx.id}")
            return tx.id
        except Exception as e:
            print(f"Error tracking outgoing transaction: {e}")
            return None
    
    async def track_incoming_transaction(
        self,
        user: User,
        currency: str,
        amount: str,
        from_address: str,
        tx_hash: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Optional[str]:
        """Track an incoming transaction (e.g., USDC deposit)."""
        try:
            tracker = await get_transaction_tracker()
            
            tx = tracker.create_transaction(
                user_id=user.id,
                currency=currency,
                tx_type="receive",
                amount=amount,
                from_address=from_address,
                to_address=self._get_user_address(user, currency),
                tx_hash=tx_hash,
                metadata=metadata
            )
            
            # Start monitoring
            await tracker.track_pending_transaction(tx)
            
            print(f"Tracking incoming {currency} transaction: {tx.id}")
            return tx.id
        except Exception as e:
            print(f"Error tracking incoming transaction: {e}")
            return None
    
    def get_pending_transactions(self, user: User, currency: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get pending transactions for user."""
        try:
            import asyncio
            # Note: This is synchronous, ideally should be async
            # For now, return empty list - caller should use async version
            return []
        except Exception as e:
            print(f"Error getting pending transactions: {e}")
            return []
    
    async def get_pending_transactions_async(
        self,
        user: User,
        currency: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get pending transactions for user (async)."""
        try:
            tracker = await get_transaction_tracker()
            txs = tracker.get_pending_transactions(user_id=user.id, currency=currency)
            return [tx.to_dict() for tx in txs]
        except Exception as e:
            print(f"Error getting pending transactions: {e}")
            return []
    
    async def get_transaction_history(
        self,
        user: User,
        currency: Optional[str] = None,
        limit: int = 50,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get transaction history for user."""
        try:
            tracker = await get_transaction_tracker()
            txs = tracker.get_transaction_history(
                user_id=user.id,
                currency=currency,
                limit=limit,
                days=days
            )
            return [tx.to_dict() for tx in txs]
        except Exception as e:
            print(f"Error getting transaction history: {e}")
            return []
    
    def _get_user_address(self, user: User, currency: str) -> str:
        """Get user address for currency."""
        if currency == "USDC":
            return user.usdc_address or ""
        elif currency == "ARWEAVE":
            return user.arweave_address or ""
        elif currency == "NANO":
            return user.nano_address or ""
        elif currency == "DOGE":
            return getattr(user, 'dogecoin_address', '') or ""
        return ""


# Global wallet service instance
wallet_service = WalletService()