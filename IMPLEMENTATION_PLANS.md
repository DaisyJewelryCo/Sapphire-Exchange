# Sapphire Exchange: 5 Implementation Plans

## Overview
This document outlines 5 separate, modular implementation plans for a secure, non-custodial PyQt6 wallet supporting USDC (Ethereum/Solana/Stellar), Nano, and Arweave.

Each plan is designed to be independently implementable while maintaining compatibility with the others.

---

## Plan 1: Offline Wallet Generation System

### Objective
Create a secure offline wallet generation system supporting BIP39/BIP44 mnemonics for USDC (Ethereum/Solana/Stellar), Nano, and RSA-4096 JWK generation for Arweave.

### Architecture

#### Core Components
1. **EntropyGenerator**
   - Uses `os.urandom()` for CSPRNG entropy
   - Validates entropy quality (minimum 256 bits)
   - Optional HRNG support (hardware random number generator)
   - Fallback entropy validation using system entropy pools

2. **WalletGenerator**
   - Per-blockchain wallet generation logic
   - BIP39 mnemonic generation and validation
   - BIP32/BIP44 HD wallet derivation
   - RSA-4096 key generation for Arweave
   - Keypath standardization

3. **KeyDerivation**
   - SLIP-0010 for Ed25519 (Nano, Solana)
   - secp256k1 ECDSA for Ethereum
   - RSA-PSS for Arweave
   - Hardened path derivation for security

#### Key Generation Specifications

**Ethereum/USDC (EVM)**
- Curve: secp256k1
- Mnemonic: BIP39 (12/24 words)
- Derivation: BIP44 path `m/44'/60'/0'/0/0`
- Address: Keccak-256 hash, last 20 bytes, 0x-prefixed
- Libraries: `eth-account`, `bip_utils`

**Solana/USDC**
- Curve: Ed25519
- Mnemonic: BIP39 (12/24 words)
- Derivation: BIP44 path `m/44'/501'/0'/0'`
- Address: Base58-encoded public key (32 bytes)
- Libraries: `bip_utils`, `solana.py`

**Stellar/USDC**
- Curve: Ed25519
- Mnemonic: BIP39 (12/24 words)
- Derivation: BIP44 path `m/44'/148'/0'/0/0`
- Address: Base32-encoded public key with checksum
- Libraries: `stellar-sdk`, `bip_utils`

**Nano**
- Curve: Ed25519
- Mnemonic: BIP39 (12/24 words)
- Derivation: BIP44 path `m/44'/165'/0'` with SLIP-0010
- Address: Base32-encoded with `nano_` prefix and blake2b checksum
- Libraries: `bip_utils`, custom SLIP-0010 implementation

**Arweave**
- Key Type: RSA-4096 (RSA-PSS)
- Format: JWK (JSON Web Key)
- Address: SHA-256 hash of public key, Base64URL-encoded
- Libraries: `cryptography`, `arweave-python-client`

### Implementation Steps

1. **Create Entropy Module** (`blockchain/entropy_generator.py`)
   - `class EntropyGenerator`
   - Methods: `generate_entropy()`, `validate_entropy()`, `get_entropy_quality()`

2. **Create BIP39/BIP44 Module** (`blockchain/bip39_derivation.py`)
   - `class BIP39Manager`: Mnemonic generation/validation
   - `class BIP44Derivation`: HD wallet path derivation
   - Wordlist validation (English, 12/24 word support)

3. **Create Asset-Specific Generators** (`blockchain/wallet_generators/`)
   - `ethereum_generator.py`: Ethereum/Solana wallet generation
   - `nano_generator.py`: Nano wallet generation with SLIP-0010
   - `arweave_generator.py`: RSA-4096 JWK generation
   - `stellar_generator.py`: Stellar wallet generation

4. **Create Unified Wallet Generator** (`blockchain/unified_wallet_generator.py`)
   - `class UnifiedWalletGenerator`
   - Methods: `generate_all()`, `generate_for_asset()`, `validate_mnemonic()`

5. **Unit Tests** (`tests/test_wallet_generation.py`)
   - Entropy quality tests
   - BIP39/BIP44 compliance tests
   - Known vector validation (test data)
   - Address format validation

