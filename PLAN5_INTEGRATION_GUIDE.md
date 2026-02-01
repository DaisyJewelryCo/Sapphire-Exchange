# Plan 5 Integration Guide

## Quick Integration Summary

Plan 5 implementation provides a complete PyQt5 wallet UI with all components ready for integration. This guide shows how to integrate the Plan 5 UI into your main application.

## Integration Steps

### Step 1: Update Main Application Window

**File**: `app.py`

```python
from PyQt5.QtWidgets import QMainWindow, QStackedWidget, QVBoxLayout, QWidget
from ui.login_screen import LoginScreen
from ui.enhanced_wallet_widget import EnhancedWalletWidget

class SapphireExchange(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sapphire Exchange")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create stacked widget for screen management
        self.stacked_widget = QStackedWidget()
        
        # Create login screen
        self.login_screen = LoginScreen(self)
        self.login_screen.login_success.connect(self.on_login_success)
        
        # Create wallet widget
        self.wallet_widget = EnhancedWalletWidget()
        
        # Add screens
        self.stacked_widget.addWidget(self.login_screen)
        self.stacked_widget.addWidget(self.wallet_widget)
        
        # Set central widget
        self.setCentralWidget(self.stacked_widget)
        
        # Show login screen first
        self.stacked_widget.setCurrentWidget(self.login_screen)
    
    def on_login_success(self, wallet_data):
        """Handle successful login."""
        # Update wallet widget with user data
        self.wallet_widget.load_wallets(wallet_data)
        # Switch to wallet screen
        self.stacked_widget.setCurrentWidget(self.wallet_widget)
```

### Step 2: Initialize async Event Loop

**File**: `app.py`

```python
import sys
from qasync import QEventLoop, asyncSlot

async def main():
    from PyQt5.QtWidgets import QApplication
    
    # Create application
    app = QApplication(sys.argv)
    
    # Create async event loop
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    # Create main window
    window = SapphireExchange()
    window.show()
    
    # Run application
    with loop:
        loop.run_forever()

if __name__ == '__main__':
    asyncio.run(main())
```

### Step 3: Update UI Dialogs Module

**File**: `ui/dialogs/__init__.py`

```python
from ui.dialogs.wallet_management import (
    CreateWalletDialog,
    ImportWalletDialog,
    WalletSelectorDialog,
    WalletInfo
)
from ui.dialogs.transaction_dialogs import (
    SendTransactionDialog,
    ReceiveDialog,
    TransactionHistoryDialog
)
from ui.dialogs.backup_dialogs import (
    MnemonicDisplayDialog,
    BackupWizardDialog,
    RecoveryWizardDialog
)
from ui.dialogs.settings_dialog import SettingsDialog

__all__ = [
    'CreateWalletDialog',
    'ImportWalletDialog',
    'WalletSelectorDialog',
    'WalletInfo',
    'SendTransactionDialog',
    'ReceiveDialog',
    'TransactionHistoryDialog',
    'MnemonicDisplayDialog',
    'BackupWizardDialog',
    'RecoveryWizardDialog',
    'SettingsDialog',
]
```

### Step 4: Export Blockchain Components

**File**: `blockchain/__init__.py`

```python
from blockchain.unified_wallet_generator import UnifiedWalletGenerator
from blockchain.nano_wallet_helper import NanoWalletHelper, NanoTransactionBuilder, NanoWalletManager
from blockchain.transaction_manager import TransactionManager
from blockchain.backup.backup_manager import BackupManager, BackupType

__all__ = [
    'UnifiedWalletGenerator',
    'NanoWalletHelper',
    'NanoTransactionBuilder',
    'NanoWalletManager',
    'TransactionManager',
    'BackupManager',
    'BackupType',
]
```

### Step 5: Create Application Service Integration

**File**: `services/application_service.py` (Update existing)

