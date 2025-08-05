# Sapphire Exchange Architecture Migration Guide

## Overview
This guide explains the changes made to unify the Sapphire Exchange architecture.

## Major Changes

### 1. Directory Structure
- `config/` - Configuration management
- `services/` - Business logic services
- `blockchain/` - Unified blockchain clients
- `repositories/` - Data access layer
- `ui/` - User interface components
- `utils/` - Utility functions
- `security/` - Security components

### 2. Consolidated Files
- Multiple `nano_utils*.py` files → `blockchain/nano_client.py`
- Multiple `arweave_utils*.py` files → `blockchain/arweave_client.py`
- `dogecoin_utils.py` → `blockchain/dogecoin_client.py`
- `blockchain_config.py` → `config/blockchain_config.py`

### 3. New Components
- `blockchain/blockchain_manager.py` - Unified blockchain interface
- `config/app_config.py` - Application configuration
- `services/auction_service.py` - Auction business logic
- `ARCHITECTURE.md` - Detailed architecture documentation

### 4. Import Changes
Update your imports:
```python
# Old
from auction_widget import AuctionWidget
from blockchain_config import config

# New
from ui.auction_widget import AuctionWidget
from config.blockchain_config import blockchain_config
```

### 5. Configuration Changes
- Environment variables remain the same
- Configuration is now centralized in `config/` package
- Mock mode is controlled via `MOCK_MODE` environment variable

### 6. Testing
- Mock implementations are integrated into clients
- Set `MOCK_MODE=true` for testing without real blockchain connections
- All clients support both real and mock modes

## Migration Steps

1. Update imports in your code
2. Install new dependencies: `pip install -r requirements_new.txt`
3. Update environment variables if needed
4. Test with mock mode first: `MOCK_MODE=true python app.py`
5. Configure real blockchain connections for production

## Benefits

- **Cleaner Architecture**: Clear separation of concerns
- **Better Testing**: Integrated mock implementations
- **Easier Maintenance**: Consolidated functionality
- **Improved Configuration**: Centralized settings management
- **Enhanced Security**: Dedicated security components
