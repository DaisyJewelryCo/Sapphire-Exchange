# Transaction Tracking Integration Guide

This guide shows practical examples of integrating transaction tracking into your application.

## Quick Start

### 1. Track Outgoing Transactions (User Sends Crypto)

**Location**: `ui/wallet_widget.py::SendTransactionDialog`

```python
async def _on_transaction_complete(self, dialog, tx_id, amount):
    """Handle successful transaction with tracking."""
    dialog.close()
    if tx_id:
        user = app_service.get_current_user()
        if user:
            # Track the transaction
            from services.wallet_service import wallet_service
            
            await wallet_service.track_outgoing_transaction(
                user=user,
                currency=self.currency,
                amount=str(amount),
                to_address=self.recipient_edit.text().strip(),
                tx_hash=tx_id,
                metadata={
                    'note': self.note_edit.text() if hasattr(self, 'note_edit') else '',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            )
        
        # Show success with confirmation monitoring
        QMessageBox.information(
            self, 
            "Transaction Sent", 
            f"Sent {amount} {self.currency}\n\n"
            f"TX: {tx_id}\n\n"
            "Monitoring for confirmations..."
        )
        self.accept()
```

### 2. Display Pending Transactions

**Location**: Dashboard or Wallet Widget

```python
from ui.pending_transactions_widget import PendingTransactionsWidget

# Create and add widget
pending_widget = PendingTransactionsWidget()
pending_widget.initialize()
layout.addWidget(pending_widget)

# Widget auto-refreshes every 5 seconds
# Shows:
# - Currency, Type, Amount
# - Status (pending/confirmed/failed)
# - Confirmations progress
# - View & Retry buttons
```

### 3. Track Incoming USDC

**Location**: `ui/funding_manager_widget.py` or separate deposit handler

```python
from services.wallet_service import wallet_service
from services.application_service import app_service

async def handle_usdc_deposit(tx_hash: str, amount: str, from_address: str):
    """Track incoming USDC deposit."""
    
    user = app_service.get_current_user()
    if not user:
        return
    
    # Track the incoming transaction
    await wallet_service.track_incoming_transaction(
        user=user,
        currency="USDC",
        amount=amount,
        from_address=from_address,
        tx_hash=tx_hash,
        metadata={
            'source': 'manual_deposit',
            'exchange': 'unknown',
            'deposit_time': datetime.now(timezone.utc).isoformat()
        }
    )
    
    # Notify user
    QMessageBox.information(
        None,
        "Deposit Received",
        f"USDC deposit of {amount} is being confirmed.\n"
        f"Check the Pending Transactions widget for status."
    )
```

### 4. Manual Deposit Entry (User Adds USDC)

**Location**: New dialog in funding manager

```python
class ManualUsdcDepositDialog(QDialog):
    """Dialog for entering manual USDC deposit."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Record USDC Deposit")
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Transaction hash input
        form = QFormLayout()
        
        self.tx_hash_edit = QLineEdit()
        self.tx_hash_edit.setPlaceholderText("Solana transaction signature")
        form.addRow("TX Hash:", self.tx_hash_edit)
        
        self.amount_edit = QLineEdit()
        self.amount_edit.setPlaceholderText("100.00")
        form.addRow("Amount (USDC):", self.amount_edit)
        
        self.from_edit = QLineEdit()
        self.from_edit.setPlaceholderText("Sender address")
        form.addRow("From Address:", self.from_edit)
        
        layout.addLayout(form)
        
        # Track button
        track_btn = QPushButton("Track Deposit")
        track_btn.clicked.connect(self.track_deposit)
        layout.addWidget(track_btn)
    
    def track_deposit(self):
        """Track the deposit."""
        try:
            tx_hash = self.tx_hash_edit.text().strip()
            amount = self.amount_edit.text().strip()
            from_address = self.from_edit.text().strip()
            
            if not tx_hash or not amount or not from_address:
                QMessageBox.warning(self, "Error", "Fill all fields")
                return
            
            user = app_service.get_current_user()
            if not user:
                return
            
            # Track it
            worker = AsyncWorker(
                wallet_service.track_incoming_transaction(
                    user=user,
                    currency="USDC",
                    amount=amount,
                    from_address=from_address,
                    tx_hash=tx_hash,
                    metadata={'source': 'manual_entry'}
                )
            )
            worker.finished.connect(
                lambda: QMessageBox.information(
                    self, 
                    "Success", 
                    "Deposit tracked. Check pending transactions."
                )
            )
            worker.start()
            
            self.accept()
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to track: {e}")
```

