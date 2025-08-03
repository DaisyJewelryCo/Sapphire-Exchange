"""
Dogecoin integration for Sapphire Exchange.
Handles Dogecoin as the main currency with wallet management and transaction capabilities.
"""
import os
import json
import hashlib
import base58
import ecdsa
import requests
from typing import Dict, Optional, Tuple, List, Union
from dataclasses import dataclass, asdict

# Dogecoin network parameters
DOGECOIN_MAINNET = {
    'pubkey_version': b'\x1e',  # 30 in hex
    'script_version': b'\x16',  # 22 in hex
    'wif_version': b'\x9e',     # 158 in hex
    'hrp': 'D',
    'rpc_port': 22555
}

DOGECOIN_TESTNET = {
    'pubkey_version': b'\x71',  # 113 in hex
    'script_version': b'\xc4',  # 196 in hex
    'wif_version': b'\xf1',     # 241 in hex
    'hrp': 'n',
    'rpc_port': 44555
}

class DogecoinWallet:
    """A wallet for Dogecoin cryptocurrency."""
    
    def __init__(self, private_key: bytes = None, network: str = 'testnet'):
        """Initialize a Dogecoin wallet.
        
        Args:
            private_key: Private key as bytes (None generates a new one)
            network: 'mainnet' or 'testnet'
        """
        self.network = DOGECOIN_TESTNET if network == 'testnet' else DOGECOIN_MAINNET
        
        if private_key is None:
            # Generate a new private key
            self.private_key = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
        elif isinstance(private_key, str):
            # Import from WIF format
            self.private_key = self.wif_to_private_key(private_key)
        else:
            self.private_key = private_key if isinstance(private_key, ecdsa.SigningKey) else None
        
        # Generate public key and address
        if self.private_key:
            self.public_key = self.private_key.get_verifying_key()
            self.address = self.get_address()
        else:
            raise ValueError("Invalid private key provided")
    
    @classmethod
    def from_seed(cls, seed_phrase: str, network: str = 'testnet') -> 'DogecoinWallet':
        """Create a wallet from a seed phrase.
        
        Args:
            seed_phrase: A string used to generate the private key
            network: 'mainnet' or 'testnet'
            
        Returns:
            DogecoinWallet: A new wallet instance
        """
        # Use PBKDF2 to generate a deterministic private key from the seed
        seed = hashlib.pbkdf2_hmac('sha256', seed_phrase.encode('utf-8'), b'dogecoin', 2048)
        return cls(seed, network)
    
    def get_address(self) -> str:
        """Get the Dogecoin address for this wallet."""
        # Get the public key in compressed format
        public_key = self.public_key.to_string('compressed')
        
        # Perform SHA-256 hashing on the public key
        sha256 = hashlib.sha256(public_key).digest()
        
        # Perform RIPEMD-160 hashing on the result of SHA-256
        ripemd160 = hashlib.new('ripemd160')
        ripemd160.update(sha256)
        hash160 = ripemd160.digest()
        
        # Add version byte
        version_hash = self.network['pubkey_version'] + hash160
        
        # Perform double SHA-256 hash on the extended RIPEMD-160 result
        checksum = hashlib.sha256(hashlib.sha256(version_hash).digest()).digest()[:4]
        
        # Append checksum to version+RIPEMD-160 hash
        binary_address = version_hash + checksum
        
        # Convert to base58
        return base58.b58encode(binary_address).decode('utf-8')
    
    def get_wif(self) -> str:
        """Get the private key in WIF format."""
        # Add version byte and compression flag
        private_key = self.network['wif_version'] + self.private_key.to_string() + b'\x01'
        
        # Double SHA-256 hash
        checksum = hashlib.sha256(hashlib.sha256(private_key).digest()).digest()[:4]
        
        # Append checksum and encode to base58
        return base58.b58encode(private_key + checksum).decode('utf-8')
    
    @staticmethod
    def wif_to_private_key(wif: str) -> ecdsa.SigningKey:
        """Convert a WIF private key to an ECDSA key."""
        # Decode the WIF
        decoded = base58.b58decode(wif)
        
        # Remove version byte and checksum (last 4 bytes)
        private_key = decoded[1:-4]
        
        # If the WIF is compressed, remove the compression flag
        if len(private_key) > 32:
            private_key = private_key[:-1]
        
        return ecdsa.SigningKey.from_string(private_key, curve=ecdsa.SECP256k1)
    
    def sign_message(self, message: str) -> str:
        """Sign a message with the wallet's private key."""
        message_hash = hashlib.sha256(message.encode('utf-8')).digest()
        signature = self.private_key.sign_digest(
            message_hash,
            sigencode=ecdsa.util.sigencode_der
        )
        return signature.hex()
    
    def verify_message(self, message: str, signature: str) -> bool:
        """Verify a signed message."""
        try:
            message_hash = hashlib.sha256(message.encode('utf-8')).digest()
            signature_bytes = bytes.fromhex(signature)
            return self.public_key.verify_digest(
                signature_bytes,
                message_hash,
                sigdecode=ecdsa.util.sigdecode_der
            )
        except:
            return False


