"""
NANO Wallet Helper Module.
Provides enhanced support for NANO wallet operations including address validation,
balance queries, and transaction handling.
"""
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import re
import aiohttp
import asyncio


@dataclass
class NanoWalletInfo:
    """NANO wallet information."""
    address: str
    public_key: str
    private_key: bytes
    balance: str = "0"
    pending: str = "0"
    block_count: int = 0


class NanoWalletHelper:
    """Helper class for NANO wallet operations."""
    
    NANO_PREFIX = "nano_"
    NANO_ADDRESS_PATTERN = r"^nano_[13456789abcdefghijkmnopqrstuwxyz]{60}$"
    
    def __init__(self, node_url: str = "https://mynano.ninja/api"):
        self.node_url = node_url
        self.session = None
    
    async def initialize(self):
        """Initialize HTTP session."""
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def close(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
    
    @staticmethod
    def is_valid_nano_address(address: str) -> bool:
        """
        Validate NANO address format.
        
        Args:
            address: Address to validate
        
        Returns:
            True if valid NANO address
        """
        return bool(re.match(NanoWalletHelper.NANO_ADDRESS_PATTERN, address))
    
    async def get_account_info(self, address: str) -> Dict[str, Any]:
        """
        Get account information from NANO node.
        
        Args:
            address: NANO address
        
        Returns:
            Account information dict
        """
        if not self.is_valid_nano_address(address):
            raise ValueError(f"Invalid NANO address: {address}")
        
        await self.initialize()
        
        try:
            payload = {
                "action": "account_info",
                "account": address,
                "representative": True,
                "pending": True
            }
            
            async with self.session.post(self.node_url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        'address': address,
                        'balance': data.get('balance', '0'),
                        'pending': data.get('pending', '0'),
                        'representative': data.get('representative', ''),
                        'block_count': int(data.get('block_count', 0)),
                        'frontier': data.get('frontier', ''),
                    }
                else:
                    raise Exception(f"Node error: {response.status}")
        
        except Exception as e:
            raise Exception(f"Failed to get account info: {str(e)}")
    
    async def get_balance(self, address: str) -> tuple:
        """
        Get balance for NANO address.
        
        Args:
            address: NANO address
        
        Returns:
            Tuple of (balance, pending) in raw units
        """
        try:
            info = await self.get_account_info(address)
            return (info['balance'], info['pending'])
        
        except Exception as e:
            raise Exception(f"Failed to get balance: {str(e)}")
    
    async def get_pending_transactions(self, address: str, count: int = 10) -> List[Dict[str, Any]]:
        """
        Get pending transactions for address.
        
        Args:
            address: NANO address
            count: Number of transactions to retrieve
        
        Returns:
            List of pending transactions
        """
        if not self.is_valid_nano_address(address):
            raise ValueError(f"Invalid NANO address: {address}")
        
        await self.initialize()
        
        try:
            payload = {
                "action": "pending",
                "account": address,
                "count": count,
                "source": True
            }
            
            async with self.session.post(self.node_url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    pending_list = []
                    for tx_hash, tx_info in data.get('blocks', {}).items():
                        pending_list.append({
                            'hash': tx_hash,
                            'amount': tx_info.get('amount', '0'),
                            'source': tx_info.get('source', ''),
                        })
                    
                    return pending_list
                else:
                    raise Exception(f"Node error: {response.status}")
        
        except Exception as e:
            raise Exception(f"Failed to get pending transactions: {str(e)}")
    
    async def validate_representative(self, representative: str) -> bool:
        """
        Check if representative is online and valid.
        
        Args:
            representative: Representative address
        
        Returns:
            True if representative is valid and online
        """
        if not self.is_valid_nano_address(representative):
            return False
        
        await self.initialize()
        
        try:
            payload = {
                "action": "account_info",
                "account": representative
            }
            
            async with self.session.post(self.node_url, json=payload) as response:
                return response.status == 200
        
        except Exception:
            return False
    
    @staticmethod
    def convert_raw_to_nano(raw: str) -> str:
        """
        Convert raw NANO units to NANO.
        
        Args:
            raw: Amount in raw units
        
        Returns:
            Amount in NANO
        """
        try:
            raw_int = int(raw)
            nano_amount = raw_int / (10 ** 30)
            return f"{nano_amount:.30f}".rstrip('0').rstrip('.')
        
        except (ValueError, TypeError):
            return "0"
    
    @staticmethod
    def convert_nano_to_raw(nano: str) -> str:
        """
        Convert NANO to raw units.
        
        Args:
            nano: Amount in NANO
        
        Returns:
            Amount in raw units
        """
        try:
            nano_float = float(nano)
            raw_amount = int(nano_float * (10 ** 30))
            return str(raw_amount)
        
        except (ValueError, TypeError):
            return "0"
    
    async def check_node_health(self) -> Dict[str, Any]:
        """
        Check NANO node health.
        
        Returns:
            Node health information
        """
        await self.initialize()
        
        try:
            payload = {"action": "active_difficulty"}
            
            async with self.session.post(self.node_url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        'node_status': 'healthy',
                        'difficulty': data.get('difficulty', ''),
                        'network_current': data.get('network_current', ''),
                        'network_receive': data.get('network_receive', ''),
                        'multiplier': data.get('multiplier', '1'),
                    }
                else:
                    return {'node_status': 'unhealthy', 'error': 'Node not responding'}
        
        except Exception as e:
            return {'node_status': 'error', 'error': str(e)}


class NanoTransactionBuilder:
    """Builder for NANO transactions."""
    
    def __init__(self, helper: NanoWalletHelper):
        self.helper = helper
        self.transaction = {
            'type': 'state_block',
            'subtype': 'send',
            'account': '',
            'previous': '',
            'representative': '',
            'balance': '',
            'link': '',
            'signature': '',
            'work': '',
        }
    
    def set_account(self, account: str) -> 'NanoTransactionBuilder':
        """Set source account."""
        if not self.helper.is_valid_nano_address(account):
            raise ValueError(f"Invalid NANO address: {account}")
        self.transaction['account'] = account
        return self
    
    def set_recipient(self, recipient: str, amount: str) -> 'NanoTransactionBuilder':
        """Set transaction recipient and amount."""
        if not self.helper.is_valid_nano_address(recipient):
            raise ValueError(f"Invalid NANO address: {recipient}")
        
        amount_raw = self.helper.convert_nano_to_raw(amount)
        self.transaction['link'] = recipient
        self.transaction['subtype'] = 'send'
        
        return self
    
    def set_representative(self, representative: str) -> 'NanoTransactionBuilder':
        """Set representative."""
        if not self.helper.is_valid_nano_address(representative):
            raise ValueError(f"Invalid NANO address: {representative}")
        self.transaction['representative'] = representative
        return self
    
    def build(self) -> Dict[str, Any]:
        """Build transaction."""
        required_fields = ['account', 'link', 'representative']
        
        for field in required_fields:
            if not self.transaction.get(field):
                raise ValueError(f"Missing required field: {field}")
        
        return self.transaction


class NanoWalletManager:
    """Manager for NANO wallet operations."""
    
    def __init__(self, node_url: str = "https://mynano.ninja/api"):
        self.helper = NanoWalletHelper(node_url)
        self.wallets: Dict[str, NanoWalletInfo] = {}
    
    async def add_wallet(self, address: str, public_key: str, private_key: bytes) -> NanoWalletInfo:
        """
        Add a NANO wallet to manager.
        
        Args:
            address: NANO address
            public_key: Public key hex
            private_key: Private key bytes
        
        Returns:
            NanoWalletInfo instance
        """
        if not self.helper.is_valid_nano_address(address):
            raise ValueError(f"Invalid NANO address: {address}")
        
        wallet = NanoWalletInfo(
            address=address,
            public_key=public_key,
            private_key=private_key
        )
        
        self.wallets[address] = wallet
        
        try:
            balance, pending = await self.helper.get_balance(address)
            wallet.balance = balance
            wallet.pending = pending
        except Exception:
            pass
        
        return wallet
    
    async def refresh_wallet_balance(self, address: str) -> Optional[NanoWalletInfo]:
        """
        Refresh balance for wallet.
        
        Args:
            address: NANO address
        
        Returns:
            Updated NanoWalletInfo or None
        """
        if address not in self.wallets:
            return None
        
        try:
            balance, pending = await self.helper.get_balance(address)
            self.wallets[address].balance = balance
            self.wallets[address].pending = pending
            return self.wallets[address]
        
        except Exception:
            return None
    
    async def refresh_all_balances(self) -> Dict[str, NanoWalletInfo]:
        """
        Refresh all wallet balances.
        
        Returns:
            Dict of updated wallets
        """
        tasks = [
            self.refresh_wallet_balance(address)
            for address in self.wallets.keys()
        ]
        
        results = await asyncio.gather(*tasks)
        
        updated = {w.address: w for w in results if w}
        return updated
    
    async def cleanup(self):
        """Cleanup resources."""
        await self.helper.close()
