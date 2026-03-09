"""
Wallet details dialog showing wallet information and action buttons.
"""
import json
from typing import Optional
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit,
    QGroupBox, QMessageBox, QApplication, QScrollArea, QInputDialog, QLineEdit
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QClipboard
from ui.custom_widgets import AddressDisplayWidget, BalanceWidget
from utils.async_worker import AsyncWorker
from services.application_service import app_service
from security.account_backup_manager import account_backup_manager


class WalletDetailsDialog(QDialog):
    """Dialog displaying wallet details and actions."""
    
    send_clicked = pyqtSignal(str)
    receive_clicked = pyqtSignal(str)
    backup_clicked = pyqtSignal()
    recover_clicked = pyqtSignal()
    delete_clicked = pyqtSignal()
    
    def __init__(self, wallet_info, parent=None, currency=None):
        super().__init__(parent)
        self.wallet_info = wallet_info
        self.currency = currency
        self.setWindowTitle(f"Wallet Details - {wallet_info.name}")
        self.setModal(True)
        self.setMinimumWidth(700)
        self.setMinimumHeight(600)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        header_layout = QHBoxLayout()
        title = QLabel(self.wallet_info.name)
        title.setFont(QFont("Arial", 16, QFont.Bold))
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QVBoxLayout()
        scroll_container = type('ScrollContainer', (), {'setLayout': lambda self, l: None})()
        
        scroll_layout = QVBoxLayout()
        
        scroll_layout.addWidget(self._create_addresses_group())
        
        scroll_layout.addWidget(self._create_balances_group())
        
        scroll_layout.addWidget(self._create_actions_group())
        
        scroll_layout.addStretch()
        
        scroll_inner = type('obj', (object,), {'layout': scroll_layout})()
        container_widget = type('Container', (object,), {})()
        
        scroll_widget_actual = self._create_scroll_content(scroll_layout)
        scroll.setWidget(scroll_widget_actual)
        
        layout.addWidget(scroll)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def _create_scroll_content(self, inner_layout):
        """Create a widget container for scroll area."""
        from PyQt5.QtWidgets import QWidget
        widget = QWidget()
        widget.setLayout(inner_layout)
        return widget
    
    def _create_addresses_group(self) -> QGroupBox:
        """Create addresses group."""
        group = QGroupBox("Wallet Addresses")
        layout = QVBoxLayout(group)
        
        if self.wallet_info.address_solana:
            layout.addWidget(self._create_address_widget(
                "Solana",
                self.wallet_info.address_solana
            ))
        
        if self.wallet_info.address_nano:
            layout.addWidget(self._create_address_widget(
                "Nano",
                self.wallet_info.address_nano
            ))
        
        if self.wallet_info.address_arweave:
            layout.addWidget(self._create_address_widget(
                "Arweave",
                self.wallet_info.address_arweave
            ))
        
        return group
    
    def _create_address_widget(self, blockchain: str, address: str) -> type:
        """Create a single address display widget."""
        from PyQt5.QtWidgets import QWidget
        
        widget = QWidget()
        widget_layout = QHBoxLayout(widget)
        widget_layout.setContentsMargins(0, 5, 0, 5)
        
        label = QLabel(f"{blockchain}:")
        label.setFont(QFont("Arial", 10, QFont.Bold))
        label.setMinimumWidth(80)
        widget_layout.addWidget(label)
        
        address_text = QTextEdit()
        address_text.setPlainText(address)
        address_text.setReadOnly(True)
        address_text.setMaximumHeight(50)
        address_text.setFont(QFont("Courier", 9))
        widget_layout.addWidget(address_text)
        
        copy_btn = QPushButton("Copy")
        copy_btn.setMaximumWidth(60)
        copy_btn.clicked.connect(lambda: self._copy_address(address))
        widget_layout.addWidget(copy_btn)
        
        return widget
    
    def _copy_address(self, address: str):
        """Copy address to clipboard."""
        clipboard = QApplication.clipboard()
        clipboard.setText(address)
        QMessageBox.information(self, "Copied", f"Address copied to clipboard")
    
    def _create_balances_group(self) -> QGroupBox:
        """Create balances group."""
        group = QGroupBox("Balance")
        layout = QHBoxLayout(group)
        
        if self.currency == 'SOL':
            balance = BalanceWidget("SOL", "0.00", "$0.00")
            layout.addWidget(balance)
        elif self.currency == 'USDC':
            balance = BalanceWidget("USDC", "0.00", "$0.00")
            layout.addWidget(balance)
        elif self.currency == 'NANO':
            balance = BalanceWidget("NANO", "0.00", "$0.00")
            layout.addWidget(balance)
        elif self.currency == 'ARWEAVE':
            balance = BalanceWidget("AR", "0.00", "$0.00")
            layout.addWidget(balance)
        else:
            solana_balance = BalanceWidget("SOL", "0.00", "$0.00")
            nano_balance = BalanceWidget("NANO", "0.00", "$0.00")
            arweave_balance = BalanceWidget("AR", "0.00", "$0.00")
            
            layout.addWidget(solana_balance)
            layout.addWidget(nano_balance)
            layout.addWidget(arweave_balance)
        
        return group
    
    def _create_actions_group(self) -> QGroupBox:
        """Create actions group."""
        group = QGroupBox("Wallet Actions")
        layout = QVBoxLayout(group)
        
        buttons_layout = QHBoxLayout()
        
        send_btn = QPushButton("📤 Send")
        send_btn.setMinimumHeight(40)
        send_btn.clicked.connect(self._on_send_clicked)
        buttons_layout.addWidget(send_btn)
        
        receive_btn = QPushButton("📥 Receive")
        receive_btn.setMinimumHeight(40)
        receive_btn.clicked.connect(self._on_receive_clicked)
        buttons_layout.addWidget(receive_btn)
        
        backup_btn = QPushButton("💾 Backup")
        backup_btn.setMinimumHeight(40)
        backup_btn.clicked.connect(self._on_backup_clicked)
        buttons_layout.addWidget(backup_btn)
        
        recover_btn = QPushButton("🔄 Recover")
        recover_btn.setMinimumHeight(40)
        recover_btn.clicked.connect(self._on_recover_clicked)
        buttons_layout.addWidget(recover_btn)

        view_key_btn = QPushButton("🔑 View Private Key")
        view_key_btn.setMinimumHeight(40)
        view_key_btn.clicked.connect(self._on_view_private_key_clicked)
        buttons_layout.addWidget(view_key_btn)
        
        layout.addLayout(buttons_layout)
        
        delete_btn = QPushButton("🗑️ Remove Wallet")
        delete_btn.setStyleSheet("background-color: #C1121F; color: white;")
        delete_btn.setMinimumHeight(35)
        delete_btn.clicked.connect(self._on_delete_clicked)
        layout.addWidget(delete_btn)
        
        return group
    
    def _on_send_clicked(self):
        """Handle send button click."""
        self.send_clicked.emit(self.wallet_info.name)
        self.close()
    
    def _on_receive_clicked(self):
        """Handle receive button click."""
        self.receive_clicked.emit(self.wallet_info.name)
        self.close()
    
    def _on_backup_clicked(self):
        """Handle backup button click."""
        self.backup_clicked.emit()
        self.close()
    
    def _on_recover_clicked(self):
        """Handle recover button click."""
        self.recover_clicked.emit()
        self.close()

    def _on_view_private_key_clicked(self):
        user = app_service.get_current_user()
        if not user:
            QMessageBox.warning(self, "Not Logged In", "Please log in to view private keys.")
            return

        nano_address = getattr(user, 'nano_address', None)
        if not nano_address:
            QMessageBox.warning(self, "Unavailable", "Nano address is required to locate your backup.")
            return

        mnemonic, ok = QInputDialog.getText(
            self,
            "Enter Mnemonic",
            "Enter your mnemonic phrase to decrypt your account backup:",
            QLineEdit.Normal
        )
        mnemonic = (mnemonic or "").strip()
        if not ok or not mnemonic:
            return

        currency = (self.currency or '').upper()
        worker = AsyncWorker(self._load_private_key_from_backup(currency, nano_address, mnemonic))
        worker.finished.connect(lambda result: self._on_private_key_loaded(currency, result))
        worker.error.connect(lambda error: QMessageBox.critical(self, "Backup Error", str(error)))
        worker.start()
        self.private_key_worker = worker

    async def _load_private_key_from_backup(self, currency: str, nano_address: str, mnemonic: str):
        success, account_data = await account_backup_manager.restore_account_from_backup(nano_address, mnemonic)
        if not success or not isinstance(account_data, dict):
            return {'success': False, 'error': 'Failed to decrypt backup. Verify your mnemonic and try again.'}

        private_keys = account_data.get('private_keys', {})
        wallets = account_data.get('wallets', {})
        currency_upper = currency or ''

        if currency_upper in ('SOL', 'USDC'):
            key_value = private_keys.get('solana') or private_keys.get('solana_private_key')
            if not key_value and isinstance(wallets.get('solana'), dict):
                key_value = wallets.get('solana', {}).get('private_key')
        elif currency_upper == 'NANO':
            key_value = private_keys.get('nano') or private_keys.get('nano_private_key')
            if not key_value and isinstance(wallets.get('nano'), dict):
                key_value = wallets.get('nano', {}).get('private_key')
        elif currency_upper == 'ARWEAVE':
            key_value = private_keys.get('arweave_jwk') or private_keys.get('arweave')
            if not key_value and isinstance(wallets.get('arweave'), dict):
                key_value = wallets.get('arweave', {}).get('jwk')
            if isinstance(key_value, dict):
                key_value = json.dumps(key_value, indent=2)
        else:
            key_value = None

        if isinstance(key_value, bytes):
            key_value = key_value.hex()

        if not key_value:
            return {'success': False, 'error': f'No private key found in backup for {currency_upper}.'}

        return {'success': True, 'private_key': str(key_value)}

    def _on_private_key_loaded(self, currency: str, result: dict):
        if not result or not result.get('success'):
            error_message = (result or {}).get('error', 'Unable to load private key from backup.')
            QMessageBox.warning(self, 'Private Key Unavailable', error_message)
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(f"{currency.upper()} Private Key")
        dialog.setModal(True)
        dialog.resize(700, 380)

        layout = QVBoxLayout(dialog)
        value_display = QTextEdit()
        value_display.setReadOnly(True)
        value_display.setPlainText(result.get('private_key', ''))
        layout.addWidget(value_display)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.exec_()
    
    def _on_delete_clicked(self):
        """Handle delete button click."""
        reply = QMessageBox.warning(
            self,
            "Remove Wallet",
            f"Are you sure you want to remove '{self.wallet_info.name}'?\n\n"
            "This action cannot be undone. Make sure you have a backup!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.delete_clicked.emit()
            self.close()
