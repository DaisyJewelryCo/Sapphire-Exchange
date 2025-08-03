---
description: Repository Information Overview
alwaysApply: true
---

# Sapphire Exchange Information

## Summary
Sapphire Exchange is a decentralized auction platform built on Arweave and Nano blockchains. It enables users to list, bid on, and purchase items with secure blockchain transactions. The application provides decentralized storage on Arweave, fast and feeless Nano transactions, secure wallet management, and a timed auction system.

## Structure
- **app.py**: Main application entry point
- **main_window.py**: PyQt5-based UI implementation
- **models.py**: Data models for users, items, and auctions
- **database.py**: Database module using Arweave for storage
- **arweave_utils.py**: Handles interactions with Arweave blockchain
- **nano_utils.py**: Manages Nano wallet and transaction functionality
- **decentralized_client.py**: Client for interacting with blockchain networks
- **mock_servers.py**: Mock implementations for testing without real blockchain
- **test_marketplace.py**: Test script for verifying marketplace functionality

## Language & Runtime
**Language**: Python
**Version**: 3.7+
**Build System**: pip (Python package manager)
**Package Manager**: pip

## Dependencies
**Main Dependencies**:
- PyArweave==0.6.0: Arweave blockchain integration
- python-dotenv>=0.19.2: Environment variable management
- requests>=2.28.0: HTTP requests
- base58>=2.1.1: Base58 encoding/decoding
- cryptography>=3.4.7: Cryptographic operations
- ed25519-blake2b==1.4.1: Digital signatures
- pynacl>=1.4.0: Cryptographic library
- pycryptodome>=3.20.0: Cryptographic primitives
- PyQt5>=5.15.9: GUI framework
- qrcode>=7.4.2: QR code generation
- Pillow>=9.5.0: Image processing

**Development Dependencies**:
- Not explicitly specified in requirements.txt

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
**Framework**: Custom testing with mock implementations
**Test Location**: test_marketplace.py
**Mock Implementation**: mock_servers.py provides simulated blockchain environments
**Run Command**:
```bash
python test_marketplace.py
```

## Features
- **Decentralized Storage**: Item data stored on Arweave blockchain
- **Nano Integration**: Fast, feeless Nano transactions for bidding and purchasing
- **Secure Wallet Management**: Built-in wallet generation and management
- **Auction System**: Support for timed auctions with automatic finalization
- **Mock Mode**: Testing environment that simulates blockchain operations
- **PyQt5 GUI**: Desktop application interface for user interaction