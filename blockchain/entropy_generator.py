"""
Cryptographically secure entropy generation and validation for wallet creation.
Uses OS-provided CSPRNG with quality validation.
"""
import os
import secrets
from typing import Tuple, Optional
from dataclasses import dataclass


@dataclass
class EntropyQuality:
    """Entropy quality assessment result."""
    bits: int
    byte_length: int
    is_valid: bool
    message: str


class EntropyGenerator:
    """Generate and validate cryptographically secure entropy for wallet keys."""
    
    MIN_ENTROPY_BITS = 128
    RECOMMENDED_ENTROPY_BITS = 256
    
    ENTROPY_BIT_SIZES = {
        12: 128,
        15: 160,
        18: 192,
        21: 224,
        24: 256
    }
    
    def __init__(self):
        """Initialize entropy generator."""
        self.generated_entropy = None
    
    def generate_entropy(self, num_words: int = 24) -> bytes:
        """
        Generate cryptographically secure entropy.
        
        Args:
            num_words: BIP39 word count (12, 15, 18, 21, or 24)
        
        Returns:
            Entropy bytes
        
        Raises:
            ValueError: If num_words is invalid
        """
        if num_words not in self.ENTROPY_BIT_SIZES:
            raise ValueError(
                f"Invalid word count: {num_words}. "
                f"Must be one of {list(self.ENTROPY_BIT_SIZES.keys())}"
            )
        
        bit_length = self.ENTROPY_BIT_SIZES[num_words]
        byte_length = bit_length // 8
        
        entropy = secrets.token_bytes(byte_length)
        self.generated_entropy = entropy
        
        return entropy
    
    def generate_for_bits(self, bits: int) -> bytes:
        """
        Generate entropy for specified bit length.
        
        Args:
            bits: Number of entropy bits (must be multiple of 8)
        
        Returns:
            Entropy bytes
        
        Raises:
            ValueError: If bits is not valid
        """
        if bits % 8 != 0:
            raise ValueError(f"Bits must be multiple of 8, got {bits}")
        
        if bits < self.MIN_ENTROPY_BITS:
            raise ValueError(
                f"Bits must be >= {self.MIN_ENTROPY_BITS}, got {bits}"
            )
        
        byte_length = bits // 8
        entropy = secrets.token_bytes(byte_length)
        self.generated_entropy = entropy
        
        return entropy
    
    def validate_entropy(self, entropy: bytes) -> EntropyQuality:
        """
        Validate entropy for quality and security.
        
        Args:
            entropy: Entropy bytes to validate
        
        Returns:
            EntropyQuality assessment
        """
        byte_length = len(entropy)
        bit_length = byte_length * 8
        
        if byte_length == 0:
            return EntropyQuality(
                bits=0,
                byte_length=0,
                is_valid=False,
                message="Entropy is empty"
            )
        
        if bit_length < self.MIN_ENTROPY_BITS:
            return EntropyQuality(
                bits=bit_length,
                byte_length=byte_length,
                is_valid=False,
                message=f"Entropy too short: {bit_length} bits < {self.MIN_ENTROPY_BITS} bits minimum"
            )
        
        if not self._has_sufficient_randomness(entropy):
            return EntropyQuality(
                bits=bit_length,
                byte_length=byte_length,
                is_valid=False,
                message="Entropy randomness check failed"
            )
        
        return EntropyQuality(
            bits=bit_length,
            byte_length=byte_length,
            is_valid=True,
            message="Entropy quality is acceptable"
        )
    
    def _has_sufficient_randomness(self, entropy: bytes) -> bool:
        """
        Check if entropy has sufficient randomness.
        Prevents low-entropy sequences like all zeros or repeated patterns.
        
        Args:
            entropy: Entropy bytes to check
        
        Returns:
            True if randomness check passes
        """
        if len(entropy) < 8:
            return True
        
        unique_bytes = len(set(entropy))
        min_unique = max(len(entropy) // 4, 4)
        
        if unique_bytes < min_unique:
            return False
        
        for i in range(0, len(entropy) - 1):
            if entropy[i] == entropy[i + 1]:
                consecutive_same = 1
                for j in range(i + 2, len(entropy)):
                    if entropy[j] == entropy[i]:
                        consecutive_same += 1
                    else:
                        break
                
                if consecutive_same > len(entropy) // 8:
                    return False
        
        return True
    
    def get_entropy_quality(self, entropy: bytes) -> EntropyQuality:
        """
        Get detailed entropy quality assessment.
        
        Args:
            entropy: Entropy bytes to assess
        
        Returns:
            EntropyQuality with detailed assessment
        """
        return self.validate_entropy(entropy)
    
    def check_system_entropy(self) -> Tuple[bool, str]:
        """
        Check system entropy pool availability (Linux/Unix).
        
        Returns:
            Tuple of (is_available, message)
        """
        try:
            if not hasattr(os, 'urandom'):
                return False, "os.urandom not available"
            
            test_entropy = os.urandom(16)
            if len(test_entropy) != 16:
                return False, "os.urandom returned insufficient bytes"
            
            linux_entropy_path = '/proc/sys/kernel/random/entropy_avail'
            if os.path.exists(linux_entropy_path):
                try:
                    with open(linux_entropy_path, 'r') as f:
                        entropy_available = int(f.read().strip())
                        if entropy_available < 256:
                            return True, f"Warning: Low entropy pool ({entropy_available} bits)"
                except (OSError, ValueError):
                    pass
            
            return True, "System entropy pool is available"
        
        except Exception as e:
            return False, f"Entropy check failed: {str(e)}"
    
    def clear_entropy(self):
        """Clear stored entropy from memory."""
        if self.generated_entropy:
            self.generated_entropy = bytes(len(self.generated_entropy))
            self.generated_entropy = None
    
    def derive_entropy_for_mnemonic(self, num_words: int = 24) -> bytes:
        """
        Generate entropy suitable for BIP39 mnemonic.
        
        Args:
            num_words: BIP39 word count
        
        Returns:
            Entropy bytes of correct length for mnemonic
        """
        entropy = self.generate_entropy(num_words)
        quality = self.validate_entropy(entropy)
        
        if not quality.is_valid:
            raise ValueError(f"Entropy validation failed: {quality.message}")
        
        return entropy
    
    def __del__(self):
        """Cleanup on object destruction."""
        self.clear_entropy()


class SecureRandomGenerator:
    """Additional secure random utilities."""
    
    @staticmethod
    def generate_seed(length: int = 32) -> bytes:
        """
        Generate secure random seed.
        
        Args:
            length: Seed length in bytes
        
        Returns:
            Random seed bytes
        """
        return secrets.token_bytes(length)
    
    @staticmethod
    def generate_salt(length: int = 16) -> bytes:
        """
        Generate secure random salt for KDF.
        
        Args:
            length: Salt length in bytes
        
        Returns:
            Random salt bytes
        """
        return secrets.token_bytes(length)
    
    @staticmethod
    def generate_iv(length: int = 12) -> bytes:
        """
        Generate secure random IV for GCM mode.
        
        Args:
            length: IV length in bytes (12 recommended for GCM)
        
        Returns:
            Random IV bytes
        """
        if length != 12 and length != 16:
            raise ValueError("IV length should be 12 (recommended) or 16 bytes")
        return secrets.token_bytes(length)
    
    @staticmethod
    def generate_nonce(length: int = 24) -> bytes:
        """
        Generate secure random nonce.
        
        Args:
            length: Nonce length in bytes
        
        Returns:
            Random nonce bytes
        """
        return secrets.token_bytes(length)
