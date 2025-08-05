"""
Enhanced Auction Interface for Sapphire Exchange.
Supports multi-currency bidding, real-time updates, and advanced auction features.
"""
import asyncio
from datetime import datetime, timezone, timedelta
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QScrollArea, QFrame, QGroupBox, QLineEdit, QTextEdit,
                             QComboBox, QSpinBox, QDateTimeEdit, QCheckBox, QProgressBar,
                             QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
                             QDialog, QDialogButtonBox, QFormLayout, QTabWidget,
                             QListWidget, QListWidgetItem, QSplitter, QTextBrowser)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QDateTime, QThread
from PyQt5.QtGui import QFont, QPixmap, QIcon, QColor, QPalette

from models import Item, Bid, User


class AuctionItemWidget(QWidget):
    """Widget displaying a single auction item."""
    
    item_selected = pyqtSignal(str)  # item_id
    bid_placed = pyqtSignal(str, float, str)  # item_id, amount, currency
    
    def __init__(self, item: Item, parent=None):
        super().__init__(parent)
        self.item = item
        self.setup_ui()
        
        # Timer for countdown updates
        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self.update_countdown)
        self.countdown_timer.start(1000)  # Update every second
    
    def setup_ui(self):
        """Setup the auction item UI."""
        layout = QVBoxLayout(self)
        
        # Item header
        header_layout = QHBoxLayout()
        
        # Item title
        title_label = QLabel(self.item.title or self.item.name)
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setWordWrap(True)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Status badge
        status_label = QLabel(self.item.status.upper())
        status_label.setFont(QFont("Arial", 10, QFont.Bold))
        status_color = self.get_status_color(self.item.status)
        status_label.setStyleSheet(f"""
            background-color: {status_color};
            color: white;
            padding: 4px 8px;
            border-radius: 12px;
        """)
        header_layout.addWidget(status_label)
        
        layout.addLayout(header_layout)
        
        # Item description
        if self.item.description:
            desc_label = QLabel(self.item.description[:200] + "..." if len(self.item.description) > 200 else self.item.description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("color: #666; margin: 5px 0;")
            layout.addWidget(desc_label)
        
        # Pricing information
        price_layout = QHBoxLayout()
        
        # Starting price
        starting_price = self.item.starting_price_doge or self.item.starting_price
        price_layout.addWidget(QLabel(f"Starting: {starting_price} DOGE"))
        
        # Current bid
        current_bid = self.item.current_bid_doge or self.item.current_bid or starting_price
        current_bid_label = QLabel(f"Current: {current_bid} DOGE")
        current_bid_label.setFont(QFont("Arial", 12, QFont.Bold))
        current_bid_label.setStyleSheet("color: #2e7d32;")
        price_layout.addWidget(current_bid_label)
        
        price_layout.addStretch()
        
        layout.addLayout(price_layout)
        
        # Auction timing
        timing_layout = QHBoxLayout()
        
        # Countdown
        self.countdown_label = QLabel("Calculating...")
        self.countdown_label.setFont(QFont("Arial", 11, QFont.Bold))
        timing_layout.addWidget(QLabel("Time left:"))
        timing_layout.addWidget(self.countdown_label)
        
        timing_layout.addStretch()
        
        # End time
        if self.item.auction_end:
            try:
                end_time = datetime.fromisoformat(self.item.auction_end.replace('Z', '+00:00'))
                end_time_str = end_time.strftime("%Y-%m-%d %H:%M UTC")
                timing_layout.addWidget(QLabel(f"Ends: {end_time_str}"))
            except:
                timing_layout.addWidget(QLabel("End time: Unknown"))
        
        layout.addLayout(timing_layout)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        view_btn = QPushButton("View Details")
        view_btn.clicked.connect(lambda: self.item_selected.emit(self.item.id))
        button_layout.addWidget(view_btn)
        
        if self.item.status == 'active' and not self.is_ended():
            bid_btn = QPushButton("Place Bid")
            bid_btn.setStyleSheet("""
                QPushButton {
                    background-color: #1976d2;
                    color: white;
                    font-weight: bold;
                    padding: 8px 16px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #1565c0;
                }
            """)
            bid_btn.clicked.connect(self.show_bid_dialog)
            button_layout.addWidget(bid_btn)
        
        layout.addLayout(button_layout)
        
        # Styling
        self.setStyleSheet("""
            QWidget {
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 15px;
                margin: 5px;
                background: white;
            }
            QWidget:hover {
                border-color: #1976d2;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
        """)
        
        self.setMaximumHeight(200)
        
        # Initial countdown update
        self.update_countdown()
    
    def get_status_color(self, status: str) -> str:
        """Get color for status badge."""
        colors = {
            'draft': '#757575',
            'active': '#2e7d32',
            'sold': '#1976d2',
            'expired': '#d32f2f',
            'cancelled': '#f57c00'
        }
        return colors.get(status, '#757575')
    
    def update_countdown(self):
        """Update the countdown display."""
        if not self.item.auction_end:
            self.countdown_label.setText("No end time")
            self.countdown_label.setStyleSheet("color: #666;")
            return
        
        try:
            end_time = datetime.fromisoformat(self.item.auction_end.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            
            if now >= end_time:
                self.countdown_label.setText("ENDED")
                self.countdown_label.setStyleSheet("color: red; font-weight: bold;")
                self.countdown_timer.stop()
                return
            
            time_left = end_time - now
            
            days = time_left.days
            hours, remainder = divmod(time_left.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            if days > 0:
                countdown_text = f"{days}d {hours}h {minutes}m"
                color = "#2e7d32"
            elif hours > 0:
                countdown_text = f"{hours}h {minutes}m {seconds}s"
                color = "#f57c00" if hours < 2 else "#2e7d32"
            else:
                countdown_text = f"{minutes}m {seconds}s"
                color = "#d32f2f" if minutes < 10 else "#f57c00"
            
            self.countdown_label.setText(countdown_text)
            self.countdown_label.setStyleSheet(f"color: {color}; font-weight: bold;")
            
        except Exception as e:
            self.countdown_label.setText("Error")
            self.countdown_label.setStyleSheet("color: red;")
    
    def is_ended(self) -> bool:
        """Check if auction has ended."""
        if not self.item.auction_end:
            return False
        try:
            end_time = datetime.fromisoformat(self.item.auction_end.replace('Z', '+00:00'))
            return datetime.now(timezone.utc) >= end_time
        except:
            return False
    
    def show_bid_dialog(self):
        """Show bid placement dialog."""
        dialog = BidDialog(self.item, self)
        if dialog.exec_() == QDialog.Accepted:
            bid_data = dialog.get_bid_data()
            self.bid_placed.emit(self.item.id, bid_data['amount'], bid_data['currency'])


class BidDialog(QDialog):
    """Dialog for placing bids."""
    
    def __init__(self, item: Item, parent=None):
        super().__init__(parent)
        self.item = item
        self.setWindowTitle(f"Place Bid - {item.title or item.name}")
        self.setModal(True)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup bid dialog UI."""
        layout = QVBoxLayout(self)
        
        # Item info
        info_group = QGroupBox("Item Information")
        info_layout = QVBoxLayout(info_group)
        
        info_layout.addWidget(QLabel(f"Title: {self.item.title or self.item.name}"))
        
        current_bid = self.item.current_bid_doge or self.item.current_bid or self.item.starting_price_doge or self.item.starting_price
        info_layout.addWidget(QLabel(f"Current Bid: {current_bid} DOGE"))
        
        layout.addWidget(info_group)
        
        # Bid form
        bid_group = QGroupBox("Your Bid")
        bid_layout = QFormLayout(bid_group)
        
        # Currency selection
        self.currency_combo = QComboBox()
        self.currency_combo.addItems(["DOGE", "NANO"])
        bid_layout.addRow("Currency:", self.currency_combo)
        
        # Bid amount
        self.amount_edit = QLineEdit()
        self.amount_edit.setPlaceholderText("Enter bid amount")
        
        # Set minimum bid
        try:
            min_bid = float(current_bid) + 0.1  # Minimum increment
            self.amount_edit.setText(str(min_bid))
        except:
            pass
        
        bid_layout.addRow("Amount:", self.amount_edit)
        
        # USD equivalent
        self.usd_label = QLabel("USD: $0.00")
        self.usd_label.setStyleSheet("color: #666; font-size: 10px;")
        bid_layout.addRow("", self.usd_label)
        
        # Auto-bid option
        self.auto_bid_checkbox = QCheckBox("Enable auto-bidding")
        bid_layout.addRow("", self.auto_bid_checkbox)
        
        # Max auto-bid amount
        self.max_auto_bid_edit = QLineEdit()
        self.max_auto_bid_edit.setPlaceholderText("Maximum auto-bid amount")
        self.max_auto_bid_edit.setEnabled(False)
        bid_layout.addRow("Max Auto-bid:", self.max_auto_bid_edit)
        
        self.auto_bid_checkbox.toggled.connect(self.max_auto_bid_edit.setEnabled)
        
        layout.addWidget(bid_group)
        
        # Bid confirmation
        confirm_group = QGroupBox("Confirmation")
        confirm_layout = QVBoxLayout(confirm_group)
        
        self.confirm_checkbox = QCheckBox("I confirm this bid and understand it is binding")
        confirm_layout.addWidget(self.confirm_checkbox)
        
        layout.addWidget(confirm_group)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Ok).setText("Place Bid")
        button_box.button(QDialogButtonBox.Ok).setEnabled(False)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Enable/disable OK button based on confirmation
        self.confirm_checkbox.toggled.connect(
            lambda checked: button_box.button(QDialogButtonBox.Ok).setEnabled(checked)
        )
        
        # Update USD equivalent when amount changes
        self.amount_edit.textChanged.connect(self.update_usd_equivalent)
    
    def update_usd_equivalent(self):
        """Update USD equivalent display."""
        try:
            amount = float(self.amount_edit.text())
            currency = self.currency_combo.currentText()
            
            # Mock conversion rates (in real implementation, use CoinGecko API)
            rates = {"DOGE": 0.08, "NANO": 1.20}
            usd_value = amount * rates.get(currency, 0)
            
            self.usd_label.setText(f"USD: ${usd_value:.2f}")
        except:
            self.usd_label.setText("USD: $0.00")
    
    def get_bid_data(self) -> dict:
        """Get bid data from form."""
        return {
            'amount': float(self.amount_edit.text()),
            'currency': self.currency_combo.currentText(),
            'auto_bid': self.auto_bid_checkbox.isChecked(),
            'max_auto_bid': float(self.max_auto_bid_edit.text()) if self.max_auto_bid_edit.text() else None
        }


class AuctionListWidget(QWidget):
    """Widget displaying list of auctions with filtering and sorting."""
    
    item_selected = pyqtSignal(str)  # item_id
    bid_placed = pyqtSignal(str, float, str)  # item_id, amount, currency
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.items = []
        self.filtered_items = []
        self.setup_ui()
    
    def setup_ui(self):
        """Setup auction list UI."""
        layout = QVBoxLayout(self)
        
        # Filter and sort controls
        controls_layout = QHBoxLayout()
        
        # Search
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search auctions...")
        self.search_edit.textChanged.connect(self.apply_filters)
        controls_layout.addWidget(QLabel("Search:"))
        controls_layout.addWidget(self.search_edit)
        
        # Status filter
        self.status_combo = QComboBox()
        self.status_combo.addItems(["All", "Active", "Ending Soon", "Sold", "Expired"])
        self.status_combo.currentTextChanged.connect(self.apply_filters)
        controls_layout.addWidget(QLabel("Status:"))
        controls_layout.addWidget(self.status_combo)
        
        # Sort by
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["End Time", "Current Bid", "Starting Price", "Title"])
        self.sort_combo.currentTextChanged.connect(self.apply_filters)
        controls_layout.addWidget(QLabel("Sort by:"))
        controls_layout.addWidget(self.sort_combo)
        
        # Sort order
        self.sort_order_combo = QComboBox()
        self.sort_order_combo.addItems(["Ascending", "Descending"])
        self.sort_order_combo.currentTextChanged.connect(self.apply_filters)
        controls_layout.addWidget(self.sort_order_combo)
        
        controls_layout.addStretch()
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh_auctions)
        controls_layout.addWidget(refresh_btn)
        
        layout.addLayout(controls_layout)
        
        # Auction list
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarNever)
        
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.addStretch()
        
        self.scroll_area.setWidget(self.scroll_widget)
        layout.addWidget(self.scroll_area)
        
        # Status bar
        self.status_label = QLabel("No auctions loaded")
        self.status_label.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(self.status_label)
    
    def set_items(self, items: list):
        """Set the list of auction items."""
        self.items = items
        self.apply_filters()
    
    def apply_filters(self):
        """Apply current filters and sorting."""
        # Start with all items
        filtered = self.items.copy()
        
        # Apply search filter
        search_text = self.search_edit.text().lower()
        if search_text:
            filtered = [item for item in filtered 
                       if search_text in (item.title or item.name or "").lower() 
                       or search_text in (item.description or "").lower()]
        
        # Apply status filter
        status_filter = self.status_combo.currentText()
        if status_filter != "All":
            if status_filter == "Active":
                filtered = [item for item in filtered if item.status == 'active']
            elif status_filter == "Ending Soon":
                # Items ending within 24 hours
                now = datetime.now(timezone.utc)
                cutoff = now + timedelta(hours=24)
                filtered = [item for item in filtered 
                           if item.status == 'active' and item.auction_end 
                           and datetime.fromisoformat(item.auction_end.replace('Z', '+00:00')) <= cutoff]
            elif status_filter == "Sold":
                filtered = [item for item in filtered if item.status == 'sold']
            elif status_filter == "Expired":
                filtered = [item for item in filtered if item.status == 'expired']
        
        # Apply sorting
        sort_by = self.sort_combo.currentText()
        reverse = self.sort_order_combo.currentText() == "Descending"
        
        if sort_by == "End Time":
            filtered.sort(key=lambda x: x.auction_end or "", reverse=reverse)
        elif sort_by == "Current Bid":
            filtered.sort(key=lambda x: float(x.current_bid_doge or x.current_bid or 0), reverse=reverse)
        elif sort_by == "Starting Price":
            filtered.sort(key=lambda x: float(x.starting_price_doge or x.starting_price or 0), reverse=reverse)
        elif sort_by == "Title":
            filtered.sort(key=lambda x: (x.title or x.name or "").lower(), reverse=reverse)
        
        self.filtered_items = filtered
        self.update_display()
    
    def update_display(self):
        """Update the display with filtered items."""
        # Clear existing widgets
        for i in reversed(range(self.scroll_layout.count())):
            child = self.scroll_layout.itemAt(i).widget()
            if child and isinstance(child, AuctionItemWidget):
                child.setParent(None)
        
        # Add filtered items
        for item in self.filtered_items:
            item_widget = AuctionItemWidget(item)
            item_widget.item_selected.connect(self.item_selected.emit)
            item_widget.bid_placed.connect(self.bid_placed.emit)
            self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, item_widget)
        
        # Update status
        self.status_label.setText(f"Showing {len(self.filtered_items)} of {len(self.items)} auctions")
    
    def refresh_auctions(self):
        """Refresh auction data."""
        # TODO: Implement actual refresh from client
        self.status_label.setText("Refreshing...")
        # Simulate refresh delay
        QTimer.singleShot(1000, lambda: self.status_label.setText(f"Showing {len(self.filtered_items)} of {len(self.items)} auctions"))


class AuctionDetailsWidget(QWidget):
    """Detailed view of a single auction item."""
    
    bid_placed = pyqtSignal(str, float, str)  # item_id, amount, currency
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.item = None
        self.setup_ui()
    
    def setup_ui(self):
        """Setup auction details UI."""
        layout = QVBoxLayout(self)
        
        # Create tabs for different sections
        self.tab_widget = QTabWidget()
        
        # Item details tab
        self.details_tab = self.create_details_tab()
        self.tab_widget.addTab(self.details_tab, "Details")
        
        # Bid history tab
        self.bid_history_tab = self.create_bid_history_tab()
        self.tab_widget.addTab(self.bid_history_tab, "Bid History")
        
        # Seller info tab
        self.seller_tab = self.create_seller_tab()
        self.tab_widget.addTab(self.seller_tab, "Seller")
        
        layout.addWidget(self.tab_widget)
    
    def create_details_tab(self) -> QWidget:
        """Create the item details tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Item title
        self.title_label = QLabel()
        self.title_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)
        
        # Item description
        self.description_browser = QTextBrowser()
        self.description_browser.setMaximumHeight(150)
        layout.addWidget(self.description_browser)
        
        # Pricing info
        price_group = QGroupBox("Pricing")
        price_layout = QFormLayout(price_group)
        
        self.starting_price_label = QLabel()
        price_layout.addRow("Starting Price:", self.starting_price_label)
        
        self.current_bid_label = QLabel()
        price_layout.addRow("Current Bid:", self.current_bid_label)
        
        self.bid_count_label = QLabel()
        price_layout.addRow("Number of Bids:", self.bid_count_label)
        
        layout.addWidget(price_group)
        
        # Timing info
        timing_group = QGroupBox("Timing")
        timing_layout = QFormLayout(timing_group)
        
        self.start_time_label = QLabel()
        timing_layout.addRow("Started:", self.start_time_label)
        
        self.end_time_label = QLabel()
        timing_layout.addRow("Ends:", self.end_time_label)
        
        self.countdown_label = QLabel()
        timing_layout.addRow("Time Left:", self.countdown_label)
        
        layout.addWidget(timing_group)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.bid_button = QPushButton("Place Bid")
        self.bid_button.setStyleSheet("""
            QPushButton {
                background-color: #1976d2;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1565c0;
            }
            QPushButton:disabled {
                background-color: #ccc;
            }
        """)
        self.bid_button.clicked.connect(self.show_bid_dialog)
        button_layout.addWidget(self.bid_button)
        
        self.watch_button = QPushButton("Add to Watchlist")
        button_layout.addWidget(self.watch_button)
        
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        return tab
    
    def create_bid_history_tab(self) -> QWidget:
        """Create the bid history tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Bid history table
        self.bid_table = QTableWidget(0, 5)
        self.bid_table.setHorizontalHeaderLabels(["Time", "Bidder", "Amount", "Currency", "Status"])
        self.bid_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.bid_table)
        
        return tab
    
    def create_seller_tab(self) -> QWidget:
        """Create the seller info tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Seller info
        seller_group = QGroupBox("Seller Information")
        seller_layout = QFormLayout(seller_group)
        
        self.seller_name_label = QLabel()
        seller_layout.addRow("Username:", self.seller_name_label)
        
        self.seller_reputation_label = QLabel()
        seller_layout.addRow("Reputation:", self.seller_reputation_label)
        
        self.seller_joined_label = QLabel()
        seller_layout.addRow("Member Since:", self.seller_joined_label)
        
        layout.addWidget(seller_group)
        
        # Seller stats
        stats_group = QGroupBox("Seller Statistics")
        stats_layout = QFormLayout(stats_group)
        
        self.total_sales_label = QLabel()
        stats_layout.addRow("Total Sales:", self.total_sales_label)
        
        self.avg_rating_label = QLabel()
        stats_layout.addRow("Average Rating:", self.avg_rating_label)
        
        layout.addWidget(stats_group)
        
        layout.addStretch()
        
        return tab
    
    def set_item(self, item: Item):
        """Set the item to display."""
        self.item = item
        self.update_display()
    
    def update_display(self):
        """Update the display with current item data."""
        if not self.item:
            return
        
        # Update details tab
        self.title_label.setText(self.item.title or self.item.name or "Untitled")
        self.description_browser.setPlainText(self.item.description or "No description available")
        
        starting_price = self.item.starting_price_doge or self.item.starting_price or 0
        self.starting_price_label.setText(f"{starting_price} DOGE")
        
        current_bid = self.item.current_bid_doge or self.item.current_bid or starting_price
        self.current_bid_label.setText(f"{current_bid} DOGE")
        
        self.bid_count_label.setText(str(len(self.item.bids)))
        
        # Update timing
        if self.item.created_at:
            try:
                created = datetime.fromisoformat(self.item.created_at.replace('Z', '+00:00'))
                self.start_time_label.setText(created.strftime("%Y-%m-%d %H:%M UTC"))
            except:
                self.start_time_label.setText("Unknown")
        
        if self.item.auction_end:
            try:
                end_time = datetime.fromisoformat(self.item.auction_end.replace('Z', '+00:00'))
                self.end_time_label.setText(end_time.strftime("%Y-%m-%d %H:%M UTC"))
                
                # Calculate countdown
                now = datetime.now(timezone.utc)
                if now >= end_time:
                    self.countdown_label.setText("ENDED")
                    self.countdown_label.setStyleSheet("color: red; font-weight: bold;")
                    self.bid_button.setEnabled(False)
                else:
                    time_left = end_time - now
                    days = time_left.days
                    hours, remainder = divmod(time_left.seconds, 3600)
                    minutes, _ = divmod(remainder, 60)
                    
                    if days > 0:
                        countdown_text = f"{days}d {hours}h {minutes}m"
                    else:
                        countdown_text = f"{hours}h {minutes}m"
                    
                    self.countdown_label.setText(countdown_text)
                    self.bid_button.setEnabled(self.item.status == 'active')
                    
            except:
                self.end_time_label.setText("Unknown")
                self.countdown_label.setText("Unknown")
        
        # Update bid history
        self.update_bid_history()
    
    def update_bid_history(self):
        """Update the bid history table."""
        self.bid_table.setRowCount(len(self.item.bids))
        
        for i, bid_data in enumerate(self.item.bids):
            # In a real implementation, bid_data would be Bid objects
            # For now, assume it's a dict
            if isinstance(bid_data, dict):
                self.bid_table.setItem(i, 0, QTableWidgetItem(bid_data.get('created_at', '')))
                self.bid_table.setItem(i, 1, QTableWidgetItem(bid_data.get('bidder_id', '')))
                self.bid_table.setItem(i, 2, QTableWidgetItem(str(bid_data.get('amount_doge', ''))))
                self.bid_table.setItem(i, 3, QTableWidgetItem('DOGE'))
                self.bid_table.setItem(i, 4, QTableWidgetItem(bid_data.get('status', '')))
    
    def show_bid_dialog(self):
        """Show bid placement dialog."""
        if self.item:
            dialog = BidDialog(self.item, self)
            if dialog.exec_() == QDialog.Accepted:
                bid_data = dialog.get_bid_data()
                self.bid_placed.emit(self.item.id, bid_data['amount'], bid_data['currency'])


class CreateAuctionDialog(QDialog):
    """Dialog for creating new auctions."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Auction")
        self.setModal(True)
        self.resize(500, 600)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup create auction UI."""
        layout = QVBoxLayout(self)
        
        # Form layout
        form_layout = QFormLayout()
        
        # Item title
        self.title_edit = QLineEdit()
        self.title_edit.setMaxLength(100)  # From ui_constants
        form_layout.addRow("Title*:", self.title_edit)
        
        # Item description
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(100)
        form_layout.addRow("Description:", self.description_edit)
        
        # Starting price
        price_layout = QHBoxLayout()
        self.starting_price_edit = QLineEdit()
        self.starting_price_edit.setPlaceholderText("0.00")
        price_layout.addWidget(self.starting_price_edit)
        
        self.currency_combo = QComboBox()
        self.currency_combo.addItems(["DOGE", "NANO"])
        price_layout.addWidget(self.currency_combo)
        
        form_layout.addRow("Starting Price*:", price_layout)
        
        # Auction duration
        duration_layout = QHBoxLayout()
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 30)
        self.duration_spin.setValue(7)
        duration_layout.addWidget(self.duration_spin)
        
        self.duration_unit_combo = QComboBox()
        self.duration_unit_combo.addItems(["Days", "Hours"])
        duration_layout.addWidget(self.duration_unit_combo)
        
        form_layout.addRow("Duration*:", duration_layout)
        
        # Category
        self.category_combo = QComboBox()
        self.category_combo.addItems([
            "Electronics", "Collectibles", "Art", "Books", 
            "Clothing", "Home & Garden", "Sports", "Other"
        ])
        form_layout.addRow("Category:", self.category_combo)
        
        # Tags
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("tag1, tag2, tag3 (max 10 tags)")
        form_layout.addRow("Tags:", self.tags_edit)
        
        # Shipping options
        shipping_group = QGroupBox("Shipping")
        shipping_layout = QVBoxLayout(shipping_group)
        
        self.shipping_required_checkbox = QCheckBox("Physical item requiring shipping")
        shipping_layout.addWidget(self.shipping_required_checkbox)
        
        shipping_cost_layout = QHBoxLayout()
        self.shipping_cost_edit = QLineEdit()
        self.shipping_cost_edit.setPlaceholderText("0.00")
        self.shipping_cost_edit.setEnabled(False)
        shipping_cost_layout.addWidget(QLabel("Shipping Cost:"))
        shipping_cost_layout.addWidget(self.shipping_cost_edit)
        shipping_cost_layout.addWidget(QLabel("DOGE"))
        
        shipping_layout.addLayout(shipping_cost_layout)
        
        self.shipping_required_checkbox.toggled.connect(self.shipping_cost_edit.setEnabled)
        
        layout.addLayout(form_layout)
        layout.addWidget(shipping_group)
        
        # Preview section
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_label = QLabel("Fill in the form to see preview")
        self.preview_label.setWordWrap(True)
        self.preview_label.setStyleSheet("border: 1px solid #ddd; padding: 10px; background: #f9f9f9;")
        preview_layout.addWidget(self.preview_label)
        
        layout.addWidget(preview_group)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Ok).setText("Create Auction")
        button_box.accepted.connect(self.create_auction)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Connect signals for live preview
        self.title_edit.textChanged.connect(self.update_preview)
        self.description_edit.textChanged.connect(self.update_preview)
        self.starting_price_edit.textChanged.connect(self.update_preview)
        self.currency_combo.currentTextChanged.connect(self.update_preview)
    
    def update_preview(self):
        """Update the auction preview."""
        title = self.title_edit.text() or "Untitled Auction"
        description = self.description_edit.toPlainText() or "No description"
        price = self.starting_price_edit.text() or "0"
        currency = self.currency_combo.currentText()
        
        preview_text = f"""
        <b>{title}</b><br>
        <i>{description[:100]}{'...' if len(description) > 100 else ''}</i><br><br>
        <b>Starting Price:</b> {price} {currency}<br>
        <b>Status:</b> Ready to create
        """
        
        self.preview_label.setText(preview_text)
    
    def create_auction(self):
        """Validate and create the auction."""
        # Validate required fields
        if not self.title_edit.text().strip():
            QMessageBox.warning(self, "Missing Title", "Please enter an auction title.")
            return
        
        if not self.starting_price_edit.text().strip():
            QMessageBox.warning(self, "Missing Price", "Please enter a starting price.")
            return
        
        try:
            price = float(self.starting_price_edit.text())
            if price <= 0:
                raise ValueError()
        except ValueError:
            QMessageBox.warning(self, "Invalid Price", "Please enter a valid starting price.")
            return
        
        # Validate tags
        tags = [tag.strip() for tag in self.tags_edit.text().split(',') if tag.strip()]
        if len(tags) > 10:
            QMessageBox.warning(self, "Too Many Tags", "Maximum 10 tags allowed.")
            return
        
        # Show confirmation
        reply = QMessageBox.question(self, "Create Auction", 
                                   "Create this auction? This action cannot be undone.",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # TODO: Implement actual auction creation
            QMessageBox.information(self, "Auction Created", "Your auction has been created successfully!")
            self.accept()
    
    def get_auction_data(self) -> dict:
        """Get auction data from form."""
        duration_hours = self.duration_spin.value()
        if self.duration_unit_combo.currentText() == "Days":
            duration_hours *= 24
        
        end_time = datetime.now(timezone.utc) + timedelta(hours=duration_hours)
        
        tags = [tag.strip() for tag in self.tags_edit.text().split(',') if tag.strip()]
        
        return {
            'title': self.title_edit.text().strip(),
            'description': self.description_edit.toPlainText().strip(),
            'starting_price_doge': self.starting_price_edit.text(),
            'currency': self.currency_combo.currentText(),
            'auction_end': end_time.isoformat(),
            'category': self.category_combo.currentText(),
            'tags': tags,
            'shipping_required': self.shipping_required_checkbox.isChecked(),
            'shipping_cost_doge': self.shipping_cost_edit.text() if self.shipping_required_checkbox.isChecked() else "0"
        }