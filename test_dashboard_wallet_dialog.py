#!/usr/bin/env python3
"""
Test wallet details dialog in DashboardWidget.
This tests clicking on a wallet button in the dashboard.
"""
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from ui.dashboard_widget import WalletOverviewWidget

def main():
    app = QApplication(sys.argv)
    
    window = QMainWindow()
    window.setWindowTitle("Dashboard Wallet Dialog Test")
    window.setGeometry(100, 100, 800, 600)
    
    # Create wallet overview widget
    wallet_widget = WalletOverviewWidget()
    window.setCentralWidget(wallet_widget)
    
    print("=" * 60)
    print("DASHBOARD WALLET DETAILS DIALOG TEST")
    print("=" * 60)
    print("✓ Window created with WalletOverviewWidget")
    print("\nInstructions:")
    print("1. You should see 'Your Wallets' section with 3 buttons:")
    print("   - NANO")
    print("   - USDC")
    print("   - ARWEAVE")
    print("\n2. Click on any wallet button")
    print("\n3. A 'Wallet Details' dialog should pop up showing:")
    print("   - Wallet name")
    print("   - Addresses for each blockchain")
    print("   - Balance widgets")
    print("   - Action buttons (Send, Receive, Backup, Recover, Remove)")
    print("\n4. Close the dialog and it should show transaction history below")
    print("=" * 60)
    
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