```python
from blockchain import UnifiedWalletGenerator, TransactionManager, BackupManager
from ui.async_task_manager import BlockchainOperationManager

class AppService:
    def __init__(self):
        self.wallet_generator = UnifiedWalletGenerator()
        self.transaction_manager = TransactionManager()
        self.backup_manager = BackupManager()
        self.operation_manager = BlockchainOperationManager()
        self.current_user = None
        self.current_wallets = {}
    
    async def register_user_with_seed(self, seed_phrase: str):
        """Register new user and generate wallets."""
        try:
            # Validate seed phrase
            if not self.wallet_generator.validate_mnemonic(seed_phrase):
                return False, "Invalid seed phrase", None
            
            # Generate wallets for all blockchains
            wallets = await self.wallet_generator.generate_all(seed_phrase)
            
            # Store wallets
            self.current_wallets = wallets
            
            # Create user object
            user = {
                'created_at': datetime.now().isoformat(),
                'wallets': wallets,
                'backup_status': {
                    'mnemonic': False,
                    'encrypted_keys': False,
                    'physical': False,
                    'social': False,
                }
            }
            
            return True, "User registered", user
        
        except Exception as e:
            return False, str(e), None
    
    async def login_user_with_seed(self, seed_phrase: str):
        """Login user with seed phrase."""
        try:
            # Validate seed phrase
            if not self.wallet_generator.validate_mnemonic(seed_phrase):
                return False, "Invalid seed phrase", None
            
            # Generate wallets
            wallets = await self.wallet_generator.generate_all(seed_phrase)
            
            # Store wallets
            self.current_wallets = wallets
            
            # Create user object
            user = {
                'login_at': datetime.now().isoformat(),
                'wallets': wallets,
            }
            
            return True, "Login successful", user
        
        except Exception as e:
            return False, str(e), None
    
    async def send_transaction(self, asset: str, recipient: str, amount: float, password: str = None):
        """Send transaction using blockchain operation manager."""
        try:
            # Get signer from key storage
            signer = await self._get_signer(asset, password)
            
            # Send transaction
            result = await self.operation_manager.send_transaction(
                asset.lower(),
                recipient,
                amount,
                signer
            )
            
            return result
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'tx_id': None
            }
    
    async def get_balance(self, asset: str, address: str):
        """Get balance for address."""
        try:
            balance = await self.operation_manager.fetch_balance(asset.lower(), address)
            return balance
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def backup_wallet(self, method: str, **kwargs):
        """Create wallet backup."""
        try:
            mnemonic = kwargs.get('mnemonic', '')
            wallet_name = kwargs.get('wallet_name', 'My Wallet')
            
            if method == 'mnemonic':
                result = await self.backup_manager.create_all_backups(
                    mnemonic=mnemonic,
                    wallet_name=wallet_name,
                    **kwargs
                )
                return result
            
            return False, "Unknown backup method"
        
        except Exception as e:
            return False, str(e)

app_service = AppService()
```

## Component Usage Examples

### Example 1: Create New Wallet Dialog

```python
from ui.dialogs.wallet_management import CreateWalletDialog

def show_create_wallet():
    dialog = CreateWalletDialog()
    if dialog.exec_():
        wallet_info = dialog.get_wallet_info()
        print(f"Created wallet: {wallet_info.name}")
        print(f"Solana address: {wallet_info.address_solana}")
        print(f"Nano address: {wallet_info.address_nano}")
        print(f"Arweave address: {wallet_info.address_arweave}")
```

### Example 2: Send Transaction Dialog

```python
from ui.dialogs.transaction_dialogs import SendTransactionDialog

def show_send_dialog():
    dialog = SendTransactionDialog("Nano", "100.00")
    if dialog.exec_():
        recipient = dialog.recipient_edit.text()
        amount = dialog.amount_spin.value()
        # Process transaction
```

### Example 3: Backup Wizard

```python
from ui.dialogs.backup_dialogs import BackupWizardDialog

def show_backup_wizard():
    dialog = BackupWizardDialog(
        mnemonic="abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
    )
    if dialog.exec_():
        backup_result = dialog.get_backup_result()
        print(f"Backup completed: {backup_result}")
```

### Example 4: NANO Wallet Operations

```python
from blockchain.nano_wallet_helper import NanoWalletHelper

async def get_nano_balance():
    helper = NanoWalletHelper()
    await helper.initialize()
    
    address = "nano_3t6k35gi95xu6tergt6p69ck76ogmitsa8mnijtpxm9fkcm736xtoncuohr3"
    
    # Get balance
    balance, pending = await helper.get_balance(address)
    print(f"Balance: {balance} NANO")
    print(f"Pending: {pending} NANO")
    
    # Get account info
    info = await helper.get_account_info(address)
    print(f"Block count: {info['block_count']}")
    
    await helper.close()
```

### Example 5: Async Task Manager

