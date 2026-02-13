#!/usr/bin/env python3
"""
Test wallet tile clicking and dialog opening.
Run this to test if clicking on wallet tiles opens the details dialog.
"""
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from ui.dialogs.wallet_management import WalletInfo
from ui.custom_widgets import WalletTileWidget

def test_wallet_tile_click():
    """Test clicking on a wallet tile."""
    app = QApplication(sys.argv)
    
    window = QMainWindow()
    window.setWindowTitle("Wallet Tile Click Test")
    window.setGeometry(100, 100, 600, 400)
    
    central = QWidget()
    layout = QVBoxLayout(central)
    window.setCentralWidget(central)
    
    title = QLabel("Click on the wallet tile below:")
    title.setFont(QFont("Arial", 14, QFont.Bold))
    layout.addWidget(title)
    
    instructions = QLabel(
        "If you see a wallet tile below and can click it, the tile is working.\n"
        "You should see debug output in the console when clicking."
    )
    layout.addWidget(instructions)
    
    tile = WalletTileWidget({
        'name': 'Test Wallet',
        'balance': '$1000.00',
        'status': 'Connected'
    })
    
    def on_tile_clicked(wallet_info):
        print(f"\n✓ SUCCESS: Tile clicked!")
        print(f"  Wallet Info: {wallet_info}")
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.information(
            window,
            "Tile Clicked",
            f"Wallet '{wallet_info.get('name')}' was clicked!\n\nThe signal is working properly."
        )
    
    tile.clicked.connect(on_tile_clicked)
    layout.addWidget(tile)
    
    layout.addStretch()
    
    window.show()
    
    print("=" * 60)
    print("WALLET TILE CLICK TEST")
    print("=" * 60)
    print("✓ Window and tile created")
    print("✓ Signal connected")
    print("\nNow click on the wallet tile...")
    print("You should see:")
    print("  1. Console output: '✓ SUCCESS: Tile clicked!'")
    print("  2. A message box appearing")
    print("=" * 60)
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    test_wallet_tile_click()
