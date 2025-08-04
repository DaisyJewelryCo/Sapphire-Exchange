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

from main_window import MainWindow

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
        window = MainWindow()
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
        print("Shutting down...")
        # Cancel all running tasks
        for task in asyncio.all_tasks(loop):
            if not task.done():
                task.cancel()
        # Stop the event loop
        if loop.is_running():
            loop.stop()
    
    app.aboutToQuit.connect(handle_quit)
    
    # Run the application
    with loop:
        try:
            loop.run_forever()
        except asyncio.CancelledError:
            pass  # Expected during shutdown
        except Exception as e:
            print(f"Unexpected error in event loop: {e}")
            return 1
    
    return 0

if __name__ == "__main__":
    # Don't use asyncio.run() with qasync
    sys.exit(main())
