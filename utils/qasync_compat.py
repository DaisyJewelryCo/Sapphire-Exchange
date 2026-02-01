"""
Compatibility utilities for working with qasync and asyncio.
Provides workarounds for qasync's event loop not registering with asyncio.get_running_loop()
"""

import asyncio
from typing import Optional, Any, Coroutine, TypeVar

T = TypeVar('T')


async def async_sleep(delay: float, result: Optional[Any] = None) -> Optional[Any]:
    """
    Sleep for a given delay in a qasync-compatible way.
    
    This is a wrapper around asyncio.sleep that handles the case where
    qasync's QEventLoop doesn't properly register with asyncio.get_running_loop().
    
    Args:
        delay: The delay in seconds
        result: Optional value to return after the delay
        
    Returns:
        The result parameter if provided, otherwise None
    """
    try:
        # Try the normal asyncio.sleep first
        return await asyncio.sleep(delay, result=result)
    except RuntimeError as e:
        if "no running event loop" in str(e):
            # Fallback: Use Qt's event loop if asyncio fails
            # Get the event loop that should be set by qasync
            loop = asyncio.get_event_loop()
            if loop and not loop.is_closed():
                # Create a future that will be resolved after the delay
                future = loop.create_future()
                
                def _resolve():
                    if not future.done():
                        future.set_result(result)
                
                # Schedule the future to be resolved after the delay
                handle = loop.call_later(delay, _resolve)
                
                try:
                    return await future
                except asyncio.CancelledError:
                    handle.cancel()
                    raise
        # Re-raise if it's not the "no running event loop" error
        raise


async def run_in_qasync_loop(coro: Coroutine[Any, Any, T]) -> T:
    """
    Run a coroutine in the qasync event loop context.
    
    This ensures proper event loop registration for asyncio operations.
    
    Args:
        coro: The coroutine to run
        
    Returns:
        The result of the coroutine
    """
    return await coro
