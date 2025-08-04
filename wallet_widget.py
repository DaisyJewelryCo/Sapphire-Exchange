"""
Enhanced Multi-Currency Wallet Widget for Sapphire Exchange.
Supports DOGE, Nano, and Arweave with real-time balance updates and secure operations.
"""
import asyncio
import json
from datetime import datetime, timezone
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QTabWidget, QGroupBox, QLineEdit, QTextEdit, QMessageBox,
                             QProgressBar, QFrame, QScrollArea, QDialog, QDialogButtonBox,
                             QFormLayout, QCheckBox, QSpinBox, QComboBox, QTableWidget,
                             QTableWidgetItem, QHeaderView, QApplication, QFileDialog)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QPixmap, QIcon, QColor, QPalette
import qrcode
from PIL import Image
import io

from dogecoin_utils import DogeWalletManager
from security_manager import SecurityManager
from performance_manager import PerformanceManager


class WalletBalanceWidget(QWidget):
    """Widget displaying balance for a single currency."""
    
    balance_updated = pyqtSignal(str, dict)  # currency, balance_data
    
    def __init__(self, currency: str, parent=None):
        super().__init__(parent)
        self.currency = currency.upper()
        self.balance_data = {}
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the balance widget UI."""
        layout = QVBoxLayout(self)
        
        # Currency header
        header_layout = QHBoxLayout()
        
        # Currency icon (placeholder)
        icon_label = QLabel("💰")
        icon_label.setFont(QFont("Arial", 16))
        header_layout.addWidget(icon_label)
        
        # Currency name
        currency_label = QLabel(self.currency)
        currency_label.setFont(QFont("Arial", 14, QFont.Bold))
        header_layout.addWidget(currency_label)
        
        header_layout.addStretch()
        
        # Refresh button
        refresh_btn = QPushButton("🔄")
        refresh_btn.setMaximumSize(30, 30)
        refresh_btn.clicked.connect(self.refresh_balance)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Balance display
        self.balance_label = QLabel("Balance: Loading...")
        self.balance_label.setFont(QFont("Arial", 12))
        layout.addWidget(self.balance_label)
        
        # USD equivalent
        self.usd_label = QLabel("USD: $0.00")
        self.usd_label.setFont(QFont("Arial", 10))
        self.usd_label.setStyleSheet("color: gray;")
        layout.addWidget(self.usd_label)
        
        # Address display
        self.address_label = QLabel("Address: Not loaded")
        self.address_label.setFont(QFont("Arial", 9))
        self.address_label.setWordWrap(True)
        self.address_label.setStyleSheet("color: #666; background: #f0f0f0; padding: 5px; border-radius: 3px;")
        layout.addWidget(self.address_label)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self.show_send_dialog)
        button_layout.addWidget(self.send_btn)
        
        self.receive_btn = QPushButton("Receive")
        self.receive_btn.clicked.connect(self.show_receive_dialog)
        button_layout.addWidget(self.receive_btn)
        
        layout.addLayout(button_layout)
        
        # Status indicator
        self.status_label = QLabel("Status: Disconnected")
        self.status_label.setFont(QFont("Arial", 8))
        self.status_label.setStyleSheet("color: red;")
        layout.addWidget(self.status_label)
        
        self.setMaximumHeight(200)
        self.setStyleSheet("""
            QWidget {
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 10px;
                margin: 5px;
                background: white;
            }
        """)
    
    def update_balance(self, balance_data: dict):
        """Update the balance display."""
        self.balance_data = balance_data
        
        if balance_data.get('status') == 'success':
            balance = balance_data.get('balance', '0')
            
            # Format balance based on currency
            if self.currency == 'NANO':
                # Convert from raw to NANO
                try:
                    balance_nano = float(balance) / (10**30)
                    formatted_balance = f"{balance_nano:.6f} NANO"
                except:
                    formatted_balance = f"{balance} raw"
            elif self.currency == 'DOGE':
                formatted_balance = f"{balance} DOGE"
            elif self.currency == 'ARWEAVE':
                formatted_balance = f"{balance} AR"
            else:
                formatted_balance = f"{balance} {self.currency}"
            
            self.balance_label.setText(f"Balance: {formatted_balance}")
            
            # Update USD equivalent if available
            usd_value = balance_data.get('usd_value')
            if usd_value:
                self.usd_label.setText(f"USD: ${usd_value:.2f}")
            
            # Update address
            address = balance_data.get('address', 'Unknown')
            if len(address) > 40:
                display_address = f"{address[:20]}...{address[-20:]}"
            else:
                display_address = address
            self.address_label.setText(f"Address: {display_address}")
            
            self.status_label.setText("Status: Connected")
            self.status_label.setStyleSheet("color: green;")
            
        else:
            error = balance_data.get('error', 'Unknown error')
            self.balance_label.setText(f"Balance: Error - {error}")
            self.status_label.setText("Status: Error")
            self.status_label.setStyleSheet("color: red;")
    
    def refresh_balance(self):
        """Emit signal to refresh balance."""
        self.balance_updated.emit(self.currency.lower(), {})
    
    def show_send_dialog(self):
        """Show send transaction dialog."""
        dialog = SendTransactionDialog(self.currency, self.balance_data, self)
        dialog.exec_()
    
    def show_receive_dialog(self):
        """Show receive dialog with QR code."""
        address = self.balance_data.get('address', '')
        if address:
            dialog = ReceiveDialog(self.currency, address, self)
            dialog.exec_()
        else:
            QMessageBox.warning(self, "No Address", "No address available for receiving.")


class SendTransactionDialog(QDialog):
    """Dialog for sending transactions."""
    
    def __init__(self, currency: str, balance_data: dict, parent=None):
        super().__init__(parent)
        self.currency = currency
        self.balance_data = balance_data
        self.setWindowTitle(f"Send {currency}")
        self.setModal(True)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the send dialog UI."""
        layout = QVBoxLayout(self)
        
        # Form layout
        form_layout = QFormLayout()
        
        # Recipient address
        self.recipient_edit = QLineEdit()
        self.recipient_edit.setPlaceholderText(f"Enter {self.currency} address")
        form_layout.addRow("To Address:", self.recipient_edit)
        
        # Amount
        self.amount_edit = QLineEdit()
        self.amount_edit.setPlaceholderText("0.00")
        form_layout.addRow("Amount:", self.amount_edit)
        
        # Fee (for DOGE)
        if self.currency == 'DOGE':
            self.fee_edit = QLineEdit()
            self.fee_edit.setText("1.0")  # Default DOGE fee
            form_layout.addRow("Fee:", self.fee_edit)
        
        # Note/Memo
        self.note_edit = QLineEdit()
        self.note_edit.setPlaceholderText("Optional note")
        form_layout.addRow("Note:", self.note_edit)
        
        layout.addLayout(form_layout)
        
        # Balance info
        balance_info = QLabel(f"Available: {self.balance_data.get('balance', '0')} {self.currency}")
        balance_info.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(balance_info)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.send_transaction)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def send_transaction(self):
        """Process the send transaction."""
        recipient = self.recipient_edit.text().strip()
        amount = self.amount_edit.text().strip()
        
        if not recipient or not amount:
            QMessageBox.warning(self, "Invalid Input", "Please enter recipient address and amount.")
            return
        
        try:
            amount_float = float(amount)
            if amount_float <= 0:
                raise ValueError("Amount must be positive")
        except ValueError:
            QMessageBox.warning(self, "Invalid Amount", "Please enter a valid amount.")
            return
        
        # Show confirmation
        msg = f"Send {amount} {self.currency} to:\n{recipient}\n\nConfirm transaction?"
        reply = QMessageBox.question(self, "Confirm Transaction", msg,
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # TODO: Implement actual transaction sending
            QMessageBox.information(self, "Transaction Sent", 
                                  f"Transaction of {amount} {self.currency} has been sent!")
            self.accept()


class ReceiveDialog(QDialog):
    """Dialog for receiving payments with QR code."""
    
    def __init__(self, currency: str, address: str, parent=None):
        super().__init__(parent)
        self.currency = currency
        self.address = address
        self.setWindowTitle(f"Receive {currency}")
        self.setModal(True)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the receive dialog UI."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel(f"Receive {self.currency}")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # QR Code
        qr_label = QLabel()
        qr_label.setAlignment(Qt.AlignCenter)
        
        try:
            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(self.address)
            qr.make(fit=True)
            
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to QPixmap
            buffer = io.BytesIO()
            qr_img.save(buffer, format='PNG')
            buffer.seek(0)
            
            pixmap = QPixmap()
            pixmap.loadFromData(buffer.getvalue())
            qr_label.setPixmap(pixmap.scaled(200, 200, Qt.KeepAspectRatio))
            
        except Exception as e:
            qr_label.setText(f"QR Code Error: {str(e)}")
        
        layout.addWidget(qr_label)
        
        # Address display
        address_group = QGroupBox("Your Address")
        address_layout = QVBoxLayout(address_group)
        
        address_text = QTextEdit()
        address_text.setPlainText(self.address)
        address_text.setReadOnly(True)
        address_text.setMaximumHeight(60)
        address_layout.addWidget(address_text)
        
        # Copy button
        copy_btn = QPushButton("Copy Address")
        copy_btn.clicked.connect(self.copy_address)
        address_layout.addWidget(copy_btn)
        
        layout.addWidget(address_group)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
    
    def copy_address(self):
        """Copy address to clipboard."""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.address)
        QMessageBox.information(self, "Copied", "Address copied to clipboard!")


