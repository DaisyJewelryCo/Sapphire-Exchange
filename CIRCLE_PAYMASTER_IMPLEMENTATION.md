# Circle Paymaster Gas Station Implementation Plan for Solana

**Objective**: Integrate Circle's Paymaster service to enable users to pay Solana transaction fees in USDC instead of SOL, while maintaining full non-custodial control over their wallets.

**Status**: Planning Phase  
**Target Completion**: 5 weeks  
**Owner**: Auto-Coding Bot / Development Team

---

## 1. Architecture Overview

### 1.1 High-Level Flow

```
User Action (PyQt5 GUI)
    ↓
[Application Service] requests sponsorship
    ↓
[Circle Paymaster Service] (NEW) calls Circle API
    ↓
[Transaction Builder] constructs atomic transaction
    ↓
Backend returns unsigned transaction + paymaster metadata
    ↓
Client signs locally (Phantom wallet / web3.js)
    ↓
Client submits to Solana RPC
    ↓
Circle charges developer account for USDC fee conversion
    ↓
Transaction confirmed on-chain
```

### 1.2 Key Components to Add/Modify

**New Files**:
- `services/circle_paymaster_service.py` - Circle API integration
- `blockchain/circle_transaction_builder.py` - Atomic transaction construction
- `config/circle_config.py` - Circle-specific configuration
- `ui/dialogs/paymaster_settings_dialog.py` - UI for paymaster configuration
- `tests/test_circle_paymaster.py` - Unit and integration tests

**Modified Files**:
- `services/application_service.py` - Add paymaster sponsorship call
- `blockchain/solana_usdc_client.py` - Integrate with Circle paymaster
- `config/app_config.py` - Add paymaster feature flags
- `config/blockchain_config.py` - Add Circle API endpoints
- `services/transaction_tracker.py` - Track paymaster transactions
- `ui/dialogs/wallet_dialog.py` - Show paymaster status

---

## 2. Prerequisites & Configuration

### 2.1 Circle Web3 Account Setup

- [ ] Create Circle Web3 account at https://app.circle.com
- [ ] Enable **Paymaster** and **Gas Station** features
- [ ] Generate API key (store in `.env` and secrets manager)
- [ ] Obtain sandbox URL for testing
- [ ] Configure billing method (card or Circle balance)
- [ ] Request Solana mainnet access (may be phased rollout)

### 2.2 Environment Variables to Add

```
# Circle Paymaster Configuration
CIRCLE_API_KEY=your_api_key_here
CIRCLE_API_BASE=https://api.sandbox.circle.com  # For testing
CIRCLE_API_VERSION=v1
ENABLE_PAYMASTER=true
PAYMASTER_FEATURE_FLAG=beta

# Solana Configuration (existing, verify)
SOLANA_RPC_URL=https://api.devnet.solana.com
SOLANA_USDC_MINT=EPjFWdd5Au...  # devnet or mainnet USDC
SOLANA_PROGRAM_ID=...

# Developer Fee Payer (for fallback)
DEVELOPER_FEE_PAYER_SECRET=...  # base58-encoded private key
DEVELOPER_FEE_PAYER_PUBKEY=...  # public key

# Monitoring & Limits
PAYMASTER_SPEND_LIMIT_USD=1000.00  # Daily cap
PAYMASTER_TIMEOUT_SECONDS=30
PAYMASTER_RETRY_MAX=3
PAYMASTER_RETRY_BACKOFF_MS=1000
```

### 2.3 Dependencies to Add

```bash
# Add to requirements.txt
circle-sdk>=1.0.0  # Official Circle SDK (if available)
# OR use httpx which is already in requirements.txt for API calls
aiofiles>=23.0.0   # For async file I/O
tenacity>=8.2.0    # For retry logic
```

---

## 3. Phase-by-Phase Implementation

### Phase 1: Core Service Infrastructure (Week 1)

