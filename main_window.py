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
        super().__init__()
        self.client = None
        self.current_user = None
        self.items = []
        self._pending_seed = None
        self.init_ui()
        
        # Connect the signal to the slot
        self.show_seed_message_box.connect(self._show_seed_message_box)
        
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
        self.setWindowTitle("Sapphire Exchange")
        self.setGeometry(100, 100, 1000, 700)
        
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        
        # Sidebar
        sidebar = self.create_sidebar()
        layout.addWidget(sidebar, stretch=1)
        
        # Main content area
        self.content_stack = QStackedWidget()
        
        # Login/Signup Page
        self.login_page = self.create_login_page()
        self.content_stack.addWidget(self.login_page)
        
        # Marketplace Page
        self.marketplace_page = self.create_marketplace_page()
        self.content_stack.addWidget(self.marketplace_page)
        
        # Create Item Page
        self.create_item_page = self.create_item_creation_page()
        self.content_stack.addWidget(self.create_item_page)
        
        # My Items Page
        self.my_items_page = self.create_my_items_page()
        self.content_stack.addWidget(self.my_items_page)
        
        layout.addWidget(self.content_stack, stretch=4)
        
        # Show login page by default
        self.content_stack.setCurrentIndex(0)
        
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
        self.seed_input.setPlaceholderText("Enter your seed phrase (or leave empty to generate new)")
        self.seed_input.setMaximumHeight(100)
        
        # Login button
        self.login_btn = QPushButton("Login / Create Account")
        self.login_btn.clicked.connect(self.handle_login)
        
        # Add widgets to layout
        form_layout.addWidget(QLabel("Seed Phrase:"))
        form_layout.addWidget(self.seed_input)
        form_layout.addWidget(self.login_btn)
        
        # Add form to main layout
        layout.addWidget(title)
        layout.addLayout(form_layout)
        
        return page
    
    def handle_login(self):
        seed_phrase = self.seed_input.toPlainText().strip()
        
        # Disable login button to prevent multiple clicks
        self.login_btn.setEnabled(False)
        
        # Show status message
        self.statusBar().showMessage("Logging in...")
        
        # Force UI update before starting the login process
        QApplication.processEvents()
        
        # Run login in a separate thread
        def on_login_complete(user_data):
            self.statusBar().clearMessage()
            self.login_btn.setEnabled(True)
            
            if user_data:
                self.current_user = user_data
                self.user_info.setText(f"Logged in as:\n{user_data.public_key[:12]}...")
                self.user_info.setVisible(True)
                self.create_item_btn.setVisible(True)
                self.my_items_btn.setVisible(True)
                self.logout_btn.setVisible(True)
                self.seed_input.setVisible(False)
                self.login_btn.setVisible(False)
                self.seed_label = QLabel("Your Seed Phrase (keep it safe!)")
                self.seed_label.setVisible(True)
                self.content_stack.parentWidget().layout().itemAt(0).widget().layout().insertWidget(1, self.seed_label)
                self.show_page(1)  # Show marketplace after login
            else:
                QMessageBox.warning(self, "Login Failed", "Invalid seed phrase or wallet data.")
        
        def on_error(error_msg):
            self.statusBar().clearMessage()
            self.login_btn.setEnabled(True)
            QMessageBox.critical(self, "Error", f"Login failed: {error_msg}")
        
        # Start login process in a worker thread
        self.worker = AsyncWorker(self.login_async(seed_phrase))
        self.worker.finished.connect(on_login_complete)
        self.worker.error.connect(on_error)
        self.worker.start()
    
    def create_marketplace_page(self):
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
        
        # Load initial items
        self.load_marketplace_items()
        
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
        page = QWidget()
        layout = QVBoxLayout(page)
        
        title = QLabel("My Items")
        title.setFont(QFont('Arial', 16, QFont.Bold))
        
        # Items list
        self.my_items_list = QListWidget()
        self.my_items_list.setViewMode(QListWidget.IconMode)
        self.my_items_list.setIconSize(QSize(150, 150))
        self.my_items_list.setResizeMode(QListWidget.Adjust)
        
        # Add widgets to layout
        layout.addWidget(title)
        layout.addWidget(self.my_items_list)
        
        return page
    
    def browse_image(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp)")
        if file_name:
            self.image_path.setText(file_name)
    
    def show_page(self, index):
        self.content_stack.setCurrentIndex(index)
        if index == 1:  # Marketplace
            self.load_marketplace_items()
        elif index == 3:  # My Items
            self.load_my_items()
    
    async def login_async(self, seed_phrase):
        try:
            print(f"Starting login with seed_phrase: {'[EMPTY]' if not seed_phrase else '[PROVIDED]'}")
            
            # Initialize client
            self.client = DecentralizedClient()
            
            # If seed_phrase is empty or None, generate a new wallet
            if not seed_phrase or seed_phrase.strip() == "":
                print("No seed phrase provided, generating new wallet...")
                # Pass None to generate a new wallet
                user_data = await self.client.initialize_user(None)
                
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
                user_data = await self.client.initialize_user(seed_phrase.strip())
                print(f"Logged in with existing wallet: {self.client.user_wallet.address}")
            
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
    
    async def load_items_async(self):
        # In a real implementation, this would query Arweave for items
        # For now, return mock data
        return [
            {
                'id': 'mock1',
                'name': 'Rare Digital Art',
                'description': 'A unique digital artwork',
                'starting_price': 1.0,
                'current_bid': 1.5,
                'owner': 'nano_owner123...',
                'auction_end_time': '2023-12-31T23:59:59Z'
            },
            {
                'id': 'mock2',
                'name': 'Crypto Collectible',
                'description': 'Limited edition collectible',
                'starting_price': 0.5,
                'current_bid': 0.0,
                'owner': 'nano_owner456...',
                'auction_end_time': '2023-12-25T12:00:00Z'
            }
        ]
    
    def load_my_items(self):
        # Clear existing items
        self.my_items_list.clear()
        
        if not self.current_user:
            self.my_items_list.addItem("Not logged in")
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
    
    async def load_user_items_async(self):
        # In a real implementation, this would query Arweave for the user's items
        # For now, return empty list
        return []
    
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
        
        # Show loading indicator
        loading_msg = QMessageBox(self)
        loading_msg.setWindowTitle("Creating Item")
        loading_msg.setText("Creating your item...")
        loading_msg.setStandardButtons(QMessageBox.NoButton)
        loading_msg.show()
        
        def on_item_created(result):
            loading_msg.close()
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
            loading_msg.close()
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
            item = await self.client.create_item(
                name=name,
                description=description,
                starting_price=starting_price,
                duration_hours=duration_hours,
                image_url=image_path or ""
            )
            
            # Convert item to dict for UI updates
            item_dict = item.to_dict()
            
            # Add to local items list for UI updates
            self.items.append(item_dict)
            
            # Return both the item and its transaction ID
            return item, item_dict.get('transaction_id', 'mock_tx_' + ''.join(random.choices('0123456789abcdef', k=16)))
            
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
