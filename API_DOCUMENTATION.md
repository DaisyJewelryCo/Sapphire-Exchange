# Sapphire Exchange API Documentation

This document provides comprehensive details on three core processes: **Login**, **Create Item**, and **Arweave Post Creation**.

---

## 1. Login Process

### Overview
The login process authenticates a user with a seed phrase, generates wallets for supported blockchains, and creates a user session.

### Login Flow

#### Entry Point
**File**: [./ui/login_screen.py](./ui/login_screen.py:221)  
**Method**: `LoginScreen.handle_login()`

### Step 1: Seed Phrase Validation

**Variables**:
- **`seed_phrase`** (string): 12, 15, 18, 21, or 24 space-separated BIP39 words
  - Example: `"abandon ability able about above absent absorb abstract abuse access accident account"`
  - Must match one of: 12, 15, 18, 21, or 24 word counts

**Validation Logic**:
```python
words = seed_phrase.strip().split()
if len(words) not in [12, 15, 18, 21, 24]:
    # Invalid length error
```

### Step 2: Async Login Process

**File**: [./services/application_service.py](./services/application_service.py:182)  
**Method**: `ApplicationService.login_user_with_seed(seed_phrase)`

**Variables Generated**:
- **`username_hash`** (int): Hash of seed phrase modulo 1,000,000
- **`username`** (string): Format `user_{username_hash:06d}` (e.g., `user_123456`)
- **`password`** (string): Format `Pw1@{seed_phrase[:20]}` - derived from seed phrase
  - Includes uppercase, digit, and special character for complexity requirements

### Step 3: User Authentication

**File**: [./services/user_service.py](./services/user_service.py:35)  
**Method**: `UserService.authenticate_user(username, password)`

**Variables**:
- **`username`** (string): Generated username from step 2
- **`password`** (string): Generated password from step 2

**Returned Variables**:
- **`user`** (User object): Contains:
  - `id` (string): UUID4
  - `username` (string): User's username
  - `password_hash` (string): Bcrypt hash of password
  - `nano_address` (string): User's Nano wallet address
  - `arweave_address` (string): User's Arweave wallet address
  - `usdc_address` (string, optional): User's USDC address
  - `created_at` (string): ISO 8601 timestamp
  - `is_active` (bool): True if account is active
  - `reputation_score` (float): User's reputation (default 0.0)
  - `total_sales` (int): Number of items sold
  - `total_purchases` (int): Number of items purchased

- **`session_token`** (string): Session identifier for authenticated requests

### Step 4: Wallet Generation

**File**: [./blockchain/unified_wallet_generator.py](./blockchain/unified_wallet_generator.py)  
**Method**: `UnifiedWalletGenerator.generate_from_mnemonic(seed_phrase, passphrase)`

**Input Variables**:
- **`seed_phrase`** (string): BIP39 mnemonic phrase
- **`passphrase`** (string): Optional BIP39 passphrase (empty in login flow)

**Returned Wallet Data** (dictionary):
```python
wallet_data = {
    'solana': {
        'address': 'string',      # Solana public address
        'public_key': 'bytes',
        'private_key': 'bytes'
    },
    'nano': {
        'address': 'string',      # Nano public address
        'public_key': 'string',   # Nano hex public key
        'private_key': 'string'   # Nano hex private key
    },
    'arweave': {
        'address': 'string',      # Arweave public key
        'public_key': 'JWK',      # JSON Web Key
        'private_key': 'JWK'      # JSON Web Key
    }
}
```

### Step 5: User Session Management

**File**: [./services/application_service.py](./services/application_service.py:49)

**Session Variables Stored**:
- **`current_user`** (User object): The authenticated user
- **`current_session`** (string): Session token
- **`is_initialized`** (bool): Application initialization state

### Login Output

**Success Response**:
```python
return (
    success=True,
    message="Login successful",
    user=User(id, username, addresses, etc.)
)
```

**Failure Response**:
```python
return (
    success=False,
    message="Invalid seed phrase" or error_description,
    user=None
)
```

---

## 2. Create Item (Auction) Method

