"""
OS keyring integration for secure key storage.
Uses platform-specific keyrings (Windows/macOS/Linux) with fallback to encrypted storage.
"""
import os
import sys
from typing import Optional, Tuple

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False


class KeyringManager:
    """Manage keys using OS-provided keyrings with fallback."""
    
    SERVICE_NAME = "sapphire_exchange"
    
    def __init__(self, use_keyring: bool = True, fallback_password: str = None):
        """
        Initialize keyring manager.
        
        Args:
            use_keyring: Whether to use OS keyring (if available)
            fallback_password: Password for fallback encrypted storage
        """
        self.use_keyring = use_keyring and KEYRING_AVAILABLE
        self.fallback_password = fallback_password
        self.fallback_storage: dict = {}
        
        if self.use_keyring:
            self._detect_backend()
    
    def _detect_backend(self):
        """Detect and report keyring backend."""
        if KEYRING_AVAILABLE:
            backend = keyring.get_keyring()
            print(f"Keyring backend: {backend.__class__.__name__}")
    
    def get_platform(self) -> str:
        """Get current platform."""
        if sys.platform == 'darwin':
            return 'macos'
        elif sys.platform == 'win32':
            return 'windows'
        elif sys.platform.startswith('linux'):
            return 'linux'
        else:
            return 'unknown'
    
    def store_key(self, key_id: str, key_data: str) -> Tuple[bool, str]:
        """
        Store key using OS keyring or fallback.
        
        Args:
            key_id: Unique key identifier
            key_data: Key data (usually hex string)
        
        Returns:
            Tuple of (success, message)
        """
        if not key_id or not key_data:
            return False, "Key ID and data cannot be empty"
        
        if self.use_keyring:
            try:
                keyring.set_password(self.SERVICE_NAME, key_id, key_data)
                return True, f"Key stored in {self.get_platform()} keyring"
            except Exception as e:
                return False, f"Keyring storage failed: {str(e)}"
        else:
            self.fallback_storage[key_id] = key_data
            return True, "Key stored in fallback storage (encrypted file recommended)"
    
    def retrieve_key(self, key_id: str) -> Tuple[Optional[str], str]:
        """
        Retrieve key from OS keyring or fallback.
        
        Args:
            key_id: Key identifier
        
        Returns:
            Tuple of (key_data, message)
        """
        if self.use_keyring:
            try:
                key_data = keyring.get_password(self.SERVICE_NAME, key_id)
                if key_data:
                    return key_data, "Key retrieved from keyring"
                return None, "Key not found in keyring"
            except Exception as e:
                return None, f"Keyring retrieval failed: {str(e)}"
        else:
            key_data = self.fallback_storage.get(key_id)
            if key_data:
                return key_data, "Key retrieved from fallback storage"
            return None, "Key not found in fallback storage"
    
    def delete_key(self, key_id: str) -> Tuple[bool, str]:
        """
        Delete key from OS keyring or fallback.
        
        Args:
            key_id: Key identifier
        
        Returns:
            Tuple of (success, message)
        """
        if self.use_keyring:
            try:
                keyring.delete_password(self.SERVICE_NAME, key_id)
                return True, "Key deleted from keyring"
            except keyring.errors.PasswordDeleteError:
                return False, "Key not found in keyring"
            except Exception as e:
                return False, f"Keyring deletion failed: {str(e)}"
        else:
            if key_id in self.fallback_storage:
                del self.fallback_storage[key_id]
                return True, "Key deleted from fallback storage"
            return False, "Key not found in fallback storage"
    
    def list_keys(self) -> list:
        """
        List all stored key IDs.
        
        Returns:
            List of key IDs
        """
        if self.use_keyring:
            try:
                import keyring.backends.osx_keychain as osx
                import keyring.backends.fail as fail_backend
                
                if isinstance(keyring.get_keyring(), fail_backend.Keyring):
                    return []
                
                return list(self.fallback_storage.keys())
            except Exception:
                return list(self.fallback_storage.keys())
        else:
            return list(self.fallback_storage.keys())
    
    def is_available(self) -> bool:
        """Check if keyring is available and working."""
        return self.use_keyring
    
    def test_keyring(self) -> Tuple[bool, str]:
        """
        Test keyring functionality.
        
        Returns:
            Tuple of (works, message)
        """
        if not self.use_keyring:
            return False, "Keyring not available on this system"
        
        try:
            test_key = f"test_{os.urandom(4).hex()}"
            test_data = "test_data"
            
            success, msg = self.store_key(test_key, test_data)
            if not success:
                return False, f"Store test failed: {msg}"
            
            retrieved, msg = self.retrieve_key(test_key)
            if retrieved != test_data:
                return False, f"Retrieve test failed: expected {test_data}, got {retrieved}"
            
            success, msg = self.delete_key(test_key)
            if not success:
                return False, f"Delete test failed: {msg}"
            
            return True, "Keyring test successful"
        
        except Exception as e:
            return False, f"Keyring test error: {str(e)}"


class KeyringFallback:
    """Fallback key storage with encryption."""
    
    def __init__(self, encrypted_storage_path: str = None):
        """
        Initialize keyring fallback.
        
        Args:
            encrypted_storage_path: Path to encrypted key storage
        """
        self.encrypted_storage_path = encrypted_storage_path or "keys.enc"
        self.keys_in_memory: dict = {}
    
    def store_encrypted(self, key_id: str, key_data: str, 
                       encryption_key: bytes) -> bool:
        """
        Store key with encryption.
        
        Args:
            key_id: Key identifier
            key_data: Key data
            encryption_key: Encryption key bytes
        
        Returns:
            True if successful
        """
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            import json
            import os
            
            iv = os.urandom(12)
            cipher = AESGCM(encryption_key)
            ciphertext = cipher.encrypt(iv, key_data.encode('utf-8'), None)
            
            self.keys_in_memory[key_id] = {
                'iv': iv.hex(),
                'ciphertext': ciphertext.hex(),
            }
            
            return True
        
        except Exception:
            return False
    
    def retrieve_encrypted(self, key_id: str, encryption_key: bytes) -> Optional[str]:
        """
        Retrieve encrypted key.
        
        Args:
            key_id: Key identifier
            encryption_key: Encryption key bytes
        
        Returns:
            Decrypted key data or None
        """
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            
            if key_id not in self.keys_in_memory:
                return None
            
            key_blob = self.keys_in_memory[key_id]
            
            iv = bytes.fromhex(key_blob['iv'])
            ciphertext = bytes.fromhex(key_blob['ciphertext'])
            
            cipher = AESGCM(encryption_key)
            plaintext = cipher.decrypt(iv, ciphertext, None)
            
            return plaintext.decode('utf-8')
        
        except Exception:
            return None
    
    def clear(self):
        """Clear all keys from memory."""
        self.keys_in_memory.clear()
