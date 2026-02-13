#!/usr/bin/env python3
"""
Simple diagnostic script to check RPC configuration without heavy dependencies.
"""

import os
from pathlib import Path

def main():
    """Check RPC configuration."""
    print("=" * 70)
    print("SOLANA RPC CONFIGURATION DIAGNOSTIC")
    print("=" * 70)
    
    # Check environment file
    env_file = Path(__file__).parent / ".env"
    print(f"\n📄 Environment File: {env_file}")
    print(f"   Exists: {'✅ Yes' if env_file.exists() else '❌ No'}")
    
    if env_file.exists():
        print(f"\n📋 Contents of .env file:")
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    print(f"   {line}")
    
    # Check environment variables
    print(f"\n🔧 Current Environment Variables:")
    
    solana_rpc = os.getenv('SOLANA_RPC_URL')
    solana_testnet = os.getenv('SOLANA_TESTNET', 'false').lower()
    
    print(f"   SOLANA_RPC_URL: {solana_rpc or '❌ NOT SET (will use default)'}")
    print(f"   SOLANA_TESTNET: {solana_testnet or 'false'}")
    
    # Show what will be used
    print(f"\n💡 Configuration that will be used:")
    
    if solana_rpc:
        print(f"   RPC Endpoint: {solana_rpc}")
    else:
        default_rpc = "https://api.mainnet-beta.solana.com"
        print(f"   RPC Endpoint: {default_rpc} (default)")
    
    if solana_testnet == 'true':
        print(f"   Network: Devnet (SOLANA_TESTNET=true)")
    else:
        print(f"   Network: Mainnet (SOLANA_TESTNET=false or not set)")
    
    # Recommendations
    print(f"\n📝 Recommendations:")
    
    if not solana_rpc or solana_rpc == "https://api.mainnet-beta.solana.com":
        print(f"""
   The default Solana RPC endpoint may be rate-limited or down.
   
   To fix this, update your .env file with one of these options:
   
   Option 1: Use Devnet for testing
   --------------------------------
   SOLANA_RPC_URL=https://api.devnet.solana.com
   SOLANA_TESTNET=true
   
   Option 2: Use a free public endpoint
   ----------------------------------------
   SOLANA_RPC_URL=https://solana-rpc.publicnode.com
   SOLANA_TESTNET=false
   
   Option 3: Sign up for a paid RPC service (recommended)
   -------------------------------------------------------
   - Alchemy: https://www.alchemy.com/
   - QuickNode: https://www.quicknode.com/
   - Infura: https://infura.io/
   
   Then add your endpoint URL to .env:
   SOLANA_RPC_URL=https://your-key.solana-mainnet.quiknode.pro
        """)
    else:
        print(f"   ✅ Custom RPC endpoint is configured")
        print(f"      {solana_rpc}")
    
    print(f"\n{'=' * 70}")
    print("After making changes:")
    print("  1. Save the .env file")
    print("  2. Restart the Sapphire Exchange application")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
