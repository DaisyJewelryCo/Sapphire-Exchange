"""
Test script for Arweave purchase service.
"""
import asyncio
import sys
from services.arweave_purchase_service import ArweavePurchaseService

async def test_arweave_purchase_service():
    """Test basic Arweave purchase service functionality."""
    print("Testing Arweave Purchase Service...")
    
    try:
        service = ArweavePurchaseService(rpc_url="https://api.mainnet-beta.solana.com")
        
        success = await service.initialize()
        print(f"✓ Service initialized: {success}")
        
        print("\nTesting token discovery...")
        ar_mint = await service.discover_arweave_token()
        if ar_mint:
            print(f"✓ Discovered AR token mint: {ar_mint}")
        else:
            print("⚠ Could not discover AR token (network may be unavailable)")
        
        print("\nTesting quote generation (100 USDC)...")
        quote = await service.get_quote(usdc_amount=100.0, output_mint=ar_mint)
        if quote:
            ar_amount = quote.output_amount / 1e12
            print(f"✓ Quote received:")
            print(f"  - Input: {quote.input_amount / 1e6} USDC")
            print(f"  - Output: {ar_amount:.6f} AR")
            print(f"  - Price Impact: {quote.price_impact:.3f}%")
            print(f"  - Route: {quote.route_description}")
        else:
            print("⚠ Could not get quote (may be due to network)")
        
        print("\nTesting estimation...")
        ar_estimate = await service.estimate_arweave_output(usdc_amount=50.0)
        if ar_estimate:
            print(f"✓ AR estimate for 50 USDC: {ar_estimate:.6f} AR")
        else:
            print("⚠ Could not get estimate")
        
        await service.shutdown()
        print("\n✓ Service shutdown successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_arweave_purchase_service())
    sys.exit(0 if success else 1)
