"""
BIP39 and BIP44 derivation for deterministic key generation.
Supports multiple curves: secp256k1 (Ethereum), Ed25519 (Nano/Solana), and others.
"""
import hashlib
import hmac
from typing import Tuple, Optional, List
from mnemonic import Mnemonic
from bip_utils import (
    Bip39MnemonicValidator,
    Bip39SeedGenerator,
    Bip39Languages,
    Bip44,
    Bip44Changes,
    Bip44Coins,
    EllipticCurveTypes
)


class BIP39Manager:
    """BIP39 mnemonic generation and validation."""
    
    SUPPORTED_LANGUAGES = ['english']
    VALID_WORD_COUNTS = [12, 15, 18, 21, 24]
    
    def __init__(self, language: str = 'english'):
        """
        Initialize BIP39 manager.
        
        Args:
            language: Language for wordlist (default: english)
        
        Raises:
            ValueError: If language is not supported
        """
        if language not in self.SUPPORTED_LANGUAGES:
            raise ValueError(f"Language '{language}' not supported")
        
        self.language = language
        self.mnemonic_gen = Mnemonic(language)
    
    def generate_mnemonic(self, word_count: int = 24) -> str:
        """
        Generate a new BIP39 mnemonic phrase.
        
        Args:
            word_count: Number of words (12, 15, 18, 21, or 24)
        
        Returns:
            Mnemonic phrase (space-separated words)
        
        Raises:
            ValueError: If word_count is invalid
        """
        if word_count not in self.VALID_WORD_COUNTS:
            raise ValueError(
                f"Invalid word count: {word_count}. "
                f"Must be one of {self.VALID_WORD_COUNTS}"
            )
        
        strength_map = {
            12: 128,
            15: 160,
            18: 192,
            21: 224,
            24: 256,
        }
        strength = strength_map[word_count]
        mnemonic = self.mnemonic_gen.generate(strength=strength)
        return mnemonic
    
    def validate_mnemonic(self, mnemonic: str) -> Tuple[bool, str]:
        """
        Validate BIP39 mnemonic phrase.
        
        Args:
            mnemonic: Mnemonic phrase to validate
        
        Returns:
            Tuple of (is_valid, message)
        """
        try:
            if not mnemonic or not isinstance(mnemonic, str):
                return False, "Mnemonic must be a non-empty string"
            
            words = mnemonic.split()
            
            if len(words) not in self.VALID_WORD_COUNTS:
                return False, f"Invalid word count: {len(words)}. Must be one of {self.VALID_WORD_COUNTS}"
            
            is_valid = Bip39MnemonicValidator(Bip39Languages.ENGLISH).IsValid(mnemonic)
            
            if not is_valid:
                return False, "Mnemonic is not valid (checksum failed)"
            
            return True, "Mnemonic is valid"
        
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def get_word_count(self, mnemonic: str) -> int:
        """
        Get word count from mnemonic.
        
        Args:
            mnemonic: Mnemonic phrase
        
        Returns:
            Number of words
        """
        return len(mnemonic.split())
    
    def mnemonic_to_entropy(self, mnemonic: str) -> Optional[str]:
        """
        Convert mnemonic to entropy hex string.
        
        Args:
            mnemonic: Mnemonic phrase
        
        Returns:
            Entropy hex string or None if invalid
        """
        is_valid, _ = self.validate_mnemonic(mnemonic)
        if not is_valid:
            return None
        
        try:
            entropy = self.mnemonic_gen.to_entropy(mnemonic).hex()
            return entropy
        except Exception:
            return None
    
    def entropy_to_mnemonic(self, entropy_hex: str) -> Optional[str]:
        """
        Convert entropy hex to mnemonic.
        
        Args:
            entropy_hex: Entropy as hex string
        
        Returns:
            Mnemonic phrase or None if invalid
        """
        try:
            entropy_bytes = bytes.fromhex(entropy_hex)
            mnemonic = self.mnemonic_gen.to_mnemonic(entropy_bytes)
            return mnemonic
        except Exception:
            return None