### Overview
Creates a new auction item with Nano wallet integration and stores metadata on Arweave.

### Entry Point
**File**: [./services/application_service.py](./services/application_service.py:271)  
**Method**: `ApplicationService.create_auction(item_data)`

### Prerequisites
- User must be logged in: `app_service.current_user` must not be None
- User must have valid blockchain addresses

### Input Variables (item_data dictionary)

**Required Variables**:
- **`title`** (string): Item name/title
  - Example: `"Vintage Rolex Watch"`
  - Max length: typically 200 characters

- **`description`** (string): Detailed item description
  - Example: `"Excellent condition, original box and papers"`
  - Max length: typically 5000 characters

- **`starting_price_usdc`** (float): Starting bid price in USDC
  - Example: `100.50`
  - Must be positive number

- **`auction_end`** (string, ISO 8601) OR `auction_duration_hours` (int)
  - ISO 8601 format: `"2024-12-31T23:59:59Z"`
  - Duration format: `168` (hours from now)
  - If duration provided, converted to `auction_end` automatically

**Optional Variables**:
- **`category`** (string): Item category
  - Example: `"watches"`, `"art"`, `"collectibles"`

- **`tags`** (list of strings): Search tags
  - Example: `["vintage", "rolex", "watch"]`

- **`shipping_required`** (bool): Whether shipping is needed
  - Default: `False`

- **`shipping_cost_usdc`** (float): Cost of shipping if required
  - Example: `15.99`
  - Default: `0.0`

### Item Creation Process

**File**: [./services/auction_service.py](./services/auction_service.py:31)  
**Method**: `AuctionService.create_auction(seller, item_data)`

### Variables Created

**Item Object** ([./models/models.py](./models/models.py:104)):
```python
item = Item(
    item_id = str(uuid.uuid4()),           # Unique item identifier
    sha_id = sha256_hash(seller_id + title + description + created_at),  # Secondary hash ID
    seller_id = current_user.id,           # ID of seller
    title = item_data['title'],
    description = item_data['description'],
    starting_price_usdc = str(starting_price),
    current_bid_usdc = None,               # No bids yet
    current_bidder = None,                 # No bidder yet
    auction_end = item_data['auction_end'],
    status = 'active',                     # 'draft' -> 'active' after Arweave confirmation
    category = item_data.get('category', ''),
    tags = item_data.get('tags', []),
    shipping_required = item_data.get('shipping_required', False),
    shipping_cost_usdc = str(item_data.get('shipping_cost_usdc', 0.0)),
    created_at = datetime.now(timezone.utc).isoformat(),
    updated_at = None,
    data_hash = sha256_hash(seller_id + title + description + created_at),
    metadata = {},
    
    # Nano Wallet for this auction
    auction_nano_address = generated_address,
    auction_nano_public_key = generated_public_key,
    auction_nano_private_key = encrypted_private_key,
    auction_nano_seed = encrypted_seed,
    auction_wallet_created_at = datetime.now(timezone.utc).isoformat(),
    
    # Arweave Storage
    arweave_metadata_uri = transaction_id,
    arweave_confirmed = True/False
)
```

### Nano Wallet Creation

**File**: [./utils/auction_wallet_manager.py](./utils/auction_wallet_manager.py)  
**Method**: `AuctionWalletManager.create_auction_wallet(user_seed, item_id)`

**Variables Generated**:
- **`nano_address`** (string): Public wallet address for this auction
  - Used to receive bids and track payments
- **`nano_public_key`** (string): Nano public key (hex format)
- **`nano_private_key`** (string): Nano private key (encrypted storage)
- **`nano_seed`** (string): Nano seed phrase (encrypted storage)

### Item Announcement Transaction

If auction wallet created successfully:

**Transaction Details**:
- **`from_address`** (string): Seller's Nano address
- **`to_address`** (string): Auction's new Nano address
- **`amount`** (raw): 0.000001 NANO (1 µNANO)
- **`memo`** (string): Item's SHA ID (first 32 characters)

### Arweave Storage

