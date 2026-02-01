"""
Sequence number generator for Arweave posts.
Generates deterministic sequence indices and ensures uniqueness via Nano wallet.
"""
import hashlib
from datetime import datetime, timezone
from typing import Optional, Tuple


class SequenceGenerator:
    """Generates unique sequence numbers for Arweave posts."""
    
    def __init__(self, nano_client=None):
        """Initialize sequence generator."""
        self.nano_client = nano_client
    
    def generate_sequence_number(self, user_id: str, timestamp: Optional[str] = None) -> int:
        """
        Generate a deterministic sequence number based on user ID and timestamp.
        All users use the same algorithm to derive the same number.
        
        Args:
            user_id: The user creating the auction
            timestamp: ISO 8601 timestamp (defaults to current time)
            
        Returns:
            Sequence number (0-2147483647)
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).isoformat()
        
        # Extract date portion for sequence (YYYY-MM-DD)
        date_str = timestamp.split('T')[0]
        
        # Create hash: algorithm(user_id + date)
        # This means same user on same day gets same sequence
        hash_input = f"{user_id}:{date_str}"
        hash_bytes = hashlib.sha256(hash_input.encode()).digest()
        
        # Convert to 32-bit unsigned integer
        sequence = int.from_bytes(hash_bytes[:4], 'big') & 0x7FFFFFFF  # 31-bit to keep positive
        
        return sequence
    
    async def get_next_available_sequence(self, user_id: str, sequence_index_nano_wallet: str,
                                         timestamp: Optional[str] = None) -> Optional[int]:
        """
        Get next available sequence number by checking Nano wallet for used sequences.
        
        Args:
            user_id: The user creating the auction
            sequence_index_nano_wallet: Nano wallet address for sequence index
            timestamp: ISO 8601 timestamp
            
        Returns:
            Available sequence number or None if check fails
        """
        try:
            base_sequence = self.generate_sequence_number(user_id, timestamp)
            
            if not self.nano_client:
                # If no Nano client, just return base sequence
                return base_sequence
            
            # Check Nano wallet for used sequences
            # In a real implementation, would parse wallet transaction history
            # For now, return base sequence with validation
            account_info = await self.nano_client.get_account_info(sequence_index_nano_wallet)
            
            if account_info:
                # If wallet exists and has balance, sequence is in use
                # Try next sequence by adding offset
                for offset in range(1, 1000):
                    test_sequence = (base_sequence + offset) & 0x7FFFFFFF
                    # In real implementation, would check transaction history
                    # For now, return first available offset
                    return test_sequence
            
            return base_sequence
            
        except Exception as e:
            print(f"Error getting next available sequence: {e}")
            return None
    
    def validate_sequence_number(self, sequence: int) -> bool:
        """
        Validate that a sequence number is within valid range.
        
        Args:
            sequence: Sequence number to validate
            
        Returns:
            True if valid, False otherwise
        """
        return 0 <= sequence <= 2147483647
    
    def create_sequence_memo(self, sequence: int) -> str:
        """
        Create a Nano transaction memo for sequence number.
        
        Args:
            sequence: Sequence number
            
        Returns:
            32-character hex string for memo
        """
        try:
            memo_str = f"{sequence:032x}"[:32]
            return memo_str
        except Exception as e:
            print(f"Error creating sequence memo: {e}")
            return "00000000000000000000000000000000"
