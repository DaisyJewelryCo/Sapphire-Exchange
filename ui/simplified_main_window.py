"""
Simplified Main Window for Sapphire Exchange.
Clean, maintainable main window using distributed components.
"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QStatusBar, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

from services.application_service import app_service
from utils.async_worker import AsyncWorker
from ui.login_screen import LoginScreen
from ui.main_window_components import (
    ActivityLogOverlay, StatusPopup, NavigationSidebar
)
from ui.auction_widget import AuctionListWidget
from ui.wallet_widget import SimpleWalletWidget


class SimplifiedMainWindow(QMainWindow):
    """Simplified main application window using unified architecture."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sapphire Exchange")
        self.resize(1200, 800)
        self.setMinimumSize(800, 600)
        
        # Initialize application service
        self.init_app_service()
        
        # Setup UI
        self.setup_ui()
        
        # Setup timers
        self.setup_timers()
    
    def init_app_service(self):
        """Initialize the application service."""
        self.app_service = app_service
        
        # Setup callbacks
        app_service.add_status_change_callback(self.on_status_change)
        app_service.add_user_change_callback(self.on_user_change)
        app_service.add_auction_update_callback(self.on_auction_update)
        
        # Initialize asynchronously
        worker = AsyncWorker(app_service.initialize())
        worker.finished.connect(self.on_app_initialized)
        worker.error.connect(self.on_init_error)
        worker.start()
        self.init_worker = worker
    
    def setup_ui(self):
        """Setup the user interface."""
        # Apply global theming
        self.apply_global_theme()
        
        # Setup status bar
        self.setup_status_bar()
        
        # Use stacked widget to switch between login and main interface
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        
        # Create login screen
        self.login_screen = LoginScreen(self)
        self.stacked_widget.addWidget(self.login_screen)
        
        # Create main interface
        self.main_widget = self.create_main_interface()
        self.stacked_widget.addWidget(self.main_widget)
        
        # Create overlays
        self.activity_overlay = ActivityLogOverlay(self)
        self.status_popup = StatusPopup(self)
        
        # Start with login screen
        self.stacked_widget.setCurrentWidget(self.login_screen)
    
    def create_main_interface(self):
        """Create the main authenticated interface."""
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create sidebar
        self.sidebar = NavigationSidebar()
        self.sidebar.nav_button_group.buttonClicked.connect(self.on_nav_button_clicked)
        main_layout.addWidget(self.sidebar)
        
        # Create main content area
        self.content_stack = QStackedWidget()
        
        # Marketplace page (index 0)
        self.marketplace_widget = AuctionListWidget(active_section="marketplace")
        self.content_stack.addWidget(self.marketplace_widget)
        
        # My Items page (index 1)
        self.my_items_widget = AuctionListWidget(active_section="my-items")
        self.content_stack.addWidget(self.my_items_widget)
        
        # Dashboard page (index 2)
        self.dashboard_widget = self.create_dashboard_widget()
        self.content_stack.addWidget(self.dashboard_widget)
        
        # Activity page (index 3)
        self.activity_widget = self.create_activity_widget()
        self.content_stack.addWidget(self.activity_widget)
        
        # Dev Tools page (index 4)
        self.dev_tools_widget = self.create_dev_tools_widget()
        self.content_stack.addWidget(self.dev_tools_widget)
        
        main_layout.addWidget(self.content_stack, 1)
        
        # Connect bid settings refresh interval to marketplace widget
        bid_settings_widget = self.dashboard_widget.get_bid_settings_widget()
        bid_settings_widget.refresh_interval_changed.connect(self.marketplace_widget.set_refresh_interval)
        
        # Connect dashboard logout button
        self.dashboard_widget.logout_btn.clicked.connect(self.logout)
        
        # Initially hide sidebar (shown after login)
        self.sidebar.setVisible(False)
        
        return main_widget
    
    def create_dashboard_widget(self):
        """Create dashboard widget."""
        from ui.dashboard_widget import DashboardWidget
        return DashboardWidget()
    
    def create_activity_widget(self):
        """Create activity widget."""
        from ui.activity_widget import ActivityWidget
        return ActivityWidget()
    
    def create_dev_tools_widget(self):
        """Create dev tools widget."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        
        title = QLabel("Developer Tools")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #1e293b; margin-bottom: 16px;")
        layout.addWidget(title)
        
        # Add wallet widget for testing
        wallet_widget = SimpleWalletWidget()
        layout.addWidget(wallet_widget)
        
        layout.addStretch(1)
        
        return widget
    
    def apply_global_theme(self):
        """Apply global theming."""
        global_style = """
            QMainWindow {
                background-color: #ffffff;
                color: #1e293b;
                font-family: 'Inter', system-ui, sans-serif;
                font-size: 16px;
            }
            QWidget {
                background-color: #ffffff;
                color: #1e293b;
            }
            QPushButton {
                background-color: #000000;
                color: #ffffff;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #374151;
            }
            QPushButton:pressed {
                background-color: #111827;
            }
            QPushButton:disabled {
                background-color: #9ca3af;
                color: #6b7280;
            }
        """
        self.setStyleSheet(global_style)
    
    def setup_status_bar(self):
        """Setup the status bar."""
        status_bar = self.statusBar()
        status_bar.setFixedHeight(48)
        status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #f1f5f9;
                color: #1e293b;
                border-top: 1px solid #e2e8f0;
                font-size: 12px;
                padding: 0 16px;
            }
        """)
        
        # Create a container for status dot and text
        status_container = QWidget()
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(8)
        
        # Status dot
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #ef4444;
                background-color: transparent;
                border: none;
                padding: 0;
            }
        """)
        status_layout.addWidget(self.status_dot)
        
        # Status text
        self.status_label = QLabel("Not logged in")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #64748b;
                background-color: transparent;
                border: none;
                padding: 0;
            }
        """)
        status_layout.addWidget(self.status_label)
        
        status_bar.addWidget(status_container)
        
        # Activity log button
        self.activity_btn = QPushButton("Activity Log")
        self.activity_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)
        self.activity_btn.clicked.connect(self.toggle_activity_overlay)
        status_bar.addPermanentWidget(self.activity_btn)
    
    def setup_timers(self):
        """Setup update timers."""
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_status)
        self.update_timer.start(5000)  # Update every 5 seconds
    
    def on_nav_button_clicked(self, button):
        """Handle navigation button clicks."""
        page_id = self.sidebar.nav_button_group.id(button)
        self.content_stack.setCurrentIndex(page_id)
    
    def on_login_success(self, user):
        """Handle successful login."""
        if user:
            # Update sidebar user info
            self.sidebar.user_profile_section.update_user_info(user)
            
            # Show sidebar and switch to main interface
            self.sidebar.setVisible(True)
            self.stacked_widget.setCurrentWidget(self.main_widget)
            
            # Load wallet balances
            self.load_wallet_balances()
            
            # Refresh dashboard widget with user info
            if hasattr(self, 'dashboard_widget') and hasattr(self.dashboard_widget, 'user_profile_widget'):
                self.dashboard_widget.user_profile_widget.load_user_info()
            
            # Refresh wallet overview in dashboard
            if hasattr(self, 'dashboard_widget') and hasattr(self.dashboard_widget, 'wallet_overview_widget'):
                self.dashboard_widget.wallet_overview_widget.load_wallet_data()
            
            # Set default page to marketplace
            self.sidebar.set_active_page(0)
            self.content_stack.setCurrentIndex(0)
    
    def load_wallet_balances(self):
        """Load wallet balances for sidebar display."""
        print(f"[DEBUG] load_wallet_balances called")
        if not app_service.is_user_logged_in():
            print(f"[DEBUG] User not logged in, skipping balance load")
            return
        
        print(f"[DEBUG] Starting wallet balance worker")
        worker = AsyncWorker(app_service.get_wallet_balances())
        worker.finished.connect(self.on_balances_loaded)
        worker.error.connect(self.on_balances_error)
        worker.start()
        self.balance_worker = worker
    
    def on_balances_loaded(self, balances):
        """Handle loaded balances."""
        print(f"[DEBUG] on_balances_loaded called with balances: {balances}")
        self.sidebar.user_profile_section.update_balances(balances)
    
    def on_balances_error(self, error):
        """Handle balance loading errors."""
        print(f"[DEBUG] on_balances_error called with error: {error}")
        print(f"Error loading balances: {error}")
    
    def logout(self):
        """Logout current user."""
        worker = AsyncWorker(app_service.logout_user())
        worker.finished.connect(self.on_logout_complete)
        worker.start()
        self.logout_worker = worker
    
    def on_logout_complete(self, success):
        """Handle logout completion."""
        if success:
            # Hide sidebar and switch to login screen
            self.sidebar.setVisible(False)
            self.stacked_widget.setCurrentWidget(self.login_screen)
            self.login_screen.reset_form()
    
    def toggle_activity_overlay(self):
        """Toggle activity log overlay."""
        if self.activity_overlay.isVisible():
            self.activity_overlay.hide()
        else:
            # Position overlay above status bar
            overlay_height = 128
            self.activity_overlay.setGeometry(
                0, self.height() - 48 - overlay_height,
                self.width(), overlay_height
            )
            self.activity_overlay.show()
    
    def update_status(self):
        """Update status information."""
        if app_service.is_user_logged_in():
            self.status_label.setText("Connected")
            self.status_dot.setStyleSheet("""
                QLabel {
                    font-size: 14px;
                    color: #22c55e;
                    background-color: transparent;
                    border: none;
                    padding: 0;
                }
            """)
        else:
            self.status_label.setText("Not logged in")
            self.status_dot.setStyleSheet("""
                QLabel {
                    font-size: 14px;
                    color: #ef4444;
                    background-color: transparent;
                    border: none;
                    padding: 0;
                }
            """)
    
    def resizeEvent(self, event):
        """Handle window resize events."""
        super().resizeEvent(event)
        
        # Reposition overlays
        if hasattr(self, 'activity_overlay') and self.activity_overlay.isVisible():
            overlay_height = 128
            self.activity_overlay.setGeometry(
                0, self.height() - 48 - overlay_height,
                self.width(), overlay_height
            )
    
    # Callback methods for app service events
    def on_app_initialized(self, result):
        """Handle app initialization completion."""
        print("Application initialized successfully")
    
    def on_init_error(self, error):
        """Handle app initialization errors."""
        print(f"Application initialization error: {error}")
        QMessageBox.critical(self, "Initialization Error", f"Failed to initialize application: {error}")
    
    def on_status_change(self, status):
        """Handle status changes."""
        self.status_label.setText(status)
        
        # Update status dot color based on status
        if status.lower() in ["connected", "ready", "online"]:
            dot_color = "#22c55e"  # Green
        elif status.lower() in ["connecting", "initializing"]:
            dot_color = "#f59e0b"  # Amber
        else:
            dot_color = "#ef4444"  # Red
        
        self.status_dot.setStyleSheet(f"""
            QLabel {{
                font-size: 14px;
                color: {dot_color};
                background-color: transparent;
                border: none;
                padding: 0;
            }}
        """)
    
    def on_user_change(self, event, user):
        """Handle user changes."""
        print(f"[DEBUG] SimplifiedMainWindow.on_user_change called with event: {event}, user: {user.username if user else None}")
        if event == 'login':
            self.on_login_success(user)
        elif event == 'logout':
            self.on_logout_complete(True)
        elif event == 'profile_updated':
            # Refresh UI components that display user information
            print(f"[DEBUG] Handling profile_updated event")
            self.refresh_user_display(user)
    
    def refresh_user_display(self, user):
        """Refresh UI components that display user information."""
        try:
            print(f"[DEBUG] refresh_user_display called with user: {user.username}")
            
            # Update sidebar user profile section
            if hasattr(self, 'sidebar') and hasattr(self.sidebar, 'user_profile_section'):
                print(f"[DEBUG] Updating sidebar user profile section")
                self.sidebar.user_profile_section.update_user_info(user)
            else:
                print(f"[DEBUG] Sidebar or user_profile_section not found")
            
            # Update dashboard widget if it exists
            if hasattr(self, 'dashboard_widget'):
                print(f"[DEBUG] Updating dashboard widget")
                if hasattr(self.dashboard_widget, 'user_profile_widget'):
                    self.dashboard_widget.user_profile_widget.load_user_info()
                else:
                    print(f"[DEBUG] Dashboard user_profile_widget not found")
            else:
                print(f"[DEBUG] Dashboard widget not found")
            
            # Update any other components that display user info
            print(f"[DEBUG] User profile refresh completed: {user.username}")
            
        except Exception as e:
            print(f"Error refreshing user display: {e}")
    
    def on_auction_update(self, event, data):
        """Handle auction updates."""
        if event in ['bid_placed', 'auction_ended']:
            # Refresh auction lists
            if hasattr(self, 'marketplace_widget'):
                self.marketplace_widget.load_auctions()
            if hasattr(self, 'my_items_widget'):
                self.my_items_widget.load_auctions()