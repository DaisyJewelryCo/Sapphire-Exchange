"""
Incoming Transaction Detector for Sapphire Exchange.
Detects and tracks incoming SOL/USDC transactions from external sources.
"""
import asyncio
from typing import Dict, Optional, List, Set
from datetime import datetime, timezone
from services.solana_balance_service import get_solana_balance_service
from services.transaction_tracker import get_transaction_tracker


class IncomingTransactionDetector:
    """Detects and tracks incoming transactions."""
    
    def __init__(self):
        """Initialize the detector."""
        self.tracked_signatures: Set[str] = set()
        self.last_checked_slot: Optional[int] = None
    
    async def detect_incoming_transactions(
        self, 
        wallet_address: str,
        known_signatures: Optional[Set[str]] = None
    ) -> List[Dict]:
        """
        Detect incoming transactions to a wallet.
        
        Args:
            wallet_address: Solana wallet address to monitor
            known_signatures: Set of already-tracked transaction signatures to skip
        
        Returns:
            List of new incoming transactions
        """
        if known_signatures is None:
            known_signatures = set()
        
        balance_service = await get_solana_balance_service()
        tracker = await get_transaction_tracker()
        
        recent_txs = await balance_service.get_recent_transactions(wallet_address, limit=20)
        
        if not recent_txs:
            return []
        
        incoming = []
        for tx_info in recent_txs:
            signature = tx_info.get("signature", "")
            
            if not signature or signature in known_signatures or signature in self.tracked_signatures:
                continue
            
            if tx_info.get("err") is not None:
                continue
            
            details = await balance_service.get_transaction_details(signature)
            if not details:
                continue
            
            tx_result = self._parse_transaction(details, wallet_address, signature)
            if tx_result and tx_result.get("type") == "receive":
                incoming.append(tx_result)
                self.tracked_signatures.add(signature)
        
        return incoming
    
    def _parse_transaction(self, tx_details: Dict, wallet_address: str, signature: str) -> Optional[Dict]:
        """Parse transaction details to extract incoming transfer info."""
        try:
            if not tx_details:
                return None
            
            meta = tx_details.get("meta", {})
            if not meta:
                return None
            
            account_keys = tx_details.get("transaction", {}).get("message", {}).get("accountKeys", [])
            
            post_token_balances = meta.get("postTokenBalances", [])
            pre_token_balances = meta.get("preTokenBalances", [])
            
            pre_balances_map = {}
            for b in pre_token_balances:
                idx = b.get("accountIndex")
                amt = b.get("uiTokenAmount", {}).get("amount", "0")
                pre_balances_map[idx] = float(amt)
            
            for post_balance in post_token_balances:
                account_idx = post_balance.get("accountIndex")
                
                if account_idx >= len(account_keys):
                    continue
                
                account = account_keys[account_idx]
                
                if account != wallet_address:
                    continue
                
                mint = post_balance.get("mint", "")
                try:
                    post_amount = float(post_balance.get("uiTokenAmount", {}).get("amount", "0"))
                except (ValueError, TypeError):
                    post_amount = 0
                
                pre_amount = pre_balances_map.get(account_idx, 0)
                
                if post_amount > pre_amount:
                    amount_diff = post_amount - pre_amount
                    return {
                        "signature": signature,
                        "type": "receive",
                        "currency": self._mint_to_currency(mint),
                        "amount": str(amount_diff),
                        "to_address": wallet_address,
                        "block_time": tx_details.get("blockTime")
                    }
            
            return None
        except Exception as e:
            print(f"Error parsing transaction {signature}: {e}")
            return None
    
    def _mint_to_currency(self, mint: Optional[str]) -> str:
        """Convert Solana token mint to currency symbol."""
        if not mint:
            return "SOL"
        
        mint_map = {
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": "USDC",
            "So11111111111111111111111111111111111111112": "SOL"
        }
        return mint_map.get(mint, "SOL")
    
    async def track_incoming_transaction(
        self,
        user_id: str,
        tx_info: Dict
    ) -> bool:
        """Track an incoming transaction in the transaction tracker."""
        try:
            tracker = await get_transaction_tracker()
            
            tx = tracker.create_transaction(
                user_id=user_id,
                currency=tx_info.get("currency", "SOL"),
                tx_type="receive",
                amount=tx_info.get("amount", "0"),
                from_address="external",
                to_address=tx_info.get("to_address", ""),
                tx_hash=tx_info.get("signature", ""),
                metadata={
                    "source": "incoming",
                    "block_time": tx_info.get("block_time"),
                    "auto_detected": True
                }
            )
            
            await tracker.track_pending_transaction(tx)
            print(f"Tracked incoming transaction: {tx.id} ({tx_info.get('amount')} {tx_info.get('currency')})")
            return True
        except Exception as e:
            print(f"Error tracking incoming transaction: {e}")
            return False


_detector = None


async def get_incoming_transaction_detector() -> IncomingTransactionDetector:
    """Get or create the incoming transaction detector singleton."""
    global _detector
    if _detector is None:
        _detector = IncomingTransactionDetector()
    return _detector