### 5. Get Transaction History

**Location**: Transaction history widget

```python
from services.wallet_service import wallet_service

class TransactionHistoryPanel(QWidget):
    """Display user transaction history."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_history()
    
    def load_history(self):
        """Load and display transaction history."""
        user = app_service.get_current_user()
        if not user:
            return
        
        worker = AsyncWorker(
            self._fetch_history(user)
        )
        worker.finished.connect(self._display_history)
        worker.start()
        self._history_worker = worker
    
    async def _fetch_history(self, user):
        """Fetch transaction history asynchronously."""
        # Get last 30 days of transactions
        history = await wallet_service.get_transaction_history(
            user=user,
            limit=100,
            days=30
        )
        return history
    
    def _display_history(self, history):
        """Display transaction history."""
        self.table.setRowCount(0)
        
        for tx_dict in history:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # Add cells: Date, Currency, Type, Amount, Status
            self.table.setItem(row, 0, QTableWidgetItem(tx_dict['created_at'][:10]))
            self.table.setItem(row, 1, QTableWidgetItem(tx_dict['currency']))
            self.table.setItem(row, 2, QTableWidgetItem(tx_dict['type']))
            self.table.setItem(row, 3, QTableWidgetItem(tx_dict['amount']))
            
            status = tx_dict['status']
            item = QTableWidgetItem(status.upper())
            if status == 'confirmed':
                item.setForeground(QColor('#4caf50'))
            elif status == 'pending':
                item.setForeground(QColor('#ff9800'))
            elif status == 'failed':
                item.setForeground(QColor('#f44336'))
            self.table.setItem(row, 4, item)
```

### 6. Retry Failed Transactions

**Location**: Pending transactions widget (built-in)

```python
async def retry_failed_transaction(tx_id: str):
    """Retry a failed transaction."""
    from services.transaction_tracker import get_transaction_tracker
    
    tracker = await get_transaction_tracker()
    success = await tracker.retry_transaction(tx_id)
    
    if success:
        QMessageBox.information(
            None,
            "Retry Scheduled",
            f"Transaction retry scheduled.\n"
            f"Status will update as confirmations arrive."
        )
    else:
        QMessageBox.warning(
            None,
            "Retry Failed",
            "Transaction exceeded max retry attempts."
        )
```

## Integration Points

### In FundingManagerWidget

```python
from ui.pending_transactions_widget import PendingTransactionsWidget

class FundingManagerWidget(QWidget):
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # ... existing funding wizard code ...
        
        # Add pending transactions section
        pending_label = QLabel("Pending Transactions")
        pending_label.setFont(QFont("Arial", 11, QFont.Bold))
        layout.addWidget(pending_label)
        
        self.pending_widget = PendingTransactionsWidget()
        layout.addWidget(self.pending_widget)
    
    def initialize(self):
        """Initialize after login."""
        self.pending_widget.initialize()
```

### In Dashboard

```python
from ui.pending_transactions_widget import TransactionMonitorWidget

class DashboardWidget(QWidget):
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Add transaction monitor
        monitor = TransactionMonitorWidget()
        monitor.initialize()
        layout.addWidget(monitor)
```

### In Login/Startup

```python
async def on_user_login(user):
    """Initialize tracking on login."""
    from services.transaction_tracker import get_transaction_tracker
    
    # Initialize tracker
    tracker = await get_transaction_tracker()
    
    # Load any pending transactions
    pending = tracker.get_pending_transactions(user_id=user.id)
    
    # Resume tracking for pending transactions
    for tx in pending:
        await tracker.track_pending_transaction(tx)
    
    print(f"Resumed tracking {len(pending)} pending transactions")
```

### In Logout/Shutdown

```python
async def on_user_logout():
    """Cleanup on logout."""
    from services.transaction_tracker import transaction_tracker
    
    # Cleanup resources
    await transaction_tracker.cleanup()
```

## Common Patterns

### Pattern 1: Send → Track → Monitor

```python
# 1. Send transaction
tx_id = blockchain.send_nano(from_addr, to_addr, amount)

# 2. Track immediately
await wallet_service.track_outgoing_transaction(
    user=user,
    currency="NANO",
    amount=amount,
    to_address=to_addr,
    tx_hash=tx_id
)

# 3. Show pending widget (auto-monitors)
pending_widget.refresh_transactions()
```

