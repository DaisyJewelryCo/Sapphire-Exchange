"""
Sapphire Exchange - Main Application Window

This module contains the main PyQt5-based UI for the Sapphire Exchange desktop application.
"""
import sys
import asyncio
import qrcode
from datetime import datetime, timedelta, timezone
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QLabel, QPushButton, QLineEdit, QTextEdit, QTabWidget, QListWidget,
                            QListWidgetItem, QMessageBox, QFileDialog, QStackedWidget)
from PyQt5.QtGui import QPixmap, QImage, QFont, QIcon
from PyQt5.QtCore import Qt, QSize, QTimer, QThread, pyqtSignal

from decentralized_client import DecentralizedClient
from models import Item, Auction, User

class AsyncWorker(QThread):
    """Worker thread for running async functions."""
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    
    def __init__(self, coro, parent=None):
        super().__init__(parent)
        self.coro = coro
        
    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.coro)
            loop.close()
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

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
        
        print("  Initializing UI...")
        self.init_ui()
        
        # Connect the signal to the slot
        print("  Connecting signals...")
        self.show_seed_message_box.connect(self._show_seed_message_box)
        print("  MainWindow initialization complete")
        
    def _show_seed_message_box(self):
        """Show the seed message box on the main thread."""
        if hasattr(self, '_pending_seed') and self._pending_seed:
            QMessageBox.information(
                self, 
                "New Wallet Generated", 
                f"A new wallet has been generated for you.\n\n"
                f"IMPORTANT: Please save this seed phrase in a secure location:\n\n{self._pending_seed}\n\n"
                "You will need this seed phrase to recover your wallet."
            )
            # Clear the pending seed after showing the message
            self._pending_seed = None
        
    def init_ui(self):
        print("  Initializing UI components...")
        self.setWindowTitle("Sapphire Exchange")
        self.setGeometry(100, 100, 1000, 700)
        
        # Main widget and layout
        print("  Creating main widget and layout...")
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        
        # Sidebar
        print("  Creating sidebar...")
        sidebar = self.create_sidebar()
        layout.addWidget(sidebar, stretch=1)
        
        # Main content area
        print("  Creating content stack...")
        self.content_stack = QStackedWidget()
        
        # Login/Signup Page
        print("  Creating login page...")
        self.login_page = self.create_login_page()
        self.content_stack.addWidget(self.login_page)
        
        # Marketplace Page
        print("  Creating marketplace page...")
        self.marketplace_page = self.create_marketplace_page()
        self.content_stack.addWidget(self.marketplace_page)
        
        # Create Item Page
        print("  Creating item creation page...")
        self.create_item_page = self.create_item_creation_page()
        self.content_stack.addWidget(self.create_item_page)
        
        # My Items Page
        print("  Creating my items page...")
        self.my_items_page = self.create_my_items_page()
        self.content_stack.addWidget(self.my_items_page)
        
        layout.addWidget(self.content_stack, stretch=4)
        
        # Show login page by default
        print("  Setting initial page to login...")
        self.content_stack.setCurrentIndex(0)
        print("  UI initialization complete")
        
    def create_sidebar(self):
        sidebar = QWidget()
        sidebar.setStyleSheet("background-color: #f5f5f5; padding: 20px;")
        layout = QVBoxLayout(sidebar)
        
        # App title
        title = QLabel("Sapphire Exchange")
        title.setFont(QFont('Arial', 16, QFont.Bold))
        
        # User info (initially hidden)
        self.user_info = QLabel()
        self.user_info.setVisible(False)
        
        # Navigation buttons
        self.marketplace_btn = QPushButton("Marketplace")
        self.marketplace_btn.clicked.connect(lambda: self.show_page(1))
        
        self.create_item_btn = QPushButton("Sell Item")
        self.create_item_btn.clicked.connect(lambda: self.show_page(2))
        self.create_item_btn.setVisible(False)
        
        self.my_items_btn = QPushButton("My Items")
        self.my_items_btn.clicked.connect(lambda: self.show_page(3))
        self.my_items_btn.setVisible(False)
        
        # Add widgets to sidebar
        layout.addWidget(title)
        layout.addWidget(self.user_info)
        layout.addWidget(self.marketplace_btn)
        layout.addWidget(self.create_item_btn)
        layout.addWidget(self.my_items_btn)
        layout.addStretch()
        
        # Logout button (initially hidden)
        self.logout_btn = QPushButton("Logout")
        self.logout_btn.clicked.connect(self.logout)
        self.logout_btn.setVisible(False)
        layout.addWidget(self.logout_btn)
        
        return sidebar
    
    def create_login_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)
        
        title = QLabel("Welcome to Sapphire Exchange")
        title.setFont(QFont('Arial', 18, QFont.Bold))
        
        # Login form
        form_layout = QVBoxLayout()
        form_layout.setSpacing(15)
        
        # Seed phrase input
        self.seed_input = QTextEdit()
        self.seed_input.setPlaceholderText("Enter your seed phrase (or leave empty to create new account)")
        self.seed_input.setMaximumHeight(100)
        
        # New user fields (initially hidden)
        self.new_user_widget = QWidget()
        new_user_layout = QVBoxLayout(self.new_user_widget)
        new_user_layout.setSpacing(10)
        
        # Username input
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Choose a username")
        
        # First name input
        self.first_name_input = QLineEdit()
        self.first_name_input.setPlaceholderText("First name")
        
        # Last name input
        self.last_name_input = QLineEdit()
        self.last_name_input.setPlaceholderText("Last name")
        
        # Add new user fields to layout
        new_user_layout.addWidget(QLabel("New Account Details:"))
        new_user_layout.addWidget(QLabel("Username:"))
        new_user_layout.addWidget(self.username_input)
        new_user_layout.addWidget(QLabel("First Name:"))
        new_user_layout.addWidget(self.first_name_input)
        new_user_layout.addWidget(QLabel("Last Name:"))
        new_user_layout.addWidget(self.last_name_input)
        
        # Initially hide new user fields
        self.new_user_widget.setVisible(False)
        
        # Toggle button for new/existing user
        self.toggle_login_btn = QPushButton("Create New Account")
        self.toggle_login_btn.setCheckable(True)
        self.toggle_login_btn.clicked.connect(self.toggle_login_mode)
        
        # Login button
        self.login_btn = QPushButton("Login")
        self.login_btn.clicked.connect(self.handle_login)
        
        # Add widgets to layout
        form_layout.addWidget(QLabel("Seed Phrase:"))
        form_layout.addWidget(self.seed_input)
        form_layout.addWidget(self.toggle_login_btn)
        form_layout.addWidget(self.new_user_widget)
        form_layout.addWidget(self.login_btn)
        
        # Add form to main layout
        layout.addWidget(title)
        layout.addLayout(form_layout)
        
        # Store the current login mode (False = login, True = create account)
        self.is_new_user = False
        
        return page
    
    def toggle_login_mode(self):
        """Toggle between login and create account modes."""
        self.is_new_user = not self.is_new_user
        
        if self.is_new_user:
            self.toggle_login_btn.setText("Use Existing Account")
            self.login_btn.setText("Create Account")
            self.new_user_widget.setVisible(True)
            self.seed_input.setPlaceholderText("Leave empty to generate a new wallet")
        else:
            self.toggle_login_btn.setText("Create New Account")
            self.login_btn.setText("Login")
            self.new_user_widget.setVisible(False)
            self.seed_input.setPlaceholderText("Enter your seed phrase")
    
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
        seed_phrase = self.seed_input.toPlainText().strip()
        
        # Validate inputs for new users
        if self.is_new_user and not self.validate_new_user_inputs():
            return
        
        # Disable login button to prevent multiple clicks
        self.login_btn.setEnabled(False)
        
        # Show status message
        status_msg = "Creating new account..." if self.is_new_user and not seed_phrase else "Logging in..."
        self.statusBar().showMessage(status_msg)
        
        # Force UI update before starting the login process
        QApplication.processEvents()
        
        # Prepare user data if this is a new user
        user_data = None
        if self.is_new_user and (not seed_phrase or self.username_input.text().strip()):
            user_data = {
                'username': self.username_input.text().strip(),
                'first_name': self.first_name_input.text().strip(),
                'last_name': self.last_name_input.text().strip()
            }
        
        # Run login in a separate thread
        def on_login_complete(user_data):
            self.statusBar().clearMessage()
            self.login_btn.setEnabled(True)
            
            if user_data:
                self.current_user = user_data
                display_name = f"{user_data.first_name} {user_data.last_name}".strip() or user_data.username
                self.user_info.setText(f"Logged in as:\n{display_name}")
                self.user_info.setVisible(True)
                self.create_item_btn.setVisible(True)
                self.my_items_btn.setVisible(True)
                self.logout_btn.setVisible(True)
                self.seed_input.setVisible(False)
                self.login_btn.setVisible(False)
                self.toggle_login_btn.setVisible(False)
                self.new_user_widget.setVisible(False)
                
                # Show seed phrase warning for new accounts
                if not seed_phrase:
                    seed = self.client.get_seed_phrase()
                    if seed:
                        QMessageBox.information(
                            self,
                            "New Account Created",
                            f"Your new account has been created!\n\n"
                            f"IMPORTANT: Please save your seed phrase in a secure location.\n"
                            f"You will need this to recover your account.\n\n"
                            f"Seed Phrase:\n{seed}"
                        )
                
                self.show_page(1)  # Show marketplace after login
            else:
                QMessageBox.warning(self, "Login Failed", "Invalid seed phrase or wallet data.")
        
        def on_error(error_msg):
            self.statusBar().clearMessage()
            self.login_btn.setEnabled(True)
            QMessageBox.critical(self, "Error", f"Login failed: {error_msg}")
        
        # Start login process in a worker thread
        self.worker = AsyncWorker(self.login_async(seed_phrase, user_data))
        self.worker.finished.connect(on_login_complete)
        self.worker.error.connect(on_error)
        self.worker.start()
    
    def create_marketplace_page(self):
        print("  Creating marketplace page...")
        page = QWidget()
        layout = QVBoxLayout(page)
        
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
        print("Creating My Items page...")
        page = QWidget()
        layout = QVBoxLayout(page)
        
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
        print(f"  content_stack has {self.content_stack.count()} pages")
        print(f"  Current attributes: {[attr for attr in dir(self) if not attr.startswith('__')]}")
        
        # Make sure the page exists in the stack
        if index >= 0 and index < self.content_stack.count():
            print(f"  Setting current index to {index}")
            self.content_stack.setCurrentIndex(index)
            
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
            print(f"  WARNING: Page index {index} out of range (0-{self.content_stack.count()-1})")
    
    async def login_async(self, seed_phrase, user_data=None):
        try:
            print(f"Starting login with seed_phrase: {'[EMPTY]' if not seed_phrase else '[PROVIDED]'}")
            
            # Initialize client
            self.client = DecentralizedClient()
            
            # If seed_phrase is empty or None, generate a new wallet
            if not seed_phrase or seed_phrase.strip() == "":
                print("No seed phrase provided, generating new wallet...")
                
                # Extract user data if provided
                username = user_data.get('username') if user_data else None
                first_name = user_data.get('first_name', '') if user_data else ''
                last_name = user_data.get('last_name', '') if user_data else ''
                
                # Initialize user with provided data or generate defaults
                user_data = await self.client.initialize_user(
                    seed_phrase=None,  # Will generate a new wallet
                    username=username,
                    first_name=first_name,
                    last_name=last_name
                )
                
                # Get the generated seed from the wallet
                seed = self.client.user_wallet.private_key.to_ascii(encoding='hex').decode('utf-8')
                print(f"Generated new wallet with address: {self.client.user_wallet.address}")
                
                # Store the seed to show in the UI thread
                self._pending_seed = seed
                
                # Schedule showing the message box on the main thread
                self.show_seed_message_box.emit()
                
                # Wait a moment to ensure the message box is shown
                await asyncio.sleep(0.1)
                
            else:
                # Use the provided seed phrase
                print(f"Using provided seed phrase to initialize wallet...")
                user_data = await self.client.initialize_user(
                    seed_phrase=seed_phrase.strip(),
                    username="temporary_username"  # This will be replaced by the actual user data from _load_user_data
                )
                print(f"Logged in with existing wallet: {self.client.user_wallet.address}")
                print(f"User data loaded: {user_data}")
                
                # Store the current user in the MainWindow instance
                self.current_user = user_data
            
            print("Login successful, returning user data")
            return user_data
            
        except Exception as e:
            print(f"Error during login: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
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
        from mock_servers import arweave_db
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
        # Show bid dialog
        from PyQt5.QtWidgets import QInputDialog
        
        current_bid = item_data.get('current_bid', item_data.get('starting_price', 0))
        min_bid = max(current_bid * 1.1, current_bid + 0.1)  # 10% minimum increase or 0.1 NANO
        
        bid_amount, ok = QInputDialog.getDouble(
            self,
            f"Bid on {item_data.get('name', 'Item')}",
            f"Enter your bid (minimum {min_bid:.2f} NANO):",
            value=min_bid,
            minValue=min_bid,
            decimals=6
        )
        
        if ok:
            self.place_bid(item_data['id'], bid_amount)
    
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
        self.current_user = None
        self.client = None
        self.user_info.setVisible(False)
        self.create_item_btn.setVisible(False)
        self.my_items_btn.setVisible(False)
        self.logout_btn.setVisible(False)
        self.content_stack.setCurrentIndex(0)  # Show login page

def main():
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Start event loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