**File**: [./services/auction_service.py](./services/auction_service.py:99)

**Arweave Tags** (metadata):
```python
tags = [
    ("Content-Type", "application/json"),
    ("App-Name", "Sapphire-Exchange"),
    ("Data-Type", "auction-item"),
    ("Seller-ID", seller.id),
    ("Item-ID", item.id),
    ("SHA-ID", item.sha_id),
    ("Auction-Nano-Address", item.auction_nano_address)  # Optional
]
```

**Stored Data** (item.to_dict()):
- All item fields converted to JSON dictionary
- Stored permanently on Arweave blockchain

**Variables Returned**:
- **`tx_id`** (string): Arweave transaction ID
  - If successful: Item status changed to `'active'`
  - If failed: Item remains in `'draft'` status

### Create Item Output

**Success Response**:
```python
return (
    success=True,
    message="Auction created successfully",
    item=Item(with all fields populated)
)
```

**Failure Response**:
```python
return (
    success=False,
    message="Error description",
    item=None
)
```

---

## 3. Arweave Post Creation

### Overview
Creates a consolidated auction post on Arweave containing:
1. **Top Section**: Current auction details (title, description, RSA fingerprint, Nano address)
2. **Bottom Section**: List of auctions expiring in next 24 hours

### Entry Point
**File**: [./services/arweave_post_service.py](./services/arweave_post_service.py:95)  
**Method**: `ArweavePostService.create_auction_post(item, user, expiring_auctions, sequence_wallet)`

### Input Variables

**Required**:
- **`item`** (Item object): The auction item being posted
  - Must have: `auction_rsa_fingerprint`, `auction_nano_address`

- **`user`** (User object): User creating the post
  - Used for sequence validation

**Optional**:
- **`expiring_auctions`** (list of Item objects): Auctions ending in next 24 hours
  - Included in "bottom section" of post
  - Default: None (service will retrieve if needed)

- **`sequence_wallet`** (string): Nano wallet for sequence validation
  - Default: Uses `item.auction_nano_address`

### Sequence Number Generation

**File**: [./utils/sequence_generator.py](./utils/sequence_generator.py)

**Variables**:
- **`sequence`** (int): Unique sequential identifier
  - Generated based on user and wallet
  - Used to prevent duplicate posts

**Generated By**:
```python
sequence = await self.sequence_generator.get_next_available_sequence(
    user_id=user.id,
    wallet=sequence_wallet or item.auction_nano_address
)
```

### Post Data Structure

**Returned post_data dictionary**:

```python
post_data = {
    # Metadata
    'version': '1.0',                      # API version
    'sequence': int,                        # Unique sequence number
    'created_at': ISO_8601_timestamp,      # When post was created
    'posted_by': user.id,                  # User ID who created post
    
    # Top Section: Current Auction Details
    'auction': {
        'item_id': item.id,
        'seller_id': item.seller_id,
        'title': item.title,
        'description': item.description,
        'starting_price_usdc': float,      # Starting price
        'current_bid_usdc': float,         # Current highest bid
        'current_bidder': string or None,  # Current bidder ID
        'auction_end': ISO_8601_timestamp, # When auction ends
        'status': string,                  # 'active', 'sold', 'expired'
        'auction_rsa_fingerprint': string, # RSA fingerprint for verification
        'auction_rsa_public_key': string,  # RSA public key
        'auction_nano_address': string,    # Nano wallet for bids
        'auction_nano_public_key': string, # Nano public key
    },
    
    # Bottom Section: Expiring Auctions List
    'expiring_auctions': [
        {
            'item_id': string,
            'title': string,
            'auction_end': ISO_8601_timestamp,
            'current_bid_usdc': float,
            'current_bidder': string,
            'top_bidder_nano_address': string,
            'auction_rsa_fingerprint': string,
        },
        # ... more expiring auctions
    ]
}
```

### Expiring Auctions Filter

**File**: [./services/arweave_post_service.py](./services/arweave_post_service.py:309)  
**Method**: `ArweavePostService.get_expiring_auctions(hours_until_expiry=24)`

