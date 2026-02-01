"""
Transaction tracker for monitoring blockchain transactions.
Maintains persistent transaction history and status tracking.
Supports Solana, Nano, and Arweave.
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
from enum import Enum
from datetime import datetime
from pathlib import Path
import json
import sqlite3
import asyncio


class TransactionStatus(Enum):
    """Transaction lifecycle status."""
    CREATED = "created"
    SIGNED = "signed"
    SUBMITTED = "submitted"
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FINALIZED = "finalized"
    FAILED = "failed"
    CANCELED = "canceled"


@dataclass
class TransactionRecord:
    """Transaction history record."""
    tx_id: str
    chain: str
    asset: str
    from_address: str
    to_address: str
    amount: float
    status: TransactionStatus
    signature: str
    broadcast_hash: Optional[str] = None
    created_at: str = ""
    submitted_at: Optional[str] = None
    confirmed_at: Optional[str] = None
    finalized_at: Optional[str] = None
    confirmations: int = 0
    block_height: Optional[int] = None
    gas_used: Optional[float] = None
    fee: Optional[float] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TransactionRecord':
        """Create from dictionary."""
        data = data.copy()
        data['status'] = TransactionStatus(data['status'])
        return cls(**data)


class TransactionTracker:
    """Track blockchain transactions with persistent storage."""
    
    DEFAULT_DB_PATH = "~/.sapphire_exchange/transactions.db"
    
    def __init__(self, db_path: str = None):
        """
        Initialize transaction tracker.
        
        Args:
            db_path: Path to SQLite database (default: ~/.sapphire_exchange/transactions.db)
        """
        self.db_path = Path(db_path or self.DEFAULT_DB_PATH).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.in_memory_cache: Dict[str, TransactionRecord] = {}
        
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database schema."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                tx_id TEXT PRIMARY KEY,
                chain TEXT NOT NULL,
                asset TEXT NOT NULL,
                from_address TEXT NOT NULL,
                to_address TEXT NOT NULL,
                amount REAL NOT NULL,
                status TEXT NOT NULL,
                signature TEXT NOT NULL,
                broadcast_hash TEXT,
                created_at TEXT NOT NULL,
                submitted_at TEXT,
                confirmed_at TEXT,
                finalized_at TEXT,
                confirmations INTEGER DEFAULT 0,
                block_height INTEGER,
                gas_used REAL,
                fee REAL,
                error TEXT,
                metadata TEXT,
                updated_at TEXT NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chain_status 
            ON transactions(chain, status)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_address 
            ON transactions(from_address, to_address)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_created_at 
            ON transactions(created_at)
        """)
        
        conn.commit()
        conn.close()
    
    async def track(self, record: TransactionRecord) -> bool:
        """
        Track new transaction.
        
        Args:
            record: TransactionRecord instance
        
        Returns:
            True if successful
        """
        try:
            if not record.created_at:
                record.created_at = datetime.utcnow().isoformat()
            
            self.in_memory_cache[record.tx_id] = record
            
            await asyncio.to_thread(self._save_to_database, record)
            
            return True
        
        except Exception:
            return False
    
    async def update_status(self, tx_id: str, status: TransactionStatus,
                          confirmations: int = 0, block_height: int = None,
                          error: str = None) -> bool:
        """
        Update transaction status.
        
        Args:
            tx_id: Transaction ID
            status: New transaction status
            confirmations: Number of confirmations
            block_height: Block height (if available)
            error: Error message (if failed)
        
        Returns:
            True if successful
        """
        try:
            record = self.in_memory_cache.get(tx_id)
            if not record:
                record = await asyncio.to_thread(self._load_from_database, tx_id)
            
            if not record:
                return False
            
            old_status = record.status
            record.status = status
            record.confirmations = confirmations
            record.block_height = block_height
            record.error = error
            
            now = datetime.utcnow().isoformat()
            
            if old_status != TransactionStatus.SUBMITTED and status == TransactionStatus.SUBMITTED:
                record.submitted_at = now
            
            if old_status not in [TransactionStatus.CONFIRMED, TransactionStatus.FINALIZED] and status == TransactionStatus.CONFIRMED:
                record.confirmed_at = now
            
            if old_status != TransactionStatus.FINALIZED and status == TransactionStatus.FINALIZED:
                record.finalized_at = now
            
            self.in_memory_cache[tx_id] = record
            await asyncio.to_thread(self._save_to_database, record)
            
            return True
        
        except Exception:
            return False
    
    async def get_transaction(self, tx_id: str) -> Optional[TransactionRecord]:
        """
        Get transaction by ID.
        
        Args:
            tx_id: Transaction ID
        
        Returns:
            TransactionRecord or None
        """
        if tx_id in self.in_memory_cache:
            return self.in_memory_cache[tx_id]
        
        return await asyncio.to_thread(self._load_from_database, tx_id)
    
    async def is_confirmed(self, tx_id: str, target_confirmations: int = 1) -> bool:
        """
        Check if transaction is confirmed.
        
        Args:
            tx_id: Transaction ID
            target_confirmations: Required confirmation count
        
        Returns:
            True if confirmed
        """
        record = await self.get_transaction(tx_id)
        if not record:
            return False
        
        return record.confirmations >= target_confirmations
    
    async def list_pending(self, chain: str = None, limit: int = 100) -> List[TransactionRecord]:
        """
        List pending transactions.
        
        Args:
            chain: Filter by chain (optional)
            limit: Maximum results
        
        Returns:
            List of pending TransactionRecords
        """
        return await asyncio.to_thread(
            self._list_by_status,
            [TransactionStatus.CREATED, TransactionStatus.SIGNED, TransactionStatus.SUBMITTED, TransactionStatus.PENDING],
            chain,
            limit
        )
    
    async def list_confirmed(self, chain: str = None, limit: int = 100) -> List[TransactionRecord]:
        """
        List confirmed transactions.
        
        Args:
            chain: Filter by chain (optional)
            limit: Maximum results
        
        Returns:
            List of confirmed TransactionRecords
        """
        return await asyncio.to_thread(
            self._list_by_status,
            [TransactionStatus.CONFIRMED, TransactionStatus.FINALIZED],
            chain,
            limit
        )
    
    async def list_failed(self, chain: str = None, limit: int = 100) -> List[TransactionRecord]:
        """
        List failed transactions.
        
        Args:
            chain: Filter by chain (optional)
            limit: Maximum results
        
        Returns:
            List of failed TransactionRecords
        """
        return await asyncio.to_thread(
            self._list_by_status,
            [TransactionStatus.FAILED, TransactionStatus.CANCELED],
            chain,
            limit
        )
    
    async def list_by_address(self, address: str, chain: str = None,
                             limit: int = 100) -> List[TransactionRecord]:
        """
        List transactions by address.
        
        Args:
            address: Blockchain address
            chain: Filter by chain (optional)
            limit: Maximum results
        
        Returns:
            List of TransactionRecords
        """
        return await asyncio.to_thread(
            self._query_by_address,
            address,
            chain,
            limit
        )
    
    async def list_recent(self, chain: str = None, hours: int = 24,
                         limit: int = 100) -> List[TransactionRecord]:
        """
        List recent transactions.
        
        Args:
            chain: Filter by chain (optional)
            hours: Hours to look back
            limit: Maximum results
        
        Returns:
            List of recent TransactionRecords
        """
        return await asyncio.to_thread(
            self._query_recent,
            chain,
            hours,
            limit
        )
    
    def _save_to_database(self, record: TransactionRecord):
        """Save transaction record to database."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        now = datetime.utcnow().isoformat()
        metadata_json = json.dumps(record.metadata)
        
        cursor.execute("""
            INSERT OR REPLACE INTO transactions 
            (tx_id, chain, asset, from_address, to_address, amount, status, signature,
             broadcast_hash, created_at, submitted_at, confirmed_at, finalized_at,
             confirmations, block_height, gas_used, fee, error, metadata, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.tx_id,
            record.chain,
            record.asset,
            record.from_address,
            record.to_address,
            record.amount,
            record.status.value,
            record.signature,
            record.broadcast_hash,
            record.created_at,
            record.submitted_at,
            record.confirmed_at,
            record.finalized_at,
            record.confirmations,
            record.block_height,
            record.gas_used,
            record.fee,
            record.error,
            metadata_json,
            now,
        ))
        
        conn.commit()
        conn.close()
    
    def _load_from_database(self, tx_id: str) -> Optional[TransactionRecord]:
        """Load transaction record from database."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM transactions WHERE tx_id = ?
        """, (tx_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        data = dict(row)
        data['metadata'] = json.loads(data['metadata'] or '{}')
        
        return TransactionRecord.from_dict(data)
    
    def _list_by_status(self, statuses: List[TransactionStatus],
                       chain: str = None, limit: int = 100) -> List[TransactionRecord]:
        """Query transactions by status."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        status_values = [s.value for s in statuses]
        placeholders = ','.join('?' * len(status_values))
        
        if chain:
            query = f"""
                SELECT * FROM transactions 
                WHERE status IN ({placeholders}) AND chain = ?
                ORDER BY created_at DESC LIMIT ?
            """
            cursor.execute(query, status_values + [chain, limit])
        else:
            query = f"""
                SELECT * FROM transactions 
                WHERE status IN ({placeholders})
                ORDER BY created_at DESC LIMIT ?
            """
            cursor.execute(query, status_values + [limit])
        
        rows = cursor.fetchall()
        conn.close()
        
        records = []
        for row in rows:
            data = dict(row)
            data['metadata'] = json.loads(data['metadata'] or '{}')
            records.append(TransactionRecord.from_dict(data))
        
        return records
    
    def _query_by_address(self, address: str, chain: str = None,
                         limit: int = 100) -> List[TransactionRecord]:
        """Query transactions by address."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if chain:
            query = """
                SELECT * FROM transactions 
                WHERE (from_address = ? OR to_address = ?) AND chain = ?
                ORDER BY created_at DESC LIMIT ?
            """
            cursor.execute(query, (address, address, chain, limit))
        else:
            query = """
                SELECT * FROM transactions 
                WHERE from_address = ? OR to_address = ?
                ORDER BY created_at DESC LIMIT ?
            """
            cursor.execute(query, (address, address, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        records = []
        for row in rows:
            data = dict(row)
            data['metadata'] = json.loads(data['metadata'] or '{}')
            records.append(TransactionRecord.from_dict(data))
        
        return records
    
    def _query_recent(self, chain: str = None, hours: int = 24,
                     limit: int = 100) -> List[TransactionRecord]:
        """Query recent transactions."""
        from datetime import timedelta
        
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if chain:
            query = """
                SELECT * FROM transactions 
                WHERE created_at > ? AND chain = ?
                ORDER BY created_at DESC LIMIT ?
            """
            cursor.execute(query, (cutoff, chain, limit))
        else:
            query = """
                SELECT * FROM transactions 
                WHERE created_at > ?
                ORDER BY created_at DESC LIMIT ?
            """
            cursor.execute(query, (cutoff, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        records = []
        for row in rows:
            data = dict(row)
            data['metadata'] = json.loads(data['metadata'] or '{}')
            records.append(TransactionRecord.from_dict(data))
        
        return records
    
    async def get_statistics(self, chain: str = None) -> Dict[str, Any]:
        """
        Get transaction statistics.
        
        Args:
            chain: Filter by chain (optional)
        
        Returns:
            Dictionary with statistics
        """
        return await asyncio.to_thread(self._calculate_statistics, chain)
    
    def _calculate_statistics(self, chain: str = None) -> Dict[str, Any]:
        """Calculate transaction statistics."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        base_query = "SELECT status, COUNT(*) as count FROM transactions"
        count_query = "SELECT COUNT(*) FROM transactions"
        sum_query = "SELECT SUM(amount) FROM transactions WHERE status = ?"
        
        where_clause = " WHERE chain = ?" if chain else ""
        
        cursor.execute(base_query + where_clause + " GROUP BY status", 
                      (chain,) if chain else ())
        status_counts = {row[0]: row[1] for row in cursor.fetchall()}
        
        cursor.execute(count_query + where_clause, (chain,) if chain else ())
        total = cursor.fetchone()[0]
        
        cursor.execute(sum_query + where_clause, 
                      ("confirmed",) + ((chain,) if chain else ()))
        confirmed_amount = cursor.fetchone()[0] or 0.0
        
        conn.close()
        
        return {
            "total_transactions": total,
            "status_counts": status_counts,
            "confirmed_amount": confirmed_amount,
            "chain": chain or "all",
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    async def export_json(self, output_path: str = None) -> Optional[str]:
        """
        Export transaction history to JSON.
        
        Args:
            output_path: Output file path (optional)
        
        Returns:
            JSON string or path if output_path provided
        """
        return await asyncio.to_thread(self._export_json_sync, output_path)
    
    def _export_json_sync(self, output_path: str = None) -> Optional[str]:
        """Synchronous JSON export."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM transactions ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        
        records = []
        for row in rows:
            data = dict(row)
            data['metadata'] = json.loads(data['metadata'] or '{}')
            record = TransactionRecord.from_dict(data)
            records.append(record.to_dict())
        
        export_data = {
            "export_date": datetime.utcnow().isoformat(),
            "total_records": len(records),
            "transactions": records,
        }
        
        json_str = json.dumps(export_data, indent=2)
        
        if output_path:
            Path(output_path).write_text(json_str, encoding='utf-8')
            return output_path
        
        return json_str
