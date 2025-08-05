"""
Unified Dogecoin client for Sapphire Exchange.
Consolidates functionality from dogecoin_utils.py with BIP39 compliance.
"""
import asyncio
import aiohttp
import json
import hashlib
import base58
import secrets
import time
from typing import Dict, Optional, Tuple, List, Union, Any
from dataclasses import dataclass
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Import BIP39 and BIP44 libraries
try:
    from mnemonic import Mnemonic
    from bip_utils import Bip44, Bip44Coins, Bip44Changes
    BIP_UTILS_AVAILABLE = True
except ImportError:
    print("Warning: BIP utilities not available. Install with: pip install mnemonic bip-utils")
    BIP_UTILS_AVAILABLE = False


@dataclass
class DogeWallet:
    """Dogecoin wallet data structure."""
    address: str
    private_key_encrypted: str
    mnemonic_hash: str
    derivation_path: str
    network: str
    created_at: str
    balance: float = 0.0


class MockDogeNetwork:
    """Mock Dogecoin network for testing."""
    def __init__(self):
        self.wallets: Dict[str, DogeWallet] = {}
        self.transactions: Dict[str, Dict[str, Any]] = {}
        self.utxos: Dict[str, List[Dict[str, Any]]] = {}
    
    def create_wallet(self, address: str, wallet: DogeWallet):
        """Create mock wallet with initial balance."""
        self.wallets[address] = wallet
        self.wallets[address].balance = 1000.0  # 1000 DOGE initial balance
        # Create initial UTXO
        self.utxos[address] = [{
            'txid': f'mock_utxo_{address[:8]}',
            'vout': 0,
            'amount': 1000.0,
            'confirmations': 100
        }]
    
    def get_balance(self, address: str) -> float:
        """Get wallet balance."""
        return self.wallets.get(address, DogeWallet("", "", "", "", "", "")).balance
    
    def send_transaction(self, from_addr: str, to_addr: str, amount: float) -> str:
        """Process mock transaction."""
        if from_addr in self.wallets and self.wallets[from_addr].balance >= amount:
            # Deduct from sender
            self.wallets[from_addr].balance -= amount
            
            # Add to receiver (create if doesn't exist)
            if to_addr not in self.wallets:
                self.wallets[to_addr] = DogeWallet(to_addr, "", "", "", "", "")
            self.wallets[to_addr].balance += amount
            
            # Generate mock transaction ID
            tx_id = hashlib.sha256(f"{from_addr}{to_addr}{amount}{time.time()}".encode()).hexdigest()
            
            # Store transaction
            self.transactions[tx_id] = {
                'from': from_addr,
                'to': to_addr,
                'amount': amount,
                'timestamp': time.time(),
                'confirmations': 1
            }
            
            return tx_id
        else:
            raise Exception("Insufficient balance")


