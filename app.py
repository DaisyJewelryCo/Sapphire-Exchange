"""
Sapphire Exchange - Main Application Entry Point

This module launches the PyQt5-based desktop application for Sapphire Exchange.
"""
import sys
import asyncio
from PyQt5.QtWidgets import QApplication

from main_window import MainWindow

# Enable asyncio event loop for PyQt5
from qasync import QEventLoop


def main():
    try:
        # Create the Qt Application
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(True)
        
        # Set up asyncio event loop
        loop = QEventLoop(app)
        asyncio.set_event_loop(loop)
        
        # Create and show the main window
        window = MainWindow()
        window.show()
        
        # Connect the aboutToQuit signal to clean up resources
        def handle_quit():
            print("Shutting down...")
            # Cancel all running tasks
            for task in asyncio.all_tasks(loop):
                task.cancel()
            # Stop the event loop
            loop.stop()
        
        app.aboutToQuit.connect(handle_quit)
        
        # Run the application
        with loop:
            loop.run_forever()
            
    except Exception as e:
        print(f"Fatal error: {e}")
        return 1
    finally:
        # Ensure the event loop is closed
        if 'loop' in locals():
            loop.close()
        
    return 0


if __name__ == "__main__":
    main()