class BIP39SeedDeriv:
    """BIP39 seed derivation from mnemonic."""
    
    BIP39_PBKDF2_ITERATIONS = 2048
    BIP39_PBKDF2_ALGORITHM = 'sha512'
    
    @staticmethod
    def mnemonic_to_seed(mnemonic: str, passphrase: str = "") -> bytes:
        """
        Derive BIP39 seed from mnemonic using PBKDF2.
        
        Args:
            mnemonic: Mnemonic phrase
            passphrase: Optional passphrase (25th word)
        
        Returns:
            64-byte seed
        """
        seed_gen = Bip39SeedGenerator(mnemonic)
        seed = seed_gen.Generate(passphrase)
        return seed
    
    @staticmethod
    def validate_seed(seed: bytes) -> Tuple[bool, str]:
        """
        Validate BIP39 seed.
        
        Args:
            seed: Seed bytes
        
        Returns:
            Tuple of (is_valid, message)
        """
        if not isinstance(seed, bytes):
            return False, "Seed must be bytes"
        
        if len(seed) != 64:
            return False, f"Seed must be 64 bytes, got {len(seed)}"
        
        return True, "Seed is valid"


class BIP44Derivation:
    """BIP44 hierarchical deterministic wallet derivation."""
    
    COIN_TYPES = {
        'ethereum': Bip44Coins.ETHEREUM,
        'solana': Bip44Coins.SOLANA,
        'nano': Bip44Coins.NANO,
        'stellar': Bip44Coins.STELLAR,
    }
    
    CURVE_TYPES = {
        'ethereum': EllipticCurveTypes.SECP256K1,
        'solana': EllipticCurveTypes.ED25519,
        'nano': EllipticCurveTypes.ED25519,
        'stellar': EllipticCurveTypes.ED25519,
    }
    
    STANDARD_PATHS = {
        'ethereum': "m/44'/60'/0'/0/0",
        'solana': "m/44'/501'/0'/0'",
        'nano': "m/44'/165'/0'",
        'stellar': "m/44'/148'/0'/0/0",
    }
    
    COIN_CODES = {
        Bip44Coins.ETHEREUM: 60,
        Bip44Coins.SOLANA: 501,
        Bip44Coins.NANO: 165,
        Bip44Coins.STELLAR: 148,
    }
    
    @staticmethod
    def derive_path(seed: bytes, asset: str, account: int = 0, 
                   change: int = 0, address_index: int = 0) -> Tuple[bytes, bytes, str]:
        """
        Derive keypair from seed using BIP44 path.
        
        Args:
            seed: BIP39 seed (64 bytes)
            asset: Asset type ('ethereum', 'solana', 'nano', 'stellar')
            account: Account index (typically 0)
            change: Change index (0 for external, 1 for internal)
            address_index: Address index
        
        Returns:
            Tuple of (private_key, public_key, derivation_path)
        
        Raises:
            ValueError: If asset is not supported
        """
        if asset not in BIP44Derivation.COIN_TYPES:
            raise ValueError(f"Unsupported asset: {asset}")
        
        coin_type = BIP44Derivation.COIN_TYPES[asset]
        curve_type = BIP44Derivation.CURVE_TYPES[asset]
        
        bip44_mnemonic = Bip44.FromSeed(seed, coin_type)
        bip44_account = bip44_mnemonic.Purpose().Coin().Account(account)
        
        if asset in ['nano', 'solana']:
            bip44_addr_ctx = bip44_account.Change(Bip44Changes.CHAIN_EXT).AddressIndex(address_index)
        else:
            bip44_addr_ctx = bip44_account.Change(change).AddressIndex(address_index)
        
        if curve_type == EllipticCurveTypes.ED25519:
            private_key_bytes = bip44_addr_ctx.PrivateKey().Raw().ToBytes()
            public_key_bytes = bip44_addr_ctx.PublicKey().RawUncompressed().ToBytes()
            if len(public_key_bytes) > 32:
                public_key_bytes = public_key_bytes[-32:]
        else:
            private_key_bytes = bip44_addr_ctx.PrivateKey().RawCompressed().ToBytes()
            public_key_bytes = bip44_addr_ctx.PublicKey().RawCompressed().ToBytes()
        
        coin_code = BIP44Derivation._get_coin_code_by_type(coin_type)
        derivation_path = f"m/44'/{coin_code}'/{account}'/0/{address_index}"
        
        return private_key_bytes, public_key_bytes, derivation_path
    
    @staticmethod
    def _get_coin_code_by_type(coin_type) -> int:
        """
        Get coin code from Bip44Coins enum.
        
        Args:
            coin_type: Bip44Coins enum value
        
        Returns:
            Coin code as integer
        """
        return BIP44Derivation.COIN_CODES.get(coin_type, 0)
    
    @staticmethod
    def get_standard_path(asset: str) -> str:
        """
        Get standard BIP44 derivation path for asset.
        
        Args:
            asset: Asset type
        
        Returns:
            Standard derivation path string
        """
        return BIP44Derivation.STANDARD_PATHS.get(asset, "m/44'/0'/0'/0/0")
    
    @staticmethod
    def derive_from_path(seed: bytes, path: str) -> Tuple[bytes, bytes]:
        """
        Derive keypair from custom BIP44 path.
        
        Args:
            seed: BIP39 seed
            path: Custom derivation path (e.g., "m/44'/60'/0'/0/0")
        
        Returns:
            Tuple of (private_key, public_key)
        """
        from bip_utils import Bip44, Bip44Coins
        
        bip44_ctx = Bip44.FromSeed(seed, Bip44Coins.BITCOIN)
        bip44_derived = bip44_ctx.DerivePath(path)
        
        private_key = bip44_derived.PrivateKey().RawCompressed().ToBytes()
        public_key = bip44_derived.PublicKey().RawCompressed().ToBytes()
        
        return private_key, public_key