### Security Considerations
- Never log private keys, mnemonics, or seeds
- Clear sensitive data from memory after use
- Validate all entropy sources
- Test against known BIP39 test vectors
- Implement entropy fallback mechanisms

### Dependencies
- `mnemonic>=0.20`: BIP39 support
- `bip_utils>=1.10.0`: BIP32/BIP44 derivation
- `cryptography>=38.0.0`: RSA-4096 generation
- `pynacl>=1.5.0`: Ed25519 operations

### Deliverables
- Entropy generation with validation
- BIP39 mnemonic generation and validation
- BIP32/BIP44 HD wallet derivation
- Per-asset wallet generation
- Comprehensive test coverage with known vectors

---

## Plan 2: Secure Key Storage System

### Objective
Implement secure, multi-layered local key storage with AES-256-GCM encryption, master password protection, and optional OS keyring integration.

### Architecture

#### Core Components

1. **MasterPassword Manager**
   - Derives encryption key from master password
   - Uses Argon2id (OWASP recommended)
   - Strong random salt generation
   - Password strength validation
   - Secure password comparison (constant-time)

2. **EncryptedVault**
   - AES-256-GCM symmetric encryption
   - Per-key unique IV (initialization vector)
   - HMAC authentication tag for integrity
   - Metadata storage (key type, asset, chain, creation date)
   - Automatic key rotation support

3. **KeyRing Integration (Optional)**
   - OS-specific keyring backend selection
   - Windows: Credential Locker
   - macOS: Keychain
   - Linux: Secret Service (GNOME Keyring/KWallet)
   - Fallback to encrypted file storage

4. **Session Manager**
   - In-memory key decryption only
   - Automatic session timeout (configurable)
   - Secure memory wiping after use
   - Rate-limiting for unlock attempts
   - Failed attempt logging

5. **Backup & Recovery**
   - Encrypted key export
   - Backup file integrity verification
   - Migration between storage backends
   - Recovery key generation

### Storage Structure

```
~/.sapphire_exchange/
├── vault.enc                 # Encrypted key storage
├── vault.meta               # Metadata (cleartext)
├── session.token            # Temporary session key
└── backup/
    ├── vault.backup.enc     # Encrypted backup
    └── recovery.key         # Recovery key (encrypted)
```

### Implementation Steps

1. **Create Password Management Module** (`security/password_manager.py`)
   - `class MasterPasswordManager`
   - Methods: `hash_password()`, `verify_password()`, `derive_key()`, `get_strength()`
   - Use Argon2id with OWASP parameters

2. **Create Encryption Module** (`security/vault_encryption.py`)
   - `class CryptoVault`
   - Methods: `encrypt_key()`, `decrypt_key()`, `verify_integrity()`
   - AES-256-GCM with authenticated encryption
   - Per-key IV generation

3. **Create Key Storage Module** (`security/key_storage.py`)
   - `class SecureKeyStorage`
   - Methods: `store_key()`, `retrieve_key()`, `list_keys()`, `delete_key()`
   - Persistent storage with encryption
   - Metadata management

4. **Create Session Manager** (`security/session_manager.py`)
   - `class SessionManager`
   - Methods: `unlock()`, `lock()`, `is_unlocked()`, `refresh_session()`
   - Timeout-based auto-lock
   - Rate-limiting for unlock attempts

5. **Create OS Keyring Integration** (`security/keyring_backend.py`)
   - `class KeyringManager`
   - Platform-specific backend selection
   - Fallback to file storage
   - Transparent key caching

6. **Create Backup System** (`security/backup_manager.py`)
   - `class BackupManager`
   - Methods: `create_backup()`, `restore_backup()`, `verify_backup()`
   - Encrypted backup files
   - Recovery key generation

7. **Unit Tests** (`tests/test_key_storage.py`)
   - Encryption/decryption correctness
   - Password strength validation
   - Session timeout behavior
   - Backup/recovery workflows
   - Cross-platform keyring tests

### Security Considerations
- Use Argon2id (memory-hard, resistant to GPU attacks)
- AES-256-GCM (authenticated encryption)
- Unique IV per encryption operation
- Constant-time comparisons for passwords/tokens
- Secure random number generation
- No logging of sensitive data
- Memory wiping after use (`secrets.token_bytes()`)
- Rate-limiting on unlock attempts
- Never store plaintext keys on disk

