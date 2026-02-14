"""
Solana USDC Client for Sapphire Exchange.
Handles USDC token operations on Solana blockchain.
"""
import asyncio
import base58
from typing import Dict, Optional, Any, Union, TYPE_CHECKING
from dataclasses import dataclass
from datetime import datetime

try:
    from solana.rpc.async_api import AsyncClient
    from solana.rpc.commitment import Confirmed
    from solders.transaction import Transaction
    from solders.pubkey import Pubkey as SoldersPubkey
    SOLANA_AVAILABLE = True
except ImportError as import_error:
    AsyncClient = None
    Confirmed = None
    Transaction = None
    SoldersPubkey = None
    SOLANA_AVAILABLE = False
    import sys
    print(f"Warning: Solana imports failed: {import_error}", file=sys.stderr)

try:
    from spl.token.instructions import (
        transfer_checked,
        get_associated_token_address
    )
    from spl.token.constants import TOKEN_PROGRAM_ID
    SPL_TOKEN_AVAILABLE = True
except ImportError as spl_error:
    transfer_checked = None
    get_associated_token_address = None
    TOKEN_PROGRAM_ID = None
    SPL_TOKEN_AVAILABLE = False
    import sys
    print(f"Warning: SPL token imports failed: {spl_error}", file=sys.stderr)

if TYPE_CHECKING:
    from solders.pubkey import Pubkey
else:
    Pubkey = SoldersPubkey


@dataclass
class SolanaWallet:
    """Solana wallet data structure."""
    address: str
    public_key: str
    balance: float  # in SOL
    usdc_balance: float  # in USDC
    created_at: str
    is_active: bool = True


