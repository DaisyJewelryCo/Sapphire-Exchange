# Funding Wizard - Complete Guide

## Overview

The **Funding Wizard** is a comprehensive, multi-step setup wizard in Sapphire Exchange that guides users through the complete process of funding their wallet across multiple blockchain networks. It provides a user-friendly interface for acquiring the three main cryptocurrencies needed for platform operations: **USDC** (Solana), **Arweave (AR)**, and **Nano (NANO)**.

### Location
- **UI Component**: `ui/funding_manager_widget.py`
- **Service Layer**: `services/funding_manager_service.py`
- **Transaction Tracking**: `services/transaction_tracker.py`

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│         Funding Wizard Dialog (FundingWizardDialog)    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  Step 1     │  │  Step 2      │  │  Step 3      │   │
│  │  Fund SOL   │  │  Swap SOL->  │  │  Purchase    │   │
│  │             │  │  USDC        │  │  Arweave     │   │
│  └─────────────┘  └──────────────┘  └──────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │            Step 4: Access Nano                   │   │
│  │  • Request via Cloudflare Worker                 │   │
│  │  • Alternative: Use Nano Faucets                 │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │     Pending Transactions Display (All Steps)     │   │
│  │  Shows real-time blockchain confirmations        │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
└─────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────┐
│          Services Layer                                 │
├─────────────────────────────────────────────────────────┤
│  • FundingManagerService (Config, Validation, Logging) │
│  • NanoCloudflareService (Nano requests with retries)  │
│  • SOL/USDC Swap Service (Jupiter DEX integration)     │
│  • TransactionTracker (Real-time blockchain monitoring)│
│  • ApplicationService (User & wallet management)       │
└─────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────┐
│          External Services & Blockchain                │
├─────────────────────────────────────────────────────────┤
│  • Solana RPC (Network: mainnet-beta)                   │
│  • Jupiter DEX (SOL/USDC swaps)                         │
│  • Cloudflare Worker (Nano distribution)               │
│  • Arweave Network (Data storage & tokens)             │
│  • Nano RPC (Nano transactions)                         │
└─────────────────────────────────────────────────────────┘
```

---

## The 4-Step Wizard Process

### Step 1: Fund Your Solana Wallet with SOL

**Purpose**: Users acquire SOL tokens to bootstrap their wallet.

**Location**: `_show_step_1_sol()` method

**What Users See**:
- Title: "Step 1: Fund Your Solana Wallet with SOL"
- Detailed information about funding options
- Three funding methods with step-by-step instructions
- QR code of their Solana address
- Copy address button
- Progress indicator showing "Step 1 of 4"

**Three Funding Methods Explained**:

1. **Centralized Exchange (Recommended)**
   - Transfer SOL from Coinbase, Kraken, FTX, or other exchanges
   - Steps provided:
     - Create account on supported exchange
     - Complete KYC verification
     - Purchase or deposit SOL
     - Withdraw SOL to your Solana wallet address
     - Arrival time: 5-30 minutes

2. **On-Ramp Services**
   - Direct bank transfer to SOL using services like Moonpay, Ramp, or Wyre
   - Steps:
     - Connect your bank account
     - Deposit funds directly to SOL
     - Funds appear instantly

3. **Swap from Existing Crypto**
   - For users who already own cryptocurrency
   - Steps:
     - Visit Jupiter or Raydium DEX
     - Swap existing tokens for SOL
     - Received instantly

**Technical Details**:

```python
def _show_step_1_sol(self):
    # Displays the SOL funding step
    # Features:
    # - Title and instructions
    # - Three funding method groups with detailed steps
    # - User's Solana address with QR code
    # - Copy address button
    # - Copy-to-clipboard functionality
