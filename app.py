"""
Sapphire Exchange - Main Application Entry Point

This module launches the PyQt5-based desktop application for Sapphire Exchange.
"""
import sys
import asyncio
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt

# Enable asyncio event loop for PyQt5
from qasync import QEventLoop

from ui.simplified_main_window import SimplifiedMainWindow

did_shutdown = False

def handle_exception(exc_type, exc_value, exc_traceback):
    """Handle uncaught exceptions."""
    sys.__excepthook__(exc_type, exc_value, exc_traceback)
    QMessageBox.critical(
        None,
        "Unhandled Exception",
        f"An unhandled exception occurred:\n\n{exc_value}",
        QMessageBox.Ok
    )

def main():
    """Main entry point for the application."""
    # Create the Qt Application
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    app.setStyle('Fusion')  # Use Fusion style for a modern look
    
    # Set up exception handling
    sys.excepthook = handle_exception
    
    # Set up asyncio event loop
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    # Create and show the main window
    try:
        window = SimplifiedMainWindow()
        window.show()
    except Exception as e:
        QMessageBox.critical(
            None,
            "Fatal Error",
            f"Failed to create main window: {str(e)}"
        )
        return 1
    
    # Connect the aboutToQuit signal to clean up resources
    def handle_quit():
        global did_shutdown
        if did_shutdown:
            return
        did_shutdown = True
        import threading
        print("[Shutdown] Active threads:", threading.enumerate())
        try:
            # Cancel all running tasks
            for task in asyncio.all_tasks(loop):
                if not task.done() and task != asyncio.current_task():
                    task.cancel()
            # Give tasks a chance to cancel gracefully, but don't hang forever
            try:
                loop.run_until_complete(asyncio.wait_for(asyncio.sleep(0.1), timeout=2.0))
            except Exception as e:
                print(f"Shutdown wait timeout or error: {e}")
            # Stop the event loop
            if loop.is_running():
                loop.stop()
            # Force Qt event loop to quit
            from PyQt5.QtWidgets import QApplication
            QApplication.quit()
        except Exception as e:
            print(f"Error during shutdown: {e}")
        
    app.aboutToQuit.connect(handle_quit)
    
    # Run the application
    try:
        return_code = app.exec_()
        return return_code
    except KeyboardInterrupt:
        print("Application interrupted by user")
        return 0
    except Exception as e:
        print(f"Application error: {e}")
        return 1
    finally:
        # Ensure the loop is properly closed
        try:
            loop.close()
        except:
            pass
    
if __name__ == "__main__":
    # Don't use asyncio.run() with qasync
    sys.exit(main())
