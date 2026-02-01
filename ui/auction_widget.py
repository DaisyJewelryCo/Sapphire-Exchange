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
                             QGridLayout, QStackedWidget)
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
        """Create authenticator status dot with popup functionality."""
        dot = QPushButton()
        dot.setFixedSize(12, 12)
        dot.setCursor(Qt.PointingHandCursor)
        
        # Determine authentication status (simplified for now)
        is_verified = self.get_overall_authentication_status()
        
        if is_verified == 'verified':
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
                    transform: scale(1.1);
                }
            """)
        elif is_verified == 'warning':
            dot.setStyleSheet("""
                QPushButton {
                    background-color: #f59e0b;
                    border: 2px solid white;
                    border-radius: 6px;
                    outline: 1px solid #f59e0b;
                }
                QPushButton:hover {
                    background-color: #d97706;
                    outline: 1px solid #d97706;
                    transform: scale(1.1);
                }
            """)
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
                    transform: scale(1.1);
                }
            """)
        
        # Connect click to show authentication popup
        dot.clicked.connect(self.show_authentication_popup)
        
        return dot
    
    def get_overall_authentication_status(self) -> str:
        """Get overall authentication status for the item."""
        # Check various authentication factors
        has_arweave = bool(self.item.arweave_metadata_uri)
        has_nano_wallet = bool(self.item.auction_nano_address)
        has_rsa = bool(self.item.auction_rsa_public_key)
        has_data_hash = bool(self.item.data_hash)
        
        verified_count = sum([has_arweave, has_nano_wallet, has_rsa, has_data_hash])
        
        if verified_count >= 3:
            return 'verified'
        elif verified_count >= 1:
            return 'warning'
        else:
            return 'error'
    
    def show_authentication_popup(self):
        """Show authentication status popup."""
        from ui.authentication_status_popup import AuthenticationStatusPopup
        
        # Close any existing popup
        if hasattr(self, 'auth_popup') and self.auth_popup:
            self.auth_popup.close()
        
        # Create new popup
        self.auth_popup = AuthenticationStatusPopup(self.item, self)
        
        # Position popup near the dot
        dot_button = self.sender()
        dot_global_pos = dot_button.mapToGlobal(dot_button.rect().bottomRight())
        popup_pos = dot_global_pos
        popup_pos.setX(popup_pos.x() + 10)  # Offset to the right
        popup_pos.setY(popup_pos.y() + 5)   # Offset down slightly
        
        # Show popup
        self.auth_popup.show_popup(popup_pos)
        self.auth_popup.closed.connect(lambda: setattr(self, 'auth_popup', None))
    
    def get_price_info(self):
        """Get price information with appropriate label."""
        if self.item.status == 'sold':
            price = self.item.current_bid_usdc or self.item.starting_price_usdc or "0"
            return {"price": f"${price}", "label": "Sold for"}
        elif self.item.status == 'active':
            current_bid = self.item.current_bid_usdc
            if current_bid and float(current_bid) > 0:
                return {"price": f"${current_bid}", "label": "Current bid"}
            else:
                starting_price = self.item.starting_price_usdc or "0"
                return {"price": f"${starting_price}", "label": "Starting price"}
        else:
            price = self.item.starting_price_usdc or "0"
            return {"price": f"${price}", "label": "Final price"}
    
    def get_minimum_bid(self):
        """Get minimum bid amount for display."""
        current_bid = self.item.current_bid_usdc
        if current_bid and float(current_bid) > 0:
            min_bid = float(current_bid) + 1.0  # Add minimum increment
            return f"${min_bid:.2f}"
        else:
            starting_price = self.item.starting_price_usdc
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
        
        info_layout.addWidget(QLabel(f"Title: {self.item.title}"))
        
        current_bid = self.item.current_bid_usdc or self.item.starting_price_usdc
        info_layout.addWidget(QLabel(f"Current Bid: {current_bid} USDC"))
        
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
    arweave_post_generated = pyqtSignal(dict, str)  # post_data, auction_title
    
    def __init__(self, parent=None, active_section="marketplace"):
        super().__init__(parent)
        self.items = []
        self.filtered_items = []
        self.active_section = active_section  # "marketplace" or "my-items"
        self.refresh_interval = 30000  # Default 30 seconds in milliseconds
        self.setup_ui()
        self.setup_periodic_refresh()
    
    def setup_ui(self):
        """Setup auction list UI."""
        layout = QVBoxLayout(self)
        
        # Add header for My Items section
        if self.active_section == "my-items":
            header_widget = self.create_header_section()
            layout.addWidget(header_widget)
        
        # Category section (without header)
        category_section = self.create_category_section()
        layout.addWidget(category_section)
        
        # Auction list
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.scroll_widget = QWidget()
        
        if self.active_section == "my-items":
            # Create partitioned layout for my-items
            self.scroll_layout = QVBoxLayout(self.scroll_widget)
            self.scroll_layout.setSpacing(20)
            self.scroll_layout.setContentsMargins(20, 20, 20, 20)
            
            # Create partition sections
            self.partition_sections = {}
            partition_configs = [
                ("current_bids", "Current Bids", "🔥", "Items you are currently bidding on"),
                ("current_auctions", "Current Auctions", "⏰", "Your active auction listings"),
                ("won_items", "Won Items", "🏆", "Auctions you have won"),
                ("sold_auctions", "Sold Auctions", "💰", "Your auctions that have been sold"),
                ("expired_auctions", "Expired Auctions", "⏳", "Your expired auction listings")
            ]
            
            for section_id, title, icon, description in partition_configs:
                section_widget = self.create_partition_section(section_id, title, icon, description)
                self.partition_sections[section_id] = section_widget
                self.scroll_layout.addWidget(section_widget)
            
            self.scroll_layout.addStretch()
        else:
            # Standard layout for marketplace
            self.scroll_layout = QVBoxLayout(self.scroll_widget)
            self.scroll_layout.addStretch()
        
        self.scroll_area.setWidget(self.scroll_widget)
        layout.addWidget(self.scroll_area)
        
        # Status bar
        self.status_label = QLabel("No auctions loaded")
        self.status_label.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(self.status_label)
    
    def setup_periodic_refresh(self):
        """Setup periodic refresh timer."""
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_auctions)
        self.refresh_timer.start(self.refresh_interval)
    
    def set_refresh_interval(self, seconds):
        """Set the refresh interval in seconds."""
        self.refresh_interval = seconds * 1000  # Convert to milliseconds
        if hasattr(self, 'refresh_timer'):
            self.refresh_timer.stop()
            self.refresh_timer.start(self.refresh_interval)
    
    def create_header_section(self):
        """Create the header section for My Items page."""
        header_widget = QWidget()
        header_widget.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border-bottom: 2px solid #e2e8f0;
                padding: 0px;
            }
        """)
        
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(20, 20, 20, 20)
        header_layout.setSpacing(0)
        
        # Main title
        title_label = QLabel("My Items")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 28px;
                font-weight: 700;
                color: #1e293b;
                margin: 0px;
                padding: 0px;
            }
        """)
        header_layout.addWidget(title_label)
        
        return header_widget
    
    def create_category_section(self):
        """Create the category filter section."""
        section = QWidget()
        section.setStyleSheet("""
            QWidget {
                background-color: #f8fafc;
                border-radius: 12px;
                border: 1px solid #e2e8f0;
            }
        """)
        
        layout = QVBoxLayout(section)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)
        
        # Category buttons (removed the "Categories" title)
        categories_layout = QHBoxLayout()
        categories_layout.setSpacing(8)
        
        # Define categories with icons based on section
        if self.active_section == "my-items":
            categories = [
                ("All", "📋", "all"),
                ("Current Bids", "🔥", "current_bids"),
                ("Current Auctions", "⏰", "current_auctions"),
                ("Won Items", "🏆", "won_items"),
                ("Expired Auctions", "⏳", "expired_auctions")
            ]
        else:
            categories = [
                ("All", "🏪", "all"),
                ("Electronics", "📱", "electronics"),
                ("Collectibles", "🎨", "collectibles"),
                ("Fashion", "👕", "fashion"),
                ("Home & Garden", "🏠", "home"),
                ("Sports", "⚽", "sports"),
                ("Books", "📚", "books"),
                ("Other", "📦", "other")
            ]
        
        self.category_buttons = {}
        self.selected_category = "all"
        
        for name, icon, category_id in categories:
            btn = QPushButton(f"{icon} {name}")
            btn.setCheckable(True)
            btn.setChecked(category_id == "all")  # Default to "All"
            btn.setStyleSheet(self.get_category_button_style(category_id == "all"))
            btn.clicked.connect(lambda checked, cat=category_id: self.on_category_selected(cat))
            
            self.category_buttons[category_id] = btn
            categories_layout.addWidget(btn)
        
        # Add Item button for my-items section (inline with categories)
        if self.active_section == "my-items":
            # Add some spacing before the button
            categories_layout.addSpacing(20)
            
            # Add Item button
            add_item_btn = QPushButton("➕ Add Item")
            add_item_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3b82f6;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 20px;
                    font-weight: 600;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #2563eb;
                }
                QPushButton:pressed {
                    background-color: #1d4ed8;
                }
            """)
            add_item_btn.clicked.connect(self.show_add_item_dialog)
            categories_layout.addWidget(add_item_btn)
        
        categories_layout.addStretch()
        layout.addLayout(categories_layout)
        
        return section
    
    def get_category_button_style(self, is_selected=False):
        """Get style for category buttons."""
        if is_selected:
            return """
                QPushButton {
                    background-color: #3b82f6;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 20px;
                    font-size: 12px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #2563eb;
                }
            """
        else:
            return """
                QPushButton {
                    background-color: white;
                    color: #64748b;
                    border: 1px solid #e2e8f0;
                    padding: 8px 16px;
                    border-radius: 20px;
                    font-size: 12px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #f8fafc;
                    border-color: #cbd5e1;
                    color: #475569;
                }
                QPushButton:checked {
                    background-color: #3b82f6;
                    color: white;
                    border-color: #3b82f6;
                }
            """
    
    def on_category_selected(self, category_id):
        """Handle category selection."""
        # Update button styles
        for cat_id, btn in self.category_buttons.items():
            is_selected = cat_id == category_id
            btn.setChecked(is_selected)
            btn.setStyleSheet(self.get_category_button_style(is_selected))
        
        self.selected_category = category_id
        self.apply_filters()
    
    def create_partition_section(self, section_id, title, icon, description):
        """Create a partition section for my-items view."""
        section_widget = QWidget()
        section_widget.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                margin: 0px;
            }
        """)
        
        section_layout = QVBoxLayout(section_widget)
        section_layout.setContentsMargins(20, 16, 20, 16)
        section_layout.setSpacing(12)
        
        # Section header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)
        
        # Title with icon
        title_label = QLabel(f"{icon} {title}")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: 600;
                color: #1e293b;
                margin: 0px;
                padding: 0px;
            }
        """)
        header_layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel(description)
        desc_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #64748b;
                margin: 0px;
                padding: 0px;
            }
        """)
        header_layout.addWidget(desc_label)
        header_layout.addStretch()
        
        section_layout.addLayout(header_layout)
        
        # Items container
        items_container = QWidget()
        items_layout = QVBoxLayout(items_container)
        items_layout.setContentsMargins(0, 0, 0, 0)
        items_layout.setSpacing(8)
        
        # Store reference to items layout for adding items later
        setattr(section_widget, 'items_layout', items_layout)
        setattr(section_widget, 'section_id', section_id)
        
        # Empty state message
        empty_label = QLabel(f"No {title.lower()} found")
        empty_label.setStyleSheet("""
            QLabel {
                color: #94a3b8;
                font-size: 14px;
                font-style: italic;
                text-align: center;
                padding: 20px;
            }
        """)
        empty_label.setAlignment(Qt.AlignCenter)
        items_layout.addWidget(empty_label)
        setattr(section_widget, 'empty_label', empty_label)
        
        section_layout.addWidget(items_container)
        
        return section_widget
    
    def set_items(self, items: list):
        """Set the list of auction items."""
        self.items = items
        self.apply_filters()
    
    def apply_filters(self):
        """Apply current category filter."""
        if self.active_section == "my-items":
            # For my-items, organize into partitions
            self.organize_my_items()
        else:
            # Standard marketplace filtering
            # Start with all items
            filtered = self.items.copy()
            
            # Apply category filter
            if hasattr(self, 'selected_category') and self.selected_category != "all":
                filtered = [item for item in filtered 
                           if self.item_matches_category(item, self.selected_category)]
            
            # Sort by auction end time (active auctions first, then by end time)
            def sort_key(item):
                if item.status == 'active':
                    try:
                        if item.auction_end:
                            end_time = datetime.fromisoformat(item.auction_end.replace('Z', '+00:00'))
                            return (0, end_time)  # Active items first, sorted by end time
                        else:
                            return (0, datetime.max.replace(tzinfo=timezone.utc))  # Active items without end time
                    except:
                        return (0, datetime.max.replace(tzinfo=timezone.utc))
                else:
                    return (1, datetime.max.replace(tzinfo=timezone.utc))  # Non-active items last
            
            filtered.sort(key=sort_key)
            
            self.filtered_items = filtered
            self.update_display()
    
    def organize_my_items(self):
        """Organize items into partitions for my-items view."""
        if not hasattr(self, 'partition_sections'):
            return
        
        # Categorize items into partitions
        partitioned_items = {
            'current_bids': [],
            'current_auctions': [],
            'won_items': [],
            'sold_auctions': [],
            'expired_auctions': []
        }
        
        # Apply category filter first if not "all"
        items_to_organize = self.items.copy()
        if hasattr(self, 'selected_category') and self.selected_category != "all":
            if self.selected_category in partitioned_items:
                # If a specific partition is selected, only show that partition
                for section_id, section_widget in self.partition_sections.items():
                    if section_id == self.selected_category:
                        section_widget.setVisible(True)
                    else:
                        section_widget.setVisible(False)
            else:
                # Show all partitions
                for section_widget in self.partition_sections.values():
                    section_widget.setVisible(True)
        else:
            # Show all partitions
            for section_widget in self.partition_sections.values():
                section_widget.setVisible(True)
        
        # Categorize items based on their status and relationship to current user
        # Note: get_user_items() already returns items belonging to the current user
        for item in items_to_organize:
            item_status = getattr(item, 'status', '').lower()
            
            # Check if user is currently bidding on this item (items they don't own but are bidding on)
            if hasattr(item, 'user_is_bidding') and getattr(item, 'user_is_bidding', False):
                partitioned_items['current_bids'].append(item)
            # Check if user won this item (items they bid on and won)
            elif hasattr(item, 'winner_id') and hasattr(item, 'current_user_id') and getattr(item, 'winner_id') == getattr(item, 'current_user_id', None):
                partitioned_items['won_items'].append(item)
            # Items owned by current user (from get_user_items)
            elif item_status == 'active':
                partitioned_items['current_auctions'].append(item)
            # Check if this is a sold auction (completed with a winner)
            elif item_status in ['completed', 'sold'] and hasattr(item, 'winner_id') and getattr(item, 'winner_id'):
                partitioned_items['sold_auctions'].append(item)
            else:
                # Expired auctions (ended without a winner) or other statuses
                partitioned_items['expired_auctions'].append(item)
        
        # Update each partition section
        for section_id, items in partitioned_items.items():
            if section_id in self.partition_sections:
                self.update_partition_section(self.partition_sections[section_id], items)
        
        # Update status
        total_items = sum(len(items) for items in partitioned_items.values())
        self.status_label.setText(f"Showing {total_items} items across all categories")
    
    def update_partition_section(self, section_widget, items):
        """Update a partition section with items."""
        items_layout = section_widget.items_layout
        empty_label = section_widget.empty_label
        
        # Clear existing items (except empty label)
        for i in reversed(range(items_layout.count())):
            child = items_layout.itemAt(i).widget()
            if child and child != empty_label and isinstance(child, AuctionItemWidget):
                child.setParent(None)
        
        if items:
            # Hide empty label and add items
            empty_label.setVisible(False)
            
            for item in items:
                item_widget = AuctionItemWidget(item, active_section=self.active_section)
                item_widget.item_selected.connect(self.item_selected.emit)
                item_widget.bid_placed.connect(self.bid_placed.emit)
                items_layout.insertWidget(items_layout.count() - 1, item_widget)  # Insert before empty label
        else:
            # Show empty label
            empty_label.setVisible(True)
    
    def item_matches_category(self, item, category):
        """Check if an item matches the selected category."""
        item_category = (item.category or "").lower()
        
        category_mappings = {
            'electronics': ['electronics', 'tech', 'computer', 'phone', 'gadget'],
            'collectibles': ['collectible', 'antique', 'vintage', 'art', 'coin', 'card'],
            'fashion': ['fashion', 'clothing', 'apparel', 'shoes', 'accessory'],
            'home': ['home', 'garden', 'furniture', 'decor', 'kitchen'],
            'sports': ['sports', 'fitness', 'outdoor', 'athletic', 'exercise'],
            'books': ['book', 'literature', 'novel', 'textbook', 'magazine'],
            'other': []  # Will match items that don't fit other categories
        }
        
        if category in category_mappings:
            keywords = category_mappings[category]
            if not keywords:  # 'other' category
                # Check if item doesn't match any other category
                for other_cat, other_keywords in category_mappings.items():
                    if other_cat != 'other' and other_keywords:
                        if any(keyword in item_category for keyword in other_keywords):
                            return False
                return True
            else:
                return any(keyword in item_category for keyword in keywords)
        
        return False
    
    def update_display(self):
        """Update the display with filtered items using enhanced tiles."""
        # Skip grid layout for my-items as it uses partitioned sections
        if self.active_section == "my-items":
            return
        
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
    
    def show_add_item_dialog(self):
        """Show dialog to add a new item."""
        arweave_service = getattr(self, 'arweave_post_service', None)
        dialog = AddItemDialog(self, arweave_service)
        dialog.post_generated.connect(self.on_post_generated)
        if dialog.exec_() == QDialog.Accepted:
            # Refresh the items list after adding
            self.refresh_auctions()
    
    def on_post_generated(self, post_data, title):
        """Handle post generated by dialog."""
        self.arweave_post_generated.emit(post_data, title)


