"""
everPay direct non-custodial flow for Sapphire Exchange.

This app never sends private keys off device.
All everPay actions are signed client-side by the user's local wallet.
"""
from typing import Any, Dict, Optional
import json
import time

from services.everpay_client import EverpayClient
from services.funding_manager_service import get_funding_manager_service
from services.local_everpay_wallet_service import get_local_everpay_wallet_service


class EverpayDirectService:
    """Client-side everPay rail wrapper for local wallet operations."""

    def __init__(self):
        self._last_nonce = 0

    def _provider_config(self) -> Dict[str, str]:
        config = get_funding_manager_service().config
        return {
            "base_url": (config.everpay_api_url or "https://api.everpay.io").strip(),
            "input_token": (config.everpay_input_token or "ethereum-usdc-0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48").strip(),
            "ar_token": (config.everpay_ar_token or "arweave,ethereum-ar-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA,0x4fadc7a98f2dc96510e42dd1a74141eeae0c1543").strip(),
        }

    def _next_nonce(self) -> str:
        current = int(time.time() * 1000)
        self._last_nonce = max(current, self._last_nonce + 1)
        return str(self._last_nonce)

    async def get_info(self) -> Dict[str, Any]:
        config = self._provider_config()
        client = EverpayClient(config["base_url"])
        try:
            return await client.get_info()
        finally:
            await client.close()

    async def get_balances(self, everpay_address: Optional[str] = None) -> Dict[str, Any]:
        local_wallet_service = get_local_everpay_wallet_service()
        address = everpay_address or local_wallet_service.get_wallet_address()
        if not address:
            raise ValueError("No local everPay wallet found")
        config = self._provider_config()
        client = EverpayClient(config["base_url"])
        try:
            return await client.get_balances(address)
        finally:
            await client.close()

    def _serialize_data(self, value: Optional[Dict[str, Any]] = None) -> str:
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

    def _token_matches_identifier(self, token: Dict[str, Any], identifier: str) -> bool:
        candidate = (identifier or "").strip()
        if not candidate:
            return False
        lowered_candidate = candidate.lower()
        lowered_tag = str(token.get("tag") or "").lower()
        lowered_symbol = str(token.get("symbol") or "").lower()
        lowered_token_id = str(token.get("id") or "").lower()
        lowered_chain_type = str(token.get("chainType") or "").lower()
        return any(
            value and lowered_candidate == value
            for value in (
                lowered_tag,
                lowered_symbol,
                lowered_token_id,
                f"{lowered_chain_type}-{lowered_symbol}-{lowered_token_id}",
            )
        ) or lowered_candidate in lowered_tag

    async def _get_token_info(self, identifier: str) -> Dict[str, Any]:
        info = await self.get_info()
        for token in info.get("tokenList", []):
            if self._token_matches_identifier(token, identifier):
                return token
        raise ValueError(f"everPay token not found for identifier: {identifier}")

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
    ) -> Dict[str, Any]:
        info = await self.get_info()
        fee_recipient = info.get("feeRecipient")
        if not fee_recipient:
            raise ValueError("everPay info response is missing feeRecipient")

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
            "data": self._serialize_data(data),
            "version": "v1",
        }
        if extra_fields:
            payload.update(extra_fields)
        return payload

    async def submit_everpay_tx(self, tx: Dict[str, Any]) -> Dict[str, Any]:
        local_wallet_service = get_local_everpay_wallet_service()
        config = self._provider_config()
        return await local_wallet_service.submit_everpay_tx(tx, base_url=config["base_url"])

    async def fund_everpay(self, amount: str, token_id: str) -> Dict[str, Any]:
        local_wallet_service = get_local_everpay_wallet_service()
        address = local_wallet_service.get_wallet_address()
        if not address:
            raise ValueError("No local everPay wallet found")
        token = await self._get_token_info(token_id)
        info = await self.get_info()
        deposit_locker = self._get_deposit_locker(info, token)
        if not deposit_locker:
            raise ValueError("everPay deposit locker is unavailable for the configured token")
        raise ValueError(
            f"everPay funding requires a deposit to the {token.get('chainType', 'input')} locker {deposit_locker}; "
            f"direct funding via /tx is not supported for {token.get('tag') or token_id}."
        )

    async def swap_to_ar(self, amount_usdc: str) -> Dict[str, Any]:
        local_wallet_service = get_local_everpay_wallet_service()
        config = self._provider_config()
        address = local_wallet_service.get_wallet_address()
        if not address:
            raise ValueError("No local everPay wallet found")
        input_token = await self._get_token_info(config["input_token"])
        ar_token = await self._get_token_info(config["ar_token"])
        tx = await self._build_everpay_tx(
            action="swap",
            token=input_token,
            amount=str(amount_usdc),
            from_address=address,
            to="everpay",
            nonce=self._next_nonce(),
            data={"swapTo": ar_token["tag"]},
            extra_fields={"swapTo": ar_token["tag"]},
        )
        return await self.submit_everpay_tx(tx)

    async def withdraw_ar_to_arweave(self, amount_ar: str, arweave_address: str) -> Dict[str, Any]:
        local_wallet_service = get_local_everpay_wallet_service()
        config = self._provider_config()
        address = local_wallet_service.get_wallet_address()
        if not address:
            raise ValueError("No local everPay wallet found")
        ar_token = await self._get_token_info(config["ar_token"])
        tx = await self._build_everpay_tx(
            action="burn",
            token=ar_token,
            amount=str(amount_ar),
            from_address=address,
            to=arweave_address,
            nonce=self._next_nonce(),
            target_chain_type="arweave",
            data={"targetChainType": "arweave"},
        )
        return await self.submit_everpay_tx(tx)


_everpay_direct_service: Optional[EverpayDirectService] = None


def get_everpay_direct_service() -> EverpayDirectService:
    global _everpay_direct_service
    if _everpay_direct_service is None:
        _everpay_direct_service = EverpayDirectService()
    return _everpay_direct_service
