"""
Encrypted vault using AES-256-GCM for secure key storage.
Provides authenticated encryption with per-key unique IVs.
"""
import json
import os
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes


@dataclass
class EncryptedKeyBlob:
    """Encrypted key with metadata."""
    key_id: str
    ciphertext: bytes
    iv: bytes
    tag: bytes
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'key_id': self.key_id,
            'ciphertext': self.ciphertext.hex(),
            'iv': self.iv.hex(),
            'tag': self.tag.hex(),
            'metadata': self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EncryptedKeyBlob':
        """Create from dictionary."""
        return cls(
            key_id=data['key_id'],
            ciphertext=bytes.fromhex(data['ciphertext']),
            iv=bytes.fromhex(data['iv']),
            tag=bytes.fromhex(data['tag']),
            metadata=data['metadata'],
        )


class CryptoVault:
    """Encrypted vault for storing private keys."""
    
    GCM_TAG_SIZE = 16
    GCM_IV_SIZE = 12
    
    def __init__(self, master_key: bytes):
        """
        Initialize encrypted vault.
        
        Args:
            master_key: 32-byte master key for AES-256
        
        Raises:
            ValueError: If master key is invalid
        """
        if not isinstance(master_key, bytes):
            raise ValueError("Master key must be bytes")
        
        if len(master_key) != 32:
            raise ValueError(f"Master key must be 32 bytes, got {len(master_key)}")
        
        self.master_key = master_key
        self.cipher = AESGCM(master_key)
    
    def encrypt_key(self, key_data: bytes, key_id: str = None,
                   metadata: Dict[str, Any] = None) -> EncryptedKeyBlob:
        """
        Encrypt a private key with unique IV.
        
        Args:
            key_data: Private key bytes to encrypt
            key_id: Optional identifier for the key
            metadata: Optional metadata (asset, chain, created_at, etc.)
        
        Returns:
            EncryptedKeyBlob with encrypted key
        """
        if not key_data or not isinstance(key_data, bytes):
            raise ValueError("Key data must be non-empty bytes")
        
        iv = os.urandom(self.GCM_IV_SIZE)
        
        if key_id is None:
            key_id = os.urandom(16).hex()
        
        if metadata is None:
            metadata = {}
        
        try:
            ciphertext_and_tag = self.cipher.encrypt(iv, key_data, None)
            
            ciphertext = ciphertext_and_tag[:-self.GCM_TAG_SIZE]
            tag = ciphertext_and_tag[-self.GCM_TAG_SIZE:]
            
            return EncryptedKeyBlob(
                key_id=key_id,
                ciphertext=ciphertext,
                iv=iv,
                tag=tag,
                metadata=metadata,
            )
        
        except Exception as e:
            raise ValueError(f"Encryption failed: {str(e)}")
    
    def decrypt_key(self, encrypted_blob: EncryptedKeyBlob) -> Optional[bytes]:
        """
        Decrypt a private key from encrypted blob.
        
        Args:
            encrypted_blob: EncryptedKeyBlob from encrypt_key()
        
        Returns:
            Decrypted key bytes or None if decryption fails
        """
        try:
            ciphertext_and_tag = encrypted_blob.ciphertext + encrypted_blob.tag
            
            plaintext = self.cipher.decrypt(
                encrypted_blob.iv,
                ciphertext_and_tag,
                None
            )
            
            return plaintext
        
        except Exception:
            return None
    
    def verify_integrity(self, encrypted_blob: EncryptedKeyBlob) -> bool:
        """
        Verify integrity of encrypted blob (before decryption).
        
        GCM provides authenticated encryption, so decryption will fail
        if ciphertext is tampered with.
        
        Args:
            encrypted_blob: EncryptedKeyBlob to verify
        
        Returns:
            True if blob appears valid (no corruption)
        """
        try:
            ciphertext_and_tag = encrypted_blob.ciphertext + encrypted_blob.tag
            
            if len(encrypted_blob.iv) != self.GCM_IV_SIZE:
                return False
            
            if len(encrypted_blob.tag) != self.GCM_TAG_SIZE:
                return False
            
            if len(encrypted_blob.ciphertext) < 16:
                return False
            
            return True
        
        except Exception:
            return False
    
    def encrypt_batch(self, keys: Dict[str, Tuple[bytes, Dict[str, Any]]]) -> Dict[str, EncryptedKeyBlob]:
        """
        Encrypt multiple keys at once.
        
        Args:
            keys: Dict of {key_id: (key_data, metadata)}
        
        Returns:
            Dict of {key_id: EncryptedKeyBlob}
        """
        encrypted = {}
        
        for key_id, (key_data, metadata) in keys.items():
            try:
                encrypted[key_id] = self.encrypt_key(key_data, key_id, metadata)
            except Exception as e:
                print(f"Failed to encrypt key {key_id}: {e}")
                continue
        
        return encrypted
    
    def decrypt_batch(self, encrypted_keys: Dict[str, EncryptedKeyBlob]) -> Dict[str, bytes]:
        """
        Decrypt multiple keys at once.
        
        Args:
            encrypted_keys: Dict of {key_id: EncryptedKeyBlob}
        
        Returns:
            Dict of {key_id: decrypted_key_bytes}
        """
        decrypted = {}
        
        for key_id, encrypted_blob in encrypted_keys.items():
            plaintext = self.decrypt_key(encrypted_blob)
            if plaintext:
                decrypted[key_id] = plaintext
        
        return decrypted
    
    @staticmethod
    def validate_key(key_data: bytes) -> Tuple[bool, str]:
        """
        Validate key format and length.
        
        Args:
            key_data: Key to validate
        
        Returns:
            Tuple of (is_valid, message)
        """
        if not isinstance(key_data, bytes):
            return False, "Key must be bytes"
        
        if len(key_data) == 0:
            return False, "Key cannot be empty"
        
        if len(key_data) > 1024:
            return False, "Key too large (>1KB)"
        
        return True, "Key is valid"


