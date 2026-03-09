#!/usr/bin/env python3
"""
Test that all wallets (Nano, Arweave, Solana) are generated from mnemonic.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from blockchain.unified_wallet_generator import UnifiedWalletGenerator
from security.account_backup_manager import AccountBackupManager


def _write_encrypted_backup(manager, path, mnemonic, account_data, backup_blob_fields):
    ciphertext, iv, tag = manager.encrypt_account_data(account_data, mnemonic)
    payload = dict(backup_blob_fields)
    payload.update({
        'ciphertext': ciphertext.hex(),
        'iv': iv.hex(),
        'tag': tag.hex(),
    })
    path.write_text(json.dumps(payload), encoding='utf-8')


def test_wallet_generation():
    """Test that all three wallets are generated from mnemonic."""
    print("\n" + "=" * 70)
    print("TEST: Multi-Asset Wallet Generation from Mnemonic")
    print("=" * 70)
    
    wallet_gen = UnifiedWalletGenerator()
    
    # Generate a new mnemonic
    print("\n[TEST] Generating new mnemonic...")
    mnemonic = wallet_gen.generate_mnemonic(24)
    print(f"[TEST] Generated mnemonic: {mnemonic[:50]}... ({len(mnemonic.split())} words)")
    
    # Test 1: Generate wallets with explicit assets list
    print("\n[TEST] Test 1: Generating wallets for ['nano', 'arweave', 'solana']...")
    success, wallet_data = wallet_gen.generate_from_mnemonic(
        mnemonic,
        assets=['nano', 'arweave', 'solana']
    )
    
    if not success:
        print(f"❌ [TEST] Wallet generation failed")
        return False
    
    print(f"✓ [TEST] Wallet generation successful")
    print(f"[TEST] Generated wallets: {list(wallet_data.keys())}")
    
    # Check all three are present
    if 'nano' not in wallet_data:
        print(f"❌ [TEST] Nano wallet missing!")
        return False
    print(f"✓ [TEST] Nano wallet present: {wallet_data['nano'].get('address', 'N/A')[:30]}...")
    
    if 'arweave' not in wallet_data:
        print(f"❌ [TEST] Arweave wallet missing!")
        return False
    print(f"✓ [TEST] Arweave wallet present: {wallet_data['arweave'].get('address', 'N/A')[:30]}...")
    
    if 'solana' not in wallet_data:
        print(f"❌ [TEST] Solana wallet missing!")
        return False
    print(f"✓ [TEST] Solana wallet present: {wallet_data['solana'].get('address', 'N/A')[:30]}...")
    
    print("\n[TEST] Verifying Solana wallet is deterministic for the same mnemonic...")
    success_repeat, wallet_data_repeat = wallet_gen.generate_from_mnemonic(
        mnemonic,
        assets=['nano', 'arweave', 'solana']
    )
    
    if not success_repeat:
        print(f"❌ [TEST] Repeat wallet generation failed")
        return False
    
    if wallet_data_repeat['solana'].get('address') != wallet_data['solana'].get('address'):
        print(f"❌ [TEST] Solana wallet changed between runs!")
        print(f"    First:  {wallet_data['solana'].get('address')}")
        print(f"    Second: {wallet_data_repeat['solana'].get('address')}")
        return False
    print(f"✓ [TEST] Solana wallet is deterministic: {wallet_data['solana'].get('address')[:30]}...")
    
    # Test 2: Generate with default assets (should be just nano)
    print("\n[TEST] Test 2: Generating wallets with default assets (should be nano only)...")
    success2, wallet_data2 = wallet_gen.generate_from_mnemonic(mnemonic)
    
    if not success2:
        print(f"❌ [TEST] Default wallet generation failed")
        return False
    
    print(f"✓ [TEST] Default wallet generation successful")
    print(f"[TEST] Generated wallets: {list(wallet_data2.keys())}")
    
    if 'nano' not in wallet_data2:
        print(f"❌ [TEST] Nano wallet missing in default!")
        return False
    print(f"✓ [TEST] Nano wallet present in default")
    
    print("\n" + "=" * 70)
    print("✓ ALL TESTS PASSED")
    print("=" * 70)
    return True


def test_backup_recovery_prefers_saved_backup_and_validates_nano_match():
    mnemonic = "general head trim believe prefer rocket fish pull domain camera speak polar burger wealth rose senior inject shed barrel bridge nest treat bamboo avoid"
    wallet_gen = UnifiedWalletGenerator()
    success, wallet_data = wallet_gen.generate_from_mnemonic(mnemonic)
    assert success
    derived_nano = wallet_data['nano']['address']

    with tempfile.TemporaryDirectory() as temp_dir:
        backup_dir = Path(temp_dir)
        manager = AccountBackupManager(backup_dir=str(backup_dir))
        original_cwd = Path.cwd()
        os.chdir(backup_dir)

        try:
            saved_backup_path = backup_dir / "sapphire_key_backup.account.enc"
            indexed_backup_path = backup_dir / f"sapphire_backup_user_test_nano_{derived_nano.replace('nano_', '').lower()[:8]}_20260309_000000.account.enc"

            mismatched_saved_data = {
                'type': 'sapphire_key_backup',
                'username': 'Wrong Saved Backup',
                'nano_address': 'nano_7HBgtEUYY8nyPRL1Qh4cn3TscUXtAPHyAMpuMuodKERWpBAHnaq',
                'wallets': {
                    'nano': {'address': 'nano_7HBgtEUYY8nyPRL1Qh4cn3TscUXtAPHyAMpuMuodKERWpBAHnaq'},
                    'solana': {'address': 'Ha7TdX34z68cJp39z1Dxpi5damuKY2UvfjpNm6yFrSFF'},
                },
            }
            indexed_data = {
                'username': 'Indexed Backup',
                'nano_address': derived_nano,
                'wallets': {
                    'nano': {'address': derived_nano},
                    'solana': {'address': '2jKgp4GkgLEymL8dbk47vjHtA4qovjQv75F7buHoHemg'},
                },
            }

            _write_encrypted_backup(
                manager,
                saved_backup_path,
                mnemonic,
                mismatched_saved_data,
                {
                    'type': 'sapphire_key_backup_enc',
                    'nano_address': mismatched_saved_data['nano_address'],
                    'solana_address': mismatched_saved_data['wallets']['solana']['address'],
                },
            )
            _write_encrypted_backup(
                manager,
                indexed_backup_path,
                mnemonic,
                indexed_data,
                {
                    'nano_address': derived_nano,
                    'solana_address': indexed_data['wallets']['solana']['address'],
                },
            )

            result_success, account_data = __import__('asyncio').run(
                manager.restore_account_from_backup(derived_nano, mnemonic)
            )
            assert result_success is False
            assert account_data is None

            matching_saved_data = {
                'type': 'sapphire_key_backup',
                'username': 'Saved Backup',
                'nano_address': derived_nano,
                'wallets': {
                    'nano': {'address': derived_nano},
                    'solana': {'address': '6ovKYTFJoDAGZzDVmUnmqtCZJbp62PzpEzjhY9NYwcoH'},
                },
            }
            _write_encrypted_backup(
                manager,
                saved_backup_path,
                mnemonic,
                matching_saved_data,
                {
                    'type': 'sapphire_key_backup_enc',
                    'nano_address': derived_nano,
                    'solana_address': matching_saved_data['wallets']['solana']['address'],
                },
            )

            result_success, account_data = __import__('asyncio').run(
                manager.restore_account_from_backup(derived_nano, mnemonic)
            )
            assert result_success is True
            assert account_data is not None
            assert account_data['nano_address'] == derived_nano
            assert account_data['wallets']['solana']['address'] == '6ovKYTFJoDAGZzDVmUnmqtCZJbp62PzpEzjhY9NYwcoH'
        finally:
            os.chdir(original_cwd)


if __name__ == "__main__":
    try:
        result = test_wallet_generation()
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"\n❌ TEST FAILED WITH EXCEPTION:")
        print(f"{type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
