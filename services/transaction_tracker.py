"""
Transaction Tracker Service for Sapphire Exchange.
Tracks pending, completed, and failed transactions across all blockchain networks.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
import asyncio
import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class Transaction:
    """Represents a single transaction."""
    
    id: str
    user_id: str
    currency: str
    type: str
    amount: str
    from_address: str
    to_address: str
    status: str
    tx_hash: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: Optional[str] = None
    confirmed_at: Optional[str] = None
    confirmations: int = 0
    retry_count: int = 0
    error_message: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Transaction':
        """Create from dictionary."""
        return cls(**data)


class TransactionTracker:
    """Service for tracking transactions across blockchains."""
    
    def __init__(self, storage_path: Optional[str] = None):
        """Initialize transaction tracker."""
        self.storage_path = Path(storage_path or "data/transactions.json")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # In-memory cache for active transactions
        self.pending_transactions: Dict[str, Transaction] = {}
        self.completed_transactions: Dict[str, Transaction] = {}
        
        # Configuration
        self.confirmation_targets = {
            "USDC": 6,      # Solana: usually 1-2 slots, use 6 for safety
            "ARWEAVE": 10,  # Arweave: 10 confirmations
            "DOGE": 6,      # Dogecoin: 6 confirmations
            "NANO": 1       # Nano: instant finality
        }
        
        self.polling_intervals = {
            "USDC": 2,      # Check every 2 seconds
            "ARWEAVE": 5,   # Check every 5 seconds
            "DOGE": 3,      # Check every 3 seconds
            "NANO": 1       # Check every 1 second
        }
        
        self.max_retries = {
            "USDC": 5,
            "ARWEAVE": 3,
            "DOGE": 4,
            "NANO": 3
        }
        
        # Active polling tasks
        self.polling_tasks: Dict[str, asyncio.Task] = {}
        self.http_session: Optional[aiohttp.ClientSession] = None
        
        # Load existing transactions
        self._load_transactions()
    
    async def initialize(self):
        """Initialize async resources."""
        if not self.http_session:
            try:
                self.http_session = aiohttp.ClientSession()
                logger.debug("Transaction tracker HTTP session initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize HTTP session: {e}. This is OK, will retry on first use.")
                self.http_session = None
    
    async def _get_http_session(self) -> Optional[aiohttp.ClientSession]:
        """Get or lazily create the HTTP session."""
        if not self.http_session:
            try:
                self.http_session = aiohttp.ClientSession()
            except Exception as e:
                logger.warning(f"Failed to create HTTP session: {e}")
                return None
        return self.http_session
    
    async def cleanup(self):
        """Cleanup async resources."""
        # Cancel all polling tasks
        for task in self.polling_tasks.values():
            if not task.done():
                task.cancel()
        
        # Close HTTP session
        if self.http_session:
            try:
                await self.http_session.close()
            except Exception as e:
                logger.warning(f"Error closing HTTP session: {e}")
    
    def create_transaction(
        self,
        user_id: str,
        currency: str,
        tx_type: str,
        amount: str,
        from_address: str,
        to_address: str,
        tx_hash: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Transaction:
        """Create and track a new transaction."""
        import uuid
        
        tx = Transaction(
            id=str(uuid.uuid4()),
            user_id=user_id,
            currency=currency,
            type=tx_type,
            amount=amount,
            from_address=from_address,
            to_address=to_address,
            status="pending",
            tx_hash=tx_hash,
            metadata=metadata or {}
        )
        
        self.pending_transactions[tx.id] = tx
        self._save_transactions()
        
        logger.info(f"Created transaction {tx.id}: {amount} {currency} from {from_address}")
        
        return tx
    
    async def track_pending_transaction(self, tx: Transaction) -> None:
        """Start tracking a pending transaction."""
        try:
            if not self.http_session:
                await self.initialize()
            
            # Start polling for confirmations
            if tx.currency not in self.polling_tasks or self.polling_tasks[tx.currency].done():
                task = asyncio.create_task(
                    self._poll_confirmations(tx.currency)
                )
                self.polling_tasks[tx.currency] = task
            
            logger.info(f"Started tracking transaction {tx.id}")
        except Exception as e:
            logger.error(f"Error tracking transaction: {e}")
    
    async def _poll_confirmations(self, currency: str) -> None:
        """Poll for transaction confirmations."""
        try:
            while True:
                # Get all pending transactions for this currency
                pending = [
                    tx for tx in self.pending_transactions.values()
                    if tx.currency == currency
                ]
                
                if not pending:
                    await asyncio.sleep(5)
                    continue
                
                for tx in pending:
                    try:
                        confirmations = await self._check_confirmations(tx)
                        tx.confirmations = confirmations
                        tx.updated_at = datetime.now(timezone.utc).isoformat()
                        
                        # Check if confirmed
                        if confirmations >= self.confirmation_targets.get(currency, 6):
                            await self._mark_confirmed(tx)
                        
                    except Exception as e:
                        tx.retry_count += 1
                        tx.error_message = str(e)
                        tx.updated_at = datetime.now(timezone.utc).isoformat()
                        
                        if tx.retry_count >= self.max_retries.get(currency, 3):
                            await self.mark_failed(tx.id, str(e))
                        else:
                            self._save_transactions()
                        
                        logger.warning(f"Error checking confirmations for {tx.id}: {e}")
                
                # Wait before next poll
                interval = self.polling_intervals.get(currency, 5)
                await asyncio.sleep(interval)
        
        except asyncio.CancelledError:
            logger.info(f"Polling task cancelled for {currency}")
        except Exception as e:
            logger.error(f"Error in confirmation polling: {e}")
    
    async def _check_confirmations(self, tx: Transaction) -> int:
        """Check confirmation count for a transaction."""
        if not tx.tx_hash:
            return 0
        
        try:
            if tx.currency == "USDC":
                return await self._check_solana_confirmations(tx.tx_hash)
            elif tx.currency == "ARWEAVE":
                return await self._check_arweave_confirmations(tx.tx_hash)
            elif tx.currency == "DOGE":
                return await self._check_dogecoin_confirmations(tx.tx_hash)
            elif tx.currency == "NANO":
                return await self._check_nano_confirmations(tx.tx_hash)
        except Exception as e:
            logger.error(f"Error checking confirmations for {tx.currency}: {e}")
        
        return 0
    
    async def _check_solana_confirmations(self, tx_hash: str) -> int:
        """Check Solana transaction confirmations."""
        try:
            if not self.http_session:
                return 0
            
            rpc_url = "https://api.mainnet-beta.solana.com"
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTransaction",
                "params": [tx_hash, {"encoding": "json"}]
            }
            
            async with self.http_session.post(
                rpc_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if "result" in data and data["result"]:
                        # Transaction found
                        if data["result"].get("meta", {}).get("err") is None:
                            # Get current slot for confirmation estimate
                            return 6  # Assume confirmed if no error
                        else:
                            return 0
                return 0
        except Exception as e:
            logger.error(f"Error checking Solana confirmations: {e}")
            return 0
    
    async def _check_arweave_confirmations(self, tx_hash: str) -> int:
        """Check Arweave transaction confirmations."""
        try:
            if not self.http_session:
                return 0
            
            # Try multiple Arweave nodes
            nodes = [
                "https://arweave.net",
                "https://g8way.arweave.net"
            ]
            
            for node in nodes:
                try:
                    url = f"{node}/tx/{tx_hash}/status"
                    async with self.http_session.get(
                        url,
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            # Arweave returns number_of_confirmations
                            return data.get("number_of_confirmations", 0)
                except Exception:
                    continue
            
            return 0
        except Exception as e:
            logger.error(f"Error checking Arweave confirmations: {e}")
            return 0
    
    async def _check_dogecoin_confirmations(self, tx_hash: str) -> int:
        """Check Dogecoin transaction confirmations."""
        try:
            # This would use a Dogecoin RPC node or API
            # For now, return 0 - needs blockchain integration
            return 0
        except Exception as e:
            logger.error(f"Error checking Dogecoin confirmations: {e}")
            return 0
    
    async def _check_nano_confirmations(self, tx_hash: str) -> int:
        """Check Nano transaction confirmations."""
        try:
            if not self.http_session:
                return 0
            
            rpc_url = "https://mynano.ninja/api"
            payload = {
                "action": "block_info",
                "json_block": "true",
                "hash": tx_hash
            }
            
            async with self.http_session.post(
                rpc_url,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    # Nano has instant finality, return confirmed
                    if "error" not in data:
                        return 1
            
            return 0
        except Exception as e:
            logger.error(f"Error checking Nano confirmations: {e}")
            return 0
    
    async def _mark_confirmed(self, tx: Transaction) -> None:
        """Mark transaction as confirmed."""
        tx.status = "confirmed"
        tx.confirmed_at = datetime.now(timezone.utc).isoformat()
        tx.updated_at = tx.confirmed_at
        
        # Move to completed
        if tx.id in self.pending_transactions:
            del self.pending_transactions[tx.id]
        self.completed_transactions[tx.id] = tx
        
        self._save_transactions()
        logger.info(f"Transaction {tx.id} confirmed with {tx.confirmations} confirmations")
    
    def get_transaction(self, tx_id: str) -> Optional[Transaction]:
        """Get transaction by ID."""
        if tx_id in self.pending_transactions:
            return self.pending_transactions[tx_id]
        if tx_id in self.completed_transactions:
            return self.completed_transactions[tx_id]
        return None
    
    def get_pending_transactions(self, user_id: Optional[str] = None, currency: Optional[str] = None) -> List[Transaction]:
        """Get pending transactions, optionally filtered."""
        txs = list(self.pending_transactions.values())
        
        if user_id:
            txs = [tx for tx in txs if tx.user_id == user_id]
        if currency:
            txs = [tx for tx in txs if tx.currency == currency]
        
        return sorted(txs, key=lambda x: x.created_at, reverse=True)
    
    def get_transaction_history(
        self,
        user_id: Optional[str] = None,
        currency: Optional[str] = None,
        limit: int = 50,
        days: int = 30
    ) -> List[Transaction]:
        """Get transaction history."""
        # Combine pending and completed
        all_txs = list(self.pending_transactions.values()) + list(self.completed_transactions.values())
        
        # Filter by user
        if user_id:
            all_txs = [tx for tx in all_txs if tx.user_id == user_id]
        
        # Filter by currency
        if currency:
            all_txs = [tx for tx in all_txs if tx.currency == currency]
        
        # Filter by date
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        all_txs = [tx for tx in all_txs if datetime.fromisoformat(tx.created_at) > cutoff]
        
        # Sort by date descending and limit
        return sorted(all_txs, key=lambda x: x.created_at, reverse=True)[:limit]
    
    async def retry_transaction(self, tx_id: str) -> bool:
        """Retry a failed transaction."""
        tx = self.get_transaction(tx_id)
        if not tx:
            return False
        
        if tx.retry_count >= self.max_retries.get(tx.currency, 3):
            logger.error(f"Transaction {tx_id} has exceeded max retries")
            return False
        
        tx.retry_count += 1
        tx.status = "pending"
        tx.updated_at = datetime.now(timezone.utc).isoformat()
        self.pending_transactions[tx_id] = tx
        
        # Remove from completed if there
        if tx_id in self.completed_transactions:
            del self.completed_transactions[tx_id]
        
        self._save_transactions()
        logger.info(f"Retrying transaction {tx_id} (attempt {tx.retry_count})")
        
        return True
    
    async def mark_failed(self, tx_id: str, error: str) -> bool:
        """Mark transaction as failed."""
        tx = self.get_transaction(tx_id)
        if not tx:
            return False
        
        tx.status = "failed"
        tx.error_message = error
        tx.updated_at = datetime.now(timezone.utc).isoformat()
        
        if tx_id in self.pending_transactions:
            del self.pending_transactions[tx_id]
        self.completed_transactions[tx_id] = tx
        
        self._save_transactions()
        logger.error(f"Transaction {tx_id} marked as failed: {error}")
        
        return True
    
    def _load_transactions(self) -> None:
        """Load transactions from storage."""
        try:
            if self.storage_path.exists():
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    
                    for tx_data in data.get('pending', []):
                        tx = Transaction.from_dict(tx_data)
                        self.pending_transactions[tx.id] = tx
                    
                    for tx_data in data.get('completed', []):
                        tx = Transaction.from_dict(tx_data)
                        self.completed_transactions[tx.id] = tx
                
                logger.info(
                    f"Loaded {len(self.pending_transactions)} pending and "
                    f"{len(self.completed_transactions)} completed transactions"
                )
        except Exception as e:
            logger.error(f"Error loading transactions: {e}")
    
    def _save_transactions(self) -> None:
        """Save transactions to storage."""
        try:
            data = {
                'pending': [tx.to_dict() for tx in self.pending_transactions.values()],
                'completed': [tx.to_dict() for tx in self.completed_transactions.values()]
            }
            
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving transactions: {e}")


# Global instance
transaction_tracker = TransactionTracker()


async def get_transaction_tracker() -> TransactionTracker:
    """Get transaction tracker singleton."""
    await transaction_tracker.initialize()
    return transaction_tracker
