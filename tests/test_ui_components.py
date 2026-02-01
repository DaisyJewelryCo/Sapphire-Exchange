"""
Tests for UI components.
Tests dialogs, widgets, and async operations.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from PyQt5.QtWidgets import QApplication
from PyQt5.QtTest import QSignalSpy

from ui.dialogs.wallet_management import CreateWalletDialog, ImportWalletDialog, WalletInfo
from ui.dialogs.transaction_dialogs import SendTransactionDialog, ReceiveDialog
from ui.dialogs.backup_dialogs import MnemonicDisplayDialog, BackupWizardDialog, RecoveryWizardDialog
from ui.dialogs.settings_dialog import SettingsDialog
from ui.custom_widgets import (
    AddressDisplayWidget, BalanceWidget, QRCodeWidget,
    TransactionListWidget, WalletTileWidget, StatusIndicatorWidget
)
from ui.async_task_manager import AsyncTaskManager, TaskResult, TaskStatus


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    app.quit()


class TestCreateWalletDialog:
    """Test wallet creation dialog."""
    
    def test_dialog_initialization(self, qapp):
        """Test dialog initializes."""
        dialog = CreateWalletDialog()
        assert dialog.windowTitle() == "Create New Wallet"
        dialog.deleteLater()
    
    def test_word_count_spinner(self, qapp):
        """Test word count spinner."""
        dialog = CreateWalletDialog()
        assert dialog.word_count.value() in [12, 24]
        dialog.deleteLater()
    
    def test_wallet_name_input(self, qapp):
        """Test wallet name input."""
        dialog = CreateWalletDialog()
        dialog.name_edit.setText("Test Wallet")
        assert dialog.name_edit.text() == "Test Wallet"
        dialog.deleteLater()


class TestImportWalletDialog:
    """Test wallet import dialog."""
    
    def test_dialog_initialization(self, qapp):
        """Test dialog initializes."""
        dialog = ImportWalletDialog()
        assert dialog.windowTitle() == "Import Wallet"
        dialog.deleteLater()
    
    def test_mnemonic_input(self, qapp):
        """Test mnemonic input."""
        dialog = ImportWalletDialog()
        test_mnemonic = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
        dialog.mnemonic_edit.setPlainText(test_mnemonic)
        assert dialog.mnemonic_edit.toPlainText() == test_mnemonic
        dialog.deleteLater()


class TestSendTransactionDialog:
    """Test send transaction dialog."""
    
    def test_dialog_initialization(self, qapp):
        """Test dialog initializes."""
        dialog = SendTransactionDialog("Solana", "10.00")
        assert dialog.windowTitle() == "Send Solana"
        dialog.deleteLater()
    
    def test_recipient_input(self, qapp):
        """Test recipient input."""
        dialog = SendTransactionDialog()
        test_address = "So1dDKkGkDmWpA8gUqLa8e7i9xdA3b4c5e6f7g8h9i"
        dialog.recipient_edit.setText(test_address)
        assert dialog.recipient_edit.text() == test_address
        dialog.deleteLater()
    
    def test_amount_input(self, qapp):
        """Test amount input."""
        dialog = SendTransactionDialog()
        dialog.amount_spin.setValue(5.0)
        assert dialog.amount_spin.value() == 5.0
        dialog.deleteLater()


class TestReceiveDialog:
    """Test receive dialog."""
    
    def test_dialog_initialization(self, qapp):
        """Test dialog initializes."""
        address = "So1dDKkGkDmWpA8gUqLa8e7i9xdA3b4c5e6f7g8h9i"
        dialog = ReceiveDialog("Solana", address)
        assert dialog.windowTitle() == "Receive Solana"
        dialog.deleteLater()


class TestMnemonicDisplayDialog:
    """Test mnemonic display dialog."""
    
    def test_dialog_initialization(self, qapp):
        """Test dialog initializes."""
        mnemonic = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
        dialog = MnemonicDisplayDialog(mnemonic, "Test Wallet")
        assert dialog.windowTitle() == "Backup Your Mnemonic"
        dialog.deleteLater()
    
    def test_mnemonic_display_read_only(self, qapp):
        """Test mnemonic is read-only."""
        mnemonic = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
        dialog = MnemonicDisplayDialog(mnemonic)
        assert dialog.mnemonic_display.isReadOnly()
        dialog.deleteLater()
    
    def test_confirmation_checkboxes(self, qapp):
        """Test confirmation checkboxes."""
        mnemonic = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
        dialog = MnemonicDisplayDialog(mnemonic)
        
        assert not dialog.understood_check.isChecked()
        assert not dialog.safe_check.isChecked()
        assert not dialog.confirm_btn.isEnabled()
        
        dialog.understood_check.setChecked(True)
        dialog.safe_check.setChecked(True)
        assert dialog.confirm_btn.isEnabled()
        
        dialog.deleteLater()


class TestBackupWizardDialog:
    """Test backup wizard dialog."""
    
    def test_dialog_initialization(self, qapp):
        """Test dialog initializes."""
        dialog = BackupWizardDialog()
        assert dialog.windowTitle() == "Backup Wizard"
        dialog.deleteLater()
    
    def test_step_navigation(self, qapp):
        """Test step navigation."""
        dialog = BackupWizardDialog()
        assert dialog.current_step == 0
        
        dialog.next_step()
        assert dialog.current_step == 1
        
        dialog.previous_step()
        assert dialog.current_step == 0
        
        dialog.deleteLater()


class TestRecoveryWizardDialog:
    """Test recovery wizard dialog."""
    
    def test_dialog_initialization(self, qapp):
        """Test dialog initializes."""
        dialog = RecoveryWizardDialog()
        assert dialog.windowTitle() == "Wallet Recovery"
        dialog.deleteLater()


class TestSettingsDialog:
    """Test settings dialog."""
    
    def test_dialog_initialization(self, qapp):
        """Test dialog initializes."""
        dialog = SettingsDialog()
        assert dialog.windowTitle() == "Settings"
        dialog.deleteLater()
    
    def test_network_settings(self, qapp):
        """Test network settings."""
        dialog = SettingsDialog()
        test_rpc = "https://api.example.com"
        dialog.solana_rpc.setText(test_rpc)
        assert dialog.solana_rpc.text() == test_rpc
        dialog.deleteLater()


class TestAddressDisplayWidget:
    """Test address display widget."""
    
    def test_widget_initialization(self, qapp):
        """Test widget initializes."""
        address = "So1dDKkGkDmWpA8gUqLa8e7i9xdA3b4c5e6f7g8h9i"
        widget = AddressDisplayWidget(address)
        assert widget.address == address
        widget.deleteLater()
    
    def test_address_update(self, qapp):
        """Test address update."""
        widget = AddressDisplayWidget()
        new_address = "So1dDKkGkDmWpA8gUqLa8e7i9xdA3b4c5e6f7g8h9i"
        widget.set_address(new_address)
        assert widget.address == new_address
        widget.deleteLater()


class TestBalanceWidget:
    """Test balance widget."""
    
    def test_widget_initialization(self, qapp):
        """Test widget initializes."""
        widget = BalanceWidget("SOL", "10.5", "$250.00")
        assert widget.currency == "SOL"
        assert widget.balance == "10.5"
        widget.deleteLater()
    
    def test_balance_update(self, qapp):
        """Test balance update."""
        widget = BalanceWidget()
        widget.update_balance("20.0", "$500.00")
        assert widget.balance == "20.0"
        widget.deleteLater()


class TestQRCodeWidget:
    """Test QR code widget."""
    
    def test_widget_initialization(self, qapp):
        """Test widget initializes."""
        data = "So1dDKkGkDmWpA8gUqLa8e7i9xdA3b4c5e6f7g8h9i"
        widget = QRCodeWidget(data)
        assert widget.data == data
        widget.deleteLater()


class TestTransactionListWidget:
    """Test transaction list widget."""
    
    def test_widget_initialization(self, qapp):
        """Test widget initializes."""
        transactions = [
            {'date': '2024-01-01', 'type': 'send', 'amount': '1.0', 'address': 'addr1', 'status': 'confirmed'},
            {'date': '2024-01-02', 'type': 'receive', 'amount': '2.0', 'address': 'addr2', 'status': 'pending'},
        ]
        widget = TransactionListWidget(transactions)
        assert len(widget.transactions) == 2
        widget.deleteLater()


class TestWalletTileWidget:
    """Test wallet tile widget."""
    
    def test_widget_initialization(self, qapp):
        """Test widget initializes."""
        wallet_info = {
            'name': 'My Wallet',
            'balance': '$100.00',
            'status': 'Ready'
        }
        widget = WalletTileWidget(wallet_info)
        assert widget.wallet_info == wallet_info
        widget.deleteLater()


class TestStatusIndicatorWidget:
    """Test status indicator widget."""
    
    def test_widget_initialization(self, qapp):
        """Test widget initializes."""
        statuses = {
            'Solana': 'Connected',
            'Nano': 'Disconnected',
            'Arweave': 'Connected'
        }
        widget = StatusIndicatorWidget(statuses)
        assert widget.statuses == statuses
        widget.deleteLater()
    
    def test_status_update(self, qapp):
        """Test status update."""
        widget = StatusIndicatorWidget()
        widget.update_status("Solana", "Connected")
        assert widget.statuses["Solana"] == "Connected"
        widget.deleteLater()


class TestAsyncTaskManager:
    """Test async task manager."""
    
    def test_manager_initialization(self):
        """Test manager initializes."""
        manager = AsyncTaskManager()
        assert len(manager.tasks) == 0
    
    @pytest.mark.asyncio
    async def test_execute_simple_task(self):
        """Test executing simple async task."""
        manager = AsyncTaskManager()
        
        async def dummy_coro():
            return "result"
        
        result = await manager.execute("test_task", dummy_coro(), "Test Task")
        
        assert result.success
        assert result.data == "result"
        assert result.status == TaskStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_task_failure(self):
        """Test task failure handling."""
        manager = AsyncTaskManager()
        
        async def failing_coro():
            raise ValueError("Test error")
        
        result = await manager.execute("test_task", failing_coro(), "Test Task")
        
        assert not result.success
        assert "Test error" in result.error
        assert result.status == TaskStatus.FAILED
    
    @pytest.mark.asyncio
    async def test_execute_batch(self):
        """Test executing batch of tasks."""
        manager = AsyncTaskManager()
        
        async def coro1():
            return "result1"
        
        async def coro2():
            return "result2"
        
        tasks = [
            ("task1", coro1(), "Task 1"),
            ("task2", coro2(), "Task 2"),
        ]
        
        results = await manager.execute_batch(tasks)
        
        assert len(results) == 2
        assert results[0].success
        assert results[1].success


class TestWalletInfo:
    """Test WalletInfo dataclass."""
    
    def test_wallet_info_creation(self):
        """Test wallet info creation."""
        wallet = WalletInfo(
            name="Test Wallet",
            mnemonic="abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about",
            address_solana="So1dDKkGkDmWpA8gUqLa8e7i9xdA3b4c5e6f7g8h9i"
        )
        
        assert wallet.name == "Test Wallet"
        assert wallet.address_solana is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