### Dependencies
- `cryptography>=38.0.0`: AES-256-GCM, key derivation
- `argon2-cffi>=21.3.0`: Argon2id hashing
- `keyring>=23.0.0`: OS keyring integration
- `pynacl>=1.5.0`: Additional crypto operations

### Deliverables
- Master password management with Argon2id
- AES-256-GCM encrypted key vault
- Session management with auto-lock
- OS keyring integration with fallback
- Encrypted backup/recovery system
- Comprehensive security testing

---

## Plan 3: Transaction Signing & Broadcasting System

### Objective
Implement secure offline transaction signing and online broadcasting for USDC (Ethereum/Solana/Stellar), Nano, and Arweave with comprehensive error handling and transaction status tracking.

### Architecture

#### Core Components

1. **Transaction Builder**
   - Asset-specific transaction construction
   - Parameter validation and normalization
   - Fee estimation and adjustment
   - Transaction simulation (where available)

2. **Offline Signer**
   - Private key-based signing
   - Per-asset signing algorithms
   - Signature verification
   - Deterministic nonce management

3. **Broadcaster**
   - Node RPC communication
   - Retry logic with exponential backoff
   - Transaction status polling
   - Timeout handling

4. **Status Tracker**
   - Real-time transaction monitoring
   - Confirmation counting
   - Block inclusion verification
   - Transaction history persistence

### Per-Asset Specifications

**Ethereum/USDC**
- RPC: Infura, Alchemy, or self-hosted
- Signing: secp256k1 ECDSA
- Transaction Format: EIP-1559 (dynamic fees)
- Confirmation: 12 blocks (typical)
- Broadcasting: `eth_sendRawTransaction`
- Status: `eth_getTransactionReceipt`, `eth_blockNumber`

**Solana/USDC**
- RPC: Solana public RPC or private
- Signing: Ed25519
- Transaction Format: Message + signatures
- Confirmation: 1 confirmation (fast finality)
- Broadcasting: `sendTransaction` / `sendRawTransaction`
- Status: `getSignatureStatuses`, `getConfirmedTransaction`

**Stellar/USDC**
- Horizon API: https://horizon.stellar.org
- Signing: Ed25519
- Transaction Format: Envelope (base64-encoded XDR)
- Confirmation: 3-5 ledger closes (~15-30 seconds)
- Broadcasting: POST to `/transactions`
- Status: GET `/transactions/{hash}`

**Nano**
- RPC: Nano node (local or remote)
- Signing: Ed25519
- Transaction Format: State block
- Confirmation: 1+ blocks
- Broadcasting: `process` RPC call
- Status: `block_info`, `account_info`

**Arweave**
- Gateway: arweave.net or custom
- Signing: RSA-4096 PSS
- Transaction Format: JSON with signature
- Confirmation: Block inclusion (10+ minutes)
- Broadcasting: POST to `/tx`
- Status: GET `/tx/{id}/status`

### Implementation Steps

1. **Create Transaction Builder Module** (`blockchain/transaction_builder.py`)
   - `class TransactionBuilder` (base class)
   - Asset-specific subclasses for each blockchain
   - Methods: `build()`, `validate()`, `estimate_fee()`, `simulate()` (where available)

2. **Create Offline Signer Module** (`blockchain/offline_signer.py`)
   - `class OfflineSigner`
   - Per-asset signing implementations
   - Methods: `sign_transaction()`, `verify_signature()`, `get_signature_type()`

3. **Create Broadcaster Module** (`blockchain/broadcaster.py`)
   - `class Broadcaster`
   - Asset-specific RPC client wrappers
   - Methods: `broadcast()`, `get_status()`, `wait_confirmation()`, `retry_with_backoff()`

4. **Create Status Tracker Module** (`blockchain/transaction_tracker.py`)
   - `class TransactionTracker`
   - Methods: `track()`, `get_status()`, `is_confirmed()`, `list_pending()`
   - Persistent storage of transaction history

5. **Create Unified Transaction Manager** (`blockchain/transaction_manager.py`)
   - `class TransactionManager`
   - Methods: `prepare()`, `sign()`, `broadcast()`, `track()`
   - Orchestrates entire transaction lifecycle

