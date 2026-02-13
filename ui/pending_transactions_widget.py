"""
Pending Transactions Widget for Sapphire Exchange.
Displays and monitors pending and recent transactions across all blockchains.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QMessageBox, QProgressBar, QGroupBox, QScrollArea
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QUrl
from PyQt5.QtGui import QFont, QColor, QDesktopServices
import asyncio
from datetime import datetime

from services.transaction_tracker import get_transaction_tracker
from services.application_service import app_service
from utils.async_worker import AsyncWorker


class PendingTransactionsWidget(QWidget):
    """Widget displaying pending and recent transactions."""
    
    transaction_updated = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tracker = None
        self.user = None
        self.setMaximumHeight(300)
        self.setup_ui()
        self.setup_refresh_timer()
    
    def setup_ui(self):
        """Setup the UI."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Pending Transactions")
        title.setFont(QFont("Arial", 11, QFont.Bold))
        layout.addWidget(title)
        
        # Transaction table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Currency", "Type", "Amount", "Status", "Confirmations", "Actions"
        ])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        
        self.table.setMaximumHeight(200)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)
        
        # Status info
        self.info_label = QLabel("Loading transaction status...")
        self.info_label.setStyleSheet("color: #666; font-size: 9px;")
        layout.addWidget(self.info_label)
        
        layout.addStretch()
    
    def setup_refresh_timer(self):
        """Setup auto-refresh timer."""
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_transactions)
        self.refresh_timer.start(5000)
    
    def initialize(self):
        """Initialize the widget."""
        try:
            self.user = app_service.get_current_user()
            if self.user:
                worker = AsyncWorker(self._init_async())
                worker.finished.connect(self.refresh_transactions)
                worker.error.connect(self._on_init_error)
                worker.start()
                self._init_worker = worker
        except Exception as e:
            print(f"Error initializing pending transactions: {e}")
    
    def _on_init_error(self, error: str):
        """Handle initialization errors."""
        print(f"Error initializing transaction tracker: {error}")
        self.info_label.setText(f"Error loading transactions: {error[:50]}")
    
    async def _init_async(self):
        """Initialize tracker asynchronously."""
        try:
            self.tracker = await get_transaction_tracker()
            print(f"Transaction tracker initialized successfully")
        except RuntimeError as e:
            if "no running event loop" in str(e):
                print(f"Warning: Event loop not ready yet, will retry on next refresh")
                self.tracker = None
            else:
                print(f"Error getting transaction tracker: {e}")
                raise
        except Exception as e:
            print(f"Error getting transaction tracker: {e}")
            raise
    
    def refresh_transactions(self):
        """Refresh the transaction list."""
        try:
            if not self.tracker:
                if not self.user:
                    return
                # Try to re-initialize if tracker wasn't ready yet
                print("Tracker not ready, retrying initialization...")
                worker = AsyncWorker(self._init_async())
                worker.finished.connect(self.refresh_transactions)
                worker.error.connect(self._on_init_error)
                worker.start()
                self._init_worker = worker
                return
            
            if not self.user:
                return
            
            pending = self.tracker.get_pending_transactions(user_id=self.user.id)
            history = self.tracker.get_transaction_history(user_id=self.user.id, limit=50, days=30)
            failed = [tx for tx in history if tx.status == "failed"]
            
            latest_incoming = {}
            for tx in history:
                if tx.type != "receive":
                    continue
                try:
                    created_at = datetime.fromisoformat(tx.created_at)
                except Exception:
                    continue
                current = latest_incoming.get(tx.currency)
                if not current:
                    latest_incoming[tx.currency] = (created_at, tx)
                    continue
                if created_at > current[0]:
                    latest_incoming[tx.currency] = (created_at, tx)
            
            tx_lookup = {}
            for tx in pending + failed:
                tx_lookup[tx.id] = tx
            for entry in latest_incoming.values():
                tx_lookup[entry[1].id] = entry[1]
            
            display_txs = list(tx_lookup.values())
            
            def _tx_sort_key(tx):
                try:
                    return datetime.fromisoformat(tx.created_at)
                except Exception:
                    return datetime.min
            
            display_txs.sort(key=_tx_sort_key, reverse=True)
            
            # Clear table
            self.table.setRowCount(0)
            
            # Add rows
            for tx in display_txs:
                row = self.table.rowCount()
                self.table.insertRow(row)
                
                # Currency
                currency_item = QTableWidgetItem(tx.currency)
                currency_item.setFont(QFont("Arial", 9, QFont.Bold))
                self.table.setItem(row, 0, currency_item)
                
                # Type
                tx_type = "Send" if tx.type == "send" else "Receive" if tx.type == "receive" else tx.type
                type_item = QTableWidgetItem(tx_type)
                self.table.setItem(row, 1, type_item)
                
                # Amount
                amount_item = QTableWidgetItem(f"{tx.amount} {tx.currency}")
                self.table.setItem(row, 2, amount_item)
                
                # Status
                status_item = QTableWidgetItem(tx.status.upper())
                if tx.status == "pending":
                    status_item.setForeground(QColor("#ff9800"))
                elif tx.status == "confirmed":
                    status_item.setForeground(QColor("#4caf50"))
                    status_item.setText("✓ CONFIRMED")
                elif tx.status == "failed":
                    status_item.setForeground(QColor("#f44336"))
                    if tx.error_message:
                        status_item.setToolTip(tx.error_message)
                self.table.setItem(row, 3, status_item)
                
                # Confirmations
                conf_text = f"{tx.confirmations}/{self.tracker.confirmation_targets.get(tx.currency, 6)}"
                conf_item = QTableWidgetItem(conf_text)
                self.table.setItem(row, 4, conf_item)
                
                # Actions
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(0, 0, 0, 0)
                
                if tx.tx_hash:
                    view_btn = QPushButton("View")
                    view_btn.setMaximumWidth(50)
                    view_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #2196f3;
                            color: white;
                            border: none;
                            padding: 3px 6px;
                            border-radius: 2px;
                            font-size: 8px;
                        }
                        QPushButton:hover {
                            background-color: #1976d2;
                        }
                    """)
                    view_btn.clicked.connect(lambda checked, h=tx.tx_hash, c=tx.currency: self._open_explorer(h, c))
                    actions_layout.addWidget(view_btn)
                
                if tx.status == "failed":
                    max_retries = self.tracker.max_retries.get(tx.currency, 3)
                    retry_btn = QPushButton("Retry")
                    retry_btn.setMaximumWidth(50)
                    retry_btn.setEnabled(tx.retry_count < max_retries)
                    retry_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #ff9800;
                            color: white;
                            border: none;
                            padding: 3px 6px;
                            border-radius: 2px;
                            font-size: 8px;
                        }
                        QPushButton:hover {
                            background-color: #f57c00;
                        }
                    """)
                    retry_btn.clicked.connect(lambda checked, tx_id=tx.id: self._retry_transaction(tx_id))
                    actions_layout.addWidget(retry_btn)
                
                self.table.setCellWidget(row, 5, actions_widget)
            
            failed_count = len([tx for tx in display_txs if tx.status == "failed"])
            incoming_count = len(latest_incoming)
            pending_count = len([tx for tx in display_txs if tx.status == "pending"])
            
            if failed_count:
                self.info_label.setText(f"{failed_count} failed transaction(s) need attention")
                self.info_label.setStyleSheet("color: #d32f2f; font-size: 9px; font-weight: bold;")
            elif display_txs:
                self.info_label.setText(f"Pending: {pending_count} | Latest incoming: {incoming_count}")
                self.info_label.setStyleSheet("color: #666; font-size: 9px;")
            else:
                self.info_label.setText("No pending transactions")
                self.info_label.setStyleSheet("color: #666; font-size: 9px;")
        
        except Exception as e:
            self.info_label.setText(f"Error: {str(e)[:50]}")
    
    def _open_explorer(self, tx_hash: str, currency: str):
        """Open transaction in blockchain explorer."""
        urls = {
            "USDC": f"https://explorer.solana.com/tx/{tx_hash}",
            "ARWEAVE": f"https://viewblock.io/arweave/tx/{tx_hash}",
            "DOGE": f"https://blockchair.com/dogecoin/transaction/{tx_hash}",
            "NANO": f"https://nanolooker.com/block/{tx_hash}"
        }
        
        url = urls.get(currency, "")
        if url:
            QDesktopServices.openUrl(QUrl(url))
        else:
            QMessageBox.warning(self, "Error", f"Explorer not available for {currency}")
    
    def _retry_transaction(self, tx_id: str):
        """Retry a failed transaction."""
        try:
            worker = AsyncWorker(self._do_retry(tx_id))
            worker.finished.connect(lambda success: self._on_retry_complete(success))
            worker.error.connect(lambda e: QMessageBox.critical(self, "Error", f"Retry failed: {e}"))
            worker.start()
            self._retry_worker = worker
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error retrying transaction: {e}")
    
    def _on_retry_complete(self, success: bool):
        if success:
            QMessageBox.information(self, "Retry Started", "Transaction retry started and will be monitored.")
        else:
            QMessageBox.warning(self, "Retry Unavailable", "Transaction could not be retried.")
        self.refresh_transactions()
    
    async def _do_retry(self, tx_id: str):
        """Do retry operation."""
        if self.tracker:
            return await self.tracker.retry_transaction(tx_id)
        return False


