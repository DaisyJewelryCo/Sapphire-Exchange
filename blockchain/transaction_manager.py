"""
Unified transaction manager orchestrating the complete transaction lifecycle.
Integrates: builder, signer, broadcaster, and tracker components.
Supports Solana (USDC), Nano, and Arweave.
"""
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import asyncio
import time

from blockchain.transaction_builder import (
    TransactionBuilder,
    TransactionBuilderFactory,
    TransactionData,
    TransactionType,
    TransactionPriority,
)
from blockchain.offline_signer import (
    OfflineSigner,
    OfflineSignerFactory,
    SignedTransaction,
)
from blockchain.broadcaster import (
    Broadcaster,
    BroadcasterFactory,
    BroadcastResult,
    BroadcastStatus,
)
from blockchain.transaction_tracker import (
    TransactionTracker,
    TransactionRecord,
    TransactionStatus,
)


class TransactionPhase(Enum):
    """Transaction processing phase."""
    PREPARED = "prepared"
    SIGNED = "signed"
    BROADCAST = "broadcast"
    TRACKING = "tracking"
    COMPLETED = "completed"


@dataclass
class TransactionWorkflow:
    """Complete transaction workflow with all components."""
    transaction_id: str
    chain: str
    asset: str
    phase: TransactionPhase
    built_transaction: Optional[Dict[str, Any]] = None
    signed_transaction: Optional[SignedTransaction] = None
    broadcast_result: Optional[BroadcastResult] = None
    transaction_record: Optional[TransactionRecord] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "transaction_id": self.transaction_id,
            "chain": self.chain,
            "asset": self.asset,
            "phase": self.phase.value,
            "built_transaction": self.built_transaction,
            "signed_transaction": self.signed_transaction.to_dict() if self.signed_transaction else None,
            "broadcast_result": self.broadcast_result.to_dict() if self.broadcast_result else None,
            "transaction_record": self.transaction_record.to_dict() if self.transaction_record else None,
            "error": self.error,
        }