6. **Integration with Existing Clients**
   - Update `nano_client.py` with signing
   - Update `arweave_client.py` with signing
   - Update `usdc_client.py` with multi-chain signing
   - Update `blockchain_manager.py` with transaction methods

7. **Unit Tests** (`tests/test_transaction_signing.py`)
   - Transaction builder validation
   - Signature correctness (against known vectors)
   - RPC communication mocking
   - Status tracking workflows
   - Error handling and retries

### Security Considerations
- Sign transactions offline (never expose private key to network)
- Verify transaction parameters before signing
- Use deterministic nonce management to prevent replay attacks
- Implement transaction simulation where available
- Clear sensitive data from memory after signing
- Log transaction metadata only (no private keys)
- Implement retry with exponential backoff to avoid DoS
- Rate-limit transaction submission attempts

### Dependencies
- Existing blockchain clients (`eth-account`, `solana.py`, `stellar-sdk`, etc.)
- `aiohttp>=3.8.0`: Async HTTP for RPC calls
- `tenacity>=8.0.0`: Retry logic
- `sqlalchemy>=2.0.0`: Transaction history storage (optional)

### Deliverables
- Per-asset transaction builders
- Secure offline signing without key exposure
- Robust broadcaster with retry logic
- Real-time transaction status tracking
- Transaction history persistence
- Comprehensive error handling

---

## Plan 4: Wallet Backup & Recovery System

### Objective
Implement secure wallet backup and recovery using BIP39 mnemonics, encrypted key exports, and social recovery mechanisms.

### Architecture

#### Core Components

1. **Mnemonic Backup**
   - BIP39 mnemonic generation and display
   - User confirmation flow
   - Checksum validation
   - Passphrase (25th word) support

2. **Physical Backup**
   - Mnemonic paper backup templates
   - QR code generation for offline scanning
   - Metal plate engraving recommendations
   - Multi-copy distribution guidance

3. **Encrypted Key Export**
   - Per-key encrypted export
   - Password-protected export files
   - Import/export versioning
   - Format compatibility across wallets

4. **Social Recovery**
   - Shamir Secret Sharing (SLIP-39)
   - Multi-signature recovery schemes
   - Threshold-based recovery (M-of-N)
   - Recovery contact management

5. **Recovery Flow**
   - Mnemonic-based wallet recovery
   - Multi-step verification
   - Account reconstruction
   - Balance verification post-recovery

### Backup Types

1. **Mnemonic Backup** (Recommended)
   - BIP39 12/24-word phrase
   - Optional passphrase (25th word)
   - Supports all BIP39/BIP44 wallets
   - Portable across wallet implementations

2. **Encrypted Key Backup**
   - Per-asset encrypted private key
   - Password-protected file
   - Portable JSON format
   - Timestamp and metadata included

3. **Social Recovery** (Advanced)
   - Shamir Secret Sharing
   - 3-of-5 threshold example
   - Recovery contact management
   - Time-locked recovery requests

### Implementation Steps

1. **Create Mnemonic Backup Module** (`blockchain/backup/mnemonic_backup.py`)
   - `class MnemonicBackup`
   - Methods: `generate()`, `validate()`, `display()`, `confirm_backup()`
   - Mnemonic display with user acknowledgment

2. **Create Key Export Module** (`blockchain/backup/key_export.py`)
   - `class KeyExporter`
   - Methods: `export_encrypted()`, `import_encrypted()`, `verify_import()`
   - Per-key encrypted export files

3. **Create Physical Backup Module** (`blockchain/backup/physical_backup.py`)
   - `class PhysicalBackupGenerator`
   - Methods: `generate_paper_template()`, `generate_qr_code()`, `generate_instructions()`
   - PDF generation for printing

4. **Create Social Recovery Module** (`blockchain/backup/social_recovery.py`)
   - `class SocialRecoveryManager`
   - Methods: `create_shares()`, `reconstruct()`, `manage_contacts()`
   - SLIP-39 implementation or `shamir` library

5. **Create Recovery Flow Module** (`blockchain/backup/recovery_flow.py`)
   - `class WalletRecovery`
   - Methods: `recover_from_mnemonic()`, `recover_from_backup()`, `recover_from_shares()`
   - Multi-step recovery with verification

