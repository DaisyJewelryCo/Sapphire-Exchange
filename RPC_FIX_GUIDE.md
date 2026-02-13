# Solana RPC Error Fix Guide

## Problem Summary

You're seeing **RPC_error for USDC** and **"Error initializing tracker: no running event loop"** messages. This guide explains what these are and how to fix them.

## Root Causes

### 1. **RPC_error** (Solana Connection Failure)
The Solana RPC endpoint is unreachable or rate-limited:
- **Default endpoint**: `https://api.mainnet-beta.solana.com`
- **Issue**: Public endpoints have rate limits and can go down frequently
- **Solution**: Switch to a more reliable RPC provider

### 2. **Event Loop Error** (Application Initialization)
The transaction tracker tried to initialize before the Qt event loop was fully ready.
- **Fixed in**: `services/transaction_tracker.py` (v2.0)
- **Now**: Gracefully handles early initialization and retries automatically

## Quick Fix (Choose One)

### Option A: Use Solana Devnet (Best for Testing)
Edit `.env` and set:
```bash
SOLANA_RPC_URL=https://api.devnet.solana.com
SOLANA_TESTNET=true
```

### Option B: Use a Free Public Endpoint
Edit `.env` and set:
```bash
SOLANA_RPC_URL=https://solana-rpc.publicnode.com
SOLANA_TESTNET=false
```

### Option C: Get a Paid RPC Endpoint (Recommended for Production)
1. Sign up at one of:
   - [Alchemy](https://www.alchemy.com/)
   - [QuickNode](https://www.quicknode.com/)
   - [Infura](https://infura.io/)
   - [Magic Eden](https://www.magiceden.io/)

2. Get your RPC endpoint URL (e.g., `https://your-key.solana-mainnet.quicknode.pro`)

3. Edit `.env` and set:
```bash
SOLANA_RPC_URL=https://your-key.solana-mainnet.quicknode.pro
SOLANA_TESTNET=false
```

## How to Check Your Configuration

Run the configuration diagnostic:
```bash
python3 diagnose_config.py
```

This shows you:
- Current environment variables
- Which RPC endpoint will be used
- Your current settings

## Changes Made (Version 2.0)

### 1. Enhanced Error Handling
**File**: `blockchain/solana_usdc_client.py`
- Added detailed error messages for RPC failures
- Added timeout protection (10 seconds)
- Clear indicators of what's wrong (✅ ✗ ⏱️)
- Distinguishes between:
  - RPC endpoint not responding (timeout)
  - RPC endpoint unreachable (connection error)
  - Health check failed (endpoint is down)

### 2. Event Loop Robustness
**File**: `services/transaction_tracker.py`
- HTTP session now initializes lazily (only when needed)
- Gracefully handles event loop not ready yet
- Can retry initialization automatically

### 3. UI Error Recovery
**File**: `ui/pending_transactions_widget.py`
- Better error handling for tracker initialization
- Shows informative error messages
- Automatically retries if tracker wasn't ready

### 4. Configuration Improvements
**File**: `config/blockchain_config.py`
- Solana RPC URL now configurable via environment
- Added diagnostic method: `diagnose_rpc_config()`
- Proper validation of RPC endpoint format

### 5. Configuration File
**File**: `.env`
```bash
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
SOLANA_TESTNET=false
```

## Testing Your Fix

### 1. Check Configuration
```bash
python3 diagnose_config.py
```

### 2. Restart Application
```bash
python3 app.py
```

### 3. Monitor Logs
Look for:
- ✅ `Solana USDC client initialized successfully` = Working
- ✗ `Solana RPC health check failed` = Endpoint down
- ⏱️ `health check timeout` = Network issue

## Common Issues and Solutions

### Issue: Still Seeing "RPC_error"

**Cause**: RPC endpoint is still unreachable

**Solutions**:
1. Check internet connection
2. Try a different RPC endpoint
3. Check [Solana Status](https://status.solana.com) for outages
4. Use a paid RPC service

```bash
# Try devnet temporarily
SOLANA_RPC_URL=https://api.devnet.solana.com
SOLANA_TESTNET=true
```

### Issue: "Event loop not ready yet" in logs

**Cause**: Widget initializing before Qt event loop fully started

**Status**: ✅ FIXED - Application will retry automatically

**What to do**: Just wait a few seconds, it retries on next refresh

### Issue: RPC endpoint rate limited

**Solution**: Use a paid RPC provider with higher rate limits:
- Alchemy (1M+ requests/day on free tier)
- QuickNode (25 Gbps bandwidth)
- Infura (100k calls/day free)

## RPC Endpoint Comparison

| Endpoint | Free Tier | Mainnet | Notes |
|----------|-----------|---------|-------|
| Official mainnet | ✅ | ✅ | Rate limited, may be down |
| Official devnet | ✅ | ❌ | Stable but no real data |
| PublicNode | ✅ | ✅ | Community-run, good speed |
| Alchemy | ✅ | ✅ | 1M+ daily, highly reliable |
| QuickNode | ✅ | ✅ | Fast, good for production |
| Infura | ✅ | ✅ | Enterprise-grade |

## Advanced Configuration

### Using Environment Variables
```bash
export SOLANA_RPC_URL="https://your-endpoint.com"
export SOLANA_TESTNET=false
python3 app.py
```

### Using .env File (Recommended)
```bash
# .env file
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
SOLANA_TESTNET=false
```

### Disable USDC (Temporary)
If you want to disable USDC temporarily while fixing RPC:
```python
# In blockchain/blockchain_manager.py
# Comment out: solana_usdc_result = await self._initialize_solana_usdc()
```

## For Developers

### Debug USDC Initialization
```python
from config.blockchain_config import blockchain_config

# See what's being used
config_info = blockchain_config.diagnose_rpc_config()
print(config_info)
```

### Force Retry
The UI will automatically retry the tracker initialization, but you can also:
```python
# In pending_transactions_widget.py
# Call refresh_transactions() again
self.refresh_transactions()
```

## Need Help?

1. Run: `python3 diagnose_config.py`
2. Check logs for error messages
3. Verify `.env` file is updated
4. Restart the application
5. Wait 10+ seconds for retries to complete

## Verification Checklist

- [ ] `.env` file updated with RPC endpoint
- [ ] `.env` file saved
- [ ] Application restarted
- [ ] Logs show "✓ Solana USDC client initialized successfully"
- [ ] No "RPC_error" in status indicator
- [ ] Transaction widget loads without errors

## Support

For ongoing issues:
1. Keep `.env` with a working RPC endpoint
2. Monitor [Solana Status Page](https://status.solana.com)
3. Use paid RPC for production
4. Check application logs for detailed error messages
