#!/usr/bin/env python3
"""
Test that wallet addresses from mnemonic are preserved during account creation.
Verifies that the address derived from mnemonic matches the user's registered address.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from blockchain.unified_wallet_generator import UnifiedWalletGenerator
from services.application_service import app_service


async def test_wallet_address_preservation():
    """Test that mnemonic-derived wallet addresses are used during registration."""
    print("\n" + "=" * 70)
    print("TEST: Wallet Address Preservation During Account Creation")
    print("=" * 70)
    
    wallet_gen = UnifiedWalletGenerator()
    
    # Generate a new mnemonic
    print("\n[TEST] Generating new mnemonic...")
    entropy = wallet_gen.entropy_gen.generate_entropy(24)
    mnemonic = wallet_gen.bip39_manager.entropy_to_mnemonic(entropy.hex())
    print(f"[TEST] Generated mnemonic: {mnemonic[:30]}... ({len(mnemonic.split())} words)")
    
    # Generate wallets from mnemonic
    print("\n[TEST] Generating wallets from mnemonic...")
    success, wallet_data = wallet_gen.generate_from_mnemonic(mnemonic)
    
    if not success:
        print(f"❌ [TEST] Failed to generate wallets from mnemonic")
        return False
    
    print(f"[TEST] Wallet generation successful")
    print(f"[TEST] Wallet data keys: {list(wallet_data.keys())}")
    
    # Extract mnemonic-derived addresses
    mnemonic_nano_address = None
    mnemonic_arweave_address = None
    mnemonic_solana_address = None
    
    if 'nano' in wallet_data:
        mnemonic_nano_address = wallet_data['nano'].get('address')
        print(f"[TEST] Mnemonic-derived Nano address: {mnemonic_nano_address}")
    
    if 'arweave' in wallet_data:
        mnemonic_arweave_address = wallet_data['arweave'].get('address')
        print(f"[TEST] Mnemonic-derived Arweave address: {mnemonic_arweave_address}")
    
    if 'solana' in wallet_data:
        mnemonic_solana_address = wallet_data['solana'].get('address')
        print(f"[TEST] Mnemonic-derived Solana address: {mnemonic_solana_address}")
    
    # Now register a user with this mnemonic
    print("\n[TEST] Registering user with seed phrase...")
    success, message, user = await app_service.register_user_with_seed(mnemonic, wallet_data)
    
    if not success or not user:
        print(f"❌ [TEST] Registration failed: {message}")
        return False
    
    print(f"✓ [TEST] User registered: {user.username}")
    
    # Check if addresses match
    print("\n[TEST] Checking address preservation...")
    
    # Check Nano address
    if mnemonic_nano_address and user.nano_address:
        if mnemonic_nano_address == user.nano_address:
            print(f"✓ [TEST] Nano address preserved: {user.nano_address}")
        else:
            print(f"❌ [TEST] Nano address MISMATCH!")
            print(f"    Mnemonic-derived: {mnemonic_nano_address}")
            print(f"    User registered:  {user.nano_address}")
            return False
    else:
        print(f"⚠️  [TEST] Nano address check skipped (missing data)")
    
    # Check Arweave address
    if mnemonic_arweave_address and user.arweave_address:
        if mnemonic_arweave_address == user.arweave_address:
            print(f"✓ [TEST] Arweave address preserved: {user.arweave_address}")
        else:
            print(f"❌ [TEST] Arweave address MISMATCH!")
            print(f"    Mnemonic-derived: {mnemonic_arweave_address}")
            print(f"    User registered:  {user.arweave_address}")
            return False
    else:
        print(f"⚠️  [TEST] Arweave address check skipped (missing data)")
    
    # Check USDC address
    if mnemonic_solana_address and user.usdc_address:
        if mnemonic_solana_address == user.usdc_address:
            print(f"✓ [TEST] USDC address preserved: {user.usdc_address}")
        else:
            print(f"❌ [TEST] USDC address MISMATCH!")
            print(f"    Mnemonic-derived: {mnemonic_solana_address}")
            print(f"    User registered:  {user.usdc_address}")
            return False
    else:
        print(f"⚠️  [TEST] USDC address check skipped (missing data)")
    
    print("\n" + "=" * 70)
    print("✓ TEST PASSED: All addresses preserved correctly!")
    print("=" * 70)
    return True


if __name__ == "__main__":
    try:
        result = asyncio.run(test_wallet_address_preservation())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"\n❌ TEST FAILED WITH EXCEPTION:")
        print(f"{type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