```

**Solana Address Display**:
- Retrieved from `app_service.get_current_user()` 
- Attempts to get address from multiple user attributes:
  - `usdc_address` (primary - Solana wallet address for USDC)
  - `solana_pubkey` (fallback)
  - `solana_address` (fallback)
  - `solana_wallet` (fallback)
- Generates QR code using `qrcode` library
- User can scan or copy the address

**Pending Transactions Display**:
- Shows any pending USDC transactions at bottom of step
- Displays up to 3 transactions with color-coded status
- Updates as confirmations progress

---

### Step 2: Swap SOL to USDC

**Purpose**: Convert SOL tokens to USDC (Solana's USDC stablecoin) using Jupiter DEX.

**Location**: `_show_step_2_swap_sol_to_usdc()` method

**What Users See**:
- Title: "Step 2: Swap SOL to USDC"
- Explanation of why USDC is needed for Arweave purchases
- Instructions to launch swap dialog
- Button to execute swap
- Progress indicator showing "Step 2 of 4"

**Key Details**:
- **Swap Ratio**: 90% of available SOL is swapped to USDC
- **Remaining**: 10% of SOL stays in wallet for transaction fees
- **Service**: Jupiter DEX API for best pricing
- **Slippage**: 0.5% (protects against price movement during swap)

**SolUsdcSwapDialog**:

A specialized dialog (`SolUsdcSwapDialog`) handles the swap process:

```python
class SolUsdcSwapDialog(QDialog):
    # Swap dialog with:
    # - Service initialization (asynchronous)
    # - Balance fetching from user wallet
    # - Quote generation from Jupiter API
    # - Estimated USDC output calculation
    # - Swap execution button
    # - Real-time status updates
```

**Swap Process Flow**:
1. Dialog initializes `SOLUSDCSwapService`
2. Fetches user's SOL balance
3. Calculates 90% of balance to swap
4. Gets quote from Jupiter API for amount
5. Displays estimated USDC output
6. User clicks "Execute Swap"
7. Swap transaction created and signed
8. Transaction broadcast to Solana network
9. Success confirmation with transaction ID

**Configuration** (from `FundingConfig`):
```python
solana_rpc_url: str = "https://api.mainnet-beta.solana.com"
jupiter_quote_api: str = "https://quote-api.jup.ag/v6/quote"
jupiter_swap_api: str = "https://quote-api.jup.ag/v6/swap"
usdc_min_amount: float = 1.0
usdc_max_amount: float = 1000.0
```

**Pending Transactions Display**:
- Shows any pending USDC transactions at bottom of step
- Indicates if swap is still processing
- Shows confirmation progress

---

### Step 3: Purchase Arweave

**Purpose**: Users acquire Arweave tokens (AR) needed for permanent data storage.

**Location**: `_show_step_3_arweave()` method

**What Users See**:
- Title: "Step 3: Purchase Arweave"
- Explanation of what Arweave is and why it's needed
- Information about current AR prices and purchase limits
- Launch button to open Arweave purchase dialog
- Progress indicator showing "Step 3 of 4"

**About Arweave**:
- **Purpose**: Permanent data storage for auction records, metadata, and transaction history
- **Why Needed**: Sapphire Exchange stores all critical auction data on Arweave permanently
- **Token**: AR is Arweave's native cryptocurrency
- **Purchase Process**: Uses USDC to purchase AR tokens

**Purchase Configuration** (from `FundingConfig`):
```python
ar_min_amount: float = 0.001      # Minimum AR to purchase
ar_max_amount: float = 100.0      # Maximum AR per transaction
```

**Arweave Purchase Dialog**:
- Imported from `ui.wallet_widget.ArweavePurchaseDialog`
- Handles:
  - AR price fetching
  - Purchase amount input with validation
  - USDC balance verification
  - Transaction creation and signing
  - Blockchain broadcast

**Integration Details**:
```python
def launch_arweave_purchase(self):
    """Launch the Arweave purchase dialog."""
    from ui.wallet_widget import ArweavePurchaseDialog
    
    dialog = ArweavePurchaseDialog(self)
    dialog.exec_()
