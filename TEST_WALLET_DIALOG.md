# Testing Wallet Details Dialog

## Quick Test - Dialog Only

Run this simple test to verify the dialog opens:

```bash
source venv/bin/activate
python3 test_simple_dialog.py
```

Click the "Open Wallet Details Dialog" button. A modal dialog should appear showing:
- Wallet name at the top
- Wallet addresses (Solana, Nano, Arweave) with copy buttons
- Balance widgets
- Action buttons (Send, Receive, Backup, Recover, Remove Wallet)
- Close button

## Full Integration Test - With Wallet Widget

Run this test to verify the entire flow:

```bash
source venv/bin/activate
python3 test_wallet_details.py
```

1. The window should show the EnhancedWalletWidget
2. Go to the **Dashboard tab** (first tab)
3. You should see a "Wallet Manager" section with 2 wallet tiles:
   - "Test Wallet 1"
   - "Test Wallet 2"
4. **Click on any wallet tile**
5. A "Wallet Details" dialog should pop up showing that wallet's information

## Debug Output

When you click on a wallet, check the console for debug messages like:

```
DEBUG: update_dashboard_wallets() called with 2 wallets
DEBUG: Creating tile for wallet: Test Wallet 1
DEBUG: Connected signal for Test Wallet 1
DEBUG: Added tile at row 0, col 0
DEBUG: Creating tile for wallet: Test Wallet 2
DEBUG: Connected signal for Test Wallet 2
DEBUG: Added tile at row 0, col 1
DEBUG: Wallet tile clicked with info: {'name': 'Test Wallet 1', 'balance': '$0.00', 'status': 'Ready'}
DEBUG: Looking for wallet: Test Wallet 1
DEBUG: Available wallets: ['Test Wallet 1', 'Test Wallet 2']
DEBUG: Found wallet, opening dialog
DEBUG: Executing dialog
```

If you don't see these messages when clicking, the signal is not being triggered.

## Possible Issues

1. **Dialog doesn't appear but no error**: The dialog might be opening behind the main window
2. **Click not registering**: The wallet tile might not be properly receiving mouse events
3. **No debug output**: The signal might not be connected

## What to Look For

- The wallet tiles should be visible in the Dashboard tab under "Wallet Manager"
- Tiles should have a border and be clickable (cursor changes to pointing hand)
- Tiles should show wallet name, balance, and status
- Clicking should open a modal dialog

If tiles are not visible, check that:
- The Dashboard tab is showing
- The wallet tiles are being added to the grid (debug output should show "Added tile")
- The scroll area has enough height to show the tiles
