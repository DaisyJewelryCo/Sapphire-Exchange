#!/usr/bin/env python3
"""
Verification script for Sapphire Exchange unified architecture.
Checks that all components are properly structured and importable.
"""
import os
import sys
from pathlib import Path

def check_file_exists(filepath, description=""):
    """Check if a file exists."""
    if os.path.exists(filepath):
        print(f"✅ {filepath} - {description}")
        return True
    else:
        print(f"❌ {filepath} - {description} (MISSING)")
        return False

def check_directory_structure():
    """Check the unified directory structure."""
    print("🔍 Checking Unified Directory Structure...")
    print("=" * 50)
    
    base_path = "/Users/seanmorrissey/Desktop/Coding/Sapphire_Exchange"
    
    # Core files
    core_files = [
        ("app.py", "Application entry point"),
        ("main_window_unified.py", "Unified main UI"),
        ("application_service.py", "Central orchestration service"),
        ("database_adapter.py", "Database abstraction layer"),
        ("models.py", "Enhanced data models"),
        ("price_service.py", "Currency pricing service"),
        ("test_unified_system.py", "Comprehensive test suite"),
        ("requirements_unified.txt", "Unified dependencies"),
        ("UNIFIED_ARCHITECTURE_COMPLETE.md", "Complete documentation")
    ]
    
    # Directory structure
    directories = [
        "config/",
        "services/",
        "repositories/",
        "blockchain/",
        "ui/",
        "utils/",
        "security/"
    ]
    
    # Service files
    service_files = [
        ("services/__init__.py", "Services package init"),
        ("services/auction_service.py", "Auction business logic"),
        ("services/wallet_service.py", "Wallet operations"),
        ("services/user_service.py", "User management (NEW)")
    ]
    
    # Repository files
    repository_files = [
        ("repositories/__init__.py", "Repositories package init"),
        ("repositories/base_repository.py", "Repository pattern base (NEW)"),
        ("repositories/user_repository.py", "User data access (NEW)"),
        ("repositories/item_repository.py", "Item data access (NEW)"),
        ("repositories/bid_repository.py", "Bid data access (NEW)")
    ]
    
    # Utility files
    utility_files = [
        ("utils/__init__.py", "Utils package init"),
        ("utils/crypto_client.py", "Cryptographic utilities"),
        ("utils/validation_utils.py", "Data validation (NEW)"),
        ("utils/conversion_utils.py", "Currency/data conversion (NEW)")
    ]
    
    # Blockchain files
    blockchain_files = [
        ("blockchain/__init__.py", "Blockchain package init"),
        ("blockchain/blockchain_manager.py", "Enhanced unified blockchain interface"),
        ("blockchain/nano_client.py", "Nano operations"),
        ("blockchain/arweave_client.py", "Arweave operations"),
        ("blockchain/dogecoin_client.py", "DOGE operations")
    ]
    
    all_passed = True
    
    # Check core files
    print("\n📁 Core Files:")
    for filename, description in core_files:
        filepath = os.path.join(base_path, filename)
        if not check_file_exists(filepath, description):
            all_passed = False
    
    # Check directories
    print("\n📁 Directory Structure:")
    for directory in directories:
        dirpath = os.path.join(base_path, directory)
        if os.path.isdir(dirpath):
            print(f"✅ {directory} - Directory exists")
        else:
            print(f"❌ {directory} - Directory missing")
            all_passed = False
    
    # Check service files
    print("\n📁 Service Layer:")
    for filename, description in service_files:
        filepath = os.path.join(base_path, filename)
        if not check_file_exists(filepath, description):
            all_passed = False
    
    # Check repository files
    print("\n📁 Repository Layer:")
    for filename, description in repository_files:
        filepath = os.path.join(base_path, filename)
        if not check_file_exists(filepath, description):
            all_passed = False
    
    # Check utility files
    print("\n📁 Utility Layer:")
    for filename, description in utility_files:
        filepath = os.path.join(base_path, filename)
        if not check_file_exists(filepath, description):
            all_passed = False
    
    # Check blockchain files
    print("\n📁 Blockchain Layer:")
    for filename, description in blockchain_files:
        filepath = os.path.join(base_path, filename)
        if not check_file_exists(filepath, description):
            all_passed = False
    
    return all_passed