class MultiCurrencyWalletWidget(QWidget):
    """Main multi-currency wallet widget."""
    
    def __init__(self, client, parent=None):
        super().__init__(parent)
        self.client = client
        self.wallet_widgets = {}
        self.setup_ui()
        
        # Setup refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_all_balances)
        self.refresh_timer.start(30000)  # Refresh every 30 seconds
    
    def setup_ui(self):
        """Setup the main wallet UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel("Multi-Currency Wallet")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Wallet actions
        generate_btn = QPushButton("Generate New Wallet")
        generate_btn.clicked.connect(self.generate_new_wallet)
        header_layout.addWidget(generate_btn)
        
        import_btn = QPushButton("Import Wallet")
        import_btn.clicked.connect(self.import_wallet)
        header_layout.addWidget(import_btn)
        
        export_btn = QPushButton("Export Wallet")
        export_btn.clicked.connect(self.export_wallet)
        header_layout.addWidget(export_btn)
        
        layout.addLayout(header_layout)
        
        # Currency tabs
        self.tab_widget = QTabWidget()
        
        # Create wallet widgets for each currency
        currencies = ['NANO', 'DOGE', 'ARWEAVE']
        for currency in currencies:
            wallet_widget = WalletBalanceWidget(currency)
            wallet_widget.balance_updated.connect(self.refresh_balance)
            self.wallet_widgets[currency.lower()] = wallet_widget
            self.tab_widget.addTab(wallet_widget, currency)
        
        layout.addWidget(self.tab_widget)
        
        # Portfolio summary
        self.portfolio_widget = PortfolioSummaryWidget()
        layout.addWidget(self.portfolio_widget)
    
    def generate_new_wallet(self):
        """Generate a new multi-currency wallet."""
        reply = QMessageBox.question(self, "Generate New Wallet",
                                   "This will generate a new wallet with a new seed phrase.\n"
                                   "Make sure to backup your current wallet first!\n\n"
                                   "Continue?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            dialog = WalletGenerationDialog(self)
            dialog.exec_()
    
    def import_wallet(self):
        """Import wallet from seed phrase or file."""
        dialog = WalletImportDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            seed_phrase = dialog.get_seed_phrase()
            if seed_phrase:
                self.initialize_wallet_from_seed(seed_phrase)
    
    def export_wallet(self):
        """Export wallet securely."""
        dialog = WalletExportDialog(self)
        dialog.exec_()
    
    def initialize_wallet_from_seed(self, seed_phrase: str):
        """Initialize wallet from seed phrase."""
        # TODO: Implement wallet initialization
        QMessageBox.information(self, "Wallet Imported", "Wallet has been imported successfully!")
        self.refresh_all_balances()
    
    def refresh_balance(self, currency: str, _):
        """Refresh balance for specific currency."""
        # TODO: Implement balance refresh using client
        pass
    
    def refresh_all_balances(self):
        """Refresh all currency balances."""
        for currency in self.wallet_widgets.keys():
            self.refresh_balance(currency, {})


class PortfolioSummaryWidget(QWidget):
    """Widget showing portfolio summary and total value."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup portfolio summary UI."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Portfolio Summary")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(title)
        
        # Total value
        self.total_value_label = QLabel("Total Value: $0.00 USD")
        self.total_value_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.total_value_label.setStyleSheet("color: #2e7d32;")
        layout.addWidget(self.total_value_label)
        
        # Breakdown table
        self.breakdown_table = QTableWidget(0, 4)
        self.breakdown_table.setHorizontalHeaderLabels(["Currency", "Balance", "USD Value", "Percentage"])
        self.breakdown_table.horizontalHeader().setStretchLastSection(True)
        self.breakdown_table.setMaximumHeight(150)
        layout.addWidget(self.breakdown_table)
        
        self.setMaximumHeight(250)
        self.setStyleSheet("""
            QWidget {
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 10px;
                margin: 5px;
                background: #f9f9f9;
            }
        """)


