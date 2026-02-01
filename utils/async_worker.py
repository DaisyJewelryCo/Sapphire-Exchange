"""
Async Worker for Sapphire Exchange.
Provides async operation support for PyQt5 applications using the main event loop.
"""

import asyncio
from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QCoreApplication


class AsyncWorker(QObject):
    """Worker for async operations using the main event loop."""
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    
    def __init__(self, coro):
        super().__init__()
        self.coro = coro
        self.retry_count = 0
        self.max_retries = 50  # 50 * 100ms = 5 seconds max
        self.task = None
    
    def start(self):
        """Start the async operation."""
        coro_name = self.coro.__name__ if hasattr(self.coro, '__name__') else 'coroutine'
        print(f"[AsyncWorker] Starting {coro_name}")
        # Start with a delay to ensure event loop is ready
        QTimer.singleShot(100, self._start_task)

    def _start_task(self):
        """Internal method to schedule the task on the event loop."""
        try:
            # Get the event loop
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError("Event loop is closed")
            
            # Check if Qt application is running
            qt_app = QCoreApplication.instance()
            if qt_app is None:
                raise RuntimeError("Qt application not running")
            
            # For qasync, use ensure_future without specifying the loop explicitly
            # This allows qasync to handle the loop binding properly
            print(f"[AsyncWorker] Creating task with ensure_future")
            self.task = asyncio.ensure_future(self._execute())
            return
                
        except RuntimeError as e:
            self.retry_count += 1
            if self.retry_count > self.max_retries:
                print(f"[AsyncWorker] Max retries exceeded: {e}")
                self.error.emit("Event loop failed to initialize")
                return
            
            if self.retry_count % 10 == 0:
                print(f"[AsyncWorker] Retrying... (attempt {self.retry_count}/{self.max_retries})")
            
            QTimer.singleShot(100, self._start_task)
        except Exception as e:
            print(f"[AsyncWorker] Unexpected error in _start_task: {e}")
            import traceback
            traceback.print_exc()
            self.error.emit(f"Failed to start task: {str(e)}")
            
    async def _execute(self):
        """Execute the coroutine and emit signals."""
        try:
            print(f"[AsyncWorker] Executing coroutine")
            result = await self.coro
            print(f"[AsyncWorker] Coroutine completed successfully")
            self.finished.emit(result)
        except Exception as e:
            print(f"[AsyncWorker] Exception in _execute: {e}")
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))



