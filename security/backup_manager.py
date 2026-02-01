"""
Encrypted backup and recovery system for wallet keys.
Manages encrypted backups with integrity verification and recovery.
"""
import json
import hashlib
import time
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime

from security.vault_encryption import VaultEncryption


class BackupManager:
    """Manage encrypted vault backups."""
    
    DEFAULT_BACKUP_DIR = "~/.sapphire_exchange/backups"
    BACKUP_EXTENSION = ".backup.enc"
    METADATA_EXTENSION = ".backup.meta"
    
    def __init__(self, vault_encryption: VaultEncryption,
                 backup_dir: str = None):
        """
        Initialize backup manager.
        
        Args:
            vault_encryption: VaultEncryption instance
            backup_dir: Directory for backups (default: ~/.sapphire_exchange/backups)
        """
        self.vault_encryption = vault_encryption
        self.backup_dir = Path(backup_dir or self.DEFAULT_BACKUP_DIR).expanduser()
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def create_backup(self, backup_name: str = None) -> Tuple[bool, str]:
        """
        Create encrypted backup of vault.
        
        Args:
            backup_name: Optional backup name (default: timestamp)
        
        Returns:
            Tuple of (success, backup_path or error_message)
        """
        try:
            if backup_name is None:
                backup_name = f"backup_{int(time.time())}"
            
            vault_json = self.vault_encryption.export_vault_json()
            
            backup_path = self.backup_dir / f"{backup_name}{self.BACKUP_EXTENSION}"
            
            if backup_path.exists():
                return False, f"Backup already exists: {backup_path}"
            
            backup_path.write_text(vault_json, encoding='utf-8')
            
            vault_hash = hashlib.sha256(vault_json.encode('utf-8')).hexdigest()
            
            metadata = {
                'backup_name': backup_name,
                'created_at': datetime.utcnow().isoformat(),
                'vault_hash': vault_hash,
                'file_size': len(vault_json),
                'key_count': len(json.loads(vault_json).get('blobs', {})),
            }
            
            metadata_path = self.backup_dir / f"{backup_name}{self.METADATA_EXTENSION}"
            metadata_path.write_text(
                json.dumps(metadata, indent=2),
                encoding='utf-8'
            )
            
            return True, str(backup_path)
        
        except Exception as e:
            return False, f"Backup creation failed: {str(e)}"
    
    def restore_backup(self, backup_name: str) -> Tuple[bool, str]:
        """
        Restore vault from backup.
        
        Args:
            backup_name: Backup name (without extension)
        
        Returns:
            Tuple of (success, message)
        """
        try:
            backup_path = self.backup_dir / f"{backup_name}{self.BACKUP_EXTENSION}"
            metadata_path = self.backup_dir / f"{backup_name}{self.METADATA_EXTENSION}"
            
            if not backup_path.exists():
                return False, f"Backup not found: {backup_path}"
            
            backup_json = backup_path.read_text(encoding='utf-8')
            
            if metadata_path.exists():
                metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
                expected_hash = metadata['vault_hash']
                actual_hash = hashlib.sha256(backup_json.encode('utf-8')).hexdigest()
                
                if expected_hash != actual_hash:
                    return False, "Backup integrity check failed (corrupted backup)"
            
            if not self.vault_encryption.import_vault_json(backup_json):
                return False, "Failed to restore backup"
            
            return True, "Backup restored successfully"
        
        except Exception as e:
            return False, f"Restore failed: {str(e)}"
    
    def verify_backup(self, backup_name: str) -> Tuple[bool, str]:
        """
        Verify backup integrity.
        
        Args:
            backup_name: Backup name
        
        Returns:
            Tuple of (is_valid, message)
        """
        try:
            backup_path = self.backup_dir / f"{backup_name}{self.BACKUP_EXTENSION}"
            metadata_path = self.backup_dir / f"{backup_name}{self.METADATA_EXTENSION}"
            
            if not backup_path.exists():
                return False, "Backup file not found"
            
            if not metadata_path.exists():
                return False, "Backup metadata not found"
            
            backup_json = backup_path.read_text(encoding='utf-8')
            metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
            
            expected_hash = metadata['vault_hash']
            actual_hash = hashlib.sha256(backup_json.encode('utf-8')).hexdigest()
            
            if expected_hash != actual_hash:
                return False, "Backup corrupted (hash mismatch)"
            
            vault_data = json.loads(backup_json)
            actual_key_count = len(vault_data.get('blobs', {}))
            expected_key_count = metadata['key_count']
            
            if actual_key_count != expected_key_count:
                return False, f"Key count mismatch: expected {expected_key_count}, got {actual_key_count}"
            
            return True, "Backup is valid"
        
        except Exception as e:
            return False, f"Verification failed: {str(e)}"
    
    def list_backups(self) -> Dict[str, Dict[str, Any]]:
        """
        List all available backups.
        
        Returns:
            Dict of {backup_name: metadata}
        """
        backups = {}
        
        for metadata_file in self.backup_dir.glob(f"*{self.METADATA_EXTENSION}"):
            try:
                backup_name = metadata_file.stem.replace(self.METADATA_EXTENSION, '')
                metadata = json.loads(metadata_file.read_text(encoding='utf-8'))
                backups[backup_name] = metadata
            except Exception:
                continue
        
        return backups
    
    def delete_backup(self, backup_name: str) -> Tuple[bool, str]:
        """
        Delete backup files.
        
        Args:
            backup_name: Backup name
        
        Returns:
            Tuple of (success, message)
        """
        try:
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
            
            return True, f"Deleted {deleted} backup files"
        
        except Exception as e:
            return False, f"Deletion failed: {str(e)}"
    
    def get_backup_info(self, backup_name: str) -> Optional[Dict[str, Any]]:
        """
        Get backup metadata and info.
        
        Args:
            backup_name: Backup name
        
        Returns:
            Metadata dict or None
        """
        metadata_path = self.backup_dir / f"{backup_name}{self.METADATA_EXTENSION}"
        
        if not metadata_path.exists():
            return None
        
        try:
            return json.loads(metadata_path.read_text(encoding='utf-8'))
        except Exception:
            return None
    
    def export_backup_to_file(self, backup_name: str, 
                             export_path: str) -> Tuple[bool, str]:
        """
        Export backup to external file (for manual backup).
        
        Args:
            backup_name: Backup name
            export_path: Path to export to
        
        Returns:
            Tuple of (success, message)
        """
        try:
            backup_path = self.backup_dir / f"{backup_name}{self.BACKUP_EXTENSION}"
            
            if not backup_path.exists():
                return False, "Backup not found"
            
            export_full_path = Path(export_path)
            export_full_path.parent.mkdir(parents=True, exist_ok=True)
            
            backup_content = backup_path.read_text(encoding='utf-8')
            export_full_path.write_text(backup_content, encoding='utf-8')
            
            return True, f"Backup exported to {export_path}"
        
        except Exception as e:
            return False, f"Export failed: {str(e)}"
    
    def import_backup_from_file(self, import_path: str, 
                               backup_name: str = None) -> Tuple[bool, str]:
        """
        Import backup from external file.
        
        Args:
            import_path: Path to backup file
            backup_name: Name for imported backup
        
        Returns:
            Tuple of (success, message)
        """
        try:
            import_full_path = Path(import_path)
            
            if not import_full_path.exists():
                return False, "Import file not found"
            
            backup_content = import_full_path.read_text(encoding='utf-8')
            
            if backup_name is None:
                backup_name = f"imported_{int(time.time())}"
            
            backup_path = self.backup_dir / f"{backup_name}{self.BACKUP_EXTENSION}"
            backup_path.write_text(backup_content, encoding='utf-8')
            
            vault_hash = hashlib.sha256(backup_content.encode('utf-8')).hexdigest()
            
            metadata = {
                'backup_name': backup_name,
                'created_at': datetime.utcnow().isoformat(),
                'imported_at': datetime.utcnow().isoformat(),
                'vault_hash': vault_hash,
                'file_size': len(backup_content),
                'key_count': len(json.loads(backup_content).get('blobs', {})),
            }
            
            metadata_path = self.backup_dir / f"{backup_name}{self.METADATA_EXTENSION}"
            metadata_path.write_text(
                json.dumps(metadata, indent=2),
                encoding='utf-8'
            )
            
            return True, f"Backup imported as {backup_name}"
        
        except Exception as e:
            return False, f"Import failed: {str(e)}"
    
    def get_backup_dir(self) -> str:
        """Get backup directory path."""
        return str(self.backup_dir)
    
    def get_total_backup_size(self) -> int:
        """Get total size of all backups in bytes."""
        total = 0
        for backup_file in self.backup_dir.glob(f"*{self.BACKUP_EXTENSION}"):
            total += backup_file.stat().st_size
        return total
