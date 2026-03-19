"""
everPay direct non-custodial flow for Sapphire Exchange.

This app never sends private keys off device.
All everPay actions are signed client-side by the user's local wallet.
"""
from typing import Any, Dict, Optional
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

    async def submit_everpay_tx(self, tx: Dict[str, Any]) -> Dict[str, Any]:
        local_wallet_service = get_local_everpay_wallet_service()
        config = self._provider_config()
        return await local_wallet_service.submit_everpay_tx(tx, base_url=config["base_url"])

    async def fund_everpay(self, amount: str, token_id: str) -> Dict[str, Any]:
        local_wallet_service = get_local_everpay_wallet_service()
        address = local_wallet_service.get_wallet_address()
        if not address:
            raise ValueError("No local everPay wallet found")
        tx = {
            "action": "transfer",
            "from": address,
            "to": "everpay",
            "token": token_id,
            "amount": str(amount),
            "nonce": self._next_nonce(),
        }
        return await self.submit_everpay_tx(tx)

    async def swap_to_ar(self, amount_usdc: str) -> Dict[str, Any]:
        local_wallet_service = get_local_everpay_wallet_service()
        config = self._provider_config()
        address = local_wallet_service.get_wallet_address()
        if not address:
            raise ValueError("No local everPay wallet found")
        tx = {
            "action": "swap",
            "from": address,
            "token": config["input_token"],
            "amount": str(amount_usdc),
            "swapTo": config["ar_token"],
            "nonce": self._next_nonce(),
        }
        return await self.submit_everpay_tx(tx)

    async def withdraw_ar_to_arweave(self, amount_ar: str, arweave_address: str) -> Dict[str, Any]:
        local_wallet_service = get_local_everpay_wallet_service()
        config = self._provider_config()
        address = local_wallet_service.get_wallet_address()
        if not address:
            raise ValueError("No local everPay wallet found")
        tx = {
            "action": "withdraw",
            "from": address,
            "token": config["ar_token"],
            "amount": str(amount_ar),
            "target": arweave_address,
            "nonce": self._next_nonce(),
        }
        return await self.submit_everpay_tx(tx)


_everpay_direct_service: Optional[EverpayDirectService] = None


def get_everpay_direct_service() -> EverpayDirectService:
    global _everpay_direct_service
    if _everpay_direct_service is None:
        _everpay_direct_service = EverpayDirectService()
    return _everpay_direct_service
