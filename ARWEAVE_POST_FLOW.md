# Arweave Post Flow Architecture

## Overview

The Arweave post flow system creates a distributed, immutable auction platform where:
- **Each auction creates its own independent Arweave post** (immutable)
- Posts contain current auction details (top section) + expiring auctions list (bottom section)
- Posts are identified by **deterministic sequence numbers** checked against Nano wallets
- Bids are recorded on Nano wallets; auctions query wallets for current bid data
- **Auctions are created locally** → previewed in Dev Tools → posted to Arweave when ready
- Users can batch multiple auctions into individual posts before posting

## Architecture Components

### 1. Auction Wallet Manager (`utils/auction_wallet_manager.py`)

Generates deterministic Nano wallets for each auction derived from the user's master seed.

**Key Features:**
- **Deterministic Wallet Generation**: Each auction wallet is derived from:
  - User's master Nano seed (index 0)
  - Item ID → SHA-256 hash → 32-bit index
  - This ensures wallets can be recovered from seed + item ID
  
- **Wallet Structure**:
  ```python
  {
      'nano_address': str,           # Nano address for auction
      'nano_public_key': str,        # Public key (hex)
      'nano_private_key': str,       # Private key (hex, encrypted)
      'nano_seed': str,              # Seed (hex, encrypted)
      'wallet_index': int,           # Deterministic index from item_id
      'item_id': str                 # Associated auction item
  }
  ```

**Usage:**
```python
from utils.auction_wallet_manager import auction_wallet_manager

wallet = auction_wallet_manager.create_auction_wallet(user_seed, item_id)
# Later: recover wallet from seed
recovered = auction_wallet_manager.recreate_auction_wallet_from_seed(user_seed, item_id)
```

### 2. Arweave Post Service (`services/arweave_post_service.py`)

Creates individual auction posts and aggregates data from Nano wallets. Each post is immutable and searchable.

**Key Features:**

- **Individual Auction Post Structure**:
  ```python
  {
      'version': '1.0',
      'sequence': int,               # Deterministic sequence number
      'created_at': str,             # ISO 8601 timestamp
      'posted_by': str,              # User ID who created auction
      
      'auction': {                   # TOP SECTION: Current auction
          'item_id': str,
          'seller_id': str,
          'title': str,
          'description': str,
          'starting_price_doge': str,
          'current_bid_doge': str,
          'current_bidder': str,
          'auction_end': str,
          'status': str,             # 'active', 'sold', 'expired'
          'auction_rsa_fingerprint': str,
          'auction_nano_address': str,
          'auction_nano_public_key': str
      },
      
      'expiring_auctions': [         # BOTTOM SECTION: Auctions expiring <24h
          {
              'item_id': str,
              'title': str,
              'current_bid_doge': str,
              'current_bidder': str,
              'auction_end': str,
              'auction_rsa_fingerprint': str,
              'top_bidder_nano_address': str
          },
          ...
      ]
  }
  ```

**Key Methods:**

| Method | Purpose |
|--------|---------|
| `create_auction_post(item, user, expiring_auctions, sequence_wallet)` | Generate individual post with sequence number |
| `post_auction_to_arweave(post_data, user)` | Post to Arweave with AR balance check |
| `search_auction_posts(sequence_start, sequence_end, date_start, date_end)` | Search by sequence/date range |
| `aggregate_auction_data(posts)` | Merge post data and fetch current bids from Nano |
| `get_expiring_auctions(hours_until_expiry)` | Find auctions ending soon |
| `verify_winner_from_nano(nano_address, auction_end_time)` | Check Nano wallet for winner |

### 3. Arweave Dev Tools Widget (`ui/arweave_dev_tools_widget.py`)

Provides in-app UI for previewing and managing Arweave posts before posting to the network.

