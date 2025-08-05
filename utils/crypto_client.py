"""
Simplified cryptocurrency client for Sapphire Exchange.
Provides a unified interface to blockchain operations.
"""
import asyncio
from typing import Dict, Any, Optional, List

from blockchain.dogecoin_client import DogecoinClient
from blockchain.nano_client import NanoClient
from blockchain.arweave_client import ArweaveClient
from config.blockchain_config import blockchain_config

class CryptoClient:
    """
    Simplified client for handling cryptocurrency operations in Sapphire Exchange.
    Provides a unified interface to the blockchain clients.
    """
    
    def __init__(self, dogecoin_client: Optional[DogecoinClient] = None, 
                nano_client: Optional[NanoClient] = None,
                arweave_client: Optional[ArweaveClient] = None):
        """Initialize the crypto client.
        
        Args:
            dogecoin_client: Optional Dogecoin client instance
            nano_client: Optional Nano client instance
            arweave_client: Optional Arweave client instance
        """
        # Initialize blockchain clients
        self.dogecoin_client = dogecoin_client or DogecoinClient(blockchain_config.get_dogecoin_config())
        self.nano_client = nano_client or NanoClient(blockchain_config.get_nano_config())
        self.arweave_client = arweave_client or ArweaveClient(blockchain_config.get_arweave_config())
    
    async def initialize(self) -> bool:
        """Initialize the crypto client."""
        try:
            # Initialize all blockchain clients
            await self.dogecoin_client.initialize()
            await self.nano_client.initialize()
            await self.arweave_client.initialize()
            return True
        except Exception as e:
            print(f"Failed to initialize crypto client: {e}")
            return False
    
    async def get_balances(self) -> Dict[str, float]:
        """Get balances for all supported currencies."""
        try:
            balances = {}
            balances['dogecoin'] = await self.dogecoin_client.get_balance()
            balances['nano'] = await self.nano_client.get_balance()
            return balances
        except Exception as e:
            print(f"Error getting balances: {e}")
            return {}
    
    async def send_transaction(self, currency: str, to_address: str, amount: float) -> Optional[str]:
        """Send a transaction in the specified currency."""
        try:
            if currency.lower() == 'dogecoin':
                return await self.dogecoin_client.send_transaction(to_address, amount)
            elif currency.lower() == 'nano':
                return await self.nano_client.send_transaction(to_address, amount)
            else:
                raise ValueError(f"Unsupported currency: {currency}")
        except Exception as e:
            print(f"Error sending {currency} transaction: {e}")
            return None
