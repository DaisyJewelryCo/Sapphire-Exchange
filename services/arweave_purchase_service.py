"""
Arweave Purchase Service for Sapphire Exchange.
Handles purchasing Arweave coins using USDC on Solana via Jupiter DEX.
"""
import asyncio
import base64
import binascii
import aiohttp
import os
from typing import Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass

from services.funding_manager_service import get_funding_manager_service

try:
    from solana.rpc.async_api import AsyncClient
    from solana.transaction import Transaction
    SOLANA_AVAILABLE = True
except ImportError:
    AsyncClient = None
    Transaction = None
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
    USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    
    WRAPPED_AR_CANDIDATES = [
        "HrFRX3amJZKUami6jPMD7T7qKHjWSXkkqwRWN3EcESj",
    ]
    
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
        self.quote_request_timeout = 4
        self.quote_max_retries = 0
        self.swap_request_timeout = 10
        self.swap_max_retries = 1
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

        self._token_cache = {
            "arweave_mint": None,
            "direct_swap_available": None,
            "last_checked_mint": None,
        }
    
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

    def _get_configured_output_mint(self) -> str:
        funding_service = get_funding_manager_service()
        configured_mint = (funding_service.config.arweave_output_mint or "").strip()
        if configured_mint:
            return configured_mint
        return os.getenv("ARWEAVE_OUTPUT_MINT", "").strip()

    def _get_native_provider_details(self) -> Dict[str, str]:
        funding_service = get_funding_manager_service()
        config = funding_service.config
        provider = (config.arweave_native_provider or "turbo").strip().lower()

        providers = {
            "turbo": {
                "id": "turbo",
                "name": "Turbo",
                "service_url": (config.turbo_payment_service_url or "https://payment.ardrive.io/v1").strip(),
                "description": "Use a Turbo payment session to convert supported Solana funds into native AR.",
            },
            "arseeding": {
                "id": "arseeding",
                "name": "Arseeding",
                "service_url": (config.arseeding_service_url or "https://arseed.web3infra.dev").strip(),
                "payment_url": (config.arseeding_pay_url or "https://api.everpay.io").strip(),
                "description": "Use Arseeding/Everpay rails to convert supported Solana funds into native AR.",
            },
        }

        return providers.get(provider, providers["turbo"])

    def _build_native_provider_message(self) -> str:
        provider = self._get_native_provider_details()
        return (
            f"Direct Jupiter AR swaps are unavailable. Continue with SOL/USDC funding, then convert to native AR with "
            f"{provider['name']} via {provider['service_url']}."
        )

    def get_native_conversion_plan(self) -> Dict[str, Any]:
        provider = self._get_native_provider_details()
        return {
            "available": True,
            "provider": provider,
            "message": self._build_native_provider_message(),
        }

    def _get_provider_api_url(self, provider: Dict[str, str], path: str) -> str:
        base_url = provider.get("service_url", "").rstrip("/")
        normalized_path = path if path.startswith("/") else f"/{path}"
        return f"{base_url}{normalized_path}"

    def _coerce_float(self, value: Any) -> Optional[float]:
        try:
            if isinstance(value, bool) or value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    def _find_first_value(self, payload: Any, key_names: list[str]) -> Any:
        normalized_names = {name.lower() for name in key_names}
        stack = [payload]

        while stack:
            current = stack.pop()
            if isinstance(current, dict):
                for key, value in current.items():
                    if key.lower() in normalized_names:
                        return value
                    if isinstance(value, (dict, list)):
                        stack.append(value)
            elif isinstance(current, list):
                stack.extend(current)

        return None

    def _extract_currency_price(self, payload: Dict[str, Any], currency: str) -> Optional[float]:
        currency_key = (currency or "USDC").strip().lower()
        direct_candidates = [
            currency_key,
            f"price{currency_key}",
            f"price_{currency_key}",
            f"{currency_key}price",
            f"{currency_key}_price",
            f"pricein{currency_key}",
        ]

        direct_value = self._find_first_value(payload, direct_candidates)
        parsed_direct = self._coerce_float(direct_value)
        if parsed_direct and parsed_direct > 0:
            return parsed_direct

        for container_key in ["price", "prices", "rates", "quote", "quotes"]:
            nested = self._find_first_value(payload, [container_key])
            if isinstance(nested, dict):
                nested_value = nested.get(currency_key)
                parsed_nested = self._coerce_float(nested_value)
                if parsed_nested and parsed_nested > 0:
                    return parsed_nested

        return None

    def _extract_provider_transaction(self, payload: Dict[str, Any]) -> Optional[str]:
        candidate = self._find_first_value(
            payload,
            [
                "solanaTransaction",
                "transactionBase64",
                "serializedTransaction",
                "swapTransaction",
                "transaction",
                "tx",
            ],
        )
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
        return None

    def _extract_provider_reference(self, payload: Dict[str, Any], provider_id: str) -> Optional[str]:
        candidate = self._find_first_value(
            payload,
            [
                "trackingId",
                "purchaseId",
                "referenceId",
                "id",
            ],
        )
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
        if provider_id == "arseeding":
            status = self._find_first_value(payload, ["orderId"])
            if isinstance(status, str) and status.strip():
                return status.strip()
        return None

    def _decode_transaction_payload(self, tx_payload: str) -> Optional[bytes]:
        candidate = (tx_payload or "").strip()
        if not candidate:
            self._set_last_error("Provider returned an empty transaction payload")
            return None

        padding = (-len(candidate)) % 4
        if padding:
            candidate = f"{candidate}{'=' * padding}"

        try:
            return base64.b64decode(candidate)
        except (binascii.Error, ValueError) as decode_error:
            self._set_last_error(f"Invalid provider transaction payload: {decode_error}")
            return None

    async def _send_signed_transaction(self, signed_tx_bytes: bytes) -> Optional[str]:
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

        return str(response.value if hasattr(response, 'value') else response)

    async def get_native_provider_quote(self, payment_amount: float, payment_currency: str = "USDC") -> Optional[Dict[str, Any]]:
        try:
            self.last_error = None
            provider = self._get_native_provider_details()
            payment_currency = (payment_currency or "USDC").strip().upper()
            response = await self._request_json(
                "GET",
                self._get_provider_api_url(provider, "/price/AR"),
                timeout=aiohttp.ClientTimeout(total=self.quote_request_timeout),
                max_retries=self.quote_max_retries,
            )
            if not response:
                if not self.last_error:
                    self._set_last_error(f"{provider['name']} price quote unavailable")
                return None

            unit_price = self._extract_currency_price(response, payment_currency)
            if unit_price is None or unit_price <= 0:
                self._set_last_error(f"{provider['name']} did not return a usable {payment_currency} price for AR")
                return None

            ar_amount = float(payment_amount) / unit_price
            if ar_amount <= 0:
                self._set_last_error(f"{provider['name']} produced an invalid AR amount estimate")
                return None

            return {
                "provider": provider,
                "payment_currency": payment_currency,
                "payment_amount": float(payment_amount),
                "ar_amount": ar_amount,
                "amount_winston": str(max(int(ar_amount * 1e12), 1)),
                "unit_price": unit_price,
                "raw": response,
            }
        except Exception as e:
            self._set_last_error(f"Error getting native provider quote: {e}")
            return None

    async def _get_native_purchase_status(self, provider: Dict[str, str], reference_id: str) -> Optional[Dict[str, Any]]:
        try:
            provider_id = provider.get("id", "")
            if provider_id == "arseeding":
                status_path = f"/ar/transfer/{reference_id}"
            else:
                status_path = f"/purchase/{reference_id}"

            response = await self._request_json(
                "GET",
                self._get_provider_api_url(provider, status_path),
                timeout=aiohttp.ClientTimeout(total=self.swap_request_timeout),
                max_retries=self.swap_max_retries,
            )
            return response
        except Exception as e:
            self._set_last_error(f"Error checking provider purchase status: {e}")
            return None

    async def execute_native_purchase(self, user_pubkey: str, payment_amount: float,
                                      arweave_address: str, keypair_bytes: Optional[bytes] = None,
                                      payment_currency: str = "USDC") -> Optional[Dict[str, Any]]:
        try:
            self.last_error = None
            normalized_keypair = self._normalize_keypair_bytes(keypair_bytes)
            if not normalized_keypair:
                self._set_last_error("Valid private key required to execute native AR funding")
                return None

            wallet_pubkey = (user_pubkey or "").strip()
            if not wallet_pubkey:
                self._set_last_error("User wallet public key is required")
                return None

            target_arweave_address = (arweave_address or "").strip()
            if not target_arweave_address:
                self._set_last_error("Arweave wallet address is required for native AR funding")
                return None

            quote = await self.get_native_provider_quote(payment_amount, payment_currency=payment_currency)
            if not quote:
                return None

            provider = quote["provider"]
            provider_id = provider.get("id", "turbo")
            amount_winston = quote["amount_winston"]
            payment_currency = quote["payment_currency"]

            if provider_id == "arseeding":
                payload = {
                    "target": target_arweave_address,
                    "quantity": amount_winston,
                    "payment": {
                        "currency": payment_currency,
                        "payer": wallet_pubkey,
                    },
                }
                request_path = "/ar/transfer"
            else:
                payload = {
                    "target": target_arweave_address,
                    "amount": amount_winston,
                    "currency": payment_currency,
                    "payer": wallet_pubkey,
                }
                request_path = "/purchase"

            create_response = await self._request_json(
                "POST",
                self._get_provider_api_url(provider, request_path),
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.swap_request_timeout),
                max_retries=self.swap_max_retries,
            )
            if not create_response:
                if not self.last_error:
                    self._set_last_error(f"{provider['name']} purchase request failed")
                return None

            tx_payload = self._extract_provider_transaction(create_response)
            if not tx_payload:
                self._set_last_error(f"{provider['name']} did not return a signable Solana transaction")
                return None

            tx_bytes = self._decode_transaction_payload(tx_payload)
            if not tx_bytes:
                return None

            signed_tx_bytes = self._sign_swap_transaction(tx_bytes, normalized_keypair)
            if not signed_tx_bytes:
                return None

            tx_signature = await self._send_signed_transaction(signed_tx_bytes)
            if not tx_signature:
                return None

            reference_id = self._extract_provider_reference(create_response, provider_id)
            status_payload = None
            if reference_id:
                for _ in range(3):
                    await asyncio.sleep(2)
                    status_payload = await self._get_native_purchase_status(provider, reference_id)
                    status_value = (self._find_first_value(status_payload, ["status", "state"]) or "").lower() if status_payload else ""
                    if status_value in {"success", "completed", "confirmed"}:
                        break
                    if status_value in {"failed", "error", "expired"}:
                        self._set_last_error(f"{provider['name']} payout failed with status: {status_value}")
                        return None

            arweave_tx_id = None
            if status_payload:
                arweave_tx_id = self._find_first_value(status_payload, ["arweaveTxId", "arTxId", "arweaveId", "arId"])

            return {
                "success": True,
                "transaction_id": tx_signature,
                "amount_usdc": payment_amount,
                "provider": provider.get("name", provider_id.title()),
                "provider_reference": reference_id,
                "arweave_tx_id": arweave_tx_id,
                "native_delivery": True,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            self._set_last_error(f"Error executing native AR funding: {e}")
            return None
    
    def _resolve_slippage(self, slippage_bps: Optional[int]) -> int:
        value = self.slippage_bps if slippage_bps is None else int(slippage_bps)
        if value < self.min_slippage_bps:
            return self.min_slippage_bps
        if value > self.max_slippage_bps:
            return self.max_slippage_bps
        return value
    
    def set_slippage_bps(self, slippage_bps: int):
        self.slippage_bps = self._resolve_slippage(slippage_bps)

    def _resolve_input_amount(self, usdc_amount: float) -> Optional[int]:
        try:
            amount = float(usdc_amount)
        except (TypeError, ValueError):
            self._set_last_error("Invalid USDC amount")
            return None

        if amount <= 0:
            self._set_last_error("USDC amount must be greater than zero")
            return None

        smallest_unit = int(amount * 1e6)
        if smallest_unit <= 0:
            self._set_last_error("USDC amount too small")
            return None
        return smallest_unit

    def _normalize_keypair_bytes(self, keypair_bytes: Any) -> Optional[bytes]:
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

    def _build_jupiter_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": "SapphireExchange/1.0"
        }
        if self.jupiter_api_key:
            headers["x-api-key"] = self.jupiter_api_key
        return headers

    async def _request_jupiter_quote(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        errors = []
        headers = self._build_jupiter_headers()
        timeout = aiohttp.ClientTimeout(total=self.quote_request_timeout)
        for endpoint in self.jupiter_quote_apis:
            response = await self._request_json(
                "GET",
                endpoint,
                params=params,
                headers=headers,
                timeout=timeout,
                max_retries=self.quote_max_retries,
            )
            if response:
                return response
            if self.last_error:
                errors.append(f"{endpoint} -> {self.last_error}")
        if errors:
            self._set_last_error("; ".join(errors))
        return None

    async def _request_jupiter_swap(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        errors = []
        headers = self._build_jupiter_headers()
        timeout = aiohttp.ClientTimeout(total=self.swap_request_timeout)
        for endpoint in self.jupiter_swap_apis:
            response = await self._request_json(
                "POST",
                endpoint,
                json=payload,
                headers=headers,
                timeout=timeout,
                max_retries=self.swap_max_retries,
            )
            if response:
                return response
            if self.last_error:
                errors.append(f"{endpoint} -> {self.last_error}")
        if errors:
            self._set_last_error("; ".join(errors))
        return None

    def _sign_swap_transaction(self, tx_bytes: bytes, keypair_bytes: bytes) -> Optional[bytes]:
        try:
            from solders.keypair import Keypair
            from solders.message import to_bytes_versioned
            from solders.transaction import VersionedTransaction

            keypair = Keypair.from_bytes(keypair_bytes)
            unsigned_tx = VersionedTransaction.from_bytes(tx_bytes)
            signature = keypair.sign_message(to_bytes_versioned(unsigned_tx.message))
            signed_tx = VersionedTransaction.populate(unsigned_tx.message, [signature])
            return bytes(signed_tx)
        except Exception as versioned_error:
            try:
                from solders.keypair import Keypair

                keypair = Keypair(keypair_bytes)
                if not Transaction:
                    self._set_last_error(f"Versioned signing failed: {versioned_error}")
                    return None
                tx = Transaction.from_bytes(tx_bytes)
                tx.sign([keypair])
                return bytes(tx)
            except Exception as legacy_error:
                self._set_last_error(
                    f"Error signing transaction: versioned={versioned_error}; legacy={legacy_error}"
                )
                return None
    
    async def _request_json(self, method: str, url: str, **kwargs) -> Optional[Dict[str, Any]]:
        if not self.http_session:
            await self.initialize()
        
        last_error = None
        timeout = kwargs.pop("timeout", aiohttp.ClientTimeout(total=self.request_timeout))
        max_retries = kwargs.pop("max_retries", self.max_retries)
        for attempt in range(max_retries + 1):
            try:
                async with self.http_session.request(method, url, timeout=timeout, **kwargs) as response:
                    if response.status == 200:
                        return await response.json()
                    error_text = await response.text()
                    last_error = f"HTTP {response.status}: {error_text[:120]}"
                    if response.status >= 500 and attempt < max_retries:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                        continue
                    break
            except asyncio.TimeoutError:
                last_error = "Request timed out"
                if attempt < max_retries:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
            except Exception as e:
                last_error = str(e)
                if attempt < max_retries:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                break
        
        if last_error:
            self._set_last_error(last_error)
        return None
    
    async def get_direct_swap_capability(self, output_mint: Optional[str] = None) -> Dict[str, Any]:
        """Check whether Jupiter can directly swap into an Arweave SPL token."""
        try:
            configured_mint = (output_mint or self._get_configured_output_mint()).strip()
            cached_mint = self._token_cache.get("last_checked_mint")
            cached_available = self._token_cache.get("direct_swap_available")
            cached_arweave_mint = self._token_cache.get("arweave_mint")

            cache_key = configured_mint or None
            if cached_mint == cache_key and cached_available is not None:
                cached_response = {
                    "available": bool(cached_available),
                    "mint": cached_arweave_mint if cached_available else configured_mint,
                    "reason": self.last_error,
                }
                if not cached_available:
                    cached_response["native_conversion"] = self.get_native_conversion_plan()
                return cached_response

            candidate_mints = []
            if configured_mint:
                candidate_mints.append(configured_mint)
            for mint in self.WRAPPED_AR_CANDIDATES:
                if mint not in candidate_mints:
                    candidate_mints.append(mint)

            for mint in candidate_mints:
                params = {
                    "inputMint": self.USDC_MINT,
                    "outputMint": mint,
                    "amount": int(1 * 1e6),
                    "slippageBps": self._resolve_slippage(None),
                }
                response = await self._request_jupiter_quote(params)
                if response and int(response.get("outAmount", 0) or 0) > 0:
                    self._token_cache["arweave_mint"] = mint
                    self._token_cache["direct_swap_available"] = True
                    self._token_cache["last_checked_mint"] = mint
                    return {
                        "available": True,
                        "mint": mint,
                        "reason": None,
                    }

            native_plan = self.get_native_conversion_plan()
            self._token_cache["arweave_mint"] = None
            self._token_cache["direct_swap_available"] = False
            self._token_cache["last_checked_mint"] = configured_mint or None
            self._set_last_error(native_plan["message"])
            return {
                "available": False,
                "mint": configured_mint or None,
                "reason": self.last_error,
                "native_conversion": native_plan,
            }

        except Exception as e:
            native_plan = self.get_native_conversion_plan()
            self._token_cache["arweave_mint"] = None
            self._token_cache["direct_swap_available"] = False
            self._token_cache["last_checked_mint"] = (output_mint or self._get_configured_output_mint()).strip() or None
            self._set_last_error(f"Error checking Arweave swap capability: {e}. {native_plan['message']}")
            return {
                "available": False,
                "mint": None,
                "reason": self.last_error,
                "native_conversion": native_plan,
            }

    async def discover_arweave_token(self) -> Optional[str]:
        """Discover the current Arweave token mint on Solana."""
        capability = await self.get_direct_swap_capability()
        if capability.get("available"):
            return capability.get("mint")
        return None
    
    async def get_quote(self, usdc_amount: float, output_mint: Optional[str] = None,
                        slippage_bps: Optional[int] = None) -> Optional[ArweaveSwapQuote]:
        """Get a Jupiter quote for swapping USDC to Arweave token."""
        try:
            self.last_error = None
            if not self.http_session:
                await self.initialize()
            
            resolved_slippage = self._resolve_slippage(slippage_bps)

            target_mint = (output_mint or "").strip()
            capability = await self.get_direct_swap_capability(output_mint=target_mint or None)
            if capability.get("available"):
                target_mint = capability.get("mint") or target_mint

            if not target_mint or not capability.get("available"):
                if not self.last_error:
                    self._set_last_error(self._build_native_provider_message())
                return None

            input_amount = self._resolve_input_amount(usdc_amount)
            if not input_amount:
                return None
            
            params = {
                "inputMint": self.USDC_MINT,
                "outputMint": target_mint,
                "amount": input_amount,
                "slippageBps": resolved_slippage,
                "onlyDirectRoutes": False,
                "asLegacyTransaction": False,
                "maxAccounts": 64,
            }

            data = await self._request_jupiter_quote(params)
            if not data:
                return None

            route_plan = (
                data.get("routePlanWithMetrics")
                or data.get("routePlanWithTokens")
                or data.get("routePlan")
                or []
            )
            output_amount = int(data.get("outAmount", 0) or 0)
            if output_amount <= 0 and route_plan and isinstance(route_plan, list):
                output_amount = int((route_plan[0] or {}).get("outAmount", 0) or 0)

            if output_amount <= 0:
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
            self.last_error = None
            if not self.http_session:
                await self.initialize()

            wallet_pubkey = (user_pubkey or "").strip()
            if not wallet_pubkey:
                self._set_last_error("User wallet public key is required")
                return None

            target_mint = (output_mint or "").strip()
            capability = await self.get_direct_swap_capability(output_mint=target_mint or None)
            if capability.get("available"):
                target_mint = capability.get("mint") or target_mint
            if not target_mint or not capability.get("available"):
                if not self.last_error:
                    self._set_last_error(self._build_native_provider_message())
                return None

            resolved_slippage = self._resolve_slippage(slippage_bps)
            input_amount = self._resolve_input_amount(usdc_amount)
            if not input_amount:
                return None

            quote_params = {
                "inputMint": self.USDC_MINT,
                "outputMint": target_mint,
                "amount": input_amount,
                "slippageBps": resolved_slippage,
                "onlyDirectRoutes": False,
                "asLegacyTransaction": False,
                "maxAccounts": 64,
            }
            quote_response = await self._request_jupiter_quote(quote_params)
            if not quote_response:
                if not self.last_error:
                    self._set_last_error("Failed to get swap quote")
                return None

            if int(quote_response.get("outAmount", 0) or 0) <= 0:
                self._set_last_error(f"Invalid quote response: {quote_response}")
                return None

            swap_request = {
                "quoteResponse": quote_response,
                "userPublicKey": wallet_pubkey,
                "wrapAndUnwrapSol": True,
                "prioritizationFeeLamports": 1000,
            }

            data = await self._request_jupiter_swap(swap_request)
            if not data:
                return None

            swap_tx = data.get("swapTransaction")
            if not swap_tx:
                self._set_last_error(f"Invalid swap response: {data}")
                return None

            self._token_cache["arweave_mint"] = target_mint
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
            self.last_error = None
            normalized_keypair = self._normalize_keypair_bytes(keypair_bytes)
            if not normalized_keypair:
                self._set_last_error("Valid private key required to execute swap")
                return None

            swap_tx_base64 = await self.build_swap_transaction(user_pubkey, usdc_amount, output_mint, slippage_bps)
            if not swap_tx_base64:
                if not self.last_error:
                    self._set_last_error("Failed to build swap transaction")
                return None

            try:
                tx_bytes = base64.b64decode(swap_tx_base64)
            except (binascii.Error, ValueError) as decode_error:
                self._set_last_error(f"Invalid swap transaction payload: {decode_error}")
                return None

            signed_tx_bytes = self._sign_swap_transaction(tx_bytes, normalized_keypair)
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
