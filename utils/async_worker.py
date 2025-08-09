"""
Async Worker for Sapphire Exchange.
Provides thread-based async operation support for PyQt5 applications.
"""

import asyncio
from PyQt5.QtCore import QThread, pyqtSignal


class AsyncWorker(QThread):
    """Worker thread for async operations."""
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    
    def __init__(self, coro):
        super().__init__()
        self.coro = coro
    
    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.coro)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            loop.close()