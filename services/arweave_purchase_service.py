"""
Arweave Purchase Service for Sapphire Exchange.
Handles purchasing Arweave coins using USDC on Solana via Jupiter DEX.
"""
import asyncio
import base58
import aiohttp
import json
from typing import Dict, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass

try:
    from solana.rpc.async_api import AsyncClient
    from solana.transaction import Transaction
    from solders.pubkey import Pubkey as SoldersPubkey
    SOLANA_AVAILABLE = True
except ImportError:
    AsyncClient = None
    Transaction = None
    SoldersPubkey = None
    SOLANA_AVAILABLE = False


@dataclass
class ArweaveSwapQuote:
    """Quote for Arweave swap on Jupiter."""
    input_amount: int  # in smallest units (USDC has 6 decimals)
    output_amount: int  # in smallest units (AR has 12 decimals)
    price_impact: float
    route_description: str
    swap_transaction: Optional[str] = None
    fees: Dict[str, Any] = None


class ArweavePurchaseService:
    """Service for purchasing Arweave using USDC on Solana via Jupiter DEX."""
    
    # Jupiter API endpoints
    JUPITER_QUOTE_API = "https://quote-api.jup.ag/v6/quote"
    JUPITER_SWAP_API = "https://quote-api.jup.ag/v6/swap"
    
    # Token mints on Solana mainnet
    USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    
    # Potential Arweave-related token mints on Solana
    # These may change; check for the most current wrapped AR or bridge token
    WRAPPED_AR_CANDIDATES = {
        "wAR_bridge": "HrFRX3amJZKUami6jPMD7T7qKHjWSXkkqwRWN3EcESj",  # Example - needs verification
    }
    
    # For testing/fallback, use a known token
    TEST_TOKEN_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC itself for testing
    
    def __init__(self, solana_client: Optional[AsyncClient] = None, rpc_url: Optional[str] = None):
        """Initialize Arweave purchase service."""
        self.solana_client = solana_client
        self.rpc_url = rpc_url or "https://api.mainnet-beta.solana.com"
        self.http_session: Optional[aiohttp.ClientSession] = None
        
        self.slippage_bps = 100
        self.min_slippage_bps = 10
        self.max_slippage_bps = 500
        
        self.max_retries = 3
        self.retry_delay = 1.5
        self.request_timeout = 12
        self.last_error: Optional[str] = None
        
        # Cache for token mints and routes
        self._token_cache = {}
    
    async def initialize(self) -> bool:
        """Initialize the service."""
        try:
            if not self.http_session:
                self.http_session = aiohttp.ClientSession()
            
            if not self.solana_client and SOLANA_AVAILABLE:
                try:
                    self.solana_client = AsyncClient(self.rpc_url)
                except Exception as e:
                    print(f"Warning: Could not initialize Solana client: {e}")
            
            return True
        except Exception as e:
            print(f"Error initializing Arweave purchase service: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown the service."""
        try:
            if self.http_session:
                await self.http_session.close()
            if self.solana_client:
                await self.solana_client.close()
        except Exception as e:
            print(f"Error shutting down purchase service: {e}")
    
    def _set_last_error(self, message: str):
        self.last_error = message
    
    def _resolve_slippage(self, slippage_bps: Optional[int]) -> int:
        value = self.slippage_bps if slippage_bps is None else int(slippage_bps)
        if value < self.min_slippage_bps:
            return self.min_slippage_bps
        if value > self.max_slippage_bps:
            return self.max_slippage_bps
        return value
    
    def set_slippage_bps(self, slippage_bps: int):
        self.slippage_bps = self._resolve_slippage(slippage_bps)
    
    async def _request_json(self, method: str, url: str, **kwargs) -> Optional[Dict[str, Any]]:
        if not self.http_session:
            await self.initialize()
        
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                timeout = kwargs.pop("timeout", aiohttp.ClientTimeout(total=self.request_timeout))
                async with self.http_session.request(method, url, timeout=timeout, **kwargs) as response:
                    if response.status == 200:
                        return await response.json()
                    error_text = await response.text()
                    last_error = f"HTTP {response.status}: {error_text[:120]}"
                    if response.status >= 500 and attempt < self.max_retries:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                        continue
                    break
            except asyncio.TimeoutError:
                last_error = "Request timed out"
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
            except Exception as e:
                last_error = str(e)
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                break
        
        if last_error:
            self._set_last_error(last_error)
        return None
    
    async def discover_arweave_token(self) -> Optional[str]:
        """Discover the current Arweave token mint on Solana."""
        try:
            # First, try to detect wrapped AR through Jupiter's token list
            if not self.http_session:
                await self.initialize()
            
            # Query Jupiter token list for Arweave
            url = "https://token.jup.ag/all"
            tokens = await self._request_json("GET", url)
            if tokens:
                # Search for Arweave-related tokens
                for token in tokens:
                    symbol = token.get('symbol', '').upper()
                    name = token.get('name', '').upper()
                    
                    # Look for wrapped AR, bridge AR, or similar
                    if any(x in symbol or x in name for x in ['AR', 'ARWEAVE', 'WAR']):
                        mint = token.get('address')
                        if mint:
                            print(f"Found Arweave token: {symbol} ({name}) - {mint}")
                            return mint
            
            self._set_last_error("No Arweave token found in Jupiter list")
            return None
        
        except Exception as e:
            print(f"Error discovering Arweave token: {e}")
            return None
    
    async def get_quote(self, usdc_amount: float, output_mint: Optional[str] = None,
                        slippage_bps: Optional[int] = None) -> Optional[ArweaveSwapQuote]:
        """Get a Jupiter quote for swapping USDC to Arweave token."""
        try:
            if not self.http_session:
                await self.initialize()
            
            resolved_slippage = self._resolve_slippage(slippage_bps)
            
            # If no output mint specified, try to discover it
            if not output_mint:
                output_mint = await self.discover_arweave_token()
            
            if not output_mint:
                self._set_last_error("Could not determine Arweave token mint")
                return None
            
            # Convert USDC amount to smallest units (6 decimals)
            input_amount = int(usdc_amount * 1e6)
            
            params = {
                "inputMint": self.USDC_MINT,
                "outputMint": output_mint,
                "amount": input_amount,
                "slippageBps": resolved_slippage,
                "onlyDirectRoutes": False,
                "asLegacyTransaction": False,
                "maxAccounts": 64,
            }
            
            data = await self._request_json("GET", self.JUPITER_QUOTE_API, params=params)
            if not data:
                return None
            
            route_plan = data.get("routePlanWithTokens")
            output_amount = int(data.get("outAmount", 0) or 0)
            if not route_plan or output_amount <= 0:
                self._set_last_error(f"Invalid Jupiter quote response: {data}")
                return None
            
            price_impact = float(data.get("priceImpactPct", 0) or 0)
            route_description = self._format_route(route_plan)
            
            return ArweaveSwapQuote(
                input_amount=input_amount,
                output_amount=output_amount,
                price_impact=price_impact,
                route_description=route_description,
                fees=data.get("fees")
            )
        
        except Exception as e:
            self._set_last_error(f"Error getting Jupiter quote: {e}")
            return None
    
    async def build_swap_transaction(self, user_pubkey: str, usdc_amount: float, 
                                    output_mint: Optional[str] = None,
                                    slippage_bps: Optional[int] = None) -> Optional[str]:
        """Build a swap transaction without signing."""
        try:
            if not self.http_session:
                await self.initialize()
            
            resolved_slippage = self._resolve_slippage(slippage_bps)
            
            # Get quote first
            quote = await self.get_quote(usdc_amount, output_mint, slippage_bps=resolved_slippage)
            if not quote:
                self._set_last_error("Failed to get swap quote")
                return None
            
            # Discover output mint if not provided
            if not output_mint:
                output_mint = await self.discover_arweave_token()
                if not output_mint:
                    self._set_last_error("Unable to discover output mint for swap")
                    return None
            
            # Request swap transaction from Jupiter
            out_amount_with_slippage = int(quote.output_amount * (1 - resolved_slippage / 10000))
            swap_request = {
                "route": {
                    "inAmount": quote.input_amount,
                    "outAmount": quote.output_amount,
                    "outAmountWithSlippage": out_amount_with_slippage,
                    "swapMode": "ExactIn",
                    "inputMint": self.USDC_MINT,
                    "outputMint": output_mint,
                },
                "userPublicKey": user_pubkey,
                "wrapAndUnwrapSol": True,
                "prioritizationFeeLamports": 1000,
            }
            
            data = await self._request_json("POST", self.JUPITER_SWAP_API, json=swap_request)
            if not data:
                return None
            
            swap_tx = data.get("swapTransaction")
            if not swap_tx:
                self._set_last_error(f"Invalid swap response: {data}")
                return None
            
            quote.swap_transaction = swap_tx
            return swap_tx
        
        except Exception as e:
            self._set_last_error(f"Error building swap transaction: {e}")
            return None
    
    async def execute_swap(self, user_pubkey: str, usdc_amount: float,
                          keypair_bytes: Optional[bytes] = None,
                          output_mint: Optional[str] = None,
                          slippage_bps: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Execute a complete swap of USDC to Arweave token."""
        try:
            if not keypair_bytes:
                self._set_last_error("Private key required to execute swap")
                return None
            
            # Build swap transaction
            swap_tx_base64 = await self.build_swap_transaction(user_pubkey, usdc_amount, output_mint, slippage_bps)
            if not swap_tx_base64:
                self._set_last_error("Failed to build swap transaction")
                return None
            
            # Decode and sign transaction
            try:
                from solders.keypair import Keypair
                import base64
                
                keypair = Keypair(keypair_bytes)
                tx_bytes = base64.b64decode(swap_tx_base64)
                
                # Reconstruct and sign transaction
                if Transaction:
                    tx = Transaction.from_bytes(tx_bytes)
                    tx.sign([keypair])
                    signed_tx = base64.b64encode(bytes(tx)).decode()
                else:
                    self._set_last_error("Transaction class not available")
                    return None
                
            except Exception as e:
                self._set_last_error(f"Error signing transaction: {e}")
                return None
            
            # Send transaction to network
            if not self.solana_client:
                self._set_last_error("Solana client not initialized")
                return None
            
            response = None
            last_error = None
            for attempt in range(self.max_retries + 1):
                try:
                    response = await self.solana_client.send_raw_transaction(bytes(signed_tx, 'utf-8'))
                    break
                except Exception as e:
                    last_error = str(e)
                    if attempt < self.max_retries:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                        continue
            
            if response is None:
                self._set_last_error(f"Error sending transaction: {last_error}")
                return None
            
            if hasattr(response, 'value'):
                tx_signature = response.value
            else:
                tx_signature = str(response)
            
            return {
                "success": True,
                "transaction_id": tx_signature,
                "amount_usdc": usdc_amount,
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            self._set_last_error(f"Error executing swap: {e}")
            return None
    
    async def estimate_arweave_output(self, usdc_amount: float) -> Optional[float]:
        """Estimate how much Arweave (in AR) we'll get for a given USDC amount."""
        try:
            quote = await self.get_quote(usdc_amount)
            if not quote:
                return None
            
            # Convert output amount from smallest units (12 decimals for AR)
            ar_amount = quote.output_amount / 1e12
            return ar_amount
        
        except Exception as e:
            print(f"Error estimating Arweave output: {e}")
            return None
    
    def _format_route(self, route_plan: list) -> str:
        """Format route plan for display."""
        try:
            if not route_plan:
                return "Direct swap"
            
            hops = []
            for route in route_plan:
                swap_info = route.get("swapInfo", {})
                label = swap_info.get("label", "Unknown")
                hops.append(label)
            
            return " → ".join(hops) if hops else "Unknown route"
        
        except Exception:
            return "Unknown route"


# Global service instance
arweave_purchase_service = None


async def get_arweave_purchase_service(config: Optional[Dict[str, Any]] = None) -> ArweavePurchaseService:
    """Get or create the global Arweave purchase service."""
    global arweave_purchase_service
    
    if not arweave_purchase_service:
        rpc_url = config.get("solana", {}).get("rpc_url") if config else None
        arweave_purchase_service = ArweavePurchaseService(rpc_url=rpc_url)
        await arweave_purchase_service.initialize()
    
    return arweave_purchase_service
