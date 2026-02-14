"""
Unified wallet generator orchestrating Solana (USDC), Nano, and Arweave.
Provides single interface for creating and managing wallets across all supported assets.
"""
import json
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from blockchain.entropy_generator import EntropyGenerator
from blockchain.bip39_derivation import BIP39Manager
from blockchain.wallet_generators.solana_generator import SolanaWalletGenerator, SolanaWallet
from blockchain.wallet_generators.nano_generator import NanoWalletGenerator, NanoWallet
from blockchain.wallet_generators.arweave_generator import ArweaveWalletGenerator, ArweaveWallet


class AssetType(Enum):
    """Supported asset types."""
    SOLANA = "solana"
    NANO = "nano"
    ARWEAVE = "arweave"


@dataclass
class MultiAssetWallet:
    """Multi-asset wallet containing all blockchain wallets."""
    wallet_name: str
    mnemonic: str
    passphrase: str = ""
    solana_wallet: Optional[SolanaWallet] = None
    nano_wallet: Optional[NanoWallet] = None
    arweave_wallet: Optional[ArweaveWallet] = None
    created_at: str = ""
    version: str = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'wallet_name': self.wallet_name,
            'mnemonic': self.mnemonic,
            'passphrase': self.passphrase,
            'solana_wallet': asdict(self.solana_wallet) if self.solana_wallet else None,
            'nano_wallet': asdict(self.nano_wallet) if self.nano_wallet else None,
            'arweave_wallet': asdict(self.arweave_wallet) if self.arweave_wallet else None,
            'created_at': self.created_at,
            'version': self.version,
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        data = self.to_dict()
        return json.dumps(data, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MultiAssetWallet':
        """Create from dictionary."""
        solana_wallet = SolanaWallet(**data['solana_wallet']) if data.get('solana_wallet') else None
        nano_wallet = NanoWallet(**data['nano_wallet']) if data.get('nano_wallet') else None
        arweave_wallet = ArweaveWallet(**data['arweave_wallet']) if data.get('arweave_wallet') else None
        
        return cls(
            wallet_name=data['wallet_name'],
            mnemonic=data['mnemonic'],
            passphrase=data.get('passphrase', ''),
            solana_wallet=solana_wallet,
            nano_wallet=nano_wallet,
            arweave_wallet=arweave_wallet,
            created_at=data.get('created_at', ''),
            version=data.get('version', '1.0'),
        )


class UnifiedWalletGenerator:
    """Generate and manage multi-asset wallets."""
    
    SUPPORTED_ASSETS = {
        'solana': SolanaWalletGenerator,
        'nano': NanoWalletGenerator,
        'arweave': ArweaveWalletGenerator,
    }
    
    def __init__(self):
        """Initialize unified wallet generator."""
        self.entropy_gen = EntropyGenerator()
        self.bip39_manager = BIP39Manager()
        
        self.solana_gen = SolanaWalletGenerator()
        self.nano_gen = NanoWalletGenerator()
        self.arweave_gen = ArweaveWalletGenerator()
    
    def generate_mnemonic(self, word_count: int = 24) -> str:
        """
        Generate a new BIP39 mnemonic phrase.
        
        Args:
            word_count: Number of words (12, 15, 18, 21, or 24)
        
        Returns:
            Mnemonic phrase (space-separated words)
        """
        return self.bip39_manager.generate_mnemonic(word_count)
    
    def validate_mnemonic(self, mnemonic: str) -> Tuple[bool, str]:
        """
        Validate BIP39 mnemonic phrase.
        
        Args:
            mnemonic: Mnemonic phrase to validate
        
        Returns:
            Tuple of (is_valid, message)
        """
        return self.bip39_manager.validate_mnemonic(mnemonic)
    
    def generate_from_mnemonic(self, mnemonic: str, passphrase: str = "", 
                              assets: List[str] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Generate wallet addresses from mnemonic.
        Only Nano wallet is derived from mnemonic.
        
        Args:
            mnemonic: BIP39 mnemonic phrase
            passphrase: Optional BIP39 passphrase
            assets: List of assets to generate (default: nano only)
        
        Returns:
            Tuple of (success, wallet_data)
        """
        try:
            if assets is None:
                assets = ['nano']
            
            print(f"\n{'='*60}")
            print(f"[WALLET_GEN] Generating wallets from mnemonic for assets: {assets}")
            print(f"[WALLET_GEN] Mnemonic word count: {len(mnemonic.split())}")
            print(f"[WALLET_GEN] Passphrase: {'(empty)' if not passphrase else '(provided)'}")
            
            wallet = self.create_from_mnemonic("temp", mnemonic, passphrase, assets)
            print(f"[WALLET_GEN] Wallet created, extracting summary...")
            wallet_data = self.get_wallet_summary(wallet)
            
            # Log nano address if present
            if 'nano' in wallet_data:
                nano_addr = wallet_data['nano'].get('address', 'N/A')
                print(f"[WALLET_GEN] Generated Nano address: {nano_addr}")
            
            print(f"[WALLET_GEN] ✓ Wallet generation successful. Assets: {list(wallet_data.keys())}")
            print(f"{'='*60}\n")
            return True, wallet_data
        except Exception as e:
            print(f"❌ [WALLET_GEN] Wallet generation failed: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            return False, {'error': str(e)}
    
    def generate_new(self, wallet_name: str, word_count: int = 24,
                    passphrase: str = "", assets: List[str] = None) -> MultiAssetWallet:
        """
        Generate new multi-asset wallet with random entropy.
        
        Args:
            wallet_name: Name for the wallet
            word_count: BIP39 word count (12, 15, 18, 21, 24)
            passphrase: Optional BIP39 passphrase (25th word)
            assets: List of assets to generate (default: all supported)
        
        Returns:
            MultiAssetWallet instance
        """
        if assets is None:
            assets = ['solana', 'nano', 'arweave']
        
        entropy = self.entropy_gen.generate_entropy(word_count)
        quality = self.entropy_gen.validate_entropy(entropy)
        
        if not quality.is_valid:
            raise ValueError(f"Entropy validation failed: {quality.message}")
        
        mnemonic = self.bip39_manager.entropy_to_mnemonic(entropy.hex())
        if not mnemonic:
            raise ValueError("Failed to convert entropy to mnemonic")
        
        return self.create_from_mnemonic(wallet_name, mnemonic, passphrase, assets)
    
    def create_from_mnemonic(self, wallet_name: str, mnemonic: str,
                            passphrase: str = "", assets: List[str] = None) -> MultiAssetWallet:
        """
        Create multi-asset wallet from existing mnemonic.
        Only Nano wallet is derived from mnemonic.
        Solana and Arweave wallets are generated fresh (not from mnemonic).
        
        Args:
            wallet_name: Name for the wallet
            mnemonic: BIP39 mnemonic phrase
            passphrase: Optional BIP39 passphrase
            assets: List of assets to generate (default: all supported)
        
        Returns:
            MultiAssetWallet instance
        
        Raises:
            ValueError: If mnemonic is invalid
        """
        if assets is None:
            assets = ['nano']
        
        is_valid, message = self.bip39_manager.validate_mnemonic(mnemonic)
        if not is_valid:
            raise ValueError(f"Invalid mnemonic: {message}")
        
        solana_wallet = None
        nano_wallet = None
        arweave_wallet = None
        
        if 'nano' in assets:
            nano_wallet = self.nano_gen.generate_from_mnemonic(mnemonic, passphrase)
        
        if 'solana' in assets:
            solana_wallet = self.solana_gen.generate_new()
        
        if 'arweave' in assets:
            arweave_wallet = self.arweave_gen.generate_new()
        
        from datetime import datetime
        created_at = datetime.utcnow().isoformat()
        
        return MultiAssetWallet(
            wallet_name=wallet_name,
            mnemonic=mnemonic,
            passphrase=passphrase,
            solana_wallet=solana_wallet,
            nano_wallet=nano_wallet,
            arweave_wallet=arweave_wallet,
            created_at=created_at,
        )
    
    def create_from_entropy(self, wallet_name: str, entropy: bytes,
                           passphrase: str = "", assets: List[str] = None) -> MultiAssetWallet:
        """
        Create multi-asset wallet from entropy bytes.
        
        Args:
            wallet_name: Name for the wallet
            entropy: Entropy bytes
            passphrase: Optional BIP39 passphrase
            assets: List of assets to generate
        
        Returns:
            MultiAssetWallet instance
        """
        mnemonic = self.bip39_manager.entropy_to_mnemonic(entropy.hex())
        if not mnemonic:
            raise ValueError("Failed to convert entropy to mnemonic")
        
        return self.create_from_mnemonic(wallet_name, mnemonic, passphrase, assets)
    
    def get_wallet_summary(self, wallet: MultiAssetWallet) -> Dict[str, Any]:
        """
        Get summary of wallet addresses and chains.
        Returns chain-indexed format for easy access by asset name.
        
        Args:
            wallet: MultiAssetWallet instance
        
        Returns:
            Dictionary with wallet data indexed by chain name (nano, solana, arweave)
        """
        summary = {}
        
        if wallet.nano_wallet:
            summary['nano'] = {
                'address': wallet.nano_wallet.address,
                'public_key': wallet.nano_wallet.public_key,
                'derivation_path': wallet.nano_wallet.derivation_path,
                'representative': wallet.nano_wallet.representative,
            }
        
        if wallet.solana_wallet:
            summary['solana'] = {
                'address': wallet.solana_wallet.address,
                'public_key': wallet.solana_wallet.public_key,
                'derivation_path': wallet.solana_wallet.derivation_path,
            }
        
        if wallet.arweave_wallet:
            summary['arweave'] = {
                'address': wallet.arweave_wallet.address,
                'wallet_id': wallet.arweave_wallet.wallet_id,
            }
        
        return summary
    
    def validate_mnemonic(self, mnemonic: str) -> Tuple[bool, str]:
        """
        Validate BIP39 mnemonic.
        
        Args:
            mnemonic: Mnemonic phrase to validate
        
        Returns:
            Tuple of (is_valid, message)
        """
        return self.bip39_manager.validate_mnemonic(mnemonic)
    
    def export_wallet_json(self, wallet: MultiAssetWallet) -> str:
        """
        Export wallet as JSON (without private keys by default).
        
        Args:
            wallet: MultiAssetWallet instance
        
        Returns:
            JSON string with wallet data (public keys only)
        """
        data = {
            'wallet_name': wallet.wallet_name,
            'created_at': wallet.created_at,
            'version': wallet.version,
            'assets': []
        }
        
        if wallet.solana_wallet:
            data['assets'].append({
                'chain': 'solana',
                'coin': 'USDC',
                'address': wallet.solana_wallet.address,
                'public_key': wallet.solana_wallet.public_key.hex(),
                'derivation_path': wallet.solana_wallet.derivation_path,
            })
        
        if wallet.nano_wallet:
            data['assets'].append({
                'chain': 'nano',
                'address': wallet.nano_wallet.address,
                'public_key': wallet.nano_wallet.public_key.hex(),
                'derivation_path': wallet.nano_wallet.derivation_path,
                'representative': wallet.nano_wallet.representative,
            })
        
        if wallet.arweave_wallet:
            data['assets'].append({
                'chain': 'arweave',
                'address': wallet.arweave_wallet.address,
                'wallet_id': wallet.arweave_wallet.wallet_id,
            })
        
        return json.dumps(data, indent=2)
    
    def export_wallet_private(self, wallet: MultiAssetWallet, password: str = None) -> str:
        """
        Export wallet with private keys (SENSITIVE!).
        
        Args:
            wallet: MultiAssetWallet instance
            password: Optional password for additional security (not encrypted here)
        
        Returns:
            JSON string with full wallet data (include private keys)
        
        Warning:
            This exports sensitive private keys. Use with caution!
        """
        data = {
            'wallet_name': wallet.wallet_name,
            'mnemonic': wallet.mnemonic,
            'passphrase': wallet.passphrase,
            'created_at': wallet.created_at,
            'version': wallet.version,
            'WARNING': 'This file contains sensitive private keys. Keep it secure!',
            'assets': []
        }
        
        if wallet.solana_wallet:
            data['assets'].append({
                'chain': 'solana',
                'coin': 'USDC',
                'address': wallet.solana_wallet.address,
                'public_key': wallet.solana_wallet.public_key.hex(),
                'private_key': wallet.solana_wallet.private_key.hex(),
                'seed': wallet.solana_wallet.seed.hex(),
                'derivation_path': wallet.solana_wallet.derivation_path,
            })
        
        if wallet.nano_wallet:
            data['assets'].append({
                'chain': 'nano',
                'address': wallet.nano_wallet.address,
                'public_key': wallet.nano_wallet.public_key.hex(),
                'private_key': wallet.nano_wallet.private_key.hex(),
                'seed': wallet.nano_wallet.seed.hex(),
                'derivation_path': wallet.nano_wallet.derivation_path,
                'representative': wallet.nano_wallet.representative,
            })
        
        if wallet.arweave_wallet:
            data['assets'].append({
                'chain': 'arweave',
                'address': wallet.arweave_wallet.address,
                'wallet_id': wallet.arweave_wallet.wallet_id,
                'jwk': wallet.arweave_wallet.jwk,
            })
        
        return json.dumps(data, indent=2)
    
    def get_address(self, wallet: MultiAssetWallet, chain: str) -> Optional[str]:
        """
        Get address for specific chain from wallet.
        
        Args:
            wallet: MultiAssetWallet instance
            chain: Chain name ('solana', 'nano', 'arweave')
        
        Returns:
            Address string or None
        """
        if chain == 'solana' and wallet.solana_wallet:
            return wallet.solana_wallet.address
        elif chain == 'nano' and wallet.nano_wallet:
            return wallet.nano_wallet.address
        elif chain == 'arweave' and wallet.arweave_wallet:
            return wallet.arweave_wallet.address
        return None
    
    def get_public_key(self, wallet: MultiAssetWallet, chain: str) -> Optional[str]:
        """
        Get public key for specific chain from wallet.
        
        Args:
            wallet: MultiAssetWallet instance
            chain: Chain name ('solana', 'nano', 'arweave')
        
        Returns:
            Public key hex string or None
        """
        if chain == 'solana' and wallet.solana_wallet:
            return wallet.solana_wallet.public_key.hex()
        elif chain == 'nano' and wallet.nano_wallet:
            return wallet.nano_wallet.public_key.hex()
        elif chain == 'arweave' and wallet.arweave_wallet:
            return wallet.arweave_wallet.public_key
        return None