6. **Create Backup Manager** (`blockchain/backup/backup_manager.py`)
   - `class BackupManager`
   - Orchestrates all backup types
   - Methods: `create_all_backups()`, `list_backups()`, `restore_backup()`

7. **UI Components** (`ui/backup_dialogs.py`)
   - Mnemonic display dialog with copy prevention
   - Backup confirmation flow
   - Recovery wizard
   - Backup management interface

8. **Unit Tests** (`tests/test_backup_recovery.py`)
   - Mnemonic generation and validation
   - BIP39 compliance tests
   - Key export/import correctness
   - Social recovery reconstruction
   - Full recovery workflow tests

### Security Considerations
- Display mnemonics only once at wallet creation
- Never re-display mnemonics after initial generation
- Prevent screenshot/copy of mnemonic display
- Store backups in separate, secure locations
- Encrypt all digital backups
- Validate checksums during recovery
- Implement time delays between recovery steps
- Log recovery events for audit trail
- Support passphrase-based additional security

### Dependencies
- `shamir>=2.0.0` or `slip39`: Secret sharing
- `qrcode>=7.4.0`: QR code generation
- `reportlab>=3.6.0`: PDF generation for backups
- Existing encryption modules from Plan 2

### Deliverables
- BIP39 mnemonic backup and recovery
- Encrypted key export/import
- Physical backup generation (PDF)
- Social recovery with secret sharing
- Complete recovery workflow
- Backup management UI

---

## Plan 5: Complete Wallet Management UI (PyQt6)

### Objective
Create a comprehensive, user-friendly PyQt6 desktop interface integrating all previous systems into a cohesive non-custodial wallet application.

### Architecture

#### Core Components

1. **Main Application Window**
   - Dashboard overview
   - Multi-wallet management
   - Status indicators (blockchain health)
   - Settings and preferences

2. **Wallet Management UI**
   - Create new wallet
   - Import existing wallet
   - List all wallets
   - Select active wallet
   - Wallet details and export

3. **Key Management UI**
   - Master password setup
   - Session management
   - Wallet unlock/lock
   - Key viewing (with warnings)

4. **Transaction UI**
   - Send transaction flow
   - Receive address display
   - Transaction history
   - Transaction status tracking
   - Fee estimation and adjustment

5. **Backup & Recovery UI**
   - Backup management
   - Mnemonic display with protection
   - Recovery wizard
   - Backup verification

6. **Settings & Security UI**
   - Network configuration
   - Security preferences
   - Backup settings
   - Session timeout
   - Theme and language

#### UI Layout

