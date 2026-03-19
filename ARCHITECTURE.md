# Sapphire Exchange everPay Direct Architecture

## Objective

Sapphire Exchange uses an everPay-only, non-custodial funding rail for native Arweave delivery.

This app never sends private keys off device.
All everPay actions are signed client-side by the user's local wallet.
The app never accepts user funds into an app-controlled wallet.

## Runtime Adaptation

The original everPay design was browser-oriented.
This repository is a PyQt desktop application, so the same custody boundary is enforced with desktop-local encrypted storage instead of browser localStorage or IndexedDB.

## Architecture Contract

### Custody Boundary

- The user controls the everPay signing key locally on the desktop device.
- The private key is encrypted at rest with a password-derived key.
- The private key is never uploaded to a backend service.
- The app never signs everPay transactions on a server.
- The app never routes user funds through an app-controlled wallet.

### Funding Path

User local EVM key -> everPay -> AR on everPay -> withdraw -> native AR -> user.arweave_address

### Backend Scope

If any backend exists, it is read-only only.

Allowed backend responsibilities:
- Static configuration
- Price lookups
- Read-only metadata

Forbidden backend responsibilities:
- Receiving user funds
- Storing user private keys
- Signing everPay transactions
- Acting as a custody intermediary

## Local Wallet Contract

### Wallet Creation

The desktop app creates a local EVM wallet for everPay signing.

Implementation contract:
- Generate a fresh EVM keypair locally.
- Encrypt the private key with AES-GCM.
- Derive the encryption key from a user password.
- Persist only encrypted wallet material and non-sensitive metadata.

### Wallet Storage

Local wallet data is stored under the user's local Sapphire Exchange data directory.

Stored material:
- Encrypted private key vault
- Wallet address
- KDF salt and metadata

Not stored remotely:
- Raw private key
- Unencrypted signing secrets

### Wallet Operations

The desktop app must support:
- Create local wallet
- Load local wallet with password
- Export encrypted wallet JSON
- Import encrypted wallet JSON
- Lock or unload local wallet from memory

## everPay API Contract

Base URL:
- `https://api.everpay.io`

Required client operations:
- `get_info()` -> `GET /info`
- `get_balances(address)` -> `GET /balances/:everpayAddress`
- `post_tx(tx, sig)` -> `POST /tx`

Transaction shape:
- `action`
- `from`
- `token`
- `amount`
- `nonce`
- optional `to`
- optional `swapTo`
- optional `target`

## Signing Contract

All everPay transaction payloads are serialized locally and signed by the user's local wallet.

Signing requirements:
- Build the unsigned everPay transaction object locally.
- Serialize the transaction locally.
- Sign the serialized payload locally.
- Submit the signed payload directly to everPay.

## Funding Flow Contract

### Step 1: Create or Load Wallet

The user must create or unlock a local everPay wallet before any executable everPay action is enabled.

### Step 2: Fund everPay

The desktop client builds a signed transfer transaction:
- `action = transfer`
- `from = userEverpayAddress`
- `to = everpay`
- `token = configured input token`
- `amount = smallest unit string`
- `nonce = local monotonic nonce`

### Step 3: Swap to AR

The desktop client builds a signed swap transaction:
- `action = swap`
- `from = userEverpayAddress`
- `token = configured USDC token`
- `amount = funded USDC amount`
- `swapTo = configured AR token`
- `nonce = local monotonic nonce`

### Step 4: Withdraw Native AR

The desktop client builds a signed withdraw transaction:
- `action = withdraw`
- `from = userEverpayAddress`
- `token = configured AR token`
- `amount = AR amount on everPay`
- `target = user.arweave_address`
- `nonce = local monotonic nonce`

## UI Flow Contract

The desktop UI must present the flow as four linear steps:
1. Create/Load Wallet
2. Fund everPay
3. Swap to AR
4. Withdraw to Arweave

UI requirements:
- Show current everPay wallet address
- Show current everPay balances
- Disable executable actions until the local wallet is available
- Disable downstream actions until prior actions are completed or confirmed
- Show the user's Arweave destination address before withdraw

## Integration Contract

### Local Wallet Service

The local wallet service is responsible for:
- Creating encrypted local wallets
- Loading encrypted local wallets
- Exporting encrypted wallet backups
- Importing encrypted wallet backups
- Signing everPay transactions locally

### everPay Client Service

The everPay client service is responsible for:
- Fetching token metadata
- Fetching balances
- Posting signed everPay transactions

### AR Purchase Flow

The Arweave funding flow must use the local wallet path for execution.
Environment-variable signer keys are compatibility-only and must not be the intended production path for user custody.

## Non-Negotiable Security Rules

- Never transmit the user's raw private key over the network.
- Never persist the user's raw private key unencrypted on disk.
- Never sign everPay actions with a backend-held key for user-owned funds.
- Never require the user to send funds to an app-controlled intermediary wallet.
