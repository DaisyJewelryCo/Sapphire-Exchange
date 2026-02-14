"""
Solana Balance Service for Sapphire Exchange.
Fetches native SOL and SPL token (USDC) balances using Solana RPC.
"""
import asyncio
import aiohttp
from typing import Dict, Optional, Any, List
from dataclasses import dataclass


@dataclass
class BalanceInfo:
    """Information about a wallet balance."""
    amount_lamports: int
    amount_human: float
    decimals: int
    mint: Optional[str] = None


class SolanaBalanceService:
    """Service for fetching Solana wallet balances."""
    
    # Canonical token mints on Solana mainnet
    WSOL_MINT = "So11111111111111111111111111111111111111112"  # Wrapped SOL
    USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC
    
    # Decimals for tokens
    SOL_DECIMALS = 9
    USDC_DECIMALS = 6
    
    def __init__(self, rpc_url: str = "https://api.mainnet-beta.solana.com"):
        """Initialize the balance service."""
        self.rpc_url = rpc_url
        self.http_session: Optional[aiohttp.ClientSession] = None
        self.request_timeout = 10
        self.max_retries = 3
        self.retry_delay = 1.0
        self.last_error: Optional[str] = None
    
    async def initialize(self) -> bool:
        """Initialize the service."""
        try:
            if not self.http_session:
                self.http_session = aiohttp.ClientSession()
            return True
        except Exception as e:
            print(f"Error initializing Solana balance service: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown the service."""
        try:
            if self.http_session:
                await self.http_session.close()
        except Exception as e:
            print(f"Error shutting down balance service: {e}")
    
    def _set_last_error(self, message: str):
        """Set last error message."""
        self.last_error = message
    
    async def _make_rpc_call(self, method: str, params: List[Any] = None) -> Optional[Dict[str, Any]]:
        """Make an RPC call to Solana network."""
        if not self.http_session:
            await self.initialize()
        
        if params is None:
            params = []
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }
        
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                timeout = aiohttp.ClientTimeout(total=self.request_timeout)
                async with self.http_session.post(
                    self.rpc_url,
                    json=payload,
                    timeout=timeout
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "result" in data:
                            return data["result"]
                        elif "error" in data:
                            error_msg = data["error"].get("message", "Unknown error")
                            last_error = f"RPC Error: {error_msg}"
                            if attempt < self.max_retries:
                                await asyncio.sleep(self.retry_delay * (attempt + 1))
                                continue
                        else:
                            last_error = "Invalid RPC response"
                            break
                    else:
                        last_error = f"HTTP {response.status}"
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
    
    async def get_native_sol_balance(self, wallet_address: str) -> Optional[BalanceInfo]:
        """Get native SOL balance for a wallet address."""
        try:
            result = await self._make_rpc_call("getBalance", [wallet_address])
            if result is None:
                self._set_last_error("Failed to fetch SOL balance")
                return None
            
            lamports = result.get("value", 0)
            amount_sol = lamports / (10 ** self.SOL_DECIMALS)
            
            return BalanceInfo(
                amount_lamports=lamports,
                amount_human=amount_sol,
                decimals=self.SOL_DECIMALS,
                mint=None
            )
        except Exception as e:
            self._set_last_error(f"Error getting SOL balance: {e}")
            return None
    
    async def get_token_accounts_by_owner(self, wallet_address: str, 
                                         filter_mint: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """Get token accounts for a wallet address, optionally filtered by mint."""
        try:
            # Use Token Program ID for SPL tokens
            token_program_id = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
            
            params = [
                wallet_address,
                {"programId": token_program_id},
                {
                    "encoding": "jsonParsed",
                    "dataSlice": None
                }
            ]
            
            result = await self._make_rpc_call("getTokenAccountsByOwner", params)
            if result is None:
                self._set_last_error("Failed to fetch token accounts")
                return None
            
            accounts = result.get("value", [])
            
            if filter_mint:
                accounts = [
                    acc for acc in accounts
                    if acc.get("account", {}).get("data", {}).get("parsed", {}).get("info", {}).get("mint") == filter_mint
                ]
            
            return accounts
        except Exception as e:
            self._set_last_error(f"Error getting token accounts: {e}")
            return None
    
    async def get_usdc_balance(self, wallet_address: str) -> Optional[BalanceInfo]:
        """Get USDC token balance for a wallet address."""
        try:
            accounts = await self.get_token_accounts_by_owner(wallet_address, self.USDC_MINT)
            if not accounts:
                return BalanceInfo(
                    amount_lamports=0,
                    amount_human=0.0,
                    decimals=self.USDC_DECIMALS,
                    mint=self.USDC_MINT
                )
            
            # Use first USDC account found
            token_info = accounts[0].get("account", {}).get("data", {}).get("parsed", {}).get("info", {})
            amount_str = token_info.get("tokenAmount", {}).get("amount", "0")
            
            try:
                amount_lamports = int(amount_str)
            except (ValueError, TypeError):
                amount_lamports = 0
            
            amount_usdc = amount_lamports / (10 ** self.USDC_DECIMALS)
            
            return BalanceInfo(
                amount_lamports=amount_lamports,
                amount_human=amount_usdc,
                decimals=self.USDC_DECIMALS,
                mint=self.USDC_MINT
            )
        except Exception as e:
            self._set_last_error(f"Error getting USDC balance: {e}")
            return None
    
    async def get_wrapped_sol_balance(self, wallet_address: str) -> Optional[BalanceInfo]:
        """Get wrapped SOL (wSOL) token balance for a wallet address."""
        try:
            accounts = await self.get_token_accounts_by_owner(wallet_address, self.WSOL_MINT)
            if not accounts:
                return BalanceInfo(
                    amount_lamports=0,
                    amount_human=0.0,
                    decimals=self.SOL_DECIMALS,
                    mint=self.WSOL_MINT
                )
            
            # Use first wSOL account found
            token_info = accounts[0].get("account", {}).get("data", {}).get("parsed", {}).get("info", {})
            amount_str = token_info.get("tokenAmount", {}).get("amount", "0")
            
            try:
                amount_lamports = int(amount_str)
            except (ValueError, TypeError):
                amount_lamports = 0
            
            amount_wsol = amount_lamports / (10 ** self.SOL_DECIMALS)
            
            return BalanceInfo(
                amount_lamports=amount_lamports,
                amount_human=amount_wsol,
                decimals=self.SOL_DECIMALS,
                mint=self.WSOL_MINT
            )
        except Exception as e:
            self._set_last_error(f"Error getting wrapped SOL balance: {e}")
            return None
    
    async def get_all_balances(self, wallet_address: str) -> Dict[str, BalanceInfo]:
        """Get all balances (native SOL, USDC, wSOL) for a wallet address."""
        balances = {}
        
        try:
            # Get native SOL
            sol_balance = await self.get_native_sol_balance(wallet_address)
            if sol_balance:
                balances['SOL'] = sol_balance
            
            # Get USDC
            usdc_balance = await self.get_usdc_balance(wallet_address)
            if usdc_balance:
                balances['USDC'] = usdc_balance
            
            # Get wSOL (optional, less common)
            wsol_balance = await self.get_wrapped_sol_balance(wallet_address)
            if wsol_balance and wsol_balance.amount_human > 0:
                balances['wSOL'] = wsol_balance
            
            return balances
        except Exception as e:
            self._set_last_error(f"Error getting all balances: {e}")
            return {}


async def get_solana_balance_service() -> SolanaBalanceService:
    """Factory function to get or create Solana balance service singleton."""
    if not hasattr(get_solana_balance_service, '_instance'):
        get_solana_balance_service._instance = SolanaBalanceService()
        await get_solana_balance_service._instance.initialize()
    return get_solana_balance_service._instance
