"""
Transaction builder for secure offline transaction construction.
Supports building transactions for Solana (USDC), Nano, and Arweave.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio


class TransactionType(Enum):
    """Transaction type enumeration."""
    TRANSFER = "transfer"
    SWAP = "swap"
    STAKE = "stake"
    UNSTAKE = "unstake"
    CUSTOM = "custom"


class TransactionPriority(Enum):
    """Transaction priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class FeeEstimate:
    """Fee estimation result."""
    base_fee: float
    priority_fee: float
    estimated_total: float
    unit_limit: int
    gas_price: float = None
    timestamp: float = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class TransactionData:
    """Generic transaction data."""
    asset: str
    chain: str
    transaction_type: TransactionType
    sender_address: str
    recipient_address: str
    amount: float
    fee: Optional[float] = None
    nonce: Optional[int] = None
    memo: Optional[str] = None
    priority: TransactionPriority = TransactionPriority.MEDIUM
    custom_params: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['transaction_type'] = self.transaction_type.value
        data['priority'] = self.priority.value
        return data


class TransactionBuilder(ABC):
    """Base class for asset-specific transaction builders."""
    
    def __init__(self, asset: str, chain: str, network: str = "mainnet"):
        """
        Initialize transaction builder.
        
        Args:
            asset: Asset type (e.g., 'usdc', 'nano')
            chain: Blockchain (e.g., 'solana', 'nano')
            network: Network type (mainnet, testnet, devnet)
        """
        self.asset = asset
        self.chain = chain
        self.network = network
        self.transaction_data: Optional[TransactionData] = None
        self.built_transaction: Optional[Dict[str, Any]] = None
    
    @abstractmethod
    async def build(self, tx_data: TransactionData) -> Dict[str, Any]:
        """
        Build transaction from transaction data.
        
        Args:
            tx_data: TransactionData instance
        
        Returns:
            Built transaction dictionary
        
        Raises:
            ValueError: If transaction data is invalid
        """
        pass
    
    @abstractmethod
    async def validate(self) -> tuple[bool, str]:
        """
        Validate built transaction.
        
        Returns:
            Tuple of (is_valid, message)
        """
        pass
    
    @abstractmethod
    async def estimate_fee(self, tx_data: TransactionData) -> FeeEstimate:
        """
        Estimate transaction fee.
        
        Args:
            tx_data: TransactionData instance
        
        Returns:
            FeeEstimate instance
        """
        pass
    
    @abstractmethod
    async def simulate(self) -> tuple[bool, Optional[str]]:
        """
        Simulate transaction execution (where available).
        
        Returns:
            Tuple of (success, error_message)
        """
        pass
    
    def get_transaction(self) -> Optional[Dict[str, Any]]:
        """Get built transaction."""
        return self.built_transaction
    
    def clear(self):
        """Clear transaction data."""
        self.transaction_data = None
        self.built_transaction = None


