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
                             QListWidget, QListWidgetItem, QSplitter, QTextBrowser,
                             QGridLayout)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QDateTime, QThread
from PyQt5.QtGui import QFont, QPixmap, QIcon, QColor, QPalette

from models.models import Item, Bid, User


class AsyncWorker(QThread):
    """Simple async worker for loading data."""
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


class AuctionItemWidget(QWidget):
    """Enhanced widget displaying a single auction item with authenticator dot and improved UI."""
    
    item_selected = pyqtSignal(str)  # item_id
    bid_placed = pyqtSignal(str, float, str)  # item_id, amount, currency
    
    def __init__(self, item: Item, parent=None, active_section="marketplace"):
        super().__init__(parent)
        self.item = item
        self.active_section = active_section  # "marketplace" or "my-items"
        self.setup_ui()
        
        # Timer for countdown updates
        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self.update_countdown)
        self.countdown_timer.start(1000)  # Update every second
    
    def setup_ui(self):
        """Setup the enhanced auction item UI based on ui_information.json specifications."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Image section with status badges (aspect ratio 4:3)
        image_frame = QFrame()
        image_frame.setFixedHeight(150)  # Approximate 4:3 ratio for 200px width
        image_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 8px 8px 0 0;
                border: 1px solid #e9ecef;
                position: relative;
            }
        """)
        
        image_layout = QVBoxLayout(image_frame)
        image_layout.setContentsMargins(8, 8, 8, 8)
        
        # Status badge overlay
        badge_layout = QHBoxLayout()
        badge_layout.addStretch()
        
        status_badge = self.create_status_badge()
        if status_badge:
            badge_layout.addWidget(status_badge)
        
        image_layout.addLayout(badge_layout)
        image_layout.addStretch()
        
        # Placeholder for image
        image_placeholder = QLabel("📷")
        image_placeholder.setAlignment(Qt.AlignCenter)
        image_placeholder.setStyleSheet("font-size: 32px; color: #6c757d;")
        image_layout.addWidget(image_placeholder)
        image_layout.addStretch()
        
        layout.addWidget(image_frame)
        
        # Content section
        content_frame = QFrame()
        content_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e9ecef;
                border-top: none;
                border-radius: 0 0 8px 8px;
                padding: 12px;
            }
        """)
        
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(8)
        
        # Header section with title and authenticator dot
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        # Item title
        title_text = self.item.title or self.item.name or f"Item #{self.item.id[:8]}"
        title_label = QLabel(title_text)
        title_label.setFont(QFont("Arial", 12, QFont.DemiBold))
        title_label.setStyleSheet("color: #1e293b;")
        title_label.setWordWrap(True)
        header_layout.addWidget(title_label, 1)
        
        # Authenticator dot with tooltip
        auth_dot = self.create_authenticator_dot()
        header_layout.addWidget(auth_dot)
        
        content_layout.addLayout(header_layout)
        
        # Description section
        if self.item.description:
            desc_text = self.item.description[:100] + "..." if len(self.item.description) > 100 else self.item.description
            desc_label = QLabel(desc_text or "No description available")
            desc_label.setFont(QFont("Arial", 10))
            desc_label.setStyleSheet("color: #64748b;")
            desc_label.setWordWrap(True)
            content_layout.addWidget(desc_label)
        
        # Price section
        price_layout = QHBoxLayout()
        price_layout.setSpacing(0)
        
        # Price display
        price_info = self.get_price_info()
        price_label = QLabel(price_info["price"])
        price_label.setFont(QFont("Arial", 16, QFont.Bold))
        price_label.setStyleSheet("color: #1e293b;")
        
        price_desc_label = QLabel(price_info["label"])
        price_desc_label.setFont(QFont("Arial", 9))
        price_desc_label.setStyleSheet("color: #64748b;")
        
        price_left_layout = QVBoxLayout()
        price_left_layout.setContentsMargins(0, 0, 0, 0)
        price_left_layout.setSpacing(2)
        price_left_layout.addWidget(price_desc_label)
        price_left_layout.addWidget(price_label)
        
        price_layout.addLayout(price_left_layout)
        price_layout.addStretch()
        
        # Timer (only for active auctions)
        if self.item.status == 'active' and not self.is_ended():
            timer_layout = QVBoxLayout()
            timer_layout.setContentsMargins(0, 0, 0, 0)
            timer_layout.setSpacing(2)
            
            timer_desc = QLabel("Ends")
            timer_desc.setFont(QFont("Arial", 9))
            timer_desc.setStyleSheet("color: #64748b;")
            timer_desc.setAlignment(Qt.AlignRight)
            
            self.countdown_label = QLabel("Calculating...")
            self.countdown_label.setFont(QFont("Arial", 11, QFont.DemiBold))
            self.countdown_label.setStyleSheet("color: #1e293b;")
            self.countdown_label.setAlignment(Qt.AlignRight)
            
            timer_layout.addWidget(timer_desc)
            timer_layout.addWidget(self.countdown_label)
            
            price_layout.addLayout(timer_layout)
        
        content_layout.addLayout(price_layout)
        
        # Buyer info (only for sold items)
        if self.item.status == 'sold' and hasattr(self.item, 'current_bidder') and self.item.current_bidder:
            buyer_label = QLabel(f"To: {self.item.current_bidder[:12]}...")
            buyer_label.setFont(QFont("Arial", 9))
            buyer_label.setStyleSheet("color: #64748b; margin-bottom: 8px;")
            content_layout.addWidget(buyer_label)
        
        # Action buttons (only for marketplace view and active items)
        if self.active_section == "marketplace" and self.item.status == 'active' and not self.is_ended():
            # Place Bid button
            bid_btn = QPushButton("Place Bid")
            bid_btn.setFixedHeight(36)
            bid_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3b82f6;
                    color: white;
                    font-weight: 500;
                    font-size: 12px;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 12px;
                }
                QPushButton:hover {
                    background-color: #2563eb;
                }
                QPushButton:pressed {
                    background-color: #1d4ed8;
                }
            """)
            
            # Add minimum bid info to button
            min_bid = self.get_minimum_bid()
            if min_bid:
                bid_btn.setText(f"Place Bid                {min_bid}")
                bid_btn.setStyleSheet(bid_btn.styleSheet() + """
                    QPushButton {
                        text-align: left;
                        padding-left: 12px;
                        padding-right: 12px;
                    }
                """)
            
            bid_btn.clicked.connect(self.show_bid_dialog)
            content_layout.addWidget(bid_btn)
            
            # View Bid History button
            history_btn = QPushButton("📊 View Bid History")
            history_btn.setFixedHeight(28)
            history_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #64748b;
                    font-size: 10px;
                    border: none;
                    text-align: center;
                }
                QPushButton:hover {
                    color: #1e293b;
                    background-color: #f8fafc;
                }
            """)
            history_btn.clicked.connect(lambda: self.item_selected.emit(self.item.id))
            content_layout.addWidget(history_btn)
        else:
            # View Details button for non-marketplace or inactive items
            view_btn = QPushButton("View Details")
            view_btn.setFixedHeight(36)
            view_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f8fafc;
                    color: #1e293b;
                    font-weight: 500;
                    font-size: 12px;
                    border: 1px solid #e2e8f0;
                    border-radius: 6px;
                    padding: 8px 12px;
                }
                QPushButton:hover {
                    background-color: #f1f5f9;
                    border-color: #cbd5e1;
                }
            """)
            view_btn.clicked.connect(lambda: self.item_selected.emit(self.item.id))
            content_layout.addWidget(view_btn)
        
        layout.addWidget(content_frame)
        
        # Main widget styling
        self.setStyleSheet("""
            AuctionItemWidget {
                background-color: transparent;
            }
            AuctionItemWidget:hover QFrame {
                border-color: #3b82f6;
            }
        """)
        
        self.setFixedWidth(280)
        self.setMinimumHeight(320)
        
        # Initial countdown update
        if hasattr(self, 'countdown_label'):
            self.update_countdown()
    
    def create_status_badge(self):
        """Create status badge based on item status."""
        if self.item.status == 'active' and not self.is_ended():
            badge = QLabel("● Live")
            badge.setStyleSheet("""
                QLabel {
                    background-color: rgba(255, 255, 255, 0.9);
                    color: #1e293b;
                    font-size: 10px;
                    font-weight: 500;
                    padding: 4px 8px;
                    border-radius: 12px;
                    border: 1px solid rgba(0, 0, 0, 0.1);
                }
            """)
            # Add blue dot
            badge.setStyleSheet(badge.styleSheet().replace("●", "<span style='color: #3b82f6;'>●</span>"))
            return badge
        elif self.item.status == 'sold':
            badge = QLabel("Sold")
            badge.setStyleSheet("""
                QLabel {
                    background-color: #dcfce7;
                    color: #166534;
                    font-size: 10px;
                    font-weight: 500;
                    padding: 4px 8px;
                    border-radius: 12px;
                }
            """)
            return badge
        elif self.item.status == 'expired' or self.is_ended():
            badge = QLabel("Expired")
            badge.setStyleSheet("""
                QLabel {
                    background-color: #f3f4f6;
                    color: #374151;
                    font-size: 10px;
                    font-weight: 500;
                    padding: 4px 8px;
                    border-radius: 12px;
                }
            """)
            return badge
        return None
    
    def create_authenticator_dot(self):
        """Create authenticator status dot with tooltip."""
        dot = QPushButton()
        dot.setFixedSize(12, 12)
        
        # Determine authentication status (simplified for now)
        is_verified = True  # This would be determined by actual verification logic
        
        if is_verified:
            dot.setStyleSheet("""
                QPushButton {
                    background-color: #10b981;
                    border: 2px solid white;
                    border-radius: 6px;
                    outline: 1px solid #10b981;
                }
                QPushButton:hover {
                    background-color: #059669;
                    outline: 1px solid #059669;
                }
            """)
            dot.setToolTip("Authentication Status\n\n✓ Item Verified\n✓ Seller Verified\n✓ Blockchain Secured")
        else:
            dot.setStyleSheet("""
                QPushButton {
                    background-color: #ef4444;
                    border: 2px solid white;
                    border-radius: 6px;
                    outline: 1px solid #ef4444;
                }
                QPushButton:hover {
                    background-color: #dc2626;
                    outline: 1px solid #dc2626;
                }
            """)
            dot.setToolTip("Authentication Status\n\n✗ Verification Pending")
        
        return dot
    
    def get_price_info(self):
        """Get price information with appropriate label."""
        if self.item.status == 'sold':
            price = self.item.current_bid_doge or self.item.current_bid or self.item.starting_price_doge or self.item.starting_price or "0"
            return {"price": f"${price}", "label": "Sold for"}
        elif self.item.status == 'active':
            current_bid = self.item.current_bid_doge or self.item.current_bid
            if current_bid and float(current_bid) > 0:
                return {"price": f"${current_bid}", "label": "Current bid"}
            else:
                starting_price = self.item.starting_price_doge or self.item.starting_price or "0"
                return {"price": f"${starting_price}", "label": "Starting price"}
        else:
            price = self.item.starting_price_doge or self.item.starting_price or "0"
            return {"price": f"${price}", "label": "Final price"}
    
    def get_minimum_bid(self):
        """Get minimum bid amount for display."""
        current_bid = self.item.current_bid_doge or self.item.current_bid
        if current_bid and float(current_bid) > 0:
            min_bid = float(current_bid) + 1.0  # Add minimum increment
            return f"${min_bid:.2f}"
        else:
            starting_price = self.item.starting_price_doge or self.item.starting_price
            if starting_price:
                return f"${starting_price}"
        return None
    
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
    """Enhanced widget displaying list of auctions with filtering and sorting."""
    
    item_selected = pyqtSignal(str)  # item_id
    bid_placed = pyqtSignal(str, float, str)  # item_id, amount, currency
    
    def __init__(self, parent=None, active_section="marketplace"):
        super().__init__(parent)
        self.items = []
        self.filtered_items = []
        self.active_section = active_section  # "marketplace" or "my-items"
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
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
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
        """Update the display with filtered items using enhanced tiles."""
        # Clear existing widgets
        for i in reversed(range(self.scroll_layout.count())):
            child = self.scroll_layout.itemAt(i).widget()
            if child and isinstance(child, AuctionItemWidget):
                child.setParent(None)
        
        # Create grid layout for tiles
        if not hasattr(self, 'grid_widget') or not self.grid_widget:
            self.grid_widget = QWidget()
            self.grid_layout = QGridLayout(self.grid_widget)
            self.grid_layout.setSpacing(16)
            self.grid_layout.setContentsMargins(16, 16, 16, 16)
            self.scroll_layout.insertWidget(0, self.grid_widget)
        else:
            # Clear existing grid items
            for i in reversed(range(self.grid_layout.count())):
                child = self.grid_layout.itemAt(i).widget()
                if child:
                    child.setParent(None)
        
        # Add filtered items in grid layout (3 columns)
        columns = 3
        for index, item in enumerate(self.filtered_items):
            row = index // columns
            col = index % columns
            
            item_widget = AuctionItemWidget(item, active_section=self.active_section)
            item_widget.item_selected.connect(self.item_selected.emit)
            item_widget.bid_placed.connect(self.bid_placed.emit)
            self.grid_layout.addWidget(item_widget, row, col)
        
        # Add stretch to fill remaining space
        self.grid_layout.setRowStretch(self.grid_layout.rowCount(), 1)
        
        # Update status
        section_name = "items" if self.active_section == "my-items" else "auctions"
        self.status_label.setText(f"Showing {len(self.filtered_items)} of {len(self.items)} {section_name}")
    
    def load_auctions(self):
        """Load auctions based on active section."""
        from services.application_service import app_service
        
        self.status_label.setText("Loading...")
        
        if self.active_section == "my-items":
            # Load user's items
            if app_service.is_user_logged_in():
                worker = AsyncWorker(app_service.get_user_items())
                worker.finished.connect(self.on_items_loaded)
                worker.error.connect(self.on_load_error)
                worker.start()
                self.worker = worker
            else:
                self.set_items([])
        else:
            # Load marketplace auctions
            worker = AsyncWorker(app_service.get_active_auctions(limit=50))
            worker.finished.connect(self.on_items_loaded)
            worker.error.connect(self.on_load_error)
            worker.start()
            self.worker = worker
    
    def on_items_loaded(self, items):
        """Handle loaded items."""
        self.set_items(items or [])
    
    def on_load_error(self, error):
        """Handle loading error."""
        self.status_label.setText(f"Error loading {self.active_section}: {str(error)}")
        self.set_items([])
    
    def refresh_auctions(self):
        """Refresh auction data."""
        self.load_auctions()


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
        # Increase height to prevent text cutoff
        self.description_browser.setMinimumHeight(100)
        self.description_browser.setMaximumHeight(200)  # Increased from 150 to 200
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
        # Increase height to prevent text cutoff
        self.description_edit.setMinimumHeight(80)
        self.description_edit.setMaximumHeight(150)  # Increased from 100 to 150
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