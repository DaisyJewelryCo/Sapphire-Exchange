"""
Login Screen for Sapphire Exchange.
Beautiful login screen with seed phrase input and new account creation.
"""

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
from blockchain.unified_wallet_generator import UnifiedWalletGenerator


class LoginScreen(QWidget):
    """Beautiful login screen with seed phrase input."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.is_new_user = False
        self.current_user = None
        self.wallet_generator = UnifiedWalletGenerator()
        self.setup_ui()
    
    def setup_ui(self):
        """Create the beautiful login screen UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
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
        """Handle new account creation with wallet generation."""
        try:
            # Generate a BIP-39 mnemonic using UnifiedWalletGenerator
            mnemonic = self.wallet_generator.generate_mnemonic()
            
            # Show the beautiful seed phrase dialog
            dialog = SeedPhraseDialog(mnemonic, self.parent_window)
            result = dialog.exec_()
            
            if result == QDialog.Accepted:
                # Set the seed phrase in the input field
                self.seed_input.setPlainText(mnemonic)
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
        """Async login process with wallet generation and account recovery."""
        try:
            # Validate mnemonic
            is_valid, message = self.wallet_generator.validate_mnemonic(seed_phrase)
            if not is_valid:
                return False, f"Invalid mnemonic phrase: {message}", None
            
            # Check if this is a new account creation or existing account recovery
            if self.is_new_user:
                # New account flow: create wallets and register user
                print(f"\n{'='*60}")
                print("[LOGIN] Creating new account with generated seed phrase...")
                print(f"[LOGIN] Mnemonic word count: {len(seed_phrase.split())}")
                
                # Generate wallets for all supported blockchains
                success, wallet_data = self.wallet_generator.generate_from_mnemonic(
                    seed_phrase,
                    passphrase=""
                )
                
                if success and wallet_data and 'nano' in wallet_data:
                    nano_addr = wallet_data['nano'].get('address')
                    print(f"[LOGIN] Generated Nano address during account creation: {nano_addr}")
                    print(f"{'='*60}\n")
                
                if not success:
                    return False, "Failed to generate wallets from mnemonic", None
                
                # Register new user with seed phrase
                success, message, user = await app_service.register_user_with_seed(seed_phrase, wallet_data)
                
                # Attach wallet data and mnemonic to user
                if success and user:
                    if isinstance(user, dict):
                        user['wallets'] = wallet_data
                        user['mnemonic'] = seed_phrase
                
                return success, message, user
            
            else:
                # Existing account recovery: try to recover from backup
                print("[LOGIN] Attempting to recover existing account from backup...")
                recovery_result = await app_service.recover_user_from_mnemonic(seed_phrase)
                
                if recovery_result is not None:
                    # Account recovered from backup
                    print("[LOGIN] ✓ Account recovered from backup!")
                    user, session_token, wallet_data = recovery_result
                    app_service.current_user = user
                    app_service.current_session = session_token
                    return True, f"Account recovered: {user.username}", {
                        'user': user,
                        'wallets': wallet_data,
                        'mnemonic': seed_phrase,
                        'session_token': session_token
                    }
                
                # No backup found - fail login
                # User must use "Create a new account" button to create new accounts
                print("[LOGIN] ❌ No backup found for this seed phrase - login failed")
                return False, "No account found for this seed phrase. Use 'Create a new account' to set up a new account.", None
            
        except Exception as e:
            return False, f"Login error: {str(e)}", None
    
    def on_login_complete(self, result):
        """Handle completion of the login process."""
        try:
            success, message, user_or_data = result
            
            # Re-enable login button
            self.login_btn.setEnabled(True)
            self.login_btn.setText("Continue")
            
            if success:
                # For recovery flow, user_or_data is a dict with 'user', 'wallets', etc.
                # For new account flow, user_or_data is a User object
                if isinstance(user_or_data, dict):
                    self.current_user = user_or_data.get('user')
                    wallets = user_or_data.get('wallets', {})
                else:
                    self.current_user = user_or_data
                    wallets = {}
                
                # Show wallet information if available
                if wallets and isinstance(wallets, dict):
                    wallet_summary = "Your wallets have been synchronized:\n\n"
                    
                    wallet_count = 0
                    
                    if 'solana' in wallets and isinstance(wallets['solana'], dict):
                        solana_addr = wallets['solana'].get('address', 'N/A')
                        if solana_addr and solana_addr != 'N/A':
                            wallet_summary += f"✓ Solana (USDC): {solana_addr[:30]}...\n"
                            wallet_count += 1
                    
                    if 'nano' in wallets and isinstance(wallets['nano'], dict):
                        nano_addr = wallets['nano'].get('address', 'N/A')
                        if nano_addr and nano_addr != 'N/A':
                            wallet_summary += f"✓ Nano: {nano_addr[:30]}...\n"
                            wallet_count += 1
                    
                    if 'arweave' in wallets and isinstance(wallets['arweave'], dict):
                        arweave_addr = wallets['arweave'].get('address', 'N/A')
                        if arweave_addr and arweave_addr != 'N/A':
                            wallet_summary += f"✓ Arweave: {arweave_addr[:30]}...\n"
                            wallet_count += 1
                    
                    if wallet_count > 0:
                        QMessageBox.information(self, "Login Successful", wallet_summary)
                
                # Reset form for next login attempt
                self.reset_form()
                
                # Notify parent window that login was successful
                if self.parent_window:
                    self.parent_window.on_login_success(self.current_user)
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
    
    def set_app_ready(self, ready):
        """Set the app ready state.
        
        Args:
            ready (bool): Whether the app is ready to use.
        """
        # This method is called by the main window when the app initialization is complete
        # Update UI state based on app readiness
        self.login_btn.setEnabled(ready)
        if not ready:
            self.login_btn.setText("Initializing...")
        else:
            self.login_btn.setText("Continue")
    
