"""
Simplified Main Window for Sapphire Exchange.
Clean, maintainable main window using distributed components.
"""

import json
import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QStatusBar, QMessageBox, QInputDialog, QLineEdit,
    QDialog, QTextEdit
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


MNEMONIC_BACKUP_FILE = "/Users/seanmorrissey/Desktop/Coding/Sapphire_Exchange/sapphire_mnemonic_backup.mnemonic.enc"


def decrypt_mnemonic_backup_payload(payload, password):
    if not isinstance(payload, dict):
        raise ValueError("Invalid backup file.")

    if payload.get('type') != 'sapphire_mnemonic_backup':
        raise ValueError("Selected file is not a Sapphire mnemonic backup.")

    kdf_data = payload.get('kdf') or {}
    cipher_data = payload.get('cipher') or {}
    salt_hex = kdf_data.get('salt')
    nonce_hex = cipher_data.get('nonce')
    ciphertext_hex = cipher_data.get('ciphertext')
    iterations = kdf_data.get('iterations', 100000)

    if not salt_hex or not nonce_hex or not ciphertext_hex:
        raise ValueError("Backup file is incomplete.")

    if not isinstance(iterations, int) or iterations <= 0:
        raise ValueError("Backup file has invalid encryption settings.")

    try:
        salt = bytes.fromhex(salt_hex)
        nonce = bytes.fromhex(nonce_hex)
        ciphertext = bytes.fromhex(ciphertext_hex)
    except ValueError as exc:
        raise ValueError("Backup file is corrupted.") from exc

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
    )
    key = kdf.derive(password.encode('utf-8'))

    try:
        mnemonic = AESGCM(key).decrypt(nonce, ciphertext, None).decode('utf-8').strip()
    except Exception as exc:
        raise ValueError("Incorrect password or unreadable backup.") from exc

    if not mnemonic:
        raise ValueError("Backup decrypted successfully, but the mnemonic is empty.")

    return mnemonic


