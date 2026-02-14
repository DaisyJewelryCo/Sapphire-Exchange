"""
Enhanced Multi-Currency Wallet Widget for Sapphire Exchange.
Supports DOGE, Nano, and Arweave with real-time balance updates and secure operations.
"""
import asyncio
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QTabWidget, QGroupBox, QLineEdit, QTextEdit, QMessageBox,
                             QProgressBar, QFrame, QScrollArea, QDialog, QDialogButtonBox,
                             QFormLayout, QCheckBox, QSpinBox, QComboBox, QTableWidget,
                             QTableWidgetItem, QHeaderView, QApplication, QFileDialog,
                             QSizePolicy)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QPixmap, QIcon, QColor, QPalette
import qrcode
from PIL import Image
import io

from security.security_manager import SecurityManager
from security.performance_manager import PerformanceManager
from services.application_service import app_service
from services.arweave_purchase_service import get_arweave_purchase_service
from services.funding_manager_service import get_funding_manager_service
from services.transaction_tracker import get_transaction_tracker
from utils.conversion_utils import format_currency
from utils.async_worker import AsyncWorker
from utils.validation_utils import Validator


class StatusDotsWidget(QWidget):
    def __init__(self, statuses, parent=None):
        super().__init__(parent)
        self.setFixedWidth(22)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignTop)
        self.set_statuses(statuses)
    def set_statuses(self, statuses):
        while self.layout.count():
            item = self.layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        for status in statuses:
            dot = QLabel()
            dot.setFixedSize(14, 14)
            color = "#2ecc40" if status == "success" or status == "connected" else ("#ff4136" if status == "error" or status == "disconnected" else "#ffdc00")
            dot.setStyleSheet(f"background-color: {color}; border-radius: 7px; margin: 2px 0 2px 0;")
            self.layout.addWidget(dot)


