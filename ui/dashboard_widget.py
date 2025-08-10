"""
Dashboard Widget for Sapphire Exchange.
Contains user profile management and wallet overview with transaction history.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QFrame, QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QGroupBox, QSizePolicy, QSpacerItem, QApplication,
    QSlider, QSpinBox
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QPalette

from services.application_service import app_service
from utils.async_worker import AsyncWorker


class BidSettingsWidget(QWidget):
    """Widget for bid settings including max bid and bid increment."""
    
    refresh_interval_changed = pyqtSignal(int)  # Signal when refresh interval changes
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the bid settings UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)
        
        # Max Bid section
        max_bid_layout = QVBoxLayout()
        max_bid_layout.setSpacing(6)
        
        max_bid_label = QLabel("Max Bid:")
        max_bid_label.setStyleSheet("color: #374151; font-size: 12px; font-weight: 500;")
        max_bid_layout.addWidget(max_bid_label)
        
        # Max bid slider and value display
        max_bid_control_layout = QHBoxLayout()
        max_bid_control_layout.setSpacing(8)
        
        self.max_bid_slider = QSlider(Qt.Horizontal)
        self.max_bid_slider.setMinimum(1)  # $0.01
        self.max_bid_slider.setMaximum(2000)  # $20.00
        self.max_bid_slider.setValue(500)  # Default $5.00
        self.max_bid_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #d1d5db;
                height: 6px;
                background: #f3f4f6;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #3b82f6;
                border: 1px solid #2563eb;
                width: 16px;
                height: 16px;
                border-radius: 8px;
                margin: -6px 0;
            }
            QSlider::sub-page:horizontal {
                background: #3b82f6;
                border-radius: 3px;
            }
        """)
        
        self.max_bid_value_label = QLabel("$5.00")
        self.max_bid_value_label.setStyleSheet("color: #1e293b; font-size: 12px; font-weight: 500; min-width: 40px;")
        self.max_bid_value_label.setAlignment(Qt.AlignRight)
        
        max_bid_control_layout.addWidget(self.max_bid_slider)
        max_bid_control_layout.addWidget(self.max_bid_value_label)
        max_bid_layout.addLayout(max_bid_control_layout)
        
        layout.addLayout(max_bid_layout)
        
        # Bid Increment section
        bid_increment_layout = QVBoxLayout()
        bid_increment_layout.setSpacing(6)
        
        bid_increment_label = QLabel("Bid Increment:")
        bid_increment_label.setStyleSheet("color: #374151; font-size: 12px; font-weight: 500;")
        bid_increment_layout.addWidget(bid_increment_label)
        
        # Bid increment slider and value display
        bid_increment_control_layout = QHBoxLayout()
        bid_increment_control_layout.setSpacing(8)
        
        self.bid_increment_slider = QSlider(Qt.Horizontal)
        self.bid_increment_slider.setMinimum(1)  # $0.01
        self.bid_increment_slider.setMaximum(25)  # $0.25
        self.bid_increment_slider.setValue(5)  # Default $0.05
        self.bid_increment_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #d1d5db;
                height: 6px;
                background: #f3f4f6;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #3b82f6;
                border: 1px solid #2563eb;
                width: 16px;
                height: 16px;
                border-radius: 8px;
                margin: -6px 0;
            }
            QSlider::sub-page:horizontal {
                background: #3b82f6;
                border-radius: 3px;
            }
        """)
        
        self.bid_increment_value_label = QLabel("$0.05")
        self.bid_increment_value_label.setStyleSheet("color: #1e293b; font-size: 12px; font-weight: 500; min-width: 40px;")
        self.bid_increment_value_label.setAlignment(Qt.AlignRight)
        
        bid_increment_control_layout.addWidget(self.bid_increment_slider)
        bid_increment_control_layout.addWidget(self.bid_increment_value_label)
        bid_increment_layout.addLayout(bid_increment_control_layout)
        
        layout.addLayout(bid_increment_layout)
        
        # Marketplace Refresh Interval section
        refresh_layout = QVBoxLayout()
        refresh_layout.setSpacing(6)
        
        refresh_label = QLabel("Marketplace Refresh:")
        refresh_label.setStyleSheet("color: #374151; font-size: 12px; font-weight: 500;")
        refresh_layout.addWidget(refresh_label)
        
        # Refresh interval slider and value display
        refresh_control_layout = QHBoxLayout()
        refresh_control_layout.setSpacing(8)
        
        self.refresh_interval_slider = QSlider(Qt.Horizontal)
        self.refresh_interval_slider.setMinimum(5)  # 5 seconds
        self.refresh_interval_slider.setMaximum(300)  # 5 minutes
        self.refresh_interval_slider.setValue(30)  # Default 30 seconds
        self.refresh_interval_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #d1d5db;
                height: 6px;
                background: #f3f4f6;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #10b981;
                border: 1px solid #059669;
                width: 16px;
                height: 16px;
                border-radius: 8px;
                margin: -6px 0;
            }
            QSlider::sub-page:horizontal {
                background: #10b981;
                border-radius: 3px;
            }
        """)
        
        self.refresh_interval_value_label = QLabel("30s")
        self.refresh_interval_value_label.setStyleSheet("color: #1e293b; font-size: 12px; font-weight: 500; min-width: 40px;")
        self.refresh_interval_value_label.setAlignment(Qt.AlignRight)
        
        refresh_control_layout.addWidget(self.refresh_interval_slider)
        refresh_control_layout.addWidget(self.refresh_interval_value_label)
        refresh_layout.addLayout(refresh_control_layout)
        
        layout.addLayout(refresh_layout)
        
        # Connect signals
        self.max_bid_slider.valueChanged.connect(self.update_max_bid_value)
        self.bid_increment_slider.valueChanged.connect(self.update_bid_increment_value)
        self.refresh_interval_slider.valueChanged.connect(self.update_refresh_interval_value)
    
    def update_max_bid_value(self, value):
        """Update max bid value display."""
        dollars = value / 100.0
        self.max_bid_value_label.setText(f"${dollars:.2f}")
    
    def update_bid_increment_value(self, value):
        """Update bid increment value display."""
        dollars = value / 100.0
        self.bid_increment_value_label.setText(f"${dollars:.2f}")
    
    def update_refresh_interval_value(self, value):
        """Update refresh interval value display and emit signal."""
        if value < 60:
            self.refresh_interval_value_label.setText(f"{value}s")
        else:
            minutes = value // 60
            seconds = value % 60
            if seconds == 0:
                self.refresh_interval_value_label.setText(f"{minutes}m")
            else:
                self.refresh_interval_value_label.setText(f"{minutes}m{seconds}s")
        
        # Emit signal for marketplace refresh interval change
        self.refresh_interval_changed.emit(value)
    
    def get_max_bid(self):
        """Get current max bid value in dollars."""
        return self.max_bid_slider.value() / 100.0
    
    def get_bid_increment(self):
        """Get current bid increment value in dollars."""
        return self.bid_increment_slider.value() / 100.0
    
    def get_refresh_interval(self):
        """Get current refresh interval in seconds."""
        return self.refresh_interval_slider.value()