```
┌─ Main Window ────────────────────────┐
│  ┌─ Menu Bar ─────────────────────┐  │
│  │ File | Wallet | Backup | Tools │  │
│  └────────────────────────────────┘  │
│  ┌─ Status Bar ───────────────────┐  │
│  │ 🟢 Nano | 🟢 Arweave | 🔴 USDC │  │
│  └────────────────────────────────┘  │
│  ┌─ Dashboard ────────────────────┐  │
│  │ Wallet: [Dropdown]             │  │
│  │ Balance Overview               │  │
│  │ Recent Transactions            │  │
│  └────────────────────────────────┘  │
│  ┌─ Action Buttons ───────────────┐  │
│  │ [Send] [Receive] [Backup]      │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

### Key Dialogs & Workflows

**1. Wallet Creation Workflow**
```
1. Welcome Screen
2. Generate vs. Import Choice
3. Asset Selection (Nano/Arweave/USDC chains)
4. Entropy Display (if generating)
5. Mnemonic Backup & Confirmation
6. Master Password Setup
7. Wallet Ready - Dashboard
```

**2. Send Transaction Workflow**
```
1. Asset Selection
2. Recipient Address Input
3. Amount Input
4. Fee Display & Adjustment
5. Transaction Review
6. Master Password Unlock
7. Signature Confirmation
8. Broadcasting
9. Status Tracking
10. Completion Notification
```

**3. Wallet Recovery Workflow**
```
1. Recovery Method Selection (Mnemonic/Backup/Shares)
2. Input Recovery Data
3. Master Password Setup
4. Recovery Validation
5. Balance Verification
6. Completion
```

### Implementation Steps

1. **Create Main Application** (`ui/main_window.py`)
   - `class SapphireExchangeApp(QMainWindow)`
   - Setup main UI structure
   - Connect blockchain manager
   - Initialize components

2. **Create Dashboard Widget** (`ui/dashboard_widget.py`)
   - `class DashboardWidget(QWidget)`
   - Wallet overview
   - Balance display per asset
   - Recent transactions
   - Quick action buttons

3. **Create Wallet Management Dialog** (`ui/wallet_dialogs.py`)
   - `class CreateWalletDialog(QDialog)`
   - `class ImportWalletDialog(QDialog)`
   - `class WalletListDialog(QDialog)`
   - Wallet creation/import/selection flows

4. **Create Key Management Dialog** (`ui/key_management_dialog.py`)
   - `class MasterPasswordDialog(QDialog)`
   - `class SessionManagerWidget(QWidget)`
   - `class UnlockDialog(QDialog)`
   - Password setup and session management

5. **Create Transaction Dialog** (`ui/transaction_dialogs.py`)
   - `class SendDialog(QDialog)`
   - `class ReceiveDialog(QDialog)`
   - `class TransactionHistoryWidget(QWidget)`
   - `class FeeEstimatorWidget(QWidget)`

6. **Create Backup Dialog** (`ui/backup_dialogs.py`)
   - `class MnemonicDisplayDialog(QDialog)`
   - `class BackupWizardDialog(QDialog)`
   - `class RecoveryWizardDialog(QDialog)`

7. **Create Settings Dialog** (`ui/settings_dialog.py`)
   - `class SettingsDialog(QDialog)`
   - Network configuration
   - Security preferences
   - Theme and language

8. **Create Status/Health Monitor** (`ui/status_monitor.py`)
   - `class StatusWidget(QWidget)`
   - Real-time blockchain health
   - Connection indicators
   - Error notifications

9. **Create Custom Widgets** (`ui/custom_widgets.py`)
   - `class AddressDisplayWidget`: Safe address display with copy button
   - `class BalanceWidget`: Formatted balance display
   - `class TransactionListWidget`: Transaction history
   - `class QRCodeWidget`: QR code display

10. **Create Async Task Manager** (`ui/async_tasks.py`)
    - Async operations without blocking UI
    - Progress dialogs
    - Error handling and user feedback

11. **Create Styles & Themes** (`ui/styles.py`)
    - Light/dark theme support
    - Custom color schemes
    - Responsive design
    - Accessibility features

12. **Integration with Plans 1-4**
    - Connect wallet generator from Plan 1
    - Use key storage from Plan 2
    - Integrate transaction signing from Plan 3
    - Use backup/recovery from Plan 4

13. **Unit & Integration Tests** (`tests/test_ui.py`)
    - Dialog workflow tests
    - User interaction simulation
    - Async operation tests
    - Error handling validation

### UI/UX Best Practices

1. **Security**
   - Never display full private keys in main UI
   - Use color warnings for destructive actions
   - Require confirmation for sensitive operations
   - Session timeouts with lock screen

2. **Accessibility**
   - Clear, readable fonts
   - High contrast mode option
   - Keyboard navigation support
   - Screen reader compatibility

3. **Feedback**
   - Clear error messages with solutions
   - Progress indicators for long operations
   - Success notifications
   - Transaction status updates

4. **Design Patterns**
   - Consistent button placement
   - Clear data flow visualization
   - Logical grouping of controls
   - Responsive to window resizing

### Design Specifications

**Color Scheme**
- Primary: #2E86AB (Blue)
- Secondary: #A23B72 (Purple)
- Success: #06A77D (Green)
- Warning: #F18F01 (Orange)
- Error: #C1121F (Red)
- Background: #F4F1DE (Light) / #1A1A1A (Dark)

**Typography**
- Title: 16pt Bold
- Regular: 11pt Regular
- Monospace (addresses): 10pt Monaco/Courier

**Icon Set**
- Use Material Design Icons
- Size: 24x24 px standard
- Color consistency with theme

### Dependencies
- `PyQt6>=6.0.0`: GUI framework
- `qasync>=0.23.0`: Async support
- `pyqtgraph>=0.13.0`: Charts (optional)
- `material-design-icons`: Icon library

### Deliverables
- Main application window with dashboard
- Complete wallet management UI
- Transaction sending/receiving dialogs
- Backup and recovery wizards
- Settings and security management
- Real-time blockchain status monitoring
- Responsive, accessible, secure interface
- Comprehensive user documentation

---

## Integration & Testing Strategy

### Cross-Plan Integration
1. Plan 1 → Plan 2: Store generated keys using secure storage
2. Plan 2 → Plan 3: Retrieve keys for signing
3. Plan 3 → Plan 4: Store transaction history for recovery
4. Plan 4 → Plan 5: Display backup/recovery options in UI
5. Plan 5 integrates all: UI orchestrates all systems

### Testing Pyramid
```
         UI Tests (Plan 5)
        /              \
   Integration Tests (Plans 1-5)
      /                    \
  Unit Tests (Plans 1-4 + helpers)
