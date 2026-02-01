"""
Nano wallet generator.
Uses Ed25519 keys with BIP44 path: m/44'/165'/0' and blake2b address encoding.
"""
import base58
import hashlib
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass

from blockchain.bip39_derivation import BIP39Manager, BIP39SeedDeriv, BIP44Derivation
from blockchain.entropy_generator import EntropyGenerator


@dataclass
class NanoWallet:
    """Nano wallet data structure."""
    mnemonic: str
    seed: bytes
    private_key: bytes
    public_key: bytes
    address: str
    derivation_path: str
    representative: str = "nano_3t6k35gi95xu6tergt6p69ck76ogmitsa8mnijtpxm9fkcm736xtoncuohr3"
    chain: str = "nano"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'mnemonic': self.mnemonic,
            'seed': self.seed.hex(),
            'private_key': self.private_key.hex(),
            'public_key': self.public_key.hex(),
            'address': self.address,
            'derivation_path': self.derivation_path,
            'representative': self.representative,
            'chain': self.chain,
        }


class NanoWalletGenerator:
    """Generate Nano wallets."""
    
    CHAIN = "nano"
    DERIVATION_PATH = "m/44'/165'/0'"
    ADDRESS_PREFIX = "nano_"
    
    DEFAULT_REPRESENTATIVE = "nano_3t6k35gi95xu6tergt6p69ck76ogmitsa8mnijtpxm9fkcm736xtoncuohr3"
    
    def __init__(self, representative: str = None):
        """
        Initialize Nano wallet generator.
        
        Args:
            representative: Default representative for wallets
        """
        self.bip39_manager = BIP39Manager()
        self.entropy_gen = EntropyGenerator()
        self.representative = representative or self.DEFAULT_REPRESENTATIVE
    
    def generate_from_entropy(self, entropy: bytes, 
                             passphrase: str = "") -> NanoWallet:
        """
        Generate Nano wallet from entropy bytes.
        
        Args:
            entropy: Entropy bytes
            passphrase: Optional BIP39 passphrase
        
        Returns:
            NanoWallet instance
        """
        mnemonic = self.bip39_manager.entropy_to_mnemonic(entropy.hex())
        if not mnemonic:
            raise ValueError("Failed to convert entropy to mnemonic")
        
        return self.generate_from_mnemonic(mnemonic, passphrase)
    
    def generate_from_mnemonic(self, mnemonic: str, 
                              passphrase: str = "") -> NanoWallet:
        """
        Generate Nano wallet from mnemonic.
        
        Args:
            mnemonic: BIP39 mnemonic phrase
            passphrase: Optional BIP39 passphrase
        
        Returns:
            NanoWallet instance
        
        Raises:
            ValueError: If mnemonic is invalid
        """
        is_valid, message = self.bip39_manager.validate_mnemonic(mnemonic)
        if not is_valid:
            raise ValueError(f"Invalid mnemonic: {message}")
        
        seed = BIP39SeedDeriv.mnemonic_to_seed(mnemonic, passphrase)
        
        private_key, public_key, derivation_path = BIP44Derivation.derive_path(
            seed, "nano", account=0, change=0, address_index=0
        )
        
        address = self._public_key_to_address(public_key)
        
        return NanoWallet(
            mnemonic=mnemonic,
            seed=seed,
            private_key=private_key,
            public_key=public_key,
            address=address,
            derivation_path=derivation_path,
            representative=self.representative,
        )
    
    def generate_new(self, word_count: int = 24, 
                    passphrase: str = "") -> NanoWallet:
        """
        Generate new Nano wallet with random entropy.
        
        Args:
            word_count: BIP39 word count (12, 15, 18, 21, 24)
            passphrase: Optional BIP39 passphrase
        
        Returns:
            NanoWallet instance
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
                seed, "nano", account=0, change=0, address_index=i
            )
            address = self._public_key_to_address(public_key)
            addresses.append((address, public_key, path))
        
        return addresses
    
    @staticmethod
    def _public_key_to_address(public_key: bytes) -> str:
        """
        Convert Ed25519 public key to Nano address.
        
        Uses blake2b for checksum with Nano address format.
        
        Args:
            public_key: Ed25519 public key (32 bytes)
        
        Returns:
            Nano address (nano_ prefix with base58 encoding)
        """
        if len(public_key) > 32:
            public_key = public_key[:32]
        
        blake2b_hash = hashlib.blake2b(public_key, digest_size=5).digest()
        checksum = blake2b_hash[::-1]
        
        encoded = base58.b58encode(public_key + checksum).decode('utf-8')
        
        return f"nano_{encoded}"
    
    @staticmethod
    def address_to_public_key(address: str) -> Optional[bytes]:
        """
        Convert Nano address back to public key.
        Validates checksum.
        
        Args:
            address: Nano address
        
        Returns:
            Public key bytes or None if invalid
        """
        try:
            if not address.startswith("nano_"):
                return None
            
            encoded = address[5:]
            decoded = base58.b58decode(encoded)
            
            if len(decoded) != 37:
                return None
            
            public_key = decoded[:32]
            checksum = decoded[32:]
            
            expected_checksum = hashlib.blake2b(public_key, digest_size=5).digest()[::-1]
            
            if checksum != expected_checksum:
                return None
            
            return public_key
        
        except Exception:
            return None
    
    @staticmethod
    def validate_address(address: str) -> Tuple[bool, str]:
        """
        Validate Nano address format and checksum.
        
        Args:
            address: Nano address to validate
        
        Returns:
            Tuple of (is_valid, message)
        """
        try:
            if not address or not isinstance(address, str):
                return False, "Address must be a non-empty string"
            
            if not address.startswith("nano_"):
                return False, "Address must start with 'nano_'"
            
            public_key = NanoWalletGenerator.address_to_public_key(address)
            
            if public_key is None:
                return False, "Invalid address checksum"
            
            if len(public_key) != 32:
                return False, f"Invalid public key length: {len(public_key)} bytes"
            
            return True, "Address is valid"
        
        except Exception as e:
            return False, f"Address validation error: {str(e)}"
    
    @staticmethod
    def get_derivation_path(account: int = 0, address_index: int = 0) -> str:
        """
        Get BIP44 derivation path for Nano.
        
        Args:
            account: Account index
            address_index: Address index
        
        Returns:
            Derivation path string
        """
        return f"m/44'/165'/{account}'/0/{address_index}"
