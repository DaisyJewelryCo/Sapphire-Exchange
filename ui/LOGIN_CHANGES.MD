Index: login_screen.py
===================================================================
--- login_screen.py	Before
+++ login_screen.py	After
@@ -1,21 +1,26 @@
 """
 Login Screen for Sapphire Exchange.
 Beautiful login screen with seed phrase input and new account creation.
+Integrates Plan 5 UI components with wallet generation for Solana, Nano, and Arweave.
 """
 
 import secrets
+import asyncio
 from PyQt5.QtWidgets import (
     QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
-    QTextEdit, QMessageBox, QFrame, QDialog
+    QTextEdit, QMessageBox, QFrame, QDialog, QProgressBar, QTabWidget
 )
-from PyQt5.QtCore import Qt
+from PyQt5.QtCore import Qt, pyqtSignal, QTimer
 from PyQt5.QtGui import QFont, QTextOption
 
 from services.application_service import app_service
 from utils.async_worker import AsyncWorker
 from ui.dialogs import SeedPhraseDialog
+from ui.dialogs.wallet_management import CreateWalletDialog, ImportWalletDialog
 from ui.logo_component import LogoComponent
+from ui.async_task_manager import BlockchainOperationManager, TaskResult
+from blockchain.unified_wallet_generator import UnifiedWalletGenerator
 
 
 class LoginScreen(QWidget):
     """Beautiful login screen with seed phrase input."""


Index: login_screen.py
===================================================================
--- login_screen.py	Before
+++ login_screen.py	After
@@ -24,13 +24,17 @@
 
 class LoginScreen(QWidget):
     """Beautiful login screen with seed phrase input."""
     
+    login_success = pyqtSignal(dict)
+    
     def __init__(self, parent=None):
         super().__init__(parent)
         self.parent_window = parent
         self.is_new_user = False
         self.current_user = None
+        self.wallet_generator = UnifiedWalletGenerator()
+        self.task_manager = BlockchainOperationManager()
         self.setup_ui()
     
     def setup_ui(self):
         """Create the beautiful login screen UI."""