class SLIPDerivation:
    """SLIP-0010 derivation for Ed25519 curves."""
    
    @staticmethod
    def derive_master_key(seed: bytes) -> Tuple[bytes, bytes]:
        """
        Derive master key from seed using SLIP-0010.
        
        Args:
            seed: Master seed
        
        Returns:
            Tuple of (master_key, chain_code)
        """
        hmac_result = hmac.new(
            b"ed25519 seed",
            seed,
            hashlib.sha512
        ).digest()
        
        master_key = hmac_result[:32]
        chain_code = hmac_result[32:]
        
        return master_key, chain_code
    
    @staticmethod
    def derive_child_key(parent_key: bytes, parent_chain_code: bytes, 
                        index: int) -> Tuple[bytes, bytes]:
        """
        Derive child key from parent using SLIP-0010.
        
        Args:
            parent_key: Parent private key
            parent_chain_code: Parent chain code
            index: Child index (must be hardened for Ed25519)
        
        Returns:
            Tuple of (child_key, child_chain_code)
        """
        if not (index & 0x80000000):
            raise ValueError("Ed25519 only supports hardened derivation")
        
        index_bytes = index.to_bytes(4, byteorder='big')
        data = b'\x00' + parent_key + index_bytes
        
        hmac_result = hmac.new(
            parent_chain_code,
            data,
            hashlib.sha512
        ).digest()
        
        child_key = hmac_result[:32]
        child_chain_code = hmac_result[32:]
        
        return child_key, child_chain_code


class WalletDerivationHelper:
    """Helper class for complete wallet derivation workflow."""
    
    def __init__(self):
        """Initialize derivation helper."""
        self.bip39_manager = BIP39Manager()
    
    def create_from_entropy(self, entropy_bytes: bytes, 
                           asset: str, passphrase: str = "") -> Tuple[str, bytes, bytes, str]:
        """
        Create wallet from entropy bytes.
        
        Args:
            entropy_bytes: Raw entropy
            asset: Asset type
            passphrase: Optional BIP39 passphrase
        
        Returns:
            Tuple of (mnemonic, private_key, public_key, derivation_path)
        """
        mnemonic = self.bip39_manager.entropy_to_mnemonic(entropy_bytes.hex())
        if not mnemonic:
            raise ValueError("Failed to convert entropy to mnemonic")
        
        return self.create_from_mnemonic(mnemonic, asset, passphrase)
    
    def create_from_mnemonic(self, mnemonic: str, asset: str, 
                            passphrase: str = "") -> Tuple[str, bytes, bytes, str]:
        """
        Create wallet from mnemonic.
        
        Args:
            mnemonic: BIP39 mnemonic phrase
            asset: Asset type
            passphrase: Optional BIP39 passphrase
        
        Returns:
            Tuple of (mnemonic, private_key, public_key, derivation_path)
        """
        is_valid, message = self.bip39_manager.validate_mnemonic(mnemonic)
        if not is_valid:
            raise ValueError(f"Invalid mnemonic: {message}")
        
        seed = BIP39SeedDeriv.mnemonic_to_seed(mnemonic, passphrase)
        
        private_key, public_key, path = BIP44Derivation.derive_path(seed, asset)
        
        return mnemonic, private_key, public_key, path