```

### Test Data & Vectors
- Known BIP39 test vectors
- Known transaction signatures
- Mock blockchain responses
- Fixture wallets for testing

### Security Auditing
- Code review checklist
- Vulnerability scanning
- Dependency auditing
- Penetration testing guidance

---

## Implementation Timeline (Recommended Order)

1. **Phase 1** (Week 1-2): Plan 1 (Wallet Generation)
2. **Phase 2** (Week 3-4): Plan 2 (Key Storage)
3. **Phase 3** (Week 5-6): Plan 3 (Transaction Signing)
4. **Phase 4** (Week 7-8): Plan 4 (Backup & Recovery)
5. **Phase 5** (Week 9-10): Plan 5 (UI Integration)
6. **Phase 6** (Week 11-12): Testing & Polish

---

## File Structure After Implementation

```
sapphire_exchange/
├── blockchain/
│   ├── entropy_generator.py
│   ├── bip39_derivation.py
│   ├── unified_wallet_generator.py
│   ├── wallet_generators/
│   │   ├── ethereum_generator.py
│   │   ├── solana_generator.py
│   │   ├── stellar_generator.py
│   │   ├── nano_generator.py
│   │   └── arweave_generator.py
│   ├── offline_signer.py
│   ├── broadcaster.py
│   ├── transaction_builder.py
│   ├── transaction_tracker.py
│   ├── transaction_manager.py
│   ├── backup/
│   │   ├── mnemonic_backup.py
│   │   ├── key_export.py
│   │   ├── physical_backup.py
│   │   ├── social_recovery.py
│   │   ├── recovery_flow.py
│   │   └── backup_manager.py
│   ├── nano_client.py (updated)
│   ├── arweave_client.py (updated)
│   ├── usdc_client.py (updated)
│   └── blockchain_manager.py (updated)
├── security/
│   ├── password_manager.py
│   ├── vault_encryption.py
│   ├── key_storage.py
│   ├── session_manager.py
│   ├── keyring_backend.py
│   └── backup_manager.py
├── ui/
│   ├── main_window.py
│   ├── dashboard_widget.py
│   ├── wallet_dialogs.py
│   ├── key_management_dialog.py
│   ├── transaction_dialogs.py
│   ├── backup_dialogs.py
│   ├── settings_dialog.py
│   ├── status_monitor.py
│   ├── custom_widgets.py
│   ├── async_tasks.py
│   └── styles.py
├── tests/
│   ├── test_wallet_generation.py
│   ├── test_key_storage.py
│   ├── test_transaction_signing.py
│   ├── test_backup_recovery.py
│   ├── test_ui.py
│   └── fixtures/
│       ├── test_vectors.json
│       └── mock_responses.json
├── app.py (updated)
├── requirements.txt (updated)
└── IMPLEMENTATION_PLANS.md (this file)
```

---

## Summary

These 5 plans provide a modular, production-grade wallet implementation:

1. **Wallet Generation**: Secure offline wallet creation with entropy validation
2. **Key Storage**: Military-grade encryption with master password protection
3. **Transaction Signing**: Secure offline signing with online broadcasting
4. **Backup & Recovery**: Multi-method recovery from loss or compromise
5. **UI**: Comprehensive PyQt6 interface for all wallet operations

Each plan is independently implementable while maintaining compatibility with the others. Follow the recommended timeline for optimal workflow.
