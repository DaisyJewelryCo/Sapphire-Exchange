# Transaction Tracking System

## Overview

The transaction tracking system monitors all user transactions across supported blockchains (USDC on Solana, Arweave, Nano, and Dogecoin). It provides:

- **Pending transaction monitoring** with automatic confirmation tracking
- **Transaction history** with persistent storage
- **Incoming transaction alerts** for USDC deposits
- **Multi-blockchain support** with currency-specific confirmation logic
- **Retry management** for failed transactions
- **Real-time UI updates** showing transaction status and confirmations

## Architecture

```
┌────────────────────────────────────────┐
│  SendTransactionDialog / UI            │
├────────────────────────────────────────┤
│ • Sends transaction                    │
│ • Calls wallet_service.track_*()       │
└────────────────┬──────────────────────┘
                 │
┌────────────────▼──────────────────────┐
│  WalletService                         │
├────────────────────────────────────────┤
│ • track_outgoing_transaction()         │
│ • track_incoming_transaction()         │
│ • get_pending_transactions_async()     │
│ • get_transaction_history()            │
└────────────────┬──────────────────────┘
                 │
┌────────────────▼──────────────────────┐
│  TransactionTracker                    │
├────────────────────────────────────────┤
│ • create_transaction()                 │
│ • track_pending_transaction()          │
│ • _poll_confirmations()                │
│ • get_pending_transactions()           │
│ • get_transaction_history()            │
│ • retry_transaction()                  │
│ • mark_failed()                        │
└────────────────┬──────────────────────┘
                 │
      ┌──────────┴──────────────────┐
      │                             │
   Blockchain RPC APIs       data/transactions.json
   (Solana, Arweave,        (Persistent Storage)
    Nano, Dogecoin)
```

## Core Components

### 1. TransactionTracker Service

**Location**: `services/transaction_tracker.py`

**Key Features**:

#### Create and Track Transactions
```python
from services.transaction_tracker import transaction_tracker

tx = tracker.create_transaction(
    user_id=user.id,
    currency="USDC",
    tx_type="send",
    amount="50.00",
    from_address=user.usdc_address,
    to_address="recipient_address",
    tx_hash="transaction_hash_from_blockchain",
    metadata={'note': 'Payment for items'}
)

await tracker.track_pending_transaction(tx)
```

#### Confirmation Targets by Currency
- **USDC (Solana)**: 6 confirmations (slots)
- **Arweave**: 10 confirmations
- **Dogecoin**: 6 confirmations
- **Nano**: 1 confirmation (instant finality)

#### Polling Intervals
- **USDC**: Check every 2 seconds
- **Arweave**: Check every 5 seconds
- **Dogecoin**: Check every 3 seconds
- **Nano**: Check every 1 second

#### Transaction Status States
- **pending**: Waiting for confirmations
- **confirmed**: Has reached target confirmations
- **failed**: Error occurred or max retries exceeded

### 2. WalletService Integration

**Location**: `services/wallet_service.py`

**New Methods**:

```python
# Track outgoing transaction (when user sends)
await wallet_service.track_outgoing_transaction(
    user=user,
    currency="USDC",
    amount="100.00",
    to_address="recipient",
    tx_hash="tx_hash",
    metadata={'note': 'Optional note'}
)

# Track incoming transaction (USDC deposit)
await wallet_service.track_incoming_transaction(
    user=user,
    currency="USDC",
    amount="50.00",
    from_address="sender",
    tx_hash="tx_hash",
    metadata={'source': 'CEX'}
)

# Get pending transactions
pending = await wallet_service.get_pending_transactions_async(
    user=user,
    currency="USDC"  # Optional filter
)

# Get transaction history
history = await wallet_service.get_transaction_history(
    user=user,
    currency="USDC",
    limit=50,
    days=30
)
```

### 3. UI Components

#### PendingTransactionsWidget

