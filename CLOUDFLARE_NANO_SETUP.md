# Cloudflare Nano Worker Setup Guide

## Overview

The funding manager now integrates with a Cloudflare Worker to facilitate Nano fund requests. This guide explains how to set up and configure the worker.

## Architecture

```
┌─────────────────────────┐
│  Funding Manager (UI)    │
│  Step 3: Request Nano    │
└──────────────┬──────────┘
               │ HTTP POST
               ▼
┌──────────────────────────────────────┐
│  Cloudflare Worker (nano-sender)     │
│  - Validates requests                │
│  - Checks rate limits                │
│  - Builds Nano blocks                │
│  - Signs with private key            │
│  - Broadcasts to Nano network        │
└──────────────┬───────────────────────┘
               │ Nano RPC
               ▼
┌──────────────────────────┐
│  Nano Network (RPC Node) │
└──────────────────────────┘
```

## Quick Setup

### 1. Install Wrangler (Cloudflare CLI)

```bash
npm install -g wrangler
```

### 2. Create Worker Project

```bash
wrangler init nano-sender
cd nano-sender
```

### 3. Create Worker File

Create or replace `src/index.ts` with the code from `utils/NANO_FUNDING.md` (lines 218-384).

**Key functions to implement:**
- `addressToPublicKey()` - Convert Nano address to 32-byte public key
- `signNanoBlock()` - Sign block with Ed25519 private key
- `nanoRpc()` - Make RPC calls to Nano node

### 4. Add Secrets

```bash
# Store your Nano private key (in HEX format)
wrangler secret put NANO_PRIVATE_KEY

# Your Nano address (the sender)
wrangler secret put NANO_ADDRESS

# Nano RPC endpoint
wrangler secret put NANO_RPC_URL
# Example: https://mynano.ninja/api

# API key for your app
wrangler secret put API_KEY
# Use: your-secure-api-key-here
```

### 5. Configure wrangler.toml

```toml
name = "nano-sender"
main = "src/index.ts"
compatibility_date = "2024-01-01"

[env.production]
# Production configuration
```

### 6. Deploy

```bash
wrangler deploy
```

Your worker will be available at:
```
https://nano-sender.<your-account>.workers.dev/sendNano
```

## Integrating with Sapphire Exchange

### 1. Update Configuration

In your app's configuration, set the Cloudflare Worker URL:

```python
# config/app_config.py or environment variable
CLOUDFLARE_NANO_WORKER_URL = "https://nano-sender.<your-account>.workers.dev/sendNano"
CLOUDFLARE_NANO_API_KEY = "your-secure-api-key"
```

### 2. Service Initialization

The `NanoCloudflareService` will automatically use these settings:

```python
from services.nano_cloudflare_service import get_nano_cloudflare_service

service = await get_nano_cloudflare_service(
    worker_url="https://nano-sender.<your-account>.workers.dev/sendNano",
    api_key="your-secure-api-key"
)
```

### 3. Testing Connection

The service includes a validation method:

```python
# Check if worker is reachable
is_reachable = await service.validate_worker_connection()
if is_reachable:
    print("Worker is online and responding")
```

## API Request/Response Format

### Request (from UI to Worker)

```json
{
  "to": "nano_3destinationaddress...",
  "amount_raw": "1000000000000000000000000",
  "api_key": "your-app-api-key"
}
```

**Fields:**
- `to`: Destination Nano address (nano_...)
- `amount_raw`: Amount in raw (smallest unit, 1 NANO = 10^30 raw)
- `api_key`: Authentication key

### Response (from Worker)

**Success:**
```json
{
  "success": true,
  "hash": "ABC123DEF456..."
}
```

**Error:**
```json
{
  "success": false,
  "error": "Insufficient balance in system wallet"
}
```

## Worker Validation Rules

The worker enforces:

1. **API Key Validation**
   - Must match `API_KEY` secret
   - Returns 401 Unauthorized if invalid

2. **Amount Limits**
   - Min: 1 raw
   - Max: 1e24 raw (~0.001 NANO)
   - Adjustable in worker code

