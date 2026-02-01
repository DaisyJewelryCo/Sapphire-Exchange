"""
Wallet management dialogs for creating, importing, and selecting wallets.
"""
from typing import Optional, List
from dataclasses import dataclass
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTextEdit, QSpinBox, QCheckBox, QProgressBar, QTabWidget, QWidget,
    QFormLayout, QMessageBox, QFileDialog, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont


@dataclass
class WalletInfo:
    """Wallet information."""
    name: str
    mnemonic: str
    address_solana: Optional[str] = None
    address_nano: Optional[str] = None
    address_arweave: Optional[str] = None


class CreateWalletDialog(QDialog):
    """Dialog for creating a new wallet."""
    
    wallet_created = pyqtSignal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Wallet")
        self.setModal(True)
        self.setMinimumWidth(600)
        self.current_mnemonic = None
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the UI."""
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("My Wallet")
        form_layout.addRow("Wallet Name:", self.name_edit)
        
        self.word_count = QSpinBox()
        self.word_count.setMinimum(12)
        self.word_count.setMaximum(24)
        self.word_count.setSingleStep(12)
        self.word_count.setValue(12)
        form_layout.addRow("Words:", self.word_count)
        
        layout.addLayout(form_layout)
        
        self.mnemonic_display = QTextEdit()
        self.mnemonic_display.setReadOnly(True)
        self.mnemonic_display.setMinimumHeight(100)
        layout.addWidget(self.mnemonic_display)
        
        self.progress = QProgressBar()
        layout.addWidget(self.progress)
        
        button_layout = QHBoxLayout()
        
        create_btn = QPushButton("Generate")
        create_btn.clicked.connect(self.generate)
        button_layout.addWidget(create_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def generate(self):
        """Generate wallet."""
        try:
            from mnemonic import Mnemonic
            mnemo = Mnemonic("english")
            words = self.word_count.value()
            mnemonic = mnemo.generate(strength=128 if words == 12 else 256)
            
            self.current_mnemonic = mnemonic
            self.mnemonic_display.setText(mnemonic)
            self.progress.setValue(100)
            
            name = self.name_edit.text() or "My Wallet"
            wallet_info = WalletInfo(
                name=name,
                mnemonic=mnemonic
            )
            self.wallet_created.emit(wallet_info)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


class ImportWalletDialog(QDialog):
    """Dialog for importing a wallet."""
    
    wallet_imported = pyqtSignal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import Wallet")
        self.setModal(True)
        self.setMinimumWidth(600)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the UI."""
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Imported Wallet")
        form_layout.addRow("Name:", self.name_edit)
        
        self.mnemonic_edit = QTextEdit()
        self.mnemonic_edit.setMinimumHeight(80)
        form_layout.addRow("Mnemonic:", self.mnemonic_edit)
        
        layout.addLayout(form_layout)
        
        button_layout = QHBoxLayout()
        import_btn = QPushButton("Import")
        import_btn.clicked.connect(self.import_wallet)
        button_layout.addWidget(import_btn)
        
        close_btn = QPushButton("Cancel")
        close_btn.clicked.connect(self.reject)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def import_wallet(self):
        """Import wallet from mnemonic."""
        try:
            from mnemonic import Mnemonic
            mnemo = Mnemonic("english")
            mnemonic = self.mnemonic_edit.toPlainText().strip()
            
            if not mnemo.check(mnemonic):
                QMessageBox.critical(self, "Error", "Invalid mnemonic phrase")
                return
            
            name = self.name_edit.text() or "Imported Wallet"
            wallet_info = WalletInfo(
                name=name,
                mnemonic=mnemonic
            )
            self.wallet_imported.emit(wallet_info)
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
