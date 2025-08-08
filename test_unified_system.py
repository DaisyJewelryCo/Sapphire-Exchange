"""
Comprehensive test suite for the unified Sapphire Exchange architecture.
Tests all major components and their integration.
"""
import asyncio
import os
import sys
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import components to test
from models.models import User, Item, Bid
from services.user_service import UserService
from services.auction_service import AuctionService
from services.wallet_service import WalletService
from repositories.user_repository import UserRepository
from repositories.item_repository import ItemRepository
from repositories.bid_repository import BidRepository
from utils.validation_utils import Validator, validate_email, validate_username
from utils.conversion_utils import ConversionUtils
from security.security_manager import SecurityManager
from security.performance_manager import PerformanceManager
from config.app_config import app_config


class TestUnifiedArchitecture(unittest.TestCase):
    """Test the unified architecture components."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock database and blockchain
        self.mock_database = Mock()
        self.mock_blockchain = Mock()
        
        # Initialize services with mocks
        self.security_manager = SecurityManager()
        self.performance_manager = PerformanceManager()
        
        self.user_service = UserService(
            database=self.mock_database,
            security_manager=self.security_manager
        )
        
        self.auction_service = AuctionService(database=self.mock_database)
        self.wallet_service = WalletService()
        
        # Initialize repositories
        self.user_repo = UserRepository(
            database=self.mock_database,
            performance_manager=self.performance_manager,
            blockchain_manager=self.mock_blockchain
        )
        
        self.item_repo = ItemRepository(
            database=self.mock_database,
            performance_manager=self.performance_manager,
            blockchain_manager=self.mock_blockchain
        )
        
        self.bid_repo = BidRepository(
            database=self.mock_database,
            performance_manager=self.performance_manager,
            blockchain_manager=self.mock_blockchain
        )
        
        # Test data
        self.test_user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'SecurePass123!'
        }
        
        self.test_item_data = {
            'title': 'Test Auction Item',
            'description': 'A test item for auction',
            'starting_price_doge': '10.0',
            'auction_end': (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            'category': 'Electronics',
            'tags': ['test', 'electronics']
        }
    
    def test_models_creation(self):
        """Test that models can be created and have required attributes."""
        # Test User model
        user = User(
            username='testuser',
            email='test@example.com',
            password_hash='hashed_password'
        )
        
        self.assertIsNotNone(user.id)
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertIsNotNone(user.created_at)
        
        # Test data hash calculation
        data_hash = user.calculate_data_hash()
        self.assertIsInstance(data_hash, str)
        self.assertEqual(len(data_hash), 64)  # SHA-256 hash length
        
        # Test Item model
        item = Item(
            seller_id=user.id,
            title='Test Item',
            description='Test Description',
            starting_price_doge='5.0'
        )
        
        self.assertIsNotNone(item.id)
        self.assertEqual(item.seller_id, user.id)
        self.assertEqual(item.title, 'Test Item')
        self.assertEqual(item.status, 'draft')
        
        # Test Bid model
        bid = Bid(
            item_id=item.id,
            bidder_id=user.id,
            amount_doge='10.0'
        )
        
        self.assertIsNotNone(bid.id)
        self.assertEqual(bid.item_id, item.id)
        self.assertEqual(bid.bidder_id, user.id)
        self.assertEqual(bid.status, 'pending')
    
    def test_validation_utils(self):
        """Test validation utilities."""
        # Test email validation
        self.assertTrue(validate_email('test@example.com'))
        self.assertFalse(validate_email('invalid-email'))
        self.assertFalse(validate_email(''))
        
        # Test username validation
        self.assertTrue(validate_username('testuser'))
        self.assertTrue(validate_username('test_user'))
        self.assertTrue(validate_username('test-user'))
        self.assertFalse(validate_username('te'))  # Too short
        self.assertFalse(validate_username('test user'))  # Space not allowed
        
        # Test password validation
        password_result = Validator.validate_password('SecurePass123!')
        self.assertTrue(password_result['valid'])
        self.assertEqual(password_result['strength'], 'strong')
        
        weak_password_result = Validator.validate_password('weak')
        self.assertFalse(weak_password_result['valid'])
        self.assertIn('Password must be at least 8 characters long', weak_password_result['errors'])
        
        # Test amount validation
        amount_result = Validator.validate_amount('10.50', min_amount=1.0)
        self.assertTrue(amount_result['valid'])
        self.assertEqual(amount_result['normalized_amount'], 10.50)
        
        invalid_amount_result = Validator.validate_amount('0.50', min_amount=1.0)
        self.assertFalse(invalid_amount_result['valid'])
        
        # Test item data validation
        item_validation = Validator.validate_item_data(self.test_item_data)
        self.assertTrue(item_validation['valid'])
        
        # Test invalid item data
        invalid_item_data = self.test_item_data.copy()
        invalid_item_data['title'] = ''  # Empty title
        invalid_item_validation = Validator.validate_item_data(invalid_item_data)
        self.assertFalse(invalid_item_validation['valid'])
    
    def test_conversion_utils(self):
        """Test conversion utilities."""
        converter = ConversionUtils()
        
        # Test NANO conversions
        raw_amount = converter.nano_to_raw('1.0')
        self.assertEqual(raw_amount, str(10**30))
        
        nano_amount = converter.raw_to_nano(str(10**30))
        self.assertEqual(nano_amount, '1.000000')
        
        # Test DOGE conversions
        satoshi_amount = converter.doge_to_satoshi('1.0')
        self.assertEqual(satoshi_amount, 10**8)
        
        doge_amount = converter.satoshi_to_doge(10**8)
        self.assertEqual(doge_amount, '1.00000000')
        
        # Test currency formatting
        formatted_usd = converter.format_currency('1234.56', 'USD')
        self.assertIn('$', formatted_usd)
        self.assertIn('1,234.56', formatted_usd)
        
        formatted_doge = converter.format_currency('1234.56789012', 'DOGE')
        self.assertIn('Ð', formatted_doge)
        
        # Test large number formatting
        large_num = converter.format_large_number(1500000)
        self.assertEqual(large_num, '1.50M')
        
        # Test percentage formatting
        percentage = converter.format_percentage(5.67)
        self.assertEqual(percentage, '+5.67%')
        
        negative_percentage = converter.format_percentage(-2.34)
        self.assertEqual(percentage, '-2.34%')
    
    def test_security_manager(self):
        """Test security manager functionality."""
        # Test password hashing
        password = 'TestPassword123!'
        hashed = self.security_manager.hash_password(password)
        
        self.assertIsInstance(hashed, str)
        self.assertNotEqual(hashed, password)
        
        # Test password verification
        self.assertTrue(self.security_manager.verify_password(password, hashed))
        self.assertFalse(self.security_manager.verify_password('wrong_password', hashed))
        
        # Test data encryption
        test_data = 'sensitive information'
        encrypted = self.security_manager.encrypt_data(test_data)
        decrypted = self.security_manager.decrypt_data(encrypted)
        
        self.assertNotEqual(encrypted, test_data)
        self.assertEqual(decrypted, test_data)
    
    def test_performance_manager(self):
        """Test performance manager caching."""
        # Test caching
        test_key = 'test_key'
        test_data = {'test': 'data'}
        
        # Set cached data
        self.performance_manager.set_cached_data(test_key, test_data, ttl_ms=5000)
        
        # Get cached data
        cached_data = self.performance_manager.get_cached_data(test_key)
        self.assertEqual(cached_data, test_data)
        
        # Test cache miss
        missing_data = self.performance_manager.get_cached_data('non_existent_key')
        self.assertIsNone(missing_data)
    
    async def test_user_service(self):
        """Test user service functionality."""
        # Mock blockchain address generation
        self.mock_blockchain.generate_nano_address = AsyncMock(return_value='nano_test_address')
        self.mock_blockchain.generate_arweave_address = AsyncMock(return_value='arweave_test_address')
        self.mock_blockchain.generate_doge_address = AsyncMock(return_value='doge_test_address')
        self.mock_blockchain.store_data = AsyncMock(return_value='test_tx_id')
        
        # Mock database methods
        self.mock_database.get_user_by_username = AsyncMock(return_value=None)
        self.mock_database.get_user_by_email = AsyncMock(return_value=None)
        self.mock_database.store_user = AsyncMock(return_value=True)
        
        # Test user creation
        user = await self.user_service.create_user(
            username='testuser',
            email='test@example.com',
            password='SecurePass123!'
        )
        
        self.assertIsNotNone(user)
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertIsNotNone(user.password_hash)
        self.assertNotEqual(user.password_hash, 'SecurePass123!')
        
        # Test user authentication
        self.mock_database.get_user_by_username = AsyncMock(return_value=user)
        
        auth_result = await self.user_service.authenticate_user('testuser', 'SecurePass123!')
        self.assertIsNotNone(auth_result)
        
        authenticated_user, session_token = auth_result
        self.assertEqual(authenticated_user.username, 'testuser')
        self.assertIsInstance(session_token, str)
        
        # Test invalid authentication
        invalid_auth = await self.user_service.authenticate_user('testuser', 'wrong_password')
        self.assertIsNone(invalid_auth)
    
    async def test_auction_service(self):
        """Test auction service functionality."""
        # Create test user
        test_user = User(
            username='seller',
            email='seller@example.com',
            password_hash='hashed'
        )
        
        # Mock blockchain operations
        self.mock_blockchain.store_data = AsyncMock(return_value='test_tx_id')
        self.mock_database.store_item = AsyncMock(return_value=True)
        
        # Test auction creation
        item = await self.auction_service.create_auction(test_user, self.test_item_data)
        
        self.assertIsNotNone(item)
        self.assertEqual(item.title, 'Test Auction Item')
        self.assertEqual(item.seller_id, test_user.id)
        self.assertEqual(item.status, 'active')
        self.assertIsNotNone(item.arweave_metadata_uri)
        
        # Test bid placement
        bidder = User(
            username='bidder',
            email='bidder@example.com',
            password_hash='hashed'
        )
        
        # Mock blockchain operations for bidding
        self.mock_blockchain.send_doge = AsyncMock(return_value='bid_tx_hash')
        self.mock_database.store_bid = AsyncMock(return_value=True)
        self.mock_database.update_item = AsyncMock(return_value=True)
        
        bid = await self.auction_service.place_bid(bidder, item, 15.0, 'DOGE')
        
        self.assertIsNotNone(bid)
        self.assertEqual(bid.item_id, item.id)
        self.assertEqual(bid.bidder_id, bidder.id)
        self.assertEqual(bid.amount_doge, '15.0')
        self.assertEqual(bid.status, 'confirmed')
    
    async def test_repositories(self):
        """Test repository functionality."""
        # Test user repository
        test_user = User(
            username='repouser',
            email='repo@example.com',
            password_hash='hashed'
        )
        
        # Mock blockchain and database operations
        self.mock_blockchain.store_data = AsyncMock(return_value='test_tx_id')
        self.mock_database.store_user = AsyncMock(return_value=True)
        
        created_user = await self.user_repo.create(test_user)
        self.assertIsNotNone(created_user)
        self.assertEqual(created_user.username, 'repouser')
        
        # Test item repository
        test_item = Item(
            seller_id=test_user.id,
            title='Repo Test Item',
            description='Test item for repository',
            starting_price_doge='5.0'
        )
        
        self.mock_database.store_item = AsyncMock(return_value=True)
        
        created_item = await self.item_repo.create(test_item)
        self.assertIsNotNone(created_item)
        self.assertEqual(created_item.title, 'Repo Test Item')
        
        # Test bid repository
        test_bid = Bid(
            item_id=test_item.id,
            bidder_id=test_user.id,
            amount_doge='10.0'
        )
        
        self.mock_database.store_bid = AsyncMock(return_value=True)
        
        created_bid = await self.bid_repo.create(test_bid)
        self.assertIsNotNone(created_bid)
        self.assertEqual(created_bid.amount_doge, '10.0')
    
    def test_config_loading(self):
        """Test configuration loading."""
        # Test that app_config is loaded
        self.assertIsNotNone(app_config)
        self.assertIsNotNone(app_config.ui)
        self.assertIsNotNone(app_config.blockchain)
        self.assertIsNotNone(app_config.security)
        
        # Test UI configuration
        self.assertGreater(app_config.ui.max_title_length, 0)
        self.assertGreater(app_config.ui.max_description_length, 0)
        self.assertGreater(app_config.ui.max_tags_per_item, 0)
        
        # Test blockchain configuration
        self.assertIsNotNone(app_config.blockchain.nano)
        self.assertIsNotNone(app_config.blockchain.arweave)
        self.assertIsNotNone(app_config.blockchain.dogecoin)
    
    def test_integration_flow(self):
        """Test a complete integration flow."""
        async def integration_test():
            # 1. Create user
            self.mock_blockchain.generate_nano_address = AsyncMock(return_value='nano_test')
            self.mock_blockchain.generate_arweave_address = AsyncMock(return_value='arweave_test')
            self.mock_blockchain.generate_doge_address = AsyncMock(return_value='doge_test')
            self.mock_blockchain.store_data = AsyncMock(return_value='tx_id')
            self.mock_database.get_user_by_username = AsyncMock(return_value=None)
            self.mock_database.get_user_by_email = AsyncMock(return_value=None)
            self.mock_database.store_user = AsyncMock(return_value=True)
            
            user = await self.user_service.create_user('integrationuser', 'int@example.com', 'SecurePass123!')
            self.assertIsNotNone(user)
            
            # 2. Create auction
            self.mock_database.store_item = AsyncMock(return_value=True)
            
            item = await self.auction_service.create_auction(user, self.test_item_data)
            self.assertIsNotNone(item)
            
            # 3. Place bid
            bidder_data = {
                'username': 'bidder',
                'email': 'bidder@example.com',
                'password': 'BidderPass123!'
            }
            
            bidder = await self.user_service.create_user(**bidder_data)
            self.assertIsNotNone(bidder)
            
            self.mock_blockchain.send_doge = AsyncMock(return_value='bid_tx')
            self.mock_database.store_bid = AsyncMock(return_value=True)
            self.mock_database.update_item = AsyncMock(return_value=True)
            
            bid = await self.auction_service.place_bid(bidder, item, 20.0, 'DOGE')
            self.assertIsNotNone(bid)
            
            # 4. Verify data integrity
            self.assertEqual(bid.item_id, item.id)
            self.assertEqual(bid.bidder_id, bidder.id)
            self.assertEqual(item.seller_id, user.id)
        
        # Run the async test
        asyncio.run(integration_test())


class TestAsyncComponents(unittest.IsolatedAsyncioTestCase):
    """Test async components separately."""
    
    async def test_price_service_integration(self):
        """Test price service integration."""
        # This would test the actual price service if available
        # For now, we'll test the structure
        try:
            from price_service import PriceConversionService
            price_service = PriceConversionService()
            self.assertIsNotNone(price_service)
        except ImportError:
            self.skipTest("Price service not available")


def run_tests():
    """Run all tests."""
    print("Running Sapphire Exchange Unified Architecture Tests...")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestUnifiedArchitecture))
    suite.addTests(loader.loadTestsFromTestCase(TestAsyncComponents))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\nOverall result: {'PASS' if success else 'FAIL'}")
    
    return success


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)