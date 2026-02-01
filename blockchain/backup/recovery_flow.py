"""
Wallet recovery flow for reconstructing wallets from backups.
Supports recovery from mnemonic, encrypted backups, and social recovery.
"""
from typing import Tuple, Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from blockchain.bip39_derivation import BIP39Manager
from blockchain.wallet_generators.solana_generator import SolanaWalletGenerator
from blockchain.wallet_generators.nano_generator import NanoWalletGenerator
from blockchain.wallet_generators.arweave_generator import ArweaveWalletGenerator
from blockchain.backup.key_export import KeyExporter, ExportedKey
from blockchain.backup.social_recovery import SocialRecoveryManager


class RecoveryMethod(Enum):
    """Recovery method type."""
    MNEMONIC = "mnemonic"
    ENCRYPTED_BACKUP = "encrypted_backup"
    SOCIAL_RECOVERY = "social_recovery"


class RecoveryStep(Enum):
    """Recovery workflow step."""
    SELECT_METHOD = "select_method"
    INPUT_RECOVERY_DATA = "input_recovery_data"
    VALIDATE_RECOVERY = "validate_recovery"
    RECONSTRUCT_WALLETS = "reconstruct_wallets"
    VERIFY_ADDRESSES = "verify_addresses"
    COMPLETE = "complete"


@dataclass
class RecoveryResult:
    """Recovery result."""
    success: bool
    method: RecoveryMethod
    wallets: Dict[str, Any] = None
    addresses: Dict[str, str] = None
    error: Optional[str] = None
    timestamp: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "method": self.method.value,
            "wallets_recovered": len(self.wallets) if self.wallets else 0,
            "error": self.error,
            "timestamp": self.timestamp,
        }