class TransactionManager:
    """Manage complete transaction lifecycle."""
    
    def __init__(self, chain: str, rpc_url: str = None, db_path: str = None):
        """
        Initialize transaction manager.
        
        Args:
            chain: Blockchain type (solana, nano, arweave)
            rpc_url: RPC endpoint URL (optional)
            db_path: Database path for transaction history (optional)
        
        Raises:
            ValueError: If chain is not supported
        """
        self.chain = chain
        self.rpc_url = rpc_url
        self.db_path = db_path
        
        self.builder = TransactionBuilderFactory.create(chain, rpc_url=rpc_url)
        self.signer = OfflineSignerFactory.create(chain)
        self.broadcaster = BroadcasterFactory.create(chain, rpc_url=rpc_url) if rpc_url else None
        self.tracker = TransactionTracker(db_path)
        
        self.workflows: Dict[str, TransactionWorkflow] = {}
    
    async def prepare(self, tx_data: TransactionData) -> Tuple[bool, TransactionWorkflow]:
        """
        Prepare transaction (build and validate).
        
        Args:
            tx_data: TransactionData instance
        
        Returns:
            Tuple of (success, TransactionWorkflow)
        """
        try:
            workflow = TransactionWorkflow(
                transaction_id=f"{self.chain}_{int(time.time() * 1000)}",
                chain=self.chain,
                asset=tx_data.asset,
                phase=TransactionPhase.PREPARED,
            )
            
            built_tx = await self.builder.build(tx_data)
            is_valid, message = await self.builder.validate()
            
            if not is_valid:
                workflow.error = f"Transaction validation failed: {message}"
                return False, workflow
            
            workflow.built_transaction = built_tx
            self.workflows[workflow.transaction_id] = workflow
            
            return True, workflow
        
        except Exception as e:
            workflow = TransactionWorkflow(
                transaction_id=f"{self.chain}_{int(time.time() * 1000)}",
                chain=self.chain,
                asset=tx_data.asset,
                phase=TransactionPhase.PREPARED,
                error=f"Preparation failed: {str(e)}",
            )
            return False, workflow
    
    async def sign(self, workflow: TransactionWorkflow,
                  private_key: bytes) -> Tuple[bool, TransactionWorkflow]:
        """
        Sign prepared transaction.
        
        Args:
            workflow: TransactionWorkflow instance
            private_key: Private key bytes
        
        Returns:
            Tuple of (success, TransactionWorkflow)
        """
        try:
            if workflow.phase.value not in [TransactionPhase.PREPARED.value]:
                return False, workflow
            
            if not workflow.built_transaction:
                workflow.error = "No built transaction to sign"
                return False, workflow
            
            signed_tx = await self.signer.sign_transaction(
                workflow.built_transaction,
                private_key
            )
            
            if not signed_tx.is_valid:
                workflow.error = signed_tx.error
                return False, workflow
            
            workflow.signed_transaction = signed_tx
            workflow.phase = TransactionPhase.SIGNED
            self.workflows[workflow.transaction_id] = workflow
            
            return True, workflow
        
        except Exception as e:
            workflow.error = f"Signing failed: {str(e)}"
            return False, workflow
    
    async def broadcast(self, workflow: TransactionWorkflow,
                       timeout: int = 120) -> Tuple[bool, TransactionWorkflow]:
        """
        Broadcast signed transaction.
        
        Args:
            workflow: TransactionWorkflow instance
            timeout: Broadcast timeout in seconds
        
        Returns:
            Tuple of (success, TransactionWorkflow)
        """
        try:
            if workflow.phase.value != TransactionPhase.SIGNED.value:
                return False, workflow
            
            if not workflow.signed_transaction:
                workflow.error = "No signed transaction to broadcast"
                return False, workflow
            
            if not self.broadcaster:
                workflow.error = "Broadcaster not initialized (RPC URL required)"
                return False, workflow
            
            async with self.broadcaster as broadcaster:
                broadcast_result = await asyncio.wait_for(
                    broadcaster.broadcast(workflow.signed_transaction.signed_data),
                    timeout=timeout
                )
            
            if broadcast_result.status == BroadcastStatus.FAILED:
                workflow.error = broadcast_result.error
                return False, workflow
            
            workflow.broadcast_result = broadcast_result
            workflow.phase = TransactionPhase.BROADCAST
            self.workflows[workflow.transaction_id] = workflow
            
            return True, workflow
        
        except asyncio.TimeoutError:
            workflow.error = f"Broadcast timeout after {timeout}s"
            return False, workflow
        
        except Exception as e:
            workflow.error = f"Broadcast failed: {str(e)}"
            return False, workflow
    
    async def track(self, workflow: TransactionWorkflow,
                   tx_data: TransactionData,
                   public_key: bytes) -> Tuple[bool, TransactionWorkflow]:
        """
        Start tracking transaction.
        
        Args:
            workflow: TransactionWorkflow instance
            tx_data: Original TransactionData
            public_key: Public key for verification
        
        Returns:
            Tuple of (success, TransactionWorkflow)
        """
        try:
            if workflow.phase.value != TransactionPhase.BROADCAST.value:
                return False, workflow
            
            if not workflow.broadcast_result:
                workflow.error = "No broadcast result to track"
                return False, workflow
            
            tx_record = TransactionRecord(
                tx_id=workflow.transaction_id,
                chain=self.chain,
                asset=tx_data.asset,
                from_address=tx_data.sender_address,
                to_address=tx_data.recipient_address,
                amount=tx_data.amount,
                status=TransactionStatus.SUBMITTED,
                signature=workflow.signed_transaction.signature,
                broadcast_hash=workflow.broadcast_result.broadcast_hash,
                fee=tx_data.fee,
            )
            
            success = await self.tracker.track(tx_record)
            if not success:
                workflow.error = "Failed to track transaction"
                return False, workflow
            
            workflow.transaction_record = tx_record
            workflow.phase = TransactionPhase.TRACKING
            self.workflows[workflow.transaction_id] = workflow
            
            return True, workflow
        
        except Exception as e:
            workflow.error = f"Tracking failed: {str(e)}"
            return False, workflow
    
    async def execute_full_workflow(self, tx_data: TransactionData,
                                   private_key: bytes,
                                   public_key: bytes,
                                   wait_confirmation: bool = True,
                                   confirmation_timeout: int = 120) -> Tuple[bool, TransactionWorkflow]:
        """
        Execute complete transaction workflow.
        
        Args:
            tx_data: TransactionData instance
            private_key: Private key bytes
            public_key: Public key bytes
            wait_confirmation: Wait for confirmation
            confirmation_timeout: Confirmation timeout in seconds
        
        Returns:
            Tuple of (success, TransactionWorkflow)
        """
        success, workflow = await self.prepare(tx_data)
        if not success:
            return False, workflow
        
        success, workflow = await self.sign(workflow, private_key)
        if not success:
            return False, workflow
        
        success, workflow = await self.broadcast(workflow)
        if not success:
            return False, workflow
        
        success, workflow = await self.track(workflow, tx_data, public_key)
        if not success:
            return False, workflow
        
        if wait_confirmation and self.broadcaster:
            success = await self._wait_for_confirmation(
                workflow,
                confirmation_timeout
            )
            if not success:
                return False, workflow
        
        workflow.phase = TransactionPhase.COMPLETED
        self.workflows[workflow.transaction_id] = workflow
        
        return True, workflow
    
    async def _wait_for_confirmation(self, workflow: TransactionWorkflow,
                                    timeout: int = 120) -> bool:
        """Wait for transaction confirmation."""
        if not workflow.broadcast_result or not self.broadcaster:
            return False
        
        try:
            async with self.broadcaster as broadcaster:
                result = await asyncio.wait_for(
                    broadcaster.wait_confirmation(
                        workflow.broadcast_result.broadcast_hash,
                        timeout=timeout
                    ),
                    timeout=timeout + 10
                )
            
            if result.status == BroadcastStatus.CONFIRMED:
                await self.tracker.update_status(
                    workflow.transaction_id,
                    TransactionStatus.CONFIRMED,
                    confirmations=result.confirmations,
                    block_height=result.block_height,
                )
                return True
            
            elif result.status == BroadcastStatus.FAILED:
                await self.tracker.update_status(
                    workflow.transaction_id,
                    TransactionStatus.FAILED,
                    error=result.error,
                )
                return False
            
            else:
                await self.tracker.update_status(
                    workflow.transaction_id,
                    TransactionStatus.PENDING,
                )
                return False
        
        except asyncio.TimeoutError:
            await self.tracker.update_status(
                workflow.transaction_id,
                TransactionStatus.PENDING,
                error="Confirmation timeout",
            )
            return False
        
        except Exception as e:
            await self.tracker.update_status(
                workflow.transaction_id,
                TransactionStatus.PENDING,
                error=str(e),
            )
            return False
    
    async def get_workflow(self, transaction_id: str) -> Optional[TransactionWorkflow]:
        """Get transaction workflow by ID."""
        return self.workflows.get(transaction_id)
    
    async def get_transaction_status(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Get transaction status."""
        record = await self.tracker.get_transaction(transaction_id)
        if not record:
            return None
        
        return {
            "transaction_id": transaction_id,
            "status": record.status.value,
            "confirmations": record.confirmations,
            "block_height": record.block_height,
            "created_at": record.created_at,
            "submitted_at": record.submitted_at,
            "confirmed_at": record.confirmed_at,
            "error": record.error,
        }
    
    async def estimate_fee(self, tx_data: TransactionData) -> Optional[Dict[str, float]]:
        """Estimate transaction fee."""
        try:
            fee_estimate = await self.builder.estimate_fee(tx_data)
            return {
                "base_fee": fee_estimate.base_fee,
                "priority_fee": fee_estimate.priority_fee,
                "estimated_total": fee_estimate.estimated_total,
                "unit_limit": fee_estimate.unit_limit,
            }
        except Exception:
            return None
    
    async def list_pending_transactions(self, limit: int = 50) -> list:
        """List pending transactions."""
        return await self.tracker.list_pending(self.chain, limit)
    
    async def list_confirmed_transactions(self, limit: int = 50) -> list:
        """List confirmed transactions."""
        return await self.tracker.list_confirmed(self.chain, limit)
    
    async def get_transaction_history(self, address: str, limit: int = 100) -> list:
        """Get transaction history for address."""
        return await self.tracker.list_by_address(address, self.chain, limit)
    
    async def export_transaction_history(self, output_path: str = None) -> Optional[str]:
        """Export transaction history to JSON."""
        return await self.tracker.export_json(output_path)


class TransactionManagerFactory:
    """Factory for creating transaction managers."""
    
    @classmethod
    def create(cls, chain: str, rpc_url: str = None,
              db_path: str = None) -> TransactionManager:
        """
        Create transaction manager for specified chain.
        
        Args:
            chain: Blockchain type (solana, nano, arweave)
            rpc_url: RPC endpoint URL (optional)
            db_path: Database path (optional)
        
        Returns:
            TransactionManager instance
        
        Raises:
            ValueError: If chain is not supported
        """
        supported = ["solana", "nano", "arweave"]
        if chain not in supported:
            raise ValueError(f"Unsupported chain: {chain}. Supported: {supported}")
        
        return TransactionManager(chain, rpc_url, db_path)
    
    @classmethod
    def get_supported_chains(cls) -> list:
        """Get list of supported chains."""
        return ["solana", "nano", "arweave"]
