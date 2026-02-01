"""
Secure local key storage with encryption and persistent storage.
Stores encrypted keys with metadata for asset and chain management.
"""
import json
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime

from security.vault_encryption import VaultEncryption, EncryptedKeyBlob


@dataclass
class StoredKeyInfo:
    """Metadata about a stored encrypted key."""
    key_id: str
    asset: str
    chain: str
    public_key: str
    address: str
    created_at: str
    updated_at: str
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class SecureKeyStorage:
    """Persistent storage for encrypted keys."""
    
    DEFAULT_STORAGE_DIR = "~/.sapphire_exchange"
    VAULT_FILE = "vault.enc"
    METADATA_FILE = "vault.meta"
    
    def __init__(self, vault_encryption: VaultEncryption, 
                 storage_dir: str = None):
        """
        Initialize key storage.
        
        Args:
            vault_encryption: VaultEncryption instance
            storage_dir: Directory for storing encrypted vault (default: ~/.sapphire_exchange)
        """
        self.vault_encryption = vault_encryption
        self.storage_dir = Path(storage_dir or self.DEFAULT_STORAGE_DIR).expanduser()
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.vault_file = self.storage_dir / self.VAULT_FILE
        self.metadata_file = self.storage_dir / self.METADATA_FILE
        
        self.key_metadata: Dict[str, StoredKeyInfo] = {}
        self._load_metadata()
    
    def store_key(self, key_id: str, key_data: bytes, public_key: str,
                 address: str, asset: str, chain: str = None,
                 description: str = None) -> bool:
        """
        Store encrypted key with metadata.
        
        Args:
            key_id: Unique key identifier
            key_data: Private key bytes
            public_key: Public key hex string
            address: Address on blockchain
            asset: Asset type (solana, nano, arweave)
            chain: Blockchain name
            description: Optional description
        
        Returns:
            True if successful
        """
        try:
            if chain is None:
                chain = asset
            
            now = datetime.utcnow().isoformat()
            
            self.vault_encryption.store_encrypted(
                key_id, key_data, asset, chain, description
            )
            
            self.key_metadata[key_id] = StoredKeyInfo(
                key_id=key_id,
                asset=asset,
                chain=chain,
                public_key=public_key,
                address=address,
                created_at=now,
                updated_at=now,
                description=description or f"Key for {asset}",
            )
            
            return True
        
        except Exception:
            return False
    
    def retrieve_key(self, key_id: str) -> Optional[bytes]:
        """
        Retrieve and decrypt key.
        
        Args:
            key_id: Key identifier
        
        Returns:
            Decrypted key bytes or None
        """
        return self.vault_encryption.retrieve_decrypted(key_id)
    
    def get_key_info(self, key_id: str) -> Optional[StoredKeyInfo]:
        """
        Get metadata about stored key.
        
        Args:
            key_id: Key identifier
        
        Returns:
            StoredKeyInfo or None
        """
        return self.key_metadata.get(key_id)
    
    def list_keys(self, asset: str = None) -> Dict[str, StoredKeyInfo]:
        """
        List stored keys.
        
        Args:
            asset: Optional filter by asset type
        
        Returns:
            Dict of {key_id: StoredKeyInfo}
        """
        if asset is None:
            return self.key_metadata.copy()
        
        return {
            key_id: info
            for key_id, info in self.key_metadata.items()
            if info.asset == asset
        }
    
    def delete_key(self, key_id: str) -> bool:
        """
        Delete encrypted key.
        
        Args:
            key_id: Key identifier
        
        Returns:
            True if successful
        """
        try:
            if self.vault_encryption.delete_key(key_id):
                if key_id in self.key_metadata:
                    del self.key_metadata[key_id]
                return True
            return False
        except Exception:
            return False
    
    def save_vault(self) -> bool:
        """
        Save encrypted vault to disk.
        
        Returns:
            True if successful
        """
        try:
            vault_json = self.vault_encryption.export_vault_json()
            
            self.vault_file.write_text(vault_json, encoding='utf-8')
            
            self._save_metadata()
            
            return True
        
        except Exception:
            return False
    
    def load_vault(self) -> bool:
        """
        Load encrypted vault from disk.
        
        Returns:
            True if successful
        """
        try:
            if not self.vault_file.exists():
                return False
            
            vault_json = self.vault_file.read_text(encoding='utf-8')
            
            if not self.vault_encryption.import_vault_json(vault_json):
                return False
            
            self._load_metadata()
            
            return True
        
        except Exception:
            return False
    
    def _save_metadata(self) -> bool:
        """Save key metadata."""
        try:
            metadata = {
                'keys': {
                    key_id: {
                        'asset': info.asset,
                        'chain': info.chain,
                        'address': info.address,
                        'public_key': info.public_key,
                        'created_at': info.created_at,
                        'updated_at': info.updated_at,
                        'description': info.description,
                    }
                    for key_id, info in self.key_metadata.items()
                }
            }
            
            self.metadata_file.write_text(
                json.dumps(metadata, indent=2),
                encoding='utf-8'
            )
            
            return True
        
        except Exception:
            return False
    
    def _load_metadata(self):
        """Load key metadata."""
        try:
            if not self.metadata_file.exists():
                self.key_metadata = {}
                return
            
            metadata = json.loads(self.metadata_file.read_text(encoding='utf-8'))
            
            self.key_metadata = {
                key_id: StoredKeyInfo(
                    key_id=key_id,
                    asset=info['asset'],
                    chain=info['chain'],
                    address=info['address'],
                    public_key=info['public_key'],
                    created_at=info['created_at'],
                    updated_at=info['updated_at'],
                    description=info.get('description', ''),
                )
                for key_id, info in metadata.get('keys', {}).items()
            }
        
        except Exception:
            self.key_metadata = {}
    
    def get_key_by_address(self, address: str) -> Optional[StoredKeyInfo]:
        """
        Get key by blockchain address.
        
        Args:
            address: Blockchain address
        
        Returns:
            StoredKeyInfo or None
        """
        for info in self.key_metadata.values():
            if info.address == address:
                return info
        return None
    
    def get_keys_by_asset(self, asset: str) -> List[StoredKeyInfo]:
        """
        Get all keys for specific asset.
        
        Args:
            asset: Asset type
        
        Returns:
            List of StoredKeyInfo
        """
        return [
            info for info in self.key_metadata.values()
            if info.asset == asset
        ]
    
    def update_key_metadata(self, key_id: str, **kwargs) -> bool:
        """
        Update key metadata.
        
        Args:
            key_id: Key identifier
            **kwargs: Fields to update
        
        Returns:
            True if successful
        """
        if key_id not in self.key_metadata:
            return False
        
        info = self.key_metadata[key_id]
        
        if 'description' in kwargs:
            info.description = kwargs['description']
        
        if 'metadata' in kwargs:
            info.metadata.update(kwargs['metadata'])
        
        info.updated_at = datetime.utcnow().isoformat()
        
        return True
    
    def export_public_keys(self, asset: str = None) -> Dict[str, Dict[str, str]]:
        """
        Export public keys and addresses (safe for backup).
        
        Args:
            asset: Optional filter by asset
        
        Returns:
            Dict of {key_id: {public_key, address, chain}}
        """
        keys = {}
        
        for key_id, info in self.list_keys(asset).items():
            keys[key_id] = {
                'public_key': info.public_key,
                'address': info.address,
                'chain': info.chain,
                'asset': info.asset,
            }
        
        return keys
    
    def clear(self):
        """Clear all keys from memory."""
        self.vault_encryption.clear()
        self.key_metadata.clear()
    
    def get_storage_path(self) -> str:
        """Get storage directory path."""
        return str(self.storage_dir)
    
    def get_vault_size(self) -> int:
        """Get vault file size in bytes."""
        if self.vault_file.exists():
            return self.vault_file.stat().st_size
        return 0
