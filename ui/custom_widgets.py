"""
Custom widgets for wallet UI.
Includes address display, balance widgets, QR code display, and transaction lists.
"""
from typing import Optional, List, Dict, Any
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit,
    QScrollArea, QFrame, QHeaderView, QTableWidget, QTableWidgetItem,
    QMessageBox, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap, QColor, QClipboard
import qrcode
from io import BytesIO


class AddressDisplayWidget(QWidget):
    """Widget for displaying wallet addresses safely."""
    
    address_copied = pyqtSignal(str)
    
    def __init__(self, address: str = "", label: str = "Address", parent=None):
        super().__init__(parent)
        self.address = address
        self.label = label
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the UI."""
        layout = QVBoxLayout(self)
        
        label_widget = QLabel(self.label)
        label_widget.setFont(QFont("Arial", 9, QFont.Bold))
        layout.addWidget(label_widget)
        
        content_layout = QHBoxLayout()
        
        self.address_text = QTextEdit()
        self.address_text.setPlainText(self.address)
        self.address_text.setReadOnly(True)
        self.address_text.setMaximumHeight(60)
        self.address_text.setFont(QFont("Courier", 9))
        content_layout.addWidget(self.address_text)
        
        copy_btn = QPushButton("Copy")
        copy_btn.setMaximumWidth(60)
        copy_btn.clicked.connect(self.copy_address)
        content_layout.addWidget(copy_btn)
        
        layout.addLayout(content_layout)
    
    def set_address(self, address: str):
        """Set address."""
        self.address = address
        self.address_text.setPlainText(address)
    
    def copy_address(self):
        """Copy address to clipboard."""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.address)
        self.address_copied.emit(self.address)
        QMessageBox.information(self, "Copied", "Address copied to clipboard")


class BalanceWidget(QWidget):
    """Widget for displaying balance information."""
    
    def __init__(self, currency: str = "SOL", balance: str = "0", usd_value: str = "$0.00", parent=None):
        super().__init__(parent)
        self.currency = currency
        self.balance = balance
        self.usd_value = usd_value
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        
        header_layout = QHBoxLayout()
        
        currency_label = QLabel(self.currency)
        currency_label.setFont(QFont("Arial", 14, QFont.Bold))
        header_layout.addWidget(currency_label)
        
        header_layout.addStretch()
        
        balance_label = QLabel(self.balance)
        balance_label.setFont(QFont("Arial", 12, QFont.Bold))
        header_layout.addWidget(balance_label)
        
        layout.addLayout(header_layout)
        
        usd_label = QLabel(self.usd_value)
        usd_label.setFont(QFont("Arial", 10))
        usd_label.setStyleSheet("color: #666;")
        layout.addWidget(usd_label)
        
        self.setStyleSheet("""
            QWidget {
                background: #f5f5f5;
                border-radius: 8px;
                padding: 10px;
                margin: 5px;
            }
        """)
    
    def update_balance(self, balance: str, usd_value: str = ""):
        """Update balance display."""
        self.balance = balance
        self.balance_label.setText(balance)
        
        if usd_value:
            self.usd_value = usd_value
            self.usd_label.setText(usd_value)


class QRCodeWidget(QWidget):
    """Widget for displaying QR codes."""
    
    def __init__(self, data: str = "", size: int = 200, parent=None):
        super().__init__(parent)
        self.data = data
        self.size = size
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the UI."""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        self.qr_label = QLabel()
        self.qr_label.setAlignment(Qt.AlignCenter)
        
        if self.data:
            self.generate_qr()
        
        layout.addWidget(self.qr_label)
    
    def generate_qr(self):
        """Generate QR code."""
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(self.data)
            qr.make(fit=True)
            
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            buffer = BytesIO()
            qr_img.save(buffer, format='PNG')
            buffer.seek(0)
            
            pixmap = QPixmap()
            pixmap.loadFromData(buffer.getvalue())
            self.qr_label.setPixmap(pixmap.scaled(self.size, self.size, Qt.KeepAspectRatio))
        
        except Exception as e:
            self.qr_label.setText(f"QR Error: {str(e)}")
    
    def set_data(self, data: str):
        """Set QR code data."""
        self.data = data
        self.generate_qr()


