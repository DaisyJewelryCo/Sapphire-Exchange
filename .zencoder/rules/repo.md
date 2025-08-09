---
description: Repository Information Overview
alwaysApply: true
---

# Sapphire Exchange Information

## Summary
Sapphire Exchange is a decentralized auction platform built on Arweave, Nano, and Dogecoin blockchains. It enables users to list, bid on, and purchase items with secure blockchain transactions. The application provides decentralized storage on Arweave, fast and feeless Nano transactions, secure wallet management, and a timed auction system.

## Structure
- **app.py**: Main application entry point with PyQt5 GUI initialization
- **ui/**: PyQt5-based user interface components and dialogs
- **models/**: Data models for users, items, and auctions
- **services/**: Business logic services for users, auctions, wallets, etc.
- **blockchain/**: Blockchain client implementations for Arweave, Nano, and Dogecoin
- **repositories/**: Data access layer for persistent storage
- **utils/**: Utility functions for validation, conversion, and async operations
- **security/**: Security and performance management components
- **config/**: Application and blockchain configuration

## Language & Runtime
**Language**: Python
**Version**: 3.7+
**Build System**: pip (Python package manager)
**Package Manager**: pip

## Dependencies
**Main Dependencies**:
- PyQt5>=5.15.9: GUI framework
- qasync>=0.23.0: Async support for PyQt5
- PyArweave>=0.6.0: Arweave blockchain integration
- cryptography>=3.4.7: Cryptographic operations
- ed25519-blake2b>=1.4.1: Digital signatures
- pynacl>=1.4.0: Cryptographic library
- mnemonic>=0.20: BIP39 wallet support
- hdwallet>=2.2.1: Hierarchical deterministic wallet
- python-dotenv>=0.19.2: Environment variable management
- qrcode>=7.4.2: QR code generation

**Development Dependencies**:
- pytest>=7.0.0: Testing framework
- pytest-asyncio>=0.21.0: Async testing support
- pytest-mock>=3.10.0: Mocking for tests
- black>=22.0.0: Code formatting
- flake8>=5.0.0: Code linting

## Build & Installation
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
# Create .env file with:
# ARWEAVE_GATEWAY_URL=https://arweave.net
# ARWEAVE_WALLET_FILE=wallet.json
# NANO_NODE_URL=https://mynano.ninja/api
# NANO_REPRESENTATIVE=nano_3t6k35gi95xu6tergt6p69ck76ogmitsa8mnijtpxm9fkcm736xtoncuohr3
```

## Usage
```bash
# Run the application
python app.py
```

## Testing
**Framework**: pytest with unittest
**Test Files**: 
- test_unified_system.py: Comprehensive test suite for all components
- test_dev_tools.py: Development tools testing
- test_refactoring.py: Tests for refactored components
- test_seed_dialog.py: Tests for seed phrase dialog

**Run Command**:
```bash
pytest
```

## Features
- **Decentralized Storage**: Item data stored on Arweave blockchain
- **Multi-Blockchain Support**: Integration with Arweave, Nano, and Dogecoin
- **Secure Wallet Management**: BIP39 seed phrase generation and HD wallet support
- **Auction System**: Support for timed auctions with automatic finalization
- **Asynchronous Architecture**: Non-blocking UI with asyncio and qasync
- **Security**: Encryption, hashing, and secure key management
- **Performance Optimization**: Caching and performance monitoring