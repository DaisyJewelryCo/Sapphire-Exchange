"""
everPay API client for Sapphire Exchange.

All everPay actions are signed client-side by the user's local wallet.
This app never sends private keys off device.
"""
from typing import Any, Dict, Optional, TypedDict, Literal

import aiohttp


EverpayTx = TypedDict(
    "EverpayTx",
    {
        "tokenSymbol": str,
        "action": Literal["transfer", "swap", "burn"],
        "from": str,
        "to": str,
        "amount": str,
        "fee": str,
        "feeRecipient": str,
        "nonce": str,
        "tokenID": str,
        "chainType": str,
        "chainID": str,
        "data": str,
        "version": str,
        "swapTo": str,
    },
    total=False,
)


class EverpayClient:
    """Small async client for the everPay API."""

    def __init__(self, base_url: str = "https://api.everpay.io"):
        self.base_url = (base_url or "https://api.everpay.io").rstrip("/")
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def get_info(self) -> Dict[str, Any]:
        session = await self._get_session()
        async with session.get(f"{self.base_url}/info", timeout=aiohttp.ClientTimeout(total=12)) as response:
            response.raise_for_status()
            return await response.json()

    async def get_balances(self, everpay_address: str) -> Dict[str, Any]:
        session = await self._get_session()
        async with session.get(
            f"{self.base_url}/balances/{everpay_address}",
            timeout=aiohttp.ClientTimeout(total=12),
        ) as response:
            response.raise_for_status()
            return await response.json()

    async def post_tx(self, tx: Dict[str, Any], sig: str) -> Dict[str, Any]:
        payload = dict(tx)
        payload["sig"] = sig
        session = await self._get_session()
        async with session.post(
            f"{self.base_url}/tx",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=12),
        ) as response:
            response.raise_for_status()
            return await response.json()
