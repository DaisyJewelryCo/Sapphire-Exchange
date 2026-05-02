"""
Arweave Purchase Service for Sapphire Exchange.
Handles native Arweave funding using everPay direct.
"""
import asyncio
import json
import time
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

import aiohttp
from Crypto.Hash import keccak

from services.funding_manager_service import get_funding_manager_service
from services.local_everpay_wallet_service import get_local_everpay_wallet_service


@dataclass
class ArweaveSwapQuote:
    """Quote for native Arweave funding."""
    input_amount: int
    output_amount: int
    price_impact: float
    route_description: str
    swap_transaction: Optional[str] = None
    fees: Dict[str, Any] = None
    executable: bool = False
    status_message: Optional[str] = None


class ArweavePurchaseService:
    """Service for purchasing native Arweave using everPay direct."""

    USDC_DECIMALS = 1_000_000
    AR_DECIMALS = 1_000_000_000_000
    TOKEN_IDENTIFIER_ALIASES = {
        "USDC-ETH-0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48": "ethereum-usdc-0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
        "AR-AR-0x0000000000000000000000000000000000000000": "arweave,ethereum-ar-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA,0x4fadc7a98f2dc96510e42dd1a74141eeae0c1543",
    }
    LEGACY_CHAIN_ALIASES = {
        "eth": "ethereum",
        "ethereum": "ethereum",
        "ar": "arweave",
        "arweave": "arweave",
        "bsc": "bsc",
        "sol": "solana",
        "solana": "solana",
    }

    def __init__(self, solana_client: Optional[Any] = None, rpc_url: Optional[str] = None):
        self.solana_client = solana_client
        self.rpc_url = rpc_url or "https://api.mainnet-beta.solana.com"
        self.http_session: Optional[aiohttp.ClientSession] = None
        self.max_retries = 3
        self.retry_delay = 1.5
        self.request_timeout = 12
        self.quote_request_timeout = 8
        self.quote_max_retries = 0
        self.swap_request_timeout = 12
        self.swap_max_retries = 1
        self.last_error: Optional[str] = None
        self._info_cache: Optional[Dict[str, Any]] = None
        self._info_cache_ts = 0.0
        self._last_nonce = 0

    async def initialize(self) -> bool:
        try:
            if not self.http_session:
                self.http_session = aiohttp.ClientSession()
            return True
        except Exception as e:
            print(f"Error initializing Arweave purchase service: {e}")
            return False

    async def shutdown(self):
        try:
            if self.http_session:
                await self.http_session.close()
                self.http_session = None
        except Exception as e:
            print(f"Error shutting down purchase service: {e}")

    def _set_last_error(self, message: str):
        self.last_error = message
        if message:
            print(f"[ArweavePurchaseService] {message}")

    def _get_native_provider_details(self) -> Dict[str, str]:
        funding_service = get_funding_manager_service()
        config = funding_service.config
        return {
            "id": "everpay",
            "name": "everPay",
            "service_url": (config.everpay_api_url or "https://api.everpay.io").strip(),
            "input_token": (config.everpay_input_token or self.TOKEN_IDENTIFIER_ALIASES["USDC-ETH-0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"]).strip(),
            "ar_token": (config.everpay_ar_token or self.TOKEN_IDENTIFIER_ALIASES["AR-AR-0x0000000000000000000000000000000000000000"]).strip(),
            "description": "Use everPay direct to swap credited funds into AR and withdraw native AR to the user's Arweave wallet.",
        }

    def _build_native_provider_message(self) -> str:
        provider = self._get_native_provider_details()
        return (
            f"Native AR funding is handled by {provider['name']} direct via {provider['service_url']}. "
            f"The local everPay wallet swaps credited funds into AR and withdraws native AR to the user's Arweave wallet."
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
                    last_error = f"HTTP {response.status}: {error_text[:160]}"
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

    async def _get_info(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        provider = self._get_native_provider_details()
        if not force_refresh and self._info_cache and (time.time() - self._info_cache_ts) < 300:
            return self._info_cache

        payload = await self._request_json(
            "GET",
            self._get_provider_api_url(provider, "/info"),
            timeout=aiohttp.ClientTimeout(total=self.quote_request_timeout),
            max_retries=self.quote_max_retries,
        )
        if payload:
            self._info_cache = payload
            self._info_cache_ts = time.time()
        return payload

    def _normalize_token_identifier(self, identifier: str) -> str:
        value = (identifier or "").strip()
        return self.TOKEN_IDENTIFIER_ALIASES.get(value, value)

    def _token_supports_chain(self, token: Dict[str, Any], chain_name: str) -> bool:
        supported = [item.strip().lower() for item in str(token.get("chainType", "")).split(",") if item.strip()]
        return chain_name.lower() in supported

    def _token_matches_identifier(self, token: Dict[str, Any], identifier: str) -> bool:
        normalized = self._normalize_token_identifier(identifier)
        lowered = normalized.lower()
        tag = str(token.get("tag", "")).strip()
        token_id = str(token.get("id", "")).strip()
        symbol = str(token.get("symbol", "")).strip()
        chain_type = str(token.get("chainType", "")).strip()

        if lowered in {tag.lower(), token_id.lower(), symbol.lower()}:
            return True

        parts = normalized.split("-", 2)
        if len(parts) == 3:
            legacy_symbol, legacy_chain, legacy_token_id = parts
            expected_chain = self.LEGACY_CHAIN_ALIASES.get(legacy_chain.strip().lower(), legacy_chain.strip().lower())
            if symbol.lower() != legacy_symbol.strip().lower():
                return False
            if not self._token_supports_chain(token, expected_chain):
                return False
            token_ids = [piece.strip().lower() for piece in token_id.split(",") if piece.strip()]
            if legacy_token_id.strip().lower() in token_ids:
                return True
            if expected_chain == "arweave" and symbol.lower() == "ar":
                return True

        return False

    async def _get_token_info(self, identifier: str) -> Optional[Dict[str, Any]]:
        info = await self._get_info()
        if not info:
            if not self.last_error:
                self._set_last_error("Could not load everPay token metadata")
            return None

        token_list = info.get("tokenList") or []
        for token in token_list:
            if self._token_matches_identifier(token, identifier):
                return token

        self._set_last_error(f"everPay token not found for identifier: {identifier}")
        return None

    def _resolve_input_amount(self, usdc_amount: float) -> Optional[int]:
        try:
            amount = Decimal(str(usdc_amount))
        except (InvalidOperation, TypeError, ValueError):
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

    async def _get_balance_payload(self, address: str) -> Optional[Dict[str, Any]]:
        provider = self._get_native_provider_details()
        return await self._request_json(
            "GET",
            self._get_provider_api_url(provider, f"/balances/{address}"),
            timeout=aiohttp.ClientTimeout(total=self.quote_request_timeout),
            max_retries=self.quote_max_retries,
        )

    async def _get_token_balance(self, address: str, token_identifier: str) -> Optional[int]:
        balances_payload = await self._get_balance_payload(address)
        if not balances_payload:
            if not self.last_error:
                self._set_last_error("Could not load everPay balances")
            return None

        for entry in balances_payload.get("balances", []):
            entry_tag = entry.get("tag")
            if self._token_matches_identifier({"tag": entry_tag, "id": entry_tag, "symbol": "", "chainType": ""}, token_identifier):
                try:
                    return int(entry.get("amount", 0) or 0)
                except (TypeError, ValueError):
                    return 0
            if self._token_matches_identifier({
                "tag": entry.get("tag", ""),
                "id": entry.get("tag", ""),
                "symbol": token_identifier,
                "chainType": entry.get("tag", "").split("-", 1)[0] if entry.get("tag") else "",
            }, token_identifier):
                try:
                    return int(entry.get("amount", 0) or 0)
                except (TypeError, ValueError):
                    return 0

        return 0

    def _get_next_nonce(self) -> str:
        current = int(time.time() * 1000)
        self._last_nonce = max(current, self._last_nonce + 1)
        return str(self._last_nonce)

    def _get_everpay_signer_address(self) -> Optional[str]:
        local_wallet_service = get_local_everpay_wallet_service()
        return local_wallet_service.get_wallet_address()

    def _serialize_everpay_data(self, value: Optional[Dict[str, Any]] = None) -> str:
        if not value:
            return ""
        return json.dumps(value, separators=(",", ":"), ensure_ascii=False)

    def _get_deposit_locker(self, info: Dict[str, Any], token: Dict[str, Any]) -> Optional[str]:
        chain_types = [segment.strip() for segment in str(token.get("chainType") or "").split(",") if segment.strip()]
        lockers = info.get("lockers") or {}
        for chain_type in chain_types:
            locker = lockers.get(chain_type)
            if locker:
                return locker
        if "ethereum" in chain_types:
            return info.get("ethLocker")
        if "arweave" in chain_types:
            return info.get("arLocker")
        return None

    async def _build_everpay_tx(
        self,
        action: str,
        token: Dict[str, Any],
        amount: str,
        from_address: str,
        to: str,
        nonce: str,
        target_chain_type: Optional[str] = None,
        fee: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        info = await self._get_info()
        if not info:
            if not self.last_error:
                self._set_last_error("Could not load everPay service metadata")
            return None

        fee_recipient = info.get("feeRecipient")
        if not fee_recipient:
            self._set_last_error("everPay info response is missing feeRecipient")
            return None

        transfer_fee = str(token.get("transferFee", "0") or "0")
        burn_fees = token.get("burnFees") or token.get("burnFeeMap") or {}
        resolved_fee = fee
        if resolved_fee is None:
            if action == "burn" and target_chain_type:
                resolved_fee = str(burn_fees.get(target_chain_type, "0") or "0")
            else:
                resolved_fee = transfer_fee

        payload = {
            "tokenSymbol": str(token.get("symbol") or ""),
            "action": action,
            "from": from_address,
            "to": to,
            "amount": str(amount),
            "fee": str(resolved_fee),
            "feeRecipient": fee_recipient,
            "nonce": nonce,
            "tokenID": str(token.get("id") or ""),
            "chainType": str(token.get("chainType") or ""),
            "chainID": str(token.get("chainID") or ""),
            "data": self._serialize_everpay_data(data),
            "version": "v1",
        }

        missing_values = [
            field for field in ("tokenSymbol", "tokenID", "chainType", "chainID") if not payload[field]
        ]
        if missing_values:
            self._set_last_error(
                f"everPay token metadata is incomplete for {token.get('tag') or token.get('symbol') or 'token'}: {', '.join(missing_values)}"
            )
            return None

        if extra_fields:
            payload.update(extra_fields)
        return payload

    def _build_legacy_signing_message(self, payload: Dict[str, Any]) -> str:
        local_wallet_service = get_local_everpay_wallet_service()
        return local_wallet_service.get_everpay_message_data(payload)

    def _sign_legacy_payload(self, payload: Dict[str, Any]) -> Optional[str]:
        local_wallet_service = get_local_everpay_wallet_service()

        if not local_wallet_service.is_wallet_loaded():
            self._set_last_error("Load the local everPay wallet before executing")
            return None

        try:
            return local_wallet_service.sign_everpay_tx(payload)
        except Exception as e:
            self._set_last_error(f"Error signing everPay transaction with local wallet: {e}")
            return None

    def _compute_everhash(self, payload: Dict[str, Any]) -> str:
        message = self._build_legacy_signing_message(payload)
        prefix = f"\x19Ethereum Signed Message:\n{len(message.encode('utf-8'))}".encode("utf-8")
        digest = keccak.new(digest_bits=256)
        digest.update(prefix + message.encode("utf-8"))
        return f"0x{digest.hexdigest()}"

    def _extract_provider_reference(self, payload: Dict[str, Any]) -> Optional[str]:
        candidate = self._find_first_value(
            payload,
            [
                "everHash",
                "hash",
                "id",
                "txHash",
                "targetChainTxHash",
                "referenceId",
                "purchaseId",
            ],
        )
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
        return None

    async def _submit_everpay_tx(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        provider = self._get_native_provider_details()
        signature = self._sign_legacy_payload(payload)
        if not signature:
            return None

        signed_payload = dict(payload)
        signed_payload["sig"] = signature
        local_reference = self._compute_everhash(payload)
        response = await self._request_json(
            "POST",
            self._get_provider_api_url(provider, "/tx"),
            json=signed_payload,
            timeout=aiohttp.ClientTimeout(total=self.swap_request_timeout),
            max_retries=self.swap_max_retries,
        )
        if response is None:
            return None

        return {
            "response": response,
            "payload": signed_payload,
            "reference": self._extract_provider_reference(response) or local_reference,
        }

    async def _poll_transaction_record(self, everhash: str, attempts: int = 5, delay: float = 2.0) -> Optional[Dict[str, Any]]:
        provider = self._get_native_provider_details()
        for _ in range(attempts):
            payload = await self._request_json(
                "GET",
                self._get_provider_api_url(provider, f"/tx/{everhash}"),
                timeout=aiohttp.ClientTimeout(total=self.swap_request_timeout),
                max_retries=0,
            )
            if payload:
                return payload
            await asyncio.sleep(delay)
        return None

    async def _await_balance_increase(
        self,
        address: str,
        token_identifier: str,
        starting_balance: int,
        attempts: int = 6,
        delay: float = 2.0,
    ) -> Optional[int]:
        for _ in range(attempts):
            current_balance = await self._get_token_balance(address, token_identifier)
            if current_balance is None:
                await asyncio.sleep(delay)
                continue
            if current_balance > starting_balance:
                return current_balance - starting_balance
            await asyncio.sleep(delay)
        return None

    async def _fetch_market_quote(self, usdc_amount: float) -> Optional[Dict[str, Any]]:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": "arweave",
            "vs_currencies": "usd",
        }
        payload = await self._request_json(
            "GET",
            url,
            params=params,
            timeout=aiohttp.ClientTimeout(total=self.quote_request_timeout),
            max_retries=self.quote_max_retries,
        )
        if not payload:
            return None

        arweave_data = payload.get("arweave") or {}
        usd_price = self._coerce_float(arweave_data.get("usd"))
        if not usd_price or usd_price <= 0:
            return None

        ar_amount = float(usdc_amount) / usd_price
        return {
            "usd_price": usd_price,
            "ar_amount": ar_amount,
        }

    def _is_execution_ready(self) -> bool:
        local_wallet_service = get_local_everpay_wallet_service()
        return bool(local_wallet_service.has_local_wallet() and self._get_everpay_signer_address())

    async def get_native_provider_quote(self, payment_amount: float, payment_currency: str = "USDC") -> Optional[Dict[str, Any]]:
        try:
            self.last_error = None
            payment_currency = (payment_currency or "USDC").strip().upper()
            if payment_currency != "USDC":
                self._set_last_error(f"everPay direct is configured for USDC input in this dialog, not {payment_currency}")
                return None

            input_amount = self._resolve_input_amount(payment_amount)
            if not input_amount:
                return None

            provider = self._get_native_provider_details()
            input_token = await self._get_token_info(provider["input_token"])
            ar_token = await self._get_token_info(provider["ar_token"])
            if not input_token or not ar_token:
                return None

            market_quote = await self._fetch_market_quote(payment_amount)
            if not market_quote:
                self._set_last_error("everPay token support loaded, but AR market pricing is temporarily unavailable")
                return None

            ar_amount = market_quote["ar_amount"]
            amount_winston = int(ar_amount * self.AR_DECIMALS)
            if amount_winston <= 0:
                self._set_last_error("everPay quote produced an invalid AR amount estimate")
                return None

            executable = self._is_execution_ready()
            status_message = (
                "everPay direct estimate ready. Executing will swap credited USDC from the local everPay wallet "
                "and withdraw native AR to the target Arweave wallet."
            )
            if not executable:
                status_message = (
                    "everPay pricing estimate is available, but execution is disabled until a local everPay wallet "
                    "is created or loaded for signing."
                )

            return {
                "provider": provider,
                "payment_currency": payment_currency,
                "payment_amount": float(payment_amount),
                "ar_amount": ar_amount,
                "amount_winston": str(amount_winston),
                "unit_price": market_quote["usd_price"],
                "raw": {
                    "input_token": input_token,
                    "output_token": ar_token,
                    "market_quote": market_quote,
                },
                "executable": executable,
                "status_message": status_message,
            }
        except Exception as e:
            self._set_last_error(f"Error getting everPay quote: {e}")
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

            output_amount = int(native_quote.get("amount_winston", "0") or 0)
            if output_amount <= 0:
                self._set_last_error("everPay quote did not include a valid AR amount")
                return None

            unit_price = native_quote.get("unit_price", 0)
            return ArweaveSwapQuote(
                input_amount=input_amount,
                output_amount=output_amount,
                price_impact=0.0,
                route_description=f"everPay Direct (AR/USD: ${unit_price:.6f})",
                fees=native_quote.get("raw") if isinstance(native_quote.get("raw"), dict) else None,
                executable=bool(native_quote.get("executable")),
                status_message=native_quote.get("status_message"),
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
        wallet_password: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        try:
            self.last_error = None
            payment_currency = (payment_currency or "USDC").strip().upper()
            if payment_currency != "USDC":
                self._set_last_error("everPay direct execution is currently configured for USDC only")
                return None

            local_wallet_service = get_local_everpay_wallet_service()
            if wallet_password and local_wallet_service.has_local_wallet() and not local_wallet_service.is_wallet_loaded():
                try:
                    local_wallet_service.load_local_wallet(wallet_password)
                except Exception as e:
                    self._set_last_error(f"Failed to unlock local everPay wallet: {e}")
                    return None

            provider = self._get_native_provider_details()
            signer_address = self._get_everpay_signer_address()
            if not signer_address:
                if not self.last_error:
                    self._set_last_error("Create or load a local everPay wallet before executing")
                return None

            target_arweave_address = (arweave_address or "").strip()
            if not target_arweave_address:
                self._set_last_error("Arweave wallet address is required for native AR funding")
                return None

            input_amount = self._resolve_input_amount(payment_amount)
            if not input_amount:
                return None

            input_token = await self._get_token_info(provider["input_token"])
            ar_token = await self._get_token_info(provider["ar_token"])
            if not input_token or not ar_token:
                return None

            starting_input_balance = await self._get_token_balance(signer_address, input_token["tag"])
            if starting_input_balance is None:
                return None

            funding_submission = None
            if starting_input_balance < input_amount:
                shortfall = input_amount - starting_input_balance
                required_amount = Decimal(input_amount) / Decimal(self.USDC_DECIMALS)
                available_amount = Decimal(starting_input_balance) / Decimal(self.USDC_DECIMALS)
                shortfall_amount = Decimal(shortfall) / Decimal(self.USDC_DECIMALS)
                info = await self._get_info()
                deposit_locker = self._get_deposit_locker(info or {}, input_token) if info else None
                funding_message = (
                    f"Configured everPay account has insufficient {payment_currency} balance. "
                    f"Required {required_amount.normalize()}, available {available_amount.normalize()}, "
                    f"shortfall {shortfall_amount.normalize()} {payment_currency}."
                )
                if deposit_locker:
                    funding_message = (
                        f"{funding_message} Deposit the shortfall to the everPay {input_token.get('chainType', 'input')} "
                        f"locker first: {deposit_locker}."
                    )
                self._set_last_error(funding_message)
                return None

            starting_ar_balance = await self._get_token_balance(signer_address, ar_token["tag"])
            if starting_ar_balance is None:
                return None

            swap_payload = await self._build_everpay_tx(
                action="swap",
                token=input_token,
                amount=str(input_amount),
                from_address=signer_address,
                to="everpay",
                nonce=self._get_next_nonce(),
                data={"swapTo": ar_token["tag"]},
                extra_fields={"swapTo": ar_token["tag"]},
            )
            if not swap_payload:
                return None
            swap_submission = await self._submit_everpay_tx(swap_payload)
            if not swap_submission:
                return None

            ar_delta = await self._await_balance_increase(
                signer_address,
                ar_token["tag"],
                starting_ar_balance,
            )
            if not ar_delta or ar_delta <= 0:
                self._set_last_error(
                    "everPay swap submitted, but no AR balance increase was observed before the timeout."
                )
                return None

            withdraw_payload = await self._build_everpay_tx(
                action="burn",
                token=ar_token,
                amount=str(ar_delta),
                from_address=signer_address,
                to=target_arweave_address,
                nonce=self._get_next_nonce(),
                target_chain_type="arweave",
                data={"targetChainType": "arweave"},
            )
            if not withdraw_payload:
                return None
            withdraw_submission = await self._submit_everpay_tx(withdraw_payload)
            if not withdraw_submission:
                return None

            withdraw_reference = withdraw_submission["reference"]
            withdraw_status = None
            arweave_tx_id = None
            if withdraw_reference.startswith("0x"):
                withdraw_status = await self._poll_transaction_record(withdraw_reference)
                if withdraw_status:
                    arweave_tx_id = self._find_first_value(withdraw_status, ["targetChainTxHash", "arweaveTxId", "txHash"])

            return {
                "success": True,
                "transaction_id": swap_submission["reference"],
                "amount_usdc": payment_amount,
                "provider": provider.get("name", "everPay"),
                "provider_reference": withdraw_reference,
                "arweave_tx_id": arweave_tx_id,
                "native_delivery": True,
                "timestamp": datetime.now().isoformat(),
                "funding_transaction_id": funding_submission["reference"] if funding_submission else None,
                "swap_transaction_id": swap_submission["reference"],
                "withdraw_transaction_id": withdraw_reference,
                "payer_address": user_pubkey,
                "everpay_address": signer_address,
                "withdraw_amount_winston": str(ar_delta),
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
        wallet_password: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        try:
            self.last_error = None
            return await self.execute_native_purchase(
                user_pubkey,
                usdc_amount,
                arweave_address=arweave_address or "",
                keypair_bytes=keypair_bytes,
                payment_currency=payment_currency,
                wallet_password=wallet_password,
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