Index: login_screen.py
===================================================================
--- login_screen.py	Before
+++ login_screen.py	After
@@ -121,24 +121,43 @@
                 border: 1px solid #4a6ee0;
             }
         """)
         
-        # New account link
-        new_account_link = QLabel(
-            "<a href='#' style='color: #2b7bba; text-decoration: none; font-weight: bold;'>Create a new account</a>"
-        )
-        new_account_link.setAlignment(Qt.AlignCenter)
-        new_account_link.setStyleSheet("""
-            QLabel {
+        # New account button - using Plan 5 dialog
+        new_account_btn = QPushButton("✨ Create New Wallet")
+        new_account_btn.setStyleSheet("""
+            QPushButton {
+                background: #06A77D;
+                color: white;
+                border: none;
                 padding: 10px;
-                margin: 5px 0;
+                border-radius: 4px;
+                font-weight: bold;
+                font-size: 13px;
             }
-            QLabel:hover {
-                background-color: #f8f9fa;
+            QPushButton:hover {
+                background: #04885d;
+            }
+        """)
+        new_account_btn.clicked.connect(self.open_create_wallet_dialog)
+        
+        # Import wallet button - using Plan 5 dialog
+        import_wallet_btn = QPushButton("📥 Import Wallet")
+        import_wallet_btn.setStyleSheet("""
+            QPushButton {
+                background: #F18F01;
+                color: white;
+                border: none;
+                padding: 10px;
                 border-radius: 4px;
+                font-weight: bold;
+                font-size: 13px;
             }
+            QPushButton:hover {
+                background: #d67f00;
+            }
         """)
-        new_account_link.linkActivated.connect(self.handle_new_account)
+        import_wallet_btn.clicked.connect(self.open_import_wallet_dialog)
         
         # Login button
         self.login_btn = QPushButton("Continue")
         self.login_btn.setStyleSheet("""
Index: login_screen.py
===================================================================
--- login_screen.py	Before
+++ login_screen.py	After
@@ -182,11 +182,22 @@
         # Add widgets to form
         form_layout.addWidget(self.form_title)
         form_layout.addWidget(seed_label)
         form_layout.addWidget(self.seed_input)
-        form_layout.addWidget(new_account_link)
+        
+        # Button group layout
+        button_group_layout = QHBoxLayout()
+        button_group_layout.addWidget(new_account_btn)
+        button_group_layout.addWidget(import_wallet_btn)
+        form_layout.addLayout(button_group_layout)
+        
         form_layout.addWidget(self.login_btn)
         
+        # Progress bar for wallet operations
+        self.progress_bar = QProgressBar()
+        self.progress_bar.setVisible(False)
+        form_layout.addWidget(self.progress_bar)
+        
         # Add to main layout
         layout.addStretch()
         layout.addWidget(title)
         layout.addWidget(subtitle)
Index: login_screen.py
===================================================================
--- login_screen.py	Before
+++ login_screen.py	After
@@ -234,49 +234,75 @@
         # Set the height to fit content
         new_height = max(min_height, min(ideal_height, max_height))
         self.seed_input.setFixedHeight(new_height)
     
-    def handle_new_account(self):
-        """Handle new account creation with seed phrase generation."""
+    def open_create_wallet_dialog(self):
+        """Open the Plan 5 create wallet dialog."""
+        dialog = CreateWalletDialog(parent=self)
+        dialog.wallet_created.connect(self.on_wallet_created)
+        dialog.exec_()
+    
+    def open_import_wallet_dialog(self):
+        """Open the Plan 5 import wallet dialog."""
+        dialog = ImportWalletDialog(parent=self)
+        dialog.wallet_imported.connect(self.on_wallet_imported)
+        dialog.exec_()
+    
+    def on_wallet_created(self, wallet_info):
+        """Handle wallet creation from Plan 5 dialog."""
         try:
-            # Generate a BIP-39 compatible seed phrase
-            wordlist = [
-                'abandon', 'ability', 'able', 'about', 'above', 'absent', 'absorb', 'abstract', 'absurd', 'abuse',
-                'access', 'accident', 'account', 'accuse', 'achieve', 'acid', 'acoustic', 'across', 'act', 'action',
-                'actor', 'actress', 'actual', 'adapt', 'add', 'addict', 'address', 'adjust', 'admit', 'adult',
-                'advance', 'advice', 'aerobic', 'affair', 'afford', 'afraid', 'again', 'agent', 'agree', 'ahead',
-                'aim', 'air', 'airport', 'aisle', 'alarm', 'album', 'alcohol', 'alert', 'alien', 'all',
-                'alley', 'allow', 'almost', 'alone', 'alpha', 'already', 'also', 'alter', 'always', 'amateur',
-                'amazing', 'among', 'amount', 'amused', 'analyst', 'anchor', 'ancient', 'anger', 'angle', 'angry',
-                'animal', 'ankle', 'announce', 'annual', 'another', 'answer', 'antenna', 'antique', 'anxiety', 'any',
-                'apart', 'apology', 'appear', 'apple', 'approve', 'april', 'arch', 'arctic', 'area', 'arena',
-                'argue', 'arm', 'armed', 'armor', 'army', 'around', 'arrange', 'arrest', 'arrive', 'arrow',
-                'art', 'artefact', 'artist', 'artwork', 'ask', 'aspect', 'assault', 'asset', 'assist', 'assume',
-                'asthma', 'athlete', 'atom', 'attack', 'attend', 'attitude', 'attract', 'auction', 'audit', 'august',
-                'aunt', 'author', 'auto', 'autumn', 'average', 'avocado', 'avoid', 'awake', 'aware', 'away',
-                'awesome', 'awful', 'awkward', 'axis', 'baby', 'bachelor', 'bacon', 'badge', 'bag', 'balance'
-            ]
+            # Set the mnemonic in the seed input field
+            self.seed_input.setPlainText(wallet_info.mnemonic)
+            self.adjust_seed_input_height()
+            self.is_new_user = True
             
-            # Generate 15 random words
-            seed_words = [secrets.choice(wordlist) for _ in range(15)]
-            seed_phrase = ' '.join(seed_words)
+            # Update form title
+            self.form_title.setText(f"Wallet Created: {wallet_info.name}")
+            self.form_title.setStyleSheet("color: #06A77D;")
             
-            # Show the beautiful seed phrase dialog
-            dialog = SeedPhraseDialog(seed_phrase, self.parent_window)
-            result = dialog.exec_()
+            # Show wallet info
+            wallet_summary = (
+                f"✓ Solana: {wallet_info.address_solana[:20] if wallet_info.address_solana else 'Not generated'}...\n"
+                f"✓ Nano: {wallet_info.address_nano[:20] if wallet_info.address_nano else 'Not generated'}...\n"
+                f"✓ Arweave: {wallet_info.address_arweave[:20] if wallet_info.address_arweave else 'Not generated'}..."
+            )
             
-            if result == QDialog.Accepted:
-                # Set the seed phrase in the input field
-                self.seed_input.setPlainText(seed_phrase)
-                # Adjust the text field height to fit the content properly
-                self.adjust_seed_input_height()
-                self.is_new_user = True
-                # Update form title to reflect new account creation
-                self.form_title.setText("New Account Created")
-                self.form_title.setStyleSheet("color: #28a745;")  # Green color for success
+            QMessageBox.information(
+                self,
+                "Wallet Created Successfully",
+                f"Your wallet '{wallet_info.name}' has been created.\n\n{wallet_summary}"
+            )
+        
+        except Exception as e:
+            QMessageBox.critical(self, "Error", f"Failed to create wallet: {str(e)}")
+    
+    def on_wallet_imported(self, wallet_info):
+        """Handle wallet import from Plan 5 dialog."""
+        try:
+            # Set the mnemonic in the seed input field
+            self.seed_input.setPlainText(wallet_info.mnemonic)
+            self.adjust_seed_input_height()
+            self.is_new_user = False
             
+            # Update form title
+            self.form_title.setText(f"Wallet Imported: {wallet_info.name}")
+            self.form_title.setStyleSheet("color: #2E86AB;")
+            
+            # Show wallet info
+            wallet_summary = (
+                f"✓ Solana: {wallet_info.address_solana[:20] if wallet_info.address_solana else 'Not available'}...\n"
+                f"✓ Nano: {wallet_info.address_nano[:20] if wallet_info.address_nano else 'Not available'}...\n"
+                f"✓ Arweave: {wallet_info.address_arweave[:20] if wallet_info.address_arweave else 'Not available'}..."
+            )
+            
+            QMessageBox.information(
+                self,
+                "Wallet Imported Successfully",
+                f"Your wallet '{wallet_info.name}' has been imported.\n\n{wallet_summary}"
+            )
+        
         except Exception as e:
-            QMessageBox.critical(self, "Error", f"Failed to generate seed phrase: {str(e)}")
+            QMessageBox.critical(self, "Error", f"Failed to import wallet: {str(e)}")
     
     def handle_login(self):
         """Handle the login process with the provided seed phrase."""
         try:
Index: login_screen.py
===================================================================
--- login_screen.py	Before
+++ login_screen.py	After
@@ -341,21 +341,46 @@
             self.login_btn.setText("Continue")
             QMessageBox.critical(self, "Login Error", f"Failed to login: {str(e)}")
     
     async def login_async(self, seed_phrase):
-        """Async login process."""
+        """Async login process with wallet generation for Solana, Nano, and Arweave."""
         try:
+            # First, validate and generate wallets from the mnemonic
+            is_valid = await self.wallet_generator.validate_mnemonic(seed_phrase)
+            if not is_valid:
+                return False, "Invalid mnemonic phrase", None
+            
+            # Generate wallets for all supported blockchains (Solana, Nano, Arweave)
+            success, wallet_data = await self.wallet_generator.generate_from_mnemonic(
+                seed_phrase,
+                passphrase=""
+            )
+            
+            if not success:
+                return False, "Failed to generate wallets from mnemonic", None
+            
+            # Prepare user data with wallet information
+            user_data = {
+                'mnemonic': seed_phrase,
+                'wallets': wallet_data,
+                'created_at': datetime.now().isoformat() if self.is_new_user else None,
+            }
+            
             if self.is_new_user:
-                # Register new user with seed phrase
+                # Register new user with generated wallets
                 success, message, user = await app_service.register_user_with_seed(seed_phrase)
             else:
                 # Login existing user with seed phrase
                 success, message, user = await app_service.login_user_with_seed(seed_phrase)
             
+            if success and user:
+                # Update user data with wallet information
+                user.update(user_data)
+            
             return success, message, user
             
         except Exception as e:
-            return False, str(e), None
+            return False, f"Login error: {str(e)}", None
     
     def on_login_complete(self, result):
         """Handle completion of the login process."""
         try:
Index: login_screen.py
===================================================================
--- login_screen.py	Before
+++ login_screen.py	After
@@ -389,20 +389,41 @@
             
             # Re-enable login button
             self.login_btn.setEnabled(True)
             self.login_btn.setText("Continue")
+            self.progress_bar.setVisible(False)
             
             if success:
                 self.current_user = user
+                
+                # Extract wallet information for display
+                wallets = user.get('wallets', {}) if isinstance(user, dict) else {}
+                wallet_summary = (
+                    f"✓ Solana: {wallets.get('solana', {}).get('address', 'Not available')[:30]}...\n"
+                    f"✓ Nano: {wallets.get('nano', {}).get('address', 'Not available')[:30]}...\n"
+                    f"✓ Arweave: {wallets.get('arweave', {}).get('address', 'Not available')[:30]}..."
+                )
+                
+                # Show success message
+                QMessageBox.information(
+                    self,
+                    "Login Successful",
+                    f"Welcome! Your wallets have been synchronized:\n\n{wallet_summary}"
+                )
+                
+                # Emit login success signal
+                self.login_success.emit(user if isinstance(user, dict) else {'user': user})
+                
                 # Notify parent window that login was successful
                 if self.parent_window:
                     self.parent_window.on_login_success(user)
             else:
-                QMessageBox.warning(self, "Login Failed", message)
+                QMessageBox.warning(self, "Login Failed", message or "Unknown error occurred")
                 
         except Exception as e:
             self.login_btn.setEnabled(True)
             self.login_btn.setText("Continue")
+            self.progress_bar.setVisible(False)
             QMessageBox.critical(self, "Login Error", f"Login process failed: {str(e)}")
     
     def on_login_error(self, error_message):
         """Handle login errors."""