**Features:**
- **Post Preview List**: Shows all locally generated posts waiting to be posted
- **Multiple View Modes**: Preview, Structure, JSON, Metadata-only
- **Post Export**: Save previews to file for inspection
- **Batch Control**: Clear all posts, view individual posts
- **Cost Estimation**: Shows estimated AR posting cost
- **Post to Arweave**: Direct posting from dev tools with confirmation

**Integration Point:**
Located in main window Dev Tools tab (index 4 in content stack)

## Data Flow

### Creating an Auction (Local Generation Only)

```
1. User fills auction creation dialog
   ├─ Generate RSA key pair for auction authenticity
   ├─ Generate deterministic Nano wallet from user_seed + item_id
   ├─ Create auction locally (stored in app memory/database)
   └─ Dialog closes successfully

2. Auction is now ready for preview
   ├─ User navigates to Dev Tools tab
   ├─ ArweaveDevToolsWidget displays generated Arweave post preview
   ├─ User can inspect post structure, JSON, costs
   └─ User can export preview to file for inspection

3. User can create more auctions before posting
   ├─ Each new auction is added to Dev Tools preview list
   ├─ User can view all pending posts
   └─ No posts sent to Arweave yet (offline)
```

### Placing a Bid

```
1. Bidder places bid on active auction
   ├─ Create Nano transaction to auction wallet
   │  ├─ Amount: bid amount converted to NANO
   │  └─ Memo: "bid:{amount_doge}"
   ├─ Transaction confirmed on Nano network
   └─ Bid recorded in Nano wallet (immutable)

2. Current bid always queried from Nano wallet
   ├─ Application queries auction's Nano address
   ├─ Fetches account balance and transaction history
   ├─ Highest depositor's amount = current bid
   └─ No secondary Arweave update needed
```

### Posting to Arweave (When Ready)

```
1. User clicks "Post to Arweave" in Dev Tools
   ├─ System generates Arweave post with:
   │  ├─ Current auction in top section
   │  ├─ Expiring auctions list in bottom section
   │  └─ Sequence number (deterministic from Nano wallet check)
   ├─ Check AR balance (minimum 0.05 AR required)
   └─ Send post to Arweave network

2. Post is now immutable on Arweave
   ├─ Identified by sequence number
   ├─ Tagged with auction metadata
   ├─ Retrievable via search (sequence/date range)
   └─ Provides audit trail
```

### Syncing Bids from Nano Wallets

```
1. When post is retrieved from Arweave
   ├─ Application fetches auction Nano wallet address
   ├─ Queries Nano account info
   ├─ Parses transaction history
   ├─ Calculates current bid (highest deposit)
   └─ Updates post's "current_bid_doge" field dynamically
   
2. No need to re-post to Arweave for bid updates
   ├─ Arweave post is immutable (contains placeholder bids)
   ├─ Live bid data always queried from Nano
   ├─ Arweave serves as immutable audit log
   └─ Nano is source of truth for bids
```

## Nano Wallet Transaction Structure

**First Transaction (Item Announcement):**
```
From: User's index-1 Nano wallet
To: Auction Nano wallet
Amount: Minimal (e.g., 0.000001 NANO)
Memo: "item:{item_id}"
Purpose: Announce item listing
```

**Bid Transactions:**
```
From: Bidder's Nano wallet
To: Auction Nano wallet
Amount: Bid amount converted to NANO
Memo: "bid:{bid_amount_doge}"
Purpose: Place bid with amount metadata
```

**Winner Verification:**
- Highest amount transaction = highest bid
- From-address of highest transaction = winner
- Memo field = bid amount for verification

## Arweave Tag Structure

**Master Post Tags:**
```
Content-Type: application/json
App-Name: Sapphire-Exchange
Data-Type: auction-master-post
Posted-By: {user_id}
Auction-Count: {count}
Version: 1.0
```

**Individual Auction Tags:**
```
Content-Type: application/json
App-Name: Sapphire-Exchange
Data-Type: auction-item
Seller-ID: {seller_id}
Item-ID: {item_id}
Auction-Nano-Address: {nano_address}
```

