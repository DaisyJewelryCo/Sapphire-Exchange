---
description: Repository Information Overview
alwaysApply: true
---

# Sapphire Exchange Information

## Summary
Sapphire Exchange is a decentralized auction platform with a PyQt5 desktop GUI that integrates multiple blockchains (Arweave for storage, Nano/Dogecoin for payments, and Solana USDC). The application enables secure item listing, bidding, and purchasing with blockchain-backed transactions. It features wallet management with BIP39 seed phrases, hierarchical deterministic wallets, and comprehensive security measures.

## Structure
- **app.py**: Main application entry point with PyQt5 and qasync initialization
- **ui/**: PyQt5 GUI components (main window, dialogs, widgets, login screen)
- **ui/dialogs/**: Specialized dialogs (seed phrases, wallet management, settings, backups)
- **services/**: Business logic layer (application, auction, user, wallet, price conversion)
- **models/**: Data models (User, Item, Bid, Transaction)
- **repositories/**: Data access layer for persistent storage and database operations
- **blockchain/**: Blockchain client implementations (Arweave, Nano, Dogecoin, Solana/USDC)
- **blockchain/wallet_generators/**: Specialized wallet generation for each blockchain
- **blockchain/backup/**: Backup and recovery mechanisms (mnemonic, physical, social)
- **config/**: Application and blockchain configuration with security/performance parameters
- **security/**: Security management (encryption, key storage, password hashing, sessions)
- **utils/**: Utility functions (validation, conversion, async helpers, viewers)
- **schemas/**: JSON schemas for data validation

## Language & Runtime
**Language**: Python  
**Version**: 3.7+  
**Build System**: pip (Python package manager)  
**Package Manager**: pip  
**GUI Framework**: PyQt5 with qasync for async support

## Dependencies

**Main Dependencies**:
- **PyQt5** (>=5.15.9): Desktop GUI framework
- **qasync** (>=0.23.0): Async/await support for PyQt5
- **PyArweave** (>=0.6.0): Arweave blockchain integration
- **solana** (>=0.30.0): Solana blockchain integration
- **cryptography** (>=3.4.7): Cryptographic operations
- **pynacl** (>=1.4.0): Cryptographic library (Nacl)
- **ed25519-blake2b** (>=1.4.1): Digital signatures for Nano
- **mnemonic** (>=0.20): BIP39 seed phrase support
- **hdwallet** (>=2.2.1): Hierarchical deterministic wallet management
- **bip32** (>=3.4): BIP32 derivation
- **ecdsa** (>=0.18.0): Elliptic curve cryptography
- **pycryptodome** (>=3.20.0): Enhanced crypto library
- **base58** (>=2.1.1): Base58 encoding/decoding
- **argon2-cffi** (>=23.0.0): Argon2 password hashing
- **requests** (>=2.28.0): HTTP client
- **aiohttp** (>=3.8.0): Async HTTP client
- **httpx** (>=0.24.0): Modern HTTP client
- **python-dotenv** (>=0.19.2): Environment configuration
- **qrcode** (>=7.4.2): QR code generation
- **Pillow** (>=9.5.0): Image processing
- **dataclasses-json** (>=0.5.7): JSON serialization for dataclasses
- **asyncpg** (>=0.29.0): PostgreSQL async driver
- **psycopg2-binary** (>=2.9.0): PostgreSQL driver
- **psutil** (>=5.9.0): System utilities for monitoring
- **structlog** (>=22.0.0): Structured logging

**Development Dependencies**:
- **pytest** (>=7.0.0): Testing framework
- **pytest-asyncio** (>=0.21.0): Async test support
- **pytest-mock** (>=3.10.0): Mocking support for tests
- **black** (>=22.0.0): Code formatter
- **flake8** (>=5.0.0): Linting tool

## Build & Installation

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables (.env file)
ARWEAVE_GATEWAY_URL=https://arweave.net
ARWEAVE_WALLET_FILE=wallet.json
NANO_NODE_URL=https://mynano.ninja/api
NANO_REPRESENTATIVE=nano_3t6k35gi95xu6tergt6p69ck76ogmitsa8mnijtpxm9fkcm736xtoncuohr3
```

## Usage

```bash
# Run the application
python app.py
```

## Testing

**Framework**: pytest with unittest  
**Test Files**:
- `test_unified_system.py`: Comprehensive system test suite
- `tests/test_ui_components.py`: UI component tests
- `tests/test_transaction_signing.py`: Transaction and signing tests

**Test Configuration**: Uses mocking for database and blockchain operations with `unittest.mock`

**Run Command**:
```bash
pytest
```

## Key Components

### Blockchain Integration
- **Arweave Client**: Permanent data storage with JSON transactions
- **Nano Client**: Feeless cryptocurrency transactions with wallet management
- **Dogecoin Client**: Payment integration with HD wallet support
- **USDC/Solana Client**: Token-based transactions on Solana chain
- **Unified Wallet Generator**: Multi-blockchain wallet creation with BIP39 support

### Services
- **ApplicationService**: Orchestrates all components with unified interface
- **AuctionService**: Manages auctions, bids, and finalization
- **UserService**: User management and authentication
- **WalletService**: Wallet operations and balance tracking
- **PriceConversionService**: Real-time price conversion via CoinGecko API
- **ArweavePostService**: Data posting to Arweave network

### Security
- **SecurityManager**: Password hashing (PBKDF2-HMAC-SHA256), session management
- **PasswordManager**: Secure password handling
- **KeyStorage**: Encrypted key management with keyring backend
- **VaultEncryption**: Encrypted vault for sensitive data
- **SessionManager**: Session timeout and activity tracking (120 min timeout, 30 min inactivity)
- **BackupManager**: Backup and recovery for wallet seeds

### Configuration
- **AppConfig**: UI constants, security parameters, performance tuning
- **BlockchainConfig**: Chain-specific settings (Nano, Arweave, USDC, Dogecoin)
- **Rate Limiting**: 60 requests/minute with 10-burst capacity
- **Performance**: 5-minute cache TTL, 10 concurrent requests max, 30s timeout
- **Currency**: Primary currency is DOGE with toggle to USD via CoinGecko

### Database
- **DatabaseAdapter**: Abstraction layer for database operations
- **Repositories**: User, Item, Bid repositories for data persistence
- **Models**: User, Item, Bid, Transaction dataclasses with serialization

## Architecture Highlights

**Multi-Blockchain Support**: Seamless integration with 4+ blockchains for different use cases  
**Async Architecture**: Non-blocking UI with asyncio and qasync  
**Security-First**: Encryption at rest, secure key derivation, rate limiting  
**Performance Optimized**: Caching, batch processing, async database operations  
**Clean Separation**: Services, repositories, models, and UI clearly separated  
**Configuration Driven**: Externalized settings for easy customization  
**Comprehensive Testing**: Unit and integration tests with mocking support
