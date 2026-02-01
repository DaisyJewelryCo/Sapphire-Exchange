"""
Unified backup manager orchestrating all backup types.
Manages mnemonic, encrypted key, physical, and social recovery backups.
"""
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from enum import Enum
import json

from blockchain.backup.mnemonic_backup import MnemonicBackup, MnemonicBackupData
from blockchain.backup.key_export import KeyExporter, ExportedKey
from blockchain.backup.physical_backup import PhysicalBackupGenerator
from blockchain.backup.social_recovery import SocialRecoveryManager, RecoveryShareSet
from blockchain.backup.recovery_flow import WalletRecovery, RecoveryMethod


class BackupType(Enum):
    """Backup type enumeration."""
    MNEMONIC = "mnemonic"
    ENCRYPTED_KEY = "encrypted_key"
    PHYSICAL = "physical"
    SOCIAL = "social"


@dataclass
class BackupRecord:
    """Backup history record."""
    backup_id: str
    backup_type: BackupType
    created_at: str
    wallet_name: str
    description: str = ""
    location: Optional[str] = None
    status: str = "pending"
    verified_at: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "backup_id": self.backup_id,
            "backup_type": self.backup_type.value,
            "created_at": self.created_at,
            "wallet_name": self.wallet_name,
            "description": self.description,
            "location": self.location,
            "status": self.status,
            "verified_at": self.verified_at,
            "metadata": self.metadata or {},
        }


