"""
Activity Widget for Sapphire Exchange.
Contains activity feed, user bid history, and leaderboards.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QPalette

from services.application_service import app_service
from utils.async_worker import AsyncWorker
from datetime import datetime, timedelta
import random


class ActivityFeedWidget(QWidget):
    """Widget for displaying global activity feed."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_timer()
        self.load_activity_data()
    
    def setup_ui(self):
        """Setup the activity feed UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Title
        title = QLabel("Global Activity Feed")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setStyleSheet("color: #1e293b; margin-bottom: 8px;")
        layout.addWidget(title)
        
        # Scroll area for activity items
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                background-color: #ffffff;
            }
            QScrollBar:vertical {
                background-color: #f1f5f9;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #cbd5e1;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #94a3b8;
            }
        """)
        
        # Content widget for scroll area
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(12, 12, 12, 12)
        self.content_layout.setSpacing(8)
        
        scroll_area.setWidget(self.content_widget)
        layout.addWidget(scroll_area)
    
    def setup_timer(self):
        """Setup timer for periodic updates."""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.load_activity_data)
        self.update_timer.start(30000)  # Update every 30 seconds
    
    def load_activity_data(self):
        """Load activity data."""
        # Clear existing items
        for i in reversed(range(self.content_layout.count())):
            child = self.content_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        # Generate sample activity data
        activities = self.generate_sample_activities()
        
        for activity in activities:
            activity_item = self.create_activity_item(activity)
            self.content_layout.addWidget(activity_item)
        
        # Add stretch to push items to top
        self.content_layout.addStretch()
    
    def generate_sample_activities(self):
        """Generate sample activity data."""
        activities = []
        event_types = [
            ("auction_created", "Auction Created", "#3b82f6"),
            ("bid_placed", "Bid Placed", "#10b981"),
            ("auction_won", "Auction Won", "#f59e0b"),
            ("item_sold", "Item Sold", "#8b5cf6"),
            ("user_joined", "User Joined", "#06b6d4")
        ]
        
        users = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace"]
        items = ["Vintage Watch", "Digital Art", "Rare Coin", "Gaming PC", "Antique Vase", "Sports Card"]
        
        for i in range(15):
            event_type, event_name, color = random.choice(event_types)
            user = random.choice(users)
            item = random.choice(items)
            timestamp = datetime.now() - timedelta(minutes=random.randint(1, 1440))
            
            if event_type == "auction_created":
                message = f"{user} created an auction for {item}"
            elif event_type == "bid_placed":
                amount = random.randint(10, 500)
                message = f"{user} placed a bid of ${amount} on {item}"
            elif event_type == "auction_won":
                amount = random.randint(50, 1000)
                message = f"{user} won {item} for ${amount}"
            elif event_type == "item_sold":
                amount = random.randint(100, 2000)
                message = f"{item} sold to {user} for ${amount}"
            else:
                message = f"{user} joined Sapphire Exchange"
            
            activities.append({
                "type": event_type,
                "name": event_name,
                "message": message,
                "timestamp": timestamp,
                "color": color
            })
        
        return sorted(activities, key=lambda x: x["timestamp"], reverse=True)
    
    def create_activity_item(self, activity):
        """Create an activity item widget."""
        item_widget = QFrame()
        item_widget.setStyleSheet("""
            QFrame {
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 4px;
                padding: 4px;
            }
            QFrame:hover {
                background-color: #f1f5f9;
            }
        """)
        item_widget.setFixedHeight(42)  # Increased by 10px
        
        layout = QHBoxLayout(item_widget)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        
        # Event type tag
        tag = QLabel(activity["name"])
        tag.setStyleSheet(f"""
            QLabel {{
                background-color: {activity["color"]};
                color: white;
                padding: 2px 6px;
                border-radius: 8px;
                font-size: 9px;
                font-weight: 500;
                min-width: 60px;
            }}
        """)
        tag.setAlignment(Qt.AlignCenter)
        tag.setFixedHeight(16)
        tag.setFixedWidth(70)
        layout.addWidget(tag)
        
        # Activity message
        message_label = QLabel(activity["message"])
        message_label.setStyleSheet("color: #374151; font-size: 10px;")
        message_label.setWordWrap(True)
        message_label.setMaximumHeight(24)  # Limit height to prevent overflow
        layout.addWidget(message_label, 1)
        
        # Timestamp
        time_str = self.format_timestamp(activity["timestamp"])
        time_label = QLabel(time_str)
        time_label.setStyleSheet("color: #6b7280; font-size: 9px;")
        time_label.setFixedWidth(50)
        layout.addWidget(time_label)
        
        return item_widget
    
    def format_timestamp(self, timestamp):
        """Format timestamp for display."""
        now = datetime.now()
        diff = now - timestamp
        
        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours}h ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes}m ago"
        else:
            return "Just now"