**Variables**:
- **`hours_until_expiry`** (int): Hours in future to check for expiring auctions
  - Default: 24 hours
  - Used to filter items from local cache

**Filtering Logic**:
```python
expiring = []
now = datetime.now(timezone.utc)
cutoff = now + timedelta(hours=hours_until_expiry)

for item in self.local_auctions.values():
    if item.status == 'active':
        end_time = datetime.fromisoformat(item.auction_end)
        if now < end_time <= cutoff:
            expiring.append(item)  # Include in post
```

### Post to Arweave

**File**: [./services/arweave_post_service.py](./services/arweave_post_service.py:177)  
**Method**: `ArweavePostService.post_auction_to_arweave(post_data, user)`

**Pre-requisites**:
- **`balance_ar`** (float): User's AR balance in Arweave
  - Minimum required: 0.05 AR
  - Checked before posting

### Arweave Tags for Post

```python
tags = [
    ("Content-Type", "application/json"),
    ("App-Name", "Sapphire-Exchange"),
    ("Data-Type", "auction-post"),
    ("Posted-By", user.id),
    ("Sequence", str(post_data['sequence'])),
    ("RSA-Fingerprint", item.auction_rsa_fingerprint),
    ("Item-ID", item.id),
    ("Auction-Status", item.status),
]
```

### Post Storage

**Variables**:
- **`tx_id`** (string): Arweave transaction ID
  - Uniquely identifies this post on Arweave
  - Cached locally: `self.cached_posts[tx_id] = post_data`

### Search for Posts

**File**: [./services/arweave_post_service.py](./services/arweave_post_service.py:228)  
**Method**: `ArweavePostService.search_auction_posts(sequence_start, sequence_end, date_start, date_end)`

**Search Variables**:
- **`sequence_start`** (int): Minimum sequence number to include
- **`sequence_end`** (int): Maximum sequence number to include
- **`date_start`** (string, ISO 8601): Optional start date filter
  - Example: `"2024-01-01T00:00:00Z"`
- **`date_end`** (string, ISO 8601): Optional end date filter
  - Example: `"2024-12-31T23:59:59Z"`

**Returned**: List of matching post_data dictionaries

### Aggregate Auction Data

**File**: [./services/arweave_post_service.py](./services/arweave_post_service.py:268)  
**Method**: `ArweavePostService.aggregate_auction_data(posts)`

**Purpose**: Fetch current bid info from Nano wallets for posts

**For each post, fetches**:
- **`nano_wallet_balance`** (string, raw): Current balance in auction wallet
- **`nano_block_count`** (string): Number of blocks processed

**Returned**: List of AuctionPostData objects with enriched Nano wallet info

### Post Creation Output

**Success Response**:
```python
return post_data = {
    'version': '1.0',
    'sequence': int,
    'created_at': string,
    'auction': {...},
    'expiring_auctions': [...]
}
```

**After Arweave posting**:
```python
tx_id = await arweave_post_service.post_auction_to_arweave(post_data, user)
# tx_id is the Arweave transaction ID (string) or None on failure
```

---

## Summary Table

| Process | Entry Point | Key Variables | Output |
|---------|-------------|---------------|--------|
| **Login** | `LoginScreen.handle_login()` | seed_phrase, username, password, user object, session_token | User object + session token |
| **Create Item** | `ApplicationService.create_auction()` | item_data (title, description, price, auction_end), seller user | Item object with auction wallet + Arweave tx_id |
| **Arweave Post** | `ArweavePostService.create_auction_post()` | item, user, expiring_auctions, sequence | post_data dictionary + Arweave tx_id |

---

## Error Handling

All three processes use try-catch blocks and return detailed error messages:

```python
# Login
success, message, user = await app_service.login_user_with_seed(seed_phrase)
if not success:
    # Handle: message contains error description

# Create Item
success, message, item = await app_service.create_auction(item_data)
if not success:
    # Handle: message contains error description

# Arweave Post
post_data = await arweave_post_service.create_auction_post(item, user)
if post_data is None:
    # Handle: post creation failed
```