class DogecoinRPC:
    """Client for interacting with the Dogecoin RPC API."""
    
    def __init__(self, 
                rpc_user: str = None, 
                rpc_password: str = None, 
                rpc_host: str = '127.0.0.1', 
                rpc_port: int = None,
                network: str = 'testnet'):
        """Initialize the Dogecoin RPC client.
        
        Args:
            rpc_user: RPC username
            rpc_password: RPC password
            rpc_host: RPC host (default: 127.0.0.1)
            rpc_port: RPC port (default: 44555 for testnet, 22555 for mainnet)
            network: 'mainnet' or 'testnet'
        """
        self.rpc_user = rpc_user or os.getenv('DOGECOIN_RPC_USER')
        self.rpc_password = rpc_password or os.getenv('DOGECOIN_RPC_PASSWORD')
        self.rpc_host = rpc_host
        
        if rpc_port is None:
            self.rpc_port = DOGECOIN_TESTNET['rpc_port'] if network == 'testnet' else DOGECOIN_MAINNET['rpc_port']
        else:
            self.rpc_port = rpc_port
        
        self.rpc_url = f"http://{self.rpc_host}:{self.rpc_port}"
        self.session = requests.Session()
        self.session.auth = (self.rpc_user, self.rpc_password)
        self.session.headers.update({'content-type': 'application/json'})
    
    async def _rpc_request(self, method: str, params: list = None) -> dict:
        """Make an RPC request to the Dogecoin node."""
        payload = {
            'method': method,
            'params': params or [],
            'jsonrpc': '2.0',
            'id': 'sapphire_exchange'
        }
        
        try:
            response = self.session.post(self.rpc_url, data=json.dumps(payload), timeout=30)
            response.raise_for_status()
            result = response.json()
            
            if 'error' in result and result['error'] is not None:
                raise Exception(f"RPC error: {result['error']}")
                
            return result.get('result')
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"RPC connection error: {e}")
    
    async def get_balance(self, account: str = "", min_confirmations: int = 1) -> float:
        """Get the balance of the wallet or a specific account."""
        return await self._rpc_request('getbalance', [account, min_confirmations])
    
    async def get_new_address(self, account: str = "", address_type: str = "legacy") -> str:
        """Generate a new receiving address."""
        return await self._rpc_request('getnewaddress', [account, address_type])
    
    async def send_to_address(
        self, 
        address: str, 
        amount: float, 
        comment: str = "", 
        comment_to: str = "", 
        subtract_fee: bool = False
    ) -> str:
        """Send DOGE to a Dogecoin address."""
        return await self._rpc_request('sendtoaddress', [
            address, 
            amount, 
            comment, 
            comment_to, 
            subtract_fee
        ])
    
    async def get_transaction(self, txid: str) -> dict:
        """Get detailed information about a transaction."""
        return await self._rpc_request('gettransaction', [txid])
    
    async def list_transactions(
        self, 
        account: str = "*", 
        count: int = 10, 
        skip: int = 0, 
        include_watchonly: bool = True
    ) -> list:
        """List recent transactions."""
        return await self._rpc_request('listtransactions', [
            account, 
            count, 
            skip, 
            include_watchonly
        ])
    
    async def get_block_count(self) -> int:
        """Get the current block count."""
        return await self._rpc_request('getblockcount')
    
    async def get_block_hash(self, height: int) -> str:
        """Get the hash of a block at a specific height."""
        return await self._rpc_request('getblockhash', [height])
    
    async def get_block(self, block_hash: str, verbosity: int = 1) -> Union[str, dict]:
        """Get a block by hash."""
        return await self._rpc_request('getblock', [block_hash, verbosity])
    
    async def validate_address(self, address: str) -> dict:
        """Validate a Dogecoin address."""
        return await self._rpc_request('validateaddress', [address])
    
    async def get_wallet_info(self) -> dict:
        """Get wallet information."""
        return await self._rpc_request('getwalletinfo')
    
    async def backup_wallet(self, destination: str) -> None:
        """Backup the wallet to a file."""
        return await self._rpc_request('backupwallet', [destination])
