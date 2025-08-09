"""
Login Screen for Sapphire Exchange.
Beautiful login screen with seed phrase input and new account creation.
"""

import secrets
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QMessageBox, QFrame, QDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QTextOption

from services.application_service import app_service
from utils.async_worker import AsyncWorker
from ui.dialogs import SeedPhraseDialog
from ui.logo_component import LogoComponent


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
        layout.setContentsMargins(20, 20, 20, 20)  # Reduced margins to prevent cutoff
        layout.setSpacing(20)  # Reduced spacing to fit better
        
        # Add logo at the top left
        logo_container = QWidget()
        logo_layout = QHBoxLayout(logo_container)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        
        self.logo = LogoComponent(size="large", clickable=False)
        logo_layout.addWidget(self.logo)
        logo_layout.addStretch()  # Push logo to the left
        
        layout.addWidget(logo_container)
        
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
        # Make card more responsive to prevent layout issues
        card.setMinimumWidth(350)
        card.setMaximumWidth(600)
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 20px;
            }
        """)
        
        # Card layout
        form_layout = QVBoxLayout(card)
        form_layout.setSpacing(15)  # Reduced spacing
        form_layout.setContentsMargins(15, 15, 15, 15)  # Reduced margins
        
        # Form title
        self.form_title = QLabel("Welcome Back")
        self.form_title.setFont(QFont('Arial', 16, QFont.Bold))
        self.form_title.setAlignment(Qt.AlignCenter)
        
        # Seed phrase input
        seed_label = QLabel("Your Seed Phrase:")
        seed_label.setFont(QFont('Arial', 12))
        
        self.seed_input = QTextEdit()
        self.seed_input.setPlaceholderText("Enter your seed phrase (12-24 words)")
        # Set appropriate height to accommodate seed phrases without scroll bars
        self.seed_input.setMinimumHeight(100)
        self.seed_input.setMaximumHeight(150)  # Increased to accommodate longer seed phrases
        # Disable scroll bars to prevent them from appearing
        self.seed_input.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.seed_input.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # Enable word wrapping to fit text properly
        self.seed_input.setWordWrapMode(QTextOption.WordWrap)
        self.seed_input.setStyleSheet("""
            QTextEdit {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 12px;
                font-size: 14px;
                min-height: 100px;
                max-height: 150px;
                font-family: 'Courier New', monospace;
                line-height: 1.4;
            }
            QTextEdit:focus {
                border: 1px solid #4a6ee0;
            }
        """)
        
        # New account link
        new_account_link = QLabel(
            "<a href='#' style='color: #2b7bba; text-decoration: none; font-weight: bold;'>Create a new account</a>"
        )
        new_account_link.setAlignment(Qt.AlignCenter)
        new_account_link.setStyleSheet("""
            QLabel {
                padding: 10px;
                margin: 5px 0;
            }
            QLabel:hover {
                background-color: #f8f9fa;
                border-radius: 4px;
            }
        """)
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
        form_layout.addWidget(self.form_title)
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
    
    def reset_form(self):
        """Reset the form to its initial state."""
        self.form_title.setText("Welcome Back")
        self.form_title.setStyleSheet("")  # Reset to default styling
        self.seed_input.clear()
        # Reset height to minimum when clearing
        self.seed_input.setFixedHeight(100)
        self.is_new_user = False
        self.login_btn.setEnabled(True)
        self.login_btn.setText("Continue")
    
    def adjust_seed_input_height(self):
        """Adjust the seed input field height to fit content without scroll bars."""
        # Get the document height
        doc = self.seed_input.document()
        doc_height = doc.size().height()
        
        # Add some padding for better appearance
        padding = 24  # Account for padding in stylesheet
        ideal_height = int(doc_height + padding)
        
        # Ensure height is within reasonable bounds
        min_height = 100
        max_height = 150
        
        # Set the height to fit content
        new_height = max(min_height, min(ideal_height, max_height))
        self.seed_input.setFixedHeight(new_height)
    
    def handle_new_account(self):
        """Handle new account creation with seed phrase generation."""
        try:
            # Generate a BIP-39 compatible seed phrase
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
            dialog = SeedPhraseDialog(seed_phrase, self.parent_window)
            result = dialog.exec_()
            
            if result == QDialog.Accepted:
                # Set the seed phrase in the input field
                self.seed_input.setPlainText(seed_phrase)
                # Adjust the text field height to fit the content properly
                self.adjust_seed_input_height()
                self.is_new_user = True
                # Update form title to reflect new account creation
                self.form_title.setText("New Account Created")
                self.form_title.setStyleSheet("color: #28a745;")  # Green color for success
            
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