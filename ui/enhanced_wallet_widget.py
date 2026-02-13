"""
Enhanced Wallet Widget with integrated popup dialogs.
Provides complete wallet management functionality with popups for all operations.
Integrates Plans 1-4 blockchain systems.
"""
from typing import Optional, Dict, List, Any
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QFrame, QMessageBox, QApplication, QGridLayout, QTabWidget, QFileDialog
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QColor
from datetime import datetime

from ui.dialogs.wallet_management import CreateWalletDialog, ImportWalletDialog, WalletSelectorDialog
from ui.dialogs.transaction_dialogs import SendTransactionDialog, ReceiveDialog, TransactionHistoryDialog
from ui.dialogs.backup_dialogs import MnemonicDisplayDialog, BackupWizardDialog, RecoveryWizardDialog
from ui.dialogs.settings_dialog import SettingsDialog
from ui.dialogs.wallet_details_dialog import WalletDetailsDialog
from ui.custom_widgets import (
    AddressDisplayWidget, BalanceWidget, QRCodeWidget,
    TransactionListWidget, WalletTileWidget, StatusIndicatorWidget
)


class EnhancedWalletWidget(QWidget):
    """Main wallet widget with integrated dialog popups."""
    
    wallet_changed = pyqtSignal(dict)
    transaction_sent = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_wallet = None
        self.wallets = []
        self.transactions = []
        self.settings = self._default_settings()
        self.setup_ui()
        self.setup_timers()
    
    def _default_settings(self) -> Dict[str, Any]:
        """Get default application settings."""
        return {
            'solana_rpc': 'https://api.mainnet-beta.solana.com',
            'nano_node': 'https://mynano.ninja/api',
            'arweave_gateway': 'https://arweave.net',
            'network_timeout': 30,
            'retry_attempts': 3,
            'session_timeout': 30,
            'password_for_transactions': True,
            'show_private_keys': False,
            'enable_biometric': True,
            'auto_lock_inactive': True,
            'theme': 'Light',
            'font_size': 11,
            'show_balance_usd': True,
            'refresh_interval': 30,
            'enable_logging': True,
            'log_level': 'INFO',
            'developer_mode': False,
        }
    
    def setup_ui(self):
        """Setup the main UI."""
        layout = QVBoxLayout(self)
        
        tabs = QTabWidget()
        tabs.addTab(self._create_dashboard_tab(), "Dashboard")
        tabs.addTab(self._create_wallets_tab(), "Wallets")
        tabs.addTab(self._create_transactions_tab(), "Transactions")
        tabs.addTab(self._create_backup_tab(), "Backup & Recovery")
        
        layout.addWidget(tabs)
    
    def _create_dashboard_tab(self) -> QWidget:
        """Create dashboard tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        header_layout = QHBoxLayout()
        
        title = QLabel("Wallet Dashboard")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        settings_btn = QPushButton("⚙️ Settings")
        settings_btn.clicked.connect(self.open_settings)
        header_layout.addWidget(settings_btn)
        
        layout.addLayout(header_layout)
        
        self.status_widget = StatusIndicatorWidget({
            "Solana": "Disconnected",
            "Nano": "Disconnected",
            "Arweave": "Disconnected"
        })
        layout.addWidget(self.status_widget)
        
        layout.addSpacing(20)
        
        balances_label = QLabel("Balances")
        balances_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(balances_label)
        
        self.balances_layout = QHBoxLayout()
        self.solana_balance = BalanceWidget("SOL", "0.00", "$0.00")
        self.nano_balance = BalanceWidget("NANO", "0.00", "$0.00")
        self.arweave_balance = BalanceWidget("AR", "0.00", "$0.00")
        
        self.balances_layout.addWidget(self.solana_balance)
        self.balances_layout.addWidget(self.nano_balance)
        self.balances_layout.addWidget(self.arweave_balance)
        
        layout.addLayout(self.balances_layout)
        
        layout.addSpacing(20)
        
        action_label = QLabel("Quick Actions")
        action_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(action_label)
        
        action_layout = QHBoxLayout()
        
        send_btn = QPushButton("📤 Send")
        send_btn.setMinimumHeight(40)
        send_btn.clicked.connect(self.open_send_dialog)
        action_layout.addWidget(send_btn)
        
        receive_btn = QPushButton("📥 Receive")
        receive_btn.setMinimumHeight(40)
        receive_btn.clicked.connect(self.open_receive_dialog)
        action_layout.addWidget(receive_btn)
        
        backup_btn = QPushButton("💾 Backup")
        backup_btn.setMinimumHeight(40)
        backup_btn.clicked.connect(self.open_backup_wizard)
        action_layout.addWidget(backup_btn)
        
        recover_btn = QPushButton("🔄 Recover")
        recover_btn.setMinimumHeight(40)
        recover_btn.clicked.connect(self.open_recovery_wizard)
        action_layout.addWidget(recover_btn)
        
        layout.addLayout(action_layout)
        
        layout.addSpacing(20)
        
        wallets_label = QLabel("Wallet Manager")
        wallets_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(wallets_label)
        
        self.dashboard_wallets_scroll = QScrollArea()
        self.dashboard_wallets_scroll.setWidgetResizable(True)
        self.dashboard_wallets_scroll.setMinimumHeight(250)
        self.dashboard_wallets_grid = QGridLayout()
        self.dashboard_wallets_grid.setSpacing(10)
        
        wallets_container = QWidget()
        wallets_container.setLayout(self.dashboard_wallets_grid)
        self.dashboard_wallets_scroll.setWidget(wallets_container)
        
        layout.addWidget(self.dashboard_wallets_scroll)
        
        return widget
    
    def _create_wallets_tab(self) -> QWidget:
        """Create wallets management tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        header_layout = QHBoxLayout()
        
        title = QLabel("Manage Wallets")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        create_btn = QPushButton("✨ Create New")
        create_btn.clicked.connect(self.open_create_wallet_dialog)
        header_layout.addWidget(create_btn)
        
        import_btn = QPushButton("📥 Import")
        import_btn.clicked.connect(self.open_import_wallet_dialog)
        header_layout.addWidget(import_btn)
        
        layout.addLayout(header_layout)
        
        self.wallets_scroll = QScrollArea()
        self.wallets_scroll.setWidgetResizable(True)
        self.wallets_grid = QGridLayout()
        
        wallets_container = QWidget()
        wallets_container.setLayout(self.wallets_grid)
        self.wallets_scroll.setWidget(wallets_container)
        
        layout.addWidget(self.wallets_scroll)
        
        return widget
    
    def _create_transactions_tab(self) -> QWidget:
        """Create transactions tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        title = QLabel("Transaction History")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title)
        
        self.transactions_widget = TransactionListWidget(self.transactions)
        layout.addWidget(self.transactions_widget)
        
        export_btn = QPushButton("📊 Export History")
        export_btn.clicked.connect(self.export_transaction_history)
        layout.addWidget(export_btn)
        
        return widget
    
    def _create_backup_tab(self) -> QWidget:
        """Create backup & recovery tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        title = QLabel("Backup & Recovery")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title)
        
        info_text = QLabel(
            "Secure your wallet with multiple backup methods:\n\n"
            "• Mnemonic Backup: Your 12-24 word recovery phrase\n"
            "• Physical Backup: Printable template for offline storage\n"
            "• Encrypted Backup: Password-protected key files\n"
            "• Social Recovery: Distribute recovery keys to trusted contacts"
        )
        info_text.setStyleSheet("color: #666; padding: 10px;")
        layout.addWidget(info_text)
        
        button_layout = QHBoxLayout()
        
        wizard_btn = QPushButton("🧙 Backup Wizard")
        wizard_btn.clicked.connect(self.open_backup_wizard)
        button_layout.addWidget(wizard_btn)
        
        recover_btn = QPushButton("🔄 Recovery Wizard")
        recover_btn.clicked.connect(self.open_recovery_wizard)
        button_layout.addWidget(recover_btn)
        
        layout.addLayout(button_layout)
        
        layout.addStretch()
        
        return widget
    
    def setup_timers(self):
        """Setup timers for balance updates."""
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_balances)
        self.refresh_timer.start(self.settings['refresh_interval'] * 1000)
    
    def open_create_wallet_dialog(self):
        """Open create wallet dialog."""
        dialog = CreateWalletDialog(parent=self)
        dialog.wallet_created.connect(self.on_wallet_created)
        dialog.exec_()
    
    def open_import_wallet_dialog(self):
        """Open import wallet dialog."""
        dialog = ImportWalletDialog(parent=self)
        dialog.wallet_imported.connect(self.on_wallet_imported)
        dialog.exec_()
    
    def on_wallet_created(self, wallet_info):
        """Handle wallet creation."""
        self.wallets.append(wallet_info)
        self.current_wallet = wallet_info
        self.wallet_changed.emit(wallet_info.__dict__)
        self.update_wallet_tiles()
        self.update_dashboard_wallets()
        
        QMessageBox.information(
            self,
            "Wallet Created",
            f"Wallet '{wallet_info.name}' has been created successfully."
        )
    
    def on_wallet_imported(self, wallet_info):
        """Handle wallet import."""
        self.wallets.append(wallet_info)
        self.current_wallet = wallet_info
        self.wallet_changed.emit(wallet_info.__dict__)
        self.update_wallet_tiles()
        self.update_dashboard_wallets()
        
        QMessageBox.information(
            self,
            "Wallet Imported",
            f"Wallet '{wallet_info.name}' has been imported successfully."
        )
    
    def update_wallet_tiles(self):
        """Update wallet tile display in Wallets tab."""
        while self.wallets_grid.count():
            item = self.wallets_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        for i, wallet in enumerate(self.wallets):
            tile = WalletTileWidget({
                'name': wallet.name,
                'balance': '$0.00',
                'status': 'Ready'
            })
            tile.clicked.connect(self.on_wallet_tile_clicked)
            
            row = i // 2
            col = i % 2
            self.wallets_grid.addWidget(tile, row, col)
    
    def update_dashboard_wallets(self):
        """Update wallet tile display in Dashboard tab."""
        while self.dashboard_wallets_grid.count():
            item = self.dashboard_wallets_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        for i, wallet in enumerate(self.wallets):
            tile = WalletTileWidget({
                'name': wallet.name,
                'balance': '$0.00',
                'status': 'Ready'
            })
            tile.clicked.connect(self.on_wallet_tile_clicked)
            
            row = i // 2
            col = i % 2
            self.dashboard_wallets_grid.addWidget(tile, row, col)
    
    def on_wallet_tile_clicked(self, wallet_info):
        """Handle wallet tile click."""
        if not wallet_info:
            QMessageBox.warning(self, "Error", "Invalid wallet information")
            return
        
        wallet_name = wallet_info.get('name', '') if isinstance(wallet_info, dict) else str(wallet_info)
        
        wallet = None
        for w in self.wallets:
            if w.name == wallet_name:
                wallet = w
                break
        
        if wallet:
            dialog = WalletDetailsDialog(wallet, parent=self)
            dialog.send_clicked.connect(self.on_send_from_details)
            dialog.receive_clicked.connect(self.on_receive_from_details)
            dialog.backup_clicked.connect(self.on_backup_from_details)
            dialog.recover_clicked.connect(self.on_recover_from_details)
            dialog.delete_clicked.connect(lambda: self.on_wallet_deleted(wallet))
            dialog.exec_()
        else:
            QMessageBox.warning(self, "Error", f"Wallet '{wallet_name}' not found")
    
    def open_send_dialog(self):
        """Open send transaction dialog."""
        if not self.current_wallet:
            QMessageBox.warning(self, "No Wallet", "Please create or select a wallet first")
            return
        
        dialog = SendTransactionDialog("Solana", "0.00", parent=self)
        dialog.transaction_sent.connect(self.on_transaction_sent)
        dialog.exec_()
    
    def open_receive_dialog(self):
        """Open receive dialog."""
        if not self.current_wallet:
            QMessageBox.warning(self, "No Wallet", "Please create or select a wallet first")
            return
        
        address = self.current_wallet.address_solana or "Address not available"
        dialog = ReceiveDialog("Solana", address, parent=self)
        dialog.exec_()
    
    def open_backup_wizard(self):
        """Open backup wizard."""
        if not self.current_wallet:
            QMessageBox.warning(self, "No Wallet", "Please create or select a wallet first")
            return
        
        dialog = BackupWizardDialog({
            'mnemonic': self.current_wallet.mnemonic,
            'name': self.current_wallet.name
        }, parent=self)
        dialog.backup_complete.connect(self.on_backup_complete)
        dialog.exec_()
    
    def open_recovery_wizard(self):
        """Open recovery wizard."""
        dialog = RecoveryWizardDialog(parent=self)
        dialog.recovery_complete.connect(self.on_recovery_complete)
        dialog.exec_()
    
    def open_settings(self):
        """Open settings dialog."""
        dialog = SettingsDialog(self.settings, parent=self)
        dialog.settings_changed.connect(self.on_settings_changed)
        dialog.exec_()
    
    def on_send_from_details(self, wallet_name):
        """Handle send from wallet details dialog."""
        for w in self.wallets:
            if w.name == wallet_name:
                self.current_wallet = w
                break
        self.open_send_dialog()
    
    def on_receive_from_details(self, wallet_name):
        """Handle receive from wallet details dialog."""
        for w in self.wallets:
            if w.name == wallet_name:
                self.current_wallet = w
                break
        self.open_receive_dialog()
    
    def on_backup_from_details(self):
        """Handle backup from wallet details dialog."""
        self.open_backup_wizard()
    
    def on_recover_from_details(self):
        """Handle recover from wallet details dialog."""
        self.open_recovery_wizard()
    
    def on_wallet_deleted(self, wallet):
        """Handle wallet deletion."""
        self.wallets = [w for w in self.wallets if w.name != wallet.name]
        if self.current_wallet == wallet:
            self.current_wallet = self.wallets[0] if self.wallets else None
        self.update_wallet_tiles()
        self.update_dashboard_wallets()
        
        QMessageBox.information(
            self,
            "Wallet Removed",
            f"Wallet '{wallet.name}' has been removed successfully."
        )
    
    def on_transaction_sent(self, transaction_data):
        """Handle transaction sent."""
        transaction_data['date'] = datetime.now().isoformat()
        transaction_data['status'] = 'pending'
        self.transactions.append(transaction_data)
        self.transaction_sent.emit(transaction_data)
    
    def on_backup_complete(self, backup_data):
        """Handle backup completion."""
        QMessageBox.information(
            self,
            "Backup Complete",
            "Your wallet has been backed up successfully."
        )
    
    def on_recovery_complete(self, mnemonic):
        """Handle recovery completion."""
        if mnemonic:
            QMessageBox.information(
                self,
                "Recovery Complete",
                "Wallet recovered successfully."
            )
    
    def on_settings_changed(self, settings):
        """Handle settings change."""
        self.settings = settings
        self.refresh_timer.setInterval(settings['refresh_interval'] * 1000)
        QMessageBox.information(self, "Settings", "Settings updated successfully")
    
    def refresh_balances(self):
        """Refresh wallet balances."""
        if self.current_wallet:
            self.solana_balance.update_balance("0.00", "$0.00")
            self.nano_balance.update_balance("0.00", "$0.00")
            self.arweave_balance.update_balance("0.00", "$0.00")
    
    def export_transaction_history(self):
        """Export transaction history."""
        if not self.transactions:
            QMessageBox.information(self, "No Transactions", "There are no transactions to export")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Transaction History",
            "transaction_history.csv",
            "CSV Files (*.csv);;JSON Files (*.json)"
        )
        
        if file_path:
            try:
                if file_path.endswith('.json'):
                    import json
                    with open(file_path, 'w') as f:
                        json.dump(self.transactions, f, indent=2)
                else:
                    import csv
                    with open(file_path, 'w') as f:
                        writer = csv.DictWriter(f, fieldnames=self.transactions[0].keys())
                        writer.writeheader()
                        writer.writerows(self.transactions)
                
                QMessageBox.information(
                    self,
                    "Exported",
                    f"Transaction history exported to {file_path}"
                )
            except Exception as e:
                QMessageBox.critical(self, "Export Error", str(e))
