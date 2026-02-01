"""
Session management with automatic locking and unlock rate limiting.
Manages user sessions with timeout-based auto-lock and failed attempt tracking.
"""
import time
import secrets
from typing import Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from security.password_manager import PasswordManager, DerivedKey


@dataclass
class SessionToken:
    """Session token with expiry."""
    token: str
    created_at: float
    last_activity: float
    expires_at: float
    is_valid: bool = True


@dataclass
class UnlockAttempt:
    """Unlock attempt record."""
    timestamp: float
    success: bool
    ip_address: str = "local"


class SessionManager:
    """Manage wallet sessions with auto-lock and rate limiting."""
    
    DEFAULT_SESSION_TIMEOUT = 30 * 60
    DEFAULT_LOCK_TIMEOUT = 60
    DEFAULT_MAX_ATTEMPTS = 5
    DEFAULT_ATTEMPT_WINDOW = 300
    
    def __init__(self, password_manager: PasswordManager,
                 session_timeout: int = None,
                 max_unlock_attempts: int = None,
                 attempt_window: int = None):
        """
        Initialize session manager.
        
        Args:
            password_manager: PasswordManager instance
            session_timeout: Session timeout in seconds (default: 30 min)
            max_unlock_attempts: Max unlock attempts before lockout
            attempt_window: Time window for counting attempts (seconds)
        """
        self.password_manager = password_manager
        self.session_timeout = session_timeout or self.DEFAULT_SESSION_TIMEOUT
        self.max_unlock_attempts = max_unlock_attempts or self.DEFAULT_MAX_ATTEMPTS
        self.attempt_window = attempt_window or self.DEFAULT_ATTEMPT_WINDOW
        
        self.session_token: Optional[SessionToken] = None
        self.derived_key: Optional[DerivedKey] = None
        self.unlock_attempts: list = []
        self.is_locked = True
    
    def unlock(self, password: str, password_hash: str = None,
              salt: bytes = None) -> Tuple[bool, str]:
        """
        Unlock session with password.
        
        Args:
            password: Master password
            password_hash: Optional hash to verify (from password_manager)
            salt: Optional salt for key derivation
        
        Returns:
            Tuple of (success, message)
        """
        current_time = time.time()
        
        if self._is_locked_out(current_time):
            lockout_time = self._get_lockout_time()
            return False, f"Too many failed attempts. Locked out for {lockout_time} seconds."
        
        if password_hash and not self.password_manager.verify_password(password, password_hash):
            self.unlock_attempts.append(UnlockAttempt(current_time, False))
            remaining = self.max_unlock_attempts - len(self._recent_failed_attempts(current_time))
            return False, f"Invalid password. {remaining} attempts remaining."
        
        try:
            self.derived_key = self.password_manager.derive_key(password, salt)
            
            self.session_token = SessionToken(
                token=secrets.token_urlsafe(32),
                created_at=current_time,
                last_activity=current_time,
                expires_at=current_time + self.session_timeout,
            )
            
            self.is_locked = False
            self.unlock_attempts.append(UnlockAttempt(current_time, True))
            
            return True, "Session unlocked successfully"
        
        except Exception as e:
            return False, f"Unlock failed: {str(e)}"
    
    def lock(self) -> bool:
        """
        Lock session.
        
        Returns:
            True if successful
        """
        self.is_locked = True
        self.session_token = None
        
        if self.derived_key:
            self.derived_key = None
        
        return True
    
    def is_unlocked(self) -> bool:
        """
        Check if session is currently unlocked.
        
        Returns:
            True if unlocked and token valid
        """
        if self.is_locked or not self.session_token:
            return False
        
        current_time = time.time()
        
        if current_time > self.session_token.expires_at:
            self.lock()
            return False
        
        return True
    
    def refresh_session(self) -> bool:
        """
        Refresh session token (extend timeout).
        
        Returns:
            True if successful
        """
        if not self.is_unlocked():
            return False
        
        current_time = time.time()
        self.session_token.last_activity = current_time
        self.session_token.expires_at = current_time + self.session_timeout
        
        return True
    
    def get_session_token(self) -> Optional[str]:
        """
        Get current session token.
        
        Returns:
            Token string or None if not unlocked
        """
        if self.is_unlocked():
            return self.session_token.token
        return None
    
    def verify_session_token(self, token: str) -> bool:
        """
        Verify session token.
        
        Args:
            token: Token to verify
        
        Returns:
            True if token is valid and current
        """
        if not self.is_unlocked():
            return False
        
        if self.session_token.token != token:
            return False
        
        return True
    
    def get_derived_key(self) -> Optional[DerivedKey]:
        """
        Get derived encryption key (only if unlocked).
        
        Returns:
            DerivedKey or None
        """
        if self.is_unlocked():
            return self.derived_key
        return None
    
    def get_session_info(self) -> dict:
        """
        Get current session information.
        
        Returns:
            Dict with session info
        """
        if not self.is_unlocked():
            return {
                'is_unlocked': False,
                'is_locked': True,
                'session_token': None,
            }
        
        current_time = time.time()
        expires_in = max(0, self.session_token.expires_at - current_time)
        
        return {
            'is_unlocked': True,
            'is_locked': False,
            'session_token': self.session_token.token[:16] + '...',
            'created_at': datetime.fromtimestamp(self.session_token.created_at).isoformat(),
            'expires_in': int(expires_in),
            'expires_at': datetime.fromtimestamp(self.session_token.expires_at).isoformat(),
        }
    
    def get_unlock_history(self, limit: int = 10) -> list:
        """
        Get recent unlock attempts.
        
        Args:
            limit: Max number of attempts to return
        
        Returns:
            List of UnlockAttempt
        """
        return self.unlock_attempts[-limit:]
    
    def _is_locked_out(self, current_time: float) -> bool:
        """
        Check if too many failed unlock attempts.
        
        Args:
            current_time: Current time (seconds since epoch)
        
        Returns:
            True if locked out
        """
        recent_failed = self._recent_failed_attempts(current_time)
        return len(recent_failed) >= self.max_unlock_attempts
    
    def _recent_failed_attempts(self, current_time: float) -> list:
        """
        Get failed unlock attempts within window.
        
        Args:
            current_time: Current time
        
        Returns:
            List of recent failed UnlockAttempt
        """
        window_start = current_time - self.attempt_window
        
        recent = [
            attempt for attempt in self.unlock_attempts
            if attempt.timestamp > window_start and not attempt.success
        ]
        
        return recent
    
    def _get_lockout_time(self) -> int:
        """
        Get remaining lockout time in seconds.
        
        Returns:
            Seconds until lockout expires
        """
        if not self.unlock_attempts:
            return 0
        
        last_failed = None
        for attempt in reversed(self.unlock_attempts):
            if not attempt.success:
                last_failed = attempt.timestamp
                break
        
        if not last_failed:
            return 0
        
        current_time = time.time()
        lockout_end = last_failed + self.attempt_window
        remaining = max(0, int(lockout_end - current_time))
        
        return remaining
    
    def clear_attempt_history(self):
        """Clear unlock attempt history."""
        self.unlock_attempts.clear()


class SessionTimeout:
    """Monitor and enforce session timeouts."""
    
    def __init__(self, session_manager: SessionManager,
                 check_interval: int = 60):
        """
        Initialize session timeout monitor.
        
        Args:
            session_manager: SessionManager instance
            check_interval: How often to check for timeout (seconds)
        """
        self.session_manager = session_manager
        self.check_interval = check_interval
        self.last_check = time.time()
    
    def check_timeout(self) -> bool:
        """
        Check if session should timeout.
        
        Returns:
            True if session timed out and locked
        """
        current_time = time.time()
        
        if current_time - self.last_check < self.check_interval:
            return False
        
        self.last_check = current_time
        
        if self.session_manager.is_unlocked():
            if current_time > self.session_manager.session_token.expires_at:
                self.session_manager.lock()
                return True
        
        return False