class TransactionMonitorWidget(QWidget):
    """Enhanced widget showing transaction history with monitoring."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tracker = None
        self.user = None
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the UI."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Transaction History")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title)
        
        # Pending section
        pending_group = QGroupBox("Pending Transactions")
        pending_layout = QVBoxLayout(pending_group)
        
        self.pending_widget = PendingTransactionsWidget()
        pending_layout.addWidget(self.pending_widget)
        layout.addWidget(pending_group)
        
        # History section
        history_group = QGroupBox("Recent Transactions (Last 30 Days)")
        history_layout = QVBoxLayout(history_group)
        
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(7)
        self.history_table.setHorizontalHeaderLabels([
            "Date", "Currency", "Type", "Amount", "Status", "Confirmations", "Hash"
        ])
        
        header = self.history_table.horizontalHeader()
        for i in range(7):
            header.setSectionResizeMode(i, QHeaderView.Stretch)
        
        self.history_table.setMaximumHeight(250)
        history_layout.addWidget(self.history_table)
        
        layout.addWidget(history_group)
    
    def initialize(self):
        """Initialize the widget."""
        self.pending_widget.initialize()
        try:
            self.user = app_service.get_current_user()
            if self.user:
                worker = AsyncWorker(self._init_async())
                worker.finished.connect(self.refresh_history)
                worker.error.connect(self._on_init_error)
                worker.start()
                self._init_worker = worker
        except Exception as e:
            print(f"Error initializing transaction monitor: {e}")
    
    def _on_init_error(self, error: str):
        """Handle initialization errors."""
        print(f"Error initializing transaction monitor tracker: {error}")
    
    async def _init_async(self):
        """Initialize tracker asynchronously."""
        try:
            self.tracker = await get_transaction_tracker()
            print(f"Transaction monitor tracker initialized successfully")
        except RuntimeError as e:
            if "no running event loop" in str(e):
                print(f"Warning: Event loop not ready yet, will retry on next refresh")
                self.tracker = None
            else:
                print(f"Error getting transaction tracker: {e}")
                raise
        except Exception as e:
            print(f"Error getting transaction tracker: {e}")
            raise
    
    def refresh_history(self):
        """Refresh transaction history."""
        try:
            if not self.tracker or not self.user:
                return
            
            # Get transaction history
            history = self.tracker.get_transaction_history(user_id=self.user.id, limit=30)
            
            # Clear table
            self.history_table.setRowCount(0)
            
            # Add rows
            for tx in history:
                row = self.history_table.rowCount()
                self.history_table.insertRow(row)
                
                # Date
                try:
                    dt = datetime.fromisoformat(tx.created_at)
                    date_str = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    date_str = tx.created_at[:16]
                
                self.history_table.setItem(row, 0, QTableWidgetItem(date_str))
                self.history_table.setItem(row, 1, QTableWidgetItem(tx.currency))
                
                # Type
                tx_type = "Send" if tx.type == "send" else "Receive" if tx.type == "receive" else tx.type
                self.history_table.setItem(row, 2, QTableWidgetItem(tx_type))
                
                self.history_table.setItem(row, 3, QTableWidgetItem(f"{tx.amount} {tx.currency}"))
                
                # Status
                status_item = QTableWidgetItem(tx.status.upper())
                if tx.status == "pending":
                    status_item.setForeground(QColor("#ff9800"))
                elif tx.status == "confirmed":
                    status_item.setForeground(QColor("#4caf50"))
                elif tx.status == "failed":
                    status_item.setForeground(QColor("#f44336"))
                self.history_table.setItem(row, 4, status_item)
                
                # Confirmations
                conf_text = f"{tx.confirmations}/{self.tracker.confirmation_targets.get(tx.currency, 6)}"
                self.history_table.setItem(row, 5, QTableWidgetItem(conf_text))
                
                # Hash
                hash_text = tx.tx_hash[:16] + "..." if tx.tx_hash else "N/A"
                self.history_table.setItem(row, 6, QTableWidgetItem(hash_text))
        
        except Exception as e:
            print(f"Error refreshing history: {e}")
