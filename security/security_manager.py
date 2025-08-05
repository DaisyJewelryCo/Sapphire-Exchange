"""
Enhanced security management for Sapphire Exchange.
Implements PBKDF2-HMAC-SHA256 password hashing, session management, and rate limiting.
"""
import os
from typing import List, Dict
import hashlib
import secrets
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class SessionData:
    """Session data structure."""
    user_id: str
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    session_token: str
    metadata: Dict = field(default_factory=dict)


class SecurityManager:
    """Enhanced security management following robot_info.json specifications."""
    
    def __init__(self):
        # From security_parameters section
        self.password_hash_algorithm = "PBKDF2-HMAC-SHA256"
        self.hash_iterations = 100000
        self.salt_length_bytes = 32
        
        # Session management
        self.session_timeout_minutes = 120
        self.inactivity_timeout_minutes = 30
        
        # Rate limiting
        self.requests_per_minute = 60
        self.burst_capacity = 10
        
        # Internal tracking
        self.rate_limit_tracker = {}  # IP -> request timestamps
        
    def hash_password(self, password: str, salt: bytes = None) -> Dict:
        """Hash password using PBKDF2-HMAC-SHA256.
        
        Args:
            password: Plain text password
            salt: Optional salt (generates new if not provided)
            
        Returns:
            Dict containing hash, salt, algorithm, and iterations
        """
        if salt is None:
            salt = os.urandom(self.salt_length_bytes)
            
        # Use specified algorithm and iterations
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            self.hash_iterations
        )
        
        return {
            'hash': key.hex(),
            'salt': salt.hex(),
            'algorithm': self.password_hash_algorithm,
            'iterations': self.hash_iterations
        }
    
    def verify_password(self, password: str, stored_hash: str, 
                       salt: str) -> bool:
        """Verify password against stored hash.
        
        Args:
            password: Plain text password to verify
            stored_hash: Stored password hash
            salt: Salt used for hashing
            
        Returns:
            True if password matches, False otherwise
        """
        try:
            salt_bytes = bytes.fromhex(salt)
            key = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt_bytes,
                self.hash_iterations
            )
            return key.hex() == stored_hash
        except Exception:
            return False
    
    def generate_secure_token(self, length: int = 32) -> str:
        """Generate cryptographically secure token.
        
        Args:
            length: Token length in bytes
            
        Returns:
            URL-safe base64 encoded token
        """
        return secrets.token_urlsafe(length)
    
    def check_rate_limit(self, identifier: str) -> Tuple[bool, Dict]:
        """Check if request is within rate limits.
        
        Args:
            identifier: Unique identifier (IP address, user ID, etc.)
            
        Returns:
            Tuple of (allowed, info_dict)
        """
        current_time = time.time()
        minute_ago = current_time - 60
        
        # Initialize tracker for new identifiers
        if identifier not in self.rate_limit_tracker:
            self.rate_limit_tracker[identifier] = []
        
        # Clean old requests (older than 1 minute)
        self.rate_limit_tracker[identifier] = [
            timestamp for timestamp in self.rate_limit_tracker[identifier]
            if timestamp > minute_ago
        ]
        
        request_count = len(self.rate_limit_tracker[identifier])
        
        # Check burst capacity (immediate requests)
        recent_requests = [
            timestamp for timestamp in self.rate_limit_tracker[identifier]
            if timestamp > current_time - 10  # Last 10 seconds
        ]
        
        if len(recent_requests) >= self.burst_capacity:
            return False, {
                'reason': 'burst_limit_exceeded',
                'requests_in_burst': len(recent_requests),
                'burst_capacity': self.burst_capacity,
                'retry_after': 10
            }
        
        # Check per-minute limit
        if request_count >= self.requests_per_minute:
            return False, {
                'reason': 'rate_limit_exceeded',
                'requests_per_minute': request_count,
                'limit': self.requests_per_minute,
                'retry_after': 60
            }
        
        # Record this request
        self.rate_limit_tracker[identifier].append(current_time)
        
        return True, {
            'requests_remaining': self.requests_per_minute - request_count - 1,
            'reset_time': minute_ago + 60
        }