class ConnectionStatusWidget(QWidget):
    """Widget for displaying connection status of all services."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_timer()
        self.update_connection_status()
    
    def setup_ui(self):
        """Setup the connection status UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        
        # Connection status labels
        self.status_labels = {}
        
        # Blockchain connections
        blockchain_services = [
            ('nano', 'Nano Network'),
            ('arweave', 'Arweave Network'),
            ('dogecoin', 'Dogecoin Network')
        ]
        
        for service_key, service_name in blockchain_services:
            status_layout = QHBoxLayout()
            
            # Service name
            name_label = QLabel(f"{service_name}:")
            name_label.setStyleSheet("color: #374151; font-size: 12px; font-weight: 500;")
            name_label.setFixedWidth(120)
            status_layout.addWidget(name_label)
            
            # Status indicator
            status_label = QLabel("Checking...")
            status_label.setStyleSheet("color: #6b7280; font-size: 12px;")
            status_layout.addWidget(status_label)
            
            status_layout.addStretch()
            layout.addLayout(status_layout)
            
            self.status_labels[service_key] = status_label
        
        # Database connection
        db_layout = QHBoxLayout()
        db_name_label = QLabel("Database:")
        db_name_label.setStyleSheet("color: #374151; font-size: 12px; font-weight: 500;")
        db_name_label.setFixedWidth(120)
        db_layout.addWidget(db_name_label)
        
        db_status_label = QLabel("Connected")
        db_status_label.setStyleSheet("color: #059669; font-size: 12px;")
        db_layout.addWidget(db_status_label)
        db_layout.addStretch()
        layout.addLayout(db_layout)
        
        self.status_labels['database'] = db_status_label
        
        # Price API connection
        price_layout = QHBoxLayout()
        price_name_label = QLabel("Price API:")
        price_name_label.setStyleSheet("color: #374151; font-size: 12px; font-weight: 500;")
        price_name_label.setFixedWidth(120)
        price_layout.addWidget(price_name_label)
        
        price_status_label = QLabel("Checking...")
        price_status_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        price_layout.addWidget(price_status_label)
        price_layout.addStretch()
        layout.addLayout(price_layout)
        
        self.status_labels['price_api'] = price_status_label
        
        # Application Service
        app_layout = QHBoxLayout()
        app_name_label = QLabel("App Service:")
        app_name_label.setStyleSheet("color: #374151; font-size: 12px; font-weight: 500;")
        app_name_label.setFixedWidth(120)
        app_layout.addWidget(app_name_label)
        
        app_status_label = QLabel("Checking...")
        app_status_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        app_layout.addWidget(app_status_label)
        app_layout.addStretch()
        layout.addLayout(app_layout)
        
        self.status_labels['app_service'] = app_status_label
    
    def setup_timer(self):
        """Setup timer for periodic status updates."""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_connection_status)
        self.update_timer.start(5000)  # Update every 5 seconds
    
    def update_connection_status(self):
        """Update the connection status for all services."""
        try:
            # Check blockchain connections
            if hasattr(app_service, 'blockchain') and app_service.blockchain:
                blockchain_status = app_service.blockchain.connection_status
                
                for service_key in ['nano', 'arweave', 'dogecoin']:
                    if service_key in blockchain_status:
                        status = blockchain_status[service_key]
                        if status.is_healthy():
                            self.status_labels[service_key].setText("Connected")
                            self.status_labels[service_key].setStyleSheet("color: #059669; font-size: 12px;")
                        else:
                            self.status_labels[service_key].setText(f"Error: {status.status.value}")
                            self.status_labels[service_key].setStyleSheet("color: #dc2626; font-size: 12px;")
                    else:
                        self.status_labels[service_key].setText("Not Available")
                        self.status_labels[service_key].setStyleSheet("color: #6b7280; font-size: 12px;")
            
            # Check database connection (always connected in current implementation)
            self.status_labels['database'].setText("Connected")
            self.status_labels['database'].setStyleSheet("color: #059669; font-size: 12px;")
            
            # Check price API (simplified check)
            if hasattr(app_service, 'price_service') and app_service.price_service:
                self.status_labels['price_api'].setText("Available")
                self.status_labels['price_api'].setStyleSheet("color: #059669; font-size: 12px;")
            else:
                self.status_labels['price_api'].setText("Not Available")
                self.status_labels['price_api'].setStyleSheet("color: #dc2626; font-size: 12px;")
            
            # Check application service
            if app_service.is_initialized:
                self.status_labels['app_service'].setText("Initialized")
                self.status_labels['app_service'].setStyleSheet("color: #059669; font-size: 12px;")
            else:
                self.status_labels['app_service'].setText("Not Initialized")
                self.status_labels['app_service'].setStyleSheet("color: #dc2626; font-size: 12px;")
                
        except Exception as e:
            print(f"Error updating connection status: {e}")
            # Set all to error state
            for label in self.status_labels.values():
                label.setText("Error")
                label.setStyleSheet("color: #dc2626; font-size: 12px;")


