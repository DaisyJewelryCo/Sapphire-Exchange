# Sapphire Exchange - Unified Architecture

## Overview
Sapphire Exchange is a decentralized auction platform built with PyQt5, integrating Nano, Arweave, and Dogecoin blockchains. The architecture follows a layered approach with clear separation of concerns.

## Architecture Layers

### 1. Presentation Layer (UI)
- **main_window.py** - Main application window and navigation
- **auction_widget.py** - Auction listing and bidding interface
- **wallet_widget.py** - Multi-currency wallet management
- **ui/** - Additional UI components and dialogs

### 2. Application Layer (Business Logic)
- **services/** - Business logic services
  - **auction_service.py** - Auction management and bidding logic
  - **wallet_service.py** - Multi-currency wallet operations
  - **user_service.py** - User management and authentication
  - **price_service.py** - Currency conversion and pricing

### 3. Integration Layer (Blockchain Clients)
- **blockchain/** - Unified blockchain integration
  - **nano_client.py** - Nano blockchain operations
  - **arweave_client.py** - Arweave storage operations
  - **dogecoin_client.py** - Dogecoin wallet operations
  - **blockchain_manager.py** - Unified blockchain interface

### 4. Data Layer
- **models.py** - Data models (User, Item, Bid, Auction)
- **database.py** - Arweave-based storage with caching
- **repositories/** - Data access patterns
  - **user_repository.py**
  - **item_repository.py**
  - **bid_repository.py**

### 5. Infrastructure Layer
- **config/** - Configuration management
  - **blockchain_config.py** - Blockchain network settings
  - **app_config.py** - Application configuration
- **utils/** - Utility functions
  - **crypto_utils.py** - Cryptographic operations
  - **validation_utils.py** - Data validation
  - **conversion_utils.py** - Currency conversions
- **security/** - Security components
  - **security_manager.py** - Security policies
  - **encryption_manager.py** - Data encryption

## Key Design Principles

### 1. Single Responsibility
Each module has a clear, single responsibility:
- UI components handle presentation only
- Services contain business logic
- Clients handle blockchain communication
- Repositories manage data access

### 2. Dependency Injection
Services and clients are injected as dependencies, enabling:
- Easy testing with mocks
- Runtime configuration switching
- Clean separation of concerns

### 3. Event-Driven Architecture
Components communicate through events:
- UI emits user actions
- Services emit business events
- Blockchain clients emit transaction events

### 4. Multi-Currency Support
Native support for DOGE, NANO, and USD:
- Unified pricing interface
- Real-time conversion rates
- Consistent display formatting

### 5. Data Integrity
Multiple layers of data verification:
- Cryptographic hashing
- Blockchain confirmation tracking
- RSA signature verification

## Component Interactions

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   UI Layer      │    │  Service Layer  │    │ Blockchain Layer│
│                 │    │                 │    │                 │
│ MainWindow      │◄──►│ AuctionService  │◄──►│ NanoClient      │
│ AuctionWidget   │    │ WalletService   │    │ ArweaveClient   │
│ WalletWidget    │    │ UserService     │    │ DogecoinClient  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Layer    │    │ Infrastructure  │    │   Config Layer  │
│                 │    │                 │    │                 │
│ Models          │    │ SecurityManager │    │ BlockchainConfig│
│ Database        │    │ PerformanceManager   │ AppConfig       │
│ Repositories    │    │ CryptoUtils     │    │ Environment     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## File Organization

```
sapphire_exchange/
├── app.py                      # Application entry point
├── main_window.py              # Main UI window
├── models.py                   # Data models
├── database.py                 # Arweave storage layer
├── config/
│   ├── __init__.py
│   ├── app_config.py          # Application configuration
│   └── blockchain_config.py    # Blockchain settings
├── services/
│   ├── __init__.py
│   ├── auction_service.py     # Auction business logic
│   ├── wallet_service.py      # Wallet operations
│   ├── user_service.py        # User management
│   └── price_service.py       # Currency pricing
├── blockchain/
│   ├── __init__.py
│   ├── blockchain_manager.py  # Unified blockchain interface
│   ├── nano_client.py         # Nano operations
│   ├── arweave_client.py      # Arweave operations
│   └── dogecoin_client.py     # Dogecoin operations
├── repositories/
│   ├── __init__.py
│   ├── base_repository.py     # Base repository pattern
│   ├── user_repository.py     # User data access
│   ├── item_repository.py     # Item data access
│   └── bid_repository.py      # Bid data access
├── ui/
│   ├── __init__.py
│   ├── auction_widget.py      # Auction interface
│   ├── wallet_widget.py       # Wallet interface
│   └── dialogs/               # UI dialogs
├── utils/
│   ├── __init__.py
│   ├── crypto_utils.py        # Cryptographic utilities
│   ├── validation_utils.py    # Data validation
│   └── conversion_utils.py    # Currency conversions
├── security/
│   ├── __init__.py
│   ├── security_manager.py    # Security policies
│   └── encryption_manager.py  # Data encryption
└── tests/
    ├── __init__.py
    ├── test_services/
    ├── test_blockchain/
    └── test_repositories/
```

## Configuration Management

### Environment Variables
Based on robot_info.json specifications:
- `ARWEAVE_GATEWAY_URL` - Arweave gateway endpoint
- `ARWEAVE_WALLET_FILE` - Arweave wallet file path
- `NANO_NODE_URL` - Nano RPC endpoint
- `NANO_REPRESENTATIVE` - Default Nano representative
- `DOGECOIN_NETWORK` - Dogecoin network (mainnet/testnet)
- `MOCK_MODE` - Enable mock blockchain clients for testing

### Configuration Hierarchy
1. Environment variables (highest priority)
2. Configuration files
3. Default values from robot_info.json

## Security Architecture

### Data Protection
- Sensitive data encrypted at rest
- Private keys never stored in plaintext
- Session-based authentication with timeouts

### Blockchain Security
- Multi-signature verification
- Transaction confirmation tracking
- RSA signature validation for Arweave data

### Network Security
- Rate limiting for API calls
- Request timeout management
- Retry logic with exponential backoff

## Performance Optimization

### Caching Strategy
- In-memory cache for frequently accessed data
- TTL-based cache invalidation (5 minutes default)
- Batch operations for bulk data access

### Async Operations
- Non-blocking blockchain operations
- Background data synchronization
- Responsive UI during network operations

### Resource Management
- Connection pooling for blockchain clients
- Memory-efficient data structures
- Garbage collection optimization

## Testing Strategy

### Unit Tests
- Service layer business logic
- Utility functions
- Data model validation

### Integration Tests
- Blockchain client operations
- Database storage and retrieval
- End-to-end auction workflows

### Mock Implementation
- Mock blockchain clients for development
- Simulated network conditions
- Test data generation

## Deployment Considerations

### Dependencies
- Python 3.7+ runtime
- PyQt5 for desktop UI
- Blockchain client libraries
- Cryptographic libraries

### Configuration
- Environment-specific settings
- Blockchain network selection
- Performance tuning parameters

### Monitoring
- Application health checks
- Blockchain connection status
- Performance metrics collection