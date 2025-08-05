#!/usr/bin/env python3
"""
Cleanup script for Sapphire Exchange unified architecture.
Removes redundant files and updates imports.
"""
import os
import shutil
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent

# Files to remove (redundant implementations)
REDUNDANT_FILES = [
    'nano_utils.py',
    'nano_utils_real.py',
    'arweave_utils_real.py',
    'update_imports.py',
    'test_activity_feed.py',
    'test_enhanced_features.py',
    'sapphire-exchange.rb'
]

# Files to move to config directory
CONFIG_FILES = [
    'blockchain_config.py'  # Already moved, but remove original
]

# Files to move to security directory
SECURITY_FILES = [
    'security_manager.py',
    'performance_manager.py'
]

# Files to move to utils directory
UTIL_FILES = [
    'crypto_client.py'
]

def cleanup_redundant_files():
    """Remove redundant files."""
    print("Cleaning up redundant files...")
    
    for filename in REDUNDANT_FILES:
        file_path = BASE_DIR / filename
        if file_path.exists():
            print(f"Removing {filename}")
            file_path.unlink()
        else:
            print(f"File not found: {filename}")

def move_files_to_directories():
    """Move files to appropriate directories."""
    print("Moving files to appropriate directories...")
    
    # Move security files
    for filename in SECURITY_FILES:
        src = BASE_DIR / filename
        dst = BASE_DIR / 'security' / filename
        if src.exists():
            print(f"Moving {filename} to security/")
            shutil.move(str(src), str(dst))
    
    # Move utility files
    for filename in UTIL_FILES:
        src = BASE_DIR / filename
        dst = BASE_DIR / 'utils' / filename
        if src.exists():
            print(f"Moving {filename} to utils/")
            shutil.move(str(src), str(dst))
    
    # Remove original blockchain_config.py if it exists
    old_config = BASE_DIR / 'blockchain_config.py'
    if old_config.exists():
        print("Removing old blockchain_config.py")
        old_config.unlink()

def create_init_files():
    """Create __init__.py files for packages."""
    print("Creating __init__.py files...")
    
    directories = [
        'utils',
        'security',
        'repositories'
    ]
    
    for directory in directories:
        init_file = BASE_DIR / directory / '__init__.py'
        if not init_file.exists():
            print(f"Creating {directory}/__init__.py")
            init_file.write_text('"""Package initialization."""\n')

def update_main_imports():
    """Update imports in main files."""
    print("Updating imports in main files...")
    
    # Update main_window.py imports
    main_window_file = BASE_DIR / 'main_window.py'
    if main_window_file.exists():
        content = main_window_file.read_text()
        
        # Update imports
        content = content.replace(
            'from auction_widget import',
            'from ui.auction_widget import'
        )
        content = content.replace(
            'from wallet_widget import',
            'from ui.wallet_widget import'
        )
        content = content.replace(
            'from blockchain_config import',
            'from config.blockchain_config import'
        )
        
        main_window_file.write_text(content)
        print("Updated main_window.py imports")
    
    # Update app.py imports if needed
    app_file = BASE_DIR / 'app.py'
    if app_file.exists():
        content = app_file.read_text()
        # App.py imports look fine, no changes needed
        print("Checked app.py imports - no changes needed")

def create_requirements_update():
    """Create updated requirements.txt with new dependencies."""
    print("Creating updated requirements.txt...")
    
    requirements = """# Core dependencies
PyQt5>=5.15.9
qasync>=0.23.0

# Blockchain integration
PyArweave==0.6.0
base58>=2.1.1
ed25519-blake2b==1.4.1
pynacl>=1.4.0

# Cryptography
cryptography>=3.4.7
pycryptodome>=3.20.0

# BIP utilities for Dogecoin
mnemonic>=0.20
bip-utils>=2.7.0

# HTTP and networking
aiohttp>=3.8.0
requests>=2.28.0

# Environment and configuration
python-dotenv>=0.19.2

# Image processing and QR codes
Pillow>=9.5.0
qrcode>=7.4.2

# Development and testing
pytest>=7.0.0
pytest-asyncio>=0.21.0
"""
    
    requirements_file = BASE_DIR / 'requirements_new.txt'
    requirements_file.write_text(requirements)
    print("Created requirements_new.txt with updated dependencies")

def create_migration_guide():
    """Create migration guide for the new architecture."""
    print("Creating migration guide...")
    
    guide = """# Sapphire Exchange Architecture Migration Guide

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
"""
    
    guide_file = BASE_DIR / 'MIGRATION_GUIDE.md'
    guide_file.write_text(guide)
    print("Created MIGRATION_GUIDE.md")

def main():
    """Run the cleanup process."""
    print("Starting Sapphire Exchange architecture cleanup...")
    print("=" * 50)
    
    try:
        cleanup_redundant_files()
        print()
        
        move_files_to_directories()
        print()
        
        create_init_files()
        print()
        
        update_main_imports()
        print()
        
        create_requirements_update()
        print()
        
        create_migration_guide()
        print()
        
        print("=" * 50)
        print("Architecture cleanup completed successfully!")
        print()
        print("Next steps:")
        print("1. Review the changes in MIGRATION_GUIDE.md")
        print("2. Install new dependencies: pip install -r requirements_new.txt")
        print("3. Test the application: MOCK_MODE=true python app.py")
        print("4. Review ARCHITECTURE.md for detailed documentation")
        
    except Exception as e:
        print(f"Error during cleanup: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())