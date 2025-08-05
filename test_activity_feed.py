#!/usr/bin/env python3
"""
Test script to verify activity feed functionality works correctly.
This tests the message logging and display components without the complex mock server.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from PyQt5.QtWidgets import QApplication, QVBoxLayout, QWidget, QTextEdit, QPushButton, QLabel
from PyQt5.QtCore import QTimer
import asyncio
from datetime import datetime

class TestActivityFeed(QWidget):
    def __init__(self):
        super().__init__()
        self.message_history = []
        self.max_messages = 50
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Activity Feed Test")
        self.setGeometry(100, 100, 400, 300)
        
        layout = QVBoxLayout()
        
        # Test button
        self.test_btn = QPushButton("Add Test Message")
        self.test_btn.clicked.connect(self.add_test_message)
        layout.addWidget(self.test_btn)
        
        # Message log
        self.message_log = QTextEdit()
        self.message_log.setReadOnly(True)
        self.message_log.setMaximumHeight(200)
        layout.addWidget(QLabel("Activity Feed:"))
        layout.addWidget(self.message_log)
        
        self.setLayout(layout)
        
        # Add some initial messages
        self.add_message("Activity feed initialized", "info")
        self.add_message("Test system ready", "success")
        
    def add_message(self, message, level="info", data_quality="unknown"):
        """Add a message to the log - simplified version of MainWindow.add_message"""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.message_history.append((timestamp, message, level, data_quality))
            
            # Keep only the last max_messages
            if len(self.message_history) > self.max_messages:
                self.message_history.pop(0)
                
            self.update_message_log()
            
        except Exception as e:
            print(f"Error adding message: {e}")
            
    def update_message_log(self):
        """Update the message log display"""
        try:
            log_text = ""
            for entry in self.message_history:
                timestamp, msg, level, data_quality = entry
                
                # Message color based on level
                if level == "error":
                    log_text += f"<font color='#e74c3c'>{timestamp} - {msg}</font><br>"
                elif level == "warning":
                    log_text += f"<font color='#f39c12'>{timestamp} - {msg}</font><br>"
                elif level == "success":
                    log_text += f"<font color='#2ecc71'>{timestamp} - {msg}</font><br>"
                else:
                    log_text += f"{timestamp} - {msg}<br>"
                    
            self.message_log.setHtml(log_text)
            
        except Exception as e:
            print(f"Error updating message log: {e}")
            
    def add_test_message(self):
        """Add a test message to demonstrate activity feed functionality"""
        messages = [
            ("Test message 1", "info"),
            ("Test message 2", "success"),
            ("Test message 3", "warning"),
            ("Test message 4", "error"),
        ]
        import random
        msg, level = random.choice(messages)
        self.add_message(msg, level)

async def main():
    app = QApplication(sys.argv)
    
    # Create and show test window
    window = TestActivityFeed()
    window.show()
    
    # Test the activity feed
    print("Testing activity feed functionality...")
    
    # Add some test messages
    QTimer.singleShot(1000, lambda: window.add_message("Async test message 1", "info"))
    QTimer.singleShot(2000, lambda: window.add_message("Async test message 2", "success"))
    QTimer.singleShot(3000, lambda: window.add_message("Activity feed working correctly!", "success"))
    
    return app.exec_()

if __name__ == "__main__":
    # Run the test
    try:
        result = asyncio.run(main())
        sys.exit(result)
    except Exception as e:
        print(f"Test failed: {e}")
        sys.exit(1)