```

**Pending Transactions Display**:
- Shows any pending Arweave transactions at bottom of step
- Displays confirmation progress toward finalization
- Shows transaction amounts and hashes

---

### Step 4: Access Nano Funds

**Purpose**: Acquire Nano tokens (NANO) for feeless, instant transactions.

**Location**: `_show_step_4_nano()` method

**What Users See**:
- Title: "Step 4: Access Nano Funds"
- Explanation of Nano and its benefits
- User's Nano address with QR code
- Button to request Nano via Cloudflare Worker
- Alternative faucet options
- Completion summary
- Progress indicator showing "Step 4 of 4"
- "Complete" button to finish wizard

**About Nano**:
- **Zero Fees**: Every transaction is completely free
- **Instant**: Transactions confirm within seconds
- **Use Cases**: P2P payments, trading, fast settlements
- **Acquisition**: Via Cloudflare Worker (if configured) or manual faucets

**Nano Address Display**:
- Retrieved from `user.nano_address`
- Generates QR code (1x1 scale, 200px size)
- Provides copy button for address
- Displays warning if Nano address not configured

**Nano Acquisition Methods**:

**1. Cloudflare Worker (Recommended)**
- Single button click: "🔗 Request Nano"
- Instant distribution (if configured)
- Automatic retry logic (3 attempts)
- Configuration required:
  - Cloudflare worker URL
  - API key
  - Rate limiting per request: 0.001 - 1.0 NANO

**2. Alternative Faucets**
If Cloudflare Worker is unavailable, users can access:
- **Nano Official Faucet**: https://faucet.nano.org/
- **mynano.ninja**: https://mynano.ninja/ (community node with faucet)
- **NanoQuakz Faucet**: https://nanoquakz.com/
- **Nano Community**: https://nano.org/

**RequestNanoDialog**:

A specialized dialog handles Nano requests with comprehensive validation:

```python
class RequestNanoDialog(QDialog):
    def __init__(self, nano_address: str, parent=None):
        # Dialog features:
        # - Amount input field (default 0.001 NANO)
        # - Address display (read-only)
        # - Validation before request
        # - Async request execution
        # - Retry handling
        # - Transaction logging
```

**Request Nano Flow**:

1. User enters amount (0.001 - 1.0 NANO)
2. Dialog validates:
   - Amount is numeric
   - Amount is within min/max limits
   - Nano address is valid format
   - Configuration is complete
3. Request sent to Cloudflare Worker with:
   ```json
   {
     "to": "nano_3destinationaddress...",
     "amount_raw": "1000000000000000000000",
     "api_key": "your-api-key"
   }
   ```
4. Cloudflare Worker processes:
   - Validates request
   - Checks rate limits
   - Fetches sender account info
   - Creates state block
   - Signs block with private key
   - Broadcasts to Nano network
5. Response returns:
   ```json
   {
     "success": true,
     "hash": "ABC123...",
     "retry_count": 0
   }
   ```
6. Success message shows transaction hash
7. Transaction logged with timestamp and details

**Validation Details**:

```python
def request_nano(self):
    # Amount validation:
    # - Not empty
    # - Valid decimal
    # - Positive value
    # - Within 30 decimal places
    
    # Configuration validation:
    # - Cloudflare worker enabled
    # - All required config present
    
    # Address validation:
    # - Starts with "nano_"
    # - Correct format
    
    # Amount limits validation:
    # - Min: 0.001 NANO
    # - Max: 1.0 NANO
```

**Nano Amount Conversion**:
```python
# User enters decimal: 0.001
# Converted to raw amount: 1000000000000000000000
# Formula: amount_decimal * 10^30 = raw_amount
```

**Pending Transactions Display**:
- Shows any pending Nano transactions at bottom of step
- Displays confirmation progress
- Auto-updates as blockchain confirms blocks

**Completion Summary**:
After Nano step, users see:
```
✓ Complete Wallet Setup!

You now have:
  • USDC funded in Solana wallet
  • Arweave tokens purchased
  • Nano acquired and ready

Your wallet is fully configured for trading and transactions!
```

---

## Wizard Navigation

### UI Components

**Header Section**:
- Title: "Wallet Funding Setup Wizard"
- Step indicator: "Step X of 4"
- Updates dynamically as user progresses

**Content Area**:
- Scrollable area for step-specific content
- Clean layout with grouped information
- Formatted text with colors and styling

**Navigation Buttons**:
- **Previous (←)**: Go back to previous step (disabled on step 1)
- **Next (→)**: Proceed to next step (visible on steps 1-3)
- **Complete**: Finish wizard (visible only on step 4)

**Button Styling**:
```python
# Previous/Next Buttons
background-color: Default
color: Black
padding: 8px 16px

