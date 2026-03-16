"""
Arweave Purchase Service for Sapphire Exchange.
Handles native Arweave funding using external provider APIs.
"""
import asyncio
import base64
import binascii
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp

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
    """Quote for native Arweave funding."""
    input_amount: int
    output_amount: int
    price_impact: float
    route_description: str
    swap_transaction: Optional[str] = None
    fees: Dict[str, Any] = None


class ArweavePurchaseService:
    """Service for purchasing native Arweave using Solana-based provider APIs."""

    USDC_DECIMALS = 1_000_000
    AR_DECIMALS = 1_000_000_000_000

    def __init__(self, solana_client: Optional[AsyncClient] = None, rpc_url: Optional[str] = None):
        self.solana_client = solana_client
        self.rpc_url = rpc_url or "https://api.mainnet-beta.solana.com"
        self.http_session: Optional[aiohttp.ClientSession] = None
        self.max_retries = 3
        self.retry_delay = 1.5
        self.request_timeout = 12
        self.quote_request_timeout = 4
        self.quote_max_retries = 0
        self.swap_request_timeout = 10
        self.swap_max_retries = 1
        self.last_error: Optional[str] = None

    async def initialize(self) -> bool:
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
        try:
            if self.http_session:
                await self.http_session.close()
            if self.solana_client:
                await self.solana_client.close()
        except Exception as e:
            print(f"Error shutting down purchase service: {e}")

    def _set_last_error(self, message: str):
        self.last_error = message
        if message:
            print(f"[ArweavePurchaseService] {message}")

    def _get_native_provider_details(self) -> Dict[str, str]:
        funding_service = get_funding_manager_service()
        config = funding_service.config
        provider = (config.arweave_native_provider or "turbo").strip().lower()

        turbo_service_url = (config.turbo_payment_service_url or "https://payment.ardrive.io/v1").strip()
        if turbo_service_url == "https://turbo.arweave.dev":
            turbo_service_url = "https://payment.ardrive.io/v1"

        providers = {
            "turbo": {
                "id": "turbo",
                "name": "Turbo",
                "service_url": turbo_service_url,
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

    def _get_native_provider_limitations(self, provider: Dict[str, str]) -> Optional[str]:
        provider_id = provider.get("id", "")
        if provider_id == "arseeding":
            return (
                "Arseeding's public API does not expose a native AR wallet-funding quote or purchase endpoint. "
                "Its documented API is for bundle/upload payments, so this error is not caused by low SOL gas."
            )
        if provider_id == "turbo":
            return (
                "Turbo's documented public API provides upload-credit/payment endpoints, not a documented native AR "
                "wallet-funding API for this flow. This error is not caused by low SOL gas."
            )
        return None

    def _build_native_provider_message(self) -> str:
        provider = self._get_native_provider_details()
        limitation = self._get_native_provider_limitations(provider)
        if limitation:
            return limitation
        return (
            f"Native AR funding is handled by {provider['name']} via {provider['service_url']}. "
            f"The purchase will convert supported Solana funds and deliver AR to your Arweave wallet."
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

    def _find_first_value(self, payload: Any, key_names: List[str]) -> Any:
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
            order_id = self._find_first_value(payload, ["orderId"])
            if isinstance(order_id, str) and order_id.strip():
                return order_id.strip()
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

    def _resolve_input_amount(self, usdc_amount: float) -> Optional[int]:
        try:
            amount = float(usdc_amount)
        except (TypeError, ValueError):
            self._set_last_error("Invalid USDC amount")
            return None

        if amount <= 0:
            self._set_last_error("USDC amount must be greater than zero")
            return None

        smallest_unit = int(amount * self.USDC_DECIMALS)
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

    async def get_native_provider_quote(self, payment_amount: float, payment_currency: str = "USDC") -> Optional[Dict[str, Any]]:
        try:
            self.last_error = None
            provider = self._get_native_provider_details()
            limitation = self._get_native_provider_limitations(provider)
            if limitation:
                self._set_last_error(limitation)
                return None

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
                "amount_winston": str(max(int(ar_amount * self.AR_DECIMALS), 1)),
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

            return await self._request_json(
                "GET",
                self._get_provider_api_url(provider, status_path),
                timeout=aiohttp.ClientTimeout(total=self.swap_request_timeout),
                max_retries=self.swap_max_retries,
            )
        except Exception as e:
            self._set_last_error(f"Error checking provider purchase status: {e}")
            return None

    async def get_quote(
        self,
        usdc_amount: float,
        output_mint: Optional[str] = None,
        slippage_bps: Optional[int] = None,
    ) -> Optional[ArweaveSwapQuote]:
        try:
            self.last_error = None
            input_amount = self._resolve_input_amount(usdc_amount)
            if not input_amount:
                return None

            native_quote = await self.get_native_provider_quote(usdc_amount, payment_currency="USDC")
            if not native_quote:
                return None

            provider = native_quote.get("provider", {})
            provider_name = provider.get("name", "Provider")
            unit_price = native_quote.get("unit_price", 0)
            output_amount = int(native_quote.get("amount_winston", "0") or 0)
            if output_amount <= 0:
                self._set_last_error(f"{provider_name} quote did not include a valid AR amount")
                return None

            return ArweaveSwapQuote(
                input_amount=input_amount,
                output_amount=output_amount,
                price_impact=0.0,
                route_description=f"{provider_name} Native AR API (USDC/AR: ${unit_price:.6f})",
                fees=native_quote.get("raw") if isinstance(native_quote.get("raw"), dict) else None,
            )
        except Exception as e:
            self._set_last_error(f"Error getting native AR quote: {e}")
            return None

    async def execute_native_purchase(
        self,
        user_pubkey: str,
        payment_amount: float,
        arweave_address: str,
        keypair_bytes: Optional[bytes] = None,
        payment_currency: str = "USDC",
    ) -> Optional[Dict[str, Any]]:
        try:
            self.last_error = None
            provider = self._get_native_provider_details()
            limitation = self._get_native_provider_limitations(provider)
            if limitation:
                self._set_last_error(limitation)
                return None

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

    async def execute_swap(
        self,
        user_pubkey: str,
        usdc_amount: float,
        keypair_bytes: Optional[bytes] = None,
        output_mint: Optional[str] = None,
        slippage_bps: Optional[int] = None,
        arweave_address: Optional[str] = None,
        payment_currency: str = "USDC",
    ) -> Optional[Dict[str, Any]]:
        try:
            self.last_error = None
            return await self.execute_native_purchase(
                user_pubkey,
                usdc_amount,
                arweave_address=arweave_address or "",
                keypair_bytes=keypair_bytes,
                payment_currency=payment_currency,
            )
        except Exception as e:
            self._set_last_error(f"Error executing native AR funding: {e}")
            return None

    async def estimate_arweave_output(self, usdc_amount: float) -> Optional[float]:
        try:
            quote = await self.get_quote(usdc_amount)
            if not quote:
                return None
            return quote.output_amount / self.AR_DECIMALS
        except Exception as e:
            print(f"Error estimating Arweave output: {e}")
            return None


arweave_purchase_service = None


async def get_arweave_purchase_service(config: Optional[Dict[str, Any]] = None) -> ArweavePurchaseService:
    global arweave_purchase_service

    if not arweave_purchase_service:
        rpc_url = config.get("solana", {}).get("rpc_url") if config else None
        arweave_purchase_service = ArweavePurchaseService(rpc_url=rpc_url)
        await arweave_purchase_service.initialize()

    return arweave_purchase_service
