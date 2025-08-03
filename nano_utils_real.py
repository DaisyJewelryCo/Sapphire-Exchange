"""
Real Nano client implementation for interacting with the Nano network.
This module provides functionality to create wallets, send and receive Nano,
and interact with the Nano network using the official RPC protocol.
"""
import os
import json
import base58
import hashlib
import asyncio
import aiohttp
from typing import Dict, Any, Optional, Tuple, Union
from dataclasses import asdict
import ed25519_blake2b

class NanoWallet:
    """A wallet for Nano cryptocurrency with real network interaction."""
    
    def __init__(self, seed: bytes = None, node_url: str = "https://mynano.ninja/api"):
        """Initialize a Nano wallet with an optional seed.
        
        Args:
            seed: Seed for the wallet (None generates a new one)
            node_url: URL of the Nano node RPC endpoint
        """
        self.node_url = node_url
        self.session = aiohttp.ClientSession()
        
        if seed is None:
            # Generate a random seed
            seed = os.urandom(32)  # 32 bytes for ed25519
        elif isinstance(seed, str):
            # If seed is a string, encode it to bytes
            seed = hashlib.sha256(seed.encode('utf-8')).digest()
        elif not isinstance(seed, bytes):
            raise ValueError("Seed must be either None, a string, or bytes")
            
        # Ensure the seed is 32 bytes
        if len(seed) != 32:
            seed = hashlib.sha256(seed).digest()[:32]
        
        # Create the signing key from the seed
        self.private_key = ed25519_blake2b.SigningKey(seed)
        self.public_key = self.private_key.get_verifying_key()
        self.address = self._public_key_to_address(self.public_key)
    
    @staticmethod
    def _public_key_to_address(public_key) -> str:
        """Convert a public key to a Nano address."""
        # Nano address format: xrb_ + account + checksum
        account = public_key.to_bytes()
        account_hash = hashlib.blake2b(account, digest_size=32).digest()
        account_encoded = base58.b58encode_check(account_hash).decode('ascii')
        return f"nano_{account_encoded}"
    
    @classmethod
    def from_seed(cls, seed_phrase: str, node_url: str = "https://mynano.ninja/api") -> 'NanoWallet':
        """Create a wallet from a seed phrase.
        
        Args:
            seed_phrase: The seed phrase as a string
            node_url: URL of the Nano node RPC endpoint
            
        Returns:
            NanoWallet: A new wallet instance
        """
        if not seed_phrase or not isinstance(seed_phrase, str):
            raise ValueError("Seed phrase must be a non-empty string")
            
        # Convert seed phrase to bytes and ensure it's 32 bytes
        seed = hashlib.sha256(seed_phrase.encode('utf-8')).digest()
        if len(seed) < 32:
            seed = hashlib.sha256(seed).digest()
        seed = seed[:32]
        
        return cls(seed=seed, node_url=node_url)
    
    async def close(self):
        """Close the HTTP session."""
        await self.session.close()
    
    async def _rpc_request(self, action: str, **params) -> Dict[str, Any]:
        """Make an RPC request to the Nano node.
        
        Args:
            action: The RPC action to perform
            **params: Additional parameters for the RPC call
            
        Returns:
            dict: The JSON response from the node
        """
        payload = {
            "action": action,
            **params
        }
        
        try:
            async with self.session.post(self.node_url, json=payload) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            print(f"RPC request failed: {e}")
            raise
    
    async def get_balance(self, account: str = None) -> int:
        """Get the balance of an account in raw.
        
        Args:
            account: Account address (defaults to wallet address)
            
        Returns:
            int: Balance in raw (1 NANO = 10^30 raw)
        """
        account = account or self.address
        response = await self._rpc_request("account_balance", account=account)
        return int(response.get("balance", 0))
    
    async def send(
        self,
        destination: str,
        amount_raw: int,
        source: str = None
    ) -> Optional[str]:
        """Send Nano to another address.
        
        Args:
            destination: Destination address
            amount_raw: Amount to send in raw (1 NANO = 10^30 raw)
            source: Source account (defaults to wallet address)
            
        Returns:
            str: Block hash if successful, None otherwise
        """
        source = source or self.address
        
        # Get account info to get the frontier
        account_info = await self._rpc_request("account_info", 
                                             account=source, 
                                             representative=True,
                                             pending=True)
        
        if 'error' in account_info:
            raise ValueError(f"Account error: {account_info.get('error', 'Unknown error')}")
        
        # Create and sign the block
        block = {
            "type": "state",
            "account": source,
            "previous": account_info.get('frontier'),
            "representative": account_info.get('representative'),
            "balance": str(int(account_info.get('balance', 0)) - amount_raw),
            "link": destination,
            "link_as_account": destination
        }
        
        # Sign the block
        block_hash = await self._rpc_request("block_hash", "state", block)
        signature = self.private_key.sign(block_hash['hash'].encode())
        block['signature'] = signature.hex()
        
        # Publish the block
        response = await self._rpc_request("process", "state", block)
        return response.get('hash')
    
    async def get_pending_blocks(self, account: str = None, count: int = 10) -> list:
        """Get pending blocks for an account.
        
        Args:
            account: Account address (defaults to wallet address)
            count: Maximum number of blocks to return
            
        Returns:
            list: List of pending blocks
        """
        account = account or self.address
        response = await self._rpc_request("pending", 
                                         account=account, 
                                         count=str(count),
                                         source="true")
        return response.get('blocks', [])
    
    async def receive_pending(self, block_hash: str) -> Optional[str]:
        """Receive a pending block.
        
        Args:
            block_hash: Hash of the pending block to receive
            
        Returns:
            str: Block hash if successful, None otherwise
        """
        response = await self._rpc_request("receive", 
                                         action="receive", 
                                         hash=block_hash)
        return response.get('block')