#### Step 1.1: Create `config/circle_config.py`
```python
# Configuration class for Circle API, endpoints, retry policy
# - PAYMASTER_ENDPOINTS: dict of API endpoints
# - RETRY_CONFIG: tenacity config for backoff
# - FEE_ESTIMATION_BUFFER: percentage buffer for fee estimation
# - SUPPORTED_TOKENS: list of supported fee tokens (USDC, SOL)
```

**Deliverable**: Configuration module with all Circle endpoints and parameters.

---

#### Step 1.2: Create `services/circle_paymaster_service.py`
**Core responsibilities**:
- Authenticate with Circle API using API key from environment
- Request paymaster session for a transaction
- Handle sponsorship responses and error codes
- Implement retry logic with exponential backoff
- Log all API calls for monitoring and debugging

**Methods to implement**:
```python
class CirclePaymasterService:
    async def initialize() -> bool
        # Validate Circle API credentials and connectivity
        # Return True if healthy, False if credentials invalid
    
    async def request_sponsorship(
        user_pubkey: str,
        transaction_message: bytes,
        fee_token: str = "USDC"
    ) -> PaymasterResponse | None
        # Call Circle /paymaster/request endpoint
        # Return paymaster metadata or None on failure
    
    async def get_paymaster_status() -> PaymasterStatus
        # Check Circle API health and current spend
    
    async def estimate_fee(transaction_size: int) -> EstimatedFee
        # Estimate USDC cost for a transaction
    
    async def _call_circle_api(
        endpoint: str,
        method: str = "POST",
        payload: dict = None
    ) -> dict
        # Low-level API call with retry logic
```

**Deliverable**: Fully async service with Circle API integration and error handling.

---

#### Step 1.3: Create `blockchain/circle_transaction_builder.py`
**Purpose**: Build atomic transactions that work with Circle paymaster.

**Methods**:
```python
class CircleTransactionBuilder:
    async def build_sponsored_transfer(
        sender_pubkey: str,
        recipient_pubkey: str,
        usdc_amount: int,
        paymaster_metadata: dict
    ) -> Transaction
        # Build transaction with paymaster metadata attached
    
    async def build_sponsored_program_call(
        user_pubkey: str,
        program_id: str,
        instruction_data: bytes,
        accounts: List[AccountMeta],
        paymaster_metadata: dict
    ) -> Transaction
        # Build generic program instruction with paymaster
    
    async def attach_paymaster_metadata(
        transaction: Transaction,
        paymaster_metadata: dict
    ) -> Transaction
        # Attach Circle paymaster fields to transaction
```

**Deliverable**: Transaction builder that integrates paymaster metadata.

---

### Phase 2: Integration with Existing Services (Week 2)

#### Step 2.1: Modify `services/application_service.py`
**Add methods**:
```python
async def sponsor_transaction(
    user_id: str,
    transaction_intent: TransactionIntent,
    use_paymaster: bool = True
) -> SponsoredTransactionResponse | None
    # High-level sponsorship orchestration
    # 1. Check if paymaster enabled (feature flag)
    # 2. Estimate fees
    # 3. Call CirclePaymasterService
    # 4. Build sponsored transaction
    # 5. Return unsigned tx + paymaster metadata or error

async def check_paymaster_availability(
    user_id: str
) -> bool
    # Check if user/transaction eligible for sponsorship
    # Validate against spend limits, user status
```

**Deliverable**: Application service extensions for paymaster workflow.

---

#### Step 2.2: Modify `blockchain/solana_usdc_client.py`
**Enhancements**:
- Add paymaster metadata field to transaction serialization
- Ensure USDC token account interactions work with sponsored transactions
- Add method to validate paymaster metadata before submission

```python
async def serialize_for_paymaster(
    transaction: Transaction,
    paymaster_metadata: dict
) -> bytes
    # Serialize transaction with paymaster fields
```