# Complete Button
background-color: #10b981 (Green)
color: White
font-weight: Bold
```

### Step Navigation Code

```python
def show_step(self, step_num):
    """Show the specified step."""
    # Clear previous content
    while self.content_layout.count():
        item = self.content_layout.takeAt(0)
        if item and item.widget():
            item.widget().deleteLater()
    
    # Show appropriate step
    if step_num == 0:
        self._show_step_1_sol()
    elif step_num == 1:
        self._show_step_2_swap_sol_to_usdc()
    elif step_num == 2:
        self._show_step_3_arweave()
    elif step_num == 3:
        self._show_step_4_nano()
    
    # Update UI
    self.current_step = step_num
    self.step_indicator.setText(f"Step {step_num + 1} of 4")
    
    # Enable/disable buttons
    self.prev_btn.setEnabled(step_num > 0)
    self.next_btn.setVisible(step_num < 3)
    self.complete_btn.setVisible(step_num == 3)
```

---

## Real-Time Transaction Tracking

### Pending Transactions Display

Each wizard step includes a pending transactions display showing real-time blockchain status:

**Display Format**:
```
📊 Pending USDC Transactions (2)
┌────────────────────────────────────┐
│ ⏳ Receive: 100.00 USDC (3/6 confirms)   │
│ ✓ Send: 50.00 USDC (6/6 confirms)      │
│ ... and 1 more pending transaction(s)   │
└────────────────────────────────────┘
```

**Status Indicators**:
- **⏳ Pending**: Transaction submitted, awaiting confirmations (orange)
- **✓ Confirmed**: Transaction finalized (green)
- **✗ Failed**: Transaction error (red)

**Implementation**:

```python
def _add_pending_transactions_display(self, currency: str):
    """Add a compact pending transactions display."""
    user = app_service.get_current_user()
    
    # Get pending transactions from tracker
    pending = []
    if self.tracker:
        pending = self.tracker.get_pending_transactions(
            user_id=user.id,
            currency=currency
        )
    
    # Create group box
    pending_group = QGroupBox(f"📊 Pending {currency} Transactions ({len(pending)})")
    pending_layout = QVBoxLayout(pending_group)
    
    # Show up to 3 transactions
    for tx in pending[:3]:
        target = self.tracker.confirmation_targets.get(currency, 6)
        
        tx_type = "Send" if tx.type == "send" else "Receive"
        status_icon = "⏳" if tx.status == "pending" else "✓"
        
        tx_label = QLabel(
            f"{status_icon} {tx_type}: {tx.amount} {currency} "
            f"({tx.confirmations}/{target} confirms)"
        )
        
        # Color coding
        if tx.status == "pending":
            tx_label.setStyleSheet("color: #ff9800;")  # Orange
        elif tx.status == "confirmed":
            tx_label.setStyleSheet("color: #4caf50;")  # Green
        elif tx.status == "failed":
            tx_label.setStyleSheet("color: #f44336;")  # Red
        
        pending_layout.addWidget(tx_label)
    
    # Show "more" indicator
    if len(pending) > 3:
        more_label = QLabel(f"... and {len(pending) - 3} more")
        pending_layout.addWidget(more_label)
    
    self.content_layout.addWidget(pending_group)
```

**Tracker Initialization**:

```python
def init_tracker(self):
    """Initialize transaction tracker asynchronously."""
    worker = AsyncWorker(self._init_tracker_async())
    worker.start()
    self._tracker_worker = worker

async def _init_tracker_async(self):
    """Initialize tracker asynchronously."""
    try:
        self.tracker = await get_transaction_tracker()
    except Exception as e:
        print(f"Error initializing tracker: {e}")
```

**Confirmation Targets**:
- USDC: 6 confirmations (≈ 2-3 seconds on Solana)
- ARWEAVE: 10+ confirmations (≈ 10-20 seconds)
- NANO: Instant (~1-2 seconds)

---

## Configuration and Services

### FundingManagerService

Central service managing all funding operations:

**Location**: `services/funding_manager_service.py`

**Responsibilities**:
- Configuration management
- Amount validation
- Transaction logging
- Feature flags

**Configuration Class**:

```python
@dataclass
class FundingConfig:
    # Cloudflare Worker
    cloudflare_worker_url: str = "https://nano-sender.yourdomain.workers.dev/sendNano"
    cloudflare_api_key: str = ""
    
    # Solana
    solana_rpc_url: str = "https://api.mainnet-beta.solana.com"
    
    # Jupiter (DEX for swaps)
    jupiter_quote_api: str = "https://quote-api.jup.ag/v6/quote"
    jupiter_swap_api: str = "https://quote-api.jup.ag/v6/swap"
    
    # Amount Limits
    usdc_min_amount: float = 1.0
    usdc_max_amount: float = 1000.0
    ar_min_amount: float = 0.001
    ar_max_amount: float = 100.0
    nano_min_amount: float = 0.001
    nano_max_amount: float = 1.0
    nano_rpc_url: str = "https://mynano.ninja/api"
    
    # Timeouts
    request_timeout: int = 30
    health_check_timeout: int = 10
    
    # Retry
    max_retries: int = 3
    retry_delay: int = 2
    
    # Feature Flags
    enable_cloudflare_nano: bool = True
    enable_arweave_purchase: bool = True
    enable_balance_check: bool = True