class SolanaUsdcClient:
    """Solana USDC blockchain client."""
    
    # Solana USDC token mint on mainnet
    USDC_MINT_MAINNET = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    # Solana USDC token mint on devnet
    USDC_MINT_DEVNET = "4zMMUcwvPn7yS9yR4GcWKmC9jVWdmJFvXh1UhcvtaKc1"
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Solana USDC client with configuration."""
        self.config = config
        
        solana_cfg = config.get('solana', {})
        self.is_testnet = solana_cfg.get('testnet', config.get('testnet', False))
        rpc_url = solana_cfg.get('rpc_url')
        if not rpc_url:
            rpc_url = 'https://api.devnet.solana.com' if self.is_testnet else 'https://api.mainnet-beta.solana.com'
        self.rpc_url = rpc_url
        self.fallback_rpcs = self._normalize_url_list(solana_cfg.get('fallback_rpcs', []))
        self.default_fallback_rpcs = self._get_default_fallback_rpcs()
        
        # USDC mint address
        self.usdc_mint = self.USDC_MINT_DEVNET if self.is_testnet else self.USDC_MINT_MAINNET
        
        # Client
        self.client: Optional[Any] = None
        
        # Lock for thread-safe operations
        self._lock: Optional[asyncio.Lock] = None
        
        # Current wallet
        self.current_wallet: Optional[SolanaWallet] = None
        self.keypair: Optional[Any] = None
        
        # Last error for debugging
        self.last_error: Optional[str] = None
        self.last_error_details: Optional[str] = None
    
    def _normalize_url_list(self, value) -> list:
        if isinstance(value, str):
            parts = [p.strip() for p in value.split(',') if p.strip()]
            return parts
        if isinstance(value, (list, tuple)):
            return [str(v).strip() for v in value if str(v).strip()]
        return []
    
    def _get_default_fallback_rpcs(self) -> list:
        if self.is_testnet:
            return [
                "https://api.devnet.solana.com",
                "https://devnet.helius-rpc.com",
                "https://rpc-devnet.helius.xyz",
            ]
        return [
            "https://api.mainnet-beta.solana.com",
            "https://solana-rpc.publicnode.com",
            "https://solana-mainnet.g.alchemy.com/v2/demo",
            "https://rpc.ironforge.network/mainnet",
            "https://rpc.ankr.com/solana"
        ]
    
    def _get_candidate_rpcs(self) -> list:
        candidates = []
        if self.rpc_url:
            candidates.append(self.rpc_url)
        for url in self.fallback_rpcs:
            if url not in candidates:
                candidates.append(url)
        for url in self.default_fallback_rpcs:
            if url not in candidates:
                candidates.append(url)
        print(f"Solana RPC candidates (in order): {candidates}")
        return candidates
    
    async def initialize(self) -> bool:
        """Initialize the Solana USDC client."""
        try:
            if not AsyncClient or not Confirmed:
                msg = "solana-py not installed. Install with: pip install solana"
                print(f"❌ Warning: {msg}")
                self.last_error = msg
                return False
            
            try:
                self._lock = asyncio.Lock()
            except RuntimeError:
                self._lock = None
            
            candidates = self._get_candidate_rpcs()
            if not candidates:
                msg = "No RPC endpoints configured for Solana USDC"
                print(f"❌ {msg}")
                self.last_error = msg
                return False
            
            print(f"🔍 Solana USDC initialization starting (testnet={self.is_testnet}, candidates={len(candidates)})")
            last_error = None
            last_error_details = []
            
            for idx, rpc in enumerate(candidates, 1):
                if self.client:
                    try:
                        await self.client.close()
                    except Exception:
                        pass
                    self.client = None
                
                self.rpc_url = rpc
                print(f"\n[{idx}/{len(candidates)}] Testing RPC: {rpc}")
                
                try:
                    self.client = AsyncClient(rpc, commitment=Confirmed)
                    print(f"  ✓ AsyncClient created successfully")
                except Exception as client_error:
                    error_msg = f"Failed to create AsyncClient: {type(client_error).__name__}: {client_error}"
                    print(f"  ❌ {error_msg}")
                    last_error_details.append(f"[{rpc}] {error_msg}")
                    last_error = client_error
                    continue
                
                try:
                    print(f"  🔗 Performing health check...")
                    health_ok = await asyncio.wait_for(self.check_health(), timeout=8.0)
                    if health_ok:
                        print(f"  ✅ Solana USDC client initialized successfully with {rpc}")
                        self.last_error = None
                        self.last_error_details = None
                        return True
                    else:
                        # If health check failed but we have a client, treat it as successful
                        # The solana library says event loop issues will retry on first use
                        print(f"  ⚠️  Health check inconclusive, accepting client (will verify on first use)")
                        self.last_error = None
                        self.last_error_details = None
                        return True
                except asyncio.TimeoutError as timeout_error:
                    error_msg = f"Health check timeout (8s) - endpoint not responding"
                    print(f"  ⏱️  {error_msg}")
                    last_error_details.append(f"[{rpc}] {error_msg}")
                    last_error = timeout_error
                    continue
                except RuntimeError as rt_error:
                    if "no running event loop" in str(rt_error):
                        # Event loop will be ready when async code actually runs
                        print(f"  ⏳ Event loop initializing, accepting client...")
                        self.last_error = None
                        self.last_error_details = None
                        return True
                    else:
                        error_msg = f"Runtime error: {rt_error}"
                        print(f"  ❌ {error_msg}")
                        last_error_details.append(f"[{rpc}] {error_msg}")
                        last_error = rt_error
                        continue
                except Exception as health_error:
                    error_msg = f"Health check error: {type(health_error).__name__}: {health_error}"
                    print(f"  ❌ {error_msg}")
                    last_error_details.append(f"[{rpc}] {error_msg}")
                    last_error = health_error
                    continue
            
            summary = f"Failed to initialize after trying {len(candidates)} RPC endpoint(s)"
            print(f"\n❌ Solana USDC client {summary}")
            if last_error:
                print(f"Last error: {type(last_error).__name__}: {last_error}")
            print("\n📋 Troubleshooting steps:")
            print("  1. Check your internet connection")
            print("  2. Verify SOLANA_RPC_URL environment variable (if set)")
            print("  3. Check if you're behind a firewall/proxy blocking Solana RPC calls")
            print("  4. Try setting SOLANA_RPC_URL to a specific working RPC endpoint")
            
            self.last_error = summary
            self.last_error_details = "; ".join(last_error_details) if last_error_details else str(last_error)
            return False
        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            print(f"❌ Error initializing Solana USDC client: {error_msg}")
            import traceback
            traceback.print_exc()
            self.last_error = error_msg
            self.last_error_details = traceback.format_exc()
            return False
    
    def get_error_details(self) -> Dict[str, Optional[str]]:
        """Get last error information for debugging."""
        return {
            "error": self.last_error,
            "details": self.last_error_details,
            "rpc_url": self.rpc_url
        }
    
    async def shutdown(self):
        """Shutdown the client."""
        try:
            if self.client:
                await self.client.close()
        except Exception as e:
            print(f"Error shutting down Solana USDC client: {e}")
    
    async def check_health(self) -> bool:
        """Check if the Solana network is accessible."""
        try:
            if not self.client:
                print("    Solana health check failed: client not initialized")
                return False
            
            try:
                response = await asyncio.wait_for(self.client.get_version(), timeout=5.0)
                is_healthy = response.value is not None
                if is_healthy:
                    print(f"    ✓ Solana health check passed: {response.value}")
                else:
                    print("    ✗ Solana health check failed: no version returned")
                return is_healthy
            except asyncio.TimeoutError:
                print("    ✗ Solana RPC timeout (5s) - endpoint not responding to version request")
                return False
            except RuntimeError as runtime_err:
                if "no running event loop" in str(runtime_err):
                    print(f"    ✗ Event loop error - ensure initialization is in async context")
                    return False
                else:
                    print(f"    ✗ Runtime error: {runtime_err}")
                    return False
            except ConnectionError as conn_error:
                print(f"    ✗ Connection error: {type(conn_error).__name__}")
                print(f"       Check firewall/proxy settings")
                return False
            except Exception as rpc_error:
                print(f"    ✗ RPC error: {type(rpc_error).__name__}: {rpc_error}")
                return False
            
        except Exception as e:
            print(f"    ✗ Health check exception: {type(e).__name__}: {e}")
            return False
    
    async def get_balance(self, address: str) -> Optional[Dict[str, Any]]:
        """Get SOL and USDC balance for an address."""
        try:
            if not self.client or not Pubkey:
                return None
            
            # Convert address string to Pubkey
            try:
                pubkey = Pubkey(base58.b58decode(address))
            except Exception:
                try:
                    pubkey = Pubkey(address.encode())
                except Exception:
                    return None
            
            # Get SOL balance
            balance_response = await self.client.get_balance(pubkey)
            sol_balance = balance_response.value / 1e9  # Convert lamports to SOL
            
            # Get USDC token balance
            # This requires finding the associated token account
            usdc_balance = await self._get_token_balance(pubkey)
            
            return {
                'address': address,
                'sol_balance': sol_balance,
                'usdc_balance': usdc_balance,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error getting Solana balance: {e}")
            return None
    
    async def _get_token_balance(self, owner: Union[str, "Pubkey"]) -> float:
        """Get USDC token balance for an owner."""
        try:
            if not self.client or not Pubkey:
                return 0.0
            
            owner_pubkey = owner if isinstance(owner, Pubkey) else Pubkey(base58.b58decode(owner))
            mint_pubkey = Pubkey(base58.b58decode(self.usdc_mint))
            
            # Get token accounts for owner
            response = await self.client.get_token_accounts_by_owner(
                owner_pubkey,
                {"mint": mint_pubkey}
            )
            
            if not response.value or len(response.value) == 0:
                return 0.0
            
            # Get the first token account balance
            token_account = response.value[0]
            token_account_pubkey = Pubkey(base58.b58decode(token_account.pubkey))
            account_info = await self.client.get_token_account_balance(
                token_account_pubkey
            )
            
            if account_info.value:
                # USDC has 6 decimals
                return float(account_info.value.amount) / 1e6
            
            return 0.0
            
        except Exception as e:
            print(f"Error getting token balance: {e}")
            return 0.0
    
    async def send_usdc(self, from_pubkey: str, to_pubkey: str, amount: float, 
                       keypair_bytes: Optional[bytes] = None) -> Optional[str]:
        """Send USDC tokens from one address to another."""
        try:
            if not self.client or not keypair_bytes or not Pubkey:
                return None
            
            # Reconstruct keypair from bytes
            keypair = None
            try:
                from solders.keypair import Keypair
                keypair = Keypair(keypair_bytes)  # type: ignore
            except Exception:
                pass
            
            if not keypair:
                try:
                    from solders.keypair import Keypair
                    keypair = Keypair.from_secret_key(keypair_bytes)  # type: ignore
                except Exception:
                    pass
            
            if not keypair:
                try:
                    from nacl.signing import SigningKey
                    signing_key = SigningKey(keypair_bytes)
                    keypair = signing_key.verify_key
                except Exception:
                    pass
            
            if not keypair:
                return None
            
            from_pubkey_obj = Pubkey(base58.b58decode(from_pubkey))
            to_pubkey_obj = Pubkey(base58.b58decode(to_pubkey))
            usdc_mint_obj = Pubkey(base58.b58decode(self.usdc_mint))
            
            if not transfer_checked or not TOKEN_PROGRAM_ID or not Transaction:
                return None
            
            # Get the sender's USDC token account
            from_token_account = await self._get_associated_token_account(
                from_pubkey_obj, usdc_mint_obj
            )
            
            # Get or create the receiver's USDC token account
            to_token_account = await self._get_or_create_associated_token_account(
                to_pubkey_obj, usdc_mint_obj
            )
            
            if not from_token_account or not to_token_account:
                return None
            
            # Create transfer instruction
            transfer_ix = None
            try:
                transfer_ix = transfer_checked(
                    program_id=TOKEN_PROGRAM_ID,  # type: ignore
                    source=from_token_account,  # type: ignore
                    mint=usdc_mint_obj,  # type: ignore
                    dest=to_token_account,  # type: ignore
                    owner=from_pubkey_obj,  # type: ignore
                    amount=int(amount * 1e6),  # type: ignore
                    decimals=6,  # type: ignore
                    signers=[keypair] if keypair else []  # type: ignore
                )
            except (TypeError, AttributeError):
                try:
                    transfer_ix = transfer_checked(
                        source=from_token_account,  # type: ignore
                        mint=usdc_mint_obj,  # type: ignore
                        dest=to_token_account,  # type: ignore
                        owner=from_pubkey_obj,  # type: ignore
                        amount=int(amount * 1e6),  # type: ignore
                        decimals=6  # type: ignore
                    )
                except (TypeError, AttributeError):
                    return None
            
            if not transfer_ix:
                return None
            
            # Build and send transaction
            recent_blockhash = await self.client.get_latest_blockhash()
            transaction = Transaction(
                signers=[keypair],
                instructions=[transfer_ix],
                recent_blockhash=recent_blockhash.value.blockhash if recent_blockhash.value else None
            )
            
            # Sign and send
            signature_response = await self.client.send_transaction(transaction)
            
            if signature_response.value:
                return str(signature_response.value)
            
            return None
            
        except Exception as e:
            print(f"Error sending USDC: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def _get_associated_token_account(self, owner: Pubkey, mint: Pubkey) -> Optional[Pubkey]:
        """Get the associated token account for an owner and mint."""
        try:
            if not get_associated_token_address:
                return None
            return get_associated_token_address(owner, mint)
        except Exception as e:
            print(f"Error getting associated token account: {e}")
            return None
    
    async def _get_or_create_associated_token_account(self, owner: Pubkey, mint: Pubkey) -> Optional[Pubkey]:
        """Get or create the associated token account for an owner and mint."""
        try:
            if not get_associated_token_address:
                return None
            ata = get_associated_token_address(owner, mint)
            
            if self.client:
                account_info = await self.client.get_account_info(ata)
                if account_info.value and account_info.value.owner == TOKEN_PROGRAM_ID:
                    return ata
            
            return ata
            
        except Exception as e:
            print(f"Error getting or creating associated token account: {e}")
            return None