class SimplifiedMainWindow(QMainWindow):
    """Simplified main application window using unified architecture."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sapphire Exchange")
        self.resize(1200, 800)
        self.setMinimumSize(800, 600)
        
        # Setup UI first
        self.setup_ui()
        
        # Delay app service initialization to ensure event loop is running
        self.app_ready = False
        self.init_worker = None
        QTimer.singleShot(100, self.init_app_service)
        
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
        self.app_ready = False
    
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
        from services.arweave_post_service import arweave_post_service
        
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
        self.marketplace_widget.arweave_post_service = arweave_post_service
        self.content_stack.addWidget(self.marketplace_widget)
        
        # My Items page (index 1)
        self.my_items_widget = AuctionListWidget(active_section="my-items")
        self.my_items_widget.arweave_post_service = arweave_post_service
        self.content_stack.addWidget(self.my_items_widget)
        
        # Activity page (index 2)
        self.activity_widget = self.create_activity_widget()
        self.content_stack.addWidget(self.activity_widget)
        
        # Dashboard page (index 3)
        self.dashboard_widget = self.create_dashboard_widget()
        self.content_stack.addWidget(self.dashboard_widget)
        
        # Dev Tools page (index 4)
        self.dev_tools_widget = self.create_dev_tools_widget()
        self.content_stack.addWidget(self.dev_tools_widget)
        
        main_layout.addWidget(self.content_stack, 1)
        
        # Connect bid settings refresh interval to marketplace widget
        bid_settings_widget = self.dashboard_widget.get_bid_settings_widget()
        bid_settings_widget.refresh_interval_changed.connect(self.marketplace_widget.set_refresh_interval)
        
        # Store dev tools reference for signal connections
        self._marketplace_widget = self.marketplace_widget
        self._my_items_widget = self.my_items_widget
        
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
        from ui.arweave_dev_tools_widget import ArweaveDevToolsWidget
        from services.arweave_post_service import arweave_post_service
        
        dev_tools = ArweaveDevToolsWidget()
        dev_tools.set_arweave_service(arweave_post_service)
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        layout.addWidget(dev_tools)
        
        self.arweave_dev_tools = dev_tools
        
        return container
    
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
        
        self.view_mnemonic_btn = QPushButton("View Backup")
        self.view_mnemonic_btn.setStyleSheet("""
            QPushButton {
                background-color: #0f172a;
                color: white;
                border: none;
                padding: 6px 10px;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #1e293b;
            }
            QPushButton:disabled {
                background-color: #cbd5e1;
                color: #64748b;
            }
        """)
        self.view_mnemonic_btn.clicked.connect(self.open_mnemonic_backup)
        status_bar.addPermanentWidget(self.view_mnemonic_btn)
        
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
            
            # Connect Arweave post signals to dev tools
            self.connect_arweave_post_signals()
            
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
        print("[DEBUG] Logout button clicked")
        worker = AsyncWorker(app_service.logout_user())
        worker.finished.connect(self.on_logout_complete)
        worker.error.connect(self.on_logout_error)
        worker.start()
        self.logout_worker = worker
    
    def on_logout_complete(self, success):
        """Handle logout completion."""
        print(f"[DEBUG] on_logout_complete called with success={success}")
        if success:
            print("[DEBUG] Logout successful, switching to login screen")
            # Hide sidebar and switch to login screen
            self.sidebar.setVisible(False)
            self.stacked_widget.setCurrentWidget(self.login_screen)
            self.login_screen.reset_form()
            self.status_label.setText("Logged out successfully")
        else:
            print("[DEBUG] Logout failed")
            QMessageBox.warning(self, "Logout Failed", "Failed to logout. Please try again.")
    
    def on_logout_error(self, error):
        """Handle logout errors."""
        print(f"[DEBUG] Logout error: {error}")
        QMessageBox.critical(self, "Error", f"Logout error: {error}")
    
    def toggle_activity_overlay(self):
        """Toggle activity log overlay."""
        if self.activity_overlay.isVisible():
            self.activity_overlay.hide()
        else:
            overlay_height = 128
            self.activity_overlay.setGeometry(
                0, self.height() - 48 - overlay_height,
                self.width(), overlay_height
            )
            self.activity_overlay.show()
    
    def open_mnemonic_backup(self):
        """Open and decrypt the configured mnemonic backup."""
        password, ok = QInputDialog.getText(
            self,
            "Enter Backup Password",
            "Enter password to decrypt your mnemonic backup:",
            QLineEdit.Password
        )
        password = (password or '').strip()
        if not ok:
            return
        if not password:
            QMessageBox.warning(self, "Password Required", "Password cannot be empty.")
            return

        try:
            with open(MNEMONIC_BACKUP_FILE, 'r', encoding='utf-8') as backup_file:
                payload = json.load(backup_file)
            mnemonic = decrypt_mnemonic_backup_payload(payload, password)
        except FileNotFoundError:
            QMessageBox.warning(self, "Backup Not Found", f"Backup file not found:\n{MNEMONIC_BACKUP_FILE}")
            return
        except json.JSONDecodeError:
            QMessageBox.warning(self, "Invalid Backup", "The configured backup file is not valid JSON.")
            return
        except ValueError as exc:
            QMessageBox.warning(self, "Unable to Decrypt Backup", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Backup Error", f"Failed to read backup: {exc}")
            return

        self.show_mnemonic_backup_dialog(mnemonic, MNEMONIC_BACKUP_FILE)

    def show_mnemonic_backup_dialog(self, mnemonic, file_path):
        """Show decrypted mnemonic in a modal dialog."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Backup Mnemonic")
        dialog.setModal(True)
        dialog.resize(640, 320)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        warning_label = QLabel(
            "This is your decrypted backup mnemonic. Keep it private and close this window when you are done."
        )
        warning_label.setWordWrap(True)
        warning_label.setStyleSheet(
            "background-color: #fff7ed; color: #9a3412; border: 1px solid #fdba74; "
            "border-radius: 6px; padding: 12px;"
        )
        layout.addWidget(warning_label)

        file_label = QLabel(f"Backup file: {os.path.basename(file_path)}")
        file_label.setStyleSheet("color: #64748b; font-size: 12px;")
        layout.addWidget(file_label)

        mnemonic_display = QTextEdit()
        mnemonic_display.setReadOnly(True)
        mnemonic_display.setPlainText(mnemonic)
        mnemonic_display.setFont(QFont("Courier New", 12, QFont.Bold))
        layout.addWidget(mnemonic_display)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn, 0, Qt.AlignRight)

        dialog.exec_()
    
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
    
    def connect_arweave_post_signals(self):
        """Connect Arweave post signals from auction widgets to dev tools."""
        try:
            if hasattr(self, 'arweave_dev_tools'):
                print(f"[DEBUG] Connecting post signals to dev tools")
                self.marketplace_widget.arweave_post_generated.connect(
                    self.arweave_dev_tools.add_post_preview
                )
                self.my_items_widget.arweave_post_generated.connect(
                    self.arweave_dev_tools.add_post_preview
                )
                print(f"[DEBUG] Post signals connected successfully")
            else:
                print(f"[DEBUG] arweave_dev_tools not found!")
        except Exception as e:
            print(f"Error connecting Arweave post signals: {e}")
            import traceback
            traceback.print_exc()
    
    # Callback methods for app service events
    def on_app_initialized(self, result):
        """Handle app initialization completion."""
        print("Application initialized successfully")
        self.app_ready = True
        if hasattr(self, 'login_screen'):
            self.login_screen.set_app_ready(True)
    
    def on_init_error(self, error):
        """Handle app initialization errors."""
        print(f"Application initialization error: {error}")
        self.app_ready = False
        if hasattr(self, 'login_screen'):
            self.login_screen.set_app_ready(False)
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