"""
Secure offline transaction signing for blockchain transactions.
Never exposes private keys to network - signing happens completely offline.
Supports Solana (USDC), Nano, and Arweave.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
import hashlib
import json
from enum import Enum

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
from nacl.signing import SigningKey
from nacl.encoding import HexEncoder
import base64


class SignatureType(Enum):
    """Signature algorithm types."""
    ED25519 = "ed25519"
    SECP256K1 = "secp256k1"
    RSA_PSS = "rsa_pss"


@dataclass
class SignedTransaction:
    """Signed transaction data."""
    transaction_id: str
    signature: str
    signed_data: str
    signature_type: SignatureType
    timestamp: float
    is_valid: bool = True
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "transaction_id": self.transaction_id,
            "signature": self.signature,
            "signed_data": self.signed_data,
            "signature_type": self.signature_type.value,
            "timestamp": self.timestamp,
            "is_valid": self.is_valid,
            "error": self.error,
        }


class OfflineSigner(ABC):
    """Base class for offline transaction signers."""
    
    def __init__(self, chain: str, asset: str):
        """
        Initialize offline signer.
        
        Args:
            chain: Blockchain type
            asset: Asset type
        """
        self.chain = chain
        self.asset = asset
    
    @abstractmethod
    async def sign_transaction(self, transaction: Dict[str, Any],
                              private_key: bytes) -> SignedTransaction:
        """
        Sign transaction with private key.
        
        Args:
            transaction: Transaction dictionary to sign
            private_key: Private key bytes
        
        Returns:
            SignedTransaction instance
        """
        pass
    
    @abstractmethod
    async def verify_signature(self, transaction: Dict[str, Any],
                              signature: str,
                              public_key: bytes) -> bool:
        """
        Verify transaction signature.
        
        Args:
            transaction: Original transaction dictionary
            signature: Signature to verify
            public_key: Public key bytes
        
        Returns:
            True if signature is valid
        """
        pass
    
    @staticmethod
    def _get_signature_type() -> SignatureType:
        """Get signature type for this signer."""
        raise NotImplementedError
    
    @staticmethod
    def _serialize_transaction(tx: Dict[str, Any]) -> bytes:
        """Serialize transaction for signing."""
        json_str = json.dumps(tx, separators=(',', ':'), sort_keys=True)
        return json_str.encode('utf-8')


class SolanaOfflineSigner(OfflineSigner):
    """Solana offline signer using Ed25519."""
    
    def __init__(self):
        """Initialize Solana offline signer."""
        super().__init__("solana", "usdc")
    
    async def sign_transaction(self, transaction: Dict[str, Any],
                              private_key: bytes) -> SignedTransaction:
        """
        Sign Solana transaction with Ed25519 private key.
        
        Args:
            transaction: Transaction dictionary
            private_key: Ed25519 private key bytes (32 bytes)
        
        Returns:
            SignedTransaction instance
        """
        try:
            if len(private_key) != 32:
                return SignedTransaction(
                    transaction_id=transaction.get("id", "unknown"),
                    signature="",
                    signed_data="",
                    signature_type=SignatureType.ED25519,
                    timestamp=0,
                    is_valid=False,
                    error="Invalid private key length for Ed25519 (must be 32 bytes)",
                )
            
            signing_key = SigningKey(private_key)
            
            tx_bytes = self._serialize_transaction(transaction)
            signature_obj = signing_key.sign(tx_bytes)
            signature = signature_obj.signature.hex()
            
            signed_tx = {
                **transaction,
                "signature": signature,
                "signed_at": signature_obj.signature,
            }
            signed_data = json.dumps(signed_tx, separators=(',', ':'))
            
            import time
            return SignedTransaction(
                transaction_id=transaction.get("id", hashlib.sha256(tx_bytes).hexdigest()[:16]),
                signature=signature,
                signed_data=signed_data,
                signature_type=SignatureType.ED25519,
                timestamp=time.time(),
                is_valid=True,
            )
        
        except Exception as e:
            import time
            return SignedTransaction(
                transaction_id=transaction.get("id", "unknown"),
                signature="",
                signed_data="",
                signature_type=SignatureType.ED25519,
                timestamp=time.time(),
                is_valid=False,
                error=f"Signing failed: {str(e)}",
            )
    
    async def verify_signature(self, transaction: Dict[str, Any],
                              signature: str,
                              public_key: bytes) -> bool:
        """
        Verify Solana transaction signature.
        
        Args:
            transaction: Original transaction dictionary
            signature: Signature hex string
            public_key: Ed25519 public key bytes (32 bytes)
        
        Returns:
            True if signature is valid
        """
        try:
            if len(public_key) != 32:
                return False
            
            from nacl.signing import VerifyKey
            from nacl.exceptions import BadSignatureError
            
            verify_key = VerifyKey(public_key)
            tx_bytes = self._serialize_transaction(transaction)
            signature_bytes = bytes.fromhex(signature)
            
            verify_key.verify(tx_bytes, signature_bytes)
            return True
        
        except Exception:
            return False
    
    @staticmethod
    def _get_signature_type() -> SignatureType:
        """Get signature type for Solana."""
        return SignatureType.ED25519


class NanoOfflineSigner(OfflineSigner):
    """Nano offline signer using Ed25519."""
    
    def __init__(self):
        """Initialize Nano offline signer."""
        super().__init__("nano", "nano")
    
    async def sign_transaction(self, transaction: Dict[str, Any],
                              private_key: bytes) -> SignedTransaction:
        """
        Sign Nano state block with Ed25519 private key.
        
        Args:
            transaction: State block dictionary
            private_key: Ed25519 private key bytes (32 bytes)
        
        Returns:
            SignedTransaction instance
        """
        try:
            if len(private_key) != 32:
                return SignedTransaction(
                    transaction_id=transaction.get("id", "unknown"),
                    signature="",
                    signed_data="",
                    signature_type=SignatureType.ED25519,
                    timestamp=0,
                    is_valid=False,
                    error="Invalid private key length for Ed25519 (must be 32 bytes)",
                )
            
            signing_key = SigningKey(private_key)
            
            tx_dict = {k: v for k, v in transaction.items() if k not in ["signature", "id"]}
            tx_bytes = self._serialize_transaction(tx_dict)
            
            signature_obj = signing_key.sign(tx_bytes)
            signature = signature_obj.signature.hex().upper()
            
            signed_tx = {
                **transaction,
                "signature": signature,
            }
            signed_data = json.dumps(signed_tx, separators=(',', ':'))
            
            import time
            block_hash = hashlib.sha256(tx_bytes).hexdigest()[:16]
            
            return SignedTransaction(
                transaction_id=block_hash,
                signature=signature,
                signed_data=signed_data,
                signature_type=SignatureType.ED25519,
                timestamp=time.time(),
                is_valid=True,
            )
        
        except Exception as e:
            import time
            return SignedTransaction(
                transaction_id=transaction.get("id", "unknown"),
                signature="",
                signed_data="",
                signature_type=SignatureType.ED25519,
                timestamp=time.time(),
                is_valid=False,
                error=f"Signing failed: {str(e)}",
            )
    
    async def verify_signature(self, transaction: Dict[str, Any],
                              signature: str,
                              public_key: bytes) -> bool:
        """
        Verify Nano state block signature.
        
        Args:
            transaction: Original state block dictionary
            signature: Signature hex string
            public_key: Ed25519 public key bytes (32 bytes)
        
        Returns:
            True if signature is valid
        """
        try:
            if len(public_key) != 32:
                return False
            
            from nacl.signing import VerifyKey
            
            verify_key = VerifyKey(public_key)
            tx_dict = {k: v for k, v in transaction.items() if k not in ["signature", "id"]}
            tx_bytes = self._serialize_transaction(tx_dict)
            
            signature_bytes = bytes.fromhex(signature)
            verify_key.verify(tx_bytes, signature_bytes)
            
            return True
        
        except Exception:
            return False
    
    @staticmethod
    def _get_signature_type() -> SignatureType:
        """Get signature type for Nano."""
        return SignatureType.ED25519


class ArweaveOfflineSigner(OfflineSigner):
    """Arweave offline signer using RSA-PSS."""
    
    def __init__(self):
        """Initialize Arweave offline signer."""
        super().__init__("arweave", "ar")
    
    async def sign_transaction(self, transaction: Dict[str, Any],
                              private_key_pem: bytes) -> SignedTransaction:
        """
        Sign Arweave transaction with RSA-4096 private key.
        
        Args:
            transaction: Transaction dictionary
            private_key_pem: RSA private key in PEM format
        
        Returns:
            SignedTransaction instance
        """
        try:
            private_key = serialization.load_pem_private_key(
                private_key_pem,
                password=None,
                backend=default_backend(),
            )
            
            if not isinstance(private_key, rsa.RSAPrivateKey):
                return SignedTransaction(
                    transaction_id=transaction.get("id", "unknown"),
                    signature="",
                    signed_data="",
                    signature_type=SignatureType.RSA_PSS,
                    timestamp=0,
                    is_valid=False,
                    error="Invalid private key type (must be RSA)",
                )
            
            tx_dict = {k: v for k, v in transaction.items() if k not in ["signature", "id"]}
            tx_bytes = self._serialize_transaction(tx_dict)
            
            signature = private_key.sign(
                tx_bytes,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
            
            signature_b64 = base64.urlsafe_b64encode(signature).decode('utf-8').rstrip('=')
            
            signed_tx = {
                **transaction,
                "signature": signature_b64,
            }
            signed_data = json.dumps(signed_tx, separators=(',', ':'))
            
            import time
            tx_hash = hashlib.sha256(tx_bytes).hexdigest()[:16]
            
            return SignedTransaction(
                transaction_id=tx_hash,
                signature=signature_b64,
                signed_data=signed_data,
                signature_type=SignatureType.RSA_PSS,
                timestamp=time.time(),
                is_valid=True,
            )
        
        except Exception as e:
            import time
            return SignedTransaction(
                transaction_id=transaction.get("id", "unknown"),
                signature="",
                signed_data="",
                signature_type=SignatureType.RSA_PSS,
                timestamp=time.time(),
                is_valid=False,
                error=f"Signing failed: {str(e)}",
            )
    
    async def verify_signature(self, transaction: Dict[str, Any],
                              signature: str,
                              public_key_pem: bytes) -> bool:
        """
        Verify Arweave transaction signature.
        
        Args:
            transaction: Original transaction dictionary
            signature: Signature base64url string
            public_key_pem: RSA public key in PEM format
        
        Returns:
            True if signature is valid
        """
        try:
            public_key = serialization.load_pem_public_key(
                public_key_pem,
                backend=default_backend(),
            )
            
            if not isinstance(public_key, rsa.RSAPublicKey):
                return False
            
            tx_dict = {k: v for k, v in transaction.items() if k not in ["signature", "id"]}
            tx_bytes = self._serialize_transaction(tx_dict)
            
            signature_b64 = signature + ('=' * (4 - len(signature) % 4))
            signature_bytes = base64.urlsafe_b64decode(signature_b64)
            
            public_key.verify(
                signature_bytes,
                tx_bytes,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
            
            return True
        
        except Exception:
            return False
    
    @staticmethod
    def _get_signature_type() -> SignatureType:
        """Get signature type for Arweave."""
        return SignatureType.RSA_PSS


class OfflineSignerFactory:
    """Factory for creating offline signers."""
    
    SIGNERS = {
        "solana": SolanaOfflineSigner,
        "nano": NanoOfflineSigner,
        "arweave": ArweaveOfflineSigner,
    }
    
    @classmethod
    def create(cls, chain: str) -> OfflineSigner:
        """
        Create offline signer for specified chain.
        
        Args:
            chain: Blockchain type (solana, nano, arweave)
        
        Returns:
            OfflineSigner instance
        
        Raises:
            ValueError: If chain is not supported
        """
        if chain not in cls.SIGNERS:
            raise ValueError(f"Unsupported chain: {chain}. Supported: {list(cls.SIGNERS.keys())}")
        
        signer_class = cls.SIGNERS[chain]
        return signer_class()
    
    @classmethod
    def get_supported_chains(cls) -> list:
        """Get list of supported chains."""
        return list(cls.SIGNERS.keys())