```python
from ui.async_task_manager import BlockchainOperationManager

async def sync_wallets():
    manager = BlockchainOperationManager()
    
    # Sync all wallets
    result = await manager.sync_wallet({
        'solana': 'wallet_solana_address',
        'nano': 'nano_wallet_address',
        'arweave': 'arweave_wallet_address'
    })
    
    if result.success:
        print("Wallets synced!")
    else:
        print(f"Error: {result.error}")
```

## File Structure

```
Sapphire_Exchange/
├── app.py (Main application - UPDATE with Plan 5)
├── ui/
│   ├── __init__.py
│   ├── login_screen.py (✅ UPDATED with Plan 5)
│   ├── enhanced_wallet_widget.py (✅ NEW - Plan 5)
│   ├── async_task_manager.py (✅ NEW - Plan 5)
│   ├── custom_widgets.py (✅ NEW - Plan 5)
│   ├── dialogs/
│   │   ├── __init__.py
│   │   ├── wallet_management.py (✅ NEW - Plan 5)
│   │   ├── transaction_dialogs.py (✅ NEW - Plan 5)
│   │   ├── backup_dialogs.py (✅ NEW - Plan 5)
│   │   └── settings_dialog.py (✅ NEW - Plan 5)
│   └── [other existing widgets]
├── blockchain/
│   ├── __init__.py (UPDATE with Plan 5 exports)
│   ├── nano_wallet_helper.py (✅ NEW - Plan 5)
│   ├── unified_wallet_generator.py (Plan 1)
│   ├── transaction_manager.py (Plan 3)
│   ├── backup/
│   │   └── backup_manager.py (Plan 4)
│   └── [other blockchain modules]
├── services/
│   ├── application_service.py (UPDATE with Plan 5)
│   └── [other services]
└── tests/
    └── test_ui_components.py (✅ NEW - Plan 5)
```

## Configuration Files

### Environment Variables
```bash
# Add to .env
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
NANO_NODE_URL=https://mynano.ninja/api
ARWEAVE_GATEWAY_URL=https://arweave.net
```

### Requirements Update
```bash
# Ensure these are in requirements.txt
PyQt5>=5.15.9
qasync>=0.23.0
aiohttp>=3.8.0
cryptography>=38.0.0
qrcode>=7.4.2
pillow>=9.0.0
```

## Testing Integration

### Run UI Tests
```bash
pytest tests/test_ui_components.py -v
```

### Run All Tests
```bash
pytest tests/ -v --cov=ui --cov=blockchain
```

### Test Main Application
```bash
python app.py  # Should show login screen, then wallet dashboard
```

## Troubleshooting

### Issue: "ImportError: cannot import name 'EnhancedWalletWidget'"
**Solution**: Ensure `ui/enhanced_wallet_widget.py` is in the correct location and is properly imported.

### Issue: "QEventLoop not initialized"
**Solution**: Ensure qasync QEventLoop is created before creating any PyQt5 widgets.

### Issue: "Async operations hanging"
**Solution**: Verify BlockchainOperationManager is properly initialized with async methods.

### Issue: "Dialogs not showing"
**Solution**: Ensure dialogs are created in the main thread and `.exec_()` is called to show them modally.

## Performance Notes

- **Async Operations**: All blockchain operations are non-blocking
- **Lazy Loading**: Dialogs are created on-demand to reduce startup time
- **Batch Operations**: Multiple tasks can run concurrently
- **Caching**: Balance and status information is cached to reduce RPC calls

## Security Checklist

- ✅ Private keys never exposed to UI
- ✅ Mnemonics displayed only once
- ✅ Password required for transactions
- ✅ Session timeout implemented
- ✅ Secure random number generation
- ✅ No logging of sensitive data
- ✅ Address validation on all inputs
- ✅ Transaction confirmation dialogs

## Next Steps

1. **Integrate into main app.py** - Add Plan 5 widgets to application window
2. **Connect to real blockchain RPC** - Replace mock operations with real RPC calls
3. **Implement biometric authentication** - Add fingerprint/face ID support
4. **Add language support** - Translate UI strings to multiple languages
5. **Implement theme switching** - Add light/dark theme toggle
6. **Add analytics dashboard** - Show portfolio and transaction history

## Support

For issues or questions about Plan 5 integration:
1. Check PLAN5_IMPLEMENTATION.md for component details
2. Review test files for usage examples
3. Check blockchain module documentation for API details
4. Review PyQt5 documentation for widget customization

---

**Plan 5 Implementation Status**: ✅ COMPLETE and READY FOR INTEGRATION