**Deliverable**: Enhanced USDC client with paymaster support.

---

#### Step 2.3: Modify `config/app_config.py`
**Add**:
- Feature flag: `PAYMASTER_ENABLED` (default: False, enable in beta)
- Fallback mode: if paymaster fails, allow regular fee payment
- User preferences: opt-in/opt-out for paymaster

**Deliverable**: Configuration updates for paymaster feature control.

---

#### Step 2.4: Modify `services/transaction_tracker.py`
**Add tracking for paymaster transactions**:
```python
async def track_sponsored_transaction(
    transaction_id: str,
    sponsorship_metadata: dict,
    user_id: str
) -> None
    # Track sponsorship request, approval, and settlement
    # Log timestamp, fees charged, settlement status
```

**Deliverable**: Transaction tracking for paymaster sponsorships.

---

### Phase 3: API Endpoints & Backend Flow (Week 2)

#### Step 3.1: Create/Modify FastAPI Endpoints (in `services/application_service.py` or new `api/paymaster_routes.py`)

```python
@app.post("/api/paymaster/estimate-fee")
async def estimate_paymaster_fee(
    transaction_intent: TransactionIntent,
    current_user: User = Depends(get_current_user)
) -> EstimatedFeeResponse
    # Return estimated USDC cost for transaction
    # Includes fee breakdown and paymaster status

@app.post("/api/paymaster/request-sponsorship")
async def request_sponsorship(
    transaction_intent: TransactionIntent,
    current_user: User = Depends(get_current_user)
) -> SponsoredTransactionResponse
    # Build and sponsor transaction
    # Return unsigned tx + paymaster metadata
    # OR return fallback instructions if paymaster unavailable

@app.post("/api/paymaster/submit-signed")
async def submit_sponsored_transaction(
    signed_transaction: SubmitTransactionRequest,
    current_user: User = Depends(get_current_user)
) -> TransactionSubmissionResponse
    # Optional: backend submission of signed tx
    # Monitor confirmation and settle fees

@app.get("/api/paymaster/status")
async def get_paymaster_status() -> PaymasterStatusResponse
    # Return Circle API health, current spend, daily limit
    # Used for dashboard monitoring
```

**Deliverable**: RESTful API endpoints for paymaster flow.

---

### Phase 4: UI Components (Week 3)

#### Step 4.1: Create `ui/dialogs/paymaster_settings_dialog.py`
**Features**:
- Toggle paymaster on/off
- View current daily spend limit
- Display estimated fee in USDC before transaction
- Fallback mode confirmation

**Deliverable**: Settings dialog for paymaster configuration.

---

#### Step 4.2: Modify Relevant PyQt5 Dialogs
**In `ui/dialogs/wallet_dialog.py` or transaction dialogs**:
- Show paymaster status badge (enabled/disabled)
- Display estimated USDC fee
- Show warning if fallback mode active
- Add "Sponsor Transaction" button if paymaster available

**Deliverable**: UI updates for user-facing paymaster features.

---

#### Step 4.3: Create `ui/paymaster_status_widget.py`
**Real-time monitoring widget**:
- Current daily spend / limit
- Paymaster API health status
- Number of sponsored transactions today
- Cost per transaction average

**Deliverable**: Dashboard widget for paymaster metrics.

---

### Phase 5: Error Handling & Fallbacks (Week 4)

#### Step 5.1: Implement Fallback Strategy
```python
# In circle_paymaster_service.py
async def handle_sponsorship_failure(
    reason: PaymasterFailureReason,
    user_id: str,
    transaction_intent: TransactionIntent
) -> FallbackResponse
    # Detect failure type:
    # - Quota exhausted → prompt user to pay SOL
    # - Billing issue → show error, retry later
    # - API unavailable → fallback to developer fee payer (if configured)
    # - Unsupported instruction → return error to client
    #
    # For each, return appropriate instructions for user
```