class DogecoinClient:
    """Unified Dogecoin blockchain client."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Dogecoin client with configuration."""
        self.config = config
        self.network = config.get('network_settings', {}).get('network', 'testnet')
        self.rpc_host = config.get('network_settings', {}).get('rpc_host', '127.0.0.1')
        self.rpc_port = config.get('network_settings', {}).get('rpc_port', 44555)
        self.rpc_user = config.get('network_settings', {}).get('rpc_user', 'dogecoin')
        self.rpc_password = config.get('network_settings', {}).get('rpc_password', 'password')
        self.mock_mode = config.get('mock_mode', False)
        
        # Wallet configuration
        self.derivation_path = config.get('wallet_specs', {}).get('derivation_path', "m/44'/3'/0'/0/0")
        self.mnemonic_standard = config.get('wallet_specs', {}).get('mnemonic_standard', 'BIP39')
        
        # Network parameters
        if self.network == 'mainnet':
            self.network_params = {
                'pubkey_version': b'\x1e',  # 30 in hex
                'script_version': b'\x16',  # 22 in hex
                'wif_version': b'\x9e',     # 158 in hex
                'hrp': 'D'
            }
        else:  # testnet
            self.network_params = {
                'pubkey_version': b'\x71',  # 113 in hex
                'script_version': b'\xc4',  # 196 in hex
                'wif_version': b'\xf1',     # 241 in hex
                'hrp': 'n'
            }
        
        # Mock network for testing
        self.mock_network = MockDogeNetwork() if self.mock_mode else None
        
        # Session for HTTP requests
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Current wallet
        self.current_wallet: Optional[DogeWallet] = None
        
        # Mnemonic generator
        self.mnemonic_generator = Mnemonic("english") if BIP_UTILS_AVAILABLE else None
    
    async def initialize(self) -> bool:
        """Initialize the Dogecoin client."""
        try:
            if not self.mock_mode:
                # Create session with basic auth for RPC
                auth = aiohttp.BasicAuth(self.rpc_user, self.rpc_password)
                self.session = aiohttp.ClientSession(
                    auth=auth,
                    timeout=aiohttp.ClientTimeout(total=30)
                )
                # Test RPC connection
                return await self.check_health()
            else:
                print("Dogecoin client initialized in mock mode")
                return True
        except Exception as e:
            print(f"Error initializing Dogecoin client: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown the Dogecoin client."""
        if self.session:
            await self.session.close()
    
    async def check_health(self) -> bool:
        """Check if Dogecoin RPC is healthy."""
        try:
            if self.mock_mode:
                return True
            
            response = await self._make_rpc_call("getblockchaininfo")
            return response is not None and "chain" in response
        except Exception:
            return False
    
    async def _make_rpc_call(self, method: str, params: List[Any] = None) -> Optional[Dict[str, Any]]:
        """Make RPC call to Dogecoin node."""
        if self.mock_mode:
            return self._handle_mock_rpc(method, params or [])
        
        try:
            if not self.session:
                return None
            
            rpc_url = f"http://{self.rpc_host}:{self.rpc_port}/"
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": method,
                "params": params or []
            }
            
            async with self.session.post(rpc_url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    if "result" in result:
                        return result["result"]
                    elif "error" in result:
                        print(f"RPC error: {result['error']}")
                        return None
                return None
        except Exception as e:
            print(f"Error making RPC call: {e}")
            return None
    
    def _handle_mock_rpc(self, method: str, params: List[Any]) -> Dict[str, Any]:
        """Handle mock RPC calls for testing."""
        if method == "getblockchaininfo":
            return {
                "chain": "test" if self.network == 'testnet' else "main",
                "blocks": 4500000,
                "headers": 4500000,
                "bestblockhash": "mock_block_hash",
                "difficulty": 1.0,
                "mediantime": int(time.time()),
                "verificationprogress": 1.0,
                "chainwork": "mock_chainwork",
                "size_on_disk": 1000000000,
                "pruned": False
            }
        
        elif method == "getbalance":
            if self.current_wallet and self.mock_network:
                return self.mock_network.get_balance(self.current_wallet.address)
            return 0.0
        
        elif method == "getnewaddress":
            # Generate mock address
            return f"mock_doge_address_{secrets.token_hex(8)}"
        
        elif method == "sendtoaddress":
            if len(params) >= 2 and self.current_wallet and self.mock_network:
                to_address = params[0]
                amount = float(params[1])
                return self.mock_network.send_transaction(
                    self.current_wallet.address, to_address, amount
                )
            return None
        
        elif method == "validateaddress":
            if len(params) >= 1:
                address = params[0]
                return {
                    "isvalid": self.validate_address(address),
                    "address": address,
                    "scriptPubKey": "mock_script",
                    "ismine": address == (self.current_wallet.address if self.current_wallet else ""),
                    "iswatchonly": False,
                    "isscript": False
                }
            return {"isvalid": False}
        
        return {}
    
    def generate_mnemonic(self, strength: int = 256) -> Optional[str]:
        """Generate BIP39 mnemonic phrase."""
        if not BIP_UTILS_AVAILABLE or not self.mnemonic_generator:
            print("BIP utilities not available")
            return None
        
        try:
            return self.mnemonic_generator.generate(strength=strength)
        except Exception as e:
            print(f"Error generating mnemonic: {e}")
            return None
    
    def validate_mnemonic(self, mnemonic: str) -> bool:
        """Validate BIP39 mnemonic phrase."""
        if not BIP_UTILS_AVAILABLE or not self.mnemonic_generator:
            return False
        
        try:
            return self.mnemonic_generator.check(mnemonic)
        except Exception:
            return False
    
    def mnemonic_to_wallet(self, mnemonic: str, passphrase: str = "") -> Optional[DogeWallet]:
        """Convert mnemonic to Dogecoin wallet."""
        if not BIP_UTILS_AVAILABLE:
            print("BIP utilities not available")
            return None
        
        try:
            # Generate seed from mnemonic
            seed = self.mnemonic_generator.to_seed(mnemonic, passphrase)
            
            # Create BIP44 wallet for Dogecoin
            bip44_mst_ctx = Bip44.FromSeed(seed, Bip44Coins.DOGECOIN)
            bip44_acc_ctx = bip44_mst_ctx.Purpose().Coin().Account(0)
            bip44_chg_ctx = bip44_acc_ctx.Change(Bip44Changes.CHAIN_EXT)
            bip44_addr_ctx = bip44_chg_ctx.AddressIndex(0)
            
            # Get address and private key
            address = bip44_addr_ctx.PublicKey().ToAddress()
            private_key = bip44_addr_ctx.PrivateKey().Raw().ToHex()
            
            # Create wallet
            wallet = DogeWallet(
                address=address,
                private_key_encrypted=self._encrypt_private_key(private_key, mnemonic),
                mnemonic_hash=hashlib.sha256(mnemonic.encode()).hexdigest(),
                derivation_path=self.derivation_path,
                network=self.network,
                created_at=time.strftime("%Y-%m-%d %H:%M:%S")
            )
            
            return wallet
        except Exception as e:
            print(f"Error converting mnemonic to wallet: {e}")
            return None
    
    def _encrypt_private_key(self, private_key: str, password: str) -> str:
        """Encrypt private key with password."""
        try:
            # Derive key from password
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'sapphire_exchange_salt',
                iterations=100000,
            )
            key = base58.b58encode(kdf.derive(password.encode()))
            
            # Encrypt private key
            fernet = Fernet(key)
            encrypted = fernet.encrypt(private_key.encode())
            return base58.b58encode(encrypted).decode()
        except Exception as e:
            print(f"Error encrypting private key: {e}")
            return ""
    
    def _decrypt_private_key(self, encrypted_key: str, password: str) -> Optional[str]:
        """Decrypt private key with password."""
        try:
            # Derive key from password
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'sapphire_exchange_salt',
                iterations=100000,
            )
            key = base58.b58encode(kdf.derive(password.encode()))
            
            # Decrypt private key
            fernet = Fernet(key)
            encrypted_bytes = base58.b58decode(encrypted_key)
            decrypted = fernet.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            print(f"Error decrypting private key: {e}")
            return None
    
    def validate_address(self, address: str) -> bool:
        """Validate Dogecoin address format."""
        try:
            if not address:
                return False
            
            # Check prefix
            if self.network == 'mainnet':
                if not address.startswith('D'):
                    return False
            else:  # testnet
                if not address.startswith(('n', 'm', '2')):
                    return False
            
            # Basic length check
            if len(address) < 26 or len(address) > 35:
                return False
            
            # Try to decode base58
            try:
                decoded = base58.b58decode(address)
                return len(decoded) == 25  # 20 bytes hash + 4 bytes checksum + 1 byte version
            except Exception:
                return False
        except Exception:
            return False
    
    async def create_wallet(self, mnemonic: Optional[str] = None) -> Optional[DogeWallet]:
        """Create new Dogecoin wallet."""
        try:
            if not mnemonic:
                mnemonic = self.generate_mnemonic()
                if not mnemonic:
                    return None
            
            wallet = self.mnemonic_to_wallet(mnemonic)
            if wallet:
                self.current_wallet = wallet
                
                # Register with mock network if in mock mode
                if self.mock_mode and self.mock_network:
                    self.mock_network.create_wallet(wallet.address, wallet)
                
                return wallet
            return None
        except Exception as e:
            print(f"Error creating wallet: {e}")
            return None
    
    async def load_wallet(self, wallet_data: Dict[str, Any], password: str) -> bool:
        """Load existing wallet from data."""
        try:
            wallet = DogeWallet(**wallet_data)
            
            # Verify we can decrypt the private key
            private_key = self._decrypt_private_key(wallet.private_key_encrypted, password)
            if not private_key:
                return False
            
            self.current_wallet = wallet
            return True
        except Exception as e:
            print(f"Error loading wallet: {e}")
            return False
    
    async def get_balance(self, address: Optional[str] = None) -> Optional[float]:
        """Get wallet balance."""
        try:
            if self.mock_mode and self.mock_network:
                target_address = address or (self.current_wallet.address if self.current_wallet else "")
                return self.mock_network.get_balance(target_address)
            
            balance = await self._make_rpc_call("getbalance")
            return float(balance) if balance is not None else None
        except Exception as e:
            print(f"Error getting balance: {e}")
            return None
    
    async def generate_address(self) -> Optional[str]:
        """Generate new receiving address."""
        try:
            address = await self._make_rpc_call("getnewaddress")
            return address
        except Exception as e:
            print(f"Error generating address: {e}")
            return None
    
    async def send_payment(self, to_address: str, amount: float, comment: str = "") -> Optional[str]:
        """Send Dogecoin payment."""
        try:
            if not self.validate_address(to_address):
                print("Invalid destination address")
                return None
            
            params = [to_address, amount]
            if comment:
                params.append(comment)
            
            tx_id = await self._make_rpc_call("sendtoaddress", params)
            return tx_id
        except Exception as e:
            print(f"Error sending payment: {e}")
            return None
    
    async def get_transaction(self, tx_id: str) -> Optional[Dict[str, Any]]:
        """Get transaction details."""
        try:
            if self.mock_mode and self.mock_network:
                return self.mock_network.transactions.get(tx_id)
            
            tx_info = await self._make_rpc_call("gettransaction", [tx_id])
            return tx_info
        except Exception as e:
            print(f"Error getting transaction: {e}")
            return None
    
    def format_balance(self, amount: float, decimals: int = 8) -> str:
        """Format DOGE amount for display."""
        try:
            return f"{amount:.{decimals}f}"
        except Exception:
            return "0.00000000"