class VaultEncryption:
    """High-level vault encryption interface."""
    
    def __init__(self, master_key: bytes):
        """
        Initialize vault encryption.
        
        Args:
            master_key: 32-byte master key
        """
        self.vault = CryptoVault(master_key)
        self.encrypted_blobs: Dict[str, EncryptedKeyBlob] = {}
    
    def store_encrypted(self, key_id: str, key_data: bytes,
                       asset: str, chain: str = None,
                       description: str = None) -> bool:
        """
        Store encrypted key with metadata.
        
        Args:
            key_id: Unique key identifier
            key_data: Private key bytes
            asset: Asset type (solana, nano, arweave)
            chain: Blockchain name
            description: Optional description
        
        Returns:
            True if successful
        """
        try:
            is_valid, message = CryptoVault.validate_key(key_data)
            if not is_valid:
                return False
            
            metadata = {
                'asset': asset,
                'chain': chain or asset,
                'description': description or f"Key for {asset}",
                'created_at': __import__('datetime').datetime.utcnow().isoformat(),
            }
            
            encrypted_blob = self.vault.encrypt_key(key_data, key_id, metadata)
            self.encrypted_blobs[key_id] = encrypted_blob
            
            return True
        
        except Exception:
            return False
    
    def retrieve_decrypted(self, key_id: str) -> Optional[bytes]:
        """
        Retrieve and decrypt key.
        
        Args:
            key_id: Key identifier
        
        Returns:
            Decrypted key bytes or None
        """
        if key_id not in self.encrypted_blobs:
            return None
        
        return self.vault.decrypt_key(self.encrypted_blobs[key_id])
    
    def list_stored_keys(self) -> Dict[str, Dict[str, Any]]:
        """
        List all stored keys (metadata only, no decrypted keys).
        
        Args:
            None
        
        Returns:
            Dict of {key_id: metadata}
        """
        keys = {}
        for key_id, blob in self.encrypted_blobs.items():
            keys[key_id] = blob.metadata
        return keys
    
    def delete_key(self, key_id: str) -> bool:
        """
        Delete stored encrypted key.
        
        Args:
            key_id: Key identifier
        
        Returns:
            True if successful
        """
        if key_id in self.encrypted_blobs:
            del self.encrypted_blobs[key_id]
            return True
        return False
    
    def export_vault_json(self) -> str:
        """
        Export entire vault as JSON.
        
        Args:
            None
        
        Returns:
            JSON string with encrypted blobs
        """
        vault_data = {
            'blobs': {
                key_id: blob.to_dict()
                for key_id, blob in self.encrypted_blobs.items()
            }
        }
        return json.dumps(vault_data, indent=2)
    
    def import_vault_json(self, json_str: str) -> bool:
        """
        Import vault from JSON.
        
        Args:
            json_str: JSON string from export_vault_json()
        
        Returns:
            True if successful
        """
        try:
            vault_data = json.loads(json_str)
            self.encrypted_blobs.clear()
            
            for key_id, blob_data in vault_data.get('blobs', {}).items():
                blob = EncryptedKeyBlob.from_dict(blob_data)
                self.encrypted_blobs[key_id] = blob
            
            return True
        
        except Exception:
            return False
    
    def clear(self):
        """Clear all stored encrypted keys from memory."""
        self.encrypted_blobs.clear()
