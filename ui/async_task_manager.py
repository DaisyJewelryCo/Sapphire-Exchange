"""
Async task manager for non-blocking operations.
Handles blockchain operations without blocking the UI.
"""
import asyncio
from typing import Callable, Any, Optional, List, Dict
from dataclasses import dataclass
from enum import Enum
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from PyQt5.QtWidgets import QProgressDialog, QMessageBox
from qasync import asyncSlot


class TaskStatus(Enum):
    """Task status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskResult:
    """Result of task execution."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    status: TaskStatus = TaskStatus.COMPLETED


class AsyncTask:
    """Represents an async task."""
    
    def __init__(self, task_id: str, coro: Any, name: str = ""):
        self.task_id = task_id
        self.coro = coro
        self.name = name or task_id
        self.status = TaskStatus.PENDING
        self.result = None
        self.error = None
        self.task = None
    
    async def run(self) -> TaskResult:
        """Run the task."""
        try:
            self.status = TaskStatus.RUNNING
            self.task = asyncio.current_task()
            result = await self.coro
            self.result = result
            self.status = TaskStatus.COMPLETED
            return TaskResult(success=True, data=result, status=TaskStatus.COMPLETED)
        except asyncio.CancelledError:
            self.status = TaskStatus.CANCELLED
            return TaskResult(success=False, error="Task cancelled", status=TaskStatus.CANCELLED)
        except Exception as e:
            self.error = str(e)
            self.status = TaskStatus.FAILED
            return TaskResult(success=False, error=str(e), status=TaskStatus.FAILED)
    
    def cancel(self):
        """Cancel the task."""
        if self.task and not self.task.done():
            self.task.cancel()
        self.status = TaskStatus.CANCELLED