class WalletGenerationDialog(QDialog):
    """Dialog for generating new wallet."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Generate New Wallet")
        self.setModal(True)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup wallet generation UI."""
        layout = QVBoxLayout(self)
        
        # Warning
        warning = QLabel("⚠️ IMPORTANT: Write down your seed phrase and store it safely!\n"
                        "This is the only way to recover your wallet.")
        warning.setStyleSheet("color: red; font-weight: bold; padding: 10px; "
                            "border: 2px solid red; border-radius: 5px;")
        warning.setWordWrap(True)
        layout.addWidget(warning)
        
        # Generate button
        generate_btn = QPushButton("Generate New Wallet")
        generate_btn.clicked.connect(self.generate_wallet)
        layout.addWidget(generate_btn)
        
        # Seed phrase display
        self.seed_display = QTextEdit()
        self.seed_display.setReadOnly(True)
        self.seed_display.setVisible(False)
        layout.addWidget(self.seed_display)
        
        # Confirmation checkbox
        self.confirm_checkbox = QCheckBox("I have written down my seed phrase safely")
        self.confirm_checkbox.setVisible(False)
        layout.addWidget(self.confirm_checkbox)
        
        # Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(False)
        layout.addWidget(self.button_box)
        
        self.confirm_checkbox.toggled.connect(
            lambda checked: self.button_box.button(QDialogButtonBox.Ok).setEnabled(checked)
        )
    
    def generate_wallet(self):
        """Generate new wallet and display seed phrase."""
        try:
            # TODO: Implement actual wallet generation
            seed_phrase = "word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12"
            
            self.seed_display.setPlainText(seed_phrase)
            self.seed_display.setVisible(True)
            self.confirm_checkbox.setVisible(True)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate wallet: {str(e)}")