class UserBidHistoryWidget(QWidget):
    """Widget for displaying user's bid history."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_bid_history()
    
    def setup_ui(self):
        """Setup the bid history UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Title
        title = QLabel("My Bid History")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setStyleSheet("color: #1e293b; margin-bottom: 8px;")
        layout.addWidget(title)
        
        # Scroll area for bid items
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                background-color: #ffffff;
            }
            QScrollBar:vertical {
                background-color: #f1f5f9;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #cbd5e1;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #94a3b8;
            }
        """)
        
        # Content widget for scroll area
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(12, 12, 12, 12)
        self.content_layout.setSpacing(6)
        
        scroll_area.setWidget(self.content_widget)
        layout.addWidget(scroll_area)
    
    def load_bid_history(self):
        """Load user's bid history."""
        # Clear existing items
        for i in reversed(range(self.content_layout.count())):
            child = self.content_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        # Generate sample bid history
        bid_history = self.generate_sample_bid_history()
        
        for bid in bid_history:
            bid_item = self.create_bid_item(bid)
            self.content_layout.addWidget(bid_item)
        
        # Add stretch to push items to top
        self.content_layout.addStretch()
    
    def generate_sample_bid_history(self):
        """Generate sample bid history data."""
        items = ["Vintage Watch", "Digital Art", "Rare Coin", "Gaming PC", "Antique Vase"]
        statuses = ["Won", "Outbid", "Active"]
        
        history = []
        for i in range(10):
            item = random.choice(items)
            amount = random.randint(50, 500)
            status = random.choice(statuses)
            date = (datetime.now() - timedelta(days=random.randint(1, 30))).strftime("%m/%d/%Y")
            
            history.append({
                "item": item,
                "amount": amount,
                "status": status,
                "date": date
            })
        
        return history
    
    def create_bid_item(self, bid):
        """Create a bid history item widget."""
        item_widget = QFrame()
        item_widget.setStyleSheet("""
            QFrame {
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 4px;
                padding: 4px;
            }
            QFrame:hover {
                background-color: #f1f5f9;
            }
        """)
        item_widget.setFixedHeight(42)  # Increased by 10px to match activity items
        
        layout = QHBoxLayout(item_widget)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        
        # Status tag with color coding
        status_colors = {
            "Won": "#10b981",
            "Outbid": "#dc2626", 
            "Active": "#3b82f6"
        }
        
        status_tag = QLabel(bid["status"])
        status_tag.setStyleSheet(f"""
            QLabel {{
                background-color: {status_colors.get(bid["status"], "#6b7280")};
                color: white;
                padding: 2px 6px;
                border-radius: 8px;
                font-size: 9px;
                font-weight: 500;
                min-width: 40px;
            }}
        """)
        status_tag.setAlignment(Qt.AlignCenter)
        status_tag.setFixedHeight(16)
        status_tag.setFixedWidth(50)
        layout.addWidget(status_tag)
        
        # Item name
        item_label = QLabel(bid["item"])
        item_label.setStyleSheet("color: #374151; font-size: 11px; font-weight: 500;")
        layout.addWidget(item_label, 1)
        
        # Bid amount
        amount_label = QLabel(f"${bid['amount']}")
        amount_label.setStyleSheet("color: #6b7280; font-size: 11px;")
        amount_label.setFixedWidth(60)
        layout.addWidget(amount_label)
        
        # Date
        date_label = QLabel(bid["date"])
        date_label.setStyleSheet("color: #6b7280; font-size: 9px;")
        date_label.setFixedWidth(60)
        layout.addWidget(date_label)
        
        return item_widget


