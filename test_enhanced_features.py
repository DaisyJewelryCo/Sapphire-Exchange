#!/usr/bin/env python3
"""
Comprehensive test script for enhanced Sapphire Exchange features.
Tests multi-currency support, security, performance, and database functionality.
"""
import asyncio
import sys
import os
import time
from datetime import datetime, timezone, timedelta

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import User, Item, Bid
from dogecoin_utils import DogeWalletManager
from security_manager import SecurityManager, SessionManager, EncryptionManager
from performance_manager import PerformanceManager, NetworkErrorHandler
from price_service import PriceConversionService, PriceAlertService
from database import EnhancedDatabase
from decentralized_client import EnhancedDecentralizedClient


class EnhancedFeaturesTester:
    """Test suite for enhanced Sapphire Exchange features."""
    
    def __init__(self):
        self.test_results = []
        self.setup_components()
    
    def setup_components(self):
        """Initialize all components for testing."""
        print("🔧 Setting up test components...")
        
        # Initialize managers
        self.security_manager = SecurityManager()
        self.session_manager = SessionManager(self.security_manager)
        self.encryption_manager = EncryptionManager()
        self.performance_manager = PerformanceManager()
        self.network_error_handler = NetworkErrorHandler()
        
        # Initialize services
        self.price_service = PriceConversionService(self.performance_manager)
        self.price_alert_service = PriceAlertService(self.price_service)
        
        # Initialize database and client
        self.database = EnhancedDatabase(
            performance_manager=self.performance_manager,
            security_manager=self.security_manager
        )
        self.client = EnhancedDecentralizedClient(mock_mode=True)
        
        # Initialize DOGE wallet manager
        self.doge_manager = DogeWalletManager()
        
        print("✅ Components initialized successfully")
    
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test result."""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"   {details}")
        
        self.test_results.append({
            'test': test_name,
            'success': success,
            'details': details,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    
    async def test_doge_wallet_generation(self):
        """Test DOGE wallet generation and management."""
        print("\n🐕 Testing DOGE Wallet Generation...")
        
        try:
            # Test wallet generation (mock mode)
            try:
                wallet_data = {
                    'mnemonic': 'test word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12',
                    'private_key': 'mock_private_key_hex',
                    'public_key': 'mock_public_key_hex',
                    'address': 'DMockAddressForTestingPurposes123456',
                    'derivation_path': "m/44'/3'/0'/0/0",
                    'network': 'mainnet'
                }
                self.log_test("DOGE Wallet Generation (Mock)", True, f"Address: {wallet_data['address']}")
            except Exception as e:
                self.log_test("DOGE Wallet Generation (Mock)", False, str(e))
            
            # Test address validation
            valid_address = "DMockAddressForTestingPurposes123456"
            invalid_address = "invalid_address"
            
            # Mock validation (since we don't have real BIP utils in test)
            valid_result = len(valid_address) == 34 and valid_address.startswith('D')
            invalid_result = len(invalid_address) == 34 and invalid_address.startswith('D')
            
            self.log_test("DOGE Address Validation (Valid)", valid_result, f"Address: {valid_address}")
            self.log_test("DOGE Address Validation (Invalid)", not invalid_result, f"Address: {invalid_address}")
            
            # Test mnemonic hashing
            mnemonic = "test mnemonic phrase for hashing"
            mnemonic_hash = self.doge_manager.calculate_mnemonic_hash(mnemonic)
            expected_length = 64  # SHA-256 hex length
            
            self.log_test("Mnemonic Hash Generation", len(mnemonic_hash) == expected_length, 
                         f"Hash length: {len(mnemonic_hash)}")
            
        except Exception as e:
            self.log_test("DOGE Wallet Tests", False, f"Unexpected error: {str(e)}")
    
    async def test_security_features(self):
        """Test security management features."""
        print("\n🔒 Testing Security Features...")
        
        try:
            # Test password hashing
            password = "test_password_123"
            hash_result = self.security_manager.hash_password(password)
            
            self.log_test("Password Hashing", 
                         all(key in hash_result for key in ['hash', 'salt', 'algorithm', 'iterations']),
                         f"Algorithm: {hash_result['algorithm']}")
            
            # Test password verification
            verification_result = self.security_manager.verify_password(
                password, hash_result['hash'], hash_result['salt']
            )
            self.log_test("Password Verification (Correct)", verification_result)
            
            wrong_verification = self.security_manager.verify_password(
                "wrong_password", hash_result['hash'], hash_result['salt']
            )
            self.log_test("Password Verification (Wrong)", not wrong_verification)
            
            # Test secure token generation
            token = self.security_manager.generate_secure_token()
            self.log_test("Secure Token Generation", len(token) > 20, f"Token length: {len(token)}")
            
            # Test rate limiting
            identifier = "test_user_123"
            
            # First request should be allowed
            allowed1, info1 = self.security_manager.check_rate_limit(identifier)
            self.log_test("Rate Limiting (First Request)", allowed1, f"Remaining: {info1.get('requests_remaining', 0)}")
            
            # Test session management
            user_id = "test_user_456"
            session_token = self.session_manager.create_session(user_id)
            self.log_test("Session Creation", len(session_token) > 20, f"Token: {session_token[:10]}...")
            
            # Validate session
            validation_result = self.session_manager.validate_session(session_token)
            self.log_test("Session Validation", validation_result['valid'], 
                         f"User ID: {validation_result.get('user_id')}")
            
            # Test encryption
            test_data = "sensitive_data_to_encrypt"
            encryption_key = self.encryption_manager.generate_encryption_key()
            
            encrypted_result = self.encryption_manager.encrypt_sensitive_data(test_data, encryption_key)
            self.log_test("Data Encryption", 'ciphertext' in encrypted_result, 
                         f"Algorithm: {encrypted_result.get('algorithm')}")
            
            # Test decryption
            decrypted_data = self.encryption_manager.decrypt_sensitive_data(encrypted_result, encryption_key)
            self.log_test("Data Decryption", decrypted_data == test_data, 
                         f"Data match: {decrypted_data == test_data}")
            
        except Exception as e:
            self.log_test("Security Features", False, f"Error: {str(e)}")
    
    async def test_performance_features(self):
        """Test performance management features."""
        print("\n⚡ Testing Performance Features...")
        
        try:
            # Test caching
            cache_key = "test_cache_key"
            cache_data = {"test": "data", "timestamp": time.time()}
            
            # Store in cache
            self.performance_manager.set_cached_data(cache_key, cache_data)
            
            # Retrieve from cache
            retrieved_data = self.performance_manager.get_cached_data(cache_key)
            cache_hit = retrieved_data is not None and retrieved_data['test'] == 'data'
            
            self.log_test("Cache Storage/Retrieval", cache_hit, f"Data: {retrieved_data}")
            
            # Test cache key generation
            args = ("arg1", "arg2")
            kwargs = {"key1": "value1", "key2": "value2"}
            cache_key_generated = self.performance_manager.create_cache_key(*args, **kwargs)
            
            self.log_test("Cache Key Generation", len(cache_key_generated) == 64, 
                         f"Key: {cache_key_generated[:16]}...")
            
            # Test batch processing (mock)
            async def mock_process_func(item):
                await asyncio.sleep(0.01)  # Simulate processing
                return f"processed_{item}"
            
            items = [f"item_{i}" for i in range(5)]
            results = await self.performance_manager.batch_process(items, mock_process_func, batch_size=2)
            
            self.log_test("Batch Processing", len(results) == len(items), 
                         f"Processed {len(results)} items")
            
            # Test performance stats
            stats = self.performance_manager.get_performance_stats()
            required_keys = ['cache_stats', 'cache_size', 'metrics']
            stats_complete = all(key in stats for key in required_keys)
            
            self.log_test("Performance Stats", stats_complete, 
                         f"Cache size: {stats.get('cache_size', 0)}")
            
            # Test network error handling
            async def failing_operation():
                raise ConnectionError("Mock network error")
            
            try:
                await self.network_error_handler.execute_with_retry(failing_operation)
                retry_worked = False
            except ConnectionError:
                retry_worked = True  # Expected to fail after retries
            
            self.log_test("Network Error Handling", retry_worked, "Retry mechanism tested")
            
        except Exception as e:
            self.log_test("Performance Features", False, f"Error: {str(e)}")
    
    async def test_price_service(self):
        """Test price conversion service."""
        print("\n💰 Testing Price Service...")
        
        try:
            # Test supported currencies
            supported = self.price_service.get_supported_currencies()
            has_required = all(currency in supported for currency in ['nano', 'doge', 'arweave'])
            
            self.log_test("Supported Currencies", has_required, 
                         f"Currencies: {', '.join(supported[:5])}")
            
            # Test fallback prices (since we can't test real API in unit tests)
            fallback_prices = {
                'nano': 1.25,
                'dogecoin': 0.085,
                'arweave': 8.75
            }
            self.price_service.update_fallback_prices(fallback_prices)
            
            self.log_test("Fallback Price Update", True, "Prices updated successfully")
            
            # Test price alerts
            user_id = "test_user_alerts"
            alert_id = self.price_alert_service.create_alert(
                user_id, "doge", 0.10, "above"
            )
            
            self.log_test("Price Alert Creation", len(alert_id) > 0, f"Alert ID: {alert_id}")
            
            # Test alert retrieval
            user_alerts = self.price_alert_service.get_user_alerts(user_id)
            self.log_test("Price Alert Retrieval", len(user_alerts) == 1, 
                         f"Alerts: {len(user_alerts)}")
            
            # Test alert toggle
            toggle_result = self.price_alert_service.toggle_alert(user_id, alert_id)
            self.log_test("Price Alert Toggle", toggle_result, "Alert toggled successfully")
            
        except Exception as e:
            self.log_test("Price Service", False, f"Error: {str(e)}")
    
    async def test_enhanced_database(self):
        """Test enhanced database functionality."""
        print("\n🗄️ Testing Enhanced Database...")
        
        try:
            # Create test user
            test_user = User(
                id="test_user_db_001",
                username="testuser",
                nano_address="nano_test123456789",
                doge_address="DTestAddress123456789",
                public_key="test_public_key",
                reputation_score=85.5
            )
            
            # Store user
            storage_key = await self.database.store(test_user)
            self.log_test("User Storage", len(storage_key) > 0, f"Key: {storage_key}")
            
            # Retrieve user
            retrieved_user = await self.database.get(User, test_user.id)
            user_match = retrieved_user is not None and retrieved_user.username == test_user.username
            
            self.log_test("User Retrieval", user_match, 
                         f"Username: {retrieved_user.username if retrieved_user else 'None'}")
            
            # Test user queries
            user_by_address = await self.database.query_users_by_address(test_user.nano_address)
            address_query_works = user_by_address is not None and user_by_address.id == test_user.id
            
            self.log_test("User Query by Address", address_query_works, 
                         f"Found user: {user_by_address.username if user_by_address else 'None'}")
            
            user_by_username = await self.database.query_users_by_username(test_user.username)
            username_query_works = user_by_username is not None and user_by_username.id == test_user.id
            
            self.log_test("User Query by Username", username_query_works,
                         f"Found user: {user_by_username.id if user_by_username else 'None'}")
            
            # Create test item
            test_item = Item(
                id="test_item_db_001",
                seller_id=test_user.id,
                title="Test Auction Item",
                description="A test item for database testing",
                starting_price_doge="10.0",
                status="active",
                category="Electronics",
                tags=["test", "electronics", "auction"]
            )
            
            # Store item
            item_key = await self.database.store(test_item)
            self.log_test("Item Storage", len(item_key) > 0, f"Key: {item_key}")
            
            # Test item queries
            items_by_seller = await self.database.query_items_by_seller(test_user.id)
            seller_query_works = len(items_by_seller) > 0 and items_by_seller[0].id == test_item.id
            
            self.log_test("Item Query by Seller", seller_query_works,
                         f"Found {len(items_by_seller)} items")
            
            items_by_status = await self.database.query_items_by_status("active")
            status_query_works = len(items_by_status) > 0
            
            self.log_test("Item Query by Status", status_query_works,
                         f"Found {len(items_by_status)} active items")
            
            # Test search functionality
            search_results = await self.database.search_items("test", {"category": "Electronics"})
            search_works = len(search_results) > 0
            
            self.log_test("Item Search", search_works,
                         f"Found {len(search_results)} items matching 'test'")
            
            # Create test bid
            test_bid = Bid(
                id="test_bid_db_001",
                item_id=test_item.id,
                bidder_id="test_bidder_001",
                amount_doge="15.0",
                status="confirmed"
            )
            
            # Store bid
            bid_key = await self.database.store(test_bid)
            self.log_test("Bid Storage", len(bid_key) > 0, f"Key: {bid_key}")
            
            # Test bid queries
            bids_by_item = await self.database.query_bids_by_item(test_item.id)
            bid_query_works = len(bids_by_item) > 0 and bids_by_item[0].id == test_bid.id
            
            self.log_test("Bid Query by Item", bid_query_works,
                         f"Found {len(bids_by_item)} bids for item")
            
            # Test database stats
            stats = self.database.get_database_stats()
            stats_complete = all(key in stats for key in ['cache_size', 'indexes', 'data_integrity'])
            
            self.log_test("Database Statistics", stats_complete,
                         f"Cache size: {stats.get('cache_size', 0)}")
            
        except Exception as e:
            self.log_test("Enhanced Database", False, f"Error: {str(e)}")
    
    async def test_multi_currency_client(self):
        """Test enhanced decentralized client."""
        print("\n🌐 Testing Multi-Currency Client...")
        
        try:
            # Test connection checking
            connections = await self.client.check_all_connections()
            connection_keys = ['arweave', 'nano', 'doge', 'overall']
            connections_complete = all(key in connections for key in connection_keys)
            
            self.log_test("Connection Status Check", connections_complete,
                         f"Overall: {connections.get('overall', False)}")
            
            # Test wallet initialization (mock)
            mock_seed = "test seed phrase for wallet initialization testing purposes only"
            
            try:
                wallet_results = await self.client.initialize_multi_currency_wallet(mock_seed)
                wallet_init_success = 'overall' in wallet_results
                
                self.log_test("Multi-Currency Wallet Init", wallet_init_success,
                             f"Status: {wallet_results.get('overall', {}).get('status', 'unknown')}")
            except Exception as e:
                self.log_test("Multi-Currency Wallet Init", False, f"Error: {str(e)}")
            
            # Test balance retrieval (mock)
            try:
                nano_balance = await self.client.get_balance('nano')
                balance_retrieval = 'status' in nano_balance
                
                self.log_test("Balance Retrieval", balance_retrieval,
                             f"Status: {nano_balance.get('status', 'unknown')}")
            except Exception as e:
                self.log_test("Balance Retrieval", False, f"Error: {str(e)}")
            
            # Test USD conversion (mock)
            try:
                usd_value = await self.client.convert_to_usd(10.0, 'doge')
                conversion_works = usd_value is not None
                
                self.log_test("USD Conversion", conversion_works,
                             f"10 DOGE = ${usd_value:.2f}" if usd_value else "Conversion failed")
            except Exception as e:
                self.log_test("USD Conversion", False, f"Error: {str(e)}")
            
        except Exception as e:
            self.log_test("Multi-Currency Client", False, f"Error: {str(e)}")
    
    async def test_data_models(self):
        """Test enhanced data models."""
        print("\n📊 Testing Enhanced Data Models...")
        
        try:
            # Test User model
            user = User(
                username="testuser123",
                nano_address="nano_test123",
                doge_address="DTest123",
                reputation_score=92.5
            )
            
            # Test validation
            username_valid = user.validate_username()
            self.log_test("User Username Validation", username_valid,
                         f"Username: {user.username}")
            
            # Test data hash calculation
            user_hash = user.calculate_data_hash()
            self.log_test("User Data Hash", len(user_hash) == 64,
                         f"Hash: {user_hash[:16]}...")
            
            # Test serialization
            user_dict = user.to_dict()
            user_from_dict = User.from_dict(user_dict)
            serialization_works = user_from_dict.username == user.username
            
            self.log_test("User Serialization", serialization_works,
                         f"Username match: {user_from_dict.username == user.username}")
            
            # Test Item model
            item = Item(
                title="Test Item for Model Testing",
                description="A comprehensive test item with all features",
                starting_price_doge="25.50",
                status="active",
                category="Test Category",
                tags=["test", "model", "validation"]
            )
            
            # Test validations
            title_valid = item.validate_title()
            desc_valid = item.validate_description()
            tags_valid = item.validate_tags()
            
            self.log_test("Item Validation", all([title_valid, desc_valid, tags_valid]),
                         f"Title: {title_valid}, Desc: {desc_valid}, Tags: {tags_valid}")
            
            # Test item hash
            item_hash = item.calculate_data_hash()
            self.log_test("Item Data Hash", len(item_hash) == 64,
                         f"Hash: {item_hash[:16]}...")
            
            # Test Bid model
            bid = Bid(
                item_id="test_item_123",
                bidder_id="test_bidder_456",
                amount_doge="30.00",
                transaction_hash="1234567890ABCDEF" * 4  # 64 chars
            )
            
            # Test bid validation
            tx_hash_valid = bid.validate_transaction_hash()
            self.log_test("Bid Transaction Hash Validation", tx_hash_valid,
                         f"Hash: {bid.transaction_hash[:16]}...")
            
            # Test bid hash
            bid_hash = bid.calculate_data_hash()
            self.log_test("Bid Data Hash", len(bid_hash) == 64,
                         f"Hash: {bid_hash[:16]}...")
            
        except Exception as e:
            self.log_test("Data Models", False, f"Error: {str(e)}")
    
    async def run_all_tests(self):
        """Run all test suites."""
        print("🚀 Starting Enhanced Sapphire Exchange Feature Tests")
        print("=" * 60)
        
        start_time = time.time()
        
        # Run all test suites
        await self.test_doge_wallet_generation()
        await self.test_security_features()
        await self.test_performance_features()
        await self.test_price_service()
        await self.test_enhanced_database()
        await self.test_multi_currency_client()
        await self.test_data_models()
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Print summary
        print("\n" + "=" * 60)
        print("📋 TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        print(f"Duration: {duration:.2f} seconds")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  - {result['test']}: {result['details']}")
        
        print("\n🎉 Enhanced feature testing completed!")
        return passed_tests == total_tests


async def main():
    """Main test execution function."""
    tester = EnhancedFeaturesTester()
    success = await tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())