**Bid Tags:**
```
Content-Type: application/json
App-Name: Sapphire-Exchange
Data-Type: bid
Item-ID: {item_id}
Bidder-ID: {bidder_id}
Currency: DOGE/NANO
Nano-Address: {auction_nano_address}
```

## AR Cost Structure

- **Account Creation**: 0.05 AR
- **Auction Post**: 0.05 AR per post update
- **Enforcement**: Checked before posting, with user warning

## Key Security Features

1. **Deterministic Wallet Recovery**: Users can regenerate auction wallets from their master seed
2. **Memo-based Bid Verification**: Bid amounts recorded in Nano transaction memos
3. **Distributed Consensus**: Winner confirmations tracked across multiple posts
4. **Data Integrity**: SHA-256 hashes verify auction data hasn't changed
5. **Encrypted Keys**: Private keys and seeds encrypted before storage

## Integration Points

### With Application Service
```python
# In application_service.py
await app_service.auction_service.create_auction(user, item_data, user_seed)
await app_service.auction_service.place_bid(bidder, item, amount)
success, msg, tx_id = await app_service.auction_service.post_auction_database_to_arweave(user)
```

### With UI Layer
- Create Auction Dialog: Collect item data, pass user seed
- Place Bid Dialog: Show auction wallet address for transparency
- Post Master Dialog: Show AR balance check, cost warning, finished auction count
- Master Post Summary: Display in dashboard

### With Blockchain Manager
- **Nano Operations**: Send Nano with memo support
- **Arweave Operations**: Store/retrieve master posts with tags
- **Balance Checking**: Verify AR balance before posting

## Future Enhancements

1. **Batch Posting**: Multiple auctions per Arweave transaction
2. **Auction Archival**: Move old auctions to archive posts
3. **Nano Indexing**: Full transaction history parsing for advanced bid tracking
4. **Winner Dispute Resolution**: Require confirmations from multiple nodes
5. **Fee Optimization**: Dynamic AR cost based on post size

## Example Flow: Complete Auction Cycle

```
1. User registers (creates index-0 Nano wallet)

2. User creates first auction
   - Generate index-1 Nano wallet from seed + item_id
   - Post item data to Arweave
   - Store in local master post

3. User creates second auction
   - Generate index-2 Nano wallet from seed + item_id
   - Post item data to Arweave
   - Add to local master post

4. User posts auction database (0.05 AR)
   - Check AR balance (min 0.05 AR)
   - Verify no finished auctions
   - Post master with both auctions to Arweave (TX_1)

5. Bidder A bids 50 DOGE on auction 1
   - Send NANO to auction 1 wallet with memo "bid:50"
   - Bid stored on Arweave
   - Master post updated in memory

6. Bidder B bids 75 DOGE on auction 1
   - Send NANO to auction 1 wallet with memo "bid:75"
   - Bid stored on Arweave
   - Master post updated in memory

7. User posts updated database (0.05 AR)
   - Syncs latest bids from Nano wallets
   - Master post now shows 75 DOGE highest bid
   - Posts updated master to Arweave (TX_2)

8. Auction 1 expires
   - Application detects end time
   - Verifies Bidder B as winner from Nano wallet
   - Updates master post status to 'sold'
   - Posts final auction update (TX_3)

9. Auction 2 expires with no bids
   - Status updated to 'expired'
   - Master post updated

10. User can load master post anytime
    - Fetch TX_3 from Arweave
    - View all auction history
    - Verify winners and bid amounts
```

## Implementation Checklist

- [x] Auction wallet manager with deterministic generation
- [x] Arweave post service with master post aggregation
- [x] Nano memo support in blockchain manager
- [x] Auction service integration with new flow
- [x] AR balance validation before posting
- [x] Winner verification from Nano wallets
- [x] Auction expiration checking
- [ ] UI integration (create auction dialog, post master dialog)
- [ ] Application service integration updates
- [ ] Testing and edge case handling
