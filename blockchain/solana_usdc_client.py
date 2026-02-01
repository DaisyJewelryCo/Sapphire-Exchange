"""
Solana USDC Client for Sapphire Exchange.
Handles USDC token operations on Solana blockchain.
"""
import asyncio
import base58
from typing import Dict, Optional, List, Any, Tuple, Union, TYPE_CHECKING
from dataclasses import dataclass
from datetime import datetime

if TYPE_CHECKING:
    from solders.pubkey import Pubkey

AsyncClient = None
AsyncToken = None
TOKEN_PROGRAM_ID = None
Pubkey = None

try:
    from solana.rpc.async_api import AsyncClient
    from solana.rpc.commitment import Confirmed
    from solana.transaction import Transaction
    from solana.account import Account
    from solders.pubkey import Pubkey
    from solders.signature import Signature
except ImportError:
    pass

try:
    from spl.token.client import Token, Client as SplClient
    from spl.token.instructions import (
        create_associated_token_account,
        transfer_checked,
        get_associated_token_address
    )
    from spl.token.constants import TOKEN_PROGRAM_ID
except ImportError:
    pass


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
        
        # Network configuration
        self.is_testnet = config.get('testnet', False)
        self.rpc_url = config.get('solana', {}).get('rpc_url', 
            'https://api.devnet.solana.com' if self.is_testnet else 'https://api.mainnet-beta.solana.com'
        )
        
        # USDC mint address
        self.usdc_mint = self.USDC_MINT_DEVNET if self.is_testnet else self.USDC_MINT_MAINNET
        
        # Client
        self.client: Optional[AsyncClient] = None
        self.token_client: Optional[AsyncToken] = None
        
        # Lock for thread-safe operations
        self._lock: Optional[asyncio.Lock] = None
        
        # Current wallet
        self.current_wallet: Optional[SolanaWallet] = None
        self.keypair: Optional[Account] = None
    
    async def initialize(self) -> bool:
        """Initialize the Solana USDC client."""
        try:
            if AsyncClient is None:
                print("Warning: solana-py not installed. Install with: pip install solana")
                return False
            
            # Try to create the lock
            try:
                self._lock = asyncio.Lock()
            except RuntimeError:
                self._lock = None
            
            # Create async client
            self.client = AsyncClient(self.rpc_url, commitment=Confirmed)
            
            print(f"Solana USDC client initialized (testnet={self.is_testnet})")
            return True
            
        except Exception as e:
            print(f"Error initializing Solana USDC client: {e}")
            import traceback
            traceback.print_exc()
            return False
    
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
                return False
            
            # Try to get cluster version
            response = await self.client.get_version()
            return response.value is not None
            
        except Exception as e:
            print(f"Solana health check failed: {e}")
            return False
    
    async def get_balance(self, address: str) -> Optional[Dict[str, Any]]:
        """Get SOL and USDC balance for an address."""
        try:
            if not self.client:
                return None
            
            # Convert address string to Pubkey
            try:
                pubkey = Pubkey(address)
            except:
                # Try base58 decode
                pubkey = Pubkey(base58.b58decode(address))
            
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
            if not self.client:
                return 0.0
            
            # Get token accounts for owner
            response = await self.client.get_token_accounts_by_owner(
                owner,
                {"mint": Pubkey(self.usdc_mint)}
            )
            
            if not response.value or len(response.value) == 0:
                return 0.0
            
            # Get the first token account balance
            token_account = response.value[0]
            account_info = await self.client.get_token_account_balance(
                Pubkey(token_account.pubkey)
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
            if not self.client or not keypair_bytes:
                return None
            
            # Reconstruct keypair from bytes
            from solders.keypair import Keypair
            keypair = Keypair.from_secret_key(keypair_bytes)
            
            from_pubkey_obj = Pubkey(from_pubkey)
            to_pubkey_obj = Pubkey(to_pubkey)
            usdc_mint_obj = Pubkey(self.usdc_mint)
            
            # Get or create associated token accounts
            from spl.token.instructions import create_associated_token_account
            
            # Get the sender's USDC token account
            from_token_account = await self._get_associated_token_account(
                from_pubkey_obj, usdc_mint_obj
            )
            
            # Get or create the receiver's USDC token account
            to_token_account = await self._get_or_create_associated_token_account(
                to_pubkey_obj, usdc_mint_obj, keypair
            )
            
            if not from_token_account or not to_token_account:
                return None
            
            # Create transfer instruction
            from spl.token.instructions import transfer_checked
            
            transfer_ix = transfer_checked(
                program_id=TOKEN_PROGRAM_ID,
                source=from_token_account,
                mint=usdc_mint_obj,
                dest=to_token_account,
                owner=from_pubkey_obj,
                amount=int(amount * 1e6),  # USDC has 6 decimals
                decimals=6,
                signers=[keypair] if keypair else []
            )
            
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
            from spl.token.instructions import get_associated_token_address
            return get_associated_token_address(owner, mint)
        except Exception as e:
            print(f"Error getting associated token account: {e}")
            return None
    
    async def _get_or_create_associated_token_account(self, owner: Pubkey, mint: Pubkey, 
                                                      payer_keypair) -> Optional[Pubkey]:
        """Get or create the associated token account for an owner and mint."""
        try:
            from spl.token.instructions import get_associated_token_address
            ata = get_associated_token_address(owner, mint)
            
            # Check if account exists
            if self.client:
                account_info = await self.client.get_account_info(ata)
                if account_info.value and account_info.value.owner == TOKEN_PROGRAM_ID:
                    return ata
            
            # Create associated token account if it doesn't exist
            # This would require additional transaction building logic
            # For now, return the address
            return ata
            
        except Exception as e:
            print(f"Error getting or creating associated token account: {e}")
            return None