**Location**: `ui/pending_transactions_widget.py`

**Features**:
- Displays pending transactions in a table
- Shows confirmations progress
- One-click blockchain explorer links
- Retry button for failed transactions
- Auto-refresh every 5 seconds

**Usage**:
```python
from ui.pending_transactions_widget import PendingTransactionsWidget

widget = PendingTransactionsWidget()
widget.initialize()
layout.addWidget(widget)
```

#### TransactionMonitorWidget

**Location**: `ui/pending_transactions_widget.py`

**Features**:
- Combined view of pending + recent transactions
- Grouped transaction display
- History table with 30-day lookback
- Full transaction details

**Usage**:
```python
from ui.pending_transactions_widget import TransactionMonitorWidget

monitor = TransactionMonitorWidget()
monitor.initialize()
layout.addWidget(monitor)
```

## Integration with SendTransactionDialog

When a transaction is sent, it's automatically tracked:

```python
# In SendTransactionDialog._on_transaction_complete():

# 1. Transaction is sent and gets tx_id/hash
tx_id = send_result['tx_hash']

# 2. Transaction is tracked
await wallet_service.track_outgoing_transaction(
    user=user,
    currency=self.currency,
    amount=str(amount),
    to_address=recipient,
    tx_hash=tx_id,
    metadata={...}
)

# 3. UI shows confirmation
QMessageBox.information(
    self, 
    "Transaction Sent",
    f"...being monitored for confirmations."
)
```

## USDC Incoming Transaction Handling

### Manual Tracking (Recommended)

When user deposits USDC to their address:

```python
# In funding_manager_widget or similar
from services.wallet_service import wallet_service

# Track the incoming USDC
await wallet_service.track_incoming_transaction(
    user=current_user,
    currency="USDC",
    amount="100.00",
    from_address="sender_solana_address",
    tx_hash="solana_tx_signature",
    metadata={
        'source': 'CEX',
        'exchange': 'Coinbase'
    }
)
```

### Automatic Balance Monitoring

The pending transaction widget automatically:
1. Monitors all pending USDC deposits
2. Checks confirmation status every 2 seconds
3. Updates UI in real-time
4. Marks as confirmed when threshold reached

### Notification Flow

```
User deposits USDC → Track incoming transaction
                  ↓
              Status: pending
                  ↓
         Check confirmations every 2s
                  ↓
         6 confirmations reached?
                  ↓
              Status: confirmed
                  ↓
         UI updates, user notified
```

## Persistent Storage

Transactions are saved to `data/transactions.json`:

```json
{
  "pending": [
    {
      "id": "uuid-1234",
      "user_id": "user-uuid",
      "currency": "USDC",
      "type": "receive",
      "amount": "100.00",
      "from_address": "...",
      "to_address": "...",
      "status": "pending",
      "tx_hash": "...",
      "created_at": "2025-02-11T...",
      "confirmations": 3,
      "retry_count": 0,
      "metadata": {...}
    }
  ],
  "completed": [...]
}
```

**Automatic Save**: Transactions are saved after each state change
**Automatic Load**: Transactions loaded on service startup
**Persistence**: Survives application restarts

## Retry Logic

### Configuration
- **USDC**: 5 max retries
- **Arweave**: 3 max retries
- **Dogecoin**: 4 max retries
- **Nano**: 3 max retries

### Retry Flow

```python
# Manual retry via UI
widget.retry_transaction(tx_id)

# Or programmatically
tracker = await get_transaction_tracker()
success = await tracker.retry_transaction(tx_id)

# Retry converts:
# status: "failed" → status: "pending"
# retry_count: 1 → retry_count: 2
# Resumes confirmation checking
```

## Confirmation Checking

### Solana/USDC
- Uses Solana RPC `getTransaction()` 
- Checks transaction status and error field
- Returns 6 if confirmed, 0 if pending

