"""
Configuration for blockchain integrations in Sapphire Exchange.
"""
import os
from typing import Dict, Any, Optional

# Environment variable names
ENV_DOGECOIN_NETWORK = 'DOGECOIN_NETWORK'  # 'mainnet' or 'testnet'
ENV_DOGECOIN_RPC_USER = 'DOGECOIN_RPC_USER'
ENV_DOGECOIN_RPC_PASSWORD = 'DOGECOIN_RPC_PASSWORD'
ENV_DOGECOIN_RPC_HOST = 'DOGECOIN_RPC_HOST'
ENV_DOGECOIN_RPC_PORT = 'DOGECOIN_RPC_PORT'

ENV_NANO_NETWORK = 'NANO_NETWORK'  # 'mainnet' or 'testnet'
ENV_NANO_NODE_URL = 'NANO_NODE_URL'

ENV_ARWEAVE_NETWORK = 'ARWEAVE_NETWORK'  # 'mainnet' or 'testnet'
ENV_ARWEAVE_NODE_URL = 'ARWEAVE_NODE_URL'

class BlockchainConfig:
    """Configuration for blockchain integrations."""
    
    def __init__(self):
        # Dogecoin configuration
        self.dogecoin_network = os.getenv(ENV_DOGECOIN_NETWORK, 'testnet')
        self.dogecoin_rpc_user = os.getenv(ENV_DOGECOIN_RPC_USER, 'dogecoin')
        self.dogecoin_rpc_password = os.getenv(ENV_DOGECOIN_RPC_PASSWORD, 'password')
        self.dogecoin_rpc_host = os.getenv(ENV_DOGECOIN_RPC_HOST, '127.0.0.1')
        self.dogecoin_rpc_port = os.getenv(ENV_DOGECOIN_RPC_PORT)
        
        # Nano configuration
        self.nano_network = os.getenv(ENV_NANO_NETWORK, 'testnet')
        self.nano_node_url = os.getenv(ENV_NANO_NODE_URL, 'https://mynano.ninja/api')
        
        # Arweave configuration
        self.arweave_network = os.getenv(ENV_ARWEAVE_NETWORK, 'testnet')
        self.arweave_node_url = os.getenv(ENV_ARWEAVE_NODE_URL, 'https://arweave.net')
        
        # Set default RPC ports if not specified
        if not self.dogecoin_rpc_port:
            self.dogecoin_rpc_port = 44555 if self.dogecoin_network == 'testnet' else 22555
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'dogecoin': {
                'network': self.dogecoin_network,
                'rpc_host': self.dogecoin_rpc_host,
                'rpc_port': self.dogecoin_rpc_port,
                'rpc_user': '***' if self.dogecoin_rpc_user else None,
                'rpc_password': '***' if self.dogecoin_rpc_password else None
            },
            'nano': {
                'network': self.nano_network,
                'node_url': self.nano_node_url
            },
            'arweave': {
                'network': self.arweave_network,
                'node_url': self.arweave_node_url
            }
        }

# Global configuration instance
config = BlockchainConfig()