**Deliverable**: Robust error handling with user-friendly fallbacks.

---

#### Step 5.2: Implement Spend Limits & Rate Limiting
```python
# In circle_paymaster_service.py
class PaymasterBudgetManager:
    async def check_daily_limit(
        spend_today_usd: float,
        new_transaction_fee: float
    ) -> bool
        # Return True if spend OK, False if would exceed limit
    
    async def check_user_limit(
        user_id: str,
        transaction_fee: float,
        limit_per_user_usd: float = 50.0
    ) -> bool
        # Prevent single user from consuming too much budget
    
    async def enforce_rate_limit(
        user_id: str
    ) -> bool
        # Max N sponsorships per hour per user
```

**Deliverable**: Budget and rate limit enforcement.

---

### Phase 6: Monitoring & Logging (Week 4)

#### Step 6.1: Add Structured Logging
```python
# In circle_paymaster_service.py
import structlog

logger = structlog.get_logger()

# Log events:
logger.info(
    "paymaster_sponsorship_requested",
    user_id=user_id,
    fee_usd=estimated_fee,
    transaction_type="transfer"
)
logger.error(
    "paymaster_api_failed",
    error_code=error_code,
    retry_count=retries,
    user_id=user_id
)
```

**Deliverable**: Comprehensive logging for paymaster operations.

---

#### Step 6.2: Add Monitoring Metrics
```python
# In circle_paymaster_service.py or monitoring module
class PaymasterMetrics:
    sponsorship_requests_total: Counter
    sponsorship_success_total: Counter
    sponsorship_failure_total: Counter
    fee_paid_usd_total: Gauge
    api_latency_seconds: Histogram
    
    # Expose metrics for Prometheus/monitoring dashboard
```

**Deliverable**: Metrics collection for observability.

---

### Phase 7: Testing & Validation (Week 4-5)

#### Step 7.1: Create `tests/test_circle_paymaster.py`
```python
# Unit tests
def test_circle_api_authentication()
def test_circle_api_request_timeout()
def test_paymaster_fee_estimation()
def test_transaction_serialization_with_metadata()
def test_fallback_on_quota_exceeded()
def test_spend_limit_enforcement()
def test_rate_limit_enforcement()

# Integration tests (devnet)
@pytest.mark.asyncio
async def test_end_to_end_sponsored_transfer():
    # 1. Estimate fee
    # 2. Request sponsorship from Circle
    # 3. Build transaction with paymaster metadata
    # 4. Sign transaction (simulate client signing)
    # 5. Submit to devnet
    # 6. Confirm on-chain
    # 7. Verify fee was charged

@pytest.mark.asyncio
async def test_fallback_flow_when_paymaster_unavailable():
    # Test graceful degradation to regular fee payment
```

**Deliverable**: Comprehensive test suite with devnet integration.

---

#### Step 7.2: Add Mock Circle API Server (for testing)
```python
# tests/mock_circle_api.py
class MockCircleAPI:
    async def handle_sponsorship_request(request) -> dict:
        # Return mock paymaster metadata or error
    
    async def handle_fee_estimate(request) -> dict:
        # Return mock fee estimate
    
    async def handle_status(request) -> dict:
        # Return mock API status
```

**Deliverable**: Mock server for isolated testing.

---

### Phase 8: Documentation & Rollout (Week 5)

#### Step 8.1: Create Integration Documentation
**File**: `CIRCLE_PAYMASTER_INTEGRATION.md`

Contents:
- Configuration guide
- API endpoint reference
- Error codes and handling
- Testing instructions
- Monitoring dashboard setup
- Troubleshooting guide

**Deliverable**: Complete developer documentation.

---

