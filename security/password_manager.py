"""
Master password management using Argon2id for secure key derivation.
Implements OWASP recommendations for password-based key derivation.
"""
import os
import re
from typing import Tuple, Optional
from dataclasses import dataclass
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHash
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


@dataclass
class PasswordStrength:
    """Password strength assessment."""
    score: int
    level: str
    issues: list
    
    def is_strong(self) -> bool:
        """Check if password meets security requirements."""
        return self.score >= 3


@dataclass
class DerivedKey:
    """Key derived from master password."""
    key: bytes
    salt: bytes
    parameters: dict


class PasswordManager:
    """Manage master password with Argon2id key derivation."""
    
    MIN_PASSWORD_LENGTH = 12
    MAX_PASSWORD_LENGTH = 128
    
    ARGON2_TIME_COST = 2
    ARGON2_MEMORY_COST = 65536
    ARGON2_PARALLELISM = 4
    
    PBKDF2_ITERATIONS = 100000
    
    def __init__(self):
        """Initialize password manager."""
        self.hasher = PasswordHasher(
            time_cost=self.ARGON2_TIME_COST,
            memory_cost=self.ARGON2_MEMORY_COST,
            parallelism=self.ARGON2_PARALLELISM,
            hash_len=32,
            salt_len=16,
        )
    
    def hash_password(self, password: str) -> Tuple[str, str]:
        """
        Hash password using Argon2id.
        
        Args:
            password: Master password to hash
        
        Returns:
            Tuple of (password_hash, salt_hex)
        
        Raises:
            ValueError: If password is invalid
        """
        is_valid, message = self.validate_password(password)
        if not is_valid:
            raise ValueError(f"Invalid password: {message}")
        
        try:
            password_hash = self.hasher.hash(password)
            
            salt_bytes = os.urandom(16)
            salt_hex = salt_bytes.hex()
            
            return password_hash, salt_hex
        
        except Exception as e:
            raise ValueError(f"Password hashing failed: {str(e)}")
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """
        Verify password against stored hash.
        
        Args:
            password: Password to verify
            password_hash: Argon2id hash from hash_password()
        
        Returns:
            True if password matches
        """
        try:
            self.hasher.verify(password_hash, password)
            return True
        except (VerifyMismatchError, VerificationError, InvalidHash):
            return False
        except Exception:
            return False
    
    def derive_key(self, password: str, salt: bytes = None, 
                  key_length: int = 32) -> DerivedKey:
        """
        Derive encryption key from master password using Argon2id.
        
        Args:
            password: Master password
            salt: Optional salt (generated if not provided)
            key_length: Desired key length in bytes (default: 32 for AES-256)
        
        Returns:
            DerivedKey with key, salt, and parameters
        
        Raises:
            ValueError: If password is invalid
        """
        is_valid, message = self.validate_password(password)
        if not is_valid:
            raise ValueError(f"Invalid password: {message}")
        
        if salt is None:
            salt = os.urandom(16)
        
        try:
            derived_hash = self.hasher.hash(password)
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=key_length,
                salt=salt,
                iterations=self.PBKDF2_ITERATIONS
            )
            
            derived_key = kdf.derive(password.encode('utf-8'))
            
            return DerivedKey(
                key=derived_key,
                salt=salt,
                parameters={
                    'argon2_time_cost': self.ARGON2_TIME_COST,
                    'argon2_memory_cost': self.ARGON2_MEMORY_COST,
                    'argon2_parallelism': self.ARGON2_PARALLELISM,
                    'pbkdf2_iterations': self.PBKDF2_ITERATIONS,
                    'key_length': key_length,
                }
            )
        
        except Exception as e:
            raise ValueError(f"Key derivation failed: {str(e)}")
    
    def derive_key_from_hash(self, password_hash: str, salt: bytes,
                            key_length: int = 32) -> Optional[DerivedKey]:
        """
        Derive encryption key from existing password hash (for session unlock).
        
        Args:
            password_hash: Argon2id hash to verify against
            salt: Salt for PBKDF2
            key_length: Desired key length
        
        Returns:
            DerivedKey if successful, None otherwise
        """
        try:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=key_length,
                salt=salt,
                iterations=self.PBKDF2_ITERATIONS
            )
            
            return DerivedKey(
                key=kdf.derive(password_hash.encode('utf-8')),
                salt=salt,
                parameters={
                    'pbkdf2_iterations': self.PBKDF2_ITERATIONS,
                    'key_length': key_length,
                }
            )
        
        except Exception:
            return None
    
    @staticmethod
    def validate_password(password: str) -> Tuple[bool, str]:
        """
        Validate password strength and format.
        
        Args:
            password: Password to validate
        
        Returns:
            Tuple of (is_valid, message)
        """
        if not password or not isinstance(password, str):
            return False, "Password must be a non-empty string"
        
        if len(password) < PasswordManager.MIN_PASSWORD_LENGTH:
            return False, f"Password must be at least {PasswordManager.MIN_PASSWORD_LENGTH} characters"
        
        if len(password) > PasswordManager.MAX_PASSWORD_LENGTH:
            return False, f"Password must be at most {PasswordManager.MAX_PASSWORD_LENGTH} characters"
        
        return True, "Password is valid"
    
    @staticmethod
    def assess_strength(password: str) -> PasswordStrength:
        """
        Assess password strength.
        
        Args:
            password: Password to assess
        
        Returns:
            PasswordStrength assessment
        """
        score = 0
        issues = []
        
        if not password:
            return PasswordStrength(0, "empty", ["Password is empty"])
        
        length = len(password)
        
        if length >= 8:
            score += 1
        else:
            issues.append("Password too short (minimum 8 characters)")
        
        if length >= 12:
            score += 1
        else:
            issues.append("Password should be at least 12 characters")
        
        if length >= 16:
            score += 1
        
        if re.search(r'[a-z]', password):
            score += 1
        else:
            issues.append("Missing lowercase letters")
        
        if re.search(r'[A-Z]', password):
            score += 1
        else:
            issues.append("Missing uppercase letters")
        
        if re.search(r'[0-9]', password):
            score += 1
        else:
            issues.append("Missing numbers")
        
        if re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>?/\\|`~]', password):
            score += 1
        else:
            issues.append("Missing special characters")
        
        if not re.search(r'(.)\1{2,}', password):
            score += 1
        else:
            issues.append("Contains repeated characters")
        
        if score >= 8:
            level = "very_strong"
        elif score >= 6:
            level = "strong"
        elif score >= 4:
            level = "moderate"
        elif score >= 2:
            level = "weak"
        else:
            level = "very_weak"
        
        return PasswordStrength(score, level, issues)
    
    @staticmethod
    def constant_time_compare(a: bytes, b: bytes) -> bool:
        """
        Compare two byte strings in constant time to prevent timing attacks.
        
        Args:
            a: First byte string
            b: Second byte string
        
        Returns:
            True if equal
        """
        if len(a) != len(b):
            return False
        
        result = 0
        for x, y in zip(a, b):
            result |= x ^ y
        
        return result == 0


class PasswordHashStorage:
    """Store and retrieve password hashes securely."""
    
    def __init__(self, storage_path: str = None):
        """
        Initialize password hash storage.
        
        Args:
            storage_path: Path to store password hash (optional)
        """
        self.storage_path = storage_path
        self.password_hash = None
        self.salt = None
    
    def save_hash(self, password_hash: str, salt_hex: str) -> bool:
        """
        Save password hash and salt.
        
        Args:
            password_hash: Argon2id hash
            salt_hex: Salt as hex string
        
        Returns:
            True if successful
        """
        try:
            self.password_hash = password_hash
            self.salt = bytes.fromhex(salt_hex)
            return True
        except Exception:
            return False
    
    def load_hash(self) -> Tuple[Optional[str], Optional[bytes]]:
        """
        Load password hash and salt.
        
        Returns:
            Tuple of (password_hash, salt_bytes)
        """
        return self.password_hash, self.salt
    
    def clear(self):
        """Clear stored hash and salt."""
        self.password_hash = None
        self.salt = None
