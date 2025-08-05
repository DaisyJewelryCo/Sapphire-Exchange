"""
Unified Main Window for Sapphire Exchange.
Uses the unified application service for all operations.
"""
import sys
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QLineEdit, QTextEdit, QMessageBox, QScrollArea,
    QFrame, QTabWidget, QListWidget, QListWidgetItem, QFormLayout,
    QGroupBox, QDialog, QDialogButtonBox, QInputDialog, QApplication,
    QGridLayout, QSpacerItem, QSizePolicy, QButtonGroup, QTextBrowser
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPixmap, QIcon

from application_service import app_service
from models import User, Item, Bid
from utils.conversion_utils import format_currency, format_time_remaining


class SeedPhraseDialog(QDialog):
    """Beautiful dialog for displaying seed phrase."""
    
    def __init__(self, seed_phrase, parent=None):
        super().__init__(parent)
        self.seed_phrase = seed_phrase
        self.setup_ui()
    
    def setup_ui(self):
        """Create the beautiful seed phrase dialog UI."""
        self.setWindowTitle("Your New Seed Phrase")
        self.setModal(True)
        self.setFixedSize(600, 500)
        
        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(25)
        
        # Header section
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #2b7bba, stop:1 #1a5a8f);
                border-radius: 8px;
                padding: 20px;
            }
        """)
        
        header_layout = QVBoxLayout(header_frame)
        
        # Title
        title = QLabel("🔐 Your New Seed Phrase")
        title.setFont(QFont('Arial', 18, QFont.Bold))
        title.setStyleSheet("color: white; margin: 0;")
        title.setAlignment(Qt.AlignCenter)
        
        # Subtitle
        subtitle = QLabel("This is your unique recovery phrase")
        subtitle.setFont(QFont('Arial', 12))
        subtitle.setStyleSheet("color: #e8f4fd; margin: 5px 0 0 0;")
        subtitle.setAlignment(Qt.AlignCenter)
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        
        # Warning section
        warning_frame = QFrame()
        warning_frame.setStyleSheet("""
            QFrame {
                background-color: #fff3cd;
                border: 1px solid #ffeaa7;
                border-radius: 6px;
                padding: 15px;
            }
        """)
        
        warning_layout = QVBoxLayout(warning_frame)
        
        warning_title = QLabel("⚠️ IMPORTANT SECURITY NOTICE")
        warning_title.setFont(QFont('Arial', 12, QFont.Bold))
        warning_title.setStyleSheet("color: #856404; margin-bottom: 8px;")
        
        warning_text = QLabel(
            "• Write down these words in the exact order shown\n"
            "• Store them in a safe, offline location\n"
            "• Never share your seed phrase with anyone\n"
            "• This is the ONLY way to recover your account"
        )
        warning_text.setFont(QFont('Arial', 10))
        warning_text.setStyleSheet("color: #856404; line-height: 1.4;")
        warning_text.setWordWrap(True)
        
        warning_layout.addWidget(warning_title)
        warning_layout.addWidget(warning_text)
        
        # Seed phrase display
        seed_frame = QFrame()
        seed_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 2px solid #e9ecef;
                border-radius: 8px;
                padding: 20px;
            }
        """)
        
        seed_layout = QVBoxLayout(seed_frame)
        
        seed_title = QLabel("Your Seed Phrase:")
        seed_title.setFont(QFont('Arial', 12, QFont.Bold))
        seed_title.setStyleSheet("color: #495057; margin-bottom: 10px;")
        
        # Create grid for seed words
        words = self.seed_phrase.split()
        words_grid = QGridLayout()
        words_grid.setSpacing(8)
        
        for i, word in enumerate(words):
            word_frame = QFrame()
            word_frame.setStyleSheet("""
                QFrame {
                    background-color: white;
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                    padding: 8px 12px;
                    min-width: 80px;
                }
            """)
            
            word_layout = QHBoxLayout(word_frame)
            word_layout.setContentsMargins(8, 6, 8, 6)
            
            # Word number
            number_label = QLabel(f"{i+1}.")
            number_label.setFont(QFont('Arial', 9))
            number_label.setStyleSheet("color: #6c757d; font-weight: bold;")
            number_label.setFixedWidth(20)
            
            # Word text
            word_label = QLabel(word)
            word_label.setFont(QFont('Courier New', 11, QFont.Bold))
            word_label.setStyleSheet("color: #212529;")
            
            word_layout.addWidget(number_label)
            word_layout.addWidget(word_label)
            word_layout.addStretch()
            
            # Arrange in 3 columns
            row = i // 3
            col = i % 3
            words_grid.addWidget(word_frame, row, col)
        
        seed_layout.addWidget(seed_title)
        seed_layout.addLayout(words_grid)
        
        # Copy button
        copy_layout = QHBoxLayout()
        copy_layout.addStretch()
        
        self.copy_button = QPushButton("📋 Copy to Clipboard")
        self.copy_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:pressed {
                background-color: #545b62;
            }
        """)
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        
        copy_layout.addWidget(self.copy_button)
        copy_layout.addStretch()
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.confirm_button = QPushButton("I've Saved My Seed Phrase")
        self.confirm_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
                min-width: 200px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)
        self.confirm_button.clicked.connect(self.accept)
        
        button_layout.addWidget(self.confirm_button)
        button_layout.addStretch()
        
        # Add all sections to main layout
        layout.addWidget(header_frame)
        layout.addWidget(warning_frame)
        layout.addWidget(seed_frame)
        layout.addLayout(copy_layout)
        layout.addStretch()
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def copy_to_clipboard(self):
        """Copy seed phrase to clipboard."""
        try:
            from PyQt5.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(self.seed_phrase)
            
            # Temporarily change button text to show feedback
            original_text = self.copy_button.text()
            self.copy_button.setText("✅ Copied!")
            self.copy_button.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                    font-size: 12px;
                }
            """)
            
            # Reset button after 2 seconds
            QTimer.singleShot(2000, lambda: self.reset_copy_button(original_text))
            
        except Exception as e:
            QMessageBox.warning(self, "Copy Failed", f"Failed to copy to clipboard: {str(e)}")
    
    def reset_copy_button(self, original_text):
        """Reset copy button to original state."""
        self.copy_button.setText(original_text)
        self.copy_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:pressed {
                background-color: #545b62;
            }
        """)


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


class LoginScreen(QWidget):
    """Beautiful login screen with seed phrase input."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.is_new_user = False
        self.current_user = None
        self.setup_ui()
    
    def setup_ui(self):
        """Create the beautiful login screen UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(50, 50, 50, 50)
        layout.setSpacing(30)
        
        # Main title
        title = QLabel("Sapphire Exchange")
        title.setFont(QFont('Arial', 28, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #2b7bba; margin-bottom: 20px;")
        
        # Subtitle
        subtitle = QLabel("Decentralized Auction Platform")
        subtitle.setFont(QFont('Arial', 14))
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #666; margin-bottom: 40px;")
        
        # Login card
        card = QFrame()
        card.setFrameStyle(QFrame.Box)
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 30px;
            }
        """)
        
        # Card layout
        form_layout = QVBoxLayout(card)
        form_layout.setSpacing(20)
        
        # Form title
        form_title = QLabel("Welcome Back")
        form_title.setFont(QFont('Arial', 16, QFont.Bold))
        form_title.setAlignment(Qt.AlignCenter)
        
        # Seed phrase input
        seed_label = QLabel("Your Seed Phrase:")
        seed_label.setFont(QFont('Arial', 12))
        
        self.seed_input = QTextEdit()
        self.seed_input.setPlaceholderText("Enter your seed phrase (12-24 words)")
        self.seed_input.setMaximumHeight(80)
        self.seed_input.setStyleSheet("""
            QTextEdit {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 8px;
                font-size: 14px;
                min-height: 60px;
                max-height: 80px;
                font-family: 'Courier New', monospace;
            }
            QTextEdit:focus {
                border: 1px solid #4a6ee0;
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
        
        # Add to main layout
        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(card, 0, Qt.AlignCenter)
        layout.addStretch()
        
        self.setLayout(layout)
    
    def handle_new_account(self):
        """Handle new account creation with seed phrase generation."""
        try:
            # Generate a BIP-39 compatible seed phrase
            import secrets
            wordlist = [
                'abandon', 'ability', 'able', 'about', 'above', 'absent', 'absorb', 'abstract', 'absurd', 'abuse',
                'access', 'accident', 'account', 'accuse', 'achieve', 'acid', 'acoustic', 'across', 'act', 'action',
                'actor', 'actress', 'actual', 'adapt', 'add', 'addict', 'address', 'adjust', 'admit', 'adult',
                'advance', 'advice', 'aerobic', 'affair', 'afford', 'afraid', 'again', 'agent', 'agree', 'ahead',
                'aim', 'air', 'airport', 'aisle', 'alarm', 'album', 'alcohol', 'alert', 'alien', 'all',
                'alley', 'allow', 'almost', 'alone', 'alpha', 'already', 'also', 'alter', 'always', 'amateur',
                'amazing', 'among', 'amount', 'amused', 'analyst', 'anchor', 'ancient', 'anger', 'angle', 'angry',
                'animal', 'ankle', 'announce', 'annual', 'another', 'answer', 'antenna', 'antique', 'anxiety', 'any',
                'apart', 'apology', 'appear', 'apple', 'approve', 'april', 'arch', 'arctic', 'area', 'arena',
                'argue', 'arm', 'armed', 'armor', 'army', 'around', 'arrange', 'arrest', 'arrive', 'arrow',
                'art', 'artefact', 'artist', 'artwork', 'ask', 'aspect', 'assault', 'asset', 'assist', 'assume',
                'asthma', 'athlete', 'atom', 'attack', 'attend', 'attitude', 'attract', 'auction', 'audit', 'august',
                'aunt', 'author', 'auto', 'autumn', 'average', 'avocado', 'avoid', 'awake', 'aware', 'away',
                'awesome', 'awful', 'awkward', 'axis', 'baby', 'bachelor', 'bacon', 'badge', 'bag', 'balance'
            ]
            
            # Generate 15 random words
            seed_words = [secrets.choice(wordlist) for _ in range(15)]
            seed_phrase = ' '.join(seed_words)
            
            # Show the beautiful seed phrase dialog
            dialog = SeedPhraseDialog(seed_phrase, self)
            result = dialog.exec_()
            
            if result == QDialog.Accepted:
                # Set the seed phrase in the input field
                self.seed_input.setPlainText(seed_phrase)
                self.is_new_user = True
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate seed phrase: {str(e)}")
    
    def handle_login(self):
        """Handle the login process with the provided seed phrase."""
        try:
            # Get and validate seed phrase
            seed_phrase = self.seed_input.toPlainText().strip()
            
            if not seed_phrase:
                QMessageBox.warning(self, "Input Required", "Please enter your seed phrase or create a new account.")
                return
                
            # Validate seed phrase format (basic check)
            words = seed_phrase.strip().split()
            if len(words) not in [12, 15, 18, 21, 24]:
                QMessageBox.warning(self, "Invalid Seed Phrase", 
                                  f"Invalid seed phrase length: {len(words)} words. Must be 12, 15, 18, 21, or 24 words.")
                return
            
            # Disable login button to prevent multiple clicks
            self.login_btn.setEnabled(False)
            self.login_btn.setText("Please wait...")
            
            # Create a worker for the login process
            worker = AsyncWorker(self.login_async(seed_phrase))
            worker.finished.connect(self.on_login_complete)
            worker.error.connect(self.on_login_error)
            worker.start()
            self.worker = worker  # Keep reference
            
        except Exception as e:
            self.login_btn.setEnabled(True)
            self.login_btn.setText("Continue")
            QMessageBox.critical(self, "Login Error", f"Failed to login: {str(e)}")
    
    async def login_async(self, seed_phrase):
        """Async login process."""
        try:
            if self.is_new_user:
                # Register new user with seed phrase
                success, message, user = await app_service.register_user_with_seed(seed_phrase)
            else:
                # Login existing user with seed phrase
                success, message, user = await app_service.login_user_with_seed(seed_phrase)
            
            return success, message, user
            
        except Exception as e:
            return False, str(e), None
    
    def on_login_complete(self, result):
        """Handle completion of the login process."""
        try:
            success, message, user = result
            
            # Re-enable login button
            self.login_btn.setEnabled(True)
            self.login_btn.setText("Continue")
            
            if success:
                self.current_user = user
                # Notify parent window that login was successful
                if self.parent_window:
                    self.parent_window.on_login_success(user)
            else:
                QMessageBox.warning(self, "Login Failed", message)
                
        except Exception as e:
            self.login_btn.setEnabled(True)
            self.login_btn.setText("Continue")
            QMessageBox.critical(self, "Login Error", f"Login process failed: {str(e)}")
    
    def on_login_error(self, error_message):
        """Handle login errors."""
        self.login_btn.setEnabled(True)
        self.login_btn.setText("Continue")
        QMessageBox.critical(self, "Login Error", f"An error occurred during login: {error_message}")


class AuctionListWidget(QWidget):
    """Widget for displaying auction listings."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_auctions()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("Active Auctions")
        header.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(header)
        
        # Search
        search_layout = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search auctions...")
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search_auctions)
        search_layout.addWidget(self.search_edit)
        search_layout.addWidget(self.search_button)
        layout.addLayout(search_layout)
        
        # Auction list
        self.auction_list = QListWidget()
        self.auction_list.itemDoubleClicked.connect(self.view_auction_details)
        # Make the auction list expand to fill available space
        self.auction_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.auction_list)
        
        # Refresh button
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.load_auctions)
        layout.addWidget(self.refresh_button)
        
        self.setLayout(layout)
    
    def load_auctions(self):
        """Load active auctions."""
        worker = AsyncWorker(app_service.get_active_auctions(limit=50))
        worker.finished.connect(self.on_auctions_loaded)
        worker.error.connect(self.on_error)
        worker.start()
        self.worker = worker
    
    def search_auctions(self):
        """Search auctions."""
        query = self.search_edit.text().strip()
        if not query:
            self.load_auctions()
            return
        
        worker = AsyncWorker(app_service.search_auctions(query, limit=50))
        worker.finished.connect(self.on_auctions_loaded)
        worker.error.connect(self.on_error)
        worker.start()
        self.worker = worker
    
    def on_auctions_loaded(self, auctions):
        """Handle loaded auctions."""
        self.auction_list.clear()
        
        for item in auctions:
            # Create list item
            list_item = QListWidgetItem()
            
            # Create display text
            current_bid = float(item.current_bid_doge or item.starting_price_doge or "0")
            time_remaining = format_time_remaining(item.auction_end)
            
            text = f"{item.title}\n"
            text += f"Current Bid: {format_currency(current_bid, 'DOGE')}\n"
            text += f"Time Remaining: {time_remaining}"
            
            list_item.setText(text)
            list_item.setData(Qt.UserRole, item)
            
            self.auction_list.addItem(list_item)
    
    def view_auction_details(self, item):
        """View auction details."""
        auction_item = item.data(Qt.UserRole)
        if auction_item:
            # Get parent window and show auction details
            main_window = self.window()
            if hasattr(main_window, 'show_auction_details'):
                main_window.show_auction_details(auction_item.id)
    
    def on_error(self, error):
        """Handle errors."""
        QMessageBox.warning(self, "Error", f"Failed to load auctions: {error}")


