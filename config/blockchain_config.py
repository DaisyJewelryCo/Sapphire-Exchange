"""
Blockchain configuration for Sapphire Exchange.
Based on robot_info.json and More_Robot_info.json specifications.
"""
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class NanoConfig:
    """Nano blockchain configuration."""
    network_type: str = "cryptocurrency"
    purpose: str = "Payments and transactions"
    rpc_endpoint: str = "http://[::1]:7076"
    default_representative: str = "nano_3t6k35gi95xu6tergt6p69ck76ogmitsa8mnijtpxm9fkcm736xtoncuohr3"
    
    # Wallet specifications
    seed_length_bits: int = 256
    address_length: int = 64
    key_derivation: str = "ed25519_blake2b"
    address_prefix: str = "nano_"
    
    # Transaction parameters
    min_amount_raw: str = "1"
    max_amount_raw: str = "340282366920938463463374607431768211455"
    decimal_places: int = 30
    confirmation_blocks: int = 1


@dataclass
class ArweaveConfig:
    """Arweave blockchain configuration."""
    network_type: str = "data storage"
    purpose: str = "Permanent, decentralized data storage"
    gateway_url: str = "https://arweave.net"
    
    # Wallet specifications
    key_type: str = "RSA-PSS"
    key_length_bits: int = 4096
    wallet_format: str = "JSON"
    
    # Data parameters
    max_block_size_bytes: int = 10485760
    transaction_fee_algorithm: str = "Winston"
    default_tags: list = None
    
    def __post_init__(self):
        if self.default_tags is None:
            self.default_tags = [
                "App-Name: Sapphire-Exchange",
                "Content-Type: application/json"
            ]


@dataclass
class DogecoinConfig:
    """Dogecoin blockchain configuration."""
    network_type: str = "cryptocurrency"
    purpose: str = "Primary currency for UI and transactions"
    
    # Wallet specifications
    derivation_path: str = "m/44'/3'/0'/0/0"
    mnemonic_standard: str = "BIP39"
    
    # Network settings
    network: str = "testnet"  # mainnet or testnet
    rpc_host: str = "127.0.0.1"
    rpc_port: int = 44555  # testnet default
    rpc_user: str = "dogecoin"
    rpc_password: str = "password"
    
    # Security settings
    export_method: str = "Secure download only"
    redisplay_policy: str = "Never re-display seed after initial generation"


