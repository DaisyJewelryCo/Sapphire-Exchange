#!/usr/bin/env python3
"""
Simple test to verify the dialog opens.
"""
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton
from ui.dialogs.wallet_management import WalletInfo
from ui.dialogs.wallet_details_dialog import WalletDetailsDialog

def open_dialog():
    wallet = WalletInfo(
        name="Test Wallet",
        mnemonic="abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about",
        address_solana="So1dDKkGkDmWpA8gUqLa8e7i9xdA3b4c5e6f7g8h9i",
        address_nano="nano_1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a",
        address_arweave="arweave_test_address_1a2b3c4d5e6f"
    )
    
    dialog = WalletDetailsDialog(wallet)
    print("Opening dialog...")
    result = dialog.exec_()
    print(f"Dialog closed with result: {result}")

app = QApplication(sys.argv)

window = QWidget()
layout = QVBoxLayout(window)

btn = QPushButton("Open Wallet Details Dialog")
btn.clicked.connect(open_dialog)
layout.addWidget(btn)

window.setWindowTitle("Test Dialog")
window.show()

sys.exit(app.exec_())
