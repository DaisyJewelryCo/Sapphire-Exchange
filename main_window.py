"""
Sapphire Exchange - Main Application Window

This module contains the main PyQt5-based UI for the Sapphire Exchange desktop application.
"""
import sys
import asyncio
import qrcode
import time
from datetime import datetime, timedelta, timezone
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QStackedWidget, QLineEdit, QTextEdit, 
                             QMessageBox, QScrollArea, QFrame, QFileDialog, QInputDialog, 
                             QDialog, QDialogButtonBox, QFormLayout, QGroupBox, QTextBrowser,
                             QListWidget, QListWidgetItem, QTabWidget, QButtonGroup)
from PyQt5 import QtGui
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer, pyqtSlot, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import (QFont, QPixmap, QIcon, QTextCursor, QTextCharFormat, QColor, 
                         QFontMetrics, QDoubleValidator)

from decentralized_client import DecentralizedClient
from models import Item, Auction, User

class AsyncWorker(QThread):
    """Worker thread for running async functions."""
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    
    def __init__(self, coro):
        super().__init__()
        self.coro = coro
        self._is_running = True
        self.loop = None
    
    def run(self):
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            if asyncio.iscoroutine(self.coro):
                result = self.loop.run_until_complete(self.coro)
            else:
                result = self.coro  # In case it's not a coroutine
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self._is_running = False
    
    def stop(self):
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        self._is_running = False
        self.quit()
        self.wait()
        if self.loop:
            self.loop.close()
    
    def __del__(self):
        self.stop()

class ItemWidget(QWidget):
    """Widget for displaying an item in the marketplace."""
    # Signal emitted when the bid button is clicked
    bid_clicked = pyqtSignal(dict)  # Signal to emit the item data
    
    def __init__(self, item_data, parent=None):
        super().__init__(parent)
        self.item_data = item_data
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Item image (placeholder for now)
        self.image_label = QLabel()
        self.image_label.setFixedSize(200, 200)
        self.image_label.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ddd;")
        
        # Item details
        self.name_label = QLabel(self.item_data.get('name', 'Unnamed Item'))
        self.name_label.setFont(QFont('Arial', 12, QFont.Bold))
        
        self.price_label = QLabel(f"Price: {self.item_data.get('starting_price', 0)} NANO")
        self.seller_label = QLabel(f"Seller: {self.item_data.get('owner', 'Unknown')}")
        
        # Bid button
        self.bid_button = QPushButton("Place Bid")
        self.bid_button.clicked.connect(self.on_bid_clicked)
        
        # Add widgets to layout
        layout.addWidget(self.image_label)
        layout.addWidget(self.name_label)
        layout.addWidget(self.price_label)
        layout.addWidget(self.seller_label)
        layout.addWidget(self.bid_button)
        
        self.setLayout(layout)
    
    def on_bid_clicked(self):
        # Emit the signal with the item data
        self.bid_clicked.emit(self.item_data)

class BidDialog(QDialog):
    """Custom dialog for placing bids with bid history."""
    def __init__(self, item_data, parent=None):
        super().__init__(parent)
        self.item_data = item_data
        self.bid_amount = 0
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle(f"Bid on {self.item_data.get('name', 'Item')}")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        # Current price and minimum bid
        current_bid = float(self.item_data.get('current_bid', self.item_data.get('starting_price', 0)))
        min_bid = max(current_bid * 1.1, current_bid + 0.1)  # 10% minimum increase or 0.1 NANO
        
        # Bid form
        form_layout = QFormLayout()
        
        # Current price
        self.current_price_label = QLabel(f"<b>Current Price:</b> {current_bid:.6f} NANO")
        form_layout.addRow(self.current_price_label)
        
        # Minimum bid
        self.min_bid_label = QLabel(f"<b>Minimum Bid:</b> {min_bid:.6f} NANO")
        form_layout.addRow(self.min_bid_label)
        
        # Bid amount input
        self.bid_input = QLineEdit()
        self.bid_input.setPlaceholderText(f"Minimum: {min_bid:.6f}")
        self.bid_input.setValidator(QDoubleValidator(min_bid, 1_000_000, 6))
        self.bid_input.textChanged.connect(self.validate_bid)
        form_layout.addRow("Your Bid (NANO):", self.bid_input)
        
        # Bid history group
        history_group = QGroupBox("Bid History")
        history_layout = QVBoxLayout()
        
        self.history_browser = QTextBrowser()
        self.history_browser.setOpenExternalLinks(False)
        self.history_browser.setReadOnly(True)
        self.history_browser.setStyleSheet("""
            QTextBrowser {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Courier New', monospace;
                font-size: 12px;
            }
        """)
        
        # Add sample bid history (replace with actual data)
        self.update_bid_history()
        
        # Toggle button for history
        self.toggle_history_btn = QPushButton("Show History")
        self.toggle_history_btn.setCheckable(True)
        self.toggle_history_btn.setChecked(False)
        self.toggle_history_btn.clicked.connect(self.toggle_history)
        
        # Initially hide the history
        self.history_browser.setVisible(False)
        
        history_layout.addWidget(self.toggle_history_btn)
        history_layout.addWidget(self.history_browser)
        history_group.setLayout(history_layout)
        
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        self.ok_button = button_box.button(QDialogButtonBox.Ok)
        self.ok_button.setEnabled(False)
        
        # Add widgets to main layout
        layout.addLayout(form_layout)
        layout.addWidget(history_group)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        
        # Store min bid for validation
        self.min_bid = min_bid
    
    def update_bid_history(self):
        """Update the bid history display."""
        # Get bids from item data (default to empty list if not present)
        bids = self.item_data.get('bids', [])
        
        if not bids:
            self.history_browser.setPlainText("No bids yet.")
            return
        
        # Format the history
        history_text = []
        for bid in sorted(bids, key=lambda x: x.get('timestamp', ''), reverse=True):
            amount = bid.get('amount', 0)
            bidder = bid.get('bidder', 'Unknown')
            timestamp = bid.get('timestamp', '')
            
            # Format timestamp if available
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    timestamp = dt.strftime('%Y-%m-%d %H:%M:%S')
                except (ValueError, AttributeError):
                    pass
            
            history_text.append(f"{timestamp} - {amount:.6f} NANO by {bidder}")
        
        self.history_browser.setPlainText("\n".join(history_text))
    
    def toggle_history(self):
        """Toggle the visibility of the bid history."""
        is_visible = not self.history_browser.isVisible()
        self.history_browser.setVisible(is_visible)
        self.toggle_history_btn.setText("Hide History" if is_visible else "Show History")
        
        # Resize dialog to fit content
        self.adjustSize()
    
    def validate_bid(self, text):
        """Validate the bid amount."""
        try:
            bid = float(text) if text else 0
            is_valid = bid >= self.min_bid
            self.ok_button.setEnabled(is_valid)
            
            # Update text color based on validation
            if text:
                if bid < self.min_bid:
                    self.bid_input.setStyleSheet("color: #dc3545;")
                else:
                    self.bid_input.setStyleSheet("color: #28a745;")
            else:
                self.bid_input.setStyleSheet("")
                
            if is_valid:
                self.bid_amount = bid
                
        except ValueError:
            self.ok_button.setEnabled(False)
            self.bid_input.setStyleSheet("color: #dc3545;")
    
    def accept(self):
        """Handle accept button click."""
        try:
            self.bid_amount = float(self.bid_input.text())
            if self.bid_amount >= self.min_bid:
                super().accept()
            else:
                QMessageBox.warning(self, "Invalid Bid", f"Bid must be at least {self.min_bid:.6f} NANO")
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid bid amount.")

