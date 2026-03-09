"""
SOL to USDC Swap Service for Sapphire Exchange.
Handles swapping SOL to USDC on Solana via Jupiter DEX.
"""
import asyncio
import base64
import binascii
import aiohttp
import os
from typing import Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

try:
    from solana.rpc.async_api import AsyncClient
    from solders.pubkey import Pubkey as SoldersPubkey
    SOLANA_AVAILABLE = True
except ImportError:
    AsyncClient = None
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
    
    LAMPORTS_PER_SOL = 1_000_000_000
    ASSOCIATED_TOKEN_ACCOUNT_RENT_LAMPORTS = 2_039_280
    TRANSACTION_FEE_BUFFER_LAMPORTS = 250_000
    DEFAULT_SWAP_RATIO = 0.9
    
    # Jupiter API endpoints
    JUPITER_QUOTE_APIS = [
        "https://quote-api.jup.ag/v6/quote",
        "https://lite-api.jup.ag/swap/v1/quote",
        "https://api.jup.ag/swap/v1/quote",
    ]
    JUPITER_SWAP_APIS = [
        "https://quote-api.jup.ag/v6/swap",
        "https://lite-api.jup.ag/swap/v1/swap",
        "https://api.jup.ag/swap/v1/swap",
    ]
    
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
        
        env_quote_api = os.getenv("JUPITER_QUOTE_API", "").strip()
        env_swap_api = os.getenv("JUPITER_SWAP_API", "").strip()
        self.jupiter_api_key = os.getenv("JUPITER_API_KEY", "").strip()
        self.jupiter_quote_apis = [env_quote_api] if env_quote_api else []
        self.jupiter_swap_apis = [env_swap_api] if env_swap_api else []
        for endpoint in self.JUPITER_QUOTE_APIS:
            if endpoint not in self.jupiter_quote_apis:
                self.jupiter_quote_apis.append(endpoint)
        for endpoint in self.JUPITER_SWAP_APIS:
            if endpoint not in self.jupiter_swap_apis:
                self.jupiter_swap_apis.append(endpoint)
    
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

    def _resolve_input_amount(self, sol_amount: float) -> Optional[int]:
        """Validate SOL input and convert to lamports."""
        try:
            amount = float(sol_amount)
        except (TypeError, ValueError):
            self._set_last_error("Invalid SOL amount")
            return None

        if amount <= 0:
            self._set_last_error("SOL amount must be greater than zero")
            return None

        lamports = int(amount * 1e9)
        if lamports <= 0:
            self._set_last_error("SOL amount too small")
            return None
        return lamports

    def _normalize_keypair_bytes(self, keypair_bytes: Any) -> Optional[bytes]:
        """Normalize private key data into bytes."""
        if not keypair_bytes:
            return None

        if isinstance(keypair_bytes, bytes):
            return keypair_bytes

        if isinstance(keypair_bytes, bytearray):
            return bytes(keypair_bytes)

        if isinstance(keypair_bytes, (list, tuple)):
            try:
                return bytes(int(v) & 0xFF for v in keypair_bytes)
            except Exception:
                return None

        if isinstance(keypair_bytes, str):
            candidate = keypair_bytes.strip()
            if not candidate:
                return None

            try:
                return base64.b64decode(candidate, validate=True)
            except (binascii.Error, ValueError):
                pass

            try:
                return bytes.fromhex(candidate)
            except ValueError:
                return None

        return None

    def _build_signing_keypair(self, keypair_bytes: bytes, expected_pubkey: Optional[str] = None):
        """Build a solders Keypair from either a 32-byte seed or 64-byte keypair."""
        from solders.keypair import Keypair

        if len(keypair_bytes) == 64:
            return Keypair.from_bytes(keypair_bytes)

        if len(keypair_bytes) == 32:
            wallet_pubkey = (expected_pubkey or "").strip()
            if wallet_pubkey:
                try:
                    pubkey_bytes = bytes(SoldersPubkey.from_string(wallet_pubkey))
                    return Keypair.from_bytes(keypair_bytes + pubkey_bytes)
                except Exception:
                    pass
            return Keypair.from_seed(keypair_bytes)

        raise ValueError(f"Unsupported Solana key length: {len(keypair_bytes)} bytes")

    def keypair_matches_pubkey(self, keypair_bytes: Any, expected_pubkey: str) -> bool:
        """Check whether key material belongs to the expected wallet address."""
        normalized_keypair = self._normalize_keypair_bytes(keypair_bytes)
        wallet_pubkey = (expected_pubkey or "").strip()
        if not normalized_keypair or not wallet_pubkey:
            return False

        try:
            keypair = self._build_signing_keypair(normalized_keypair, wallet_pubkey)
            return str(keypair.pubkey()) == wallet_pubkey
        except Exception:
            return False

    def _sign_swap_transaction(self, tx_bytes: bytes, keypair_bytes: bytes,
                               expected_pubkey: Optional[str] = None) -> Optional[bytes]:
        """Sign Jupiter swap transaction bytes."""
        try:
            from solders.transaction import VersionedTransaction

            keypair = self._build_signing_keypair(keypair_bytes, expected_pubkey)
            unsigned_tx = VersionedTransaction.from_bytes(tx_bytes)
            legacy_tx = unsigned_tx.into_legacy_transaction()

            if legacy_tx is not None:
                legacy_tx.sign([keypair], legacy_tx.message.recent_blockhash)
                return bytes(legacy_tx)

            signed_tx = VersionedTransaction(unsigned_tx.message, [keypair])
            return bytes(signed_tx)
        except Exception as sign_error:
            self._set_last_error(f"Error signing transaction: {sign_error}")
            return None
    
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
    
    def _build_jupiter_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": "SapphireExchange/1.0"
        }
        if self.jupiter_api_key:
            headers["x-api-key"] = self.jupiter_api_key
        return headers
    
    async def _request_jupiter_quote(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Request quote using multiple Jupiter endpoints."""
        errors = []
        headers = self._build_jupiter_headers()
        for endpoint in self.jupiter_quote_apis:
            response = await self._request_json("GET", endpoint, params=params, headers=headers)
            if response:
                return response
            if self.last_error:
                errors.append(f"{endpoint} -> {self.last_error}")
        if errors:
            self._set_last_error("; ".join(errors))
        return None
    
    async def _request_jupiter_swap(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Request swap transaction using multiple Jupiter endpoints."""
        errors = []
        headers = self._build_jupiter_headers()
        for endpoint in self.jupiter_swap_apis:
            response = await self._request_json("POST", endpoint, json=payload, headers=headers)
            if response:
                return response
            if self.last_error:
                errors.append(f"{endpoint} -> {self.last_error}")
        if errors:
            self._set_last_error("; ".join(errors))
        return None

    async def _request_rpc(self, method: str, params: Optional[list] = None) -> Optional[Dict[str, Any]]:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or []
        }
        response = await self._request_json("POST", self.rpc_url, json=payload)
        if not response:
            return None
        if "error" in response:
            error_msg = response["error"].get("message", "Unknown Solana RPC error")
            self._set_last_error(f"RPC Error: {error_msg}")
            return None
        return response.get("result")

    async def wallet_has_token_account(self, wallet_pubkey: str, mint: Optional[str] = None) -> Optional[bool]:
        target_mint = (mint or self.USDC_MINT).strip()
        wallet_address = (wallet_pubkey or "").strip()
        if not wallet_address or not target_mint:
            return None

        result = await self._request_rpc(
            "getTokenAccountsByOwner",
            [
                wallet_address,
                {"mint": target_mint},
                {"encoding": "jsonParsed"}
            ]
        )
        if result is None:
            return None

        accounts = result.get("value") or []
        return len(accounts) > 0

    async def calculate_swap_plan(self, wallet_pubkey: str, sol_balance: float,
                                  swap_ratio: Optional[float] = None) -> Optional[Dict[str, Any]]:
        self.last_error = None
        wallet_address = (wallet_pubkey or "").strip()
        if not wallet_address:
            self._set_last_error("User wallet public key is required")
            return None

        try:
            balance_lamports = int(float(sol_balance) * self.LAMPORTS_PER_SOL)
        except (TypeError, ValueError):
            self._set_last_error("Invalid SOL balance")
            return None

        if balance_lamports <= 0:
            self._set_last_error("No SOL available to swap")
            return None

        resolved_ratio = self.DEFAULT_SWAP_RATIO if swap_ratio is None else float(swap_ratio)
        if resolved_ratio <= 0:
            self._set_last_error("Swap ratio must be greater than zero")
            return None

        requested_lamports = min(int(balance_lamports * resolved_ratio), balance_lamports)
        reserve_lamports = self.TRANSACTION_FEE_BUFFER_LAMPORTS

        has_usdc_account = await self.wallet_has_token_account(wallet_address, self.USDC_MINT)
        if has_usdc_account is not True:
            reserve_lamports += self.ASSOCIATED_TOKEN_ACCOUNT_RENT_LAMPORTS

        max_swappable_lamports = max(balance_lamports - reserve_lamports, 0)
        swap_lamports = min(requested_lamports, max_swappable_lamports)
        if swap_lamports <= 0:
            reserve_sol = reserve_lamports / self.LAMPORTS_PER_SOL
            balance_sol = balance_lamports / self.LAMPORTS_PER_SOL
            self._set_last_error(
                f"Not enough SOL to cover swap network costs. Balance: {balance_sol:.6f} SOL, required reserve: {reserve_sol:.6f} SOL"
            )
            return None

        return {
            "balance_lamports": balance_lamports,
            "balance_sol": balance_lamports / self.LAMPORTS_PER_SOL,
            "requested_lamports": requested_lamports,
            "requested_sol": requested_lamports / self.LAMPORTS_PER_SOL,
            "swap_lamports": swap_lamports,
            "swap_amount_sol": swap_lamports / self.LAMPORTS_PER_SOL,
            "reserve_lamports": reserve_lamports,
            "reserve_sol": reserve_lamports / self.LAMPORTS_PER_SOL,
            "usdc_account_exists": has_usdc_account is True,
        }
    
    async def get_quote(self, sol_amount: float, slippage_bps: Optional[int] = None) -> Optional[SolUsdcSwapQuote]:
        """Get a Jupiter quote for swapping SOL to USDC."""
        try:
            self.last_error = None
            if not self.http_session:
                await self.initialize()
            
            resolved_slippage = self._resolve_slippage(slippage_bps)
            input_amount = self._resolve_input_amount(sol_amount)
            if not input_amount:
                return None
            
            params = {
                "inputMint": self.SOL_MINT,
                "outputMint": self.USDC_MINT,
                "amount": input_amount,
                "slippageBps": resolved_slippage,
                "onlyDirectRoutes": "false",
            }
            
            response = await self._request_jupiter_quote(params)
            if not response:
                if not self.last_error:
                    self._set_last_error("Failed to get quote from Jupiter")
                return None
            
            route_plan = (
                response.get("routePlanWithMetrics")
                or response.get("routePlanWithTokens")
                or response.get("routePlan")
                or []
            )
            output_amount = int(response.get("outAmount", 0) or 0)
            if output_amount <= 0 and route_plan:
                first_route = route_plan[0] if isinstance(route_plan, list) else {}
                output_amount = int(first_route.get("outAmount", 0) or 0)
            
            if output_amount <= 0:
                self._set_last_error("No routes available for this swap")
                return None
            
            price_impact = float(response.get("priceImpactPct", 0) or 0)
            
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
            self.last_error = None
            if not self.http_session:
                await self.initialize()

            wallet_pubkey = (user_pubkey or "").strip()
            if not wallet_pubkey:
                self._set_last_error("User wallet public key is required")
                return None
            
            resolved_slippage = self._resolve_slippage(slippage_bps)
            input_amount = self._resolve_input_amount(sol_amount)
            if not input_amount:
                return None
            
            params = {
                "inputMint": self.SOL_MINT,
                "outputMint": self.USDC_MINT,
                "amount": input_amount,
                "slippageBps": resolved_slippage,
                "userPublicKey": wallet_pubkey,
                "wrapAndUnwrapSol": "true",
            }
            
            response = await self._request_jupiter_quote(params)
            if not response:
                if not self.last_error:
                    self._set_last_error("Failed to get route for transaction")
                return None
            
            route_plan = (
                response.get("routePlanWithMetrics")
                or response.get("routePlanWithTokens")
                or response.get("routePlan")
                or []
            )
            quote_response = response.get("quoteResponse") or response
            
            swap_payload = {
                "quoteResponse": quote_response,
                "userPublicKey": wallet_pubkey,
                "wrapAndUnwrapSol": True,
            }
            if route_plan and isinstance(route_plan, list):
                swap_payload["route"] = route_plan[0]
            
            swap_response = await self._request_jupiter_swap(swap_payload)
            if not swap_response or "swapTransaction" not in swap_response:
                if not self.last_error:
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
            self.last_error = None
            normalized_keypair = self._normalize_keypair_bytes(keypair_bytes)
            if not normalized_keypair:
                self._set_last_error("Valid private key required to execute swap")
                return None

            swap_tx_base64 = await self.build_swap_transaction(user_pubkey, sol_amount, slippage_bps)
            if not swap_tx_base64:
                if not self.last_error:
                    self._set_last_error("Failed to build swap transaction")
                return None

            try:
                tx_bytes = base64.b64decode(swap_tx_base64)
            except (binascii.Error, ValueError) as decode_error:
                self._set_last_error(f"Invalid swap transaction payload: {decode_error}")
                return None

            signed_tx_bytes = self._sign_swap_transaction(tx_bytes, normalized_keypair, user_pubkey)
            if not signed_tx_bytes:
                return None

            if not self.solana_client:
                self._set_last_error("Solana client not initialized")
                return None

            response = None
            last_error = None
            for attempt in range(self.max_retries + 1):
                try:
                    response = await self.solana_client.send_raw_transaction(signed_tx_bytes)
                    break
                except Exception as e:
                    last_error = str(e)
                    if attempt < self.max_retries:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                        continue

            if response is None:
                self._set_last_error(f"Error sending transaction: {last_error}")
                return None

            tx_signature = response.value if hasattr(response, 'value') else str(response)
            return {
                "success": True,
                "transaction_id": str(tx_signature),
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
