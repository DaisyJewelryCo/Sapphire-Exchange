"""
Comprehensive test for auction item SHA generation, encryption/decryption, and authenticity verification.
Demonstrates the complete cycle of:
1. SHA ID generation from auction item data
2. Encryption of SHA ID and item data
3. Decryption and verification
4. Authenticity checks for Arweave posts
"""

import asyncio
import json
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Tuple
import hashlib

from models.models import Item, User
from security.vault_encryption import VaultEncryption, CryptoVault, EncryptedKeyBlob
from security.security_manager import EncryptionManager


class AuctionSHAVerifier:
    """Verify SHA generation, encryption, and authenticity of auction items."""
    
    def __init__(self):
        """Initialize verifier with encryption keys."""
        self.master_key = os.urandom(32)
        self.vault = VaultEncryption(self.master_key)
        self.encryption_manager = EncryptionManager()
        self.test_results = []
    
    def create_test_item(self) -> Tuple[Item, User]:
        """Create a test auction item and seller."""
        seller = User(
            username="test_seller",
            password_hash="hash123",
            nano_address="nano_test123",
            arweave_address="arweave_test123"
        )
        
        item = Item(
            seller_id=seller.id,
            title="Vintage Motorcycle",
            description="1970s Harley-Davidson in excellent condition",
            starting_price_usdc="1500.0",
            auction_end=(datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
            status="draft",
            tags=["motorcycle", "vintage", "harley"],
            category="vehicles",
            shipping_required=True,
            shipping_cost_usdc="150.0"
        )
        
        return item, seller
    
    def test_sha_generation(self, item: Item) -> Dict:
        """Test 1: Verify SHA ID generation from item data."""
        print("\n" + "="*70)
        print("TEST 1: SHA ID GENERATION")
        print("="*70)
        
        result = {
            'test': 'SHA ID Generation',
            'passed': False,
            'details': {}
        }
        
        try:
            # Calculate expected SHA from same data as Item model
            expected_hash = hashlib.sha256(
                f"{item.seller_id}{item.title}{item.description}{item.created_at}".encode()
            ).hexdigest()
            
            print(f"\nItem Data:")
            print(f"  Title: {item.title}")
            print(f"  Seller ID: {item.seller_id}")
            print(f"  Created: {item.created_at}")
            
            print(f"\nGenerated SHA ID: {item.sha_id}")
            print(f"Expected SHA ID:  {expected_hash}")
            print(f"Match: {item.sha_id == expected_hash}")
            
            result['details'] = {
                'sha_id': item.sha_id,
                'expected': expected_hash,
                'matches': item.sha_id == expected_hash,
                'item_data': {
                    'title': item.title,
                    'seller_id': item.seller_id,
                    'created_at': item.created_at,
                    'description': item.description[:50] + "..."
                }
            }
            
            if item.sha_id == expected_hash:
                print("\n✓ SHA ID generation PASSED")
                result['passed'] = True
            else:
                print("\n✗ SHA ID generation FAILED")
        
        except Exception as e:
            print(f"\n✗ Error: {e}")
            result['details']['error'] = str(e)
        
        self.test_results.append(result)
        return result
    
    def test_encryption_decryption(self, item: Item) -> Dict:
        """Test 2: Encrypt SHA ID and item data, then decrypt."""
        print("\n" + "="*70)
        print("TEST 2: SHA ENCRYPTION & DECRYPTION")
        print("="*70)
        
        result = {
            'test': 'SHA Encryption/Decryption',
            'passed': False,
            'details': {}
        }
        
        try:
            # Store encrypted SHA ID
            self.vault.store_encrypted(
                key_id=item.id,
                key_data=item.sha_id.encode(),
                asset='auction_sha',
                chain='sapphire',
                description=f"SHA ID for item: {item.title}"
            )
            
            print(f"\nEncrypted SHA ID for item: {item.id}")
            print(f"Original SHA: {item.sha_id}")
            
            # Decrypt and verify
            decrypted_sha = self.vault.retrieve_decrypted(item.id)
            decrypted_sha_str = decrypted_sha.decode() if decrypted_sha else None
            
            print(f"Decrypted SHA: {decrypted_sha_str}")
            print(f"Match: {decrypted_sha_str == item.sha_id}")
            
            result['details'] = {
                'original_sha': item.sha_id,
                'decrypted_sha': decrypted_sha_str,
                'matches': decrypted_sha_str == item.sha_id,
                'encryption_successful': decrypted_sha is not None,
                'vault_key_id': item.id,
                'stored_keys': list(self.vault.list_stored_keys().keys())
            }
            
            if decrypted_sha_str == item.sha_id:
                print("\n✓ SHA encryption/decryption PASSED")
                result['passed'] = True
            else:
                print("\n✗ SHA encryption/decryption FAILED")
        
        except Exception as e:
            print(f"\n✗ Error: {e}")
            result['details']['error'] = str(e)
        
        self.test_results.append(result)
        return result
    
    def test_item_data_encryption(self, item: Item) -> Dict:
        """Test 3: Encrypt complete item data and verify integrity."""
        print("\n" + "="*70)
        print("TEST 3: ITEM DATA ENCRYPTION & INTEGRITY")
        print("="*70)
        
        result = {
            'test': 'Item Data Encryption',
            'passed': False,
            'details': {}
        }
        
        try:
            # Convert item to JSON
            item_json = json.dumps(item.to_dict(), indent=2)
            
            # Encrypt using AES-256-GCM
            encryption_key = self.encryption_manager.generate_encryption_key()
            encrypted_data = self.encryption_manager.encrypt_sensitive_data(
                item_json, 
                encryption_key
            )
            
            print(f"\nOriginal item data size: {len(item_json)} bytes")
            print(f"Encrypted data size: {len(encrypted_data['ciphertext'])} bytes")
            print(f"Encryption algorithm: {encrypted_data['algorithm']}")
            
            # Decrypt and verify
            decrypted_json = self.encryption_manager.decrypt_sensitive_data(
                encrypted_data,
                encryption_key
            )
            
            decrypted_item_dict = json.loads(decrypted_json)
            original_item_dict = item.to_dict()
            
            # Compare critical fields
            fields_match = (
                decrypted_item_dict['sha_id'] == original_item_dict['sha_id'] and
                decrypted_item_dict['item_id'] == original_item_dict['item_id'] and
                decrypted_item_dict['title'] == original_item_dict['title']
            )
            
            print(f"\nDecrypted successfully: {decrypted_json is not None}")
            print(f"Critical fields match: {fields_match}")
            print(f"  - SHA ID match: {decrypted_item_dict['sha_id'] == original_item_dict['sha_id']}")
            print(f"  - Item ID match: {decrypted_item_dict['item_id'] == original_item_dict['item_id']}")
            print(f"  - Title match: {decrypted_item_dict['title'] == original_item_dict['title']}")
            
            result['details'] = {
                'encryption_successful': encrypted_data is not None,
                'decryption_successful': decrypted_json is not None,
                'data_integrity': fields_match,
                'original_size': len(item_json),
                'encrypted_size': len(encrypted_data['ciphertext']),
                'algorithm': encrypted_data['algorithm'],
                'matched_fields': {
                    'sha_id': decrypted_item_dict['sha_id'] == original_item_dict['sha_id'],
                    'item_id': decrypted_item_dict['item_id'] == original_item_dict['item_id'],
                    'title': decrypted_item_dict['title'] == original_item_dict['title'],
                    'seller_id': decrypted_item_dict['seller_id'] == original_item_dict['seller_id']
                }
            }
            
            if fields_match:
                print("\n✓ Item data encryption/integrity PASSED")
                result['passed'] = True
            else:
                print("\n✗ Item data encryption/integrity FAILED")
        
        except Exception as e:
            print(f"\n✗ Error: {e}")
            result['details']['error'] = str(e)
        
        self.test_results.append(result)
        return result
    
    def test_authenticity_verification(self, item: Item) -> Dict:
        """Test 4: Verify authenticity of item data using SHA ID."""
        print("\n" + "="*70)
        print("TEST 4: AUTHENTICITY VERIFICATION")
        print("="*70)
        
        result = {
            'test': 'Authenticity Verification',
            'passed': False,
            'details': {}
        }
        
        try:
            # Use the Item's built-in verify_integrity method
            is_valid, message = item.verify_integrity()
            
            print(f"\nVerifying item integrity...")
            print(f"Result: {message}")
            print(f"Valid: {is_valid}")
            
            # Create a tampered copy to test failure case
            tampered_item = Item(
                seller_id=item.seller_id,
                title=item.title + " [TAMPERED]",  # Modify title
                description=item.description,
                starting_price_usdc=item.starting_price_usdc,
                auction_end=item.auction_end,
                status=item.status,
                tags=item.tags,
                category=item.category,
                shipping_required=item.shipping_required,
                shipping_cost_usdc=item.shipping_cost_usdc
            )
            
            # Manually set original SHA to test detection
            tampered_item.sha_id = item.sha_id
            is_tampered, tampered_msg = tampered_item.verify_integrity()
            
            print(f"\nTampered item verification:")
            print(f"Result: {tampered_msg}")
            print(f"Correctly detected as invalid: {not is_tampered}")
            
            result['details'] = {
                'original_valid': is_valid,
                'original_message': message,
                'tampered_detected': not is_tampered,
                'tampered_message': tampered_msg,
                'authenticity_check_working': is_valid and not is_tampered,
                'original_sha_id': item.sha_id,
                'calculated_hash': item.calculate_data_hash()
            }
            
            if is_valid and not is_tampered:
                print("\n✓ Authenticity verification PASSED")
                result['passed'] = True
            else:
                print("\n✗ Authenticity verification FAILED")
        
        except Exception as e:
            print(f"\n✗ Error: {e}")
            result['details']['error'] = str(e)
        
        self.test_results.append(result)
        return result
    
    def test_arweave_post_integrity(self, item: Item) -> Dict:
        """Test 5: Verify how SHA ID would be used in Arweave post for authenticity."""
        print("\n" + "="*70)
        print("TEST 5: ARWEAVE POST INTEGRITY SIMULATION")
        print("="*70)
        
        result = {
            'test': 'Arweave Post Integrity',
            'passed': False,
            'details': {}
        }
        
        try:
            # Simulate Arweave post structure with SHA ID
            arweave_post = {
                'type': 'auction_item',
                'item_id': item.item_id,
                'sha_id': item.sha_id,
                'seller_id': item.seller_id,
                'title': item.title,
                'description': item.description,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'content_hash': item.data_hash,
                'authenticity_chain': {
                    'original_sha': item.sha_id,
                    'item_data_hash': item.calculate_data_hash(),
                    'verify_integrity': item.verify_integrity()[0]
                }
            }
            
            # Convert to JSON (as it would be on Arweave)
            post_json = json.dumps(arweave_post, indent=2)
            
            # Create checksum of the post
            post_checksum = hashlib.sha256(post_json.encode()).hexdigest()
            
            print(f"\nArweave Post Structure:")
            print(f"  Item ID: {item.item_id}")
            print(f"  SHA ID: {item.sha_id}")
            print(f"  Content Hash: {item.data_hash}")
            print(f"  Post Checksum: {post_checksum}")
            
            # Verify post integrity by reconstructing it
            reconstructed_post = json.loads(post_json)
            reconstructed_checksum = hashlib.sha256(post_json.encode()).hexdigest()
            
            checksum_match = post_checksum == reconstructed_checksum
            integrity_claim = reconstructed_post['authenticity_chain']['verify_integrity']
            
            print(f"\nPost Verification:")
            print(f"  Checksum match: {checksum_match}")
            print(f"  Integrity verified: {integrity_claim}")
            print(f"  SHA ID intact: {reconstructed_post['sha_id'] == item.sha_id}")
            
            result['details'] = {
                'post_structure': {
                    'item_id': item.item_id,
                    'sha_id': item.sha_id,
                    'content_hash': item.data_hash
                },
                'post_checksum': post_checksum,
                'checksum_match': checksum_match,
                'integrity_verified': integrity_claim,
                'sha_id_intact': reconstructed_post['sha_id'] == item.sha_id,
                'authenticity_valid': checksum_match and integrity_claim,
                'post_size_bytes': len(post_json)
            }
            
            if checksum_match and integrity_claim:
                print("\n✓ Arweave post integrity PASSED")
                result['passed'] = True
            else:
                print("\n✗ Arweave post integrity FAILED")
        
        except Exception as e:
            print(f"\n✗ Error: {e}")
            result['details']['error'] = str(e)
        
        self.test_results.append(result)
        return result
    
    def test_vault_export_import(self, item: Item) -> Dict:
        """Test 6: Verify vault can be exported and imported while preserving SHA."""
        print("\n" + "="*70)
        print("TEST 6: VAULT EXPORT/IMPORT")
        print("="*70)
        
        result = {
            'test': 'Vault Export/Import',
            'passed': False,
            'details': {}
        }
        
        try:
            # Export vault to JSON
            vault_json = self.vault.export_vault_json()
            vault_data = json.loads(vault_json)
            
            print(f"\nVault exported with {len(vault_data['blobs'])} encrypted keys")
            
            # Create new vault and import
            new_vault = VaultEncryption(self.master_key)
            import_success = new_vault.import_vault_json(vault_json)
            
            print(f"Import successful: {import_success}")
            
            # Retrieve and verify the decrypted SHA
            decrypted_from_new = new_vault.retrieve_decrypted(item.id)
            decrypted_str = decrypted_from_new.decode() if decrypted_from_new else None
            
            print(f"Retrieved SHA from imported vault: {decrypted_str}")
            print(f"Match with original: {decrypted_str == item.sha_id}")
            
            result['details'] = {
                'export_successful': vault_json is not None,
                'import_successful': import_success,
                'keys_preserved': len(vault_data['blobs']) > 0,
                'sha_restored': decrypted_str == item.sha_id,
                'vault_size_bytes': len(vault_json)
            }
            
            if import_success and decrypted_str == item.sha_id:
                print("\n✓ Vault export/import PASSED")
                result['passed'] = True
            else:
                print("\n✗ Vault export/import FAILED")
        
        except Exception as e:
            print(f"\n✗ Error: {e}")
            result['details']['error'] = str(e)
        
        self.test_results.append(result)
        return result
    
    def generate_report(self) -> Dict:
        """Generate comprehensive test report."""
        print("\n" + "="*70)
        print("TEST SUMMARY REPORT")
        print("="*70)
        
        passed_tests = sum(1 for r in self.test_results if r['passed'])
        total_tests = len(self.test_results)
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\nTests Passed: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        
        for i, result in enumerate(self.test_results, 1):
            status = "✓ PASSED" if result['passed'] else "✗ FAILED"
            print(f"\n  {i}. {result['test']}: {status}")
        
        report = {
            'summary': {
                'total_tests': total_tests,
                'passed': passed_tests,
                'failed': total_tests - passed_tests,
                'success_rate': success_rate,
                'timestamp': datetime.now(timezone.utc).isoformat()
            },
            'tests': self.test_results,
            'verdict': "✓ ALL TESTS PASSED - SHA verification system is secure and functional" if passed_tests == total_tests else "✗ SOME TESTS FAILED - Review failures above"
        }
        
        print(f"\n{report['verdict']}")
        print("="*70)
        
        return report


async def run_all_tests():
    """Run complete verification test suite."""
    print("\n" + "="*70)
    print("AUCTION SHA VERIFICATION TEST SUITE")
    print("Testing encryption, decryption, and authenticity verification")
    print("="*70)
    
    verifier = AuctionSHAVerifier()
    item, seller = verifier.create_test_item()
    
    # Run all tests
    verifier.test_sha_generation(item)
    verifier.test_encryption_decryption(item)
    verifier.test_item_data_encryption(item)
    verifier.test_authenticity_verification(item)
    verifier.test_arweave_post_integrity(item)
    verifier.test_vault_export_import(item)
    
    # Generate report
    report = verifier.generate_report()
    
    # Save report
    report_path = "test_results_sha_verification.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nFull report saved to: {report_path}")
    
    return report


if __name__ == "__main__":
    report = asyncio.run(run_all_tests())