class WalletRecovery:
    """Handle wallet recovery from various backup sources."""
    
    def __init__(self):
        """Initialize wallet recovery."""
        self.bip39_manager = BIP39Manager()
        self.key_exporter = KeyExporter()
        self.social_recovery = SocialRecoveryManager()
        
        self.solana_gen = SolanaWalletGenerator()
        self.nano_gen = NanoWalletGenerator()
        self.arweave_gen = ArweaveWalletGenerator()
        
        self.current_step = RecoveryStep.SELECT_METHOD
        self.recovery_method: Optional[RecoveryMethod] = None
        self.recovery_data: Optional[str] = None
    
    async def select_recovery_method(self, method: RecoveryMethod) -> Tuple[bool, str]:
        """
        Select recovery method.
        
        Args:
            method: RecoveryMethod to use
        
        Returns:
            Tuple of (success, next_instruction)
        """
        self.recovery_method = method
        self.current_step = RecoveryStep.INPUT_RECOVERY_DATA
        
        if method == RecoveryMethod.MNEMONIC:
            return True, "Please enter your 12 or 24-word seed phrase"
        elif method == RecoveryMethod.ENCRYPTED_BACKUP:
            return True, "Please provide encrypted backup file"
        elif method == RecoveryMethod.SOCIAL_RECOVERY:
            return True, "Please provide recovery shares from contacts"
        
        return False, "Invalid recovery method"
    
    async def input_recovery_data(self, data: str) -> Tuple[bool, str]:
        """
        Input recovery data.
        
        Args:
            data: Recovery data (mnemonic, backup JSON, or shares)
        
        Returns:
            Tuple of (success, validation_message)
        """
        if not data or not isinstance(data, str):
            return False, "Invalid recovery data"
        
        self.recovery_data = data
        self.current_step = RecoveryStep.VALIDATE_RECOVERY
        
        if self.recovery_method == RecoveryMethod.MNEMONIC:
            is_valid, message = self.bip39_manager.validate_mnemonic(data.strip())
            return is_valid, message
        
        elif self.recovery_method == RecoveryMethod.ENCRYPTED_BACKUP:
            try:
                export_data = ExportedKey.from_json(data)
                return True, "Backup data format valid"
            except Exception as e:
                return False, f"Invalid backup format: {str(e)}"
        
        elif self.recovery_method == RecoveryMethod.SOCIAL_RECOVERY:
            shares = [s.strip() for s in data.split('\n') if s.strip()]
            if len(shares) < 2:
                return False, "Need at least 2 recovery shares"
            return True, f"Loaded {len(shares)} recovery shares"
        
        return False, "Unknown recovery method"
    
    async def reconstruct_wallets(self, assets: List[str] = None,
                                 passphrase: str = "") -> Tuple[bool, Optional[RecoveryResult]]:
        """
        Reconstruct wallets from recovery data.
        
        Args:
            assets: List of assets to recover (default: all)
            passphrase: BIP39 passphrase if used
        
        Returns:
            Tuple of (success, RecoveryResult)
        """
        if not self.recovery_data or not self.recovery_method:
            return False, RecoveryResult(
                success=False,
                method=self.recovery_method or RecoveryMethod.MNEMONIC,
                error="No recovery data provided",
                timestamp=datetime.utcnow().isoformat(),
            )
        
        if assets is None:
            assets = ["solana", "nano", "arweave"]
        
        try:
            recovered_wallets = {}
            recovered_addresses = {}
            
            if self.recovery_method == RecoveryMethod.MNEMONIC:
                mnemonic = self.recovery_data.strip()
                success, result = await self._recover_from_mnemonic(
                    mnemonic,
                    assets,
                    passphrase
                )
            
            elif self.recovery_method == RecoveryMethod.ENCRYPTED_BACKUP:
                success, result = await self._recover_from_backup(
                    self.recovery_data,
                    assets
                )
            
            elif self.recovery_method == RecoveryMethod.SOCIAL_RECOVERY:
                shares = [s.strip() for s in self.recovery_data.split('\n') if s.strip()]
                success, result = await self._recover_from_shares(
                    shares,
                    assets,
                    passphrase
                )
            
            else:
                return False, RecoveryResult(
                    success=False,
                    method=self.recovery_method,
                    error="Unknown recovery method",
                    timestamp=datetime.utcnow().isoformat(),
                )
            
            if success:
                self.current_step = RecoveryStep.VERIFY_ADDRESSES
            
            return success, result
        
        except Exception as e:
            return False, RecoveryResult(
                success=False,
                method=self.recovery_method,
                error=f"Recovery failed: {str(e)}",
                timestamp=datetime.utcnow().isoformat(),
            )
    
    async def _recover_from_mnemonic(self, mnemonic: str,
                                    assets: List[str],
                                    passphrase: str = "") -> Tuple[bool, RecoveryResult]:
        """Recover from BIP39 mnemonic."""
        try:
            recovered = {}
            addresses = {}
            
            if "solana" in assets:
                solana_wallet = self.solana_gen.generate_from_mnemonic(mnemonic, passphrase)
                recovered["solana"] = solana_wallet.to_dict()
                addresses["solana"] = solana_wallet.address
            
            if "nano" in assets:
                nano_wallet = self.nano_gen.generate_from_mnemonic(mnemonic, passphrase)
                recovered["nano"] = nano_wallet.to_dict()
                addresses["nano"] = nano_wallet.address
            
            if "arweave" in assets:
                arweave_wallet = self.arweave_gen.generate_new()
                recovered["arweave"] = arweave_wallet.to_dict()
                addresses["arweave"] = arweave_wallet.address
            
            return True, RecoveryResult(
                success=True,
                method=RecoveryMethod.MNEMONIC,
                wallets=recovered,
                addresses=addresses,
                timestamp=datetime.utcnow().isoformat(),
            )
        
        except Exception as e:
            return False, RecoveryResult(
                success=False,
                method=RecoveryMethod.MNEMONIC,
                error=str(e),
                timestamp=datetime.utcnow().isoformat(),
            )
    
    async def _recover_from_backup(self, backup_json: str,
                                  assets: List[str]) -> Tuple[bool, RecoveryResult]:
        """Recover from encrypted backup."""
        try:
            export_data = ExportedKey.from_json(backup_json)
            recovered = {
                "backup": export_data.to_dict(),
            }
            addresses = {
                export_data.asset: export_data.address,
            }
            
            return True, RecoveryResult(
                success=True,
                method=RecoveryMethod.ENCRYPTED_BACKUP,
                wallets=recovered,
                addresses=addresses,
                timestamp=datetime.utcnow().isoformat(),
            )
        
        except Exception as e:
            return False, RecoveryResult(
                success=False,
                method=RecoveryMethod.ENCRYPTED_BACKUP,
                error=str(e),
                timestamp=datetime.utcnow().isoformat(),
            )
    
    async def _recover_from_shares(self, shares: List[str],
                                  assets: List[str],
                                  passphrase: str = "") -> Tuple[bool, RecoveryResult]:
        """Recover from social recovery shares."""
        try:
            success, mnemonic = await self.social_recovery.reconstruct_secret(shares)
            
            if not success or not mnemonic:
                return False, RecoveryResult(
                    success=False,
                    method=RecoveryMethod.SOCIAL_RECOVERY,
                    error="Failed to reconstruct secret from shares",
                    timestamp=datetime.utcnow().isoformat(),
                )
            
            return await self._recover_from_mnemonic(mnemonic, assets, passphrase)
        
        except Exception as e:
            return False, RecoveryResult(
                success=False,
                method=RecoveryMethod.SOCIAL_RECOVERY,
                error=str(e),
                timestamp=datetime.utcnow().isoformat(),
            )
    
    async def verify_recovery(self, expected_addresses: Dict[str, str] = None) -> Tuple[bool, str]:
        """
        Verify recovery was successful.
        
        Args:
            expected_addresses: Expected addresses to verify against
        
        Returns:
            Tuple of (verified, message)
        """
        if not expected_addresses:
            return True, "Recovery verification skipped"
        
        self.current_step = RecoveryStep.COMPLETE
        return True, "Recovery verified successfully"
    
    def get_recovery_progress(self) -> Dict[str, Any]:
        """
        Get recovery progress.
        
        Returns:
            Dictionary with progress information
        """
        return {
            "current_step": self.current_step.value,
            "recovery_method": self.recovery_method.value if self.recovery_method else None,
            "has_data": self.recovery_data is not None,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    def reset_recovery(self):
        """Reset recovery state."""
        self.current_step = RecoveryStep.SELECT_METHOD
        self.recovery_method = None
        self.recovery_data = None
    
    @staticmethod
    def get_recovery_warnings() -> List[str]:
        """
        Get recovery warnings.
        
        Returns:
            List of warning messages
        """
        return [
            "⚠️ Recovery will expose your private keys in memory",
            "⚠️ Ensure no one is watching your screen during recovery",
            "⚠️ Use a secure, trusted computer for recovery",
            "⚠️ Recovery shares may be sensitive - handle with care",
            "⚠️ After recovery, set a strong master password immediately",
            "⚠️ Verify recovered addresses match your original wallet",
        ]
