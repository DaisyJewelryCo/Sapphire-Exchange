"""
RSA key generation utilities for Sapphire Exchange.
Provides RSA key pair generation for auction items.
"""
import base64
from typing import Tuple, Dict
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding


class RSAKeyGenerator:
    """RSA key generation and management utilities."""
    
    @staticmethod
    def generate_key_pair(key_size: int = 2048) -> Tuple[str, str]:
        """
        Generate RSA key pair.
        
        Args:
            key_size: RSA key size in bits (default: 2048)
            
        Returns:
            Tuple of (private_key_pem, public_key_pem) as strings
        """
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size
        )
        
        # Get public key
        public_key = private_key.public_key()
        
        # Serialize private key to PEM format
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')
        
        # Serialize public key to PEM format
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        
        return private_pem, public_pem
    
    @staticmethod
    def generate_key_pair_base64(key_size: int = 2048) -> Tuple[str, str]:
        """
        Generate RSA key pair and return as base64 encoded strings.
        
        Args:
            key_size: RSA key size in bits (default: 2048)
            
        Returns:
            Tuple of (private_key_base64, public_key_base64) as strings
        """
        private_pem, public_pem = RSAKeyGenerator.generate_key_pair(key_size)
        
        # Convert to base64 for compact storage
        private_b64 = base64.b64encode(private_pem.encode('utf-8')).decode('utf-8')
        public_b64 = base64.b64encode(public_pem.encode('utf-8')).decode('utf-8')
        
        return private_b64, public_b64
    
    @staticmethod
    def get_key_fingerprint(public_key_pem: str) -> str:
        """
        Generate a fingerprint for the public key.
        
        Args:
            public_key_pem: Public key in PEM format
            
        Returns:
            SHA-256 fingerprint of the public key
        """
        import hashlib
        
        # Remove PEM headers and whitespace
        key_data = public_key_pem.replace('-----BEGIN PUBLIC KEY-----', '')
        key_data = key_data.replace('-----END PUBLIC KEY-----', '')
        key_data = key_data.replace('\n', '').replace(' ', '')
        
        # Generate SHA-256 hash
        fingerprint = hashlib.sha256(key_data.encode('utf-8')).hexdigest()
        
        # Format as colon-separated pairs
        return ':'.join(fingerprint[i:i+2] for i in range(0, len(fingerprint), 2))
    
    @staticmethod
    def create_auction_rsa_data(user_id: str, auction_id: str) -> Dict[str, str]:
        """
        Create RSA key pair data for an auction item.
        
        Args:
            user_id: User ID creating the auction
            auction_id: Auction/Item ID
            
        Returns:
            Dictionary containing RSA key data and metadata
        """
        private_key, public_key = RSAKeyGenerator.generate_key_pair()
        private_b64, public_b64 = RSAKeyGenerator.generate_key_pair_base64()
        fingerprint = RSAKeyGenerator.get_key_fingerprint(public_key)
        
        return {
            'private_key_pem': private_key,
            'public_key_pem': public_key,
            'private_key_base64': private_b64,
            'public_key_base64': public_b64,
            'fingerprint': fingerprint,
            'user_id': user_id,
            'auction_id': auction_id,
            'created_at': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()
        }


# Convenience functions
def generate_auction_rsa_keys(user_id: str, auction_id: str) -> Dict[str, str]:
    """Generate RSA keys for an auction item."""
    return RSAKeyGenerator.create_auction_rsa_data(user_id, auction_id)


def get_rsa_fingerprint(public_key_pem: str) -> str:
    """Get fingerprint for an RSA public key."""
    return RSAKeyGenerator.get_key_fingerprint(public_key_pem)


if __name__ == "__main__":
    # Test the RSA functionality
    print("Testing RSA key generation...")
    
    try:
        # Test key pair generation
        private_key, public_key = RSAKeyGenerator.generate_key_pair()
        print("✓ RSA key pair generated successfully")
        
        # Test fingerprint generation
        fingerprint = RSAKeyGenerator.get_key_fingerprint(public_key)
        print(f"✓ RSA fingerprint: {fingerprint[:32]}...")
        
        # Test auction RSA data creation
        rsa_data = RSAKeyGenerator.create_auction_rsa_data("test_user", "test_auction")
        print(f"✓ Auction RSA data created")
        print(f"   Fingerprint: {rsa_data['fingerprint'][:32]}...")
        print(f"   User ID: {rsa_data['user_id']}")
        print(f"   Auction ID: {rsa_data['auction_id']}")
        
        print("\n🎉 RSA utilities are working correctly!")
        
    except Exception as e:
        print(f"❌ RSA test failed: {e}")
        import traceback
        traceback.print_exc()