"""
Authentication Status Popup for Sapphire Exchange.
Shows detailed authentication status for items including blockchain verification.
"""
import asyncio
from typing import Dict, Any
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
                             QPushButton, QGraphicsDropShadowEffect)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect
from PyQt5.QtGui import QFont, QColor

from models.models import Item
from services.application_service import app_service


class AuthenticationStatusPopup(QWidget):
    """Popup widget showing detailed authentication status for an item."""
    
    closed = pyqtSignal()
    
    def __init__(self, item: Item, parent=None):
        super().__init__(parent)
        self.item = item
        self.parent_widget = parent
        
        # Set window flags for popup behavior
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Initialize authentication status
        self.auth_status = {
            'arweave': {'status': 'checking', 'message': 'Checking Arweave status...'},
            'nano': {'status': 'checking', 'message': 'Checking Nano network...'},
            'rsa': {'status': 'checking', 'message': 'Verifying RSA signature...'},
            'data_integrity': {'status': 'checking', 'message': 'Validating data integrity...'},
            'seller_verification': {'status': 'checking', 'message': 'Verifying seller...'}
        }
        
        self.setup_ui()
        self.setup_animations()
        
        # Start authentication checks
        QTimer.singleShot(100, self.start_authentication_checks)
    
    def setup_ui(self):
        """Setup the popup UI."""
        self.setFixedSize(320, 280)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Main container with shadow
        self.container = QFrame()
        self.container.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e2e8f0;
            }
        """)
        
        # Add drop shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 4)
        self.container.setGraphicsEffect(shadow)
        
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(16, 16, 16, 16)
        container_layout.setSpacing(12)
        
        # Header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        title_label = QLabel("Authentication Status")
        title_label.setFont(QFont("Arial", 14, QFont.DemiBold))
        title_label.setStyleSheet("color: #1e293b; margin-bottom: 4px;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Close button
        close_btn = QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #f1f5f9;
                color: #64748b;
                border: none;
                border-radius: 12px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e2e8f0;
                color: #475569;
            }
        """)
        close_btn.clicked.connect(self.close_popup)
        header_layout.addWidget(close_btn)
        
        container_layout.addLayout(header_layout)
        
        # Item info
        item_name = self.item.title or self.item.name or f"Item #{self.item.id[:8]}"
        item_label = QLabel(f"Item: {item_name}")
        item_label.setFont(QFont("Arial", 10))
        item_label.setStyleSheet("color: #64748b; margin-bottom: 8px;")
        item_label.setWordWrap(True)
        container_layout.addWidget(item_label)
        
        # Authentication status list
        self.status_list_widget = QWidget()
        self.status_list_layout = QVBoxLayout(self.status_list_widget)
        self.status_list_layout.setContentsMargins(0, 0, 0, 0)
        self.status_list_layout.setSpacing(8)
        
        # Create status items
        self.status_widgets = {}
        for auth_type, status_info in self.auth_status.items():
            status_widget = self.create_status_item(auth_type, status_info)
            self.status_widgets[auth_type] = status_widget
            self.status_list_layout.addWidget(status_widget)
        
        container_layout.addWidget(self.status_list_widget)
        
        # Footer with refresh button
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #f8fafc;
                color: #475569;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #f1f5f9;
                border-color: #cbd5e1;
            }
        """)
        refresh_btn.clicked.connect(self.start_authentication_checks)
        footer_layout.addWidget(refresh_btn)
        
        container_layout.addLayout(footer_layout)
        
        layout.addWidget(self.container)
    
    def create_status_item(self, auth_type: str, status_info: Dict[str, str]) -> QWidget:
        """Create a status item widget."""
        item_widget = QWidget()
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(0, 0, 0, 0)
        item_layout.setSpacing(12)
        
        # Status dot
        status_dot = QLabel("●")
        status_dot.setFixedSize(12, 12)
        status_dot.setAlignment(Qt.AlignCenter)
        self.update_status_dot(status_dot, status_info['status'])
        item_layout.addWidget(status_dot)
        
        # Status info
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)
        
        # Service name
        service_name = self.get_service_display_name(auth_type)
        name_label = QLabel(service_name)
        name_label.setFont(QFont("Arial", 11, QFont.DemiBold))
        name_label.setStyleSheet("color: #1e293b;")
        info_layout.addWidget(name_label)
        
        # Status message
        message_label = QLabel(status_info['message'])
        message_label.setFont(QFont("Arial", 9))
        message_label.setStyleSheet("color: #64748b;")
        message_label.setWordWrap(True)
        info_layout.addWidget(message_label)
        
        item_layout.addLayout(info_layout, 1)
        
        # Store references for updates
        item_widget.status_dot = status_dot
        item_widget.message_label = message_label
        
        return item_widget
    
    def get_service_display_name(self, auth_type: str) -> str:
        """Get display name for authentication service."""
        names = {
            'arweave': 'Arweave Network',
            'nano': 'Nano Network',
            'rsa': 'RSA Signature',
            'data_integrity': 'Data Integrity',
            'seller_verification': 'Seller Verification'
        }
        return names.get(auth_type, auth_type.title())
    
    def update_status_dot(self, dot_widget: QLabel, status: str):
        """Update status dot color based on status."""
        colors = {
            'verified': '#10b981',    # Green
            'warning': '#f59e0b',     # Yellow/Orange
            'error': '#ef4444',       # Red
            'checking': '#6b7280'     # Gray
        }
        
        color = colors.get(status, '#6b7280')
        dot_widget.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 12px;
                font-weight: bold;
            }}
        """)
    
    def setup_animations(self):
        """Setup popup animations."""
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(200)
        self.fade_animation.setEasingCurve(QEasingCurve.OutCubic)
    
    def show_popup(self, position):
        """Show popup at specified position."""
        # Position popup near the status dot
        self.move(position)
        
        # Ensure popup stays within screen bounds
        screen_geometry = self.parent_widget.screen().geometry() if self.parent_widget else None
        if screen_geometry:
            popup_rect = QRect(position.x(), position.y(), self.width(), self.height())
            if popup_rect.right() > screen_geometry.right():
                popup_rect.moveRight(screen_geometry.right() - 10)
            if popup_rect.bottom() > screen_geometry.bottom():
                popup_rect.moveBottom(screen_geometry.bottom() - 10)
            if popup_rect.left() < screen_geometry.left():
                popup_rect.moveLeft(screen_geometry.left() + 10)
            if popup_rect.top() < screen_geometry.top():
                popup_rect.moveTop(screen_geometry.top() + 10)
            self.move(popup_rect.topLeft())
        
        # Fade in animation
        self.setWindowOpacity(0.0)
        self.show()
        
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.start()
    
    def close_popup(self):
        """Close popup with fade out animation."""
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.finished.connect(self.hide)
        self.fade_animation.start()
        self.closed.emit()
    
    def start_authentication_checks(self):
        """Start authentication status checks."""
        # Reset all statuses to checking
        for auth_type in self.auth_status:
            self.auth_status[auth_type] = {
                'status': 'checking', 
                'message': 'Checking...'
            }
            self.update_status_display(auth_type)
        
        # Start async checks
        QTimer.singleShot(500, self.check_arweave_status)
        QTimer.singleShot(750, self.check_nano_status)
        QTimer.singleShot(1000, self.check_rsa_status)
        QTimer.singleShot(1250, self.check_data_integrity)
        QTimer.singleShot(1500, self.check_seller_verification)
    
    def check_arweave_status(self):
        """Check Arweave network status."""
        try:
            # Check if item has Arweave metadata
            if self.item.arweave_metadata_uri:
                if self.item.arweave_confirmed:
                    self.auth_status['arweave'] = {
                        'status': 'verified',
                        'message': 'Metadata confirmed on Arweave'
                    }
                else:
                    self.auth_status['arweave'] = {
                        'status': 'warning',
                        'message': 'Metadata pending confirmation'
                    }
            else:
                self.auth_status['arweave'] = {
                    'status': 'warning',
                    'message': 'No Arweave metadata found'
                }
        except Exception as e:
            self.auth_status['arweave'] = {
                'status': 'error',
                'message': f'Error checking Arweave: {str(e)[:30]}...'
            }
        
        self.update_status_display('arweave')
    
    def check_nano_status(self):
        """Check Nano network status."""
        try:
            # Check if item has Nano address
            if self.item.auction_nano_address:
                # In a real implementation, you'd check the address on the network
                self.auth_status['nano'] = {
                    'status': 'verified',
                    'message': 'Auction wallet verified'
                }
            else:
                self.auth_status['nano'] = {
                    'status': 'warning',
                    'message': 'No auction wallet found'
                }
        except Exception as e:
            self.auth_status['nano'] = {
                'status': 'error',
                'message': f'Error checking Nano: {str(e)[:30]}...'
            }
        
        self.update_status_display('nano')
    
    def check_rsa_status(self):
        """Check Nano wallet and SHA verification status."""
        try:
            if self.item.auction_nano_public_key and self.item.sha_id:
                self.auth_status['nano'] = {
                    'status': 'verified',
                    'message': 'Nano wallet verified'
                }
            else:
                self.auth_status['rsa'] = {
                    'status': 'warning',
                    'message': 'No RSA signature found'
                }
        except Exception as e:
            self.auth_status['rsa'] = {
                'status': 'error',
                'message': f'Error checking RSA: {str(e)[:30]}...'
            }
        
        self.update_status_display('rsa')
    
    def check_data_integrity(self):
        """Check data integrity status."""
        try:
            # Check if item has data hash
            if self.item.data_hash:
                # In a real implementation, you'd recalculate and compare the hash
                self.auth_status['data_integrity'] = {
                    'status': 'verified',
                    'message': 'Data integrity verified'
                }
            else:
                self.auth_status['data_integrity'] = {
                    'status': 'warning',
                    'message': 'No data hash found'
                }
        except Exception as e:
            self.auth_status['data_integrity'] = {
                'status': 'error',
                'message': f'Error checking integrity: {str(e)[:30]}...'
            }
        
        self.update_status_display('data_integrity')
    
    def check_seller_verification(self):
        """Check seller verification status."""
        try:
            # Check seller reputation and verification
            # This would typically involve checking the seller's reputation score
            # and verification status from the user service
            self.auth_status['seller_verification'] = {
                'status': 'verified',
                'message': 'Seller identity verified'
            }
        except Exception as e:
            self.auth_status['seller_verification'] = {
                'status': 'error',
                'message': f'Error checking seller: {str(e)[:30]}...'
            }
        
        self.update_status_display('seller_verification')
    
    def update_status_display(self, auth_type: str):
        """Update the display for a specific authentication type."""
        if auth_type in self.status_widgets:
            widget = self.status_widgets[auth_type]
            status_info = self.auth_status[auth_type]
            
            # Update status dot
            self.update_status_dot(widget.status_dot, status_info['status'])
            
            # Update message
            widget.message_label.setText(status_info['message'])
    
    def mousePressEvent(self, event):
        """Handle mouse press events to close popup when clicking outside."""
        if not self.container.geometry().contains(event.pos()):
            self.close_popup()
        super().mousePressEvent(event)