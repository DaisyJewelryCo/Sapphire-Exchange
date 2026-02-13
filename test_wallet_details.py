"""
Quick test to verify WalletDetailsDialog opens when clicking wallet tiles.
"""
import sys
from PyQt5.QtWidgets import QApplication
from ui.dialogs.wallet_management import WalletInfo
from ui.enhanced_wallet_widget import EnhancedWalletWidget

def main():
    app = QApplication(sys.argv)
    
    widget = EnhancedWalletWidget()
    
    wallet1 = WalletInfo(
        name="Test Wallet 1",
        mnemonic="abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about",
        address_solana="So1dDKkGkDmWpA8gUqLa8e7i9xdA3b4c5e6f7g8h9i",
        address_nano="nano_1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a",
        address_arweave="arweave_test_address_1a2b3c4d5e6f"
    )
    
    wallet2 = WalletInfo(
        name="Test Wallet 2",
        mnemonic="legal winner thank year wave sausage worth useful legal winner thank yellow",
        address_solana="So2dDKkGkDmWpA8gUqLa8e7i9xdA3b4c5e6f7g8h9j",
        address_nano="nano_2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b",
        address_arweave="arweave_test_address_2b3c4d5e6f7g"
    )
    
    widget.wallets = [wallet1, wallet2]
    widget.current_wallet = wallet1
    widget.update_wallet_tiles()
    widget.update_dashboard_wallets()
    
    print(f"✓ Wallets added: {[w.name for w in widget.wallets]}")
    print(f"✓ Dashboard wallet count: {widget.dashboard_wallets_grid.count()}")
    print(f"✓ Wallets tab count: {widget.wallets_grid.count()}")
    print("\nNow click on a wallet tile in the Dashboard tab to test the dialog...")
    print("The WalletDetailsDialog should open with wallet information and action buttons.")
    
    widget.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