3. **Address Validation**
   - Must start with `nano_`
   - Must be valid format

4. **Rate Limiting** (Optional)
   - Per IP: 10 requests/hour
   - Per destination: 100 requests/day
   - Implement using KV or Durable Objects

## Security Considerations

✅ **Private Key Security**
- Stored ONLY in Cloudflare Secrets
- Never exposed to client app
- Never logged or transmitted

✅ **Request Validation**
- API key required for all requests
- Amount validated
- Address format checked

✅ **Rate Limiting**
- Prevents abuse
- IP-based and destination-based

✅ **Worker Isolation**
- Runs in isolated Cloudflare environment
- No server maintenance needed
- Automatic scaling

## Troubleshooting

### Worker Returns 401 Unauthorized

**Problem:** `API_KEY` doesn't match

**Solution:**
```bash
# Verify secret is set correctly
wrangler secret list

# Re-add if needed
wrangler secret put API_KEY
```

### Worker Times Out

**Problem:** Nano RPC endpoint is slow

**Solution:**
1. Check RPC endpoint is reachable
2. Use faster endpoint (QuickNode, RPC pool)
3. Increase timeout in worker code

### "No Route" Error

**Problem:** Worker can't reach Nano network

**Solution:**
1. Verify `NANO_RPC_URL` is correct
2. Test RPC endpoint directly
3. Check firewall/network access

### Signing Fails

**Problem:** Invalid private key format

**Solution:**
1. Ensure private key is in HEX format (no "nano_" prefix)
2. Private key should be 64 characters (32 bytes hex)
3. Use this command to verify:
   ```bash
   echo $NANO_PRIVATE_KEY | wc -c  # Should output 65 (64 + newline)
   ```

## Testing

### From Funding Manager UI

1. Go to Dashboard → Funding Manager
2. Click "Launch Funding Wizard"
3. Navigate to Step 3: "Acquire Nano"
4. Click "🔗 Request Nano" button
5. Enter amount (0.001 to 1 NANO)
6. Click "🚀 Send Request"
7. Check for success message with transaction hash

### Manual Testing with curl

```bash
curl -X POST https://nano-sender.<your-account>.workers.dev/sendNano \
  -H "Content-Type: application/json" \
  -d '{
    "to": "nano_3t6k35gi95xu6tergt6p69ck76ogmitsa8mnijtpxm9fkcm736xtoncuohr3",
    "amount_raw": "1000000000000000000000000",
    "api_key": "your-secure-api-key"
  }'
```

## Implementation Checklist

- [ ] Install Wrangler CLI
- [ ] Create worker project
- [ ] Implement address-to-pubkey conversion
- [ ] Implement block signing (Ed25519)
- [ ] Set Cloudflare Secrets (4 required)
- [ ] Configure wrangler.toml
- [ ] Deploy worker
- [ ] Test with curl
- [ ] Test from Funding Manager UI
- [ ] Configure app with worker URL/API key
- [ ] Validate worker connection
- [ ] Monitor worker logs
- [ ] Set up rate limiting (optional)

## Required Dependencies for Worker

The worker requires a Nano signing library. Common options:

1. **TweetNaCl.js** (recommended for simplicity)
   ```javascript
   import nacl from 'tweetnacl';
   ```

2. **libsodium.js**
   ```javascript
   import sodium from 'libsodium.js';
   ```

3. **Pure JavaScript implementation** (if KV/environment constraints)

## References

- [NANO_FUNDING.md](./utils/NANO_FUNDING.md) - Full implementation details
- [Cloudflare Workers Docs](https://developers.cloudflare.com/workers/)
- [Nano RPC Docs](https://docs.nano.org/commands/rpc-protocol/)
- [NaCl Signing](https://doc.libsodium.org/public-key_cryptography/signing)

## Support

For issues or questions:
1. Check worker logs: `wrangler tail`
2. Verify Secrets: `wrangler secret list`
3. Test RPC endpoint directly
4. Review transaction trace in Cloudflare dashboard