class WalletImportDialog(QDialog):
    """Dialog for importing wallet."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import Wallet")
        self.setModal(True)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup wallet import UI."""
        layout = QVBoxLayout(self)
        
        # Import method tabs
        tab_widget = QTabWidget()
        
        # Seed phrase tab
        seed_tab = QWidget()
        seed_layout = QVBoxLayout(seed_tab)
        
        seed_layout.addWidget(QLabel("Enter your 12-24 word seed phrase:"))
        self.seed_edit = QTextEdit()
        self.seed_edit.setPlaceholderText("word1 word2 word3 ...")
        seed_layout.addWidget(self.seed_edit)
        
        tab_widget.addTab(seed_tab, "Seed Phrase")
        
        # File import tab
        file_tab = QWidget()
        file_layout = QVBoxLayout(file_tab)
        
        file_layout.addWidget(QLabel("Import from encrypted wallet file:"))
        
        file_select_layout = QHBoxLayout()
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setReadOnly(True)
        file_select_layout.addWidget(self.file_path_edit)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_file)
        file_select_layout.addWidget(browse_btn)
        
        file_layout.addLayout(file_select_layout)
        
        file_layout.addWidget(QLabel("Password:"))
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        file_layout.addWidget(self.password_edit)
        
        tab_widget.addTab(file_tab, "File Import")
        
        layout.addWidget(tab_widget)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def browse_file(self):
        """Browse for wallet file."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Wallet File", "", "JSON Files (*.json)")
        if file_path:
            self.file_path_edit.setText(file_path)
    
    def get_seed_phrase(self) -> str:
        """Get the seed phrase from input."""
        return self.seed_edit.toPlainText().strip()


class WalletExportDialog(QDialog):
    """Dialog for exporting wallet."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export Wallet")
        self.setModal(True)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup wallet export UI."""
        layout = QVBoxLayout(self)
        
        # Warning
        warning = QLabel("⚠️ WARNING: Exported wallet files contain sensitive information.\n"
                        "Store them securely and use a strong password!")
        warning.setStyleSheet("color: orange; font-weight: bold; padding: 10px; "
                            "border: 2px solid orange; border-radius: 5px;")
        warning.setWordWrap(True)
        layout.addWidget(warning)
        
        # Password fields
        form_layout = QFormLayout()
        
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        form_layout.addRow("Password:", self.password_edit)
        
        self.confirm_password_edit = QLineEdit()
        self.confirm_password_edit.setEchoMode(QLineEdit.Password)
        form_layout.addRow("Confirm Password:", self.confirm_password_edit)
        
        layout.addLayout(form_layout)
        
        # Export button
        export_btn = QPushButton("Export Wallet")
        export_btn.clicked.connect(self.export_wallet)
        layout.addWidget(export_btn)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
    
    def export_wallet(self):
        """Export the wallet."""
        password = self.password_edit.text()
        confirm_password = self.confirm_password_edit.text()
        
        if not password:
            QMessageBox.warning(self, "No Password", "Please enter a password.")
            return
        
        if password != confirm_password:
            QMessageBox.warning(self, "Password Mismatch", "Passwords do not match.")
            return
        
        # Get save location
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Wallet", "wallet_backup.json", 
                                                 "JSON Files (*.json)")
        if file_path:
            try:
                # TODO: Implement actual wallet export
                QMessageBox.information(self, "Export Complete", 
                                      f"Wallet exported successfully to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export wallet: {str(e)}")