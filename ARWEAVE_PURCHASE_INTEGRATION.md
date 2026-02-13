# Arweave Purchase Integration

## Overview
This document describes the integration of Arweave (AR) purchasing functionality using USDC from a Solana wallet via Jupiter DEX.

## Components Added

### 1. Arweave Purchase Service (`services/arweave_purchase_service.py`)
**Purpose**: Handles all Arweave purchasing operations using Jupiter DEX on Solana.

**Key Features**:
- **Quote Generation**: Fetches real-time swap quotes from Jupiter
- **Token Discovery**: Automatically discovers Arweave token mints on Solana
- **Transaction Building**: Constructs swap transactions for signing
- **Swap Execution**: Executes complete swap from USDC to AR
- **Estimation**: Estimates AR output for a given USDC amount

**Key Methods**:
```python
async def discover_arweave_token() -> Optional[str]
    # Discovers current Arweave token mint on Solana

async def get_quote(usdc_amount: float, output_mint: Optional[str]) -> Optional[ArweaveSwapQuote]
    # Gets Jupiter quote for swap

async def build_swap_transaction(user_pubkey: str, usdc_amount: float) -> Optional[str]
    # Builds swap transaction (base64 encoded)

async def execute_swap(user_pubkey: str, usdc_amount: float, keypair_bytes: Optional[bytes]) -> Optional[Dict]
    # Executes complete swap end-to-end

async def estimate_arweave_output(usdc_amount: float) -> Optional[float]
    # Estimates AR output amount
```

### 2. Arweave Purchase Dialog (`ui/wallet_widget.py` - ArweavePurchaseDialog)
**Purpose**: Provides user interface for purchasing Arweave.

**Features**:
- Real-time AR estimate as user types USDC amount
- Shows price impact and swap route
- Confirmation dialog before transaction
- Progress indication during swap
- Success/error feedback

**User Flow**:
1. User enters USDC amount
2. System fetches quote and shows AR estimate
3. User confirms transaction
4. System builds, signs, and sends swap transaction
5. User sees transaction ID and confirmation

### 3. Wallet Widget Integration (`ui/wallet_widget.py`)
**Changes**:
- Added "Buy with USDC" button to Arweave wallet tab
- Integrated ArweavePurchaseDialog for purchase workflow
- Connected purchase button to show_purchase_dialog() method

## How to Use

### From the UI
1. Navigate to the Wallet section
2. Click on the "ARWEAVE" tab
3. Click "Buy with USDC" button
4. Enter amount of USDC you want to spend
5. Review the AR estimate and price impact
6. Click OK to confirm
7. System will execute the swap on Jupiter DEX

### From Code
```python
# Initialize service
service = await get_arweave_purchase_service(config)

# Get a quote
quote = await service.get_quote(usdc_amount=100.0)

# Execute swap (requires private key)
result = await service.execute_swap(
    user_pubkey="wallet_address",
    usdc_amount=100.0,
    keypair_bytes=private_key_bytes
)

# Check result
if result and result.get('success'):
    print(f"Swap successful: {result['transaction_id']}")
```

## Technical Details

### Jupiter DEX Integration
- **Quote API**: `https://quote-api.jup.ag/v6/quote`
- **Swap API**: `https://quote-api.jup.ag/v6/swap`
- **Token Discovery**: Queries `https://token.jup.ag/all`

### Slippage Configuration
- Default slippage: 1% (100 basis points)
- Configurable via `ArweavePurchaseService.slippage_bps`

### Token Specifications
- **USDC**: `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v` (Solana mainnet)
- **AR**: Dynamically discovered from token list (varies by bridge/wrapper)

### Transaction Flow
1. Build quote request with input/output mints and amount
2. Receive route plan and swap details
3. Request signed transaction from Jupiter
4. Sign with user's private key
5. Send to Solana network
6. Monitor for confirmation

## Important Notes

### Security
- Private keys are NOT stored in service - passed at execution time
- All signing happens locally
- No keys exposed to Jupiter API

### Solana Considerations
- Requires SOL for transaction fees (gas)
- USDC must exist in Associated Token Account (ATA)
- AR output may be wrapped token requiring redemption

### AR Token Types
- **Native AR**: Arweave's native token (on Arweave chain)
- **Wrapped AR (wAR)**: Bridge token on Solana
- Some swaps may return wrapped AR requiring bridge redemption

### Error Handling
- Network timeouts: 10-second timeout with clear error messages
- Invalid quotes: System retries or uses fallback tokens
- Transaction failures: User notified with error details

## Configuration

### Recommended Setup
```python
config = {
    "solana": {
        "rpc_url": "https://api.mainnet-beta.solana.com",
        "commitment": "confirmed"
    }
}

service = await get_arweave_purchase_service(config)
```

### Alternative RPC Endpoints
- Mainnet: `https://api.mainnet-beta.solana.com`
- QuickNode: Requires API key
- Alchemy: Requires API key

## Testing

### Mock Mode
The service can operate in mock/test mode:
- Quotes will use cached data
- No actual transactions sent
- Useful for UI testing

### Test Amounts
- Start with small amounts ($5-$20 USDC)
- Verify addresses on Solana Explorer
- Monitor token account balances

## Known Limitations

1. **Wrapped AR Redemption**: Currently shows warning for wrapped tokens; manual redemption required
2. **Token Discovery**: May have slight delays fetching current token mints
3. **Price Impact**: Shows estimated impact; actual may vary slightly
4. **Rate Limiting**: Jupiter has rate limits on public API

## Future Enhancements

- [ ] Automatic wrapped AR to native AR redemption
- [ ] Multi-route optimization
- [ ] Transaction history tracking
- [ ] Price alerts
- [ ] Limit orders via Jupiter
- [ ] Historical price charts

## Troubleshooting

### "Could not determine Arweave token mint"
- Check internet connection
- Verify Jupiter API is accessible
- Try using explicit token mint

### "Transaction failed"
- Ensure sufficient SOL for gas fees
- Check USDC balance in Solana wallet
- Verify slippage tolerance isn't too low

### "No route found"
- AR liquidity may be low
- Try smaller amounts
- Check if token is listed on Solana

## References

- [Jupiter DEX Documentation](https://station.jup.ag/docs/apis/overview)
- [Solana Token Mints](https://solscan.io/)
- [Arweave on Solana](https://arweave.org/)