class MainWindow(QMainWindow):
    """Main application window."""
    # Signal to show the seed message box on the main thread
    show_seed_message_box = pyqtSignal()
    
    def __init__(self):
        print("Initializing MainWindow...")
        super().__init__()
        print("  Setting up attributes...")
        self.client = None
        self.current_user = None
        self.items = []
        self._pending_seed = None
        self.mock_mode = True  # Ensure mock_mode is set
        self.message_history = []
        self.max_messages = 100  # Maximum number of messages to keep in history
        
        print("  Initializing UI...")
        self.init_ui_components()
        
        # Connect the signal to the slot
        print("  Connecting signals...")
        self.show_seed_message_box.connect(self._show_seed_message_box)
        print("  MainWindow initialization complete")
        
        # Initial connection check
        QTimer.singleShot(1000, self.check_connections)
    
    def _show_seed_message_box(self):
        """Show the seed message box on the main thread with copy functionality."""
        try:
            if not hasattr(self, '_pending_seed') or not self._pending_seed:
                return
                
            seed = self._pending_seed
            
            # Create a custom message box
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("New Wallet Generated")
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setText(
                "A new wallet has been generated for you.\n\n"
                "IMPORTANT: Please save this seed phrase in a secure location.\n"
                "You will need this seed phrase to recover your wallet."
            )
            
            # Add the seed phrase in a read-only text field
            seed_text = QTextEdit()
            seed_text.setPlainText(seed)
            seed_text.setReadOnly(True)
            seed_text.setMinimumWidth(400)
            seed_text.setMinimumHeight(100)
            
            # Add copy to clipboard button
            copy_btn = QPushButton("Copy to Clipboard")
            copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(seed))
            
            # Add widgets to layout
            layout = msg_box.layout()
            layout.addWidget(QLabel("\nYour seed phrase:"), 1, 0, 1, 2)
            layout.addWidget(seed_text, 2, 0, 1, 2)
            layout.addWidget(QLabel(" "), 3, 0)  # Spacer
            layout.addWidget(copy_btn, 4, 1)
            
            # Show the message box
            msg_box.exec_()
            
        except Exception as e:
            print(f"Error showing seed message box: {e}")
            # Fall back to simple message box if there's an error
            QMessageBox.information(
                self, 
                "New Wallet Generated", 
                f"A new wallet has been generated for you.\n\n"
                f"IMPORTANT: Please save this seed phrase in a secure location:\n\n{seed}\n\n"
                "You will need this seed phrase to recover your wallet."
            )
        finally:
            # Clear the pending seed after showing the message
            if hasattr(self, '_pending_seed'):
                self._pending_seed = None
    
    def init_ui_components(self):
        """Initialize all UI components."""
        self.setWindowTitle("Sapphire Exchange")
        self.setMinimumSize(1000, 700)
        
        # Main layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # Main layout with status bar at bottom
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Content area with sidebar and main content
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # Sidebar
        self.sidebar = self.create_sidebar()
        content_layout.addWidget(self.sidebar, stretch=1)
        
        # Stacked widget for pages
        self.stacked_widget = QStackedWidget()
        content_layout.addWidget(self.stacked_widget, stretch=4)
        
        main_layout.addWidget(content_widget, 1)  # Take all available space
        
        # Status bar at bottom
        self.status_bar = QFrame()
        self.status_bar.setFrameShape(QFrame.StyledPanel)
        self.status_bar.setStyleSheet("""
            QFrame {
                background-color: #f5f5f5;
                border-top: 1px solid #ddd;
                padding: 4px 8px;
            }
            QLabel {
                color: #555;
                font-size: 12px;
            }
        """)
        
        # Status bar layout
        status_layout = QHBoxLayout(self.status_bar)
        status_layout.setContentsMargins(8, 4, 8, 4)
        status_layout.setSpacing(10)
        
        # Status indicator (colored dot)
        self.status_indicator = QLabel("●")
        self.status_indicator.setStyleSheet("font-size: 16px; color: #999;")
        self.status_indicator.setCursor(Qt.PointingHandCursor)
        self.status_indicator.mousePressEvent = self.on_status_clicked
        status_layout.addWidget(self.status_indicator)
        
        # Status text
        self.status_text = QLabel("Initializing...")
        status_layout.addWidget(self.status_text, 1)  # Take remaining space
        
        # Message log button
        self.toggle_log_btn = QPushButton("▲")
        self.toggle_log_btn.setFixedSize(20, 20)
        self.toggle_log_btn.setFlat(True)
        self.toggle_log_btn.setStyleSheet("""
            QPushButton {
                border: none;
                font-size: 12px;
                color: #666;
            }
            QPushButton:hover {
                color: #000;
                background-color: #e0e0e0;
                border-radius: 2px;
            }
        """)
        self.toggle_log_btn.clicked.connect(self.toggle_message_log)
        status_layout.addWidget(self.toggle_log_btn)
        
        # Message log (initially hidden)
        self.message_log = QTextEdit()
        self.message_log.setReadOnly(True)
        self.message_log.setMaximumHeight(150)
        self.message_log.setStyleSheet("""
            QTextEdit {
                background-color: #f9f9f9;
                border: none;
                border-top: 1px solid #eee;
                padding: 8px;
                font-family: 'Monospace';
                font-size: 11px;
                color: #333;
            }
        """)
        self.message_log.hide()
        
        # Add to main layout
        main_layout.addWidget(self.status_bar)
        main_layout.addWidget(self.message_log)
        
        # Initialize pages
        self.create_login_page()
        self.create_marketplace_page()
        self.create_item_creation_page()
        self.create_my_items_page()
        
        # Show login page by default
        self.stacked_widget.setCurrentIndex(0)
        
        # Apply styles
        self.setStyleSheet("""
            QMainWindow {
                background-color: white;
            }
            QPushButton {
                background-color: #2b7bba;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #1f5f8b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        
        # Connect the toggle log button
        self.toggle_log_btn.clicked.connect(self.toggle_message_log)
        status_layout.addWidget(self.toggle_log_btn)
        
        # Message log (initially hidden)
        self.message_log = QTextEdit()
        self.message_log.setReadOnly(True)
        self.message_log.setMaximumHeight(150)
        self.message_log.setStyleSheet("""
            QTextEdit {
                background-color: #f9f9f9;
                border: none;
                border-top: 1px solid #eee;
                padding: 8px;
                font-family: 'Monospace';
                font-size: 11px;
                color: #333;
            }
        """)
        self.message_log.hide()
        
        # Add to main layout
        main_layout.addWidget(self.status_bar)
        main_layout.addWidget(self.message_log)
        
        # Initialize pages
        self.create_login_page()
        self.create_marketplace_page()
        self.create_item_creation_page()
        self.create_my_items_page()
        
        # Show login page by default
        self.stacked_widget.setCurrentIndex(0)
        
        # Apply styles
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f7fa;
            }
            QPushButton {
                background-color: #4a6ee0;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #3a5ed0;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
            QLineEdit, QTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 6px;
                font-size: 14px;
            }
            QLineEdit:focus, QTextEdit:focus {
                border: 1px solid #4a6ee0;
            }
            QLabel {
                color: #333;
            }
            QScrollArea {
                border: none;
            }
        """)
            
        # Connect the toggle log button
        self.toggle_log_btn.clicked.connect(self.toggle_message_log)
        status_layout.addWidget(self.toggle_log_btn)
            
        # Message log (initially hidden)
        self.message_log = QTextEdit()
        self.message_log.setReadOnly(True)
        self.message_log.setMaximumHeight(150)
        self.message_log.setStyleSheet("""
            QTextEdit {
                background-color: #f9f9f9;
                border: none;
                border-top: 1px solid #eee;
                padding: 8px;
                font-family: 'Monospace';
                font-size: 11px;
                color: #333;
            }
        """)
        self.message_log.hide()
            
        # Add to main layout
        main_layout.addWidget(self.status_bar)
        main_layout.addWidget(self.message_log)
            
        # Initialize pages
        self.create_login_page()
        self.create_marketplace_page()
        self.create_item_creation_page()
        self.create_my_items_page()
            
        # Show login page by default
        self.stacked_widget.setCurrentIndex(0)
        
    def closeEvent(self, event):
        """Clean up resources when the window is closed."""
        if hasattr(self, 'worker') and self.worker and self.worker.isRunning():
            self.worker.stop()
        event.accept()
    
    def check_connections(self):
        """Check the current connection status."""
        try:
            # Update connection status
            if hasattr(self, 'client') and self.client is not None:
                # Ensure we have a valid connection status
                if not hasattr(self, 'connection_status'):
                    self.connection_status = False
                
                # Update status based on client state
                if hasattr(self.client, 'is_connected') and callable(self.client.is_connected):
                    self.connection_status = self.client.is_connected()
                elif hasattr(self.client, '_is_connected'):
                    self.connection_status = self.client._is_connected
                
                # Update the status dot
                if hasattr(self, 'status_dot') and self.status_dot is not None:
                    self.status_dot.setStyleSheet(
                        f"background-color: {'#2ecc71' if self.connection_status else '#e74c3c'};"
                        "border-radius: 8px; width: 16px; height: 16px;"
                    )
            else:
                # Default to disconnected if no client
                self.connection_status = False
                if hasattr(self, 'status_dot') and self.status_dot is not None:
                    self.status_dot.setStyleSheet(
                        "background-color: #e74c3c;"
                        "border-radius: 8px; width: 16px; height: 16px;"
                    )
        except Exception as e:
            print(f"Error in check_connections: {e}")
            self.connection_status = False
        
        # Schedule next check
        QTimer.singleShot(1000, self.check_connections)
        
    def on_status_clicked(self, event):
        """Handle status indicator click."""
        # Toggle connection status
        if self.client and self.client.is_connected:
            self.client.disconnect()
        else:
            self.client.connect()
            
    def add_message(self, message, level="info"):
        """Add a message to the log."""
        # Add timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.message_history.append((timestamp, message, level))
        
        # Keep only the last max_messages
        if len(self.message_history) > self.max_messages:
            self.message_history.pop(0)
            
        # Update the log display
        self.update_message_log()
        
        # Auto-scroll to bottom
        self.message_log.verticalScrollBar().setValue(
            self.message_log.verticalScrollBar().maximum()
        )
        
        # If error level, also show in status bar for a few seconds
        if level == "error":
            self.status_text.setText(f"Error: {message}")
            QTimer.singleShot(5000, lambda: self.status_text.setText(""))
    
    def update_message_log(self):
        """Update the message log with all messages."""
        log_text = ""
        for timestamp, msg, level in self.message_history:
            if level == "error":
                log_text += f"<font color='#e74c3c'>{timestamp} - {msg}</font><br>"
            elif level == "warning":
                log_text += f"<font color='#f39c12'>{timestamp} - {msg}</font><br>"
            elif level == "success":
                log_text += f"<font color='#2ecc71'>{timestamp} - {msg}</font><br>"
            else:
                log_text += f"{timestamp} - {msg}<br>"
        
        self.message_log.setHtml(log_text)
        
    def toggle_message_log(self):
        """Toggle the visibility of the message log."""
        is_visible = not self.message_log.isVisible()
        self.message_log.setVisible(is_visible)
        self.toggle_log_btn.setText("▼" if is_visible else "▲")
        
        # Resize window to fit content
        self.adjustSize()
        
    def create_sidebar(self):
        """Create the sidebar with navigation buttons."""
        sidebar = QWidget()
        sidebar.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
                border-right: 1px solid #e0e0e0;
            }
            QPushButton {
                text-align: left;
                padding: 12px 20px;
                border: none;
                border-radius: 0;
                font-size: 14px;
                color: #333;
                background: transparent;
            }
            QPushButton:hover {
                background-color: #e8e8e8;
            }
            QPushButton:checked {
                background-color: #e0e0e0;
                font-weight: bold;
            }
        """)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 20, 0, 20)
        layout.setSpacing(0)
        
        # App title/logo
        title = QLabel("Sapphire Exchange")
        title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                padding: 20px;
                color: #333;
                border-bottom: 1px solid #e0e0e0;
            }
        """)
        layout.addWidget(title)
        
        # Navigation buttons - initially only show Marketplace
        self.nav_buttons = {
            "marketplace_btn": ("🏠 Marketplace", 1, True),  # Always visible
            "sell_item_btn": ("🛍️ Sell Item", 2, False),    # Hidden until login
            "my_items_btn": ("📦 My Items", 3, False),     # Hidden until login
            "settings_btn": ("⚙️ Settings", 4, False)      # Hidden until login
        }
        
        self.nav_button_group = QButtonGroup()
        for btn_name, (text, page_id, visible) in self.nav_buttons.items():
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setVisible(visible)  # Only Marketplace is visible by default
            btn.clicked.connect(lambda checked, p=page_id: self.show_page(p))
            self.nav_button_group.addButton(btn, page_id)
            setattr(self, btn_name, btn)  # Store reference to button
            layout.addWidget(btn)
        
        # Add stretch to push buttons to top
        layout.addStretch()
        
        # Logout button
        self.logout_btn = QPushButton("🚪 Logout")
        self.logout_btn.clicked.connect(self.logout)
        self.logout_btn.setVisible(False)  # Initially hidden until login
        layout.addWidget(self.logout_btn)
        
        return sidebar
        
    def create_login_page(self):
        """Create a simplified login/signup page."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)
        
        # Add to stacked widget
        self.stacked_widget.addWidget(page)
        
        # Logo/Title
        title = QLabel("Sapphire Exchange")
        title.setFont(QFont('Arial', 24, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        layout.addSpacing(30) 
        card = QWidget()
        card.setFixedWidth(350)  # Reduced from 400px
        card.setStyleSheet("""
            QWidget {
                background: white;
                border-radius: 12px;
                padding: 25px;
                border: 1px solid #e0e0e0;
                /* Removed unsupported box-shadow */
            }
        """)
        
        form_layout = QVBoxLayout(card)
        form_layout.setSpacing(20)
        
        # Form title
        form_title = QLabel("Welcome Back")
        form_title.setFont(QFont('Arial', 16, QFont.Bold))
        form_title.setAlignment(Qt.AlignCenter)
        
        # Seed phrase input
        seed_label = QLabel("Your Seed Phrase:")
        self.seed_input = QTextEdit()
        self.seed_input.setPlaceholderText("Enter your 12 or 24 word seed phrase")
        self.seed_input.setMaximumHeight(80)  # Increased from 60 to 80
        self.seed_input.setStyleSheet("""
            QTextEdit {
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 8px;
                font-size: 14px;
                min-height: 60px;
                max-height: 80px;
            }
            QTextEdit:focus {
                border: 1px solid #2b7bba;
            }
        """)
        
        # New account link
        new_account_link = QLabel(
            "<a href='#' style='color: #2b7bba; text-decoration: none;'>Create a new account</a>"
        )
        new_account_link.setAlignment(Qt.AlignCenter)
        new_account_link.linkActivated.connect(self.handle_new_account)
        
        # Login button
        self.login_btn = QPushButton("Continue")
        self.login_btn.setStyleSheet("""
            QPushButton {
                background: #2b7bba;
                color: white;
                border: none;
                padding: 12px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 15px;
            }
            QPushButton:hover {
                background: #1a5a8f;
            }
            QPushButton:disabled {
                background: #cccccc;
            }
        """)
        self.login_btn.clicked.connect(self.handle_login)
        
        # Add widgets to form
        form_layout.addWidget(form_title)
        form_layout.addWidget(seed_label)
        form_layout.addWidget(self.seed_input)
        form_layout.addWidget(new_account_link)
        form_layout.addWidget(self.login_btn)
        
        # Add card to main layout
        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(card, 0, Qt.AlignCenter)
        layout.addStretch()
        
        # Initialize state
        self.is_new_user = False
        
        return page
        
    def _set_seed_phrase(self, seed_phrase):
        """Helper method to set the seed phrase in the input field."""
        try:
            print(f"DEBUG: Setting seed phrase: {seed_phrase}")
            
            # Clear the input field completely
            self.seed_input.clear()
            
            # Set the text directly using setPlainText
            self.seed_input.setPlainText(seed_phrase)
            
            # Force focus and update the display
            self.seed_input.setFocus()
            self.seed_input.update()
            self.seed_input.repaint()
            
            # Debug information
            current_text = self.seed_input.toPlainText()
            print(f"DEBUG: Current input content: '{current_text}'")
            print(f"DEBUG: Text length: {len(current_text)}")
            print(f"DEBUG: Document has content: {not self.seed_input.document().isEmpty()}")
            
            # If text is still not set, try an alternative approach
            if not current_text.strip():
                print("WARNING: Text not set, trying alternative method...")
                self.seed_input.setText(seed_phrase)
                self.seed_input.update()
                print(f"DEBUG: After setText, content: '{self.seed_input.toPlainText()}'")
            
            return True
            
        except Exception as e:
            print(f"ERROR in _set_seed_phrase: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
            
    def handle_new_account(self):
        """Handle new account creation."""
        try:
            # Generate a simple seed phrase
            import secrets
            wordlist = [
                'abandon', 'ability', 'able', 'about', 'above', 'absent', 'absorb', 'abstract', 'absurd', 'abuse',
                'access', 'accident', 'account', 'accuse', 'achieve', 'acid', 'acoustic', 'across', 'act', 'action',
                'actor', 'actress', 'actual', 'adapt', 'add', 'addict', 'address', 'adjust', 'admit', 'adult',
                'advance', 'advice', 'aerobic', 'affair', 'afford', 'afraid', 'again', 'age', 'agent', 'agree',
                'ahead', 'aim', 'air', 'airport', 'aisle', 'alarm', 'album', 'alcohol', 'alert', 'alien'
            ]
            seed_phrase = ' '.join(secrets.choice(wordlist) for _ in range(12))
            
            # Create a custom dialog for the seed phrase
            dialog = QDialog(self)
            dialog.setWindowTitle("Your Recovery Phrase")
            dialog.setMinimumWidth(500)
            dialog.setStyleSheet("""
                QDialog {
                    background-color: #f5f5f5;
                    font-family: Arial, sans-serif;
                }
                QLabel {
                    color: #333333;
                    font-size: 14px;
                    margin: 5px 0;
                }
                QPushButton {
                    background: #2b7bba;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 4px;
                    font-weight: bold;
                    min-width: 120px;
                }
                QPushButton:hover {
                    background: #1a5a8f;
                }
                QTextEdit {
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                    padding: 10px;
                    background: white;
                    font-family: monospace;
                    font-size: 16px;
                    margin: 10px 0;
                }
            """)
            
            layout = QVBoxLayout(dialog)
            
            # Title
            title = QLabel("Your Wallet Recovery Phrase")
            title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2b7bba; margin-bottom: 15px;")
            
            # Warning text
            warning = QLabel(
                "Write down these words in the correct order and keep them in a safe place. "
                "You will need this phrase to recover your wallet if you lose access to this device. "
                "Never share this phrase with anyone!"
            )
            warning.setWordWrap(True)
            warning.setStyleSheet("color: #d35400; background: #fdebd0; padding: 10px; border-radius: 4px;")
            
            # Seed phrase display
            seed_display = QTextEdit()
            seed_display.setPlainText(seed_phrase)
            seed_display.setReadOnly(True)
            seed_display.setAlignment(Qt.AlignCenter)
            seed_display.setStyleSheet("""
                QTextEdit {
                    background: #f8f9fa;
                    border: 2px dashed #2b7bba;
                    font-size: 16px;
                    font-weight: bold;
                    padding: 15px;
                    border-radius: 6px;
                    text-align: center;
                }
            """)
            
            # Copy button
            copy_btn = QPushButton("Copy to Clipboard")
            copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(seed_phrase))
            
            # Confirm button
            confirm_btn = QPushButton("I've Saved My Phrase")
            confirm_btn.clicked.connect(dialog.accept)
            confirm_btn.setStyleSheet("background: #27ae60;")
            
            # Add widgets to layout
            layout.addWidget(title)
            layout.addWidget(warning)
            layout.addWidget(QLabel("Your recovery phrase:"))
            layout.addWidget(seed_display)
            
            # Button layout
            btn_layout = QHBoxLayout()
            btn_layout.addWidget(copy_btn)
            btn_layout.addWidget(confirm_btn)
            
            layout.addLayout(btn_layout)
            
            # Show the dialog
            dialog.exec_()
            
            # Store the seed phrase in a class variable for later use
            self._pending_seed = seed_phrase
            
            # Set the seed phrase directly in the input field
            success = self._set_seed_phrase(seed_phrase)
            
            # If direct setting failed, try again with a small delay
            if not success:
                QTimer.singleShot(100, lambda: self._set_seed_phrase(seed_phrase))
            
            # Force the input field to update and repaint
            self.seed_input.update()
            self.seed_input.repaint()
            
            # Enable login and set flags
            self.login_btn.setEnabled(True)
            self.is_new_user = True
            
            # Set focus to the login button for better UX
            self.login_btn.setFocus()
            
            # Debug output
            print(f"DEBUG: Seed phrase generated: {seed_phrase}")
            print(f"DEBUG: Input field content after setting: '{self.seed_input.toPlainText()}'")
            print(f"DEBUG: Input field has focus: {self.seed_input.hasFocus()}")
            
            # Force a complete UI update
            QApplication.processEvents()
            
            return True
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create account: {str(e)}")
            return False
    
    def handle_login(self):
        """Handle the login process with the provided seed phrase."""
        try:
            # Get and validate seed phrase
            seed_phrase = self.seed_input.toPlainText().strip()
            
            if not seed_phrase:
                QMessageBox.warning(self, "Input Required", "Please enter your seed phrase or create a new account.")
                return
                
            # Validate seed phrase format (basic check)
            words = seed_phrase.split()
            if len(words) not in [12, 15, 18, 21, 24]:
                QMessageBox.warning(
                    self, 
                    "Invalid Seed Phrase",
                    "Seed phrase must be 12, 15, 18, 21, or 24 words long.\n\n"
                    f"Current length: {len(words)} words"
                )
                return
                
            # Disable UI during login attempt
            self.login_btn.setEnabled(False)
            self.login_btn.setText("Logging in...")
            QApplication.processEvents()  # Force UI update
                
            # Update UI
            self.login_btn.setEnabled(False)
            self.login_btn.setText("Please wait...")
            QApplication.processEvents()
            
            # Initialize client if needed
            if not self.client:
                self.client = DecentralizedClient()
            
            # Try to login
            worker = AsyncWorker(self.login_async(seed_phrase))
            worker.finished.connect(self.on_login_complete)
            worker.error.connect(self.on_error)
            worker.start()
            
        except Exception as e:
            self.login_btn.setEnabled(True)
            self.login_btn.setText("Continue")
            QMessageBox.critical(self, "Login Error", f"Failed to login: {str(e)}")
            print(f"Login error: {e}")
    
    def validate_new_user_inputs(self):
        """Validate new user inputs."""
        if not self.is_new_user:
            return True
            
        username = self.username_input.text().strip()
        first_name = self.first_name_input.text().strip()
        last_name = self.last_name_input.text().strip()
        
        if not username:
            QMessageBox.warning(self, "Validation Error", "Username is required.")
            return False
            
        # Add more validation as needed
        return True
    
    def handle_login(self):
        """Handle the login process with the provided seed phrase."""
        # Get and validate seed phrase
        seed_phrase = self.seed_input.toPlainText().strip()
        
        # If no seed phrase in input but we have a pending seed, use that
        if not seed_phrase and hasattr(self, '_pending_seed') and self._pending_seed:
            seed_phrase = self._pending_seed
            self.seed_input.setPlainText(seed_phrase)
            
        if not seed_phrase:
            QMessageBox.warning(self, "Input Required", "Please enter your seed phrase or create a new account.")
            return
            
        # Validate seed phrase format (basic check)
        if len(seed_phrase.split()) not in [12, 15, 18, 21, 24]:
            QMessageBox.warning(
                self, 
                "Invalid Seed Phrase",
                "Seed phrase must be 12, 15, 18, 21, or 24 words long.\n\n"
                "If you just created a new account, please use the seed phrase that was shown to you."
            )
            return
            
        # Disable login button to prevent multiple clicks
        self.login_btn.setEnabled(False)
        self.login_btn.setText("Please wait...")
        
        # Clear any previous error messages
        self.statusBar().clearMessage()
        
        # Show status message
        status_msg = "Creating your account..." if self.is_new_user else "Logging in..."
        self.statusBar().showMessage(status_msg)
        
        # Force UI update before starting the login process
        QApplication.processEvents()
        
        def on_login_complete(user_data):
            """Handle successful login."""
            try:
                self.statusBar().clearMessage()
                self.login_btn.setEnabled(True)
                self.login_btn.setText("Continue")
                
                if user_data and hasattr(user_data, 'username'):
                    self.current_user = user_data
                    username = getattr(user_data, 'username', 'User')
                    
                    # Update UI for logged-in state
                    if hasattr(self, 'user_info'):
                        self.user_info.setText(f"Logged in as: {username}")
                        self.user_info.setVisible(True)
                    
                    # Show all navigation buttons after successful login
                    for btn_name in self.nav_buttons.keys():
                        if hasattr(self, btn_name):
                            getattr(self, btn_name).setVisible(True)
                            
                    # Also show other UI elements that should be visible after login
                    for btn_name in ['create_item_btn', 'my_items_btn', 'logout_btn']:
                        if hasattr(self, btn_name):
                            getattr(self, btn_name).setVisible(True)
                    
                    # Update connection status
                    if hasattr(self, 'client') and self.client:
                        self.client._is_connected = True
                    
                    # Navigate to marketplace
                    self.show_page(1)
                    
                    # Show success message
                    self.add_message(f"Successfully logged in as {username}", "success")
                    
                else:
                    QMessageBox.warning(self, "Login Failed", "Invalid user data received.")
                    self.add_message("Login failed: Invalid user data", "error")
                    
            except Exception as e:
                error_msg = f"Error during login: {str(e)}"
                print(error_msg)
                QMessageBox.critical(self, "Login Error", error_msg)
                self.add_message(error_msg, "error")
        
        def on_error(error_msg):
            """Handle login errors."""
            try:
                self.statusBar().clearMessage()
                self.login_btn.setEnabled(True)
                self.login_btn.setText("Continue")
                
                # Show user-friendly error message
                error_str = str(error_msg).lower()
                if "invalid seed" in error_str or "invalid mnemonic" in error_str:
                    error_msg = "The seed phrase you entered is invalid. Please check and try again."
                elif "timeout" in error_str or "connection" in error_str:
                    error_msg = "Connection to the network failed. Please check your internet connection and try again."
                
                QMessageBox.critical(
                    self, 
                    "Login Error",
                    f"We couldn't log you in.\n\n{error_msg}"
                )
                
                # Log the error
                self.add_message(f"Login error: {error_msg}", "error")
                
            except Exception as e:
                print(f"Error in on_error handler: {e}")
        
        # Start login process in a worker thread
        try:
            async def login_wrapper():
                try:
                    # Ensure we have a clean client instance
                    self.client = DecentralizedClient(mock_mode=True)
                    return await self.login_async(seed_phrase, None)
                except Exception as e:
                    print(f"Error in login_wrapper: {e}")
                    raise
            
            self.worker = AsyncWorker(login_wrapper())
            self.worker.finished.connect(on_login_complete)
            self.worker.error.connect(on_error)
            self.worker.start()
            
        except Exception as e:
            error_msg = f"Failed to start login process: {str(e)}"
            print(error_msg)
            on_error(error_msg)
    
    def create_marketplace_page(self):
        """Create the marketplace page."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Add to stacked widget
        self.stacked_widget.addWidget(page)
        
        # Search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search items...")
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self.search_items)
        
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(search_btn)
        
        # Items grid
        self.items_grid = QListWidget()
        self.items_grid.setViewMode(QListWidget.IconMode)
        self.items_grid.setIconSize(QSize(200, 200))
        self.items_grid.setResizeMode(QListWidget.Adjust)
        self.items_grid.setSpacing(20)
        
        # Add widgets to layout
        layout.addLayout(search_layout)
        layout.addWidget(self.items_grid)
        
        # Don't load items here - they'll be loaded when the page is shown
        # via the show_page method
        print("  Marketplace page created")
        return page
    
    def create_item_creation_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        title = QLabel("Create New Item")
        title.setFont(QFont('Arial', 16, QFont.Bold))
        
        # Form layout
        form_layout = QVBoxLayout()
        
        # Item name
        self.item_name = QLineEdit()
        self.item_name.setPlaceholderText("Item Name")
        
        # Item description
        self.item_description = QTextEdit()
        self.item_description.setPlaceholderText("Item Description")
        self.item_description.setMaximumHeight(100)
        
        # Starting price
        self.starting_price = QLineEdit()
        self.starting_price.setPlaceholderText("Starting Price (NANO)")
        
        # Duration (in hours)
        self.duration = QLineEdit("24")
        self.duration.setPlaceholderText("Auction Duration (hours)")
        
        # Image upload
        self.image_path = QLineEdit()
        self.image_path.setPlaceholderText("Image Path")
        self.image_path.setReadOnly(True)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_image)
        
        image_layout = QHBoxLayout()
        image_layout.addWidget(self.image_path)
        image_layout.addWidget(browse_btn)
        
        # Create button
        create_btn = QPushButton("Create Item")
        create_btn.clicked.connect(self.create_item)
        
        # Add widgets to form
        form_layout.addWidget(QLabel("Item Name:"))
        form_layout.addWidget(self.item_name)
        form_layout.addWidget(QLabel("Description:"))
        form_layout.addWidget(self.item_description)
        form_layout.addWidget(QLabel("Starting Price (NANO):"))
        form_layout.addWidget(self.starting_price)
        form_layout.addWidget(QLabel("Auction Duration (hours):"))
        form_layout.addWidget(self.duration)
        form_layout.addWidget(QLabel("Item Image:"))
        form_layout.addLayout(image_layout)
        form_layout.addWidget(create_btn)
        
        # Add title and form to main layout
        layout.addWidget(title)
        layout.addLayout(form_layout)
        layout.addStretch()
        
        return page
    
    def create_my_items_page(self):
        """Create the 'My Items' page."""
        print("Creating My Items page...")
        page = QWidget()
        layout = QVBoxLayout(page)
        
        # Add to stacked widget
        self.stacked_widget.addWidget(page)
        
        title = QLabel("My Items")
        title.setFont(QFont('Arial', 16, QFont.Bold))
        
        # Items list
        print("  Creating my_items_list...")
        self.my_items_list = QListWidget()
        self.my_items_list.setViewMode(QListWidget.IconMode)
        self.my_items_list.setIconSize(QSize(150, 150))
        self.my_items_list.setResizeMode(QListWidget.Adjust)
        
        # Add widgets to layout
        layout.addWidget(title)
        layout.addWidget(self.my_items_list)
        
        print("  My Items page created")
        return page
    
    def browse_image(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp)")
        if file_name:
            self.image_path.setText(file_name)
    
    def load_my_items(self):
        """Load the current user's items."""
        if not hasattr(self, 'my_items_list'):
            return
            
        self.my_items_list.clear()
        
        if not self.current_user:
            self.my_items_list.addItem("Please log in to view your items")
            return
            
        # Show loading indicator
        self.my_items_list.addItem("Loading your items...")
        
        # Load items in background
        def on_items_loaded(items):
            self.my_items_list.clear()
            
            if not items:
                self.my_items_list.addItem("You don't have any items yet")
                return
                
            for item_data in items:
                item = QListWidgetItem(item_data.get('name', 'Unnamed Item'))
                self.my_items_list.addItem(item)
        
        def on_error(error_msg):
            self.my_items_list.clear()
            self.my_items_list.addItem(f"Error loading items: {error_msg}")
        
        # Start loading items in a worker thread
        self.worker = AsyncWorker(self.load_user_items_async())
        self.worker.finished.connect(on_items_loaded)
        self.worker.error.connect(on_error)
        self.worker.start()
    
    def show_page(self, index):
        print(f"\n=== show_page({index}) called ===")
        print(f"  content_stack has {self.stacked_widget.count()} pages")
        print(f"  Current attributes: {[attr for attr in dir(self) if not attr.startswith('__')]}")
        
        # Make sure the page exists in the stack
        if index >= 0 and index < self.stacked_widget.count():
            print(f"  Setting current index to {index}")
            self.stacked_widget.setCurrentIndex(index)
            
            # Load content for the specific page
            if index == 1:  # Marketplace
                print("  Loading marketplace items...")
                self.load_marketplace_items()
            elif index == 3:  # My Items
                print("  Attempting to load My Items page...")
                if hasattr(self, 'my_items_list'):
                    print("  my_items_list found, calling load_my_items()")
                    self.load_my_items()
                else:
                    print("  WARNING: my_items_list attribute not found!")
                    print("  Current attributes:", [attr for attr in dir(self) if not attr.startswith('__')])
        else:
            print(f"  WARNING: Page index {index} out of range (0-{self.stacked_widget.count()-1})")
    
    async def login_async(self, seed_phrase, user_data=None):
        """
        Handle the login or account creation process asynchronously.
        
        Args:
            seed_phrase: The seed phrase for login
            user_data: Not used in simplified flow (kept for compatibility)
            
        Returns:
            User: The authenticated user object
            
        Raises:
            ValueError: If login or account creation fails
        """
        try:
            import random
            import asyncio
            from datetime import datetime
            from models import User
            
            # Simulate network delay (0.5-1.5 seconds)
            await asyncio.sleep(0.5 + random.random())
            
            # Validate seed phrase format
            if not seed_phrase or not seed_phrase.strip():
                raise ValueError("Seed phrase cannot be empty")
                
            words = seed_phrase.strip().split()
            if len(words) not in [12, 15, 18, 21, 24]:
                raise ValueError(f"Invalid seed phrase length: {len(words)} words. Must be 12, 15, 18, 21, or 24 words.")
            
            # Initialize client
            self.client = DecentralizedClient(mock_mode=True)
            
            # Connect the client
            if not self.client.connect():
                raise ValueError("Failed to connect to the network")
            
            # For new users (coming from handle_new_account)
            if self.is_new_user:
                print("Creating new account with provided seed phrase...")
                try:
                    # Generate a default username
                    username = f"user_{int(time.time()) % 10000}"
                    
                    # Initialize user with the provided seed phrase
                    user = await self.client.initialize_user(
                        seed_phrase=seed_phrase,
                        username=username
                    )
                    
                    if not user or not hasattr(self.client, 'user_wallet') or not self.client.user_wallet:
                        raise ValueError("Failed to initialize user wallet")
                        
                    print(f"Created new wallet with address: {self.client.user_wallet.address}")
                    return user
                    
                except Exception as e:
                    error_msg = f"Error creating account: {str(e)}"
                    print(error_msg)
                    raise ValueError(error_msg) from e
                    
            # For existing users
            else:
                print("Logging in with existing seed phrase...")
                try:
                    # First, try to create a wallet from the seed phrase
                    self.client.user_wallet = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: NanoWallet.from_seed(seed_phrase, mock_mode=True)
                    )
                    
                    if not self.client.user_wallet or not hasattr(self.client.user_wallet, 'public_key'):
                        raise ValueError("Invalid seed phrase: Could not derive wallet")
                    
                    # Convert public key to hex for lookup
                    public_key_hex = self.client.user_wallet.public_key.to_ascii(encoding='hex').decode('utf-8')
                    
                    # Try to load user data
                    user = await self.client._load_user_data()
                    
                    if not user:
                        # If no user data found, check if this is a valid Nano wallet
                        if not hasattr(self.client.user_wallet, 'address'):
                            raise ValueError("Invalid seed phrase: Not a valid wallet")
                            
                        # For mock mode, we'll create a new user if one doesn't exist
                        print("No existing user found, creating new user...")
                        username = f"user_{int(time.time()) % 10000}"
                        user = await self.client.initialize_user(
                            seed_phrase=seed_phrase,
                            username=username
                        )
                    
                    if not user:
                        raise ValueError("Failed to load or create user")
                        
                    print(f"Successfully logged in as {getattr(user, 'username', 'unknown')}")
                    return user
                    
                except Exception as e:
                    error_msg = f"Login failed: {str(e)}"
                    print(error_msg)
                    raise ValueError(error_msg) from e
                    
        except Exception as e:
            error_msg = f"Login error: {str(e)}"
            print(error_msg)
            raise ValueError(error_msg) from e
    
    def load_marketplace_items(self):
        # Clear existing items
        self.items_grid.clear()
        
        # Show loading indicator
        loading_item = QListWidgetItem("Loading items...")
        self.items_grid.addItem(loading_item)
        
        # Load items in background
        def on_items_loaded(items):
            self.items_grid.clear()
            
            if not items:
                self.items_grid.addItem(QListWidgetItem("No items found"))
                return
                
            for item_data in items:
                item_widget = ItemWidget(item_data)
                # Connect the bid_clicked signal to the main window's on_bid_clicked method
                item_widget.bid_clicked.connect(self.on_bid_clicked)
                list_item = QListWidgetItem()
                list_item.setSizeHint(QSize(220, 320))
                self.items_grid.addItem(list_item)
                self.items_grid.setItemWidget(list_item, item_widget)
        
        def on_error(error_msg):
            self.items_grid.clear()
            self.items_grid.addItem(QListWidgetItem(f"Error loading items: {error_msg}"))
        
        # Start loading items in a worker thread
        self.worker = AsyncWorker(self.load_items_async())
        self.worker.finished.connect(on_items_loaded)
        self.worker.error.connect(on_error)
        self.worker.start()
            
        # Show loading indicator
        self.my_items_list.addItem("Loading your items...")
        
        # Load items in background
        def on_items_loaded(items):
            self.my_items_list.clear()
            
            if not items:
                self.my_items_list.addItem("You don't have any items yet")
                return
                
            for item_data in items:
                item = QListWidgetItem(item_data.get('name', 'Unnamed Item'))
                self.my_items_list.addItem(item)
        
        def on_error(error_msg):
            self.my_items_list.clear()
            self.my_items_list.addItem(f"Error loading items: {error_msg}")
        
        # Start loading items in a worker thread
        self.worker = AsyncWorker(self.load_user_items_async())
        self.worker.finished.connect(on_items_loaded)
        self.worker.error.connect(on_error)
        self.worker.start()
    
    async def load_items_async(self):
        """Load all items from the mock database."""
        from mock_server import arweave_db
        from datetime import datetime, timezone
        
        items = []
        
        # Get all items from the mock Arweave database
        for tx_id, item_data in arweave_db.items.items():
            # Skip items that don't have the expected structure
            if not isinstance(item_data, dict):
                continue
                
            # Calculate time left
            time_left = "N/A"
            if 'auction_end_time' in item_data:
                try:
                    end_time = datetime.fromisoformat(item_data['auction_end_time'].replace('Z', '+00:00'))
                    now = datetime.now(timezone.utc)
                    
                    if end_time <= now:
                        time_left = "Ended"
                    else:
                        delta = end_time - now
                        if delta.days > 0:
                            time_left = f"{delta.days}d {delta.seconds // 3600}h"
                        else:
                            hours = delta.seconds // 3600
                            minutes = (delta.seconds % 3600) // 60
                            time_left = f"{hours}h {minutes}m"
                except (ValueError, TypeError):
                    pass
            
            # Create item dictionary for the UI
            item = {
                'id': tx_id,
                'name': item_data.get('name', 'Unnamed Item'),
                'description': item_data.get('description', 'No description'),
                'starting_price': float(item_data.get('starting_price', 0.0)),
                'current_bid': float(item_data.get('starting_price', 0.0)),  # In a real app, this would track the highest bid
                'owner': item_data.get('original_owner', 'Unknown'),
                'auction_end_time': item_data.get('auction_end_time', ''),
                'nano_address': item_data.get('nano_address', '')
            }
            items.append(item)
        
        # If no items found in mock database, add some sample items
        if not items and hasattr(self, 'mock_mode') and self.mock_mode:
            sample_items = [
                {
                    'name': 'Sample Digital Art',
                    'description': 'A beautiful piece of digital artwork',
                    'starting_price': 10.5,
                    'auction_end_time': (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
                    'original_owner': 'sample_owner_1',
                    'nano_address': 'nano_sample1234567890'
                },
                {
                    'name': 'Rare Collectible',
                    'description': 'A limited edition collectible item',
                    'starting_price': 25.0,
                    'auction_end_time': (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat(),
                    'original_owner': 'sample_owner_2',
                    'nano_address': 'nano_sample0987654321'
                }
            ]
            
            for item_data in sample_items:
                tx_id = arweave_db.store_data(item_data)
                item = {
                    'id': tx_id,
                    'name': item_data['name'],
                    'description': item_data['description'],
                    'starting_price': float(item_data['starting_price']),
                    'current_bid': float(item_data['starting_price']),
                    'owner': item_data['original_owner'],
                    'auction_end_time': item_data['auction_end_time'],
                    'nano_address': item_data['nano_address']
                }
                items.append(item)
        
        return items
    
    async def load_user_items_async(self):
        """Load items owned by the current user."""
        if not self.current_user:
            return []
            
        # Get all items and filter by owner
        all_items = await self.load_items_async()
        return [item for item in all_items if item.get('owner') == self.current_user.public_key]
    
    def create_item(self):
        # Get form data
        name = self.item_name.text().strip()
        description = self.item_description.toPlainText().strip()
        price_text = self.starting_price.text().strip()
        duration_text = self.duration.text().strip()
        
        # Validate inputs
        if not name:
            QMessageBox.warning(self, "Error", "Item name is required")
            return
            
        try:
            price = float(price_text)
            if price <= 0:
                raise ValueError("Price must be positive")
        except ValueError:
            QMessageBox.warning(self, "Error", "Invalid price")
            return
            
        try:
            duration = float(duration_text)
            if duration <= 0:
                raise ValueError("Duration must be positive")
        except ValueError:
            QMessageBox.warning(self, "Error", "Invalid duration")
            return
        
        # Create a simple loading overlay
        loading_widget = QWidget(self)
        loading_widget.setGeometry(self.rect())
        loading_widget.setStyleSheet("background-color: rgba(0, 0, 0, 128);")
        
        loading_layout = QVBoxLayout(loading_widget)
        loading_label = QLabel("Creating your item...")
        loading_label.setStyleSheet("color: white; font-size: 16px;")
        loading_label.setAlignment(Qt.AlignCenter)
        
        loading_layout.addWidget(loading_label, 0, Qt.AlignCenter)
        loading_widget.show()
        
        # Make sure the loading widget is on top
        loading_widget.raise_()
        
        def on_item_created(result):
            loading_widget.deleteLater()  # Clean up the loading widget
            
            if result:
                item, tx_id = result
                QMessageBox.information(
                    self,
                    "Item Created",
                    f"Item created successfully!\n\n"
                    f"Transaction ID: {tx_id}\n"
                    f"Nano Address: {item.metadata.get('nano_address', 'N/A')}"
                )
                # Clear form
                self.item_name.clear()
                self.item_description.clear()
                self.starting_price.clear()
                self.duration.setText("24")
                self.image_path.clear()
                
                # Switch to marketplace
                self.show_page(1)
            else:
                QMessageBox.critical(self, "Error", "Failed to create item")
        
        def on_error(error_msg):
            loading_widget.deleteLater()  # Clean up the loading widget
            QMessageBox.critical(self, "Error", f"Failed to create item: {error_msg}")
        
        # Start item creation in a worker thread
        self.worker = AsyncWorker(
            self.create_item_async(
                name=name,
                description=description,
                starting_price=price,
                duration_hours=duration,
                image_path=self.image_path.text()
            )
        )
        self.worker.finished.connect(on_item_created)
        self.worker.error.connect(on_error)
        self.worker.start()
    
    async def create_item_async(self, name, description, starting_price, duration_hours, image_path=None):
        try:
            if not self.client or not self.current_user:
                raise ValueError("Not logged in or client not initialized")
                
            # Create the item using the decentralized client
            # client.create_item returns a tuple of (item_data, tx_id)
            item_data, tx_id = await self.client.create_item(
                name=name,
                description=description,
                starting_price=starting_price,
                duration_hours=duration_hours,
                image_data=image_path.encode() if image_path else None
            )
            
            # Add to local items list for UI updates
            if item_data:
                self.items.append(item_data)
            
            # Return both the item data and transaction ID
            return item_data, tx_id
            
        except Exception as e:
            print(f"Error creating item: {e}")
            raise
    
    def on_bid_clicked(self, item_data):
        # Show custom bid dialog with history
        dialog = BidDialog(item_data, self)
        if dialog.exec_() == QDialog.Accepted:
            self.place_bid(item_data['id'], dialog.bid_amount)
    
    def place_bid(self, item_id, amount):
        # Show loading indicator
        loading_msg = QMessageBox(self)
        loading_msg.setWindowTitle("Placing Bid")
        loading_msg.setText(f"Placing bid of {amount} NANO...")
        loading_msg.setStandardButtons(QMessageBox.NoButton)
        loading_msg.show()
        
        def on_bid_placed(result):
            loading_msg.close()
            if result:
                self.add_message("Bid placed successfully!", "success")
                QMessageBox.information(
                    self,
                    "Bid Placed",
                    f"Your bid of {amount} NANO has been placed!\n\n"
                    f"Transaction ID: {result}"
                )
                # Refresh marketplace
                self.load_marketplace_items()
            else:
                QMessageBox.critical(self, "Error", "Failed to place bid")
        
        def on_error(error_msg):
            loading_msg.close()
            self.add_message(f"Bid failed: {str(error_msg)}", "error")
            QMessageBox.critical(self, "Error", f"Failed to place bid: {error_msg}")
        
        # Start bid process in a worker thread
        self.worker = AsyncWorker(self.place_bid_async(item_id, amount))
        self.worker.finished.connect(on_bid_placed)
        self.worker.error.connect(on_error)
        self.worker.start()
    
    async def place_bid_async(self, item_id, amount):
        # In a real implementation, this would use the DecentralizedClient
        # For now, return a mock transaction ID
        return f"mock_bid_tx_{item_id}_{int(amount * 1e6)}"
    
    def search_items(self):
        query = self.search_input.text().strip()
        # In a real implementation, this would filter items based on the search query
        # For now, just reload all items
        self.load_marketplace_items()
    
    def logout(self):
        """Handle user logout."""
        self.current_user = None
        self.client = None
        
        # Hide user info
        if hasattr(self, 'user_info'):
            self.user_info.setVisible(False)
        
        # Reset navigation buttons - only show Marketplace
        if hasattr(self, 'nav_buttons'):
            for btn_name, (_, _, visible) in self.nav_buttons.items():
                if hasattr(self, btn_name):
                    getattr(self, btn_name).setVisible(visible)
        
        # Hide other UI elements
        for btn_name in ['create_item_btn', 'my_items_btn', 'logout_btn']:
            if hasattr(self, btn_name):
                getattr(self, btn_name).setVisible(False)
        
        # Clear any sensitive data
        if hasattr(self, 'seed_input'):
            self.seed_input.clear()
        
        # Show login page
        self.stacked_widget.setCurrentIndex(0)