### Arweave
- Queries multiple nodes (arweave.net, g8way.arweave.net)
- Fetches `/tx/{hash}/status` endpoint
- Returns `number_of_confirmations`

### Nano
- Uses Nano RPC `block_info` 
- Instant finality after 1 confirmation
- Returns 1 if found (confirmed)

### Dogecoin
- Placeholder for blockchain integration
- Needs Dogecoin RPC node connection

## Error Handling

### Transaction Errors
1. **Validation errors**: Caught before creation
2. **Network errors**: Auto-retry with backoff
3. **Max retries exceeded**: Mark as failed
4. **Confirmation failures**: Manual retry via UI

### Example Error Handling

```python
try:
    await wallet_service.track_outgoing_transaction(...)
except Exception as e:
    # Mark as failed
    await tracker.mark_failed(tx_id, str(e))
    
    # Show to user
    QMessageBox.warning(self, "Error", f"Failed to track: {e}")
```

## Best Practices

### 1. Always Track Transactions
```python
# ✓ Do this
await wallet_service.track_outgoing_transaction(...)

# ✗ Don't forget tracking
# Just send without tracking
```

### 2. Use Async Methods
```python
# ✓ Use async
pending = await wallet_service.get_pending_transactions_async(user)

# ✗ Avoid blocking
pending = wallet_service.get_pending_transactions(user)  # Returns []
```

### 3. Include Metadata
```python
# ✓ Add context
await wallet_service.track_outgoing_transaction(
    ...,
    metadata={
        'note': 'Payment for auction items',
        'related_auction_id': 'auction-123'
    }
)
```

### 4. Monitor in UI
```python
# ✓ Always show status
widget = PendingTransactionsWidget()
widget.initialize()
layout.addWidget(widget)

# ✗ Don't hide transactions
# Just tell user "done" without monitoring
```

## Testing

### Manual Testing

```python
from services.transaction_tracker import TransactionTracker
import asyncio

async def test_tracker():
    tracker = TransactionTracker()
    await tracker.initialize()
    
    # Create test transaction
    tx = tracker.create_transaction(
        user_id="test-user",
        currency="USDC",
        tx_type="send",
        amount="10.00",
        from_address="Address1",
        to_address="Address2",
        tx_hash="test_hash_123"
    )
    
    # Track it
    await tracker.track_pending_transaction(tx)
    
    # Check status
    pending = tracker.get_pending_transactions(user_id="test-user")
    print(f"Pending: {len(pending)}")

asyncio.run(test_tracker())
```

### Unit Tests

Tests should verify:
- Transaction creation
- Confirmation tracking
- State transitions
- Persistence (load/save)
- Retry logic
- Multiple currencies

## Performance Considerations

### Polling Load
- 4 concurrent polling tasks (one per currency)
- Each polls at configured intervals
- Total network calls: ~30 RPC calls/minute

### Memory Usage
- In-memory caches: ~1KB per transaction
- Storage: ~100 pending + ~1000 completed
- Total: ~200KB-500KB typical

### Optimization Tips
1. Archive old transactions monthly
2. Limit confirmation check depth
3. Batch RPC queries when possible
4. Use connection pooling for HTTP

## Troubleshooting

### Transactions Not Appearing
1. Check `data/transactions.json` exists
2. Verify user_id matches in service
3. Check logs for errors

### Confirmations Not Updating
1. Verify RPC node is accessible
2. Check network connectivity
3. Verify tx_hash format
4. Try manual refresh

### Memory Issues
1. Clear completed transactions
2. Reduce polling interval
3. Archive old transactions
4. Restart service

## Future Enhancements

1. **WebSocket Support**: Real-time updates vs polling
2. **Transaction Webhooks**: External notifications
3. **Advanced Filtering**: Tag-based queries
4. **Analytics**: Transaction statistics dashboard
5. **Multi-sig Support**: Grouped transaction tracking
6. **Failed Transaction Recovery**: Auto-recovery flows