class SolanaTransactionBuilder(TransactionBuilder):
    """Solana transaction builder for USDC transfers."""
    
    USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    DEFAULT_COMMITMENT = "confirmed"
    
    def __init__(self, rpc_url: str = None, network: str = "mainnet"):
        """
        Initialize Solana transaction builder.
        
        Args:
            rpc_url: Solana RPC endpoint URL
            network: Network type (mainnet, testnet, devnet)
        """
        super().__init__("usdc", "solana", network)
        self.rpc_url = rpc_url or self._get_default_rpc(network)
        self.recent_blockhash: Optional[str] = None
    
    def _get_default_rpc(self, network: str) -> str:
        """Get default RPC endpoint for network."""
        endpoints = {
            "mainnet": "https://api.mainnet-beta.solana.com",
            "testnet": "https://api.testnet.solana.com",
            "devnet": "https://api.devnet.solana.com",
        }
        return endpoints.get(network, endpoints["mainnet"])
    
    async def build(self, tx_data: TransactionData) -> Dict[str, Any]:
        """
        Build Solana transaction.
        
        Args:
            tx_data: TransactionData instance
        
        Returns:
            Built transaction dictionary
        
        Raises:
            ValueError: If transaction data is invalid
        """
        is_valid, message = self._validate_transaction_data(tx_data)
        if not is_valid:
            raise ValueError(f"Invalid transaction data: {message}")
        
        self.transaction_data = tx_data
        
        self.built_transaction = {
            "type": "solana_transfer",
            "chain": self.chain,
            "asset": self.asset,
            "sender": tx_data.sender_address,
            "recipient": tx_data.recipient_address,
            "amount": int(tx_data.amount * 1e6),
            "decimals": 6,
            "mint": self.USDC_MINT,
            "fee": int(tx_data.fee * 1e9) if tx_data.fee else None,
            "memo": tx_data.memo,
            "priority": tx_data.priority.value,
            "recent_blockhash": self.recent_blockhash,
            "nonce": tx_data.nonce,
        }
        
        return self.built_transaction
    
    async def validate(self) -> tuple[bool, str]:
        """Validate built Solana transaction."""
        if not self.built_transaction:
            return False, "No transaction built"
        
        required_fields = ["sender", "recipient", "amount", "mint"]
        for field in required_fields:
            if field not in self.built_transaction or not self.built_transaction[field]:
                return False, f"Missing required field: {field}"
        
        if self.built_transaction["amount"] <= 0:
            return False, "Amount must be positive"
        
        if len(self.built_transaction["sender"]) < 20:
            return False, "Invalid sender address"
        
        if len(self.built_transaction["recipient"]) < 20:
            return False, "Invalid recipient address"
        
        return True, "Transaction is valid"
    
    async def estimate_fee(self, tx_data: TransactionData) -> FeeEstimate:
        """
        Estimate Solana transaction fee.
        
        Solana uses a fixed fee per signature (5000 lamports = 0.000005 SOL).
        Priority fees are variable.
        """
        base_fee = 0.000005
        
        priority_multipliers = {
            TransactionPriority.LOW: 1,
            TransactionPriority.MEDIUM: 2,
            TransactionPriority.HIGH: 5,
            TransactionPriority.CRITICAL: 10,
        }
        
        multiplier = priority_multipliers.get(tx_data.priority, 2)
        priority_fee = base_fee * multiplier
        
        return FeeEstimate(
            base_fee=base_fee,
            priority_fee=priority_fee,
            estimated_total=base_fee + priority_fee,
            unit_limit=200000,
            gas_price=None,
        )
    
    async def simulate(self) -> tuple[bool, Optional[str]]:
        """Simulate Solana transaction (requires full implementation)."""
        if not self.built_transaction:
            return False, "No transaction to simulate"
        
        return True, None
    
    @staticmethod
    def _validate_transaction_data(tx_data: TransactionData) -> tuple[bool, str]:
        """Validate transaction data."""
        if not tx_data.sender_address:
            return False, "Sender address required"
        
        if not tx_data.recipient_address:
            return False, "Recipient address required"
        
        if tx_data.amount <= 0:
            return False, "Amount must be positive"
        
        return True, "Valid"