#### Step 8.2: Add Feature Flag & Staged Rollout
```python
# In config/app_config.py
PAYMASTER_FEATURE_FLAGS = {
    "enabled": env("ENABLE_PAYMASTER", default=False),
    "rollout_percentage": env("PAYMASTER_ROLLOUT_PCT", default=0),  # 0-100
    "daily_spend_limit_usd": env("PAYMASTER_SPEND_LIMIT", default=1000),
    "max_per_user_usd": env("PAYMASTER_MAX_PER_USER", default=50),
    "max_per_user_per_hour": env("PAYMASTER_MAX_PER_HOUR", default=10),
    "enable_fallback": env("PAYMASTER_ENABLE_FALLBACK", default=True),
}

# Usage in application:
if should_enable_paymaster(current_user, PAYMASTER_FEATURE_FLAGS):
    # Use paymaster flow
else:
    # Fall back to regular fee payment
```

**Deliverable**: Feature flag infrastructure for safe rollout.

---

## 4. Data Models & API Schemas

### 4.1 Pydantic Models (in `models/models.py` or new `models/paymaster_models.py`)

```python
from pydantic import BaseModel
from typing import Optional, Dict, Any
from enum import Enum

class PaymasterTokenType(str, Enum):
    USDC = "USDC"
    SOL = "SOL"

class TransactionIntent(BaseModel):
    user_pubkey: str
    recipient_pubkey: Optional[str] = None
    program_id: Optional[str] = None
    instruction_data: Optional[str] = None
    amount: Optional[int] = None
    token_mint: Optional[str] = None
    transaction_type: str  # "transfer", "program_call", etc.

class EstimatedFee(BaseModel):
    usdc_amount: float
    sol_amount: Optional[float] = None
    gas_limit: int
    timestamp: str

class PaymasterMetadata(BaseModel):
    paymaster_address: str
    paymaster_signature: str
    nonce: str
    valid_until: int
    sponsored_fee_token: PaymasterTokenType
    fee_amount: float

class SponsoredTransactionResponse(BaseModel):
    transaction_message: str  # base64-encoded unsigned transaction
    paymaster_metadata: PaymasterMetadata
    estimated_fee_usdc: float
    estimated_fee_sol: Optional[float] = None
    expires_at: str

class PaymasterResponse(BaseModel):
    success: bool
    sponsorship_id: Optional[str] = None
    paymaster_metadata: Optional[PaymasterMetadata] = None
    error: Optional[str] = None
    error_code: Optional[str] = None

class PaymasterStatus(BaseModel):
    api_healthy: bool
    current_spend_usd: float
    daily_limit_usd: float
    remaining_budget: float
    transactions_today: int
    last_check: str
```

**Deliverable**: Type-safe data models for paymaster operations.

---

## 5. Implementation Checklist

### Pre-Implementation
- [ ] Set up Circle Web3 account and API key
- [ ] Configure `.env` with all Circle settings
- [ ] Add dependencies to `requirements.txt`
- [ ] Review Circle API documentation
- [ ] Create feature branch: `feature/circle-paymaster-solana`

### Phase 1: Infrastructure
- [ ] Create `config/circle_config.py`
- [ ] Create `services/circle_paymaster_service.py`
- [ ] Create `blockchain/circle_transaction_builder.py`
- [ ] Create `models/paymaster_models.py` (Pydantic schemas)

### Phase 2: Integration
- [ ] Modify `services/application_service.py`
- [ ] Modify `blockchain/solana_usdc_client.py`
- [ ] Modify `config/app_config.py`
- [ ] Modify `services/transaction_tracker.py`

### Phase 3: API
- [ ] Create REST API endpoints for sponsorship
- [ ] Add request/response validation
- [ ] Add authentication/authorization checks
- [ ] Add CORS configuration

### Phase 4: UI
- [ ] Create `ui/dialogs/paymaster_settings_dialog.py`
- [ ] Update wallet dialogs to show paymaster status
- [ ] Create status widget for dashboard
- [ ] Add paymaster indicators to transaction dialogs

