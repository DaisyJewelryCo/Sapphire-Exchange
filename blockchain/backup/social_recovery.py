"""
Social recovery using Shamir Secret Sharing (SLIP-39).
Allows splitting mnemonic across multiple recovery contacts.
"""
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import json

try:
    from shamir import SecretSharer
    HAS_SHAMIR = True
except ImportError:
    HAS_SHAMIR = False


class RecoveryContactStatus(Enum):
    """Recovery contact status."""
    PENDING = "pending"
    SHARED = "shared"
    CONFIRMED = "confirmed"
    REVOKED = "revoked"


@dataclass
class RecoveryContact:
    """Recovery contact information."""
    contact_id: str
    name: str
    share: str
    status: RecoveryContactStatus = RecoveryContactStatus.PENDING
    shared_at: Optional[str] = None
    confirmed_at: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "contact_id": self.contact_id,
            "name": self.name,
            "share": self.share,
            "status": self.status.value,
            "shared_at": self.shared_at,
            "confirmed_at": self.confirmed_at,
            "metadata": self.metadata or {},
        }


@dataclass
class RecoveryShareSet:
    """Set of recovery shares."""
    share_set_id: str
    total_shares: int
    threshold: int
    created_at: str
    contacts: List[RecoveryContact]
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "share_set_id": self.share_set_id,
            "total_shares": self.total_shares,
            "threshold": self.threshold,
            "created_at": self.created_at,
            "contact_count": len(self.contacts),
            "contacts": [c.to_dict() for c in self.contacts],
            "metadata": self.metadata or {},
        }