```

**Key Methods**:

```python
# Validation
is_valid, errors = service.validate_config()
is_valid, error = service.validate_nano_amount(0.5)
is_valid, error = service.validate_usdc_amount(50.0)
is_valid, error = service.validate_ar_amount(1.0)

# Configuration
service.save_config(config)
service.load_config()

# Transaction logging
service.log_transaction(
    transaction_type="nano_request",
    details={"address": "...", "hash": "..."},
    success=True
)

# History
history = service.get_transaction_history(limit=50)

# Status
status = service.get_config_status()
```

**Configuration Files**:
- **Config**: `funding_config.json` (JSON format)
- **Log**: `funding_transactions.log` (Text log)

**Transaction Log Format**:
```json
{
  "timestamp": "2024-02-13T23:42:35",
  "type": "nano_request",
  "success": true,
  "details": {
    "address": "nano_3...",
    "tx_hash": "ABC123",
    "retry_count": 0
  }
}
```

### NanoCloudflareService

Specialized service for Nano requests:

**Features**:
- Automatic retry logic (3 retries default)
- Error classification
- Rate limiting support
- Request history tracking
- Comprehensive validation

**Retry Behavior**:
- **Retryable Errors**: Timeouts, connection resets, 5xx, rate limit (429)
- **Non-retryable**: Invalid key (401), invalid amount (400), invalid address (400)
- **Retry Delay**: 2 seconds between attempts
- **Max Retries**: 3 attempts

**Response Format**:
```python
{
    "success": True/False,
    "hash": "transaction_id",
    "timestamp": "2024-02-13T...",
    "retry_count": 0-3,
    "status": "success|failed|timeout",
    "error": "error message if failed"
}
```

### SOL/USDC Swap Service

Handles swapping SOL to USDC via Jupiter:

**Features**:
- Balance fetching
- Quote generation (with 0.5% slippage protection)
- Transaction creation and signing
- Confirmation tracking

**Flow**:
1. Fetch user's SOL balance
2. Calculate 90% of balance to swap
3. Get quote from Jupiter API
4. Display estimated USDC output
5. Execute swap transaction
6. Monitor for blockchain confirmation

---

## User Experience Flows

### Typical User Journey

**Scenario: New User Funding Complete Wallet**

```
1. User launches Sapphire Exchange app
   ↓
2. User clicks "Wallet Funding Manager" in Dashboard
   ↓
3. Funding Wizard opens
   ↓
4. STEP 1: Fund SOL
   - User sees Solana address (with QR code)
   - User transfers SOL from exchange
   - User clicks "Next →"
   ↓
5. STEP 2: Swap SOL to USDC
   - User sees swap details (90% of balance)
   - User sees estimated USDC output
   - User clicks "Execute Swap"
   - Wizard shows "⏳ Preparing transaction..."
   - Swap completes (usually in 10-20 seconds)
   - User clicks "Next →"
   ↓
6. STEP 3: Purchase Arweave
   - User sees Arweave information
   - User clicks "Launch Arweave Purchase"
   - Separate dialog opens for AR purchase
   - User enters amount and completes purchase
   - Dialog closes, user clicks "Next →"
   ↓
7. STEP 4: Access Nano
   - User sees Nano address with QR code
   - User can request Nano via Cloudflare Worker
   - Dialog pops up for amount entry
   - User enters 0.001 NANO (or more)
   - Cloudflare Worker processes instantly
   - Transaction hash displayed
   - User clicks "Complete"
   ↓
8. Wizard closes
   ↓
9. User's wallet is fully funded and ready for trading!
```

### Checking Transaction Progress

```
1. User opens Funding Wizard again
   ↓
2. Each step displays pending transactions
   ↓
3. User can see confirmation progress
   Example: "⏳ Receive: 100.00 USDC (3/6 confirms)"
   ↓
