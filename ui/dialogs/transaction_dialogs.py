"""
Transaction dialogs for sending and receiving.
Integrates with Plan 3 (Transaction Signing & Broadcasting).
"""
from typing import Optional, Dict, Any
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QMessageBox, QFormLayout,
    QGroupBox, QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
import qrcode
from io import BytesIO
from PyQt5.QtGui import QPixmap


class SendTransactionDialog(QDialog):
    """Dialog for sending transactions."""
    
    transaction_sent = pyqtSignal(dict)
    
    def __init__(self, currency: str = "Solana", current_balance: str = "0", parent=None):
        super().__init__(parent)
        self.currency = currency
        self.current_balance = current_balance
        self.setWindowTitle(f"Send {currency}")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the UI."""
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        self.recipient_edit = QLineEdit()
        self.recipient_edit.setPlaceholderText(f"Enter {self.currency} address")
        form_layout.addRow("Recipient:", self.recipient_edit)
        
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setMinimum(0)
        self.amount_spin.setMaximum(9999999)
        self.amount_spin.setDecimals(8)
        form_layout.addRow("Amount:", self.amount_spin)
        
        if self.currency.upper() in ["DOGE", "BTC"]:
            self.fee_spin = QDoubleSpinBox()
            self.fee_spin.setMinimum(0.0001)
            self.fee_spin.setValue(1.0)
            form_layout.addRow("Fee:", self.fee_spin)
        
        self.memo_edit = QLineEdit()
        self.memo_edit.setPlaceholderText("Optional memo")
        form_layout.addRow("Memo:", self.memo_edit)
        
        layout.addLayout(form_layout)
        
        info_label = QLabel(f"Available: {self.current_balance} {self.currency}")
        info_label.setStyleSheet("color: #666;")
        layout.addWidget(info_label)
        
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        button_layout = QHBoxLayout()
        
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self.send)
        button_layout.addWidget(self.send_btn)
        
        close_btn = QPushButton("Cancel")
        close_btn.clicked.connect(self.reject)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def send(self):
        """Send transaction."""
        recipient = self.recipient_edit.text().strip()
        amount = self.amount_spin.value()
        
        if not recipient or amount <= 0:
            QMessageBox.warning(self, "Invalid Input", "Please enter recipient and amount")
            return
        
        reply = QMessageBox.question(
            self,
            "Confirm Transaction",
            f"Send {amount} {self.currency} to:\n{recipient}?\n\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.progress.setVisible(True)
            
            transaction_data = {
                "recipient": recipient,
                "amount": amount,
                "currency": self.currency,
                "memo": self.memo_edit.text(),
            }
            
            if hasattr(self, 'fee_spin'):
                transaction_data["fee"] = self.fee_spin.value()
            
            self.transaction_sent.emit(transaction_data)
            self.progress.setValue(100)
            
            QMessageBox.information(
                self,
                "Transaction Sent",
                f"Sent {amount} {self.currency} successfully"
            )
            self.accept()


class ReceiveDialog(QDialog):
    """Dialog for receiving transactions."""
    
    def __init__(self, currency: str = "Solana", address: str = "", parent=None):
        super().__init__(parent)
        self.currency = currency
        self.address = address
        self.setWindowTitle(f"Receive {currency}")
        self.setModal(True)
        self.setMinimumSize(400, 500)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the UI."""
        layout = QVBoxLayout(self)
        
        title = QLabel(f"Receive {self.currency}")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(title)
        
        if self.address:
            try:
                qr = qrcode.QRCode(version=1, box_size=10, border=4)
                qr.add_data(self.address)
                qr.make(fit=True)
                
                qr_img = qr.make_image(fill_color="black", back_color="white")
                buffer = BytesIO()
                qr_img.save(buffer, format='PNG')
                buffer.seek(0)
                
                pixmap = QPixmap()
                pixmap.loadFromData(buffer.getvalue())
                
                qr_label = QLabel()
                qr_label.setPixmap(pixmap.scaled(200, 200, Qt.KeepAspectRatio))
                qr_label.setAlignment(Qt.AlignCenter)
                layout.addWidget(qr_label)
            except Exception as e:
                layout.addWidget(QLabel(f"QR Code Error: {str(e)}"))
        
        address_group = QGroupBox("Your Address")
        address_layout = QVBoxLayout(address_group)
        
        address_text = QTextEdit()
        address_text.setPlainText(self.address)
        address_text.setReadOnly(True)
        address_text.setMaximumHeight(80)
        address_layout.addWidget(address_text)
        
        copy_btn = QPushButton("Copy Address")
        copy_btn.clicked.connect(self.copy_address)
        address_layout.addWidget(copy_btn)
        
        layout.addWidget(address_group)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
    
    def copy_address(self):
        """Copy address to clipboard."""
        from PyQt5.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(self.address)
        QMessageBox.information(self, "Copied", "Address copied to clipboard")


class TransactionHistoryDialog(QDialog):
    """Dialog for viewing transaction history."""
    
    def __init__(self, transactions: list = None, parent=None):
        super().__init__(parent)
        self.transactions = transactions or []
        self.setWindowTitle("Transaction History")
        self.setModal(True)
        self.setMinimumSize(700, 500)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the UI."""
        layout = QVBoxLayout(self)
        
        title = QLabel("Recent Transactions")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title)
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Date", "Type", "Amount", "Address", "Status"
        ])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        
        for i, tx in enumerate(self.transactions):
            self.table.insertRow(i)
            self.table.setItem(i, 0, QTableWidgetItem(tx.get('date', '')))
            self.table.setItem(i, 1, QTableWidgetItem(tx.get('type', '')))
            self.table.setItem(i, 2, QTableWidgetItem(str(tx.get('amount', ''))))
            self.table.setItem(i, 3, QTableWidgetItem(tx.get('address', '')[:20] + '...'))
            self.table.setItem(i, 4, QTableWidgetItem(tx.get('status', '')))
        
        layout.addWidget(self.table)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