class BlockchainConfig:
    """Unified blockchain configuration for all supported networks."""
    
    def __init__(self):
        """Initialize blockchain configuration from environment variables."""
        # Nano configuration
        self.nano = NanoConfig(
            rpc_endpoint=os.getenv('NANO_NODE_URL', 'http://[::1]:7076'),
            default_representative=os.getenv(
                'NANO_REPRESENTATIVE', 
                'nano_3t6k35gi95xu6tergt6p69ck76ogmitsa8mnijtpxm9fkcm736xtoncuohr3'
            )
        )
        
        # Arweave configuration
        self.arweave = ArweaveConfig(
            gateway_url=os.getenv('ARWEAVE_GATEWAY_URL', 'https://arweave.net')
        )
        
        # Dogecoin configuration
        dogecoin_network = os.getenv('DOGECOIN_NETWORK', 'testnet')
        dogecoin_rpc_port = os.getenv('DOGECOIN_RPC_PORT')
        if not dogecoin_rpc_port:
            dogecoin_rpc_port = 44555 if dogecoin_network == 'testnet' else 22555
        
        self.dogecoin = DogecoinConfig(
            network=dogecoin_network,
            rpc_host=os.getenv('DOGECOIN_RPC_HOST', '127.0.0.1'),
            rpc_port=int(dogecoin_rpc_port),
            rpc_user=os.getenv('DOGECOIN_RPC_USER', 'dogecoin'),
            rpc_password=os.getenv('DOGECOIN_RPC_PASSWORD', 'password')
        )
        
        # Environment-specific settings
        self.mock_nano = os.getenv('MOCK_NANO', 'false').lower() == 'true'
        self.mock_arweave = os.getenv('MOCK_ARWEAVE', 'false').lower() == 'true'
        self.mock_dogecoin = os.getenv('MOCK_DOGECOIN', 'false').lower() == 'true'
        
        # Wallet file paths
        self.arweave_wallet_file = os.getenv('ARWEAVE_WALLET_FILE', 'wallet.json')
        self.dogecoin_wallet_file = os.getenv('DOGECOIN_WALLET_FILE', 'dogecoin_wallet.dat')
    
    def get_nano_config(self) -> Dict[str, Any]:
        """Get Nano configuration dictionary."""
        return {
            "network_type": self.nano.network_type,
            "purpose": self.nano.purpose,
            "rpc_endpoint": self.nano.rpc_endpoint,
            "default_representative": self.nano.default_representative,
            "wallet_specs": {
                "seed_length_bits": self.nano.seed_length_bits,
                "address_length": self.nano.address_length,
                "key_derivation": self.nano.key_derivation,
                "address_prefix": self.nano.address_prefix
            },
            "transaction_parameters": {
                "min_amount_raw": self.nano.min_amount_raw,
                "max_amount_raw": self.nano.max_amount_raw,
                "decimal_places": self.nano.decimal_places,
                "confirmation_blocks": self.nano.confirmation_blocks
            },
            "mock_mode": self.mock_nano
        }
    
    def get_arweave_config(self) -> Dict[str, Any]:
        """Get Arweave configuration dictionary."""
        return {
            "network_type": self.arweave.network_type,
            "purpose": self.arweave.purpose,
            "gateway_url": self.arweave.gateway_url,
            "wallet_specs": {
                "key_type": self.arweave.key_type,
                "key_length_bits": self.arweave.key_length_bits,
                "wallet_format": self.arweave.wallet_format
            },
            "data_parameters": {
                "max_block_size_bytes": self.arweave.max_block_size_bytes,
                "transaction_fee_algorithm": self.arweave.transaction_fee_algorithm,
                "default_tags": self.arweave.default_tags
            },
            "wallet_file": self.arweave_wallet_file,
            "mock_mode": self.mock_arweave
        }
    
    def get_dogecoin_config(self) -> Dict[str, Any]:
        """Get Dogecoin configuration dictionary."""
        return {
            "network_type": self.dogecoin.network_type,
            "purpose": self.dogecoin.purpose,
            "wallet_specs": {
                "derivation_path": self.dogecoin.derivation_path,
                "mnemonic_standard": self.dogecoin.mnemonic_standard
            },
            "network_settings": {
                "network": self.dogecoin.network,
                "rpc_host": self.dogecoin.rpc_host,
                "rpc_port": self.dogecoin.rpc_port,
                "rpc_user": self.dogecoin.rpc_user,
                "rpc_password": "***"  # Hide password in config output
            },
            "security_settings": {
                "export_method": self.dogecoin.export_method,
                "redisplay_policy": self.dogecoin.redisplay_policy
            },
            "wallet_file": self.dogecoin_wallet_file,
            "mock_mode": self.mock_dogecoin
        }
    
    def get_conversion_formulas(self) -> Dict[str, Dict[str, Any]]:
        """Get currency conversion formulas from robot_info.json."""
        return {
            "nano_to_raw": {
                "description": "Convert Nano to raw units",
                "formula": "raw = nano * 10^30",
                "example": {"input": 1.5, "output": "1500000000000000000000000000000"}
            },
            "raw_to_nano": {
                "description": "Convert raw units to Nano",
                "formula": "nano = raw / 10^30",
                "example": {"input": "1500000000000000000000000000000", "output": 1.5}
            },
            "ar_to_winston": {
                "description": "Convert AR to winston",
                "formula": "winston = ar * 10^12",
                "example": {"input": 1.5, "output": "1500000000000"}
            },
            "winston_to_ar": {
                "description": "Convert winston to AR",
                "formula": "ar = winston / 10^12",
                "example": {"input": "1500000000000", "output": 1.5}
            }
        }
    
    def get_api_endpoints(self) -> Dict[str, Dict[str, Any]]:
        """Get API endpoint configurations."""
        return {
            "nano_rpc": {
                "base_url": self.nano.rpc_endpoint,
                "methods": [
                    "account_balance",
                    "account_info", 
                    "account_create",
                    "block_confirm",
                    "send_payment"
                ]
            },
            "arweave_gateway": {
                "base_url": self.arweave.gateway_url,
                "endpoints": [
                    "/tx",
                    "/tx_anchor",
                    "/price/{bytes}",
                    "/wallet/{address}/balance"
                ]
            }
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "nano": self.get_nano_config(),
            "arweave": self.get_arweave_config(),
            "dogecoin": self.get_dogecoin_config(),
            "conversion_formulas": self.get_conversion_formulas(),
            "api_endpoints": self.get_api_endpoints()
        }
    
    def validate(self) -> bool:
        """Validate blockchain configuration."""
        try:
            # Validate Nano configuration
            assert self.nano.rpc_endpoint.startswith(('http://', 'https://'))
            assert len(self.nano.default_representative) == 65  # nano_ + 60 chars
            assert self.nano.default_representative.startswith('nano_')
            
            # Validate Arweave configuration
            assert self.arweave.gateway_url.startswith(('http://', 'https://'))
            assert self.arweave.key_length_bits > 0
            assert self.arweave.max_block_size_bytes > 0
            
            # Validate Dogecoin configuration
            assert self.dogecoin.network in ['mainnet', 'testnet']
            assert self.dogecoin.rpc_port > 0
            assert len(self.dogecoin.rpc_user) > 0
            
            return True
        except (AssertionError, ValueError):
            return False


# Global configuration instance
blockchain_config = BlockchainConfig()