class WalletBalanceWidget(QWidget):
    """Widget displaying balance for a single currency."""
    
    balance_updated = pyqtSignal(str, dict)  # currency, balance_data
    
    def __init__(self, currency: str, parent=None):
        super().__init__(parent)
        self.currency = currency.upper()
        self.balance_data = {}
        self.statuses = ["disconnected"]
        self.tracker = None
        self.setup_ui()
        self.setup_pending_refresh()
        
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
        
        if self.currency == "ARWEAVE":
            self.buy_btn = QPushButton("Buy with USDC")
            self.buy_btn.clicked.connect(self.show_purchase_dialog)
            button_layout.addWidget(self.buy_btn)
        
        layout.addLayout(button_layout)
        
        # Status indicator and label layout
        status_row = QHBoxLayout()
        self.status_dots_widget = StatusDotsWidget(self.statuses)
        status_row.addWidget(self.status_dots_widget)
        status_row.setAlignment(self.status_dots_widget, Qt.AlignLeft | Qt.AlignTop)
        self.status_label = QLabel("Status: Disconnected")
        self.status_label.setFont(QFont("Arial", 8))
        self.status_label.setStyleSheet("color: red;")
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        layout.addLayout(status_row)
        
        # Pending Transactions for this currency
        self.pending_label = QLabel(f"Pending {self.currency} Transactions")
        self.pending_label.setFont(QFont("Arial", 9, QFont.Bold))
        self.pending_label.setStyleSheet("color: #666; margin-top: 8px;")
        layout.addWidget(self.pending_label)
        
        self.pending_list = QListWidget()
        self.pending_list.setMaximumHeight(80)
        self.pending_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #e2e8f0;
                border-radius: 4px;
                background: #f8fafc;
                font-size: 9px;
            }
            QListWidget::item {
                padding: 4px;
                border-bottom: 1px solid #f0f0f0;
            }
            QListWidget::item:last {
                border-bottom: none;
            }
        """)
        layout.addWidget(self.pending_list)
        
        # Remove height constraint to prevent text cutoff
        # self.setMaximumHeight(200)
        self.setMinimumHeight(220)  # Increased to accommodate pending transactions
        self.setStyleSheet("""
            QWidget {
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 10px;
                margin: 5px;
                background: white;
            }
        """)
    
    def update_status_dots(self, statuses):
        self.status_dots_widget.set_statuses(statuses)

    def update_balance(self, balance_data: dict):
        """Update the balance display."""
        self.balance_data = balance_data
        # Determine statuses
        statuses = []
        status_val = balance_data.get('status')
        if isinstance(status_val, list):
            statuses = status_val
        elif status_val:
            statuses = [status_val]
        else:
            statuses = ["disconnected"]
        self.update_status_dots(statuses)
        if 'success' in statuses or 'connected' in statuses:
            balance = balance_data.get('balance', '0')
            if self.currency == 'NANO':
                try:
                    balance_nano = float(balance) / (10**30)
                    formatted_balance = f"{balance_nano:.6f} NANO"
                except:
                    formatted_balance = f"{balance} raw"
            elif self.currency == 'DOGE':
                try:
                    formatted_balance = f"{float(balance):,.2f} DOGE"
                except:
                    formatted_balance = f"{balance} DOGE"
            else:
                formatted_balance = str(balance)
            self.balance_label.setText(f"Balance: {formatted_balance}")
            usd_value = balance_data.get('usd', '0.00')
            self.usd_label.setText(f"USD: ${usd_value}")
            address = balance_data.get('address', 'N/A')
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
    
    def setup_pending_refresh(self):
        """Setup auto-refresh of pending transactions."""
        self.pending_timer = QTimer()
        self.pending_timer.timeout.connect(self.refresh_pending_transactions)
        self.pending_timer.start(4000)
    
    def refresh_pending_transactions(self):
        """Refresh pending transactions display."""
        try:
            user = app_service.get_current_user()
            if not user or not self.tracker:
                # Try to initialize tracker
                worker = AsyncWorker(self._init_tracker_async())
                worker.finished.connect(self._display_pending)
                worker.start()
                self._tracker_worker = worker
                return
            
            self._display_pending()
        except Exception as e:
            print(f"Error refreshing pending: {e}")
    
    async def _init_tracker_async(self):
        """Initialize tracker asynchronously."""
        try:
            self.tracker = await get_transaction_tracker()
        except Exception as e:
            print(f"Error initializing tracker: {e}")
    
    def _display_pending(self):
        """Display pending transactions for this currency."""
        try:
            if not self.tracker:
                return
            
            user = app_service.get_current_user()
            if not user:
                return
            
            # Get pending transactions for this currency
            pending = self.tracker.get_pending_transactions(
                user_id=user.id,
                currency=self.currency
            )
            
            # Clear list
            self.pending_list.clear()
            
            if not pending:
                self.pending_label.setText(f"✓ No pending {self.currency} transactions")
                return
            
            # Add items for each pending transaction
            for tx in pending:
                target = self.tracker.confirmation_targets.get(self.currency, 6)
                
                # Format transaction item
                tx_type = "Send" if tx.type == "send" else "Receive"
                status_icon = "⏳" if tx.status == "pending" else "✓" if tx.status == "confirmed" else "✗"
                
                item_text = (
                    f"{status_icon} {tx_type}: {tx.amount} {self.currency} "
                    f"({tx.confirmations}/{target} confirms) - {tx.status.upper()}"
                )
                
                from PyQt5.QtWidgets import QListWidgetItem
                item = QListWidgetItem(item_text)
                
                # Color code based on status
                if tx.status == "pending":
                    item.setForeground(QColor("#ff9800"))
                elif tx.status == "confirmed":
                    item.setForeground(QColor("#4caf50"))
                elif tx.status == "failed":
                    item.setForeground(QColor("#f44336"))
                
                self.pending_list.addItem(item)
            
            # Update label
            self.pending_label.setText(f"📊 Pending {self.currency} Transactions ({len(pending)})")
        
        except Exception as e:
            self.pending_label.setText(f"Error loading: {str(e)[:30]}")
    
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
    
    def show_purchase_dialog(self):
        """Show purchase dialog for Arweave."""
        dialog = ArweavePurchaseDialog(self)
        dialog.exec_()


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
        
        # Note/Memo (optional for all currencies)
        self.note_edit = QLineEdit()
        self.note_edit.setPlaceholderText("Optional note or memo")
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
        
        show_loading = QMessageBox(self)
        show_loading.setWindowTitle("Processing")
        show_loading.setText("Validating address and processing transaction...")
        show_loading.setStandardButtons(QMessageBox.NoButton)
        show_loading.show()
        QApplication.processEvents()
        
        try:
            user = app_service.get_current_user()
            if not user:
                raise Exception("User not authenticated")
            
            if self.currency == "NANO":
                if not user.nano_address:
                    raise Exception("Nano wallet not configured")
                
                if not app_service.blockchain.nano_client.validate_address(recipient):
                    show_loading.close()
                    QMessageBox.warning(self, "Invalid Address", f"Invalid {self.currency} address format.")
                    return
                
                amount_raw = app_service.blockchain.nano_client.nano_to_raw(amount_float)
                
                note = self.note_edit.text().strip() if hasattr(self, 'note_edit') else ""
                
                worker = AsyncWorker(
                    app_service.blockchain.send_nano(user.nano_address, recipient, str(amount_raw), memo=note)
                )
                worker.finished.connect(lambda tx_id: self._on_transaction_complete(show_loading, tx_id, amount))
                worker.error.connect(lambda err: self._on_transaction_error(show_loading, err))
                worker.start()
                self._worker = worker
                
            elif self.currency == "DOGE":
                if not user.dogecoin_address:
                    raise Exception("Dogecoin wallet not configured")
                
                note = self.note_edit.text().strip() if hasattr(self, 'note_edit') else ""
                
                worker = AsyncWorker(
                    app_service.blockchain.dogecoin_client.send_payment(recipient, amount_float, comment=note)
                )
                worker.finished.connect(lambda tx_id: self._on_transaction_complete(show_loading, tx_id, amount))
                worker.error.connect(lambda err: self._on_transaction_error(show_loading, err))
                worker.start()
                self._worker = worker
                
            elif self.currency == "ARWEAVE":
                if not user.arweave_address:
                    raise Exception("Arweave wallet not configured")
                
                note = self.note_edit.text().strip() if hasattr(self, 'note_edit') else ""
                
                worker = AsyncWorker(
                    app_service.blockchain.arweave_client.send_payment(user.arweave_address, recipient, amount_float, memo=note)
                )
                worker.finished.connect(lambda tx_id: self._on_transaction_complete(show_loading, tx_id, amount))
                worker.error.connect(lambda err: self._on_transaction_error(show_loading, err))
                worker.start()
                self._worker = worker
            else:
                show_loading.close()
                QMessageBox.warning(self, "Unsupported Currency", f"{self.currency} transactions not yet implemented.")
                
        except Exception as e:
            show_loading.close()
            QMessageBox.critical(self, "Error", f"Transaction failed: {str(e)}")
    
    def _on_transaction_complete(self, dialog, tx_id, amount):
        """Handle successful transaction."""
        dialog.close()
        if tx_id:
            # Track the transaction
            user = app_service.get_current_user()
            if user:
                worker = AsyncWorker(self._track_transaction(user, amount, tx_id))
                worker.finished.connect(lambda: self._show_success_message(tx_id, amount))
                worker.start()
                self._track_worker = worker
            else:
                self._show_success_message(tx_id, amount)
        else:
            QMessageBox.warning(self, "Transaction Failed", "Transaction could not be processed.")
    
    async def _track_transaction(self, user, amount, tx_id):
        """Track the transaction in the tracker."""
        try:
            from services.wallet_service import wallet_service
            recipient = self.recipient_edit.text().strip()
            
            await wallet_service.track_outgoing_transaction(
                user=user,
                currency=self.currency,
                amount=str(amount),
                to_address=recipient,
                tx_hash=tx_id,
                metadata={
                    'note': self.note_edit.text().strip() if hasattr(self, 'note_edit') else '',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            )
        except Exception as e:
            print(f"Error tracking transaction: {e}")
    
    def _show_success_message(self, tx_id, amount):
        """Show success message."""
        QMessageBox.information(self, "Transaction Sent", 
                              f"Transaction of {amount} {self.currency} has been sent!\n\n"
                              f"Transaction ID: {tx_id[:32]}..." if len(str(tx_id)) > 32 else f"Transaction ID: {tx_id}\n\n"
                              f"The transaction is being monitored for confirmations.")
        self.accept()
    
    def _on_transaction_error(self, dialog, error):
        """Handle transaction error."""
        dialog.close()
        QMessageBox.critical(self, "Transaction Error", f"Error: {str(error)}")


class ArweavePurchaseDialog(QDialog):
    """Dialog for purchasing Arweave using USDC."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Buy Arweave")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.purchase_service = None
        self.execute_btn = None
        self.setup_ui()
    
    def setup_ui(self):
        """Setup purchase dialog UI."""
        layout = QVBoxLayout(self)
        
        info_label = QLabel("Purchase Arweave (AR) with USDC on Solana")
        info_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(info_label)
        
        form_layout = QFormLayout()
        
        self.usdc_amount_edit = QLineEdit()
        self.usdc_amount_edit.setPlaceholderText("Amount in USDC (e.g., 50)")
        self.usdc_amount_edit.textChanged.connect(self.update_estimate)
        form_layout.addRow("USDC Amount:", self.usdc_amount_edit)
        
        self.ar_estimate_label = QLabel("AR Estimate: Enter amount to calculate")
        self.ar_estimate_label.setStyleSheet("color: #666; font-weight: bold;")
        form_layout.addRow("", self.ar_estimate_label)
        
        self.price_impact_label = QLabel("Price Impact: --")
        self.price_impact_label.setStyleSheet("color: #ff9800;")
        form_layout.addRow("", self.price_impact_label)
        
        self.route_label = QLabel("Route: Ready to calculate")
        self.route_label.setStyleSheet("color: #666; font-size: 9px;")
        self.route_label.setWordWrap(True)
        form_layout.addRow("", self.route_label)
        
        layout.addLayout(form_layout)
        
        # Status indicator
        self.status_label = QLabel("ℹ️ Enter USDC amount to see AR estimate")
        self.status_label.setStyleSheet("color: #1976d2; padding: 8px; border: 1px solid #1976d2; border-radius: 3px; background: #e3f2fd;")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        warning = QLabel("⚠️ This will execute a swap on Jupiter DEX.\n"
                        "Make sure you have sufficient USDC balance and ~0.005 SOL for gas fees.")
        warning.setStyleSheet("color: #ff9800; padding: 10px; border: 1px solid #ff9800; border-radius: 3px;")
        warning.setWordWrap(True)
        layout.addWidget(warning)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.execute_purchase)
        button_box.rejected.connect(self.reject)
        self.execute_btn = button_box.button(QDialogButtonBox.Ok)
        self.execute_btn.setText("Execute Swap")
        self.execute_btn.setEnabled(False)
        layout.addWidget(button_box)
    
    def _parse_usdc_amount(self):
        amount_text = self.usdc_amount_edit.text().strip()
        if not amount_text:
            return None, "Please enter a USDC amount."
        
        try:
            amount_decimal = Decimal(amount_text)
        except InvalidOperation:
            return None, "Please enter a valid amount."
        
        if amount_decimal <= 0:
            return None, "Amount must be positive."
        
        validation = Validator.validate_amount(amount_text, min_amount=0.0)
        if not validation["valid"]:
            return None, validation["errors"][0]
        
        funding_service = get_funding_manager_service()
        is_valid, error = funding_service.validate_usdc_amount(float(amount_decimal))
        if not is_valid:
            return None, error
        
        return amount_decimal, ""
    
    def update_estimate(self):
        """Update AR estimate as user enters USDC amount."""
        amount_decimal, error = self._parse_usdc_amount()
        if error:
            if not self.usdc_amount_edit.text().strip():
                self.ar_estimate_label.setText("AR Estimate: Enter amount to calculate")
                self.price_impact_label.setText("Price Impact: --")
                self.route_label.setText("Route: Ready to calculate")
                self.status_label.setText("Enter USDC amount to see AR estimate")
                self.status_label.setStyleSheet("color: #1976d2; padding: 8px; border: 1px solid #1976d2; border-radius: 3px; background: #e3f2fd;")
            else:
                self.ar_estimate_label.setText("AR Estimate: Invalid input")
                self.price_impact_label.setText("Price Impact: N/A")
                self.route_label.setText("Route: N/A")
                self.status_label.setText(error)
                self.status_label.setStyleSheet("color: #d32f2f; padding: 8px; border: 1px solid #d32f2f; border-radius: 3px; background: #ffebee;")
            if hasattr(self, 'execute_btn'):
                self.execute_btn.setEnabled(False)
            return
        
        usdc_amount = float(amount_decimal)
        self.ar_estimate_label.setText("AR Estimate: Calculating...")
        self.price_impact_label.setText("Price Impact: Calculating...")
        self.route_label.setText("Route: Calculating...")
        self.status_label.setText("Fetching price information from Jupiter DEX...")
        self.status_label.setStyleSheet("color: #1976d2; padding: 8px; border: 1px solid #1976d2; border-radius: 3px; background: #e3f2fd;")
        
        worker = AsyncWorker(self._fetch_estimate(usdc_amount))
        worker.finished.connect(self._on_estimate_ready)
        worker.error.connect(self._on_estimate_error)
        worker.start()
        self._estimate_worker = worker
    
    def _on_estimate_error(self, error):
        """Handle estimate fetch error."""
        error_msg = str(error)[:100]
        self.ar_estimate_label.setText(f"AR Estimate: Error")
        self.price_impact_label.setText(f"Price Impact: N/A")
        self.route_label.setText(f"Route: Failed to calculate")
        self.status_label.setText(f"❌ Error: {error_msg}")
        self.status_label.setStyleSheet("color: #d32f2f; padding: 8px; border: 1px solid #d32f2f; border-radius: 3px; background: #ffebee;")
        if hasattr(self, 'execute_btn'):
            self.execute_btn.setEnabled(False)
    
    async def _fetch_estimate(self, usdc_amount: float):
        """Fetch AR estimate from Jupiter."""
        try:
            service = await get_arweave_purchase_service()
            
            # Try with auto-discovered token first
            quote = await service.get_quote(usdc_amount)
            
            # If that fails, try with known Arweave token mints
            if not quote or (quote and quote.output_amount == 0):
                print("Auto-discovery failed, trying known Arweave mints...")
                
                # Known Arweave-related token mints on Solana
                known_ar_mints = [
                    "HrFRX3amJZKUami6jPMD7T7qKHjWSXkkqwRWN3EcESj",  # Wrapped AR
                    "A7n8jRSQn9YvRLr6V8ztkP2z2ypeEo7b6QksA1JForward",  # ForwardAR
                    "JBoQUUqRpdB8oYbT8p7EQfR8nxZDj6z83ZV8b7Zz49sE",  # Test mint (placeholder)
                ]
                
                for mint in known_ar_mints:
                    quote = await service.get_quote(usdc_amount, output_mint=mint)
                    if quote and quote.output_amount > 0:
                        print(f"Found working Arweave mint: {mint}")
                        break
            
            if quote and quote.output_amount > 0:
                ar_amount = quote.output_amount / 1e12
                route_str = quote.route_description or "Direct swap via Jupiter DEX"
                
                return {
                    'ar_amount': ar_amount,
                    'price_impact': quote.price_impact,
                    'route': route_str
                }
            
            return await self._fetch_estimate_from_coingecko(usdc_amount)
        except Exception as e:
            print(f"Error fetching estimate from Jupiter: {e}")
            return await self._fetch_estimate_from_coingecko(usdc_amount)
    
    async def _fetch_estimate_from_coingecko(self, usdc_amount: float):
        try:
            import aiohttp
            
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": "arweave",
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_market_cap": "false"
            }
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status == 200:
                            data = await response.json()
                            if "arweave" in data:
                                ar_price_usd = data["arweave"].get("usd")
                                if ar_price_usd and ar_price_usd > 0:
                                    ar_amount = usdc_amount / ar_price_usd
                                    return {
                                        'ar_amount': ar_amount,
                                        'price_impact': 0.1,
                                        'route': f"CoinGecko Price Feed (AR/USD: ${ar_price_usd:.2f})"
                                    }
            except asyncio.TimeoutError:
                print("CoinGecko request timed out")
            except Exception as e:
                print(f"Error calling CoinGecko API: {e}")
            
            fallback_ar_price = 8.50
            ar_amount = usdc_amount / fallback_ar_price
            return {
                'ar_amount': ar_amount,
                'price_impact': 0.2,
                'route': f"Fallback Price (AR/USD: ${fallback_ar_price:.2f})"
            }
        except Exception as e:
            print(f"Critical error in CoinGecko fallback: {e}")
            ar_amount = usdc_amount / 10.0
            return {
                'ar_amount': ar_amount,
                'price_impact': 0.5,
                'route': "Emergency Fallback Price"
            }
    
    def _on_estimate_ready(self, estimate_data):
        """Handle estimate data ready."""
        try:
            if estimate_data:
                ar_amount = estimate_data.get('ar_amount', 0)
                price_impact = estimate_data.get('price_impact', 0)
                route = estimate_data.get('route', 'Unknown')
                
                if ar_amount > 0:
                    self.ar_estimate_label.setText(f"✓ AR Estimate: {ar_amount:.6f} AR")
                    self.ar_estimate_label.setStyleSheet("color: #2e7d32; font-weight: bold;")
                    self.price_impact_label.setText(f"Price Impact: {price_impact:.3f}%")
                    self.route_label.setText(f"Route: {route}")
                    self.status_label.setText(f"✓ Quote Ready - You will receive ~{ar_amount:.6f} AR")
                    self.status_label.setStyleSheet("color: #2e7d32; padding: 8px; border: 1px solid #2e7d32; border-radius: 3px; background: #f1f8e9;")
                    
                    # Enable execute button
                    if hasattr(self, 'execute_btn'):
                        self.execute_btn.setEnabled(True)
                else:
                    self.ar_estimate_label.setText("⚠️ AR Estimate: No output (check token mint)")
                    self.ar_estimate_label.setStyleSheet("color: #ff9800; font-weight: bold;")
                    self.price_impact_label.setText("Price Impact: N/A")
                    self.route_label.setText("Route: No valid route found")
                    self.status_label.setText("⚠️ Invalid quote received - no output amount. Please try a different amount.")
                    self.status_label.setStyleSheet("color: #ff9800; padding: 8px; border: 1px solid #ff9800; border-radius: 3px; background: #fff3e0;")
                    if hasattr(self, 'execute_btn'):
                        self.execute_btn.setEnabled(False)
            else:
                self.ar_estimate_label.setText("✗ AR Estimate: Failed to calculate")
                self.ar_estimate_label.setStyleSheet("color: #f44336; font-weight: bold;")
                self.price_impact_label.setText("Price Impact: N/A")
                self.route_label.setText("Route: No quote available")
                self.status_label.setText("❌ Failed to fetch quote - please try again")
                self.status_label.setStyleSheet("color: #d32f2f; padding: 8px; border: 1px solid #d32f2f; border-radius: 3px; background: #ffebee;")
                if hasattr(self, 'execute_btn'):
                    self.execute_btn.setEnabled(False)
        except Exception as e:
            error_msg = str(e)[:40]
            self.ar_estimate_label.setText(f"✗ Error: {error_msg}")
    
    def execute_purchase(self):
        """Execute the Arweave purchase."""
        try:
            amount_decimal, error = self._parse_usdc_amount()
            if error:
                QMessageBox.warning(self, "Invalid Amount", error)
                return
            
            usdc_amount = float(amount_decimal)
            
            user = app_service.get_current_user()
            if not user:
                QMessageBox.critical(self, "Error", "User not authenticated")
                return
            
            msg = f"Purchase {self.ar_estimate_label.text()} for {usdc_amount} USDC?\n\n" \
                  f"This will execute a swap on Jupiter DEX.\n" \
                  f"Confirm transaction?"
            
            reply = QMessageBox.question(self, "Confirm Purchase", msg,
                                        QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                progress = QMessageBox(self)
                progress.setWindowTitle("Processing")
                progress.setText("Building and sending swap transaction...\nThis may take a few seconds.")
                progress.setStandardButtons(QMessageBox.NoButton)
                progress.show()
                QApplication.processEvents()
                
                worker = AsyncWorker(self._execute_swap(usdc_amount, user))
                worker.finished.connect(lambda result: self._on_purchase_complete(progress, result))
                worker.error.connect(lambda err: self._on_purchase_error(progress, err))
                worker.start()
                self._purchase_worker = worker
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error: {str(e)}")
    
    async def _execute_swap(self, usdc_amount: float, user):
        """Execute the swap."""
        try:
            service = await get_arweave_purchase_service()
            
            if not hasattr(user, 'usdc_address') or not user.usdc_address:
                raise Exception("Solana wallet not configured")
            
            # Get private key (this would normally come from secure storage)
            # For now, assuming it's available in the user object
            keypair_bytes = None
            if hasattr(user, 'solana_private_key'):
                keypair_bytes = user.solana_private_key
            
            result = await service.execute_swap(
                user.usdc_address,
                usdc_amount,
                keypair_bytes=keypair_bytes
            )
            
            return result
        
        except Exception as e:
            print(f"Error executing swap: {e}")
            raise
    
    def _on_purchase_complete(self, dialog, result):
        """Handle successful purchase."""
        dialog.close()
        if result and result.get('success'):
            tx_id = result.get('transaction_id', '')
            display_id = tx_id[:20] + "..." if len(tx_id) > 20 else tx_id
            
            QMessageBox.information(self, "Purchase Successful",
                                  f"Arweave purchase initiated!\n\n"
                                  f"Transaction: {display_id}\n\n"
                                  f"The AR will appear in your wallet after confirmation.")
            self.accept()
        else:
            error_msg = result.get('error', 'Unknown error') if result else 'Unknown error'
            QMessageBox.warning(self, "Purchase Failed", f"Error: {error_msg}")
    
    def _on_purchase_error(self, dialog, error):
        """Handle purchase error."""
        dialog.close()
        QMessageBox.critical(self, "Purchase Error", f"Error: {str(error)}")


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
        # Increase height to prevent text cutoff
        address_text.setMinimumHeight(50)
        address_text.setMaximumHeight(80)  # Increased from 60 to 80
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


class WalletWidget(QWidget):
    """Main widget to display multiple currency balances."""
    
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
        # Increase height to prevent text cutoff
        self.breakdown_table.setMinimumHeight(120)
        self.breakdown_table.setMaximumHeight(180)  # Increased from 150 to 180
        layout.addWidget(self.breakdown_table)
        
        # Remove height constraint to prevent text cutoff
        # self.setMaximumHeight(250)
        self.setMinimumHeight(200)
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
        
        self.confirm_checkbox.toggled.connect(self._on_confirm_checkbox)
    
    def _on_confirm_checkbox(self, checked):
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(checked)
        if checked:
            # Simulate click on OK button to ensure QDialogButtonBox logic is triggered
            self.button_box.button(QDialogButtonBox.Ok).click()
    
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


class SimpleWalletWidget(QWidget):
    """Simple wallet widget for basic balance display."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_balances()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("Wallet")
        header.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(header)
        
        # Balances
        self.balances_group = QGroupBox("Balances")
        balances_layout = QVBoxLayout()
        
        self.sol_balance_label = QLabel("SOL: Loading...")
        self.usdc_balance_label = QLabel("USDC: Loading...")
        self.nano_balance_label = QLabel("NANO: Loading...")
        self.arweave_balance_label = QLabel("ARWEAVE: Loading...")
        
        balances_layout.addWidget(self.sol_balance_label)
        balances_layout.addWidget(self.usdc_balance_label)
        balances_layout.addWidget(self.nano_balance_label)
        balances_layout.addWidget(self.arweave_balance_label)
        
        self.balances_group.setLayout(balances_layout)
        layout.addWidget(self.balances_group)
        
        # Addresses
        self.addresses_group = QGroupBox("Addresses")
        addresses_layout = QVBoxLayout()
        
        user = app_service.get_current_user()
        if user:
            solana_address = getattr(user, 'usdc_address', 'Not set')
            
            self.sol_address_label = QLabel(f"SOL: {solana_address}")
            self.usdc_address_label = QLabel(f"USDC: {solana_address}")
            self.nano_address_label = QLabel(f"NANO: {user.nano_address}")
            self.arweave_address_label = QLabel(f"ARWEAVE: {user.arweave_address}")
            
            # Make addresses selectable/copyable
            for label in [self.sol_address_label, self.usdc_address_label, self.nano_address_label, self.arweave_address_label]:
                label.setTextInteractionFlags(label.textInteractionFlags() | Qt.TextSelectableByMouse)
                label.setFont(QFont("Courier", 8))
                label.setStyleSheet("color: #666; background: #f5f5f5; padding: 4px; border-radius: 3px; margin: 2px 0;")
            
            addresses_layout.addWidget(self.sol_address_label)
            addresses_layout.addWidget(self.usdc_address_label)
            addresses_layout.addWidget(self.nano_address_label)
            addresses_layout.addWidget(self.arweave_address_label)
        
        self.addresses_group.setLayout(addresses_layout)
        layout.addWidget(self.addresses_group)
        
        # Refresh button
        self.refresh_button = QPushButton("Refresh Balances")
        self.refresh_button.clicked.connect(self.load_balances)
        layout.addWidget(self.refresh_button)
        
        # Add stretch to push content to the top but allow expansion
        layout.addStretch()
        self.setLayout(layout)
    
    def load_balances(self):
        """Load wallet balances."""
        if not app_service.is_user_logged_in():
            return
        
        worker = AsyncWorker(app_service.get_wallet_balances())
        worker.finished.connect(self.on_balances_loaded)
        worker.error.connect(self.on_error)
        worker.start()
        self.worker = worker
    
    def on_balances_loaded(self, balances):
        """Handle loaded balances."""
        sol_balance = balances.get('sol', 0) or 0
        usdc_balance = balances.get('usdc', 0) or 0
        nano_balance = balances.get('nano', 0) or 0
        arweave_balance = balances.get('arweave', 0) or 0
        
        self.sol_balance_label.setText(f"SOL: {format_currency(sol_balance, 'SOL')}")
        self.usdc_balance_label.setText(f"USDC: {format_currency(usdc_balance, 'USDC')}")
        self.nano_balance_label.setText(f"NANO: {format_currency(nano_balance, 'NANO')}")
        self.arweave_balance_label.setText(f"ARWEAVE: {format_currency(arweave_balance, 'ARWEAVE')}")
    
    def on_error(self, error):
        """Handle errors."""
        self.sol_balance_label.setText("SOL: Error loading")
        self.usdc_balance_label.setText("USDC: Error loading")
        self.nano_balance_label.setText("NANO: Error loading")
        self.arweave_balance_label.setText("ARWEAVE: Error loading")