class TransactionListWidget(QWidget):
    """Widget for displaying transaction list."""
    
    transaction_selected = pyqtSignal(dict)
    
    def __init__(self, transactions: List[Dict] = None, parent=None):
        super().__init__(parent)
        self.transactions = transactions or []
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the UI."""
        layout = QVBoxLayout(self)
        
        title = QLabel("Recent Transactions")
        title.setFont(QFont("Arial", 11, QFont.Bold))
        layout.addWidget(title)
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Date", "Type", "Amount", "Address", "Status"
        ])
        
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(self.table.SelectRows)
        self.table.itemSelectionChanged.connect(self.on_transaction_selected)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        
        self.populate_transactions()
        
        layout.addWidget(self.table)
    
    def populate_transactions(self):
        """Populate transaction table."""
        self.table.setRowCount(len(self.transactions))
        
        for i, tx in enumerate(self.transactions):
            self.table.setItem(i, 0, QTableWidgetItem(tx.get('date', '')))
            self.table.setItem(i, 1, QTableWidgetItem(tx.get('type', '')))
            self.table.setItem(i, 2, QTableWidgetItem(str(tx.get('amount', ''))))
            
            address = tx.get('address', '')[:20]
            self.table.setItem(i, 3, QTableWidgetItem(address + ('...' if len(tx.get('address', '')) > 20 else '')))
            
            status_item = QTableWidgetItem(tx.get('status', ''))
            status = tx.get('status', '')
            if status.lower() == 'confirmed':
                status_item.setForeground(QColor("#06A77D"))
            elif status.lower() == 'pending':
                status_item.setForeground(QColor("#F18F01"))
            elif status.lower() == 'failed':
                status_item.setForeground(QColor("#C1121F"))
            
            self.table.setItem(i, 4, status_item)
    
    def set_transactions(self, transactions: List[Dict]):
        """Set transactions."""
        self.transactions = transactions
        self.populate_transactions()
    
    def on_transaction_selected(self):
        """Handle transaction selection."""
        selected_rows = self.table.selectionModel().selectedRows()
        
        if selected_rows:
            row = selected_rows[0].row()
            if row < len(self.transactions):
                self.transaction_selected.emit(self.transactions[row])


class WalletTileWidget(QFrame):
    """Widget for displaying wallet as a clickable tile."""
    
    clicked = pyqtSignal(dict)
    
    def __init__(self, wallet_info: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.wallet_info = wallet_info
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setLineWidth(2)
        self.setCursor(Qt.PointingHandCursor)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        name = QLabel(self.wallet_info.get('name', 'Unnamed Wallet'))
        name.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(name)
        
        balance = QLabel(f"Balance: {self.wallet_info.get('balance', '$0.00')}")
        balance.setFont(QFont("Arial", 10))
        layout.addWidget(balance)
        
        status = QLabel(f"Status: {self.wallet_info.get('status', 'Unknown')}")
        status.setFont(QFont("Arial", 9))
        status.setStyleSheet("color: #666;")
        layout.addWidget(status)
        
        self.setStyleSheet("""
            QFrame {
                background: white;
                border: 2px solid #ddd;
                border-radius: 8px;
                padding: 10px;
            }
            QFrame:hover {
                border: 2px solid #2E86AB;
                background: #f9f9f9;
            }
        """)
        
        self.setMinimumHeight(100)
    
    def mousePressEvent(self, event):
        """Handle mouse press."""
        self.clicked.emit(self.wallet_info)
        super().mousePressEvent(event)


class StatusIndicatorWidget(QWidget):
    """Widget showing blockchain connection status."""
    
    def __init__(self, statuses: Dict[str, str] = None, parent=None):
        super().__init__(parent)
        self.statuses = statuses or {}
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        for blockchain, status in self.statuses.items():
            status_layout = QHBoxLayout()
            
            indicator = QLabel("●")
            color = "#06A77D" if status.lower() == "connected" else "#C1121F"
            indicator.setStyleSheet(f"color: {color}; font-size: 16px;")
            status_layout.addWidget(indicator)
            
            label = QLabel(f"{blockchain}: {status}")
            label.setFont(QFont("Arial", 9))
            status_layout.addWidget(label)
            
            layout.addLayout(status_layout)
        
        layout.addStretch()
    
    def update_status(self, blockchain: str, status: str):
        """Update blockchain status."""
        self.statuses[blockchain] = status