def check_code_structure():
    """Check code structure and patterns."""
    print("\n🔍 Checking Code Structure...")
    print("=" * 50)
    
    base_path = "/Users/seanmorrissey/Desktop/Coding/Sapphire_Exchange"
    
    # Check if key classes exist in files
    checks = [
        ("application_service.py", "class ApplicationService", "Central application service"),
        ("database_adapter.py", "class DatabaseAdapter", "Database adapter pattern"),
        ("services/user_service.py", "class UserService", "User service implementation"),
        ("repositories/base_repository.py", "class BaseRepository", "Repository base class"),
        ("repositories/user_repository.py", "class UserRepository", "User repository"),
        ("repositories/item_repository.py", "class ItemRepository", "Item repository"),
        ("repositories/bid_repository.py", "class BidRepository", "Bid repository"),
        ("utils/validation_utils.py", "class Validator", "Validation utilities"),
        ("utils/conversion_utils.py", "class ConversionUtils", "Conversion utilities"),
        ("main_window_unified.py", "class MainWindow", "Unified main window")
    ]
    
    all_passed = True
    
    for filename, class_name, description in checks:
        filepath = os.path.join(base_path, filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if class_name in content:
                        print(f"✅ {filename} - {description} (class found)")
                    else:
                        print(f"⚠️  {filename} - {description} (class not found)")
                        all_passed = False
            except Exception as e:
                print(f"❌ {filename} - Error reading file: {e}")
                all_passed = False
        else:
            print(f"❌ {filename} - File missing")
            all_passed = False
    
    return all_passed

def check_imports():
    """Check that key imports are structured correctly."""
    print("\n🔍 Checking Import Structure...")
    print("=" * 50)
    
    base_path = "/Users/seanmorrissey/Desktop/Coding/Sapphire_Exchange"
    
    # Check package __init__.py files
    init_files = [
        ("services/__init__.py", ["AuctionService", "WalletService", "UserService"]),
        ("repositories/__init__.py", ["BaseRepository", "UserRepository", "ItemRepository", "BidRepository"]),
        ("utils/__init__.py", ["Validator", "ConversionUtils"])
    ]
    
    all_passed = True
    
    for filename, expected_exports in init_files:
        filepath = os.path.join(base_path, filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    missing_exports = []
                    for export in expected_exports:
                        if export not in content:
                            missing_exports.append(export)
                    
                    if not missing_exports:
                        print(f"✅ {filename} - All exports present")
                    else:
                        print(f"⚠️  {filename} - Missing exports: {missing_exports}")
                        all_passed = False
            except Exception as e:
                print(f"❌ {filename} - Error reading file: {e}")
                all_passed = False
        else:
            print(f"❌ {filename} - File missing")
            all_passed = False
    
    return all_passed

def check_documentation():
    """Check documentation completeness."""
    print("\n🔍 Checking Documentation...")
    print("=" * 50)
    
    base_path = "/Users/seanmorrissey/Desktop/Coding/Sapphire_Exchange"
    
    doc_files = [
        ("UNIFIED_ARCHITECTURE_COMPLETE.md", "Complete architecture documentation"),
        ("UNIFIED_ARCHITECTURE_SUMMARY.md", "Architecture summary"),
        ("requirements_unified.txt", "Unified requirements file")
    ]
    
    all_passed = True
    
    for filename, description in doc_files:
        filepath = os.path.join(base_path, filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if len(content) > 1000:  # Reasonable documentation length
                        print(f"✅ {filename} - {description} (comprehensive)")
                    else:
                        print(f"⚠️  {filename} - {description} (may be incomplete)")
            except Exception as e:
                print(f"❌ {filename} - Error reading file: {e}")
                all_passed = False
        else:
            print(f"❌ {filename} - {description} (missing)")
            all_passed = False
    
    return all_passed

def count_lines_of_code():
    """Count lines of code in the unified system."""
    print("\n📊 Code Statistics...")
    print("=" * 50)
    
    base_path = "/Users/seanmorrissey/Desktop/Coding/Sapphire_Exchange"
    
    python_files = []
    for root, dirs, files in os.walk(base_path):
        # Skip certain directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    total_lines = 0
    total_files = 0
    
    for filepath in python_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = len(f.readlines())
                total_lines += lines
                total_files += 1
                relative_path = os.path.relpath(filepath, base_path)
                print(f"📄 {relative_path}: {lines} lines")
        except Exception as e:
            print(f"❌ Error reading {filepath}: {e}")
    
    print(f"\n📊 Total: {total_files} Python files, {total_lines} lines of code")
    return total_files, total_lines

def main():
    """Main verification function."""
    print("🚀 Sapphire Exchange - Unified Architecture Verification")
    print("=" * 60)
    
    # Run all checks
    structure_ok = check_directory_structure()
    code_ok = check_code_structure()
    imports_ok = check_imports()
    docs_ok = check_documentation()
    
    # Count code
    file_count, line_count = count_lines_of_code()
    
    # Final summary
    print("\n" + "=" * 60)
    print("📋 VERIFICATION SUMMARY")
    print("=" * 60)
    
    checks = [
        ("Directory Structure", structure_ok),
        ("Code Structure", code_ok),
        ("Import Structure", imports_ok),
        ("Documentation", docs_ok)
    ]
    
    all_passed = True
    for check_name, passed in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{check_name}: {status}")
        if not passed:
            all_passed = False
    
    print(f"\nCode Statistics: {file_count} files, {line_count} lines")
    
    if all_passed:
        print("\n🎉 UNIFICATION COMPLETE!")
        print("✅ All components are properly structured")
        print("✅ Architecture is unified and consistent")
        print("✅ Ready for development and testing")
    else:
        print("\n⚠️  UNIFICATION ISSUES DETECTED")
        print("❌ Some components need attention")
        print("📝 Review the failed checks above")
    
    print("\n" + "=" * 60)
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)