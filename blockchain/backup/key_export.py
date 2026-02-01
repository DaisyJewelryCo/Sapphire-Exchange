"""
Encrypted key export and import for wallet backup.
Allows exporting private keys in encrypted password-protected files.
"""
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import json
import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend


@dataclass
class ExportedKey:
    """Exported encrypted key data."""
    key_id: str
    asset: str
    chain: str
    address: str
    public_key: str
    ciphertext: str
    iv: str
    tag: str
    salt: str
    algorithm: str = "PBKDF2-AESGCM-256"
    version: str = "1.0"
    timestamp: str = ""
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        if self.metadata is None:
            data['metadata'] = {}
        return data
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExportedKey':
        """Create from dictionary."""
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ExportedKey':
        """Create from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


class KeyExporter:
    """Export and import encrypted private keys."""
    
    ITERATIONS = 480000
    KEY_SIZE = 32
    IV_SIZE = 12
    TAG_SIZE = 16
    SALT_SIZE = 16
    
    def __init__(self):
        """Initialize key exporter."""
        pass
    
    async def export_encrypted(self, private_key: bytes,
                              public_key: str,
                              address: str,
                              asset: str,
                              chain: str,
                              password: str,
                              key_id: str = None,
                              metadata: Dict[str, Any] = None) -> Tuple[bool, Optional[ExportedKey]]:
        """
        Export private key encrypted with password.
        
        Args:
            private_key: Private key bytes
            public_key: Public key hex string
            address: Blockchain address
            asset: Asset type
            chain: Blockchain name
            password: Export password
            key_id: Optional key identifier
            metadata: Optional metadata dictionary
        
        Returns:
            Tuple of (success, ExportedKey)
        """
        try:
            if not password or len(password) < 8:
                return False, None
            
            if not private_key or not isinstance(private_key, bytes):
                return False, None
            
            if key_id is None:
                key_id = os.urandom(16).hex()
            
            salt = os.urandom(self.SALT_SIZE)
            iv = os.urandom(self.IV_SIZE)
            
            derived_key = self._derive_key(password, salt)
            
            cipher = AESGCM(derived_key)
            ciphertext_and_tag = cipher.encrypt(iv, private_key, None)
            
            ciphertext = ciphertext_and_tag[:-self.TAG_SIZE]
            tag = ciphertext_and_tag[-self.TAG_SIZE:]
            
            exported_key = ExportedKey(
                key_id=key_id,
                asset=asset,
                chain=chain,
                address=address,
                public_key=public_key,
                ciphertext=ciphertext.hex(),
                iv=iv.hex(),
                tag=tag.hex(),
                salt=salt.hex(),
                timestamp=datetime.utcnow().isoformat(),
                metadata=metadata or {},
            )
            
            return True, exported_key
        
        except Exception as e:
            return False, None
    
    async def import_encrypted(self, exported_key: ExportedKey,
                              password: str) -> Tuple[bool, Optional[bytes]]:
        """
        Import and decrypt private key from exported data.
        
        Args:
            exported_key: ExportedKey instance
            password: Import password
        
        Returns:
            Tuple of (success, private_key_bytes)
        """
        try:
            if not password:
                return False, None
            
            salt = bytes.fromhex(exported_key.salt)
            iv = bytes.fromhex(exported_key.iv)
            ciphertext = bytes.fromhex(exported_key.ciphertext)
            tag = bytes.fromhex(exported_key.tag)
            
            derived_key = self._derive_key(password, salt)
            
            cipher = AESGCM(derived_key)
            ciphertext_and_tag = ciphertext + tag
            
            private_key = cipher.decrypt(iv, ciphertext_and_tag, None)
            
            return True, private_key
        
        except Exception as e:
            return False, None
    
    async def verify_import(self, exported_key: ExportedKey,
                           password: str,
                           expected_public_key: str) -> Tuple[bool, str]:
        """
        Verify imported key matches expected public key.
        
        Args:
            exported_key: ExportedKey instance
            password: Import password
            expected_public_key: Expected public key to verify against
        
        Returns:
            Tuple of (verified, message)
        """
        try:
            success, private_key = await self.import_encrypted(exported_key, password)
            if not success or not private_key:
                return False, "Failed to decrypt key"
            
            if exported_key.public_key != expected_public_key:
                return False, "Imported public key does not match expected key"
            
            return True, "Import verified successfully"
        
        except Exception as e:
            return False, f"Verification failed: {str(e)}"
    
    async def batch_export(self, keys: Dict[str, Tuple[bytes, str, str]],
                          assets: Dict[str, str],
                          password: str) -> Tuple[bool, Optional[Dict[str, ExportedKey]]]:
        """
        Export multiple keys at once.
        
        Args:
            keys: Dictionary of {key_id: (private_key, public_key, address)}
            assets: Dictionary of {key_id: asset} mappings
            password: Export password
        
        Returns:
            Tuple of (success, dictionary of ExportedKeys)
        """
        try:
            exported_keys = {}
            
            for key_id, (private_key, public_key, address) in keys.items():
                asset = assets.get(key_id, "unknown")
                chain = asset
                
                success, exported_key = await self.export_encrypted(
                    private_key=private_key,
                    public_key=public_key,
                    address=address,
                    asset=asset,
                    chain=chain,
                    password=password,
                    key_id=key_id,
                )
                
                if success:
                    exported_keys[key_id] = exported_key
            
            return len(exported_keys) > 0, exported_keys if exported_keys else None
        
        except Exception as e:
            return False, None
    
    async def batch_import(self, exported_keys: Dict[str, ExportedKey],
                          password: str) -> Tuple[bool, Optional[Dict[str, bytes]]]:
        """
        Import multiple keys at once.
        
        Args:
            exported_keys: Dictionary of {key_id: ExportedKey}
            password: Import password
        
        Returns:
            Tuple of (success, dictionary of {key_id: private_key})
        """
        try:
            imported_keys = {}
            
            for key_id, exported_key in exported_keys.items():
                success, private_key = await self.import_encrypted(exported_key, password)
                
                if success and private_key:
                    imported_keys[key_id] = private_key
            
            return len(imported_keys) > 0, imported_keys if imported_keys else None
        
        except Exception as e:
            return False, None
    
    def export_collection_to_json(self, exported_keys: Dict[str, ExportedKey]) -> str:
        """
        Export collection of keys to JSON.
        
        Args:
            exported_keys: Dictionary of {key_id: ExportedKey}
        
        Returns:
            JSON string
        """
        data = {
            "version": "1.0",
            "export_date": datetime.utcnow().isoformat(),
            "key_count": len(exported_keys),
            "keys": {key_id: key.to_dict() for key_id, key in exported_keys.items()},
        }
        return json.dumps(data, indent=2)
    
    def import_collection_from_json(self, json_str: str) -> Dict[str, ExportedKey]:
        """
        Import collection of keys from JSON.
        
        Args:
            json_str: JSON string
        
        Returns:
            Dictionary of {key_id: ExportedKey}
        """
        data = json.loads(json_str)
        exported_keys = {}
        
        for key_id, key_data in data.get("keys", {}).items():
            exported_keys[key_id] = ExportedKey.from_dict(key_data)
        
        return exported_keys
    
    @staticmethod
    def _derive_key(password: str, salt: bytes) -> bytes:
        """
        Derive encryption key from password using PBKDF2.
        
        Args:
            password: Password string
            salt: Salt bytes
        
        Returns:
            Derived key bytes (32 bytes for AES-256)
        """
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=KeyExporter.ITERATIONS,
            backend=default_backend(),
        )
        return kdf.derive(password.encode('utf-8'))
    
    @staticmethod
    def validate_export_format(exported_key: ExportedKey) -> Tuple[bool, str]:
        """
        Validate exported key format.
        
        Args:
            exported_key: ExportedKey to validate
        
        Returns:
            Tuple of (is_valid, message)
        """
        if not exported_key.key_id:
            return False, "Missing key_id"
        
        if not exported_key.asset:
            return False, "Missing asset"
        
        if not exported_key.address:
            return False, "Missing address"
        
        if not exported_key.public_key:
            return False, "Missing public_key"
        
        required_fields = ["ciphertext", "iv", "tag", "salt"]
        for field in required_fields:
            if not getattr(exported_key, field, None):
                return False, f"Missing {field}"
        
        return True, "Valid export format"