class NanoRPC:
    """Client for interacting with the Nano network RPC."""
    
    def __init__(self, node_url: str = "https://mynano.ninja/api"):
        """Initialize the Nano RPC client.
        
        Args:
            node_url: URL of the Nano node RPC endpoint
        """
        self.node_url = node_url
        self.session = aiohttp.ClientSession()
    
    async def close(self):
        """Close the HTTP session."""
        await self.session.close()
    
    async def _rpc_request(self, action: str, **params) -> Dict[str, Any]:
        """Make an RPC request to the Nano node.
        
        Args:
            action: The RPC action to perform
            **params: Additional parameters for the RPC call
            
        Returns:
            dict: The JSON response from the node
        """
        payload = {
            "action": action,
            **params
        }
        
        try:
            async with self.session.post(self.node_url, json=payload) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            print(f"RPC request failed: {e}")
            raise
    
    async def get_account_balance(self, account: str) -> Dict[str, int]:
        """Get the balance of a Nano account.
        
        Args:
            account: The Nano account address
            
        Returns:
            dict: The account balance information
        """
        return await self._rpc_request("account_balance", account=account)
    
    async def get_account_info(self, account: str, representative: bool = True) -> Dict[str, Any]:
        """Get information about a Nano account.
        
        Args:
            account: The Nano account address
            representative: Whether to include representative information
            
        Returns:
            dict: The account information
        """
        return await self._rpc_request(
            "account_info", 
            account=account, 
            representative=str(representative).lower(),
            pending="true"
        )
    
    async def send_payment(
        self, 
        wallet_id: str, 
        source: str, 
        destination: str, 
        amount: Union[int, str]
    ) -> Dict[str, Any]:
        """Send a payment from one account to another.
        
        Args:
            wallet_id: The wallet ID containing the source account
            source: The source account address
            destination: The destination account address
            amount: The amount to send in raw
            
        Returns:
            dict: The transaction result
        """
        # First, check if we need to receive any pending blocks
        pending = await self._rpc_request("pending", account=source, count="1")
        if pending.get('blocks'):
            await self._rpc_request("receive", wallet=wallet_id, account=source, block=pending['blocks'][0])
        
        # Now send the payment
        return await self._rpc_request(
            "send",
            wallet=wallet_id,
            source=source,
            destination=destination,
            amount=str(amount)
        )
    
    async def get_block_count(self) -> int:
        """Get the current block count.
        
        Returns:
            int: The current block count
        """
        response = await self._rpc_request("block_count")
        return int(response.get('count', 0))
