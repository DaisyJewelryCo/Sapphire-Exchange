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
    def _make_json_serializable(obj: Any) -> Any:
        """
        Convert bytes and other non-serializable objects to JSON-serializable format.
        Recursively handles dicts and lists.
        
        Args:
            obj: Object to make JSON-serializable
        
        Returns:
            JSON-serializable version of the object
        """
        if isinstance(obj, bytes):
            return obj.hex()
        elif isinstance(obj, dict):
            return {k: AccountBackupManager._make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [AccountBackupManager._make_json_serializable(item) for item in obj]
        else:
            return obj
    
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
            # Convert wallet_data to JSON-serializable format (bytes -> hex strings)
            serializable_wallet_data = self._make_json_serializable(wallet_data)
            serializable_private_keys = self._make_json_serializable(private_keys or {})
            
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
                'wallets': serializable_wallet_data,
                'private_keys': serializable_private_keys,
                'created_at': user.created_at,
                'updated_at': datetime.utcnow().isoformat(),
            }
            
            print(f"[BACKUP] Encrypting account data...")
            # Encrypt account data
            ciphertext, iv, tag = self.encrypt_account_data(account_data, mnemonic)
            print(f"[BACKUP] Account data encrypted. Ciphertext size: {len(ciphertext)} bytes")
            
            # Create timestamped backup filename
            # Format: sapphire_backup_user_USERNAME_nano_NANOADDRESSHORT_TIMESTAMP.account.enc
            username = user.username or 'unknown'
            nano_short = nano_address.replace("nano_", "").lower()[:8]
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_name = f"sapphire_backup_user_{username}_nano_{nano_short}_{timestamp}"
            backup_path = self.backup_dir / f"{backup_name}{self.BACKUP_EXTENSION}"
            
            print(f"[BACKUP] Backup filename: {backup_name}")
            print(f"[BACKUP] Backup path: {backup_path}")
            
            # Save encrypted backup
            backup_blob = {
                'nano_address': nano_address,
                'ciphertext': ciphertext.hex(),
                'iv': iv.hex(),
                'tag': tag.hex(),
            }
            
            print(f"[BACKUP] Writing encrypted backup to disk...")
            backup_path.write_text(json.dumps(backup_blob), encoding='utf-8')
            print(f"✓ [BACKUP] Encrypted backup written")
            
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
            print(f"[BACKUP] Writing metadata to disk...")
            metadata_path.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
            print(f"✓ [BACKUP] Metadata written")
            
            print(f"✓ [BACKUP] Account backup created successfully: {backup_path.name}")
            return True, str(backup_path)
        
        except Exception as e:
            print(f"❌ [BACKUP] Backup creation failed: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            return False, f"Backup creation failed: {str(e)}"
    
    async def restore_account_from_backup(self, nano_address: str, 
                                         mnemonic: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Restore account backup using Nano address and mnemonic.
        Finds the most recent backup for the given nano address.
        
        Args:
            nano_address: User's Nano address (backup key)
            mnemonic: Nano mnemonic (used to decrypt backup)
        
        Returns:
            Tuple of (success, account_data or None)
        """
        try:
            # Support both old and new backup naming formats
            nano_short = nano_address.replace("nano_", "").lower()[:8]
            nano_full = nano_address.replace("nano_", "").lower()
            
            # Try new format first: sapphire_backup_user_*_nano_NANOSHORT_*.account.enc
            pattern_new = f"sapphire_backup_user_*_nano_{nano_short}_*.account.enc"
            backup_files = sorted(self.backup_dir.glob(pattern_new), reverse=True)
            
            # Fall back to old format: just the nano address hash
            if not backup_files:
                print(f"[BACKUP_RESTORE] No new-format backups found, checking old format...")
                pattern_old = f"{nano_full}{self.BACKUP_EXTENSION}"
                backup_path_old = self.backup_dir / pattern_old
                if backup_path_old.exists():
                    backup_files = [backup_path_old]
                    print(f"✓ [BACKUP_RESTORE] Found old-format backup: {backup_path_old.name}")
            
            if not backup_files:
                print(f"❌ [BACKUP_RESTORE] No backups found for nano address: {nano_address}")
                print(f"[BACKUP_RESTORE] Searched patterns:")
                print(f"  - New format: {pattern_new}")
                print(f"  - Old format: {nano_full}{self.BACKUP_EXTENSION}")
                print(f"[BACKUP_RESTORE] Total backups in directory: {len(list(self.backup_dir.glob('*.account.enc')))}")
                return False, None
            
            # Use the most recent backup
            backup_path = backup_files[0]
            print(f"✓ [BACKUP_RESTORE] Found {len(backup_files)} backup(s), using: {backup_path.name}")
            
            # Load encrypted backup
            backup_blob = json.loads(backup_path.read_text(encoding='utf-8'))
            
            ciphertext = bytes.fromhex(backup_blob['ciphertext'])
            iv = bytes.fromhex(backup_blob['iv'])
            tag = bytes.fromhex(backup_blob['tag'])
            
            print(f"[BACKUP_RESTORE] Decrypting account data...")
            
            # Decrypt account data
            account_data = self.decrypt_account_data(ciphertext, iv, tag, mnemonic)
            
            if account_data is None:
                print(f"❌ [BACKUP_RESTORE] Decryption failed (returned None)")
                return False, None
            
            print(f"✓ [BACKUP_RESTORE] Decryption successful")
            
            # Verify Nano address matches
            if account_data.get('nano_address') != nano_address:
                print(f"❌ [BACKUP_RESTORE] Address mismatch! Backup: {account_data.get('nano_address')}, Expected: {nano_address}")
                return False, None
            
            print(f"✓ [BACKUP_RESTORE] Backup verified successfully for user: {account_data.get('username')}")
            return True, account_data
        
        except Exception as e:
            print(f"❌ [BACKUP_RESTORE] Backup restoration failed: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            return False, None
    
    async def verify_backup(self, nano_address: str) -> Tuple[bool, str]:
        """
        Verify backup exists and is accessible.
        Looks for the most recent backup for the given nano address.
        
        Args:
            nano_address: User's Nano address
        
        Returns:
            Tuple of (is_valid, message)
        """
        try:
            # Support both old and new backup naming formats
            nano_short = nano_address.replace("nano_", "").lower()[:8]
            nano_full = nano_address.replace("nano_", "").lower()
            
            # Try new format first
            pattern_new = f"sapphire_backup_user_*_nano_{nano_short}_*.account.enc"
            backup_files = sorted(self.backup_dir.glob(pattern_new), reverse=True)
            
            # Fall back to old format
            if not backup_files:
                pattern_old = f"{nano_full}{self.BACKUP_EXTENSION}"
                backup_path_old = self.backup_dir / pattern_old
                if backup_path_old.exists():
                    backup_files = [backup_path_old]
            
            if not backup_files:
                return False, "Backup not found"
            
            backup_path = backup_files[0]
            metadata_path = self.backup_dir / f"{backup_path.stem}{self.METADATA_EXTENSION}"
            
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
        Exports the most recent backup for the given nano address.
        
        Args:
            nano_address: User's Nano address
            export_path: Destination path for export
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Support both old and new backup naming formats
            nano_short = nano_address.replace("nano_", "").lower()[:8]
            nano_full = nano_address.replace("nano_", "").lower()
            
            # Try new format first
            pattern_new = f"sapphire_backup_user_*_nano_{nano_short}_*.account.enc"
            backup_files = sorted(self.backup_dir.glob(pattern_new), reverse=True)
            
            # Fall back to old format
            if not backup_files:
                pattern_old = f"{nano_full}{self.BACKUP_EXTENSION}"
                backup_path_old = self.backup_dir / pattern_old
                if backup_path_old.exists():
                    backup_files = [backup_path_old]
            
            if not backup_files:
                return False, "Backup not found"
            
            backup_path = backup_files[0]
            
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
        Delete all account backups for a nano address.
        
        Args:
            nano_address: User's Nano address
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Support both old and new backup naming formats
            nano_short = nano_address.replace("nano_", "").lower()[:8]
            nano_full = nano_address.replace("nano_", "").lower()
            
            deleted = 0
            
            # Delete new-format backups
            pattern_new = f"sapphire_backup_user_*_nano_{nano_short}_*"
            backup_files = list(self.backup_dir.glob(f"{pattern_new}{self.BACKUP_EXTENSION}"))
            metadata_files = list(self.backup_dir.glob(f"{pattern_new}{self.METADATA_EXTENSION}"))
            
            for backup_file in backup_files:
                backup_file.unlink()
                deleted += 1
                print(f"[BACKUP] Deleted: {backup_file.name}")
            
            for metadata_file in metadata_files:
                metadata_file.unlink()
                deleted += 1
                print(f"[BACKUP] Deleted: {metadata_file.name}")
            
            # Delete old-format backups
            pattern_old = f"{nano_full}{self.BACKUP_EXTENSION}"
            backup_path_old = self.backup_dir / pattern_old
            metadata_path_old = self.backup_dir / f"{nano_full}{self.METADATA_EXTENSION}"
            
            if backup_path_old.exists():
                backup_path_old.unlink()
                deleted += 1
                print(f"[BACKUP] Deleted: {backup_path_old.name}")
            
            if metadata_path_old.exists():
                metadata_path_old.unlink()
                deleted += 1
                print(f"[BACKUP] Deleted: {metadata_path_old.name}")
            
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
