"""
Arweave wallet generator.
Uses RSA-4096 keys in JWK format (not BIP39/BIP44).
"""
import json
import hashlib
import base64
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend


@dataclass
class ArweaveWallet:
    """Arweave wallet data structure with JWK format."""
    wallet_id: str
    jwk: Dict[str, Any]
    public_key: str
    address: str
    chain: str = "arweave"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'wallet_id': self.wallet_id,
            'jwk': self.jwk,
            'public_key': self.public_key,
            'address': self.address,
            'chain': self.chain,
        }
    
    def to_json(self) -> str:
        """Convert JWK to JSON string."""
        return json.dumps(self.jwk, indent=2)


class ArweaveWalletGenerator:
    """Generate Arweave wallets with RSA-4096 keys."""
    
    CHAIN = "arweave"
    KEY_SIZE = 4096
    PUBLIC_EXPONENT = 65537
    
    def __init__(self):
        """Initialize Arweave wallet generator."""
        pass
    
    def generate_new(self) -> ArweaveWallet:
        """
        Generate new Arweave wallet with RSA-4096 keypair.
        
        Returns:
            ArweaveWallet instance with JWK format
        """
        private_key = rsa.generate_private_key(
            public_exponent=self.PUBLIC_EXPONENT,
            key_size=self.KEY_SIZE,
            backend=default_backend()
        )
        
        public_key = private_key.public_key()
        
        jwk = self._private_key_to_jwk(private_key, public_key)
        
        public_key_str = self._export_public_key_pem(public_key)
        
        address = self._public_key_to_address(public_key)
        
        wallet_id = self._generate_wallet_id()
        
        return ArweaveWallet(
            wallet_id=wallet_id,
            jwk=jwk,
            public_key=public_key_str,
            address=address,
        )
    
    @staticmethod
    def _private_key_to_jwk(private_key, public_key) -> Dict[str, Any]:
        """
        Convert RSA private key to JWK format (Arweave format).
        
        Args:
            private_key: RSA private key object
            public_key: RSA public key object
        
        Returns:
            JWK dictionary
        """
        public_numbers = public_key.public_numbers()
        private_numbers = private_key.private_numbers()
        
        def int_to_base64(num: int, length: int) -> str:
            """Convert integer to base64url string."""
            byte_str = num.to_bytes(length, byteorder='big')
            return base64.urlsafe_b64encode(byte_str).decode('utf-8').rstrip('=')
        
        key_size_bytes = (public_numbers.n.bit_length() + 7) // 8
        
        jwk = {
            'kty': 'RSA',
            'e': int_to_base64(public_numbers.e, 3),
            'n': int_to_base64(public_numbers.n, key_size_bytes),
            'd': int_to_base64(private_numbers.d, key_size_bytes),
            'p': int_to_base64(private_numbers.p, key_size_bytes // 2),
            'q': int_to_base64(private_numbers.q, key_size_bytes // 2),
            'dp': int_to_base64(private_numbers.dmp1, key_size_bytes // 2),
            'dq': int_to_base64(private_numbers.dmq1, key_size_bytes // 2),
            'qi': int_to_base64(private_numbers.iqmp, key_size_bytes // 2),
        }
        
        return jwk
    
    @staticmethod
    def _export_public_key_pem(public_key) -> str:
        """
        Export public key as PEM format.
        
        Args:
            public_key: RSA public key object
        
        Returns:
            PEM-encoded public key string
        """
        pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return pem.decode('utf-8')
    
    @staticmethod
    def _public_key_to_address(public_key) -> str:
        """
        Convert RSA public key to Arweave address.
        
        Arweave address = SHA-256(public_key) in base64url format
        
        Args:
            public_key: RSA public key object
        
        Returns:
            Arweave address
        """
        pem_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        address_hash = hashlib.sha256(pem_bytes).digest()
        
        address = base64.urlsafe_b64encode(address_hash).decode('utf-8').rstrip('=')
        
        return address
    
    @staticmethod
    def _generate_wallet_id() -> str:
        """
        Generate unique wallet ID.
        
        Returns:
            Wallet ID (UUID-like)
        """
        import secrets
        wallet_id = base64.urlsafe_b64encode(secrets.token_bytes(16)).decode('utf-8').rstrip('=')
        return wallet_id
    
    @staticmethod
    def load_from_jwk(jwk: Dict[str, Any]) -> ArweaveWallet:
        """
        Load wallet from JWK dictionary.
        
        Args:
            jwk: JWK dictionary
        
        Returns:
            ArweaveWallet instance
        
        Raises:
            ValueError: If JWK is invalid
        """
        try:
            if jwk.get('kty') != 'RSA':
                raise ValueError("JWK must be RSA key type")
            
            required_fields = ['e', 'n']
            for field in required_fields:
                if field not in jwk:
                    raise ValueError(f"Missing required JWK field: {field}")
            
            private_key_pem = ArweaveWalletGenerator._jwk_to_pem(jwk)
            private_key = serialization.load_pem_private_key(
                private_key_pem.encode('utf-8'),
                password=None,
                backend=default_backend()
            )
            
            public_key = private_key.public_key()
            public_key_str = ArweaveWalletGenerator._export_public_key_pem(public_key)
            address = ArweaveWalletGenerator._public_key_to_address(public_key)
            wallet_id = ArweaveWalletGenerator._generate_wallet_id()
            
            return ArweaveWallet(
                wallet_id=wallet_id,
                jwk=jwk,
                public_key=public_key_str,
                address=address,
            )
        
        except Exception as e:
            raise ValueError(f"Failed to load JWK: {str(e)}")
    
    @staticmethod
    def _jwk_to_pem(jwk: Dict[str, Any]) -> str:
        """
        Convert JWK to PEM format.
        
        Args:
            jwk: JWK dictionary
        
        Returns:
            PEM-encoded private key
        """
        from cryptography.hazmat.primitives.asymmetric.rsa import (
            RSAPrivateNumbers, RSAPublicNumbers
        )
        
        def base64_to_int(val: str) -> int:
            """Convert base64url to integer."""
            padding = 4 - (len(val) % 4)
            val_padded = val + ('=' * padding)
            return int.from_bytes(
                base64.urlsafe_b64decode(val_padded),
                byteorder='big'
            )
        
        e = base64_to_int(jwk['e'])
        n = base64_to_int(jwk['n'])
        d = base64_to_int(jwk.get('d', ''))
        p = base64_to_int(jwk.get('p', ''))
        q = base64_to_int(jwk.get('q', ''))
        dp = base64_to_int(jwk.get('dp', ''))
        dq = base64_to_int(jwk.get('dq', ''))
        qi = base64_to_int(jwk.get('qi', ''))
        
        public_numbers = RSAPublicNumbers(e, n)
        private_numbers = RSAPrivateNumbers(p, q, d, dp, dq, qi, public_numbers)
        
        private_key = private_numbers.private_key(default_backend())
        
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        return pem.decode('utf-8')
    
    @staticmethod
    def validate_address(address: str) -> Tuple[bool, str]:
        """
        Validate Arweave address format.
        
        Args:
            address: Arweave address to validate
        
        Returns:
            Tuple of (is_valid, message)
        """
        try:
            if not address or not isinstance(address, str):
                return False, "Address must be a non-empty string"
            
            padding = 4 - (len(address) % 4)
            if padding != 4:
                address_padded = address + ('=' * padding)
            else:
                address_padded = address
            
            decoded = base64.urlsafe_b64decode(address_padded)
            
            if len(decoded) != 32:
                return False, f"Invalid address length: {len(decoded)} bytes (expected 32)"
            
            return True, "Address is valid"
        
        except Exception as e:
            return False, f"Address validation error: {str(e)}"
    
    @staticmethod
    def export_wallet_json(wallet: ArweaveWallet) -> str:
        """
        Export wallet as JSON string (safe for file storage).
        
        Args:
            wallet: ArweaveWallet instance
        
        Returns:
            JSON string with wallet data
        """
        return json.dumps(wallet.to_dict(), indent=2)
    
    @staticmethod
    def import_wallet_json(json_str: str) -> ArweaveWallet:
        """
        Import wallet from JSON string.
        
        Args:
            json_str: JSON string with wallet data
        
        Returns:
            ArweaveWallet instance
        
        Raises:
            ValueError: If JSON is invalid
        """
        try:
            data = json.loads(json_str)
            return ArweaveWallet(
                wallet_id=data['wallet_id'],
                jwk=data['jwk'],
                public_key=data['public_key'],
                address=data['address'],
            )
        except Exception as e:
            raise ValueError(f"Failed to import wallet JSON: {str(e)}")