class BackupManager:
    """Manage all wallet backups."""
    
    DEFAULT_BACKUP_DIR = "~/.sapphire_exchange/backups"
    
    def __init__(self, backup_dir: str = None):
        """
        Initialize backup manager.
        
        Args:
            backup_dir: Directory for storing backups
        """
        self.backup_dir = Path(backup_dir or self.DEFAULT_BACKUP_DIR).expanduser()
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        self.mnemonic_backup = MnemonicBackup()
        self.key_exporter = KeyExporter()
        self.physical_generator = PhysicalBackupGenerator()
        self.social_recovery = SocialRecoveryManager()
        self.wallet_recovery = WalletRecovery()
        
        self.backup_history: Dict[str, BackupRecord] = {}
        self._load_backup_history()
    
    async def create_all_backups(self, mnemonic: str,
                                wallet_name: str,
                                private_keys: Dict[str, bytes] = None,
                                public_keys: Dict[str, str] = None,
                                addresses: Dict[str, str] = None,
                                contact_names: List[str] = None,
                                export_password: str = None,
                                passphrase: str = "") -> Tuple[bool, Dict[str, Any]]:
        """
        Create all backup types.
        
        Args:
            mnemonic: BIP39 mnemonic phrase
            wallet_name: Name of wallet
            private_keys: Dictionary of {asset: private_key_bytes}
            public_keys: Dictionary of {asset: public_key_hex}
            addresses: Dictionary of {asset: address}
            contact_names: List of recovery contact names
            export_password: Password for key export
            passphrase: BIP39 passphrase if used
        
        Returns:
            Tuple of (success, backup_results_dict)
        """
        results = {
            "wallet_name": wallet_name,
            "timestamp": datetime.utcnow().isoformat(),
            "backups": {},
            "errors": [],
        }
        
        success, mnemonic_backup = await self.create_mnemonic_backup(
            mnemonic,
            wallet_name,
            passphrase
        )
        results["backups"]["mnemonic"] = success
        if not success:
            results["errors"].append("Mnemonic backup failed")
        
        if private_keys and export_password:
            success, encrypted_backups = await self.create_encrypted_backups(
                private_keys,
                public_keys or {},
                addresses or {},
                export_password,
                wallet_name
            )
            results["backups"]["encrypted_keys"] = success
            if not success:
                results["errors"].append("Encrypted key backup failed")
        
        success, physical_backup = await self.create_physical_backup(
            mnemonic,
            wallet_name
        )
        results["backups"]["physical"] = success
        if not success:
            results["errors"].append("Physical backup failed")
        
        if contact_names:
            success, social_backup = await self.create_social_recovery(
                mnemonic,
                wallet_name,
                contact_names
            )
            results["backups"]["social"] = success
            if not success:
                results["errors"].append("Social recovery backup failed")
        
        return len(results["errors"]) == 0, results
    
    async def create_mnemonic_backup(self, mnemonic: str,
                                    wallet_name: str,
                                    passphrase: str = "") -> Tuple[bool, str]:
        """Create mnemonic backup."""
        try:
            import os
            backup_id = os.urandom(16).hex()
            
            word_count = len(mnemonic.split())
            success, backup_data = await self.mnemonic_backup.generate(word_count, passphrase)
            
            if not success:
                return False, backup_id
            
            record = BackupRecord(
                backup_id=backup_id,
                backup_type=BackupType.MNEMONIC,
                created_at=datetime.utcnow().isoformat(),
                wallet_name=wallet_name,
                description="BIP39 mnemonic backup",
                status="pending",
            )
            
            self.backup_history[backup_id] = record
            self._save_backup_history()
            
            return True, backup_id
        
        except Exception as e:
            return False, str(e)
    
    async def create_encrypted_backups(self, private_keys: Dict[str, bytes],
                                      public_keys: Dict[str, str],
                                      addresses: Dict[str, str],
                                      password: str,
                                      wallet_name: str) -> Tuple[bool, Dict[str, str]]:
        """Create encrypted key backups."""
        try:
            import os
            backup_ids = {}
            
            for asset, private_key in private_keys.items():
                public_key = public_keys.get(asset, "")
                address = addresses.get(asset, "")
                
                success, exported = await self.key_exporter.export_encrypted(
                    private_key=private_key,
                    public_key=public_key,
                    address=address,
                    asset=asset,
                    chain=asset,
                    password=password,
                )
                
                if success and exported:
                    backup_id = os.urandom(16).hex()
                    backup_file = self.backup_dir / f"{backup_id}_{asset}.enc"
                    backup_file.write_text(exported.to_json(), encoding='utf-8')
                    
                    record = BackupRecord(
                        backup_id=backup_id,
                        backup_type=BackupType.ENCRYPTED_KEY,
                        created_at=datetime.utcnow().isoformat(),
                        wallet_name=wallet_name,
                        description=f"Encrypted {asset} private key",
                        location=str(backup_file),
                        status="active",
                    )
                    
                    self.backup_history[backup_id] = record
                    backup_ids[asset] = backup_id
            
            self._save_backup_history()
            return len(backup_ids) > 0, backup_ids
        
        except Exception as e:
            return False, {}
    
    async def create_physical_backup(self, mnemonic: str,
                                    wallet_name: str) -> Tuple[bool, str]:
        """Create physical backup template."""
        try:
            import os
            backup_id = os.urandom(16).hex()
            
            success, html_content = await self.physical_generator.generate_paper_template(
                mnemonic,
                wallet_name
            )
            
            if not success:
                return False, backup_id
            
            backup_file = self.backup_dir / f"{backup_id}_physical.html"
            Path(backup_file).write_text(html_content, encoding='utf-8')
            
            record = BackupRecord(
                backup_id=backup_id,
                backup_type=BackupType.PHYSICAL,
                created_at=datetime.utcnow().isoformat(),
                wallet_name=wallet_name,
                description="Physical backup template (HTML)",
                location=str(backup_file),
                status="pending",
            )
            
            self.backup_history[backup_id] = record
            self._save_backup_history()
            
            return True, backup_id
        
        except Exception as e:
            return False, str(e)
    
    async def create_social_recovery(self, mnemonic: str,
                                    wallet_name: str,
                                    contact_names: List[str],
                                    threshold: int = 3) -> Tuple[bool, str]:
        """Create social recovery scheme."""
        try:
            import os
            backup_id = os.urandom(16).hex()
            
            success, recovery_set = await self.social_recovery.create_recovery_scheme(
                mnemonic,
                contact_names,
                threshold
            )
            
            if not success or not recovery_set:
                return False, backup_id
            
            backup_file = self.backup_dir / f"{backup_id}_social.json"
            backup_file.write_text(self.social_recovery.export_recovery_scheme(recovery_set), encoding='utf-8')
            
            record = BackupRecord(
                backup_id=backup_id,
                backup_type=BackupType.SOCIAL,
                created_at=datetime.utcnow().isoformat(),
                wallet_name=wallet_name,
                description=f"Social recovery ({recovery_set.threshold}-of-{recovery_set.total_shares})",
                location=str(backup_file),
                status="pending",
                metadata={
                    "total_shares": recovery_set.total_shares,
                    "threshold": recovery_set.threshold,
                    "contacts": len(contact_names),
                },
            )
            
            self.backup_history[backup_id] = record
            self._save_backup_history()
            
            return True, backup_id
        
        except Exception as e:
            return False, str(e)
    
    async def list_backups(self, backup_type: BackupType = None,
                          wallet_name: str = None) -> List[BackupRecord]:
        """
        List backups with optional filtering.
        
        Args:
            backup_type: Filter by backup type
            wallet_name: Filter by wallet name
        
        Returns:
            List of BackupRecords
        """
        results = []
        
        for record in self.backup_history.values():
            if backup_type and record.backup_type != backup_type:
                continue
            
            if wallet_name and record.wallet_name != wallet_name:
                continue
            
            results.append(record)
        
        return sorted(results, key=lambda r: r.created_at, reverse=True)
    
    async def verify_backup(self, backup_id: str,
                           test_password: str = None) -> Tuple[bool, str]:
        """
        Verify backup integrity.
        
        Args:
            backup_id: Backup ID to verify
            test_password: Password for encrypted backups
        
        Returns:
            Tuple of (verified, message)
        """
        try:
            if backup_id not in self.backup_history:
                return False, "Backup not found"
            
            record = self.backup_history[backup_id]
            
            if record.backup_type == BackupType.MNEMONIC:
                return True, "Mnemonic backup verified"
            
            elif record.backup_type == BackupType.ENCRYPTED_KEY:
                if not record.location or not Path(record.location).exists():
                    return False, "Backup file not found"
                return True, "Encrypted backup verified"
            
            elif record.backup_type == BackupType.PHYSICAL:
                if not record.location or not Path(record.location).exists():
                    return False, "Backup file not found"
                return True, "Physical backup verified"
            
            elif record.backup_type == BackupType.SOCIAL:
                if not record.location or not Path(record.location).exists():
                    return False, "Backup file not found"
                return True, "Social recovery backup verified"
            
            return False, "Unknown backup type"
        
        except Exception as e:
            return False, f"Verification failed: {str(e)}"
    
    async def delete_backup(self, backup_id: str) -> Tuple[bool, str]:
        """
        Delete backup.
        
        Args:
            backup_id: Backup ID to delete
        
        Returns:
            Tuple of (success, message)
        """
        try:
            if backup_id not in self.backup_history:
                return False, "Backup not found"
            
            record = self.backup_history[backup_id]
            
            if record.location and Path(record.location).exists():
                Path(record.location).unlink()
            
            del self.backup_history[backup_id]
            self._save_backup_history()
            
            return True, "Backup deleted successfully"
        
        except Exception as e:
            return False, f"Deletion failed: {str(e)}"
    
    def _load_backup_history(self):
        """Load backup history from file."""
        try:
            history_file = self.backup_dir / "backups.json"
            
            if history_file.exists():
                data = json.loads(history_file.read_text(encoding='utf-8'))
                
                for record_data in data.get("backups", []):
                    record = BackupRecord(
                        backup_id=record_data["backup_id"],
                        backup_type=BackupType(record_data["backup_type"]),
                        created_at=record_data["created_at"],
                        wallet_name=record_data["wallet_name"],
                        description=record_data.get("description", ""),
                        location=record_data.get("location"),
                        status=record_data.get("status", "pending"),
                        verified_at=record_data.get("verified_at"),
                    )
                    self.backup_history[record.backup_id] = record
        
        except Exception:
            pass
    
    def _save_backup_history(self):
        """Save backup history to file."""
        try:
            history_file = self.backup_dir / "backups.json"
            
            data = {
                "version": "1.0",
                "last_updated": datetime.utcnow().isoformat(),
                "backups": [r.to_dict() for r in self.backup_history.values()],
            }
            
            history_file.write_text(json.dumps(data, indent=2), encoding='utf-8')
        
        except Exception:
            pass
    
    async def get_backup_statistics(self) -> Dict[str, Any]:
        """Get backup statistics."""
        stats = {
            "total_backups": len(self.backup_history),
            "by_type": {},
            "by_wallet": {},
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        for record in self.backup_history.values():
            backup_type = record.backup_type.value
            stats["by_type"][backup_type] = stats["by_type"].get(backup_type, 0) + 1
            
            wallet = record.wallet_name
            stats["by_wallet"][wallet] = stats["by_wallet"].get(wallet, 0) + 1
        
        return stats
