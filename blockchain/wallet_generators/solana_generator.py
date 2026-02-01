"""
Solana wallet generator for USDC on Solana.
Uses Ed25519 keys and BIP44 path: m/44'/501'/0'/0'
"""
import base58
import hashlib
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass

from blockchain.bip39_derivation import BIP39Manager, BIP39SeedDeriv, BIP44Derivation
from blockchain.entropy_generator import EntropyGenerator


@dataclass
class SolanaWallet:
    """Solana wallet data structure."""
    mnemonic: str
    seed: bytes
    private_key: bytes
    public_key: bytes
    address: str
    derivation_path: str
    chain: str = "solana"
    coin: str = "USDC"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'mnemonic': self.mnemonic,
            'seed': self.seed.hex(),
            'private_key': self.private_key.hex(),
            'public_key': self.public_key.hex(),
            'address': self.address,
            'derivation_path': self.derivation_path,
            'chain': self.chain,
            'coin': self.coin,
        }


class SolanaWalletGenerator:
    """Generate Solana wallets for USDC trading."""
    
    CHAIN = "solana"
    COIN = "USDC"
    DERIVATION_PATH = "m/44'/501'/0'/0'"
    
    USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    
    def __init__(self):
        """Initialize Solana wallet generator."""
        self.bip39_manager = BIP39Manager()
        self.entropy_gen = EntropyGenerator()
    
    def generate_from_entropy(self, entropy: bytes, 
                             passphrase: str = "") -> SolanaWallet:
        """
        Generate Solana wallet from entropy bytes.
        
        Args:
            entropy: Entropy bytes
            passphrase: Optional BIP39 passphrase (25th word)
        
        Returns:
            SolanaWallet instance
        """
        mnemonic = self.bip39_manager.entropy_to_mnemonic(entropy.hex())
        if not mnemonic:
            raise ValueError("Failed to convert entropy to mnemonic")
        
        return self.generate_from_mnemonic(mnemonic, passphrase)
    
    def generate_from_mnemonic(self, mnemonic: str, 
                              passphrase: str = "") -> SolanaWallet:
        """
        Generate Solana wallet from mnemonic.
        
        Args:
            mnemonic: BIP39 mnemonic phrase
            passphrase: Optional BIP39 passphrase
        
        Returns:
            SolanaWallet instance
        
        Raises:
            ValueError: If mnemonic is invalid
        """
        is_valid, message = self.bip39_manager.validate_mnemonic(mnemonic)
        if not is_valid:
            raise ValueError(f"Invalid mnemonic: {message}")
        
        seed = BIP39SeedDeriv.mnemonic_to_seed(mnemonic, passphrase)
        
        private_key, public_key, derivation_path = BIP44Derivation.derive_path(
            seed, "solana", account=0, change=0, address_index=0
        )
        
        address = self._public_key_to_address(public_key)
        
        return SolanaWallet(
            mnemonic=mnemonic,
            seed=seed,
            private_key=private_key,
            public_key=public_key,
            address=address,
            derivation_path=derivation_path,
        )
    
    def generate_new(self, word_count: int = 24, 
                    passphrase: str = "") -> SolanaWallet:
        """
        Generate new Solana wallet with random entropy.
        
        Args:
            word_count: BIP39 word count (12, 15, 18, 21, 24)
            passphrase: Optional BIP39 passphrase
        
        Returns:
            SolanaWallet instance
        """
        entropy = self.entropy_gen.generate_entropy(word_count)
        
        quality = self.entropy_gen.validate_entropy(entropy)
        if not quality.is_valid:
            raise ValueError(f"Entropy validation failed: {quality.message}")
        
        return self.generate_from_entropy(entropy, passphrase)
    
    def derive_multiple_addresses(self, mnemonic: str, 
                                 count: int = 5,
                                 passphrase: str = "") -> list:
        """
        Derive multiple addresses from single mnemonic.
        
        Args:
            mnemonic: BIP39 mnemonic
            count: Number of addresses to derive
            passphrase: Optional BIP39 passphrase
        
        Returns:
            List of (address, public_key, derivation_path) tuples
        """
        is_valid, message = self.bip39_manager.validate_mnemonic(mnemonic)
        if not is_valid:
            raise ValueError(f"Invalid mnemonic: {message}")
        
        seed = BIP39SeedDeriv.mnemonic_to_seed(mnemonic, passphrase)
        
        addresses = []
        for i in range(count):
            _, public_key, path = BIP44Derivation.derive_path(
                seed, "solana", account=0, change=0, address_index=i
            )
            address = self._public_key_to_address(public_key)
            addresses.append((address, public_key, path))
        
        return addresses
    
    @staticmethod
    def _public_key_to_address(public_key: bytes) -> str:
        """
        Convert Ed25519 public key to Solana address.
        
        Args:
            public_key: Ed25519 public key (32 bytes)
        
        Returns:
            Solana address (Base58 encoded)
        """
        if len(public_key) > 32:
            public_key = public_key[:32]
        
        address = base58.b58encode(public_key).decode('utf-8')
        return address
    
    @staticmethod
    def validate_address(address: str) -> Tuple[bool, str]:
        """
        Validate Solana address format.
        
        Args:
            address: Solana address to validate
        
        Returns:
            Tuple of (is_valid, message)
        """
        try:
            if not address or not isinstance(address, str):
                return False, "Address must be a non-empty string"
            
            decoded = base58.b58decode(address)
            
            if len(decoded) != 32:
                return False, f"Invalid address length: {len(decoded)} bytes (expected 32)"
            
            return True, "Address is valid"
        
        except Exception as e:
            return False, f"Address validation error: {str(e)}"
    
    @staticmethod
    def get_derivation_path(account: int = 0, change: int = 0, 
                           address_index: int = 0) -> str:
        """
        Get BIP44 derivation path for given indices.
        
        Args:
            account: Account index
            change: Change index (0 for external)
            address_index: Address index
        
        Returns:
            Derivation path string
        """
        return f"m/44'/501'/{account}'/0/{address_index}"