class UserProfileWidget(QWidget):
    """Widget for managing user profile information."""
    
    username_changed = pyqtSignal(str)  # Signal when username is changed
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_user_info()
    
    def setup_ui(self):
        """Setup the user profile UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Title
        title = QLabel("User Profile")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setStyleSheet("color: #1e293b; margin-bottom: 8px;")
        layout.addWidget(title)
        
        # Username section
        username_group = QGroupBox("Username")
        username_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        username_layout = QVBoxLayout(username_group)
        
        # Current username display
        self.current_username_label = QLabel("Current: Loading...")
        self.current_username_label.setStyleSheet("color: #64748b; font-size: 14px;")
        username_layout.addWidget(self.current_username_label)
        
        # Username input
        input_layout = QHBoxLayout()
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter new username (3-32 characters)")
        self.username_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #3b82f6;
                outline: none;
            }
        """)
        input_layout.addWidget(self.username_input)
        
        self.update_username_btn = QPushButton("Update")
        self.update_username_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
            }
            QPushButton:disabled {
                background-color: #9ca3af;
                color: #6b7280;
            }
        """)
        self.update_username_btn.clicked.connect(self.update_username)
        input_layout.addWidget(self.update_username_btn)
        
        username_layout.addLayout(input_layout)
        layout.addWidget(username_group)
        
        # User stats section
        stats_group = QGroupBox("Statistics")
        stats_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        stats_layout = QVBoxLayout(stats_group)
        
        self.reputation_label = QLabel("Reputation: Loading...")
        self.reputation_label.setStyleSheet("color: #64748b; font-size: 14px;")
        stats_layout.addWidget(self.reputation_label)
        
        self.sales_label = QLabel("Total Sales: Loading...")
        self.sales_label.setStyleSheet("color: #64748b; font-size: 14px;")
        stats_layout.addWidget(self.sales_label)
        
        self.purchases_label = QLabel("Total Purchases: Loading...")
        self.purchases_label.setStyleSheet("color: #64748b; font-size: 14px;")
        stats_layout.addWidget(self.purchases_label)
        
        layout.addWidget(stats_group)
        
        # Bid Settings section
        bid_settings_group = QGroupBox("Bid Settings")
        bid_settings_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        bid_settings_layout = QVBoxLayout(bid_settings_group)
        
        # Create bid settings widget
        self.bid_settings_widget = BidSettingsWidget()
        bid_settings_layout.addWidget(self.bid_settings_widget)
        
        layout.addWidget(bid_settings_group)
        
        # Connection Information section
        connection_group = QGroupBox("Connection Information")
        connection_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        connection_layout = QVBoxLayout(connection_group)
        
        # Create connection status widget
        self.connection_widget = ConnectionStatusWidget()
        connection_layout.addWidget(self.connection_widget)
        
        layout.addWidget(connection_group)
        
        # Add stretch to push content to top
        layout.addStretch()
    
    def load_user_info(self):
        """Load current user information."""
        print(f"[DEBUG] DashboardWidget.load_user_info called")
        if app_service.is_user_logged_in():
            user = app_service.get_current_user()
            if user:
                print(f"[DEBUG] Dashboard updating username display to: {user.username}")
                self.current_username_label.setText(f"Current: {user.username}")
                self.reputation_label.setText(f"Reputation: {user.reputation_score:.1f}/100")
                self.sales_label.setText(f"Total Sales: {user.total_sales}")
                self.purchases_label.setText(f"Total Purchases: {user.total_purchases}")
                print(f"[DEBUG] Dashboard user info update completed")
                
                # Refresh connection status
                if hasattr(self, 'connection_widget'):
                    self.connection_widget.update_connection_status()
    
    def update_username(self):
        """Update the username."""
        new_username = self.username_input.text().strip()
        
        if not new_username:
            QMessageBox.warning(self, "Invalid Username", "Please enter a username.")
            return
        
        if len(new_username) < 3 or len(new_username) > 32:
            QMessageBox.warning(self, "Invalid Username", "Username must be between 3 and 32 characters.")
            return
        
        # Disable button during update
        self.update_username_btn.setEnabled(False)
        self.update_username_btn.setText("Updating...")
        
        # Update username via app service
        worker = AsyncWorker(app_service.update_username(new_username))
        worker.finished.connect(self.on_username_updated)
        worker.error.connect(self.on_username_error)
        worker.start()
        self.username_worker = worker
    
    def on_username_updated(self, success):
        """Handle username update completion."""
        self.update_username_btn.setEnabled(True)
        self.update_username_btn.setText("Update")
        
        if success:
            self.username_input.clear()
            self.load_user_info()  # Refresh display
            self.username_changed.emit(self.current_username_label.text().replace("Current: ", ""))
            QMessageBox.information(self, "Success", "Username updated successfully!")
        else:
            QMessageBox.warning(self, "Error", "Failed to update username. Please try again.")
    
    def on_username_error(self, error):
        """Handle username update error."""
        self.update_username_btn.setEnabled(True)
        self.update_username_btn.setText("Update")
        QMessageBox.critical(self, "Error", f"Error updating username: {error}")


class WalletOverviewWidget(QWidget):
    """Widget for displaying wallet balances and transaction history."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_wallet = None
        self.wallet_balances = {}
        self.setup_ui()
        self.load_wallet_data()
        
        # Setup refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.load_wallet_data)
        self.refresh_timer.start(30000)  # Refresh every 30 seconds
    
    def setup_ui(self):
        """Setup the wallet overview UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Title
        title = QLabel("Wallet Overview")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setStyleSheet("color: #1e293b; margin-bottom: 8px;")
        layout.addWidget(title)
        
        # Wallet buttons section
        wallets_group = QGroupBox("Your Wallets")
        wallets_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        wallets_layout = QVBoxLayout(wallets_group)
        
        # Wallet sections with addresses
        self.wallet_buttons = {}
        self.wallet_addresses = {}
        self.copy_buttons = {}
        currencies = ['NANO', 'DOGE', 'ARWEAVE']
        
        for currency in currencies:
            # Create wallet container
            wallet_container = QFrame()
            wallet_container.setStyleSheet("""
                QFrame {
                    background-color: #f8fafc;
                    border: 1px solid #e2e8f0;
                    border-radius: 8px;
                    margin: 2px;
                    padding: 8px;
                }
            """)
            wallet_layout = QVBoxLayout(wallet_container)
            wallet_layout.setContentsMargins(8, 8, 8, 8)
            wallet_layout.setSpacing(6)
            
            # Wallet balance button
            btn = QPushButton(f"{currency} - Loading...")
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #1e293b;
                    border: none;
                    padding: 8px;
                    border-radius: 4px;
                    font-size: 14px;
                    font-weight: bold;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: #e2e8f0;
                }
                QPushButton:pressed {
                    background-color: #cbd5e1;
                }
            """)
            btn.clicked.connect(lambda checked, c=currency: self.show_wallet_details(c))
            self.wallet_buttons[currency] = btn
            wallet_layout.addWidget(btn)
            
            # Address section
            address_container = QHBoxLayout()
            address_container.setContentsMargins(0, 0, 0, 0)
            address_container.setSpacing(8)
            
            # Address label
            address_label = QLabel("Loading address...")
            address_label.setStyleSheet("""
                QLabel {
                    color: #64748b;
                    font-size: 11px;
                    font-family: monospace;
                    background-color: #f1f5f9;
                    padding: 4px 8px;
                    border-radius: 4px;
                    border: 1px solid #e2e8f0;
                }
            """)
            address_label.setWordWrap(True)
            self.wallet_addresses[currency] = address_label
            address_container.addWidget(address_label, 1)
            
            # Copy button
            copy_btn = QPushButton("📋")
            copy_btn.setFixedSize(28, 28)
            copy_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3b82f6;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #2563eb;
                }
                QPushButton:pressed {
                    background-color: #1d4ed8;
                }
            """)
            copy_btn.setToolTip(f"Copy {currency} address")
            copy_btn.clicked.connect(lambda checked, c=currency: self.copy_address(c))
            self.copy_buttons[currency] = copy_btn
            address_container.addWidget(copy_btn)
            
            wallet_layout.addLayout(address_container)
            wallets_layout.addWidget(wallet_container)
        
        layout.addWidget(wallets_group)
        
        # Transaction history section
        history_group = QGroupBox("Transaction History")
        history_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        history_layout = QVBoxLayout(history_group)
        
        # Current wallet label
        self.current_wallet_label = QLabel("Select a wallet to view transaction history")
        self.current_wallet_label.setStyleSheet("color: #64748b; font-size: 14px; margin-bottom: 8px;")
        history_layout.addWidget(self.current_wallet_label)
        
        # Transaction table
        self.transaction_table = QTableWidget()
        self.transaction_table.setColumnCount(4)
        self.transaction_table.setHorizontalHeaderLabels(["Date", "Type", "Amount", "Status"])
        self.transaction_table.horizontalHeader().setStretchLastSection(True)
        self.transaction_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.transaction_table.setAlternatingRowColors(True)
        self.transaction_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.transaction_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                background-color: white;
                gridline-color: #f1f5f9;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f1f5f9;
            }
            QTableWidget::item:selected {
                background-color: #eff6ff;
                color: #1e293b;
            }
            QHeaderView::section {
                background-color: #f8fafc;
                padding: 8px;
                border: none;
                border-bottom: 2px solid #e2e8f0;
                font-weight: bold;
            }
        """)
        
        # Initially hide the table
        self.transaction_table.setVisible(False)
        history_layout.addWidget(self.transaction_table)
        
        # No transactions message
        self.no_transactions_label = QLabel("No transactions to display")
        self.no_transactions_label.setAlignment(Qt.AlignCenter)
        self.no_transactions_label.setStyleSheet("color: #9ca3af; font-size: 14px; padding: 20px;")
        history_layout.addWidget(self.no_transactions_label)
        
        layout.addWidget(history_group)
    
    def copy_address(self, currency):
        """Copy wallet address to clipboard."""
        try:
            addresses = app_service.get_wallet_addresses()
            if currency in addresses:
                address = addresses[currency]
                clipboard = QApplication.clipboard()
                clipboard.setText(address)
                
                # Show confirmation message
                QMessageBox.information(
                    self,
                    "Address Copied",
                    f"{currency} address copied to clipboard:\n{address}"
                )
            else:
                QMessageBox.warning(
                    self,
                    "Address Not Available",
                    f"No {currency} address found for current user."
                )
        except Exception as e:
            print(f"Error copying address: {e}")
            QMessageBox.critical(
                self,
                "Copy Error",
                f"Failed to copy {currency} address: {str(e)}"
            )
    
    def load_wallet_data(self):
        """Load wallet balance data and addresses."""
        if not app_service.is_user_logged_in():
            return
        
        # Load wallet addresses first
        self.load_wallet_addresses()
        
        # Load wallet balances
        worker = AsyncWorker(app_service.get_wallet_balances())
        worker.finished.connect(self.on_balances_loaded)
        worker.error.connect(self.on_balances_error)
        worker.start()
        self.balance_worker = worker
    
    def load_wallet_addresses(self):
        """Load and display wallet addresses."""
        try:
            addresses = app_service.get_wallet_addresses()
            
            for currency in ['NANO', 'DOGE', 'ARWEAVE']:
                if currency in self.wallet_addresses:
                    if currency in addresses and addresses[currency]:
                        address = addresses[currency]
                        # Truncate long addresses for display
                        if len(address) > 20:
                            display_address = f"{address[:10]}...{address[-10:]}"
                        else:
                            display_address = address
                        self.wallet_addresses[currency].setText(display_address)
                        self.wallet_addresses[currency].setToolTip(f"Full address: {address}")
                        # Enable copy button
                        if currency in self.copy_buttons:
                            self.copy_buttons[currency].setEnabled(True)
                    else:
                        self.wallet_addresses[currency].setText("No address available")
                        self.wallet_addresses[currency].setToolTip("No address available")
                        # Disable copy button
                        if currency in self.copy_buttons:
                            self.copy_buttons[currency].setEnabled(False)
        except Exception as e:
            print(f"Error loading wallet addresses: {e}")
            for currency in ['NANO', 'DOGE', 'ARWEAVE']:
                if currency in self.wallet_addresses:
                    self.wallet_addresses[currency].setText("Error loading address")
                    if currency in self.copy_buttons:
                        self.copy_buttons[currency].setEnabled(False)
    
    def on_balances_loaded(self, balances):
        """Handle loaded wallet balances."""
        self.wallet_balances = balances
        
        # Update wallet buttons
        for currency, btn in self.wallet_buttons.items():
            currency_key = currency.lower()
            if currency_key == 'arweave':
                currency_key = 'ar'  # Arweave might use 'ar' as key
            
            if currency_key in balances:
                balance_data = balances[currency_key]
                if isinstance(balance_data, dict):
                    balance = balance_data.get('balance', '0')
                    if currency == 'NANO':
                        try:
                            balance_nano = float(balance) / (10**30)
                            display_balance = f"{balance_nano:.6f}"
                        except:
                            display_balance = "0.000000"
                    else:
                        try:
                            display_balance = f"{float(balance):,.2f}"
                        except:
                            display_balance = "0.00"
                    
                    btn.setText(f"{currency} - {display_balance}")
                else:
                    # Handle case where balance_data is not a dict (e.g., direct value)
                    try:
                        if currency == 'NANO':
                            balance_nano = float(balance_data) / (10**30)
                            display_balance = f"{balance_nano:.6f}"
                        else:
                            display_balance = f"{float(balance_data):,.2f}"
                        btn.setText(f"{currency} - {display_balance}")
                    except:
                        btn.setText(f"{currency} - {balance_data}")
            else:
                btn.setText(f"{currency} - Not available")
    
    def on_balances_error(self, error):
        """Handle balance loading error."""
        print(f"Error loading wallet balances: {error}")
        for currency, btn in self.wallet_buttons.items():
            btn.setText(f"{currency} - Error loading")
    
    def show_wallet_details(self, currency):
        """Show transaction history for selected wallet."""
        self.current_wallet = currency
        self.current_wallet_label.setText(f"Transaction History - {currency}")
        
        # Load transaction history
        worker = AsyncWorker(app_service.get_wallet_transactions(currency.lower(), limit=50))
        worker.finished.connect(self.on_transactions_loaded)
        worker.error.connect(self.on_transactions_error)
        worker.start()
        self.transaction_worker = worker
    
    def on_transactions_loaded(self, transactions):
        """Handle loaded transaction history."""
        if not transactions:
            self.transaction_table.setVisible(False)
            self.no_transactions_label.setVisible(True)
            self.no_transactions_label.setText(f"No {self.current_wallet} transactions found")
            return
        
        self.no_transactions_label.setVisible(False)
        self.transaction_table.setVisible(True)
        
        # Populate transaction table
        self.transaction_table.setRowCount(len(transactions))
        
        for row, tx in enumerate(transactions):
            # Date
            date_item = QTableWidgetItem(tx.get('date', 'Unknown'))
            self.transaction_table.setItem(row, 0, date_item)
            
            # Type
            tx_type = tx.get('type', 'Unknown')
            type_item = QTableWidgetItem(tx_type.title())
            self.transaction_table.setItem(row, 1, type_item)
            
            # Amount
            amount = tx.get('amount', '0')
            amount_item = QTableWidgetItem(f"{amount} {self.current_wallet}")
            self.transaction_table.setItem(row, 2, amount_item)
            
            # Status
            status = tx.get('status', 'Unknown')
            status_item = QTableWidgetItem(status.title())
            self.transaction_table.setItem(row, 3, status_item)
    
    def on_transactions_error(self, error):
        """Handle transaction loading error."""
        self.transaction_table.setVisible(False)
        self.no_transactions_label.setVisible(True)
        self.no_transactions_label.setText(f"Error loading {self.current_wallet} transactions: {error}")


class DashboardWidget(QWidget):
    """Main dashboard widget containing user profile and wallet overview."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the dashboard UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Title only (no logo)
        title = QLabel("Dashboard")
        title.setFont(QFont("Arial", 20, QFont.Bold))
        title.setStyleSheet("color: #1e293b; margin-bottom: 16px;")
        layout.addWidget(title)
        
        # Main content layout (45% left, 55% right)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        
        # Left column - User Profile (45%)
        self.user_profile_widget = UserProfileWidget()
        self.user_profile_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        content_layout.addWidget(self.user_profile_widget, 45)
        
        # Right column - Wallet Overview (55%)
        self.wallet_overview_widget = WalletOverviewWidget()
        self.wallet_overview_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        content_layout.addWidget(self.wallet_overview_widget, 55)
        
        layout.addLayout(content_layout)
        
        # Connect signals
        self.user_profile_widget.username_changed.connect(self.on_username_changed)
    
    def on_username_changed(self, new_username):
        """Handle username change."""
        # You could emit a signal here to update other parts of the UI
        print(f"Username changed to: {new_username}")
    
    def get_bid_settings_widget(self):
        """Get the bid settings widget for connecting signals."""
        return self.user_profile_widget.bid_settings_widget