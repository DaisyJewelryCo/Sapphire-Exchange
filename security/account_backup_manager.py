"""
Account Backup Manager for Sapphire Exchange.
Encrypts account data using Nano mnemonic-derived keys.
Enables account recovery by providing the Nano mnemonic on re-login.
"""
import json
import hashlib
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import os


class AccountBackupManager:
    """Manage encrypted account backups indexed by Nano address."""
    
    DEFAULT_BACKUP_DIR = "~/.sapphire_exchange/account_backups"
    BACKUP_EXTENSION = ".account.enc"
    METADATA_EXTENSION = ".account.meta"
    
    GCM_TAG_SIZE = 16
    GCM_IV_SIZE = 12
    PBKDF2_ITERATIONS = 100000
    SALT = b"sapphire_exchange_account_backup"
    
    def __init__(self, backup_dir: str = None):
        """
        Initialize account backup manager.
        
        Args:
            backup_dir: Directory for account backups
        """
        self.backup_dir = Path(backup_dir or self.DEFAULT_BACKUP_DIR).expanduser()
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def derive_key_from_mnemonic(mnemonic: str) -> bytes:
        """
        Derive 32-byte AES-256 key from Nano mnemonic using PBKDF2-HMAC-SHA256.
        
        Args:
            mnemonic: BIP39 Nano mnemonic phrase
        
        Returns:
            32-byte encryption key
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=AccountBackupManager.SALT,
            iterations=AccountBackupManager.PBKDF2_ITERATIONS,
        )
        return kdf.derive(mnemonic.encode())
    
    def encrypt_account_data(self, account_data: Dict[str, Any], 
                            mnemonic: str) -> Tuple[bytes, bytes, bytes]:
        """
        Encrypt account data with mnemonic-derived key.
        
        Args:
            account_data: Account data to encrypt (dict)
            mnemonic: Nano mnemonic (used to derive key)
        
        Returns:
            Tuple of (ciphertext, iv, tag)
        """
        try:
            # Derive encryption key from mnemonic
            master_key = self.derive_key_from_mnemonic(mnemonic)
            cipher = AESGCM(master_key)
            
            # Generate random IV
            iv = os.urandom(self.GCM_IV_SIZE)
            
            # Serialize account data
            plaintext = json.dumps(account_data).encode('utf-8')
            
            # Encrypt with GCM (includes authentication)
            ciphertext_and_tag = cipher.encrypt(iv, plaintext, None)
            
            # Split ciphertext and tag
            ciphertext = ciphertext_and_tag[:-self.GCM_TAG_SIZE]
            tag = ciphertext_and_tag[-self.GCM_TAG_SIZE:]
            
            return ciphertext, iv, tag
        
        except Exception as e:
            raise ValueError(f"Encryption failed: {str(e)}")
    
    def decrypt_account_data(self, ciphertext: bytes, iv: bytes, 
                            tag: bytes, mnemonic: str) -> Optional[Dict[str, Any]]:
        """
        Decrypt account data with mnemonic-derived key.
        
        Args:
            ciphertext: Encrypted account data
            iv: Initialization vector
            tag: Authentication tag
            mnemonic: Nano mnemonic (used to derive key)
        
        Returns:
            Decrypted account data or None if decryption fails
        """
        try:
            # Derive encryption key from mnemonic
            master_key = self.derive_key_from_mnemonic(mnemonic)
            cipher = AESGCM(master_key)
            
            # Combine ciphertext and tag
            ciphertext_and_tag = ciphertext + tag
            
            # Decrypt
            plaintext = cipher.decrypt(iv, ciphertext_and_tag, None)
            
            # Deserialize
            return json.loads(plaintext.decode('utf-8'))
        
        except Exception as e:
            print(f"Decryption failed: {str(e)}")
            return None
    
    async def create_account_backup(self, user: Any, nano_address: str, 
                                   mnemonic: str, wallet_data: Dict[str, Any],
                                   private_keys: Optional[Dict[str, str]] = None,
                                   arweave_tx_id: Optional[str] = None) -> Tuple[bool, str]:
        """
        Create encrypted backup of user account including private keys.
        Backup is indexed by Nano address for easy retrieval during recovery.
        
        Args:
            user: User object with account data
            nano_address: User's Nano address (used as backup key)
            mnemonic: Nano mnemonic (used to encrypt backup)
            wallet_data: Wallet information for all blockchains
            private_keys: Dict of private keys by chain (nano, arweave, usdc, dogecoin)
            arweave_tx_id: Optional Arweave profile URI
        
        Returns:
            Tuple of (success, backup_path or error_message)
        """
        try:
            # Prepare account data for backup
            account_data = {
                'user_id': user.id,
                'username': user.username,
                'nano_address': nano_address,
                'arweave_address': user.arweave_address,
                'usdc_address': getattr(user, 'usdc_address', None),
                'email': user.email,
                'reputation_score': user.reputation_score,
                'total_sales': user.total_sales,
                'total_purchases': user.total_purchases,
                'bio': user.bio,
                'location': user.location,
                'website': user.website,
                'avatar_url': user.avatar_url,
                'preferences': user.preferences,
                'inventory': user.inventory,
                'metadata': user.metadata,
                'arweave_profile_uri': arweave_tx_id or user.arweave_profile_uri,
                'wallets': wallet_data,
                'private_keys': private_keys or {},
                'created_at': user.created_at,
                'updated_at': datetime.utcnow().isoformat(),
            }
            
            # Encrypt account data
            ciphertext, iv, tag = self.encrypt_account_data(account_data, mnemonic)
            
            # Use Nano address as filename (sanitize for filesystem)
            backup_name = nano_address.replace("nano_", "").lower()
            backup_path = self.backup_dir / f"{backup_name}{self.BACKUP_EXTENSION}"
            
            # Save encrypted backup
            backup_blob = {
                'nano_address': nano_address,
                'ciphertext': ciphertext.hex(),
                'iv': iv.hex(),
                'tag': tag.hex(),
            }
            
            backup_path.write_text(json.dumps(backup_blob), encoding='utf-8')
            
            # Create metadata file
            metadata = {
                'nano_address': nano_address,
                'user_id': user.id,
                'username': user.username,
                'created_at': datetime.utcnow().isoformat(),
                'backup_version': '1.0',
                'encrypted': True,
                'backup_hash': hashlib.sha256(ciphertext).hexdigest(),
            }
            
            metadata_path = self.backup_dir / f"{backup_name}{self.METADATA_EXTENSION}"
            metadata_path.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
            
            return True, str(backup_path)
        
        except Exception as e:
            return False, f"Backup creation failed: {str(e)}"
    
    async def restore_account_from_backup(self, nano_address: str, 
                                         mnemonic: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Restore account backup using Nano address and mnemonic.
        
        Args:
            nano_address: User's Nano address (backup key)
            mnemonic: Nano mnemonic (used to decrypt backup)
        
        Returns:
            Tuple of (success, account_data or None)
        """
        try:
            # Find backup by Nano address
            backup_name = nano_address.replace("nano_", "").lower()
            backup_path = self.backup_dir / f"{backup_name}{self.BACKUP_EXTENSION}"
            
            if not backup_path.exists():
                return False, None
            
            # Load encrypted backup
            backup_blob = json.loads(backup_path.read_text(encoding='utf-8'))
            
            ciphertext = bytes.fromhex(backup_blob['ciphertext'])
            iv = bytes.fromhex(backup_blob['iv'])
            tag = bytes.fromhex(backup_blob['tag'])
            
            # Decrypt account data
            account_data = self.decrypt_account_data(ciphertext, iv, tag, mnemonic)
            
            if account_data is None:
                return False, None
            
            # Verify Nano address matches
            if account_data.get('nano_address') != nano_address:
                return False, None
            
            return True, account_data
        
        except Exception as e:
            print(f"Backup restoration failed: {str(e)}")
            return False, None
    
    async def verify_backup(self, nano_address: str) -> Tuple[bool, str]:
        """
        Verify backup exists and is accessible.
        
        Args:
            nano_address: User's Nano address
        
        Returns:
            Tuple of (is_valid, message)
        """
        try:
            backup_name = nano_address.replace("nano_", "").lower()
            backup_path = self.backup_dir / f"{backup_name}{self.BACKUP_EXTENSION}"
            metadata_path = self.backup_dir / f"{backup_name}{self.METADATA_EXTENSION}"
            
            if not backup_path.exists():
                return False, "Backup not found"
            
            if not metadata_path.exists():
                return False, "Backup metadata not found"
            
            # Verify backup file is valid JSON
            try:
                json.loads(backup_path.read_text(encoding='utf-8'))
            except json.JSONDecodeError:
                return False, "Backup file corrupted"
            
            return True, "Backup is valid"
        
        except Exception as e:
            return False, f"Verification failed: {str(e)}"
    
    async def export_backup_to_file(self, nano_address: str, 
                                   export_path: str) -> Tuple[bool, str]:
        """
        Export encrypted backup to external file for offline storage.
        
        Args:
            nano_address: User's Nano address
            export_path: Destination path for export
        
        Returns:
            Tuple of (success, message)
        """
        try:
            backup_name = nano_address.replace("nano_", "").lower()
            backup_path = self.backup_dir / f"{backup_name}{self.BACKUP_EXTENSION}"
            
            if not backup_path.exists():
                return False, "Backup not found"
            
            export_full_path = Path(export_path)
            export_full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy backup file
            backup_content = backup_path.read_text(encoding='utf-8')
            export_full_path.write_text(backup_content, encoding='utf-8')
            
            # Also export metadata
            metadata_path = self.backup_dir / f"{backup_name}{self.METADATA_EXTENSION}"
            if metadata_path.exists():
                metadata_content = metadata_path.read_text(encoding='utf-8')
                metadata_export = export_full_path.parent / f"{export_full_path.stem}.meta"
                metadata_export.write_text(metadata_content, encoding='utf-8')
            
            return True, f"Backup exported to {export_path}"
        
        except Exception as e:
            return False, f"Export failed: {str(e)}"
    
    async def import_backup_from_file(self, import_path: str, 
                                     mnemonic: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Import backup from external file and decrypt.
        
        Args:
            import_path: Path to backup file
            mnemonic: Nano mnemonic (used to decrypt)
        
        Returns:
            Tuple of (success, account_data or None)
        """
        try:
            import_full_path = Path(import_path)
            
            if not import_full_path.exists():
                return False, None
            
            # Load encrypted backup
            backup_blob = json.loads(import_full_path.read_text(encoding='utf-8'))
            
            ciphertext = bytes.fromhex(backup_blob['ciphertext'])
            iv = bytes.fromhex(backup_blob['iv'])
            tag = bytes.fromhex(backup_blob['tag'])
            
            # Decrypt account data
            account_data = self.decrypt_account_data(ciphertext, iv, tag, mnemonic)
            
            if account_data is None:
                return False, None
            
            return True, account_data
        
        except Exception as e:
            print(f"Import failed: {str(e)}")
            return False, None
    
    def list_account_backups(self) -> Dict[str, Dict[str, Any]]:
        """
        List all available account backups.
        
        Returns:
            Dict of {nano_address: metadata}
        """
        backups = {}
        
        for metadata_file in self.backup_dir.glob(f"*{self.METADATA_EXTENSION}"):
            try:
                metadata = json.loads(metadata_file.read_text(encoding='utf-8'))
                nano_address = metadata.get('nano_address')
                if nano_address:
                    backups[nano_address] = metadata
            except Exception:
                continue
        
        return backups
    
    async def delete_backup(self, nano_address: str) -> Tuple[bool, str]:
        """
        Delete account backup.
        
        Args:
            nano_address: User's Nano address
        
        Returns:
            Tuple of (success, message)
        """
        try:
            backup_name = nano_address.replace("nano_", "").lower()
            backup_path = self.backup_dir / f"{backup_name}{self.BACKUP_EXTENSION}"
            metadata_path = self.backup_dir / f"{backup_name}{self.METADATA_EXTENSION}"
            
            deleted = 0
            
            if backup_path.exists():
                backup_path.unlink()
                deleted += 1
            
            if metadata_path.exists():
                metadata_path.unlink()
                deleted += 1
            
            if deleted == 0:
                return False, "Backup not found"
            
            return True, f"Backup deleted"
        
        except Exception as e:
            return False, f"Deletion failed: {str(e)}"
    
    def get_backup_dir(self) -> str:
        """Get backup directory path."""
        return str(self.backup_dir)


# Global instance
account_backup_manager = AccountBackupManager()