### Phase 5: Error Handling
- [ ] Implement fallback strategy
- [ ] Implement budget and rate limiting
- [ ] Add error messages for all failure modes
- [ ] Test edge cases

### Phase 6: Monitoring
- [ ] Add structured logging
- [ ] Add metrics collection
- [ ] Create monitoring dashboard queries
- [ ] Add alerts for budget threshold

### Phase 7: Testing
- [ ] Create unit tests for all services
- [ ] Create integration tests on devnet
- [ ] Create mock Circle API server
- [ ] Add end-to-end tests
- [ ] Test fallback flows
- [ ] Stress test with high transaction volume

### Phase 8: Documentation & Rollout
- [ ] Create integration documentation
- [ ] Add feature flag infrastructure
- [ ] Set rollout percentage to 0% initially
- [ ] Stage rollout: 5% → 10% → 25% → 100%
- [ ] Monitor metrics at each stage
- [ ] Create rollback plan

---

## 6. Error Codes & Handling

| Code | Meaning | User Action | Fallback |
|------|---------|-------------|----------|
| `PAYMASTER_QUOTA_EXCEEDED` | Developer's daily budget exhausted | Retry tomorrow or use SOL | Pay SOL fee |
| `PAYMASTER_INVALID_TOKEN` | Unsupported token for fee payment | Contact support | Pay SOL fee |
| `PAYMASTER_API_TIMEOUT` | Circle API slow to respond | Retry in a moment | Pay SOL fee |
| `PAYMASTER_INSTRUCTION_UNSUPPORTED` | Transaction instruction not compatible with paymaster | Use regular transaction | Pay SOL fee |
| `PAYMASTER_USER_LIMIT_EXCEEDED` | User sponsorship limit exceeded | Contact support | Pay SOL fee |
| `PAYMASTER_INVALID_ACCOUNT` | Invalid account metadata | Check wallet address | Pay SOL fee |

---

## 7. Security Considerations

### 7.1 API Key Management
- [ ] Store Circle API key in environment variables only (never in code)
- [ ] Use secrets manager (e.g., HashiCorp Vault, AWS Secrets Manager)
- [ ] Rotate API keys every 90 days
- [ ] Restrict API key to Solana endpoints only
- [ ] Monitor API key usage for anomalies

### 7.2 Transaction Signing
- [ ] User private keys never sent to backend
- [ ] Unsigned transactions sent to client for signing
- [ ] Paymaster metadata validated before submission
- [ ] Use `solana.transaction.TransactionSignature` for verification

### 7.3 Spend Control
- [ ] Enforce daily spend limits
- [ ] Enforce per-user limits
- [ ] Require approval for transactions over threshold
- [ ] Log all sponsorship decisions

### 7.4 User Trust
- [ ] Clearly communicate when fees are sponsored by developer
- [ ] Show estimated fee before user confirms
- [ ] Transparent billing: show final fee charged
- [ ] Allow user to opt-out of paymaster and pay SOL instead

---

## 8. Monitoring & Metrics

### 8.1 Key Metrics to Track
- **Sponsorship Success Rate**: % of sponsorship requests approved
- **Average Fee Cost**: Average USD cost per sponsored transaction
- **Daily Spend**: Total USD spent on sponsorships per day
- **API Latency**: Time to get response from Circle API
- **Error Rate**: % of failed sponsorship requests
- **User Adoption**: % of users enabling paymaster
- **Fallback Rate**: % of transactions falling back to SOL payment

### 8.2 Alerts
- [ ] Daily spend exceeds 80% of limit
- [ ] Daily spend exceeds 100% of limit (should not happen)
- [ ] Sponsorship success rate drops below 95%
- [ ] API latency exceeds 5 seconds
- [ ] More than 3 failed API calls in a row

---

## 9. Rollout Timeline