class NanoTransactionBuilder(TransactionBuilder):
    """Nano transaction builder."""
    
    def __init__(self, network: str = "mainnet"):
        """
        Initialize Nano transaction builder.
        
        Args:
            network: Network type (mainnet, testnet)
        """
        super().__init__("nano", "nano", network)
        self.node_url = self._get_node_url(network)
    
    def _get_node_url(self, network: str) -> str:
        """Get Nano node URL."""
        endpoints = {
            "mainnet": "https://mynano.ninja/api",
            "testnet": "https://mynano.ninja/api",
        }
        return endpoints.get(network, endpoints["mainnet"])
    
    async def build(self, tx_data: TransactionData) -> Dict[str, Any]:
        """
        Build Nano state block transaction.
        
        Args:
            tx_data: TransactionData instance
        
        Returns:
            Built transaction dictionary
        
        Raises:
            ValueError: If transaction data is invalid
        """
        is_valid, message = self._validate_transaction_data(tx_data)
        if not is_valid:
            raise ValueError(f"Invalid transaction data: {message}")
        
        self.transaction_data = tx_data
        
        self.built_transaction = {
            "type": "nano_state_block",
            "chain": self.chain,
            "asset": self.asset,
            "account": tx_data.sender_address,
            "destination": tx_data.recipient_address,
            "amount": int(tx_data.amount * 1e30),
            "previous": None,
            "balance": None,
            "representative": tx_data.custom_params.get("representative") if tx_data.custom_params else None,
            "link": tx_data.custom_params.get("link") if tx_data.custom_params else None,
            "work": None,
            "signature": None,
            "memo": tx_data.memo,
        }
        
        return self.built_transaction
    
    async def validate(self) -> tuple[bool, str]:
        """Validate built Nano transaction."""
        if not self.built_transaction:
            return False, "No transaction built"
        
        required_fields = ["account", "destination", "amount"]
        for field in required_fields:
            if field not in self.built_transaction or not self.built_transaction[field]:
                return False, f"Missing required field: {field}"
        
        if self.built_transaction["amount"] <= 0:
            return False, "Amount must be positive"
        
        if not self.built_transaction["account"].startswith("nano_"):
            return False, "Invalid account address (must start with nano_)"
        
        if not self.built_transaction["destination"].startswith("nano_"):
            return False, "Invalid destination address (must start with nano_)"
        
        return True, "Transaction is valid"
    
    async def estimate_fee(self, tx_data: TransactionData) -> FeeEstimate:
        """
        Estimate Nano transaction fee.
        
        Nano has zero transaction fees.
        """
        return FeeEstimate(
            base_fee=0.0,
            priority_fee=0.0,
            estimated_total=0.0,
            unit_limit=0,
            gas_price=0.0,
        )
    
    async def simulate(self) -> tuple[bool, Optional[str]]:
        """Nano transactions don't simulate."""
        return True, None
    
    @staticmethod
    def _validate_transaction_data(tx_data: TransactionData) -> tuple[bool, str]:
        """Validate transaction data."""
        if not tx_data.sender_address or not tx_data.sender_address.startswith("nano_"):
            return False, "Invalid sender address"
        
        if not tx_data.recipient_address or not tx_data.recipient_address.startswith("nano_"):
            return False, "Invalid recipient address"
        
        if tx_data.amount <= 0:
            return False, "Amount must be positive"
        
        return True, "Valid"


