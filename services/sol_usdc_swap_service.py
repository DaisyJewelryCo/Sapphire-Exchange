"""
SOL to USDC Swap Service for Sapphire Exchange.
Handles swapping SOL to USDC on Solana via Jupiter DEX.
"""
import asyncio
import base64
import aiohttp
import json
from typing import Dict, Optional, Any
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
class SolUsdcSwapQuote:
    """Quote for SOL to USDC swap on Jupiter."""
    input_amount: int  # in smallest units (SOL has 9 decimals - lamports)
    output_amount: int  # in smallest units (USDC has 6 decimals)
    price_impact: float
    route_description: str
    swap_transaction: Optional[str] = None
    fees: Dict[str, Any] = None


class SolUsdcSwapService:
    """Service for swapping SOL to USDC on Solana via Jupiter DEX."""
    
    # Jupiter API endpoints
    JUPITER_QUOTE_API = "https://quote-api.jup.ag/v6/quote"
    JUPITER_SWAP_API = "https://quote-api.jup.ag/v6/swap"
    
    # Token mints on Solana mainnet
    SOL_MINT = "So11111111111111111111111111111111111111112"  # Wrapped SOL
    USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    
    def __init__(self, solana_client: Optional[AsyncClient] = None, rpc_url: Optional[str] = None):
        """Initialize SOL/USDC swap service."""
        self.solana_client = solana_client
        self.rpc_url = rpc_url or "https://api.mainnet-beta.solana.com"
        self.http_session: Optional[aiohttp.ClientSession] = None
        
        self.slippage_bps = 50  # 0.5% default slippage
        self.min_slippage_bps = 10  # 0.1% minimum
        self.max_slippage_bps = 500  # 5% maximum
        
        self.max_retries = 3
        self.retry_delay = 1.5
        self.request_timeout = 12
        self.last_error: Optional[str] = None
    
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
            print(f"Error initializing SOL/USDC swap service: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown the service."""
        try:
            if self.http_session:
                await self.http_session.close()
            if self.solana_client:
                await self.solana_client.close()
        except Exception as e:
            print(f"Error shutting down swap service: {e}")
    
    def _set_last_error(self, message: str):
        """Set last error message."""
        self.last_error = message
    
    def _resolve_slippage(self, slippage_bps: Optional[int]) -> int:
        """Resolve and validate slippage value."""
        value = self.slippage_bps if slippage_bps is None else int(slippage_bps)
        if value < self.min_slippage_bps:
            return self.min_slippage_bps
        if value > self.max_slippage_bps:
            return self.max_slippage_bps
        return value
    
    def set_slippage_bps(self, slippage_bps: int):
        """Set slippage tolerance in basis points."""
        self.slippage_bps = self._resolve_slippage(slippage_bps)
    
    async def _request_json(self, method: str, url: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Make async HTTP request and return JSON."""
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
    
    async def get_quote(self, sol_amount: float, slippage_bps: Optional[int] = None) -> Optional[SolUsdcSwapQuote]:
        """Get a Jupiter quote for swapping SOL to USDC."""
        try:
            if not self.http_session:
                await self.initialize()
            
            resolved_slippage = self._resolve_slippage(slippage_bps)
            
            # Convert SOL amount to lamports (9 decimals)
            input_amount = int(sol_amount * 1e9)
            
            params = {
                "inputMint": self.SOL_MINT,
                "outputMint": self.USDC_MINT,
                "amount": input_amount,
                "slippageBps": resolved_slippage,
                "onlyDirectRoutes": False,
            }
            
            response = await self._request_json("GET", self.JUPITER_QUOTE_API, params=params)
            if not response:
                self._set_last_error("Failed to get quote from Jupiter")
                return None
            
            # Check if response contains routes
            if "routePlanWithMetrics" not in response or not response["routePlanWithMetrics"]:
                self._set_last_error("No routes available for this swap")
                return None
            
            route_data = response["routePlanWithMetrics"][0]
            output_amount = int(route_data.get("outAmount", 0))
            price_impact = float(route_data.get("percentFee", 0)) if "percentFee" in route_data else 0.0
            
            # Build route description
            route_description = f"Jupiter DEX: {sol_amount} SOL → {output_amount / 1e6:.2f} USDC"
            
            return SolUsdcSwapQuote(
                input_amount=input_amount,
                output_amount=output_amount,
                price_impact=price_impact,
                route_description=route_description,
                fees=response.get("fees", {})
            )
        
        except Exception as e:
            self._set_last_error(f"Error getting quote: {e}")
            return None
    
    async def build_swap_transaction(self, user_pubkey: str, sol_amount: float,
                                    slippage_bps: Optional[int] = None) -> Optional[str]:
        """Build a swap transaction for swapping SOL to USDC."""
        try:
            if not self.http_session:
                await self.initialize()
            
            resolved_slippage = self._resolve_slippage(slippage_bps)
            
            # Convert SOL amount to lamports
            input_amount = int(sol_amount * 1e9)
            
            params = {
                "inputMint": self.SOL_MINT,
                "outputMint": self.USDC_MINT,
                "amount": input_amount,
                "slippageBps": resolved_slippage,
                "userPublicKey": user_pubkey,
                "wrapAndUnwrapSol": True,
            }
            
            response = await self._request_json("GET", self.JUPITER_QUOTE_API, params=params)
            if not response or "routePlanWithMetrics" not in response:
                self._set_last_error("Failed to get route for transaction")
                return None
            
            # Request swap transaction from Jupiter
            swap_payload = {
                "route": response["routePlanWithMetrics"][0],
                "userPublicKey": user_pubkey,
                "wrapAndUnwrapSol": True,
            }
            
            swap_response = await self._request_json("POST", self.JUPITER_SWAP_API, json=swap_payload)
            if not swap_response or "swapTransaction" not in swap_response:
                self._set_last_error("Failed to build swap transaction")
                return None
            
            return swap_response["swapTransaction"]
        
        except Exception as e:
            self._set_last_error(f"Error building transaction: {e}")
            return None
    
    async def execute_swap(self, user_pubkey: str, sol_amount: float,
                          keypair_bytes: Optional[bytes] = None,
                          slippage_bps: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Execute a complete swap of SOL to USDC."""
        try:
            if not keypair_bytes:
                self._set_last_error("Private key required to execute swap")
                return None
            
            # Build swap transaction
            swap_tx_base64 = await self.build_swap_transaction(user_pubkey, sol_amount, slippage_bps)
            if not swap_tx_base64:
                self._set_last_error("Failed to build swap transaction")
                return None
            
            # Decode and sign transaction
            try:
                from solders.keypair import Keypair
                
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
                "amount_sol": sol_amount,
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            self._set_last_error(f"Error executing swap: {e}")
            return None
    
    async def estimate_usdc_output(self, sol_amount: float) -> Optional[float]:
        """Estimate how much USDC we'll get for a given SOL amount."""
        try:
            quote = await self.get_quote(sol_amount)
            if not quote:
                return None
            
            # Convert output amount (smallest unit with 6 decimals) to USDC
            return quote.output_amount / 1e6
        
        except Exception as e:
            self._set_last_error(f"Error estimating output: {e}")
            return None


async def get_sol_usdc_swap_service() -> SolUsdcSwapService:
    """Factory function to get or create SOL/USDC swap service singleton."""
    if not hasattr(get_sol_usdc_swap_service, '_instance'):
        get_sol_usdc_swap_service._instance = SolUsdcSwapService()
        await get_sol_usdc_swap_service._instance.initialize()
    return get_sol_usdc_swap_service._instance