class SessionManager:
    """Manage user sessions with timeout handling."""
    
    def __init__(self, security_manager: SecurityManager):
        self.security_manager = security_manager
        self.active_sessions = {}
        
    def create_session(self, user_id: str, metadata: Dict = None) -> str:
        """Create new user session.
        
        Args:
            user_id: User identifier
            metadata: Optional session metadata
            
        Returns:
            Session token
        """
        session_token = self.security_manager.generate_secure_token()
        now = datetime.now(timezone.utc)
        
        session_data = SessionData(
            user_id=user_id,
            created_at=now,
            last_activity=now,
            expires_at=now + timedelta(
                minutes=self.security_manager.session_timeout_minutes
            ),
            session_token=session_token,
            metadata=metadata or {}
        )
        
        self.active_sessions[session_token] = session_data
        return session_token
    
    def validate_session(self, session_token: str) -> Dict:
        """Validate session and check timeouts.
        
        Args:
            session_token: Session token to validate
            
        Returns:
            Dict with validation result and session data
        """
        if session_token not in self.active_sessions:
            return {'valid': False, 'reason': 'session_not_found'}
        
        session = self.active_sessions[session_token]
        now = datetime.now(timezone.utc)
        
        # Check session timeout
        if now > session.expires_at:
            del self.active_sessions[session_token]
            return {'valid': False, 'reason': 'session_expired'}
        
        # Check inactivity timeout
        inactivity_limit = session.last_activity + timedelta(
            minutes=self.security_manager.inactivity_timeout_minutes
        )
        
        if now > inactivity_limit:
            del self.active_sessions[session_token]
            return {'valid': False, 'reason': 'inactivity_timeout'}
        
        # Update last activity
        session.last_activity = now
        
        return {
            'valid': True,
            'user_id': session.user_id,
            'session_data': session,
            'expires_at': session.expires_at.isoformat(),
            'last_activity': session.last_activity.isoformat()
        }
    
    def destroy_session(self, session_token: str) -> bool:
        """Destroy a session.
        
        Args:
            session_token: Session token to destroy
            
        Returns:
            True if session was destroyed, False if not found
        """
        if session_token in self.active_sessions:
            del self.active_sessions[session_token]
            return True
        return False
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions."""
        now = datetime.now(timezone.utc)
        expired_tokens = []
        
        for token, session in self.active_sessions.items():
            if now > session.expires_at:
                expired_tokens.append(token)
        
        for token in expired_tokens:
            del self.active_sessions[token]
        
        return len(expired_tokens)
    
    def get_active_session_count(self) -> int:
        """Get count of active sessions."""
        return len(self.active_sessions)
    
    def get_user_sessions(self, user_id: str) -> List[SessionData]:
        """Get all active sessions for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of active sessions for the user
        """
        return [
            session for session in self.active_sessions.values()
            if session.user_id == user_id
        ]


class EncryptionManager:
    """Handle data encryption and decryption."""
    
    def __init__(self):
        self.encryption_methods = ["AES-256-GCM", "ChaCha20-Poly1305"]
        
    def encrypt_sensitive_data(self, data: str, key: bytes) -> Dict:
        """Encrypt sensitive data using AES-256-GCM.
        
        Args:
            data: Data to encrypt
            key: Encryption key (32 bytes for AES-256)
            
        Returns:
            Dict containing encrypted data and metadata
        """
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            
            # Generate random nonce
            nonce = os.urandom(12)  # 96-bit nonce for GCM
            
            # Encrypt data
            aesgcm = AESGCM(key)
            ciphertext = aesgcm.encrypt(nonce, data.encode(), None)
            
            return {
                'ciphertext': ciphertext.hex(),
                'nonce': nonce.hex(),
                'algorithm': 'AES-256-GCM',
                'key_length': len(key)
            }
            
        except Exception as e:
            raise ValueError(f"Encryption failed: {str(e)}")
    
    def decrypt_sensitive_data(self, encrypted_data: Dict, key: bytes) -> str:
        """Decrypt sensitive data.
        
        Args:
            encrypted_data: Dict containing encrypted data and metadata
            key: Decryption key
            
        Returns:
            Decrypted data as string
        """
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            
            ciphertext = bytes.fromhex(encrypted_data['ciphertext'])
            nonce = bytes.fromhex(encrypted_data['nonce'])
            
            # Decrypt data
            aesgcm = AESGCM(key)
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            
            return plaintext.decode()
            
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")
    
    def generate_encryption_key(self) -> bytes:
        """Generate a secure encryption key.
        
        Returns:
            32-byte encryption key for AES-256
        """
        return os.urandom(32)