4. Colors indicate status:
   - Orange: Pending (awaiting confirmations)
   - Green: Confirmed (finalized)
   - Red: Failed (issue occurred)
   ↓
5. Confirmations count up in real-time
   (3/6 → 4/6 → 5/6 → 6/6 → ✓ Confirmed)
```

### Recovery from Errors

**Scenario: Nano Request Fails**

```
1. User enters amount in RequestNanoDialog
   ↓
2. Clicks "🚀 Send Request"
   ↓
3. Status shows: "⏳ Sending request..."
   ↓
4. If error occurs:
   - Dialog shows error message
   - User sees detailed error (e.g., "Rate limited")
   - Transaction is logged with error details
   ↓
5. User can:
   - Retry the request
   - Try alternative faucet
   - Wait and try later
```

---

## Error Handling

### Validation Errors

**Amount Validation**:
```python
# Invalid amount checks:
- Amount is not empty
- Amount is numeric (can be parsed to Decimal)
- Amount is positive
- Amount has <= 30 decimal places
- Amount is within min/max limits
```

**Address Validation**:
```python
# Nano address format:
- Starts with "nano_"
- Correct length
- Valid characters (base32 encoding)

# Solana address format:
- 44 characters
- Valid base58 encoding

# Arweave address:
- 43 characters
- Valid base64 URL encoding
```

**Configuration Validation**:
```python
# Required checks:
- Cloudflare worker URL is set
- Cloudflare API key is set (if Nano enabled)
- USDC min < max
- Nano min < max
- All timeouts are positive
```

### Network Error Handling

**Retry Logic**:
```
Attempt 1: Send request
  ↓
  [Timeout/Error]
  ↓
Wait 2 seconds
  ↓
Attempt 2: Retry
  ↓
  [Success]
  ↓
Return result with retry_count=1
```

**Max Retries**: 3 attempts (configurable)

**Error Types**:
- **Transient**: Connection errors, timeouts, 5xx - RETRY
- **Permanent**: Invalid input, auth failure - DO NOT RETRY
- **Rate Limit**: 429 status code - RETRY with backoff

### User Error Messages

**Invalid Amount**:
```
"Minimum Nano amount is 0.001"
"Maximum Nano amount is 1.0"
"Please enter a valid amount"
"Amount has too many decimal places"
```

**Invalid Address**:
```
"Invalid Nano address configured"
"Nano address not configured"
```

**Configuration Errors**:
```
"Cloudflare API key not set"
"Nano requests are disabled in configuration"
"Configuration Error: [list of issues]"
```

**Network Errors**:
```
"Request failed: {detailed error}"
"Request timed out after all retries"
"Error: {exception message}"
```

---

## Advanced Features

### QR Code Generation

All wizard steps with addresses display QR codes:

```python
import qrcode
from PIL import Image

qr = qrcode.QRCode(
    version=1,
    box_size=10,  # or 8 for Nano
    border=2
)
qr.add_data(address)
qr.make(fit=True)

qr_img = qr.make_image(fill_color="black", back_color="white")

# Convert to QPixmap for PyQt5
buffer = io.BytesIO()
qr_img.save(buffer, format='PNG')
buffer.seek(0)

pixmap = QPixmap()
pixmap.loadFromData(buffer.getvalue(), 'PNG')
scaled = pixmap.scaledToWidth(200, Qt.SmoothTransformation)
label.setPixmap(scaled)
```

### Clipboard Integration

Users can copy addresses with one click:

```python
def _copy_to_clipboard(self, text):
    """Copy text to clipboard."""
    clipboard = QApplication.clipboard()
    clipboard.setText(text)
    QMessageBox.information(self, "Copied", "Address copied to clipboard!")
```

### External Link Integration

Faucet links open in default browser:

```python
def _open_url(self, url):
    """Open URL in default browser."""
    QDesktopServices.openUrl(QUrl(url))

# Usage in Step 4:
for link_name, url in faucet_links:
    link_btn.clicked.connect(lambda checked, u=url: self._open_url(u))
```

### Async Operations

All long-running operations are async to prevent UI blocking:

```python
# Swap execution
worker = AsyncWorker(self._execute_swap_async())
worker.finished.connect(self._on_swap_complete)
worker.error.connect(self._on_swap_error)
worker.start()