class AddItemDialog(QDialog):
    """Dialog for adding a new auction item."""
    
    post_generated = pyqtSignal(dict, str)  # post_data, auction_title
    
    def __init__(self, parent=None, arweave_post_service=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Item")
        self.setModal(True)
        self.resize(500, 600)
        self.wallet_data = None
        self.arweave_post_service = arweave_post_service
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the add item dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("Create New Auction")
        title.setFont(QFont('Arial', 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #2b7bba; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Form
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        # Item name
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter item name...")
        form_layout.addRow("Item Name*:", self.name_edit)
        
        # Description
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Describe your item...")
        self.description_edit.setMaximumHeight(100)
        form_layout.addRow("Description*:", self.description_edit)
        
        # Category
        self.category_combo = QComboBox()
        self.category_combo.addItems([
            "Electronics", "Collectibles", "Art", "Books", "Clothing", 
            "Home & Garden", "Sports", "Toys", "Other"
        ])
        form_layout.addRow("Category:", self.category_combo)
        
        # Starting price is now always zero - removed from UI
        # The starting price will be set to 0 automatically
        
        # Auction duration
        self.duration_combo = QComboBox()
        self.duration_combo.addItems([
            "1 hour", "3 hours", "6 hours", "12 hours", 
            "1 day", "3 days", "7 days", "14 days"
        ])
        self.duration_combo.setCurrentText("7 days")
        form_layout.addRow("Auction Duration:", self.duration_combo)
        
        # Tags
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("tag1, tag2, tag3...")
        form_layout.addRow("Tags:", self.tags_edit)
        
        layout.addLayout(form_layout)
        
        # Wallet generation section
        wallet_group = QGroupBox("Auction Wallet")
        wallet_layout = QVBoxLayout(wallet_group)
        
        # Generate wallet button
        self.generate_wallet_btn = QPushButton("Generate RSA and Wallet")
        self.generate_wallet_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                font-weight: 500;
                font-size: 12px;
                border: none;
                border-radius: 6px;
                padding: 10px 16px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
            QPushButton:pressed {
                background-color: #047857;
            }
            QPushButton:disabled {
                background-color: #9ca3af;
                color: #6b7280;
            }
        """)
        self.generate_wallet_btn.clicked.connect(self.generate_wallet_and_rsa)
        wallet_layout.addWidget(self.generate_wallet_btn)
        
        # Wallet address display (read-only)
        wallet_form_layout = QFormLayout()
        self.wallet_address_edit = QLineEdit()
        self.wallet_address_edit.setReadOnly(True)
        self.wallet_address_edit.setPlaceholderText("Wallet will be generated when you click the button above")
        self.wallet_address_edit.setStyleSheet("""
            QLineEdit {
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 4px;
                padding: 8px;
                color: #495057;
            }
        """)
        wallet_form_layout.addRow("Auction Wallet Address:", self.wallet_address_edit)
        
        # RSA fingerprint display (read-only)
        self.rsa_fingerprint_edit = QLineEdit()
        self.rsa_fingerprint_edit.setReadOnly(True)
        self.rsa_fingerprint_edit.setPlaceholderText("RSA fingerprint will be generated")
        self.rsa_fingerprint_edit.setStyleSheet("""
            QLineEdit {
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 4px;
                padding: 8px;
                color: #495057;
                font-family: monospace;
                font-size: 10px;
            }
        """)
        wallet_form_layout.addRow("RSA Fingerprint:", self.rsa_fingerprint_edit)
        
        wallet_layout.addLayout(wallet_form_layout)
        layout.addWidget(wallet_group)
        
        # Store wallet data
        self.wallet_data = None
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        self.create_btn = QPushButton("Create Auction")
        self.create_btn.setEnabled(False)  # Disabled until wallet is generated
        self.create_btn.setStyleSheet("""
            QPushButton:disabled {
                background-color: #e5e7eb;
                color: #9ca3af;
                border: 1px solid #d1d5db;
            }
            QPushButton:enabled {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
            }
            QPushButton:enabled:hover {
                background-color: #218838;
            }
            QPushButton:enabled:pressed {
                background-color: #1e7e34;
            }
        """)
        self.create_btn.clicked.connect(self.create_auction)
        button_layout.addWidget(self.create_btn)
        
        layout.addLayout(button_layout)
    
    def generate_wallet_and_rsa(self):
        """Generate wallet and RSA keys for the auction."""
        try:
            # Import the wallet generation utilities
            import asyncio
            import uuid
            from utils.auction_wallet_utils import generate_auction_wallet_and_rsa
            
            # Disable the button during generation
            self.generate_wallet_btn.setEnabled(False)
            self.generate_wallet_btn.setText("Generating...")
            
            # Generate a temporary auction ID for wallet generation
            temp_auction_id = str(uuid.uuid4())
            
            # For now, use a placeholder user ID (in real implementation, get from current user)
            user_id = "current_user_id"  # This should come from the current logged-in user
            
            # Create event loop if needed
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Generate wallet and RSA keys
            self.wallet_data = loop.run_until_complete(
                generate_auction_wallet_and_rsa(user_id, temp_auction_id)
            )
            
            if self.wallet_data and self.wallet_data.get('nano_address'):
                # Update UI with generated wallet info
                self.wallet_address_edit.setText(self.wallet_data['nano_address'])
                self.rsa_fingerprint_edit.setText(self.wallet_data['rsa_fingerprint'])
                
                # Enable the create auction button
                self.create_btn.setEnabled(True)
                
                # Update button text and style
                self.generate_wallet_btn.setText("✓ Wallet Generated")
                self.generate_wallet_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #059669;
                        color: white;
                        font-weight: 500;
                        font-size: 12px;
                        border: none;
                        border-radius: 6px;
                        padding: 10px 16px;
                        min-height: 20px;
                    }
                """)
                
                # Wallet generated successfully - no popup needed
            else:
                raise Exception("Failed to generate wallet data")
                
        except Exception as e:
            QMessageBox.critical(self, "Generation Failed", 
                               f"Failed to generate wallet and RSA keys:\n\n{str(e)}")
            
            # Re-enable the button
            self.generate_wallet_btn.setEnabled(True)
            self.generate_wallet_btn.setText("Generate RSA and Wallet")
    
    def create_auction(self):
        """Create the auction with the provided data."""
        # Validate required fields
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Item name is required.")
            return
        
        if not self.description_edit.toPlainText().strip():
            QMessageBox.warning(self, "Validation Error", "Description is required.")
            return
        
        # Check if wallet has been generated
        if not self.wallet_data:
            QMessageBox.warning(self, "Missing Wallet", "Please generate a wallet and RSA keys first.")
            return
        
        # Parse duration
        duration_text = self.duration_combo.currentText()
        duration_hours = self.parse_duration(duration_text)
        
        # Parse tags
        tags = [tag.strip() for tag in self.tags_edit.text().split(',') if tag.strip()]
        
        item_data = {
            'title': self.name_edit.text().strip(),
            'description': self.description_edit.toPlainText().strip(),
            'category': self.category_combo.currentText(),
            'starting_price_usdc': "0.0",
            'currency': "NANO",
            'auction_duration_hours': duration_hours,
            'tags': tags
        }
        
        # Add wallet and RSA data if available
        if self.wallet_data:
            item_data.update({
                'auction_nano_address': self.wallet_data.get('nano_address', ''),
                'auction_nano_public_key': self.wallet_data.get('nano_public_key', ''),
                'auction_nano_private_key': self.wallet_data.get('nano_private_key', ''),
                'auction_nano_seed': self.wallet_data.get('nano_seed', ''),
                'auction_rsa_private_key': self.wallet_data.get('rsa_private_key', ''),
                'auction_rsa_public_key': self.wallet_data.get('rsa_public_key', ''),
                'auction_rsa_fingerprint': self.wallet_data.get('rsa_fingerprint', ''),
                'auction_wallet_created_at': self.wallet_data.get('created_at', ''),
            })
        
        # Create auction using async worker
        from services.application_service import app_service
        
        self.create_btn.setEnabled(False)
        self.create_btn.setText("Creating...")
        
        worker = AsyncWorker(app_service.create_auction(item_data))
        worker.finished.connect(self.on_auction_created)
        worker.error.connect(self.on_creation_error)
        worker.start()
        self.worker = worker
    
    def parse_duration(self, duration_text):
        """Parse duration text to hours."""
        duration_map = {
            "1 hour": 1,
            "3 hours": 3,
            "6 hours": 6,
            "12 hours": 12,
            "1 day": 24,
            "3 days": 72,
            "7 days": 168,
            "14 days": 336
        }
        return duration_map.get(duration_text, 168)  # Default to 7 days
    
    def on_auction_created(self, result):
        """Handle successful auction creation."""
        success, message, item = result
        
        self.create_btn.setEnabled(True)
        self.create_btn.setText("Create Auction")
        
        if success:
            QMessageBox.information(self, "Success", f"Auction created successfully!\n\n{message}")
            
            print(f"[DEBUG] on_auction_created: arweave_post_service={self.arweave_post_service is not None}, item={item is not None}")
            if self.arweave_post_service and item:
                try:
                    import asyncio
                    from services.application_service import app_service
                    print(f"[DEBUG] Generating Arweave post for: {item.title}")
                    loop = asyncio.get_event_loop() if asyncio.get_event_loop().is_running() else asyncio.new_event_loop()
                    if not loop.is_running():
                        asyncio.set_event_loop(loop)
                    post_data = loop.run_until_complete(
                        self.arweave_post_service.create_auction_post(item, app_service.current_user)
                    )
                    print(f"[DEBUG] Post data generated: {post_data is not None}")
                    if post_data:
                        print(f"[DEBUG] Emitting post_generated signal")
                        self.post_generated.emit(post_data, item.title)
                    else:
                        print(f"[DEBUG] Post data is None - check arweave_post_service.create_auction_post")
                except Exception as e:
                    print(f"Error generating Arweave post: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"[DEBUG] Skipping post generation: arweave_post_service={self.arweave_post_service}, item={item}")
            
            self.accept()
        else:
            QMessageBox.warning(self, "Creation Failed", f"Failed to create auction:\n\n{message}")
    
    def on_creation_error(self, error):
        """Handle auction creation error."""
        self.create_btn.setEnabled(True)
        self.create_btn.setText("Create Auction")
        QMessageBox.critical(self, "Error", f"An error occurred while creating the auction:\n\n{str(error)}")


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
        
        self.title_label.setText(self.item.title or "Untitled")
        self.description_browser.setPlainText(self.item.description or "No description available")
        
        starting_price = self.item.starting_price_usdc or 0
        self.starting_price_label.setText(f"{starting_price} USDC")
        
        current_bid = self.item.current_bid_usdc or starting_price
        self.current_bid_label.setText(f"{current_bid} USDC")
        
        bid_count = 0
        self.bid_count_label.setText(str(bid_count))
        
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
        
        # Starting price is now always zero - removed from UI
        # The starting price will be set to 0 automatically
        
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
        
        # Wallet generation section
        wallet_group = QGroupBox("Auction Wallet")
        wallet_layout = QVBoxLayout(wallet_group)
        
        # Generate wallet button
        self.generate_wallet_btn = QPushButton("Generate RSA and Wallet")
        self.generate_wallet_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                font-weight: 500;
                font-size: 12px;
                border: none;
                border-radius: 6px;
                padding: 10px 16px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
            QPushButton:pressed {
                background-color: #047857;
            }
            QPushButton:disabled {
                background-color: #9ca3af;
                color: #6b7280;
            }
        """)
        self.generate_wallet_btn.clicked.connect(self.generate_wallet_and_rsa)
        wallet_layout.addWidget(self.generate_wallet_btn)
        
        # Wallet address display (read-only)
        wallet_form_layout = QFormLayout()
        self.wallet_address_edit = QLineEdit()
        self.wallet_address_edit.setReadOnly(True)
        self.wallet_address_edit.setPlaceholderText("Wallet will be generated when you click the button above")
        self.wallet_address_edit.setStyleSheet("""
            QLineEdit {
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 4px;
                padding: 8px;
                color: #495057;
            }
        """)
        wallet_form_layout.addRow("Auction Wallet Address:", self.wallet_address_edit)
        
        # RSA fingerprint display (read-only)
        self.rsa_fingerprint_edit = QLineEdit()
        self.rsa_fingerprint_edit.setReadOnly(True)
        self.rsa_fingerprint_edit.setPlaceholderText("RSA fingerprint will be generated")
        self.rsa_fingerprint_edit.setStyleSheet("""
            QLineEdit {
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 4px;
                padding: 8px;
                color: #495057;
                font-family: monospace;
                font-size: 10px;
            }
        """)
        wallet_form_layout.addRow("RSA Fingerprint:", self.rsa_fingerprint_edit)
        
        wallet_layout.addLayout(wallet_form_layout)
        layout.addWidget(wallet_group)
        
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
        self.create_auction_btn = button_box.button(QDialogButtonBox.Ok)
        self.create_auction_btn.setText("Create Auction")
        self.create_auction_btn.setEnabled(False)
        self.create_auction_btn.setStyleSheet("""
            QPushButton:disabled {
                background-color: #e5e7eb;
                color: #9ca3af;
                border: 1px solid #d1d5db;
            }
            QPushButton:enabled {
                background-color: #3b82f6;
                color: white;
                font-weight: 500;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:enabled:hover {
                background-color: #2563eb;
            }
        """)
        button_box.accepted.connect(self.create_auction)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Store wallet data
        self.wallet_data = None
        
        # Connect signals for live preview
        self.title_edit.textChanged.connect(self.update_preview)
        self.description_edit.textChanged.connect(self.update_preview)
        # Starting price is always 0, no need to connect signals
    
    def update_preview(self):
        """Update the auction preview."""
        title = self.title_edit.text() or "Untitled Auction"
        description = self.description_edit.toPlainText() or "No description"
        
        wallet_status = "Wallet Generated" if self.wallet_data else "Wallet Not Generated"
        wallet_color = "#10b981" if self.wallet_data else "#ef4444"
        
        preview_text = f"""
        <b>{title}</b><br>
        <i>{description[:100]}{'...' if len(description) > 100 else ''}</i><br><br>
        <b>Starting Price:</b> 0.00 (Always starts at zero)<br>
        <b>Wallet Status:</b> <span style="color: {wallet_color};">{wallet_status}</span><br>
        <b>Status:</b> {'Ready to create' if self.wallet_data else 'Generate wallet first'}
        """
        
        self.preview_label.setText(preview_text)
    
    def generate_wallet_and_rsa(self):
        """Generate wallet and RSA keys for the auction."""
        try:
            # Import the wallet generation utilities
            import asyncio
            import uuid
            from utils.auction_wallet_utils import generate_auction_wallet_and_rsa
            
            # Disable the button during generation
            self.generate_wallet_btn.setEnabled(False)
            self.generate_wallet_btn.setText("Generating...")
            
            # Generate a temporary auction ID for wallet generation
            temp_auction_id = str(uuid.uuid4())
            
            # For now, use a placeholder user ID (in real implementation, get from current user)
            user_id = "current_user_id"  # This should come from the current logged-in user
            
            # Create event loop if needed
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Generate wallet and RSA keys
            self.wallet_data = loop.run_until_complete(
                generate_auction_wallet_and_rsa(user_id, temp_auction_id)
            )
            
            if self.wallet_data and self.wallet_data.get('nano_address'):
                # Update UI with generated wallet info
                self.wallet_address_edit.setText(self.wallet_data['nano_address'])
                self.rsa_fingerprint_edit.setText(self.wallet_data['rsa_fingerprint'])
                
                # Enable the create auction button
                self.create_auction_btn.setEnabled(True)
                
                # Update button text and style
                self.generate_wallet_btn.setText("✓ Wallet Generated")
                self.generate_wallet_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #059669;
                        color: white;
                        font-weight: 500;
                        font-size: 12px;
                        border: none;
                        border-radius: 6px;
                        padding: 10px 16px;
                        min-height: 20px;
                    }
                """)
                
                # Update preview
                self.update_preview()
                
                QMessageBox.information(self, "Wallet Generated", 
                                      f"Auction wallet and RSA keys generated successfully!\n\n"
                                      f"Wallet Address: {self.wallet_data['nano_address'][:20]}...\n"
                                      f"RSA Fingerprint: {self.wallet_data['rsa_fingerprint'][:32]}...")
            else:
                raise Exception("Failed to generate wallet data")
                
        except Exception as e:
            QMessageBox.critical(self, "Generation Failed", 
                               f"Failed to generate wallet and RSA keys:\n\n{str(e)}")
            
            # Re-enable the button
            self.generate_wallet_btn.setEnabled(True)
            self.generate_wallet_btn.setText("Generate RSA and Wallet")
    
    def create_auction(self):
        """Validate and create the auction."""
        # Validate required fields
        if not self.title_edit.text().strip():
            QMessageBox.warning(self, "Missing Title", "Please enter an auction title.")
            return
        
        # Check if wallet has been generated
        if not self.wallet_data:
            QMessageBox.warning(self, "Missing Wallet", "Please generate a wallet and RSA keys first.")
            return
        
        # Validate tags
        tags = [tag.strip() for tag in self.tags_edit.text().split(',') if tag.strip()]
        if len(tags) > 10:
            QMessageBox.warning(self, "Too Many Tags", "Maximum 10 tags allowed.")
            return
        
        # Show confirmation
        reply = QMessageBox.question(self, "Create Auction", 
                                   "Create this auction?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.accept()
    
    def get_auction_data(self) -> dict:
        """Get auction data from form."""
        duration_hours = self.duration_spin.value()
        if self.duration_unit_combo.currentText() == "Days":
            duration_hours *= 24
        
        end_time = datetime.now(timezone.utc) + timedelta(hours=duration_hours)
        
        tags = [tag.strip() for tag in self.tags_edit.text().split(',') if tag.strip()]
        
        # Base auction data
        auction_data = {
            'title': self.title_edit.text().strip(),
            'description': self.description_edit.toPlainText().strip(),
            'starting_price_doge': "0.0",  # Always zero now
            'starting_price': 0.0,  # Always zero now
            'currency': "NANO",  # Default to NANO since we're generating NANO wallets
            'auction_end': end_time.isoformat(),
            'category': self.category_combo.currentText(),
            'tags': tags,
            'shipping_required': self.shipping_required_checkbox.isChecked(),
            'shipping_cost_doge': self.shipping_cost_edit.text() if self.shipping_required_checkbox.isChecked() else "0"
        }
        
        # Add wallet and RSA data if available
        if self.wallet_data:
            auction_data.update({
                'auction_nano_address': self.wallet_data.get('nano_address', ''),
                'auction_nano_public_key': self.wallet_data.get('nano_public_key', ''),
                'auction_nano_private_key': self.wallet_data.get('nano_private_key', ''),
                'auction_nano_seed': self.wallet_data.get('nano_seed', ''),
                'auction_rsa_private_key': self.wallet_data.get('rsa_private_key', ''),
                'auction_rsa_public_key': self.wallet_data.get('rsa_public_key', ''),
                'auction_rsa_fingerprint': self.wallet_data.get('rsa_fingerprint', ''),
                'auction_wallet_created_at': self.wallet_data.get('created_at', ''),
            })
        
        return auction_data