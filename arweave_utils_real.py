"""
Real Arweave client implementation for interacting with the Arweave network.
This module provides functionality to store and retrieve data from the Arweave blockchain.
"""
import os
import json
import asyncio
from typing import Dict, Any, Optional, Union, List
from dataclasses import asdict
import arweave
from arweave.arweave_lib import Transaction, Wallet
from arweave.transaction_uploader import get_uploader

class ArweaveClient:
    """Client for interacting with the Arweave network."""
    
    def __init__(self, wallet_path: str = None, node_url: str = "https://arweave.net"):
        """Initialize the Arweave client.
        
        Args:
            wallet_path: Path to the Arweave wallet file
            node_url: URL of the Arweave node to connect to
        """
        self.node_url = node_url
        self.wallet = None
        self.client = arweave.Node(node_url=node_url)
        
        if wallet_path and os.path.exists(wallet_path):
            self.load_wallet(wallet_path)
    
    def load_wallet(self, wallet_path: str) -> None:
        """Load an Arweave wallet from a file.
        
        Args:
            wallet_path: Path to the wallet file
        """
        with open(wallet_path, 'r', encoding='utf-8') as f:
            self.wallet = Wallet(json.load(f))
    
    def create_wallet(self, wallet_path: str) -> Dict[str, Any]:
        """Create a new Arweave wallet and save it to a file.
        
        Args:
            wallet_path: Path to save the wallet file
            
        Returns:
            Dict containing wallet information
        """
        wallet = Wallet()
        wallet_info = {
            'kty': 'RSA',
            'n': wallet.n,
            'e': wallet.e,
            'd': wallet.d,
            'p': wallet.p,
            'q': wallet.q,
            'dp': wallet.dp,
            'dq': wallet.dq,
            'qi': wallet.qi
        }
        
        # Save wallet to file
        with open(wallet_path, 'w', encoding='utf-8') as f:
            json.dump(wallet_info, f)
            
        self.wallet = wallet
        return wallet_info
    
    async def store_data(
        self,
        data: Union[Dict, str, bytes],
        wallet: Optional[Wallet] = None,
        content_type: str = "application/json"
    ) -> str:
        """Store data on Arweave.
        
        Args:
            data: Data to store (dict, str, or bytes)
            wallet: Optional wallet to use for the transaction
            content_type: MIME type of the data
            
        Returns:
            Transaction ID of the stored data
            
        Raises:
            ValueError: If no wallet is provided and none is loaded
        """
        wallet = wallet or self.wallet
        if not wallet:
            raise ValueError("No wallet provided and no wallet loaded")
        
        # Convert data to bytes if it's a dict or string
        if isinstance(data, dict):
            data = json.dumps(data).encode('utf-8')
        elif isinstance(data, str):
            data = data.encode('utf-8')
        
        # Create and sign the transaction
        tx = Transaction(
            wallet=wallet,
            data=data,
            content_type=content_type
        )
        tx.sign()
        
        # Upload the transaction
        uploader = get_uploader(tx, data)
        while not uploader.is_complete:
            await asyncio.sleep(1)
            uploader.upload_chunk()
        
        return tx.id
    
    async def get_data(self, tx_id: str) -> Optional[Dict]:
        """Retrieve data from Arweave by transaction ID.
        
        Args:
            tx_id: Transaction ID to retrieve
            
        Returns:
            Deserialized data if successful, None otherwise
        """
        try:
            # Get transaction data
            tx_data = self.client.transaction(tx_id).data
            
            # Try to decode as JSON, return raw bytes if that fails
            try:
                return json.loads(tx_data)
            except json.JSONDecodeError:
                return tx_data
        except Exception as e:
            print(f"Error retrieving data from Arweave: {e}")
            return None
    
    async def get_balance(self, address: Optional[str] = None) -> int:
        """Get the balance of an Arweave address.
        
        Args:
            address: Address to check balance for (defaults to wallet address)
            
        Returns:
            Balance in winston (smallest unit of AR)
        """
        if not address and not self.wallet:
            raise ValueError("No address provided and no wallet loaded")
            
        address = address or self.wallet.address
        return int(self.client.wallets.get_balance(address))
    
    async def transfer(
        self,
        target: str,
        amount: int,
        wallet: Optional[Wallet] = None
    ) -> str:
        """Transfer AR to another address.
        
        Args:
            target: Target address
            amount: Amount to transfer in winston (1 AR = 10^12 winston)
            wallet: Optional wallet to use for the transaction
            
        Returns:
            Transaction ID
        """
        wallet = wallet or self.wallet
        if not wallet:
            raise ValueError("No wallet provided and no wallet loaded")
            
        tx = self.client.create_transaction(
            target=target,
            amount=amount,
            wallet=wallet
        )
        tx.sign()
        response = self.client.transactions.post_tx(tx)
        return tx.id if response.status_code == 200 else None