# Nano request
worker = AsyncWorker(self._execute_request(amount_raw))
worker.finished.connect(self._on_request_complete)
worker.error.connect(self._on_request_error)
worker.start()

# Tracker initialization
worker = AsyncWorker(self._init_tracker_async())
worker.start()
```

---

## Configuration Setup

### Initial Setup

1. **Create Configuration File** (`funding_config.json`):
```json
{
  "cloudflare_worker_url": "https://nano-sender.yourdomain.workers.dev/sendNano",
  "cloudflare_api_key": "your-api-key-here",
  "solana_rpc_url": "https://api.mainnet-beta.solana.com",
  "jupiter_quote_api": "https://quote-api.jup.ag/v6/quote",
  "jupiter_swap_api": "https://quote-api.jup.ag/v6/swap",
  "usdc_min_amount": 1.0,
  "usdc_max_amount": 1000.0,
  "ar_min_amount": 0.001,
  "ar_max_amount": 100.0,
  "nano_min_amount": 0.001,
  "nano_max_amount": 1.0,
  "nano_rpc_url": "https://mynano.ninja/api",
  "request_timeout": 30,
  "health_check_timeout": 10,
  "max_retries": 3,
  "retry_delay": 2,
  "enable_cloudflare_nano": true,
  "enable_arweave_purchase": true,
  "enable_balance_check": true
}
```

2. **Cloudflare Worker Setup**:
   - Deploy Nano sender worker
   - Set environment secrets
   - Note the worker URL

3. **Load Configuration** (in app initialization):
```python
from services.funding_manager_service import get_funding_manager_service

funding_service = get_funding_manager_service()
funding_service.load_config()

# Validate
is_valid, errors = funding_service.validate_config()
if not is_valid:
    print(f"Configuration errors: {errors}")
```

### Runtime Configuration Management

**Get Service**:
```python
funding_service = get_funding_manager_service()
```

**Check Configuration Status**:
```python
status = funding_service.get_config_status()
# Returns:
# {
#   "is_valid": True/False,
#   "errors": [...],
#   "cloudflare_configured": True/False,
#   "features": {
#     "nano": True/False,
#     "arweave": True/False,
#     "balance_check": True/False
#   },
#   "transaction_count": 123
# }
```

**Update Configuration**:
```python
new_config = FundingConfig(
    cloudflare_api_key="new-key",
    max_retries=5,
    nano_max_amount=2.0
)
funding_service.save_config(new_config)
```

---

## Monitoring and Logging

### Transaction Logging

All funding operations are logged automatically:

```python
# Log successful request
funding_service.log_transaction(
    transaction_type="nano_request",
    details={
        "address": "nano_3...",
        "tx_hash": "ABC123...",
        "retry_count": 0,
        "status": "success"
    },
    success=True
)

# Log failed request
funding_service.log_transaction(
    transaction_type="nano_request",
    details={
        "address": "nano_3...",
        "error": "Rate limited",
        "retry_count": 3,
        "status": "failed"
    },
    success=False
)
```

### Viewing Transaction History

```python
# Get all transactions (default 50)
history = funding_service.get_transaction_history()

# Get last 10 transactions
history = funding_service.get_transaction_history(limit=10)

