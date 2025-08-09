"""
Dashboard Widget for Sapphire Exchange.
Contains user profile management and wallet overview with transaction history.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QFrame, QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QGroupBox, QSizePolicy, QSpacerItem
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QPalette

from services.application_service import app_service
from utils.async_worker import AsyncWorker
from ui.logo_component import HeaderWithLogo


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
        
        # Add stretch to push content to top
        layout.addStretch()
    
    def load_user_info(self):
        """Load current user information."""
        if app_service.is_user_logged_in():
            user = app_service.get_current_user()
            if user:
                self.current_username_label.setText(f"Current: {user.username}")
                self.reputation_label.setText(f"Reputation: {user.reputation_score:.1f}/100")
                self.sales_label.setText(f"Total Sales: {user.total_sales}")
                self.purchases_label.setText(f"Total Purchases: {user.total_purchases}")
    
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
        
        # Wallet buttons
        self.wallet_buttons = {}
        currencies = ['NANO', 'DOGE', 'ARWEAVE']
        
        for currency in currencies:
            btn = QPushButton(f"{currency} - Loading...")
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #f8fafc;
                    color: #1e293b;
                    border: 1px solid #e2e8f0;
                    padding: 12px;
                    border-radius: 8px;
                    font-size: 14px;
                    text-align: left;
                    margin: 2px;
                }
                QPushButton:hover {
                    background-color: #f1f5f9;
                    border-color: #cbd5e1;
                }
                QPushButton:pressed {
                    background-color: #e2e8f0;
                }
            """)
            btn.clicked.connect(lambda checked, c=currency: self.show_wallet_details(c))
            self.wallet_buttons[currency] = btn
            wallets_layout.addWidget(btn)
        
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
    
    def load_wallet_data(self):
        """Load wallet balance data."""
        if not app_service.is_user_logged_in():
            return
        
        worker = AsyncWorker(app_service.get_wallet_balances())
        worker.finished.connect(self.on_balances_loaded)
        worker.error.connect(self.on_balances_error)
        worker.start()
        self.balance_worker = worker
    
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
                    btn.setText(f"{currency} - {balance}")
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
        
        # Header with logo and title
        self.header = HeaderWithLogo(title="Dashboard", show_title=True)
        layout.addWidget(self.header)
        
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