### Pattern 2: USDC Deposit → Track → Confirm

```python
# 1. User deposits USDC to their wallet
# (detected via explorer or user input)

# 2. Track the incoming transaction
await wallet_service.track_incoming_transaction(
    user=user,
    currency="USDC",
    amount="100.00",
    from_address="exchange_address",
    tx_hash="solana_tx_signature"
)

# 3. Monitor shows progress (pending → 1 → 2 → ... → confirmed)
# 4. User notified when confirmed
```

### Pattern 3: Batch Import History

```python
async def import_transaction_history(user, transactions):
    """Import existing transactions from blockchain."""
    
    for tx_data in transactions:
        await wallet_service.track_outgoing_transaction(
            user=user,
            currency=tx_data['currency'],
            amount=tx_data['amount'],
            to_address=tx_data['to'],
            tx_hash=tx_data['hash'],
            metadata={'imported': True, 'source': 'blockchain'}
        )
    
    QMessageBox.information(
        None,
        "Import Complete",
        f"Imported {len(transactions)} transactions"
    )
```

## Error Handling Examples

### Handle Network Errors

```python
async def send_with_error_handling(user, to_addr, amount):
    """Send with comprehensive error handling."""
    
    try:
        # Send
        tx_id = await blockchain.send_transaction(to_addr, amount)
        
        # Track
        await wallet_service.track_outgoing_transaction(
            user=user,
            currency="USDC",
            amount=str(amount),
            to_address=to_addr,
            tx_hash=tx_id
        )
        
        return True
    
    except NetworkError as e:
        QMessageBox.warning(
            None,
            "Network Error",
            f"Could not send: {e}\n"
            f"Please check your connection and try again."
        )
        return False
    
    except ValidationError as e:
        QMessageBox.warning(
            None,
            "Invalid Input",
            f"Address or amount invalid: {e}"
        )
        return False
```

### Handle Confirmation Timeouts

```python
# Long-running transaction monitoring
# TransactionTracker polls indefinitely until:
# 1. Confirmed (target confirmations reached)
# 2. Failed (explicit failure)
# 3. Max retries exceeded

# User can manually:
# - View on blockchain explorer
# - Retry failed transactions
# - Mark as failed if stuck
```

## Testing Integration

```python
async def test_transaction_flow():
    """Test complete transaction flow."""
    from models.models import User
    from services.wallet_service import wallet_service
    
    # Create test user
    user = User(
        username="test_user",
        password_hash="hash",
        nano_address="nano_test_address",
        arweave_address="arweave_test_address",
        usdc_address="solana_test_address"
    )
    
    # Send transaction
    await wallet_service.track_outgoing_transaction(
        user=user,
        currency="USDC",
        amount="10.00",
        to_address="recipient_address",
        tx_hash="test_tx_hash_123"
    )
    
    # Check pending
    pending = await wallet_service.get_pending_transactions_async(user)
    assert len(pending) == 1
    assert pending[0]['status'] == 'pending'
    
    # Get history
    history = await wallet_service.get_transaction_history(user)
    assert len(history) == 1
    
    print("✓ Transaction tracking works!")
```

## Debugging

### Enable Detailed Logging

```python
import logging

# Enable debug logging for transaction tracker
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('transaction_tracker')
logger.setLevel(logging.DEBUG)
```

### Check Storage

```python
# View saved transactions
import json
from pathlib import Path

with open('data/transactions.json', 'r') as f:
    data = json.load(f)
    print(f"Pending: {len(data['pending'])}")
    print(f"Completed: {len(data['completed'])}")
    
    for tx in data['pending']:
        print(f"  {tx['currency']}: {tx['status']} - {tx['id']}")
```

### Manual Confirmation Check

```python
async def check_confirmation_status(tx_hash: str, currency: str):
    """Manually check confirmation status."""
    from services.transaction_tracker import get_transaction_tracker
    
    tracker = await get_transaction_tracker()
    confirmations = await tracker._check_confirmations_sync(tx_hash, currency)
    print(f"Confirmations: {confirmations}")
```

## Production Checklist

- [ ] Storage path configured correctly
- [ ] Blockchain RPC nodes accessible
- [ ] Polling intervals appropriate for load
- [ ] Error handling tested
- [ ] UI widgets integrated
- [ ] Logging enabled
- [ ] Database migrations run
- [ ] Shutdown cleanup tested
- [ ] Memory limits monitored
- [ ] Network connectivity tested
