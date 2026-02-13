"""
Funding Manager Service for Sapphire Exchange.
Provides robust configuration, validation, and orchestration for wallet funding operations.
"""

import json
import logging
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path


logger = logging.getLogger(__name__)


@dataclass
class FundingConfig:
    """Configuration for funding manager."""
    
    # Cloudflare Worker Configuration
    cloudflare_worker_url: str = "https://nano-sender.yourdomain.workers.dev/sendNano"
    cloudflare_api_key: str = ""
    
    # Solana Configuration
    solana_rpc_url: str = "https://api.mainnet-beta.solana.com"
    
    # Jupiter Configuration
    jupiter_quote_api: str = "https://quote-api.jup.ag/v6/quote"
    jupiter_swap_api: str = "https://quote-api.jup.ag/v6/swap"
    
    # USDC Configuration
    usdc_min_amount: float = 1.0
    usdc_max_amount: float = 1000.0
    
    # Arweave Configuration
    ar_min_amount: float = 0.001
    ar_max_amount: float = 100.0
    
    # Nano Configuration
    nano_min_amount: float = 0.001
    nano_max_amount: float = 1.0
    nano_rpc_url: str = "https://mynano.ninja/api"
    
    # Network Timeouts (seconds)
    request_timeout: int = 30
    health_check_timeout: int = 10
    
    # Retry Configuration
    max_retries: int = 3
    retry_delay: int = 2
    
    # Feature Flags
    enable_cloudflare_nano: bool = True
    enable_arweave_purchase: bool = True
    enable_balance_check: bool = True
    
    def validate(self) -> tuple[bool, List[str]]:
        """
        Validate configuration.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        if not self.cloudflare_worker_url:
            errors.append("Cloudflare worker URL not configured")
        
        if self.enable_cloudflare_nano and not self.cloudflare_api_key:
            errors.append("Cloudflare API key not set (required for Nano)")
        
        if self.usdc_min_amount <= 0:
            errors.append("USDC min amount must be positive")
        
        if self.usdc_max_amount <= self.usdc_min_amount:
            errors.append("USDC max amount must be greater than min amount")
        
        if self.nano_min_amount <= 0:
            errors.append("Nano min amount must be positive")
        
        if self.nano_max_amount <= self.nano_min_amount:
            errors.append("Nano max amount must be greater than min amount")
        
        return len(errors) == 0, errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FundingConfig":
        """Create config from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class FundingManagerService:
    """Service managing wallet funding operations."""
    
    CONFIG_FILE = "funding_config.json"
    LOG_FILE = "funding_transactions.log"
    
    def __init__(self, config: Optional[FundingConfig] = None):
        """Initialize funding manager service."""
        self.config = config or FundingConfig()
        self.logger = self._setup_logger()
        self.transaction_history: List[Dict[str, Any]] = []
        self._load_transaction_history()
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logging for funding transactions."""
        logger = logging.getLogger("funding_manager")
        logger.setLevel(logging.INFO)
        
        handler = logging.FileHandler(self.LOG_FILE)
        handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def _load_transaction_history(self):
        """Load transaction history from file."""
        try:
            if Path(self.LOG_FILE).exists():
                with open(self.LOG_FILE, 'r') as f:
                    lines = f.readlines()
                    self.transaction_history = [line.strip() for line in lines if line.strip()]
        except Exception as e:
            logger.warning(f"Could not load transaction history: {e}")
    
    def save_config(self, config: Optional[FundingConfig] = None):
        """Save configuration to file."""
        try:
            if config:
                self.config = config
            
            config_dict = self.config.to_dict()
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(config_dict, f, indent=2)
            
            self.logger.info("Configuration saved successfully")
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
            raise
    
    def load_config(self) -> bool:
        """Load configuration from file."""
        try:
            if Path(self.CONFIG_FILE).exists():
                with open(self.CONFIG_FILE, 'r') as f:
                    config_dict = json.load(f)
                    self.config = FundingConfig.from_dict(config_dict)
                    self.logger.info("Configuration loaded successfully")
                    return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            return False
    
    def log_transaction(self, transaction_type: str, details: Dict[str, Any], success: bool):
        """Log a funding transaction."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": transaction_type,
            "success": success,
            "details": details
        }
        
        self.logger.info(json.dumps(log_entry))
        self.transaction_history.append(json.dumps(log_entry))
    
    def get_transaction_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent transaction history."""
        history = []
        for entry in self.transaction_history[-limit:]:
            try:
                history.append(json.loads(entry))
            except json.JSONDecodeError:
                pass
        return history
    
    def validate_config(self) -> tuple[bool, List[str]]:
        """Validate current configuration."""
        return self.config.validate()
    
    def validate_nano_amount(self, amount: float) -> tuple[bool, str]:
        """
        Validate Nano amount.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if amount < self.config.nano_min_amount:
            return False, f"Minimum Nano amount is {self.config.nano_min_amount}"
        
        if amount > self.config.nano_max_amount:
            return False, f"Maximum Nano amount is {self.config.nano_max_amount}"
        
        return True, ""
    
    def validate_usdc_amount(self, amount: float) -> tuple[bool, str]:
        """
        Validate USDC amount.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if amount < self.config.usdc_min_amount:
            return False, f"Minimum USDC amount is {self.config.usdc_min_amount}"
        
        if amount > self.config.usdc_max_amount:
            return False, f"Maximum USDC amount is {self.config.usdc_max_amount}"
        
        return True, ""
    
    def validate_ar_amount(self, amount: float) -> tuple[bool, str]:
        """
        Validate Arweave amount.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if amount < self.config.ar_min_amount:
            return False, f"Minimum AR amount is {self.config.ar_min_amount}"
        
        if amount > self.config.ar_max_amount:
            return False, f"Maximum AR amount is {self.config.ar_max_amount}"
        
        return True, ""
    
    def get_config_status(self) -> Dict[str, Any]:
        """Get current configuration status."""
        is_valid, errors = self.validate_config()
        
        return {
            "is_valid": is_valid,
            "errors": errors,
            "cloudflare_configured": bool(self.config.cloudflare_api_key),
            "features": {
                "nano": self.config.enable_cloudflare_nano,
                "arweave": self.config.enable_arweave_purchase,
                "balance_check": self.config.enable_balance_check
            },
            "transaction_count": len(self.transaction_history)
        }


# Global instance
_funding_manager_service = None


def get_funding_manager_service() -> FundingManagerService:
    """Get or create the global funding manager service."""
    global _funding_manager_service
    
    if not _funding_manager_service:
        _funding_manager_service = FundingManagerService()
        _funding_manager_service.load_config()
    
    return _funding_manager_service
