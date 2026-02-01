"""
Mnemonic backup system for BIP39 wallet recovery.
Handles mnemonic generation, display, confirmation, and validation.
"""
from typing import Tuple, Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from blockchain.bip39_derivation import BIP39Manager
from blockchain.entropy_generator import EntropyGenerator


class BackupStatus(Enum):
    """Backup status."""
    PENDING = "pending"
    DISPLAYED = "displayed"
    CONFIRMED = "confirmed"
    VERIFIED = "verified"


@dataclass
class MnemonicBackupData:
    """Mnemonic backup data."""
    mnemonic: str
    passphrase: str = ""
    word_count: int = 24
    created_at: str = ""
    confirmed_at: Optional[str] = None
    status: BackupStatus = BackupStatus.PENDING
    confirmation_attempts: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "mnemonic": self.mnemonic,
            "passphrase": self.passphrase,
            "word_count": self.word_count,
            "created_at": self.created_at,
            "confirmed_at": self.confirmed_at,
            "status": self.status.value,
            "confirmation_attempts": self.confirmation_attempts,
        }


class MnemonicBackup:
    """Manage BIP39 mnemonic backup and confirmation."""
    
    def __init__(self):
        """Initialize mnemonic backup manager."""
        self.bip39_manager = BIP39Manager()
        self.entropy_gen = EntropyGenerator()
        self.backup_data: Optional[MnemonicBackupData] = None
    
    async def generate(self, word_count: int = 24,
                      passphrase: str = "") -> Tuple[bool, MnemonicBackupData]:
        """
        Generate new mnemonic backup.
        
        Args:
            word_count: BIP39 word count (12, 15, 18, 21, 24)
            passphrase: Optional BIP39 passphrase (25th word)
        
        Returns:
            Tuple of (success, MnemonicBackupData)
        """
        try:
            if word_count not in [12, 15, 18, 21, 24]:
                return False, MnemonicBackupData(
                    mnemonic="",
                    passphrase=passphrase,
                    word_count=word_count,
                )
            
            entropy = self.entropy_gen.generate_entropy(word_count)
            quality = self.entropy_gen.validate_entropy(entropy)
            
            if not quality.is_valid:
                return False, MnemonicBackupData(
                    mnemonic="",
                    passphrase=passphrase,
                    word_count=word_count,
                )
            
            mnemonic = self.bip39_manager.entropy_to_mnemonic(entropy.hex())
            if not mnemonic:
                return False, MnemonicBackupData(
                    mnemonic="",
                    passphrase=passphrase,
                    word_count=word_count,
                )
            
            is_valid, message = self.bip39_manager.validate_mnemonic(mnemonic)
            if not is_valid:
                return False, MnemonicBackupData(
                    mnemonic="",
                    passphrase=passphrase,
                    word_count=word_count,
                )
            
            self.backup_data = MnemonicBackupData(
                mnemonic=mnemonic,
                passphrase=passphrase,
                word_count=word_count,
                created_at=datetime.utcnow().isoformat(),
                status=BackupStatus.PENDING,
            )
            
            return True, self.backup_data
        
        except Exception as e:
            return False, MnemonicBackupData(
                mnemonic="",
                passphrase=passphrase,
                word_count=word_count,
            )
    
    def validate_mnemonic(self, mnemonic: str) -> Tuple[bool, str]:
        """
        Validate mnemonic phrase.
        
        Args:
            mnemonic: Mnemonic phrase to validate
        
        Returns:
            Tuple of (is_valid, message)
        """
        is_valid, message = self.bip39_manager.validate_mnemonic(mnemonic)
        return is_valid, message
    
    def get_mnemonic_display(self) -> Optional[str]:
        """
        Get mnemonic for display (one-time display only).
        
        Returns:
            Mnemonic phrase or None if not available
        """
        if not self.backup_data:
            return None
        
        if self.backup_data.status == BackupStatus.CONFIRMED:
            return None
        
        self.backup_data.status = BackupStatus.DISPLAYED
        return self.backup_data.mnemonic
    
    def get_mnemonic_words(self) -> Optional[List[str]]:
        """
        Get mnemonic as word list.
        
        Returns:
            List of mnemonic words or None
        """
        if not self.backup_data:
            return None
        
        return self.backup_data.mnemonic.split()
    
    def get_mnemonic_word_indices(self) -> Optional[Dict[int, str]]:
        """
        Get mnemonic words with indices for user confirmation.
        
        Returns:
            Dictionary of {index: word} or None
        """
        words = self.get_mnemonic_words()
        if not words:
            return None
        
        return {i + 1: word for i, word in enumerate(words)}
    
    async def confirm_backup(self, confirmation_words: Dict[int, str]) -> Tuple[bool, str]:
        """
        Confirm backup by verifying user's mnemonic recollection.
        
        Args:
            confirmation_words: Dictionary of {index: word} from user
        
        Returns:
            Tuple of (success, message)
        """
        if not self.backup_data:
            return False, "No backup data available"
        
        self.backup_data.confirmation_attempts += 1
        
        mnemonic_words = self.backup_data.mnemonic.split()
        
        for idx, word in confirmation_words.items():
            if idx < 1 or idx > len(mnemonic_words):
                return False, f"Invalid word index: {idx}"
            
            expected_word = mnemonic_words[idx - 1]
            if word.lower().strip() != expected_word.lower().strip():
                return False, f"Word at position {idx} is incorrect"
        
        self.backup_data.status = BackupStatus.CONFIRMED
        self.backup_data.confirmed_at = datetime.utcnow().isoformat()
        
        return True, "Backup confirmed successfully"
    
    async def verify_mnemonic_against_backup(self, mnemonic: str) -> Tuple[bool, str]:
        """
        Verify provided mnemonic against stored backup.
        
        Args:
            mnemonic: Mnemonic to verify
        
        Returns:
            Tuple of (matches, message)
        """
        if not self.backup_data:
            return False, "No backup data available for comparison"
        
        is_valid, message = self.validate_mnemonic(mnemonic)
        if not is_valid:
            return False, f"Invalid mnemonic: {message}"
        
        if mnemonic.lower().strip() == self.backup_data.mnemonic.lower().strip():
            self.backup_data.status = BackupStatus.VERIFIED
            return True, "Mnemonic verified successfully"
        else:
            return False, "Mnemonic does not match backup"
    
    def export_for_storage(self) -> Optional[Dict[str, Any]]:
        """
        Export backup data for secure storage.
        
        Returns:
            Dictionary with backup data (mnemonic excluded for security)
        """
        if not self.backup_data:
            return None
        
        return {
            "word_count": self.backup_data.word_count,
            "has_passphrase": len(self.backup_data.passphrase) > 0,
            "created_at": self.backup_data.created_at,
            "confirmed_at": self.backup_data.confirmed_at,
            "status": self.backup_data.status.value,
            "confirmation_attempts": self.backup_data.confirmation_attempts,
        }
    
    def clear_backup(self):
        """Clear sensitive backup data from memory."""
        if self.backup_data:
            self.backup_data.mnemonic = ""
            self.backup_data.passphrase = ""
            self.backup_data = None
    
    def get_backup_status(self) -> Optional[str]:
        """Get current backup status."""
        if not self.backup_data:
            return None
        
        return self.backup_data.status.value
    
    def is_backup_confirmed(self) -> bool:
        """Check if backup has been confirmed."""
        if not self.backup_data:
            return False
        
        return self.backup_data.status in [BackupStatus.CONFIRMED, BackupStatus.VERIFIED]
    
    async def generate_test_questions(self, num_questions: int = 3) -> Optional[Dict[int, str]]:
        """
        Generate random questions for mnemonic verification.
        
        Args:
            num_questions: Number of questions to generate
        
        Returns:
            Dictionary of {position: word} questions or None
        """
        words = self.get_mnemonic_words()
        if not words or num_questions > len(words):
            return None
        
        import random
        
        positions = random.sample(range(1, len(words) + 1), num_questions)
        questions = {pos: f"What is word #{pos}?" for pos in sorted(positions)}
        
        return questions
    
    def get_backup_summary(self) -> Optional[Dict[str, Any]]:
        """
        Get summary of backup status.
        
        Returns:
            Dictionary with backup summary
        """
        if not self.backup_data:
            return None
        
        return {
            "word_count": self.backup_data.word_count,
            "status": self.backup_data.status.value,
            "created_at": self.backup_data.created_at,
            "confirmed_at": self.backup_data.confirmed_at,
            "confirmation_attempts": self.backup_data.confirmation_attempts,
            "is_confirmed": self.is_backup_confirmed(),
            "has_passphrase": len(self.backup_data.passphrase) > 0,
        }