# Each entry has:
# {
#   "timestamp": "2024-02-13T23:42:35",
#   "type": "nano_request",
#   "success": True/False,
#   "details": {...}
# }
```

### Log File Location

Transactions are logged to: `funding_transactions.log`

**Format**:
```
2024-02-13 23:42:35,123 - funding_manager - INFO - {"timestamp": "2024-02-13T23:42:35", "type": "nano_request", ...}
```

---

## Security Considerations

### Private Key Safety
- **Nano signing**: Private keys stored in Cloudflare Secrets
- **Solana signing**: Keys managed by wallet service
- **Never exposed**: Keys never transmitted to client

### API Security
- **Rate limiting**: Configured per request type
- **API key validation**: Required for Cloudflare Worker
- **Amount limits**: Enforced to prevent excessive transfers
- **Address validation**: Prevents sending to invalid addresses

### Transaction Validation
- **Amount checks**: Min/max limits enforced
- **Address format**: Validated before broadcast
- **Confirmation tracking**: Prevents double-spending
- **Retry safeguards**: Won't retry permanent failures

### User Data Protection
- **Address display**: Shown in QR code and text
- **Transaction hashes**: Logged and displayed to user
- **No secrets logged**: Private keys never appear in logs
- **Session isolation**: Each user has isolated wallet data

---

## Troubleshooting

### Nano Request Fails

**Problem**: "Unauthorized - Invalid API key"

**Solution**:
1. Check `funding_config.json` has correct API key
2. Verify Cloudflare Worker is deployed
3. Ensure API key matches Worker secret
4. Reload configuration: `funding_service.load_config()`

**Problem**: "Rate limited - please try again later"

**Solution**:
1. Wait a few minutes before retrying
2. Check faucet links as alternative
3. Ensure not making too many requests

**Problem**: Request times out

**Solution**:
1. Check internet connection
2. Verify Cloudflare Worker is online
3. Check Nano RPC endpoint is responding
4. Increase `request_timeout` in config

### Swap Fails

**Problem**: "Could not fetch quote"

**Solution**:
1. Verify SOL balance >= minimum required
2. Check Solana RPC is responding
3. Verify Jupiter API is reachable
4. Check network connection

**Problem**: "Swap failed: Insufficient balance"

**Solution**:
1. Ensure 90% of SOL balance is available
2. Wait for previous transactions to confirm
3. Add more SOL to wallet

### Arweave Purchase Fails

**Problem**: "Insufficient USDC balance"

**Solution**:
1. Complete SOL → USDC swap in Step 2
2. Wait for swap to confirm (10-20 seconds)
3. Ensure purchase amount <= USDC balance

### Pending Transactions Not Showing

**Problem**: No pending transactions displayed

**Solution**:
1. Ensure TransactionTracker is initialized
2. Check `data/transactions.json` exists
3. Verify user ID is correctly set
4. Reload wizard dialog

---

## Deployment Checklist

- [ ] Create `funding_config.json` with all required settings
- [ ] Deploy Cloudflare Worker for Nano requests
- [ ] Set Cloudflare secrets (NANO_PRIVATE_KEY, API_KEY, etc.)
- [ ] Test Nano request with valid configuration
- [ ] Verify swap service can reach Jupiter API
- [ ] Test Arweave purchase dialog
- [ ] Configure amount limits for production
- [ ] Set up transaction logging
- [ ] Test all four wizard steps
- [ ] Verify QR code generation works
- [ ] Test error handling scenarios
- [ ] Monitor transaction logs
- [ ] Setup alerting for failed transactions
- [ ] Document API keys and secrets in secure location

---

## Performance Optimization

### Async Operations

All blocking operations use async/await:
- Nano requests
- Swap execution
- Balance fetching
- Quote generation
- Tracker initialization

**Benefits**:
- UI remains responsive
- No frozen screens
- Better user experience
- Cancellable operations

### Lazy Loading

Components initialize only when needed:
```python
def init_tracker(self):
    """Initialize tracker when wizard opens."""
    worker = AsyncWorker(self._init_tracker_async())
    worker.start()
    self._tracker_worker = worker
```

### Caching

Transaction tracker caches:
- Pending transactions
- Confirmation targets
- Transaction history

**Cache Time**: 5-minute default TTL

---

## Future Enhancements

1. **Multi-Blockchain Support**
   - Add Dogecoin funding path
   - Add Ethereum support
   - Generic blockchain adapter

2. **Advanced Features**
   - Batch transactions
   - Recurring purchases
   - Dollar-cost averaging
   - Price alerts

3. **Analytics**
   - Transaction history export
   - Cost tracking
   - Portfolio analytics
   - Tax reporting

4. **UX Improvements**
   - Wizard resume (save progress)
   - Mobile-friendly version
   - Wallet import/export
   - Multi-signature support

---

## Summary

The Funding Wizard is a comprehensive, user-friendly system for onboarding users and funding their wallets across multiple blockchains. It provides:

✅ **4-Step Setup Process**: SOL → USDC → Arweave → Nano  
✅ **Real-Time Monitoring**: Transaction tracking with live confirmations  
✅ **Robust Error Handling**: Validation, retries, and clear error messages  
✅ **Security-First Design**: Private key safety, rate limiting, validation  
✅ **Excellent UX**: QR codes, copy buttons, external links, async operations  
✅ **Extensible Architecture**: Services, configuration, logging, monitoring  

Users can go from zero to fully-funded trading wallet in minutes with minimal friction!