class AsyncTaskManager(QObject):
    """Manager for async tasks."""
    
    task_started = pyqtSignal(str)
    task_completed = pyqtSignal(str, TaskResult)
    task_failed = pyqtSignal(str, str)
    task_progress = pyqtSignal(str, int)
    
    def __init__(self):
        super().__init__()
        self.tasks: Dict[str, AsyncTask] = {}
        self.running_tasks = []
    
    async def execute(self, task_id: str, coro: Any, name: str = "",
                     show_progress: bool = False) -> TaskResult:
        """
        Execute async task.
        
        Args:
            task_id: Unique task identifier
            coro: Coroutine to execute
            name: Display name for task
            show_progress: Show progress dialog
        
        Returns:
            TaskResult with execution status
        """
        task = AsyncTask(task_id, coro, name)
        self.tasks[task_id] = task
        
        self.task_started.emit(task_id)
        
        try:
            result = await task.run()
            
            if result.success:
                self.task_completed.emit(task_id, result)
            else:
                self.task_failed.emit(task_id, result.error or "Unknown error")
            
            return result
        
        finally:
            if task_id in self.tasks:
                del self.tasks[task_id]
    
    async def execute_batch(self, tasks: List[tuple]) -> List[TaskResult]:
        """
        Execute multiple tasks concurrently.
        
        Args:
            tasks: List of (task_id, coroutine, name) tuples
        
        Returns:
            List of TaskResults
        """
        async_tasks = [
            self.execute(task_id, coro, name)
            for task_id, coro, name in tasks
        ]
        
        results = await asyncio.gather(*async_tasks, return_exceptions=True)
        
        return [
            r if isinstance(r, TaskResult) else TaskResult(success=False, error=str(r))
            for r in results
        ]
    
    def cancel_task(self, task_id: str):
        """Cancel a running task."""
        if task_id in self.tasks:
            self.tasks[task_id].cancel()
    
    def cancel_all(self):
        """Cancel all running tasks."""
        for task in self.tasks.values():
            task.cancel()
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get task status."""
        if task_id in self.tasks:
            return self.tasks[task_id].status
        return None


class ProgressDialogTaskRunner(QObject):
    """Runs async tasks with a progress dialog."""
    
    task_completed = pyqtSignal(bool, Any)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.progress_dialog = None
    
    async def run_with_progress(self, coro: Any, title: str = "Processing",
                               message: str = "Please wait...",
                               cancellable: bool = True) -> Any:
        """
        Run async task with progress dialog.
        
        Args:
            coro: Coroutine to execute
            title: Dialog title
            message: Dialog message
            cancellable: Allow cancellation
        
        Returns:
            Task result
        """
        self.progress_dialog = QProgressDialog(message, "Cancel", 0, 0)
        self.progress_dialog.setWindowTitle(title)
        self.progress_dialog.setModal(True)
        self.progress_dialog.setCancelButton(None if not cancellable else None)
        self.progress_dialog.show()
        
        try:
            result = await coro
            self.progress_dialog.close()
            self.task_completed.emit(True, result)
            return result
        
        except Exception as e:
            self.progress_dialog.close()
            self.task_completed.emit(False, str(e))
            raise


class BlockchainOperationManager(AsyncTaskManager):
    """Manager for blockchain-specific operations."""
    
    # Signals for blockchain operations
    balance_updated = pyqtSignal(str, str, str)  # asset, balance, usd_value
    transaction_confirmed = pyqtSignal(str, dict)  # tx_id, transaction_data
    wallet_synced = pyqtSignal(dict)  # wallet_data
    
    async def fetch_balance(self, asset: str, address: str) -> TaskResult:
        """
        Fetch balance for an asset.
        
        Args:
            asset: Blockchain asset (Solana, Nano, Arweave)
            address: Wallet address
        
        Returns:
            TaskResult with balance data
        """
        async def balance_coro():
            try:
                if asset.lower() == 'solana':
                    balance = await self._fetch_solana_balance(address)
                elif asset.lower() == 'nano':
                    balance = await self._fetch_nano_balance(address)
                elif asset.lower() == 'arweave':
                    balance = await self._fetch_arweave_balance(address)
                else:
                    raise ValueError(f"Unknown asset: {asset}")
                
                return balance
            
            except Exception as e:
                raise Exception(f"Failed to fetch {asset} balance: {str(e)}")
        
        result = await self.execute(f"balance_{asset}_{address[:10]}", balance_coro,
                                   f"Fetching {asset} balance")
        
        if result.success:
            balance = result.data.get('balance', '0')
            usd_value = result.data.get('usd_value', '$0.00')
            self.balance_updated.emit(asset, balance, usd_value)
        
        return result
    
    async def send_transaction(self, asset: str, recipient: str,
                              amount: str, signer=None) -> TaskResult:
        """
        Send transaction.
        
        Args:
            asset: Blockchain asset
            recipient: Recipient address
            amount: Amount to send
            signer: Transaction signer
        
        Returns:
            TaskResult with transaction ID
        """
        async def tx_coro():
            try:
                if asset.lower() == 'solana':
                    tx_id = await self._send_solana_transaction(recipient, amount, signer)
                elif asset.lower() == 'nano':
                    tx_id = await self._send_nano_transaction(recipient, amount, signer)
                elif asset.lower() == 'arweave':
                    tx_id = await self._send_arweave_transaction(recipient, amount, signer)
                else:
                    raise ValueError(f"Unknown asset: {asset}")
                
                return {'tx_id': tx_id, 'asset': asset, 'amount': amount}
            
            except Exception as e:
                raise Exception(f"Failed to send {asset} transaction: {str(e)}")
        
        return await self.execute(
            f"tx_{asset}_{recipient[:10]}",
            tx_coro,
            f"Sending {asset} transaction"
        )
    
    async def track_transaction(self, asset: str, tx_id: str, timeout: int = 300) -> TaskResult:
        """
        Track transaction confirmation.
        
        Args:
            asset: Blockchain asset
            tx_id: Transaction ID
            timeout: Timeout in seconds
        
        Returns:
            TaskResult with final transaction status
        """
        async def track_coro():
            start_time = asyncio.get_event_loop().time()
            
            while True:
                try:
                    if asset.lower() == 'solana':
                        status = await self._check_solana_tx(tx_id)
                    elif asset.lower() == 'nano':
                        status = await self._check_nano_tx(tx_id)
                    elif asset.lower() == 'arweave':
                        status = await self._check_arweave_tx(tx_id)
                    else:
                        raise ValueError(f"Unknown asset: {asset}")
                    
                    if status.get('confirmed'):
                        return status
                    
                    elapsed = asyncio.get_event_loop().time() - start_time
                    if elapsed > timeout:
                        raise TimeoutError(f"Transaction tracking timeout after {timeout}s")
                    
                    await asyncio.sleep(5)
                
                except Exception as e:
                    raise Exception(f"Failed to track {asset} transaction: {str(e)}")
        
        return await self.execute(
            f"track_{asset}_{tx_id[:10]}",
            track_coro,
            f"Tracking {asset} transaction"
        )
    
    async def sync_wallet(self, wallet_data: dict) -> TaskResult:
        """
        Synchronize wallet with blockchain.
        
        Args:
            wallet_data: Wallet information
        
        Returns:
            TaskResult with synced wallet data
        """
        async def sync_coro():
            try:
                synced = {'addresses': {}, 'balances': {}}
                
                for asset in ['solana', 'nano', 'arweave']:
                    address_key = f"address_{asset}"
                    if address_key in wallet_data:
                        address = wallet_data[address_key]
                        balance_result = await self.fetch_balance(asset, address)
                        
                        if balance_result.success:
                            synced['addresses'][asset] = address
                            synced['balances'][asset] = balance_result.data
                
                return synced
            
            except Exception as e:
                raise Exception(f"Wallet sync failed: {str(e)}")
        
        result = await self.execute("sync_wallet", sync_coro, "Syncing wallet")
        
        if result.success:
            self.wallet_synced.emit(result.data)
        
        return result
    
    async def _fetch_solana_balance(self, address: str) -> dict:
        """Fetch Solana balance (stub)."""
        await asyncio.sleep(0.5)
        return {'balance': '0.00', 'usd_value': '$0.00'}
    
    async def _fetch_nano_balance(self, address: str) -> dict:
        """Fetch Nano balance (stub)."""
        await asyncio.sleep(0.5)
        return {'balance': '0.00', 'usd_value': '$0.00'}
    
    async def _fetch_arweave_balance(self, address: str) -> dict:
        """Fetch Arweave balance (stub)."""
        await asyncio.sleep(0.5)
        return {'balance': '0.00', 'usd_value': '$0.00'}
    
    async def _send_solana_transaction(self, recipient: str, amount: str, signer) -> str:
        """Send Solana transaction (stub)."""
        await asyncio.sleep(1)
        return f"tx_{hash(recipient)}"
    
    async def _send_nano_transaction(self, recipient: str, amount: str, signer) -> str:
        """Send Nano transaction (stub)."""
        await asyncio.sleep(1)
        return f"tx_{hash(recipient)}"
    
    async def _send_arweave_transaction(self, recipient: str, amount: str, signer) -> str:
        """Send Arweave transaction (stub)."""
        await asyncio.sleep(1)
        return f"tx_{hash(recipient)}"
    
    async def _check_solana_tx(self, tx_id: str) -> dict:
        """Check Solana transaction status (stub)."""
        await asyncio.sleep(2)
        return {'confirmed': True, 'status': 'confirmed'}
    
    async def _check_nano_tx(self, tx_id: str) -> dict:
        """Check Nano transaction status (stub)."""
        await asyncio.sleep(2)
        return {'confirmed': True, 'status': 'confirmed'}
    
    async def _check_arweave_tx(self, tx_id: str) -> dict:
        """Check Arweave transaction status (stub)."""
        await asyncio.sleep(2)
        return {'confirmed': True, 'status': 'confirmed'}
