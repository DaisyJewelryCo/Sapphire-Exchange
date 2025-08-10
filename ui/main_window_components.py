"""
Main Window Components for Sapphire Exchange.
Contains reusable UI components for the main application window.
"""

import asyncio
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QListWidget, QListWidgetItem, QTextBrowser,
    QGridLayout, QButtonGroup, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor

from services.application_service import app_service
from utils.async_worker import AsyncWorker
from ui.logo_component import LogoComponent


class ActivityLogOverlay(QWidget):
    """Activity log overlay component."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.activity_history = []
        self.max_activities = 100
        self.setup_ui()
        self.add_initial_activities()
    
    def setup_ui(self):
        """Create the activity log overlay UI."""
        self.setVisible(False)
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 0.1);
                border-top: 1px solid #e2e8f0;
            }
        """)
        
        overlay_layout = QVBoxLayout(self)
        overlay_layout.setContentsMargins(16, 8, 16, 8)
        
        # Header
        header_layout = QHBoxLayout()
        activity_title = QLabel("Activity Log")
        activity_title.setStyleSheet("font-weight: 600; color: #1e293b;")
        header_layout.addWidget(activity_title)
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #64748b;
                border: none;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #1e293b;
                background-color: #f1f5f9;
                border-radius: 12px;
            }
        """)
        close_btn.clicked.connect(self.hide)
        header_layout.addWidget(close_btn)
        
        overlay_layout.addLayout(header_layout)
        
        # Activity list
        self.activity_list = QTextBrowser()
        self.activity_list.setMaximumHeight(80)
        self.activity_list.setStyleSheet("""
            QTextBrowser {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
            }
        """)
        overlay_layout.addWidget(self.activity_list)
    
    def add_initial_activities(self):
        """Add some initial activities to demonstrate the system."""
        base_time = datetime.now()
        
        activities = [
            (base_time - timedelta(minutes=5), "Application started", "info"),
            (base_time - timedelta(minutes=4), "Connecting to Arweave network", "connecting"),
            (base_time - timedelta(minutes=3), "Connected to Nano node", "success"),
            (base_time - timedelta(minutes=2), "Wallet initialized", "success"),
            (base_time - timedelta(minutes=1), "Ready for trading", "info"),
        ]
        
        for timestamp, message, activity_type in activities:
            self.add_activity(message, activity_type, timestamp)
    
    def add_activity(self, message, activity_type="info", timestamp=None):
        """Add an activity to the log."""
        if timestamp is None:
            timestamp = datetime.now()
        
        activity = {
            'timestamp': timestamp,
            'message': message,
            'type': activity_type
        }
        
        self.activity_history.append(activity)
        
        # Keep only the most recent activities
        if len(self.activity_history) > self.max_activities:
            self.activity_history = self.activity_history[-self.max_activities:]
        
        self.update_activity_log_content()
    
    def update_activity_log_content(self):
        """Update the activity log content display."""
        if not hasattr(self, 'activity_list'):
            return
        
        # Build HTML content for the activity log
        html_content = []
        
        # Show most recent activities first
        recent_activities = sorted(self.activity_history, key=lambda x: x['timestamp'], reverse=True)[:20]
        
        for activity in recent_activities:
            timestamp_str = activity['timestamp'].strftime("%H:%M:%S")
            message = activity['message']
            activity_type = activity['type']
            
            # Color coding based on activity type
            color_map = {
                'bid': '#3b82f6',      # Blue
                'connecting': '#f59e0b', # Amber
                'update': '#10b981',    # Emerald
                'error': '#ef4444',     # Red
                'success': '#22c55e',   # Green
                'info': '#6b7280'       # Gray
            }
            
            color = color_map.get(activity_type, '#6b7280')
            
            html_content.append(f"""
                <div style="margin-bottom: 4px; padding: 2px 0;">
                    <span style="color: #9ca3af; font-size: 10px;">{timestamp_str}</span>
                    <span style="color: {color}; font-weight: 500; margin-left: 8px;">[{activity_type.upper()}]</span>
                    <span style="color: #374151; margin-left: 4px;">{message}</span>
                </div>
            """)
        
        self.activity_list.setHtml("".join(html_content))


class StatusPopup(QWidget):
    """Status popup for detailed connection information."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.wallet_status_indicators = {}
        self.setup_ui()
        self.setVisible(False)
    
    def setup_ui(self):
        """Create the status popup UI."""
        self.setFixedSize(320, 240)
        self.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Title
        title = QLabel("Connection Status")
        title.setFont(QFont('Arial', 14, QFont.Bold))
        title.setStyleSheet("color: #1e293b; margin-bottom: 8px;")
        layout.addWidget(title)
        
        # Overall status
        self.overall_status_label = QLabel("Overall Status: Checking...")
        self.overall_status_label.setStyleSheet("color: #64748b; font-weight: 500; margin-bottom: 12px;")
        layout.addWidget(self.overall_status_label)
        
        # Service status indicators
        services = [
            ("arweave", "Arweave Network"),
            ("nano", "Nano Network"),
            ("doge", "Dogecoin Network")
        ]
        
        for service_id, service_name in services:
            service_container = QWidget()
            service_layout = QHBoxLayout(service_container)
            service_layout.setContentsMargins(0, 0, 0, 0)
            service_layout.setSpacing(8)
            
            # Status dot
            dot = QLabel("●")
            dot.setStyleSheet("font-size: 14px; color: #ef4444;")  # Red by default
            
            # Service name
            name_label = QLabel(service_name)
            name_label.setStyleSheet("color: #374151; font-weight: 500;")
            
            # Status text
            status_label = QLabel("Disconnected")
            status_label.setStyleSheet("color: #6b7280; font-size: 12px;")
            
            service_layout.addWidget(dot)
            service_layout.addWidget(name_label)
            service_layout.addStretch()
            service_layout.addWidget(status_label)
            
            # Store references
            self.wallet_status_indicators[service_id] = {
                'container': service_container,
                'dot': dot,
                'name': name_label,
                'status': status_label
            }
            
            layout.addWidget(service_container)
        
        layout.addStretch()
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #f1f5f9;
                color: #374151;
                border: 1px solid #d1d5db;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #e2e8f0;
            }
        """)
        close_btn.clicked.connect(self.hide)
        layout.addWidget(close_btn)
    
    def update_service_status(self, service_id, is_connected, status_text=""):
        """Update the status of a specific service."""
        if service_id not in self.wallet_status_indicators:
            return
        
        indicators = self.wallet_status_indicators[service_id]
        
        if is_connected:
            color = "#22c55e"  # Green
            status = status_text or "Connected"
        else:
            color = "#ef4444"  # Red
            status = status_text or "Disconnected"
        
        indicators['dot'].setStyleSheet(f"font-size: 14px; color: {color};")
        indicators['status'].setText(status)
        indicators['status'].setStyleSheet(f"color: {color}; font-size: 12px;")


class UserProfileSection(QWidget):
    """User profile section for sidebar."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the user profile section UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # User info container with better styling
        user_info_container = QWidget()
        user_info_container.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        user_info_layout = QVBoxLayout(user_info_container)
        user_info_layout.setContentsMargins(12, 12, 12, 12)
        user_info_layout.setSpacing(8)
        
        # User avatar and name row
        user_row = QWidget()
        user_row_layout = QHBoxLayout(user_row)
        user_row_layout.setContentsMargins(0, 0, 0, 0)
        user_row_layout.setSpacing(12)
        
        self.user_avatar = QLabel("👤")
        self.user_avatar.setFixedSize(48, 48)
        self.user_avatar.setAlignment(Qt.AlignCenter)
        self.user_avatar.setStyleSheet("""
            QLabel {
                background-color: #f1f5f9;
                border: 2px solid #e2e8f0;
                border-radius: 24px;
                font-size: 24px;
                color: #64748b;
            }
        """)
        user_row_layout.addWidget(self.user_avatar)
        
        # User details column
        user_details = QWidget()
        user_details_layout = QVBoxLayout(user_details)
        user_details_layout.setContentsMargins(0, 0, 0, 0)
        user_details_layout.setSpacing(2)
        
        # User name
        self.username_label = QLabel("User Name")
        self.username_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: 600;
                color: #1e293b;
                background-color: transparent;
                border: none;
                padding: 0;
            }
        """)
        user_details_layout.addWidget(self.username_label)
        

        
        user_row_layout.addWidget(user_details, 1)
        user_info_layout.addWidget(user_row)
        
        # Bid credits with better styling
        self.bid_credits_label = QLabel("Available Bid Credits: $0.00")
        self.bid_credits_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                font-weight: 500;
                color: #059669;
                background-color: #ecfdf5;
                border: 1px solid #d1fae5;
                border-radius: 6px;
                padding: 6px 8px;
                margin-top: 4px;
            }
        """)
        user_info_layout.addWidget(self.bid_credits_label)
        
        layout.addWidget(user_info_container)
        
        # Wallet balances with improved styling
        balances_container = QWidget()
        balances_container.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        balances_layout = QVBoxLayout(balances_container)
        balances_layout.setContentsMargins(12, 12, 12, 12)
        balances_layout.setSpacing(8)
        
        balances_title = QLabel("Wallet Balances")
        balances_title.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: 600;
                color: #374151;
                background-color: transparent;
                border: none;
                padding: 0 0 4px 0;
            }
        """)
        balances_layout.addWidget(balances_title)
        
        # Balance items in horizontal layout with wallet type headers and values underneath
        balances_horizontal_layout = QHBoxLayout()
        balances_horizontal_layout.setSpacing(0)
        
        # NANO wallet section
        nano_container = QWidget()
        nano_layout = QVBoxLayout(nano_container)
        nano_layout.setContentsMargins(8, 4, 8, 4)
        nano_layout.setSpacing(2)
        
        nano_header = QLabel("NANO")
        nano_header.setAlignment(Qt.AlignCenter)
        nano_header.setStyleSheet("""
            QLabel {
                font-size: 11px;
                font-weight: 600;
                color: #374151;
                background-color: transparent;
                border: none;
                padding: 0;
            }
        """)
        nano_layout.addWidget(nano_header)
        
        self.nano_balance_label = QLabel("$0.00")
        self.nano_balance_label.setAlignment(Qt.AlignCenter)
        self.nano_balance_label.setStyleSheet("""
            QLabel {
                font-size: 10px;
                color: #1e293b;
                background-color: transparent;
                border: none;
                padding: 0;
            }
        """)
        nano_layout.addWidget(self.nano_balance_label)
        
        balances_horizontal_layout.addWidget(nano_container)
        
        # DOGE wallet section
        doge_container = QWidget()
        doge_layout = QVBoxLayout(doge_container)
        doge_layout.setContentsMargins(8, 4, 8, 4)
        doge_layout.setSpacing(2)
        
        doge_header = QLabel("DOGE")
        doge_header.setAlignment(Qt.AlignCenter)
        doge_header.setStyleSheet("""
            QLabel {
                font-size: 11px;
                font-weight: 600;
                color: #374151;
                background-color: transparent;
                border: none;
                padding: 0;
            }
        """)
        doge_layout.addWidget(doge_header)
        
        self.doge_balance_label = QLabel("0.00")
        self.doge_balance_label.setAlignment(Qt.AlignCenter)
        self.doge_balance_label.setStyleSheet("""
            QLabel {
                font-size: 10px;
                color: #1e293b;
                background-color: transparent;
                border: none;
                padding: 0;
            }
        """)
        doge_layout.addWidget(self.doge_balance_label)
        
        balances_horizontal_layout.addWidget(doge_container)
        
        # AR wallet section
        ar_container = QWidget()
        ar_layout = QVBoxLayout(ar_container)
        ar_layout.setContentsMargins(8, 4, 8, 4)
        ar_layout.setSpacing(2)
        
        ar_header = QLabel("AR")
        ar_header.setAlignment(Qt.AlignCenter)
        ar_header.setStyleSheet("""
            QLabel {
                font-size: 11px;
                font-weight: 600;
                color: #374151;
                background-color: transparent;
                border: none;
                padding: 0;
            }
        """)
        ar_layout.addWidget(ar_header)
        
        self.ar_balance_label = QLabel("0.00")
        self.ar_balance_label.setAlignment(Qt.AlignCenter)
        self.ar_balance_label.setStyleSheet("""
            QLabel {
                font-size: 10px;
                color: #1e293b;
                background-color: transparent;
                border: none;
                padding: 0;
            }
        """)
        ar_layout.addWidget(self.ar_balance_label)
        
        balances_horizontal_layout.addWidget(ar_container)
        
        balances_layout.addLayout(balances_horizontal_layout)
        
        layout.addWidget(balances_container)
    
    def update_user_info(self, user):
        """Update user information display."""
        print(f"[DEBUG] UserProfileSection.update_user_info called with user: {user.username if user else None}")
        if user:
            print(f"[DEBUG] Updating username label to: {user.username}")
            self.username_label.setText(user.username or "User")
            
            self.bid_credits_label.setText(f"Available Bid Credits: ${user.bid_credits:.2f}")
            print(f"[DEBUG] UserProfileSection update completed")
    
    def update_balances(self, balances):
        """Update balance display."""
        print(f"[DEBUG] UserProfileSection.update_balances called with: {balances}")
        nano_balance = balances.get('nano', 0) or 0
        doge_balance = balances.get('dogecoin', 0) or 0
        ar_balance = balances.get('arweave', 0) or 0
        
        print(f"[DEBUG] Parsed balances - NANO: {nano_balance}, DOGE: {doge_balance}, AR: {ar_balance}")
        
        # Format balances for inline display (values only, no currency prefix)
        self.nano_balance_label.setText(f"${self.format_balance(nano_balance)}")
        self.doge_balance_label.setText(self.format_balance(doge_balance))
        self.ar_balance_label.setText(self.format_balance(ar_balance))
        
        print(f"[DEBUG] Balance labels updated")
    
    def format_balance(self, balance):
        """Format balance for compact display."""
        if balance == 0:
            return "0"
        elif balance < 0.01:
            return f"{balance:.4f}"
        elif balance < 1:
            return f"{balance:.3f}"
        elif balance < 100:
            return f"{balance:.2f}"
        else:
            return f"{balance:.1f}"


class NavigationSidebar(QWidget):
    """Navigation sidebar component."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.nav_button_group = QButtonGroup()
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the navigation sidebar UI."""
        self.setFixedWidth(256)  # w-64 = 256px
        self.setStyleSheet("""
            QWidget {
                background-color: #f8fafc;
                border-right: 1px solid #e2e8f0;
            }
            QPushButton {
                background-color: transparent;
                color: #64748b;
                border: none;
                padding: 12px 16px;
                text-align: left;
                font-size: 14px;
                font-weight: 500;
                border-radius: 6px;
                margin: 2px 8px;
            }
            QPushButton:hover {
                background-color: #f1f5f9;
                color: #1e293b;
            }
            QPushButton:checked {
                background-color: #000000;
                color: #ffffff;
            }
        """)
        
        # Create sidebar layout
        self.sidebar_layout = QVBoxLayout(self)
        self.sidebar_layout.setContentsMargins(0, 16, 0, 16)
        self.sidebar_layout.setSpacing(8)
        
        # Add logo at the top
        logo_container = QWidget()
        logo_container.setFixedHeight(40)  # Fixed height to prevent expansion
        logo_layout = QHBoxLayout(logo_container)
        logo_layout.setContentsMargins(12, 4, 12, 4)
        
        self.logo = LogoComponent(size="small", clickable=True, compact=True)
        # Connect logo click to navigate to marketplace (home)
        self.logo.logo_clicked.connect(lambda: self.nav_button_group.button(0).click() if self.nav_button_group.button(0) else None)
        # Set a maximum width for the logo to prevent it from being cut off
        self.logo.setMaximumWidth(140)
        # Set size policy to prevent expansion
        from PyQt5.QtWidgets import QSizePolicy
        self.logo.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        logo_layout.addWidget(self.logo)
        # Remove stretch to keep logo compact
        
        self.sidebar_layout.addWidget(logo_container)
        
        # Add separator after logo
        logo_separator = QLabel()
        logo_separator.setFixedHeight(1)
        logo_separator.setStyleSheet("QLabel { background-color: #e2e8f0; margin: 8px 16px; padding: 0; }")
        self.sidebar_layout.addWidget(logo_separator)
        
        # User profile section
        self.user_profile_section = UserProfileSection()
        self.sidebar_layout.addWidget(self.user_profile_section)
        
        # Add separator
        separator = QLabel()
        separator.setFixedHeight(1)
        separator.setStyleSheet("QLabel { background-color: #e2e8f0; margin: 16px; padding: 0; }")
        self.sidebar_layout.addWidget(separator)
        
        # Navigation buttons
        self.nav_buttons = {
            "marketplace_btn": {
                "text": "🛍️  Marketplace",
                "page_id": 0,
                "icon": "Gavel"
            },
            "my_items_btn": {
                "text": "📦  My Items", 
                "page_id": 1,
                "icon": "Package"
            },
            "activity_btn": {
                "text": "📈  Activity",
                "page_id": 2,
                "icon": "Activity"
            },
            "dashboard_btn": {
                "text": "📊  Dashboard",
                "page_id": 3,
                "icon": "LayoutDashboard"
            },
            "dev_tools_btn": {
                "text": "🔧  Dev Tools",
                "page_id": 4,
                "icon": "Settings"
            }
        }
        
        # Create navigation buttons
        for btn_name, btn_data in self.nav_buttons.items():
            btn = QPushButton(btn_data["text"])
            btn.setCheckable(True)
            self.nav_button_group.addButton(btn, btn_data["page_id"])
            setattr(self, btn_name, btn)  # Store reference to button
            self.sidebar_layout.addWidget(btn)
        
        # Add spacer
        self.sidebar_layout.addStretch(1)
    
    def set_active_page(self, page_id):
        """Set the active page in navigation."""
        button = self.nav_button_group.button(page_id)
        if button:
            button.setChecked(True)