class ArweaveTransactionBuilder(TransactionBuilder):
    """Arweave transaction builder."""
    
    AR_TO_WINSTON = 1e12
    
    def __init__(self, gateway_url: str = None, network: str = "mainnet"):
        """
        Initialize Arweave transaction builder.
        
        Args:
            gateway_url: Arweave gateway URL
            network: Network type (mainnet, testnet)
        """
        super().__init__("ar", "arweave", network)
        self.gateway_url = gateway_url or "https://arweave.net"
        self.last_tx: Optional[str] = None
    
    async def build(self, tx_data: TransactionData) -> Dict[str, Any]:
        """
        Build Arweave transaction.
        
        Args:
            tx_data: TransactionData instance
        
        Returns:
            Built transaction dictionary
        
        Raises:
            ValueError: If transaction data is invalid
        """
        is_valid, message = self._validate_transaction_data(tx_data)
        if not is_valid:
            raise ValueError(f"Invalid transaction data: {message}")
        
        self.transaction_data = tx_data
        
        self.built_transaction = {
            "type": "arweave_transfer",
            "chain": self.chain,
            "asset": self.asset,
            "from": tx_data.sender_address,
            "to": tx_data.recipient_address,
            "quantity": str(int(tx_data.amount * self.AR_TO_WINSTON)),
            "reward": str(int((tx_data.fee or 0) * self.AR_TO_WINSTON)) if tx_data.fee else "0",
            "last_tx": self.last_tx or "",
            "tags": self._build_tags(tx_data),
            "data": tx_data.memo or "",
            "signature": None,
            "owner": None,
            "id": None,
        }
        
        return self.built_transaction
    
    async def validate(self) -> tuple[bool, str]:
        """Validate built Arweave transaction."""
        if not self.built_transaction:
            return False, "No transaction built"
        
        required_fields = ["from", "to", "quantity"]
        for field in required_fields:
            if field not in self.built_transaction or self.built_transaction[field] is None:
                return False, f"Missing required field: {field}"
        
        try:
            quantity = int(self.built_transaction["quantity"])
            if quantity <= 0:
                return False, "Amount must be positive"
        except (ValueError, TypeError):
            return False, "Invalid quantity format"
        
        if len(self.built_transaction["from"]) < 20:
            return False, "Invalid from address"
        
        if len(self.built_transaction["to"]) < 20:
            return False, "Invalid to address"
        
        return True, "Transaction is valid"
    
    async def estimate_fee(self, tx_data: TransactionData) -> FeeEstimate:
        """
        Estimate Arweave transaction fee.
        
        Fee depends on transaction size and network load.
        """
        base_size = 300
        data_size = len(tx_data.memo or "") if tx_data.memo else 0
        total_size = base_size + data_size
        
        wei_per_byte = 0.5
        estimated_fee = (total_size * wei_per_byte) / self.AR_TO_WINSTON
        
        priority_multipliers = {
            TransactionPriority.LOW: 1.0,
            TransactionPriority.MEDIUM: 1.5,
            TransactionPriority.HIGH: 2.0,
            TransactionPriority.CRITICAL: 3.0,
        }
        
        multiplier = priority_multipliers.get(tx_data.priority, 1.0)
        estimated_fee *= multiplier
        
        return FeeEstimate(
            base_fee=estimated_fee / multiplier,
            priority_fee=estimated_fee - (estimated_fee / multiplier),
            estimated_total=estimated_fee,
            unit_limit=total_size,
            gas_price=wei_per_byte,
        )
    
    async def simulate(self) -> tuple[bool, Optional[str]]:
        """Arweave transactions don't have simulation."""
        return True, None
    
    @staticmethod
    def _build_tags(tx_data: TransactionData) -> List[Dict[str, str]]:
        """Build Arweave transaction tags."""
        tags = [
            {"name": "Content-Type", "value": "application/json"},
            {"name": "App-Name", "value": "Sapphire-Exchange"},
            {"name": "App-Version", "value": "1.0"},
            {"name": "Type", "value": "transfer"},
        ]
        
        if tx_data.memo:
            tags.append({"name": "Memo", "value": tx_data.memo})
        
        return tags
    
    @staticmethod
    def _validate_transaction_data(tx_data: TransactionData) -> tuple[bool, str]:
        """Validate transaction data."""
        if not tx_data.sender_address:
            return False, "Sender address required"
        
        if not tx_data.recipient_address:
            return False, "Recipient address required"
        
        if tx_data.amount <= 0:
            return False, "Amount must be positive"
        
        return True, "Valid"


class TransactionBuilderFactory:
    """Factory for creating asset-specific transaction builders."""
    
    BUILDERS = {
        "solana": SolanaTransactionBuilder,
        "nano": NanoTransactionBuilder,
        "arweave": ArweaveTransactionBuilder,
    }
    
    @classmethod
    def create(cls, chain: str, **kwargs) -> TransactionBuilder:
        """
        Create transaction builder for specified chain.
        
        Args:
            chain: Blockchain type (solana, nano, arweave)
            **kwargs: Additional arguments for builder initialization
        
        Returns:
            TransactionBuilder instance
        
        Raises:
            ValueError: If chain is not supported
        """
        if chain not in cls.BUILDERS:
            raise ValueError(f"Unsupported chain: {chain}. Supported: {list(cls.BUILDERS.keys())}")
        
        builder_class = cls.BUILDERS[chain]
        return builder_class(**kwargs)
    
    @classmethod
    def get_supported_chains(cls) -> List[str]:
        """Get list of supported chains."""
        return list(cls.BUILDERS.keys())