class WalletWidget(QWidget):
    """Widget for wallet management."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_balances()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("Wallet")
        header.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(header)
        
        # Balances
        self.balances_group = QGroupBox("Balances")
        balances_layout = QVBoxLayout()
        
        self.nano_balance_label = QLabel("NANO: Loading...")
        self.doge_balance_label = QLabel("DOGE: Loading...")
        
        balances_layout.addWidget(self.nano_balance_label)
        balances_layout.addWidget(self.doge_balance_label)
        
        self.balances_group.setLayout(balances_layout)
        layout.addWidget(self.balances_group)
        
        # Addresses
        self.addresses_group = QGroupBox("Addresses")
        addresses_layout = QVBoxLayout()
        
        user = app_service.get_current_user()
        if user:
            self.nano_address_label = QLabel(f"NANO: {user.nano_address}")
            self.doge_address_label = QLabel(f"DOGE: {user.doge_address}")
            
            addresses_layout.addWidget(self.nano_address_label)
            addresses_layout.addWidget(self.doge_address_label)
        
        self.addresses_group.setLayout(addresses_layout)
        layout.addWidget(self.addresses_group)
        
        # Refresh button
        self.refresh_button = QPushButton("Refresh Balances")
        self.refresh_button.clicked.connect(self.load_balances)
        layout.addWidget(self.refresh_button)
        
        # Add stretch to push content to the top but allow expansion
        layout.addStretch()
        self.setLayout(layout)
    
    def load_balances(self):
        """Load wallet balances."""
        if not app_service.is_user_logged_in():
            return
        
        worker = AsyncWorker(app_service.get_wallet_balances())
        worker.finished.connect(self.on_balances_loaded)
        worker.error.connect(self.on_error)
        worker.start()
        self.worker = worker
    
    def on_balances_loaded(self, balances):
        """Handle loaded balances."""
        nano_balance = balances.get('nano', 0) or 0
        doge_balance = balances.get('dogecoin', 0) or 0
        
        self.nano_balance_label.setText(f"NANO: {format_currency(nano_balance, 'NANO')}")
        self.doge_balance_label.setText(f"DOGE: {format_currency(doge_balance, 'DOGE')}")
    
    def on_error(self, error):
        """Handle errors."""
        self.nano_balance_label.setText("NANO: Error loading")
        self.doge_balance_label.setText("DOGE: Error loading")


class MainWindow(QMainWindow):
    """Main application window using unified architecture."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sapphire Exchange")
        # Set initial size but allow resizing
        self.resize(1200, 800)
        self.setMinimumSize(800, 600)  # Set minimum size to ensure usability
        
        # Initialize application service
        self.init_app_service()
        
        # Setup UI
        self.setup_ui()
        
        # Setup timers
        self.setup_timers()
    
    def init_app_service(self):
        """Initialize the application service."""
        # Setup callbacks
        app_service.add_status_change_callback(self.on_status_change)
        app_service.add_user_change_callback(self.on_user_change)
        app_service.add_auction_update_callback(self.on_auction_update)
        
        # Initialize asynchronously
        worker = AsyncWorker(app_service.initialize())
        worker.finished.connect(self.on_app_initialized)
        worker.error.connect(self.on_init_error)
        worker.start()
        self.init_worker = worker
    
    def setup_ui(self):
        """Setup the user interface."""
        # Create and configure status bar
        status_bar = self.statusBar()
        status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #f8f9fa;
                color: #212529;
                border-top: 1px solid #dee2e6;
                font-size: 12px;
                padding: 4px;
            }
            QStatusBar::item {
                border: none;
                padding: 0 8px;
            }
        """)
        
        # Add permanent widgets to status bar
        self.status_label = QLabel("Status: Initializing...")
        self.connection_status = QLabel("Connections: Checking...")
        self.last_update = QLabel("Last update: --:--:--")
        
        # Add widgets to status bar
        status_bar.addPermanentWidget(self.status_label, 1)
        status_bar.addPermanentWidget(self.connection_status, 2)
        status_bar.addPermanentWidget(self.last_update)
        
        # Create a timer to update the status bar periodically
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(5000)  # Update every 5 seconds
        
        # Initialize connection status indicators
        self.setup_connection_indicators()
        
        # Use stacked widget to switch between login and main interface
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        
        # Create login screen
        self.login_screen = LoginScreen(self)
        self.stacked_widget.addWidget(self.login_screen)
        
        # Create main interface
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)  # Changed to horizontal layout for sidebar
        
        # Create sidebar
        self.create_sidebar(main_layout)
        
        # Create main content area
        self.create_main_content(main_layout)
        
        # Add main widget to stacked widget
        self.stacked_widget.addWidget(main_widget)
        
        # Start with login screen
        self.stacked_widget.setCurrentWidget(self.login_screen)
        
        # Initial status update
        self.update_status()
    
    def create_sidebar(self, parent_layout):
        """Create the sidebar navigation."""
        self.sidebar = QWidget()
        # Remove fixed width to make it responsive, but set a reasonable minimum and maximum width
        self.sidebar.setMinimumWidth(180)
        self.sidebar.setMaximumWidth(250)
        sidebar_style = (
            "QWidget { background-color: #2c3e50; border-right: 1px solid #34495e; }"
            "QPushButton { background-color: transparent; color: #ecf0f1; border: none; padding: 12px 16px; text-align: left; font-size: 14px; font-weight: 500; }"
            "QPushButton:hover { background-color: #34495e; }"
            "QPushButton:checked { background-color: #1abc9c; }"
            "QPushButton:pressed { background-color: #16a085; }"
            "QLabel { color: #ecf0f1; padding: 8px; }"
            "QLabel#user_info { font-size: 12px; padding: 4px 8px; background-color: rgba(0, 0, 0, 0.2); border-radius: 4px; margin: 8px; }"
            "QLabel#user_balance { font-size: 14px; font-weight: bold; color: #1abc9c; }"
        )
        self.sidebar.setStyleSheet(sidebar_style)
        
        # Create sidebar layout and store it as instance variable
        self.sidebar_layout = QVBoxLayout()
        self.sidebar_layout.setContentsMargins(0, 0, 0, 0)
        self.sidebar_layout.setSpacing(0)
        self.sidebar.setLayout(self.sidebar_layout)
        
        # Add logo
        logo_label = QLabel("Sapphire Exchange")
        logo_label.setAlignment(Qt.AlignCenter)
        logo_label.setStyleSheet(
            "QLabel {"
            "    color: #ecf0f1;"
            "    font-size: 16px;"
            "    font-weight: bold;"
            "    padding: 20px 10px;"
            "    border-bottom: 1px solid #34495e;"
            "}"
        )
        self.sidebar_layout.addWidget(logo_label)
        
        # Navigation buttons with proper visibility states
        self.nav_buttons = {
            "marketplace_btn": {
                "text": "🏠  Marketplace",
                "page_id": 0,  # Changed to match our tab structure
                "visible": True,  # Always visible
                "requires_auth": False
            },
            "sell_item_btn": {
                "text": "🛍️  Sell Item",
                "page_id": 2,  # New page for item creation
                "visible": False,  # Requires auth
                "requires_auth": True
            },
            "my_items_btn": {
                "text": "📦  My Items",
                "page_id": 3,  # New page for user's items
                "visible": False,  # Requires auth
                "requires_auth": True
            },
            "settings_btn": {
                "text": "⚙️  Settings",
                "page_id": 4,  # New page for settings
                "visible": False,  # Requires auth
                "requires_auth": True
            }
        }
        
        # Create navigation buttons
        self.nav_button_group = QButtonGroup()
        for btn_name, btn_data in self.nav_buttons.items():
            btn = QPushButton(btn_data["text"])
            btn.setCheckable(True)
            btn.setVisible(btn_data["visible"])
            btn.setProperty("requires_auth", btn_data["requires_auth"])
            btn.clicked.connect(lambda checked, p=btn_data["page_id"]: self.switch_tab(p))
            self.nav_button_group.addButton(btn, btn_data["page_id"])
            setattr(self, btn_name, btn)  # Store reference to button
            self.sidebar_layout.addWidget(btn)
        
        # Add spacer
        self.sidebar_layout.addStretch(1)
        
        # Add user info (initially hidden)
        self.user_info_widget = QLabel("Not logged in")
        self.user_info_widget.setAlignment(Qt.AlignCenter)
        self.user_info_widget.setStyleSheet("QLabel { color: #bdc3c7; font-size: 12px; padding: 10px; border-top: 1px solid #34495e; }")
        self.user_info_widget.setVisible(False)
        self.sidebar_layout.addWidget(self.user_info_widget)
        
        # Add logout button (initially hidden)
        self.logout_btn = QPushButton("Logout")
        self.logout_btn.setStyleSheet("QPushButton { background-color: #e74c3c; color: white; border: none; padding: 10px; margin: 10px; border-radius: 4px; } QPushButton:hover { background-color: #c0392b; }")
        self.logout_btn.setVisible(False)
        self.logout_btn.clicked.connect(self.logout)
        self.sidebar_layout.addWidget(self.logout_btn)
        
        parent_layout.addWidget(self.sidebar)
    
    def create_main_content(self, parent_layout):
        """Create the main content area."""
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        
        # Main content with tabs
        self.tab_widget = QTabWidget()
        # Make the tab widget expand to fill available space
        self.tab_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Marketplace tab (index 0)
        self.auctions_widget = AuctionListWidget()
        self.tab_widget.addTab(self.auctions_widget, "Marketplace")
        
        # Wallet tab (index 1)
        self.wallet_widget = WalletWidget()
        self.tab_widget.addTab(self.wallet_widget, "Wallet")
        
        # Sell Item tab (index 2)
        # TODO: Implement item creation widget
        sell_item_widget = QWidget()
        sell_item_layout = QVBoxLayout(sell_item_widget)
        sell_item_label = QLabel("Sell Item - Under Construction")
        sell_item_label.setAlignment(Qt.AlignCenter)
        sell_item_layout.addWidget(sell_item_label)
        self.tab_widget.addTab(sell_item_widget, "Sell Item")
        
        # My Items tab (index 3)
        # TODO: Implement user items widget
        my_items_widget = QWidget()
        my_items_layout = QVBoxLayout(my_items_widget)
        my_items_label = QLabel("My Items - Under Construction")
        my_items_label.setAlignment(Qt.AlignCenter)
        my_items_layout.addWidget(my_items_label)
        self.tab_widget.addTab(my_items_widget, "My Items")
        
        # Settings tab (index 4)
        # TODO: Implement settings widget
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)
        settings_label = QLabel("Settings - Under Construction")
        settings_label.setAlignment(Qt.AlignCenter)
        settings_layout.addWidget(settings_label)
        self.tab_widget.addTab(settings_widget, "Settings")
        
        content_layout.addWidget(self.tab_widget)
        parent_layout.addWidget(content_widget)
        
        # Create activity feed overlay
        self.create_activity_feed()
        
        # Initialize connection status
        self.update_connection_status("arweave", False)
        self.update_connection_status("nano", False)
        self.update_connection_status("doge", False)
        self.update_main_status_indicator()
        self.update_timestamp()
    
    def switch_tab(self, index):
        """Switch between tabs."""
        self.tab_widget.setCurrentIndex(index)
        
        # Update sidebar button states if using button group
        if hasattr(self, 'nav_button_group'):
            button = self.nav_button_group.button(index)
            if button:
                button.setChecked(True)
        else:
            # Fallback to individual button handling
            buttons = [self.marketplace_btn, self.sell_item_btn, self.my_items_btn, self.settings_btn]
            for i, btn in enumerate(buttons):
                if btn:
                    btn.setChecked(i == index)
    
    def show_login(self):
        """Show login screen."""
        self.stacked_widget.setCurrentWidget(self.login_screen)
    
    def on_login_success(self, user):
        """Handle successful login."""
        if user:
            self.user_info_widget.setText(f"Logged in as: {user.username}")
            self.logout_btn.setVisible(True)
            
            # Show navigation buttons that require authentication
            if hasattr(self, 'nav_buttons'):
                for btn_name, btn_data in self.nav_buttons.items():
                    if btn_data.get("requires_auth", False):
                        btn = getattr(self, btn_name, None)
                        if btn:
                            btn.setVisible(True)
            
            # Switch to main interface
            self.stacked_widget.setCurrentIndex(1)  # Main widget is at index 1
            
            # Refresh wallet
            if hasattr(self, 'wallet_widget'):
                self.wallet_widget.load_balances()
            
            # Refresh auctions
            if hasattr(self, 'auctions_widget'):
                self.auctions_widget.load_auctions()
    
    def logout(self):
        """Logout current user."""
        worker = AsyncWorker(app_service.logout_user())
        worker.finished.connect(self.on_logout_complete)
        worker.start()
        self.logout_worker = worker
    
    def on_logout_complete(self, success):
        """Handle logout completion."""
        if success:
            self.user_info_widget.setText("Not logged in")
            self.logout_btn.setVisible(False)
            
            # Hide navigation buttons that require authentication
            if hasattr(self, 'nav_buttons'):
                for btn_name, btn_data in self.nav_buttons.items():
                    if btn_data.get("requires_auth", False):
                        btn = getattr(self, btn_name, None)
                        if btn:
                            btn.setVisible(False)
    
    def setup_connection_indicators(self):
        """Setup connection status indicators in the status bar."""
        status_bar = self.statusBar()
        
        # Create a container widget for connection indicators
        self.indicators_widget = QWidget()
        self.indicators_layout = QHBoxLayout(self.indicators_widget)
        self.indicators_layout.setContentsMargins(0, 0, 10, 0)
        self.indicators_layout.setSpacing(15)
        
        # Add connection indicators for each service
        self.connection_indicators = {}
        
        # Add service indicators (Arweave, Nano, Doge)
        services = [
            ("arweave", "Arweave"),
            ("nano", "Nano"),
            ("doge", "Doge")
        ]
        
        for service_id, service_name in services:
            # Create indicator widget
            container = QWidget()
            container.setObjectName(f"{service_id}_widget")
            layout = QHBoxLayout(container)
            layout.setContentsMargins(5, 0, 5, 0)
            layout.setSpacing(5)
            
            # Status dot
            dot = QLabel("●")
            dot.setObjectName(f"{service_id}_dot")
            dot.setStyleSheet("font-size: 16px; color: #95a5a6;")
            dot.setToolTip(f"{service_name} status")
            
            # Service name
            label = QLabel(service_name.upper())
            label.setObjectName(f"{service_id}_label")
            label.setStyleSheet("color: #95a5a6; font-size: 10px; font-weight: bold;")
            
            layout.addWidget(dot)
            layout.addWidget(label)
            
            # Store reference
            self.connection_indicators[service_id] = container
            self.indicators_layout.addWidget(container)
        
        # Add wallet status indicator
        self.wallet_container = QWidget()
        self.wallet_container.setObjectName("wallet_indicator")
        wallet_layout = QHBoxLayout(self.wallet_container)
        wallet_layout.setContentsMargins(5, 0, 5, 0)
        wallet_layout.setSpacing(5)
        
        # Wallet dot indicator
        self.wallet_dot = QLabel("●")
        self.wallet_dot.setObjectName("wallet_dot")
        self.wallet_dot.setStyleSheet("font-size: 16px; color: #95a5a6;")  # Default gray
        
        # Wallet label
        wallet_label = QLabel("WALLET")
        wallet_label.setStyleSheet("color: #95a5a6; font-size: 10px; font-weight: bold;")
        
        wallet_layout.addWidget(self.wallet_dot)
        wallet_layout.addWidget(wallet_label)
        self.indicators_layout.addWidget(self.wallet_container)
        
        # Add activity feed indicator
        self.activity_container = QWidget()
        self.activity_container.setObjectName("activity_indicator")
        activity_layout = QHBoxLayout(self.activity_container)
        activity_layout.setContentsMargins(5, 0, 5, 0)
        activity_layout.setSpacing(5)
        
        # Activity dot indicator
        self.activity_dot = QLabel("●")
        self.activity_dot.setObjectName("activity_dot")
        self.activity_dot.setStyleSheet("font-size: 16px; color: #95a5a6;")  # Default gray
        
        # Activity label
        activity_label = QLabel("ACTIVITY")
        activity_label.setStyleSheet("color: #95a5a6; font-size: 10px; font-weight: bold;")
        
        activity_layout.addWidget(self.activity_dot)
        activity_layout.addWidget(activity_label)
        self.indicators_layout.addWidget(self.activity_container)
        
        # Make activity container clickable
        self.activity_container.mousePressEvent = lambda e: self.toggle_activity_log_overlay()
        self.activity_container.setCursor(Qt.PointingHandCursor)
        
        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setStyleSheet("color: #95a5a6;")
        self.indicators_layout.addWidget(separator)
        
        # Add to status bar
        status_bar.addPermanentWidget(self.indicators_widget)
        
        # Add stretch to push indicators to the right
        status_bar.addPermanentWidget(QWidget(), 1)
    
    def update_status(self):
        """Update status display with detailed connection information."""
        try:
            status = app_service.get_system_status()
            
            if not status:
                self.statusBar().showMessage("Status: Not connected")
                return
                
            if status.get('initialized'):
                # Get blockchain status
                blockchain_status = status.get('blockchain', {})
                overall_status = blockchain_status.get('overall_status', 'unknown')
                
                # Get connection status for each service
                connections = []
                for service in ['arweave', 'nano', 'doge']:
                    if service in status and 'status' in status[service]:
                        status_text = '✓' if status[service]['status'] == 'connected' else '✗'
                        connections.append(f"{service.upper()}: {status_text}")
                
                # Format status message
                status_msg = f"Status: {overall_status.title()} | {' | '.join(connections)} | Last update: {datetime.now().strftime('%H:%M:%S')}"
                self.statusBar().showMessage(status_msg)
                
                # Update connection indicators
                for service in ['arweave', 'nano', 'doge']:
                    if service in status and 'status' in status[service]:
                        is_connected = status[service]['status'] == 'connected'
                        self.update_connection_status(service, is_connected)
                
                # Update main status indicator
                self.update_main_status_indicator()
                
            else:
                self.statusBar().showMessage("Status: Initializing...")
                
        except Exception as e:
            self.statusBar().showMessage(f"Status: Error - {str(e)}")
    
    def refresh_auctions(self):
        """Refresh auction listings."""
        if app_service.is_user_logged_in():
            self.auctions_widget.load_auctions()
    
    def show_auction_details(self, item_id: str):
        """Show auction details dialog."""
        worker = AsyncWorker(app_service.get_auction_details(item_id))
        worker.finished.connect(lambda details: self.on_auction_details_loaded(details, item_id))
        worker.start()
        self.details_worker = worker
    
    def on_auction_details_loaded(self, details, item_id):
        """Handle loaded auction details."""
        if not details:
            QMessageBox.warning(self, "Error", "Failed to load auction details")
            return
        
        # Create details dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Auction Details")
        dialog.setFixedSize(600, 400)
        
        layout = QVBoxLayout()
        
        item = details['item']
        bids = details['bids']
        seller = details['seller']
        
        # Item info
        info_text = f"Title: {item.title}\n"
        info_text += f"Description: {item.description}\n"
        info_text += f"Seller: {seller.username if seller else 'Unknown'}\n"
        info_text += f"Starting Price: {format_currency(item.starting_price_doge, 'DOGE')}\n"
        info_text += f"Current Bid: {format_currency(item.current_bid_doge or item.starting_price_doge, 'DOGE')}\n"
        info_text += f"Time Remaining: {details['time_remaining']}\n"
        info_text += f"Bids: {len(bids)}"
        
        info_label = QLabel(info_text)
        layout.addWidget(info_label)
        
        # Bid button
        if app_service.is_user_logged_in() and item.status == 'active':
            bid_button = QPushButton("Place Bid")
            bid_button.clicked.connect(lambda: self.place_bid(item_id, dialog))
            layout.addWidget(bid_button)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def place_bid(self, item_id: str, parent_dialog):
        """Place a bid on an auction."""
        amount, ok = QInputDialog.getDouble(
            self, "Place Bid", "Bid Amount (DOGE):", 
            decimals=8, min=0.00000001
        )
        
        if not ok:
            return
        
        worker = AsyncWorker(app_service.place_bid(item_id, amount, "DOGE"))
        worker.finished.connect(lambda result: self.on_bid_placed(result, parent_dialog))
        worker.start()
        self.bid_worker = worker
    
    def on_bid_placed(self, result, parent_dialog):
        """Handle bid placement result."""
        success, message, bid = result
        
        if success:
            QMessageBox.information(self, "Success", "Bid placed successfully!")
            parent_dialog.accept()
            self.auctions_widget.load_auctions()  # Refresh auctions
        else:
            QMessageBox.warning(self, "Error", f"Failed to place bid: {message}")
    
    # Event callbacks
    def on_app_initialized(self, success):
        """Handle application initialization."""
        if success:
            self.statusBar().showMessage("Status: Ready")
        else:
            self.statusBar().showMessage("Status: Initialization failed")
    
    def on_init_error(self, error):
        """Handle initialization error."""
        self.statusBar().showMessage(f"Status: Error - {error}")
    
    def on_status_change(self, component, status):
        """Handle status changes."""
        # Update UI based on status changes
        pass
    
    def on_user_change(self, event, user):
        """Handle user changes."""
        if event == 'login':
            self.on_login_success(user)
        elif event == 'logout':
            self.user_info_widget.setText("Not logged in")
            self.logout_btn.setVisible(False)
            
            # Hide navigation buttons that require authentication
            if hasattr(self, 'nav_buttons'):
                for btn_name, btn_data in self.nav_buttons.items():
                    if btn_data.get("requires_auth", False):
                        btn = getattr(self, btn_name, None)
                        if btn:
                            btn.setVisible(False)
    
    def on_auction_update(self, event, data):
        """Handle auction updates."""
        if event in ['bid_placed', 'auction_ended']:
            # Refresh auction list
            self.auctions_widget.load_auctions()
    
    def setup_timers(self):
        """Setup update timers."""
        # Status update timer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(5000)  # Update every 5 seconds
        
        # Auction refresh timer
        self.auction_timer = QTimer()
        self.auction_timer.timeout.connect(self.refresh_auctions)
        self.auction_timer.start(30000)  # Refresh every 30 seconds
    
    def closeEvent(self, event):
        """Handle window close event."""
        # Shutdown application service
        worker = AsyncWorker(app_service.shutdown())
        worker.finished.connect(lambda: event.accept())
        worker.start()
        
        # Don't accept the event immediately
        event.ignore()
    
    def create_status_indicator(self, name, color):
        """Create a status indicator widget.
        
        Args:
            name (str): Name of the service (e.g., 'Arweave', 'Nano')
            color (str): Base color for the indicator
            
        Returns:
            QWidget: Configured status indicator widget
        """
        widget = QWidget()
        widget.setObjectName(f"{name.lower()}_widget")
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(3)
        
        # Status dot
        dot = QLabel("●")
        dot.setObjectName(f"{name.lower()}_dot")
        dot.setStyleSheet(f"font-size: 12px; color: {color};")
        dot.setCursor(Qt.PointingHandCursor)
        
        # Service name
        label = QLabel(name)
        label.setObjectName(f"{name.lower()}_label")
        label.setStyleSheet("color: #ecf0f1; font-size: 11px;")
        
        layout.addWidget(dot)
        layout.addWidget(label)
        
        # Store reference
        self.connection_indicators[name.lower()] = widget
        
        return widget
    
    def update_connection_status(self, service, is_connected, error_msg=None, status_detail=None):
        """Update the connection status for a service.
        
        Args:
            service (str): Service name ('arweave', 'nano', 'doge')
            is_connected (bool): Whether the service is connected
            error_msg (str, optional): Error message if connection failed
            status_detail (str, optional): Detailed status information
        """
        if service not in self.connection_indicators:
            return
            
        widget = self.connection_indicators[service]
        dot = widget.findChild(QLabel, f"{service}_dot")
        label = widget.findChild(QLabel, f"{service}_label")
        
        if not dot or not label:
            return
            
        # Update color and tooltip based on connection status
        if is_connected:
            color = "#2ecc71"  # Green
            status_text = f"Connected to {service.title()}"
            if status_detail:
                status_text += f"\n{status_detail}"
        else:
            color = "#e74c3c"  # Red
            status_text = f"Failed to connect to {service.title()}"
            if error_msg:
                status_text += f"\nError: {error_msg}"
                # Add error to message log
                self.add_message(f"{service.title()} connection failed: {error_msg}", "error", "failed")
        
        dot.setStyleSheet(f"font-size: 12px; color: {color};")
        widget.setToolTip(status_text)
        
        # Update main status indicator
        self.update_main_status_indicator()
        
        # Update timestamp
        self.update_timestamp()
    
    def update_main_status_indicator(self):
        """Update the main status indicator based on connection states."""
        if not hasattr(self, 'main_status_indicator') or not hasattr(self, 'connection_indicators'):
            return
            
        connected = 0
        total_services = len(self.connection_indicators)
        
        for service in self.connection_indicators.values():
            dot = service.findChild(QLabel, service.objectName().replace('_widget', '_dot'))
            if dot and "color: #2ecc71" in dot.styleSheet():
                connected += 1
        
        # Set color and tooltip based on connection state (as per JSON spec)
        if connected == total_services:
            color = "#2ecc71"  # Green - All connections healthy
            status_text = "All connections healthy"
        elif connected > 0:
            color = "#f39c12"  # Orange - Partial connection issues
            status_text = "Partial connection issues"
        else:
            color = "#e74c3c"  # Red - One or more services offline or malfunctioning
            status_text = "One or more services offline or malfunctioning"
            
        # Update main indicator with enhanced tooltip
        style = f"font-size: 16px; color: {color};"
        self.main_status_indicator.setStyleSheet(style)
        self.main_status_indicator.setCursor(Qt.PointingHandCursor)
        
        # Update tooltip to reflect current status
        tooltip = f"Click to expand error diagnostics\n\nStatus: {status_text}\nConnected: {connected}/{total_services} services"
        self.main_status_indicator.setToolTip(tooltip)
    
    def update_wallet_status(self, is_connected=True, error_msg=None):
        """Update the wallet status indicator.
        
        Args:
            is_connected (bool): Whether the wallet is connected
            error_msg (str, optional): Error message if connection failed
        """
        # Make sure we have the required UI elements
        if not hasattr(self, 'wallet_dot') or not hasattr(self, 'wallet_container'):
            # If we don't have the UI elements yet, try to set them up
            if hasattr(self, 'setup_connection_indicators'):
                self.setup_connection_indicators()
                # If still not available after setup, give up
                if not hasattr(self, 'wallet_dot') or not hasattr(self, 'wallet_container'):
                    return
            else:
                return
            
        try:
            if is_connected:
                self.wallet_dot.setStyleSheet("font-size: 16px; color: #2ecc71;")  # Green
                tooltip = "Wallet: Connected"
            else:
                self.wallet_dot.setStyleSheet("font-size: 16px; color: #e74c3c;")  # Red
                tooltip = "Wallet: Disconnected"
                if error_msg:
                    tooltip += f"\nError: {error_msg}"
            
            # Update the parent widget's tooltip
            if self.wallet_container is not None:
                self.wallet_container.setToolTip(tooltip)
                
        except Exception as e:
            print(f"Error updating wallet status: {e}")
    
    def update_activity_status(self, has_new_activity=False):
        """Update the activity feed status indicator.
        
        Args:
            has_new_activity (bool): Whether there is new activity to show
        """
        # Make sure we have the required UI elements
        if not hasattr(self, 'activity_dot') or not hasattr(self, 'activity_container'):
            # If we don't have the UI elements yet, try to set them up
            if hasattr(self, 'setup_connection_indicators'):
                self.setup_connection_indicators()
                # If still not available after setup, give up
                if not hasattr(self, 'activity_dot') or not hasattr(self, 'activity_container'):
                    return
            else:
                return
            
        try:
            if has_new_activity:
                self.activity_dot.setStyleSheet("font-size: 16px; color: #f39c12;")  # Orange
                tooltip = "New activity available! Click to view."
            else:
                self.activity_dot.setStyleSheet("font-size: 16px; color: #95a5a6;")  # Gray
                tooltip = "Activity feed"
            
            # Update the parent widget's tooltip
            if self.activity_container is not None:
                self.activity_container.setToolTip(tooltip)
                
        except Exception as e:
            print(f"Error updating activity status: {e}")
    
    def update_timestamp(self):
        """Update the last updated timestamp."""
        if hasattr(self, 'last_updated') and self.last_updated is not None:
            from datetime import datetime
            self.last_updated.setText(datetime.now().strftime("%H:%M:%S"))
    
    def create_activity_feed(self):
        """Create the activity feed widget."""
        # Create activity widget
        self.activity_widget = QWidget(self)
        self.activity_widget.setObjectName('activityFeed')
        self.activity_widget.setStyleSheet("""
            QWidget#activityFeed {
                background-color: rgba(44, 62, 80, 0.95);
                border: 1px solid #34495e;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        
        layout = QVBoxLayout(self.activity_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title = QLabel("Activity Feed")
        title.setStyleSheet("font-weight: bold; font-size: 14px; color: #ecf0f1; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Message log
        self.message_log = QTextBrowser()
        self.message_log.setMaximumHeight(150)
        self.message_log.setStyleSheet("""
            QTextBrowser {
                background-color: #ffffff;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Courier New', monospace;
                font-size: 11px;
            }
        """)
        layout.addWidget(self.message_log)
        
        # Initially hide the activity widget
        self.activity_widget.setVisible(False)
        
        # Position the activity widget
        self._position_activity_overlay()
        
        # Initialize message history
        self.message_history = []
        self.max_messages = 100  # Maximum number of messages to keep in history
        
        return self.activity_widget
    
    def _position_activity_overlay(self):
        """Position the activity overlay at the bottom of the window."""
        if not hasattr(self, 'activity_widget') or not self.activity_widget:
            return
            
        # Position at bottom of window
        parent_rect = self.rect()
        widget_rect = self.activity_widget.rect()
        
        x = parent_rect.left() + 20
        y = parent_rect.bottom() - widget_rect.height() - 20
        
        self.activity_widget.move(x, y)
        self.activity_widget.setFixedWidth(parent_rect.width() - 40)
    
    def toggle_activity_log_overlay(self):
        """Toggle the visibility of the activity log overlay."""
        if not hasattr(self, 'activity_widget') or not self.activity_widget:
            return
        is_visible = self.activity_widget.isVisible()
        self.activity_widget.setVisible(not is_visible)
        self.toggle_log_btn.setText("▼ Activity Log" if is_visible else "▲ Activity Log")
        if not is_visible:
            self._position_activity_overlay()
        self.adjustSize()
    
    def on_status_clicked(self, event):
        """Handle status indicator click."""
        # Toggle message log visibility when clicking on any status indicator
        self.toggle_activity_log_overlay()
        # Accept the event to prevent further propagation
        if event:
            event.accept()
    
    def add_message(self, message, level="info", data_quality="unknown"):
        """Add a message to the log with data quality indicator.
        
        Args:
            message (str): The message to add
            level (str): Message level ('info', 'warning', 'error', 'success')
            data_quality (str): Data quality status ('verified', 'pending', 'failed', 'unknown')
        """
        try:
            # Add timestamp
            from datetime import datetime
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.message_history.append((timestamp, message, level, data_quality))
            
            # Keep only the last max_messages
            if len(self.message_history) > self.max_messages:
                self.message_history = self.message_history[-self.max_messages:]
                
            # Update the message log if it exists
            if hasattr(self, 'message_log') and self.message_log is not None:
                self.update_message_log()
                
            # Show error messages in status bar if available
            if level == "error" and hasattr(self, 'status_text') and self.status_text is not None:
                error_msg = f"Error: {message[:50]}..." if len(message) > 50 else f"Error: {message}"
                self.status_text.setText(error_msg)
                # Clear the error message after 5 seconds
                QTimer.singleShot(5000, lambda: self.status_text.setText("") if hasattr(self, 'status_text') else None)
                
            # Print to console for debugging
            print(f"[{timestamp}] [{level.upper()}] {message}")
            
        except Exception as e:
            print(f"Error in add_message: {str(e)}")
    
    def update_message_log(self):
        """Update the message log with all messages and data quality indicators."""
        try:
            if not hasattr(self, 'message_log') or self.message_log is None:
                return
                
            log_text = ""
            for entry in self.message_history:
                # Handle both old format (3 items) and new format (4 items)
                if len(entry) == 3:
                    timestamp, msg, level = entry
                    data_quality = "unknown"
                elif len(entry) == 4:
                    timestamp, msg, level, data_quality = entry
                else:
                    continue
                    
                # Map data quality to emoji indicators
                quality_emoji = {
                    "verified": "✅",
                    "pending": "⏳",
                    "failed": "❌",
                    "unknown": "❓"
                }.get(data_quality, "❓")
                
                # Format message with appropriate color
                color = {
                    "error": "#e74c3c",
                    "warning": "#f39c12",
                    "success": "#27ae60",
                    "info": "#3498db"
                }.get(level, "#7f8c8d")
                
                log_text += f"<span style='color: {color};'>{quality_emoji} [{timestamp}] {msg}</span><br>"
                
            self.message_log.setHtml(log_text)
            
        except Exception as e:
            print(f"Error updating message log: {str(e)}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())