class LeaderboardWidget(QWidget):
    """Widget for displaying leaderboards."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_leaderboard_data()
    
    def setup_ui(self):
        """Setup the leaderboard UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Title
        title = QLabel("Leaderboards")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setStyleSheet("color: #1e293b; margin-bottom: 8px;")
        layout.addWidget(title)
        
        # Top Spender (single entry)
        self.top_spenders_group = self.create_leaderboard_group("Top Spender", "#3b82f6")
        self.top_spenders_group.setMaximumHeight(200)  # Increased for more spacing
        layout.addWidget(self.top_spenders_group)
        
        # Top Seller (single entry)
        self.top_sellers_group = self.create_leaderboard_group("Top Seller", "#10b981")
        self.top_sellers_group.setMaximumHeight(200)  # Increased for more spacing
        layout.addWidget(self.top_sellers_group)
        
        # Overall Rankings (Top 4)
        self.overall_rankings_group = self.create_leaderboard_group("Overall Rankings", "#f59e0b")
        self.overall_rankings_group.setMaximumHeight(380)  # Increased for 4 taller entries
        layout.addWidget(self.overall_rankings_group)
        
        # Add stretch
        layout.addStretch()
    
    def create_leaderboard_group(self, title, color):
        """Create a leaderboard group widget."""
        group = QGroupBox(title)
        group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                font-size: 14px;
                border: 2px solid {color};
                border-radius: 10px;
                margin-top: 16px;
                padding-top: 16px;
                color: {color};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px 0 8px;
            }}
        """)
        
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        return group
    
    def load_leaderboard_data(self):
        """Load leaderboard data."""
        # Generate sample data
        users = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry"]
        
        # Top Spender (single entry)
        top_spender_user = random.choice(users)
        top_spender_amount = random.randint(5000, 15000)
        spenders = [(top_spender_user, f"${top_spender_amount:,}")]
        
        self.populate_leaderboard(self.top_spenders_group, spenders, "#3b82f6", max_items=1)
        
        # Top Seller (single entry)
        top_seller_user = random.choice(users)
        top_seller_amount = random.randint(3000, 8000)
        sellers = [(top_seller_user, f"${top_seller_amount:,}")]
        
        self.populate_leaderboard(self.top_sellers_group, sellers, "#10b981", max_items=1)
        
        # Overall Rankings (Top 4)
        rankings = []
        for i in range(4):
            user = random.choice(users)
            score = random.randint(80, 100)
            rankings.append((user, f"{score}/100"))
        
        self.populate_leaderboard(self.overall_rankings_group, rankings, "#f59e0b", max_items=4)
    
    def populate_leaderboard(self, group, data, color, max_items=5):
        """Populate a leaderboard group with data."""
        layout = group.layout()
        
        # Clear existing items
        for i in reversed(range(layout.count())):
            child = layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        # Add leaderboard items
        for i, (name, value) in enumerate(data[:max_items]):
            item_widget = QFrame()
            item_widget.setStyleSheet("""
                QFrame {
                    background-color: #f8fafc;
                    border: 1px solid #e2e8f0;
                    border-radius: 6px;
                    padding: 8px;
                }
            """)
            item_widget.setMinimumHeight(70)  # Use minimum height instead of fixed
            item_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
            
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(8, 8, 8, 8)
            item_layout.setSpacing(10)
            
            # Rank
            rank_label = QLabel(f"#{i+1}")
            rank_label.setStyleSheet(f"""
                QLabel {{
                    background-color: {color};
                    color: white;
                    padding: 2px 6px;
                    border-radius: 10px;
                    font-size: 10px;
                    font-weight: bold;
                }}
            """)
            rank_label.setAlignment(Qt.AlignCenter)
            rank_label.setFixedSize(30, 24)
            rank_label.setScaledContents(False)
            item_layout.addWidget(rank_label)
            
            # Name
            name_label = QLabel(name)
            name_label.setStyleSheet("color: #374151; font-size: 12px; font-weight: 600;")
            name_label.setMinimumWidth(80)  # Reduced minimum width
            name_label.setAlignment(Qt.AlignVCenter)  # Vertically center the text
            name_label.setWordWrap(False)  # Prevent word wrapping
            item_layout.addWidget(name_label, 1)
            
            # Value
            value_label = QLabel(value)
            value_label.setStyleSheet("color: #6b7280; font-size: 11px; font-weight: 500;")
            value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)  # Right align and vertically center
            value_label.setMinimumWidth(70)  # Reduced minimum width
            value_label.setWordWrap(False)  # Prevent word wrapping
            item_layout.addWidget(value_label)
            
            layout.addWidget(item_widget)


class ActivityWidget(QWidget):
    """Main activity widget containing all activity components."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the activity widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Title only (no logo)
        title = QLabel("Activity & Leaderboards")
        title.setFont(QFont("Arial", 20, QFont.Bold))
        title.setStyleSheet("color: #1e293b; margin-bottom: 16px;")
        layout.addWidget(title)
        
        # Main content layout (60% left, 40% right)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        
        # Left column (60%) - Activity Feed and Bid History
        left_column = QWidget()
        left_column.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        left_layout = QVBoxLayout(left_column)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(16)
        
        # Activity Feed (takes more space)
        self.activity_feed = ActivityFeedWidget()
        left_layout.addWidget(self.activity_feed, 2)
        
        # User Bid History
        self.bid_history = UserBidHistoryWidget()
        left_layout.addWidget(self.bid_history, 1)
        
        content_layout.addWidget(left_column, 60)
        
        # Right column (40%) - Leaderboards
        self.leaderboard = LeaderboardWidget()
        self.leaderboard.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        content_layout.addWidget(self.leaderboard, 40)
        
        layout.addLayout(content_layout)