```
Week 0: Setup
├─ Circle account & API access
├─ Environment configuration
└─ Feature branch creation

Week 1: Infrastructure (Phase 1-2)
├─ Core services implemented
├─ Config & models created
└─ Integration with existing services

Week 2: API & UI (Phase 3-4)
├─ REST API endpoints
├─ PyQt5 UI components
└─ Error handling basics

Week 3-4: Testing & Polish (Phase 5-7)
├─ Unit & integration tests
├─ Devnet end-to-end validation
├─ Monitoring & logging
└─ Documentation

Week 5: Rollout (Phase 8)
├─ Beta release (5% rollout)
├─ Monitor metrics closely
├─ Staged increase to 100%
└─ Production GA with feature flag

Post-Launch: Maintenance
├─ Monitor spend & metrics weekly
├─ Respond to user feedback
├─ Plan next phase (e.g., other chains)
└─ Cost optimization
```

---

## 10. Success Criteria

- [ ] Users can opt-in to paymaster sponsorship via settings
- [ ] Estimated fees displayed accurately (within 5% of final)
- [ ] 99% sponsorship success rate in production
- [ ] <2 second API latency for sponsorship requests (p95)
- [ ] <$0.10 average cost per sponsored transaction
- [ ] All error modes have graceful fallbacks
- [ ] Comprehensive logging for all operations
- [ ] Zero security incidents (API keys, key management)
- [ ] Full test coverage (>90%) for new code
- [ ] Documentation complete and maintainable

---

## 11. Future Enhancements

1. **Multi-Chain Paymaster**: Extend to other blockchains (Polygon, Arbitrum, etc.)
2. **User Fee Discounts**: Offer tiered sponsorship for high-value users
3. **Batch Transactions**: Sponsor multiple transactions in one API call
4. **Custom Tokens**: Accept other SPL tokens for fee payment
5. **Webhooks**: Real-time settlement notifications from Circle
6. **Advanced Analytics**: Dashboard showing ROI of sponsorship program
7. **Integration with Gasless Relayers**: Support alternative relayer networks

---

## Appendix A: File Structure Summary

```
Sapphire_Exchange/
├── config/
│   ├── circle_config.py                      (NEW)
│   ├── blockchain_config.py                  (MODIFIED)
│   └── app_config.py                         (MODIFIED)
├── services/
│   ├── circle_paymaster_service.py          (NEW)
│   ├── application_service.py               (MODIFIED)
│   ├── transaction_tracker.py               (MODIFIED)
│   └── user_service.py                      (MODIFIED for spend limits)
├── blockchain/
│   ├── circle_transaction_builder.py        (NEW)
│   └── solana_usdc_client.py                (MODIFIED)
├── models/
│   ├── paymaster_models.py                  (NEW)
│   └── models.py                            (MODIFIED)
├── ui/
│   ├── dialogs/
│   │   └── paymaster_settings_dialog.py     (NEW)
│   ├── paymaster_status_widget.py           (NEW)
│   └── wallet_widget.py                     (MODIFIED)
├── tests/
│   ├── test_circle_paymaster.py             (NEW)
│   └── mock_circle_api.py                   (NEW)
├── CIRCLE_PAYMASTER_IMPLEMENTATION.md       (THIS FILE)
├── CIRCLE_PAYMASTER_INTEGRATION.md          (NEW - Final docs)
└── requirements.txt                         (MODIFIED - add tenacity)
```

---

## Appendix B: Quick Reference Commands

```bash
# Set up environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run tests
pytest tests/test_circle_paymaster.py -v

# Run with Circle sandbox
export CIRCLE_API_BASE=https://api.sandbox.circle.com
export ENABLE_PAYMASTER=true
python app.py

# Monitor logs
tail -f debug_output.log | grep paymaster

# Deploy to production (after staged rollout)
export PAYMASTER_ROLLOUT_PCT=100
python app.py
```

---

**End of Implementation Plan**

For questions or clarifications, refer to Circle's official documentation:  
https://developers.circle.com/docs/paymaster-solana
