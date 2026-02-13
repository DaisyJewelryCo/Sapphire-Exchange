#!/usr/bin/env python3
"""
Diagnostic script for Sapphire Exchange RPC connectivity issues.
Run this to identify which RPC endpoints are working.
"""

import asyncio
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from config.blockchain_config import blockchain_config
from blockchain.solana_usdc_client import SolanaUsdcClient


async def test_solana_rpc():
    """Test Solana RPC connectivity."""
    print("=" * 60)
    print("SOLANA RPC DIAGNOSTIC TEST")
    print("=" * 60)
    
    # Get configuration
    config = blockchain_config.get_usdc_config()
    print(f"\n📋 Configuration:")
    print(f"  Testnet: {config['solana'].get('testnet', False)}")
    print(f"  RPC URL: {config['solana'].get('rpc_url', 'NOT SET')}")
    
    # Show environment variables
    print(f"\n🔧 Environment Variables:")
    import os
    print(f"  SOLANA_RPC_URL: {os.getenv('SOLANA_RPC_URL', 'NOT SET')}")
    print(f"  SOLANA_TESTNET: {os.getenv('SOLANA_TESTNET', 'NOT SET')}")
    
    # Test client initialization
    print(f"\n🧪 Testing Solana USDC Client Initialization:")
    client = SolanaUsdcClient(config)
    
    try:
        print(f"  ⏳ Initializing client...")
        result = await asyncio.wait_for(client.initialize(), timeout=15.0)
        
        if result:
            print(f"  ✅ Client initialization SUCCESSFUL")
            
            # Test health check
            print(f"\n🏥 Testing Health Check:")
            health = await client.check_health()
            if health:
                print(f"  ✅ Health check PASSED - RPC is responsive")
            else:
                print(f"  ⚠️  Health check FAILED - RPC may be unresponsive")
        else:
            print(f"  ❌ Client initialization FAILED")
    
    except asyncio.TimeoutError:
        print(f"  ❌ Client initialization TIMEOUT (15 seconds)")
        print(f"     The RPC endpoint is not responding within timeout")
    except Exception as e:
        print(f"  ❌ Client initialization ERROR: {e}")
    
    finally:
        try:
            await client.shutdown()
        except:
            pass


async def test_other_endpoints():
    """Test alternative Solana RPC endpoints."""
    print(f"\n\n{'=' * 60}")
    print("ALTERNATIVE SOLANA RPC ENDPOINTS")
    print("=" * 60)
    
    endpoints = {
        "Mainnet Beta (Official)": "https://api.mainnet-beta.solana.com",
        "Devnet (Official)": "https://api.devnet.solana.com",
        "Quicknode (Free Tier)": "https://solana-mainnet.g.alchemy.com/v2/demo",
        "Alchemy Demo": "https://solana-rpc.publicnode.com",
    }
    
    for name, url in endpoints.items():
        print(f"\n  Testing: {name}")
        print(f"  URL: {url}")
        
        config = blockchain_config.get_usdc_config()
        config['solana']['rpc_url'] = url
        
        client = SolanaUsdcClient(config)
        try:
            print(f"    ⏳ Connecting...")
            result = await asyncio.wait_for(client.initialize(), timeout=5.0)
            if result:
                print(f"    ✅ RESPONSIVE")
            else:
                print(f"    ⚠️  UNRESPONSIVE (health check failed)")
        except asyncio.TimeoutError:
            print(f"    ⏱️  TIMEOUT")
        except Exception as e:
            print(f"    ❌ ERROR: {str(e)[:50]}")
        finally:
            try:
                await client.shutdown()
            except:
                pass


def main():
    """Run all diagnostic tests."""
    try:
        asyncio.run(test_solana_rpc())
        asyncio.run(test_other_endpoints())
        
        print(f"\n\n{'=' * 60}")
        print("RECOMMENDATIONS")
        print("=" * 60)
        print("""
If all endpoints fail:
  1. Check your internet connection
  2. Check if Solana is experiencing outages: https://status.solana.com
  3. Try a paid RPC provider (Alchemy, QuickNode, Infura)

If only your configured endpoint fails:
  1. Update SOLANA_RPC_URL in .env to a working endpoint
  2. Or set SOLANA_TESTNET=true to use devnet automatically

To use a specific RPC provider:
  1. Sign up for a free tier account
  2. Get your RPC endpoint URL
  3. Add to .env: SOLANA_RPC_URL=https://your-rpc-url.com
  4. Restart the application
        """)
        
    except KeyboardInterrupt:
        print("\n\nDiagnostic cancelled by user")
        return 1
    except Exception as e:
        print(f"\nFatal error during diagnostics: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
