"""
Test script for verifying marketplace functionality including item creation,
display, and bidding with Nano and Arweave integration.
"""
import asyncio
import sys
import os
from datetime import datetime, timezone, timedelta

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from decentralized_client import EnhancedDecentralizedClient
from mock_server import arweave_db, nano_db

async def test_marketplace():
    print("=== Testing Marketplace Functionality ===")
    
    # Initialize client with mock mode
    client = EnhancedDecentralizedClient(mock_mode=True)
    
    # Test data
    seed_phrase = "test_seed_123"
    username = "test_user"
    first_name = "Test"
    last_name = "User"
    
    # Step 1: Create a new user
    print("\n1. Creating a new user...")
    success = await client.login(seed_phrase, username, first_name, last_name)
    if not success:
        print("Failed to create user")
        return
    
    print(f"Created user: {client.current_user.username}")
    
    # Step 2: Get user balance
    balance = await client.get_balance()
    print(f"User balance: {balance} NANO")
    
    # Step 3: Create a new item
    print("\n2. Creating a new item...")
    item_data = {
        'name': 'Test Item',
        'description': 'A test item for the marketplace',
        'starting_price': 10.0,
        'duration_hours': 24,
        'metadata': {
            'category': 'test',
            'condition': 'new',
            'nano_tag': 'nano_test_item_001'  # Unique Nano tag for this item
        }
    }
    
    item_id = await client.create_item(**item_data)
    print(f"Created item with ID: {item_id}")
    
    # Add a small delay to ensure the item is confirmed in the mock database
    print("\nWaiting for item confirmation...")
    await asyncio.sleep(0.5)  # Short delay to ensure confirmation
    
    # Step 4: Get item details
    print("\n3. Retrieving item details...")
    item = await client.get_item(item_id)
    if item:
        print(f"Item details:")
        print(f"  Name: {item.get('name', 'N/A')}")
        print(f"  Description: {item.get('description', 'N/A')}")
        print(f"  Current Price: {item.get('current_price', item.get('starting_price', 'N/A'))} NANO")
        print(f"  Owner: {item.get('owner_username', 'N/A')}")
        print(f"  Status: {item.get('status', 'N/A')}")
        print(f"  Nano Tag: {item.get('metadata', {}).get('nano_tag', 'N/A')}")
    else:
        print(f"Failed to retrieve item details for ID: {item_id}")
        print(f"Available items: {arweave_db.items.keys()}")
        print(f"Pending transactions: {arweave_db.pending_transactions.keys()}")
        return
    
    # Step 5: Get marketplace items
    print("\n4. Listing marketplace items...")
    marketplace_items = await client.get_user_inventory()
    print(f"Found {len(marketplace_items)} items in the marketplace:")
    for idx, market_item in enumerate(marketplace_items, 1):
        print(f"  {idx}. {market_item['name']} - {market_item['current_price']} NANO")
    
    # Step 6: Place a bid on the item
    print("\n5. Placing a bid on the item...")
    bid_amount = float(item['current_price']) + 1.0  # Bid 1 NANO higher than current price
    try:
        bid_success = await client.place_bid(item_id, bid_amount)
        if bid_success:
            print(f"Successfully placed bid of {bid_amount} NANO on item")
            
            # Verify the bid was recorded
            updated_item = await client.get_item(item_id)
            print(f"Updated item price: {updated_item['current_price']} NANO")
            print(f"Number of bids: {len(updated_item['bids'])}")
            
            # Verify the bid details
            if updated_item['bids']:
                last_bid = updated_item['bids'][-1]
                print(f"Last bid amount: {last_bid['amount']} NANO")
                print(f"Bid timestamp: {last_bid['timestamp']}")
        else:
            print("Failed to place bid")
    except Exception as e:
        print(f"Error placing bid: {e}")
    
    # Step 7: Verify Nano balance after bid
    new_balance = await client.get_balance()
    print(f"\n6. Balance after bid: {new_balance} NANO")
    print(f"Bid amount: {bid_amount} NANO")
    print(f"Expected balance: {balance - bid_amount} NANO")
    
    # Step 8: Verify Arweave data
    print("\n7. Verifying Arweave data...")
    try:
        arweave_item = await arweave_db.get_data(item_id)
        if arweave_item:
            print("Item data found in Arweave mock database:")
            print(f"  Name: {arweave_item.get('name', 'N/A')}")
            print(f"  Description: {arweave_item.get('description', 'N/A')}")
            print(f"  Current Price: {arweave_item.get('current_price', 'N/A')} NANO")
            print(f"  Owner: {arweave_item.get('owner_username', 'N/A')}")
        else:
            print("Item data not found in Arweave mock database")
    except Exception as e:
        print(f"Error retrieving Arweave data: {e}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    asyncio.run(test_marketplace())
