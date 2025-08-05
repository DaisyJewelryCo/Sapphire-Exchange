"""
Application configuration for Sapphire Exchange.
Based on robot_info.json and More_Robot_info.json specifications.
"""
import os
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class UIConstants:
    """UI constants from robot_info.json."""
    default_page_size: int = 20
    max_title_length: int = 100
    max_description_length: int = 2000
    max_tags_per_item: int = 10
    max_tag_length: int = 20


@dataclass
class SecurityParameters:
    """Security parameters from robot_info.json."""
    password_hashing_algorithm: str = "PBKDF2-HMAC-SHA256"
    password_iterations: int = 100000
    salt_length_bytes: int = 32
    session_timeout_minutes: int = 120
    inactivity_timeout_minutes: int = 30
    requests_per_minute: int = 60
    burst_capacity: int = 10


@dataclass
class PerformanceParameters:
    """Performance parameters from robot_info.json."""
    cache_ttl_ms: int = 300000  # 5 minutes
    batch_size: int = 50
    max_concurrent_requests: int = 10
    request_timeout_ms: int = 30000


@dataclass
class ErrorHandling:
    """Error handling configuration from robot_info.json."""
    network_timeout_ms: int = 10000
    max_retries: int = 3
    backoff_factor: int = 2
    max_confirm_attempts: int = 10
    confirmation_delay_ms: int = 3000


class AppConfig:
    """Main application configuration class."""
    
    def __init__(self):
        """Initialize application configuration."""
        # Load configuration from robot_info.json specifications
        self.app_name = "Sapphire Exchange"
        self.app_version = "1.0.0"
        self.app_description = "Decentralized auction platform using Nano and Arweave, with DOGE-powered UI"
        
        # Primary currency configuration
        self.primary_currency = "DOGE"
        self.display_currency_toggle = True  # DOGE/USD toggle via CoinGecko
        
        # Configuration components
        self.ui = UIConstants()
        self.security = SecurityParameters()
        self.performance = PerformanceParameters()
        self.error_handling = ErrorHandling()
        
        # Environment-specific settings
        self.debug_mode = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
        self.mock_mode = os.getenv('MOCK_MODE', 'false').lower() == 'true'
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.log_file = os.getenv('LOG_FILE', 'sapphire_exchange.log')
        
        # API endpoints
        self.coingecko_api_url = "https://api.coingecko.com/api/v3"
        self.usps_api_url = os.getenv('USPS_API_URL', '')
        
        # Wallet configuration
        self.wallet_derivation_path = "m/44'/3'/0'/0/0"  # DOGE BIP44 path
        self.wallet_seed_standard = "BIP39"
        
        # Data integrity settings
        self.enable_data_verification = True
        self.enable_rsa_signature_check = True
        self.enable_blockchain_confirmation_tracking = True
    
    def get_currency_config(self) -> Dict[str, Any]:
        """Get currency configuration."""
        return {
            "primary": self.primary_currency,
            "display_toggle": self.display_currency_toggle,
            "supported_currencies": ["DOGE", "NANO", "USD"],
            "conversion_api": self.coingecko_api_url,
            "wallet_config": {
                "derivation_path": self.wallet_derivation_path,
                "standard": self.wallet_seed_standard,
                "secure_handling": {
                    "initial_display": True,
                    "allow_export": True,
                    "redisplay": False
                }
            }
        }
    
    def get_ui_config(self) -> Dict[str, Any]:
        """Get UI configuration."""
        return {
            "layout": {
                "sidebar_position": "left",
                "sidebar_visibility": "always",
                "bottom_bar_position": "bottom-left"
            },
            "constants": {
                "default_page_size": self.ui.default_page_size,
                "max_title_length": self.ui.max_title_length,
                "max_description_length": self.ui.max_description_length,
                "max_tags_per_item": self.ui.max_tags_per_item,
                "max_tag_length": self.ui.max_tag_length
            },
            "behavior": {
                "popup_behavior": "disabled",
                "page_navigation": "none",
                "bid_action_inline": True
            }
        }
    
    def get_security_config(self) -> Dict[str, Any]:
        """Get security configuration."""
        return {
            "password_hashing": {
                "algorithm": self.security.password_hashing_algorithm,
                "iterations": self.security.password_iterations,
                "salt_length_bytes": self.security.salt_length_bytes
            },
            "session": {
                "timeout_minutes": self.security.session_timeout_minutes,
                "inactivity_timeout_minutes": self.security.inactivity_timeout_minutes
            },
            "rate_limiting": {
                "requests_per_minute": self.security.requests_per_minute,
                "burst_capacity": self.security.burst_capacity
            },
            "data_integrity": {
                "enable_verification": self.enable_data_verification,
                "enable_rsa_check": self.enable_rsa_signature_check,
                "enable_confirmation_tracking": self.enable_blockchain_confirmation_tracking
            }
        }
    
    def get_performance_config(self) -> Dict[str, Any]:
        """Get performance configuration."""
        return {
            "cache": {
                "ttl_ms": self.performance.cache_ttl_ms,
                "batch_size": self.performance.batch_size
            },
            "network": {
                "max_concurrent_requests": self.performance.max_concurrent_requests,
                "request_timeout_ms": self.performance.request_timeout_ms
            },
            "error_handling": {
                "network_timeout_ms": self.error_handling.network_timeout_ms,
                "max_retries": self.error_handling.max_retries,
                "backoff_factor": self.error_handling.backoff_factor,
                "max_confirm_attempts": self.error_handling.max_confirm_attempts,
                "confirmation_delay_ms": self.error_handling.confirmation_delay_ms
            }
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "application": {
                "name": self.app_name,
                "version": self.app_version,
                "description": self.app_description,
                "debug_mode": self.debug_mode,
                "mock_mode": self.mock_mode
            },
            "currency": self.get_currency_config(),
            "ui": self.get_ui_config(),
            "security": self.get_security_config(),
            "performance": self.get_performance_config()
        }
    
    def validate(self) -> bool:
        """Validate configuration settings."""
        try:
            # Validate UI constants
            assert self.ui.max_title_length > 0
            assert self.ui.max_description_length > 0
            assert self.ui.max_tags_per_item > 0
            assert self.ui.max_tag_length > 0
            
            # Validate security parameters
            assert self.security.password_iterations > 0
            assert self.security.salt_length_bytes > 0
            assert self.security.session_timeout_minutes > 0
            
            # Validate performance parameters
            assert self.performance.cache_ttl_ms > 0
            assert self.performance.batch_size > 0
            assert self.performance.max_concurrent_requests > 0
            
            return True
        except AssertionError:
            return False


# Global configuration instance
app_config = AppConfig()