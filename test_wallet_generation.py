#!/usr/bin/env python3
"""
Test that all wallets (Nano, Arweave, Solana) are generated from mnemonic.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from blockchain.unified_wallet_generator import UnifiedWalletGenerator


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