class SocialRecoveryManager:
    """Manage social recovery using secret sharing."""
    
    def __init__(self):
        """Initialize social recovery manager."""
        self.has_shamir = HAS_SHAMIR
    
    async def create_shares(self, mnemonic: str,
                           total_shares: int = 5,
                           threshold: int = 3) -> Tuple[bool, Optional[List[str]]]:
        """
        Create recovery shares from mnemonic using Shamir Secret Sharing.
        
        Args:
            mnemonic: BIP39 mnemonic phrase
            total_shares: Total number of shares to create
            threshold: Minimum shares needed for recovery
        
        Returns:
            Tuple of (success, list_of_shares)
        """
        if not self.has_shamir:
            return False, None
        
        try:
            if threshold > total_shares or threshold < 2:
                return False, None
            
            if not mnemonic or not isinstance(mnemonic, str):
                return False, None
            
            secret_bytes = mnemonic.encode('utf-8')
            shares = SecretSharer.split_secret(secret_bytes, total_shares, threshold)
            
            return True, [share.hex() for share in shares]
        
        except Exception as e:
            return False, None
    
    async def reconstruct_secret(self, shares: List[str]) -> Tuple[bool, Optional[str]]:
        """
        Reconstruct secret from recovery shares.
        
        Args:
            shares: List of share hex strings
        
        Returns:
            Tuple of (success, reconstructed_mnemonic)
        """
        if not self.has_shamir:
            return False, None
        
        try:
            if not shares or len(shares) < 2:
                return False, None
            
            share_bytes = [bytes.fromhex(share) for share in shares]
            secret_bytes = SecretSharer.recover_secret(share_bytes)
            mnemonic = secret_bytes.decode('utf-8')
            
            return True, mnemonic
        
        except Exception as e:
            return False, None
    
    async def create_recovery_scheme(self, mnemonic: str,
                                    contact_names: List[str],
                                    threshold: int = 3) -> Tuple[bool, Optional[RecoveryShareSet]]:
        """
        Create recovery scheme with named contacts.
        
        Args:
            mnemonic: BIP39 mnemonic phrase
            contact_names: List of contact names
            threshold: Minimum shares needed for recovery
        
        Returns:
            Tuple of (success, RecoveryShareSet)
        """
        try:
            total_shares = len(contact_names)
            
            if threshold > total_shares:
                return False, None
            
            success, shares = await self.create_shares(
                mnemonic,
                total_shares=total_shares,
                threshold=threshold
            )
            
            if not success or not shares:
                return False, None
            
            import os
            share_set_id = os.urandom(16).hex()
            
            contacts = []
            for i, name in enumerate(contact_names):
                contact_id = os.urandom(16).hex()
                contact = RecoveryContact(
                    contact_id=contact_id,
                    name=name,
                    share=shares[i],
                    status=RecoveryContactStatus.PENDING,
                )
                contacts.append(contact)
            
            recovery_set = RecoveryShareSet(
                share_set_id=share_set_id,
                total_shares=total_shares,
                threshold=threshold,
                created_at=datetime.utcnow().isoformat(),
                contacts=contacts,
            )
            
            return True, recovery_set
        
        except Exception as e:
            return False, None
    
    async def mark_share_shared(self, recovery_set: RecoveryShareSet,
                               contact_id: str) -> Tuple[bool, str]:
        """
        Mark share as shared with contact.
        
        Args:
            recovery_set: RecoveryShareSet instance
            contact_id: Contact ID
        
        Returns:
            Tuple of (success, message)
        """
        try:
            for contact in recovery_set.contacts:
                if contact.contact_id == contact_id:
                    contact.status = RecoveryContactStatus.SHARED
                    contact.shared_at = datetime.utcnow().isoformat()
                    return True, f"Share marked as shared with {contact.name}"
            
            return False, "Contact not found"
        
        except Exception as e:
            return False, str(e)
    
    async def confirm_share_received(self, recovery_set: RecoveryShareSet,
                                    contact_id: str) -> Tuple[bool, str]:
        """
        Confirm contact has received and secured their share.
        
        Args:
            recovery_set: RecoveryShareSet instance
            contact_id: Contact ID
        
        Returns:
            Tuple of (success, message)
        """
        try:
            for contact in recovery_set.contacts:
                if contact.contact_id == contact_id:
                    contact.status = RecoveryContactStatus.CONFIRMED
                    contact.confirmed_at = datetime.utcnow().isoformat()
                    return True, f"Confirmed receipt from {contact.name}"
            
            return False, "Contact not found"
        
        except Exception as e:
            return False, str(e)
    
    async def revoke_share(self, recovery_set: RecoveryShareSet,
                          contact_id: str) -> Tuple[bool, str]:
        """
        Revoke share from contact.
        
        Args:
            recovery_set: RecoveryShareSet instance
            contact_id: Contact ID
        
        Returns:
            Tuple of (success, message)
        """
        try:
            for contact in recovery_set.contacts:
                if contact.contact_id == contact_id:
                    contact.status = RecoveryContactStatus.REVOKED
                    return True, f"Share revoked from {contact.name}"
            
            return False, "Contact not found"
        
        except Exception as e:
            return False, str(e)
    
    def export_recovery_scheme(self, recovery_set: RecoveryShareSet) -> str:
        """
        Export recovery scheme to JSON.
        
        Args:
            recovery_set: RecoveryShareSet instance
        
        Returns:
            JSON string
        """
        return json.dumps(recovery_set.to_dict(), indent=2)
    
    def import_recovery_scheme(self, json_str: str) -> Optional[RecoveryShareSet]:
        """
        Import recovery scheme from JSON.
        
        Args:
            json_str: JSON string
        
        Returns:
            RecoveryShareSet or None
        """
        try:
            data = json.loads(json_str)
            
            contacts = []
            for contact_data in data.get("contacts", []):
                contact = RecoveryContact(
                    contact_id=contact_data["contact_id"],
                    name=contact_data["name"],
                    share=contact_data["share"],
                    status=RecoveryContactStatus(contact_data["status"]),
                    shared_at=contact_data.get("shared_at"),
                    confirmed_at=contact_data.get("confirmed_at"),
                )
                contacts.append(contact)
            
            return RecoveryShareSet(
                share_set_id=data["share_set_id"],
                total_shares=data["total_shares"],
                threshold=data["threshold"],
                created_at=data["created_at"],
                contacts=contacts,
            )
        
        except Exception as e:
            return None
    
    def get_recovery_instructions(self, recovery_set: RecoveryShareSet) -> str:
        """
        Get recovery instructions for scheme.
        
        Args:
            recovery_set: RecoveryShareSet instance
        
        Returns:
            Instructions text
        """
        instructions = f"""
SOCIAL RECOVERY INSTRUCTIONS
==============================

RECOVERY SCHEME DETAILS
Total Shares: {recovery_set.total_shares}
Threshold: {recovery_set.threshold}
Created: {recovery_set.created_at}

This recovery scheme splits your wallet seed phrase across {recovery_set.total_shares} 
recovery contacts. You need shares from at least {recovery_set.threshold} contacts to recover your wallet.

RECOVERY PROCESS
================

1. Contact at least {recovery_set.threshold} of your trusted recovery contacts
2. Request their recovery shares
3. Enter shares in recovery dialog (order doesn't matter)
4. Wallet will be reconstructed and recovered
5. Set new master password
6. Verify recovered addresses

DISTRIBUTION NOTES
===================

- Each contact has ONE share
- Never give your complete share list to anyone
- Each share alone is useless without others
- Minimum {recovery_set.threshold} shares needed for recovery
- Store contact information securely
- Update recovery scheme if relationships change

CONTACTS
========
"""
        
        for contact in recovery_set.contacts:
            instructions += f"""
Name: {contact.name}
Status: {contact.status.value}
Contact ID: {contact.contact_id}
"""
        
        return instructions
    
    @staticmethod
    def validate_recovery_scheme(recovery_set: RecoveryShareSet) -> Tuple[bool, str]:
        """
        Validate recovery scheme structure.
        
        Args:
            recovery_set: RecoveryShareSet instance
        
        Returns:
            Tuple of (is_valid, message)
        """
        if not recovery_set.share_set_id:
            return False, "Missing share_set_id"
        
        if recovery_set.total_shares < 2:
            return False, "Total shares must be at least 2"
        
        if recovery_set.threshold < 2:
            return False, "Threshold must be at least 2"
        
        if recovery_set.threshold > recovery_set.total_shares:
            return False, "Threshold cannot exceed total shares"
        
        if len(recovery_set.contacts) != recovery_set.total_shares:
            return False, "Contact count does not match total shares"
        
        for contact in recovery_set.contacts:
            if not contact.contact_id or not contact.name or not contact.share:
                return False, "Contact is missing required fields"
        
        return True, "Recovery scheme is valid"
    
    @staticmethod
    def get_recommended_schemes() -> Dict[str, Dict[str, int]]:
        """
        Get recommended recovery schemes.
        
        Returns:
            Dictionary of recommended schemes
        """
        return {
            "basic": {
                "total_shares": 3,
                "threshold": 2,
                "description": "Good for small groups (2 out of 3 needed)",
            },
            "standard": {
                "total_shares": 5,
                "threshold": 3,
                "description": "Recommended for most users (3 out of 5 needed)",
            },
            "enhanced": {
                "total_shares": 7,
                "threshold": 4,
                "description": "Maximum security (4 out of 7 needed)",
            },
        }
