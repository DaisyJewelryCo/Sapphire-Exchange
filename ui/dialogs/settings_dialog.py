"""
Settings dialog for application configuration.
Handles network settings, security preferences, and theme configuration.
"""
from typing import Dict, Any
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QCheckBox, QComboBox, QSpinBox, QDoubleSpinBox, QTabWidget, QWidget,
    QFormLayout, QGroupBox, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont


class SettingsDialog(QDialog):
    """Settings dialog for application configuration."""
    
    settings_changed = pyqtSignal(dict)
    
    def __init__(self, current_settings: Dict[str, Any] = None, parent=None):
        super().__init__(parent)
        self.current_settings = current_settings or {}
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setMinimumSize(600, 500)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the UI."""
        layout = QVBoxLayout(self)
        
        tabs = QTabWidget()
        tabs.addTab(self._create_network_tab(), "Network")
        tabs.addTab(self._create_security_tab(), "Security")
        tabs.addTab(self._create_display_tab(), "Display")
        tabs.addTab(self._create_advanced_tab(), "Advanced")
        
        layout.addWidget(tabs)
        
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(save_btn)
        
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self.reset_defaults)
        button_layout.addWidget(reset_btn)
        
        close_btn = QPushButton("Cancel")
        close_btn.clicked.connect(self.reject)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def _create_network_tab(self) -> QWidget:
        """Create network settings tab."""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # Solana RPC
        self.solana_rpc = QLineEdit()
        self.solana_rpc.setText(
            self.current_settings.get('solana_rpc', 'https://api.mainnet-beta.solana.com')
        )
        layout.addRow("Solana RPC:", self.solana_rpc)
        
        # Nano Node
        self.nano_node = QLineEdit()
        self.nano_node.setText(
            self.current_settings.get('nano_node', 'https://mynano.ninja/api')
        )
        layout.addRow("Nano Node:", self.nano_node)
        
        # Arweave Gateway
        self.arweave_gateway = QLineEdit()
        self.arweave_gateway.setText(
            self.current_settings.get('arweave_gateway', 'https://arweave.net')
        )
        layout.addRow("Arweave Gateway:", self.arweave_gateway)
        
        # Network timeout
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setMinimum(5)
        self.timeout_spin.setMaximum(60)
        self.timeout_spin.setValue(self.current_settings.get('network_timeout', 30))
        self.timeout_spin.setSuffix(" seconds")
        layout.addRow("Network Timeout:", self.timeout_spin)
        
        # Retry attempts
        self.retry_spin = QSpinBox()
        self.retry_spin.setMinimum(1)
        self.retry_spin.setMaximum(10)
        self.retry_spin.setValue(self.current_settings.get('retry_attempts', 3))
        layout.addRow("Retry Attempts:", self.retry_spin)
        
        return widget
    
    def _create_security_tab(self) -> QWidget:
        """Create security settings tab."""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # Session timeout
        self.session_timeout = QSpinBox()
        self.session_timeout.setMinimum(1)
        self.session_timeout.setMaximum(120)
        self.session_timeout.setValue(self.current_settings.get('session_timeout', 30))
        self.session_timeout.setSuffix(" minutes")
        layout.addRow("Session Timeout:", self.session_timeout)
        
        # Require password for transactions
        self.password_for_tx = QCheckBox()
        self.password_for_tx.setChecked(
            self.current_settings.get('password_for_transactions', True)
        )
        layout.addRow("Require Password for Transactions:", self.password_for_tx)
        
        # Show full private key
        self.show_pk = QCheckBox()
        self.show_pk.setChecked(
            self.current_settings.get('show_private_keys', False)
        )
        layout.addRow("Allow Viewing Private Keys:", self.show_pk)
        
        # Enable biometric
        self.enable_biometric = QCheckBox()
        self.enable_biometric.setChecked(
            self.current_settings.get('enable_biometric', True)
        )
        layout.addRow("Enable Biometric Auth:", self.enable_biometric)
        
        # Auto-lock on inactive
        self.auto_lock = QCheckBox()
        self.auto_lock.setChecked(
            self.current_settings.get('auto_lock_inactive', True)
        )
        layout.addRow("Auto-Lock on Inactivity:", self.auto_lock)
        
        return widget
    
    def _create_display_tab(self) -> QWidget:
        """Create display settings tab."""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # Theme
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark", "System"])
        current_theme = self.current_settings.get('theme', 'Light')
        self.theme_combo.setCurrentText(current_theme)
        layout.addRow("Theme:", self.theme_combo)
        
        # Font size
        self.font_size = QSpinBox()
        self.font_size.setMinimum(8)
        self.font_size.setMaximum(18)
        self.font_size.setValue(self.current_settings.get('font_size', 11))
        layout.addRow("Font Size:", self.font_size)
        
        # Show balance in USD
        self.show_usd = QCheckBox()
        self.show_usd.setChecked(
            self.current_settings.get('show_balance_usd', True)
        )
        layout.addRow("Show Balance in USD:", self.show_usd)
        
        # Refresh interval
        self.refresh_interval = QSpinBox()
        self.refresh_interval.setMinimum(5)
        self.refresh_interval.setMaximum(300)
        self.refresh_interval.setValue(self.current_settings.get('refresh_interval', 30))
        self.refresh_interval.setSuffix(" seconds")
        layout.addRow("Balance Refresh Interval:", self.refresh_interval)
        
        return widget
    
    def _create_advanced_tab(self) -> QWidget:
        """Create advanced settings tab."""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # Enable logging
        self.enable_logging = QCheckBox()
        self.enable_logging.setChecked(
            self.current_settings.get('enable_logging', True)
        )
        layout.addRow("Enable Logging:", self.enable_logging)
        
        # Log level
        self.log_level = QComboBox()
        self.log_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        current_level = self.current_settings.get('log_level', 'INFO')
        self.log_level.setCurrentText(current_level)
        layout.addRow("Log Level:", self.log_level)
        
        # Enable developer mode
        self.dev_mode = QCheckBox()
        self.dev_mode.setChecked(
            self.current_settings.get('developer_mode', False)
        )
        layout.addRow("Developer Mode:", self.dev_mode)
        
        return widget
    
    def save_settings(self):
        """Save settings."""
        settings = {
            'solana_rpc': self.solana_rpc.text(),
            'nano_node': self.nano_node.text(),
            'arweave_gateway': self.arweave_gateway.text(),
            'network_timeout': self.timeout_spin.value(),
            'retry_attempts': self.retry_spin.value(),
            'session_timeout': self.session_timeout.value(),
            'password_for_transactions': self.password_for_tx.isChecked(),
            'show_private_keys': self.show_pk.isChecked(),
            'enable_biometric': self.enable_biometric.isChecked(),
            'auto_lock_inactive': self.auto_lock.isChecked(),
            'theme': self.theme_combo.currentText(),
            'font_size': self.font_size.value(),
            'show_balance_usd': self.show_usd.isChecked(),
            'refresh_interval': self.refresh_interval.value(),
            'enable_logging': self.enable_logging.isChecked(),
            'log_level': self.log_level.currentText(),
            'developer_mode': self.dev_mode.isChecked(),
        }
        
        self.settings_changed.emit(settings)
        QMessageBox.information(self, "Settings Saved", "Your settings have been saved.")
        self.accept()
    
    def reset_defaults(self):
        """Reset to default settings."""
        reply = QMessageBox.question(
            self,
            "Reset to Defaults",
            "Are you sure you want to reset all settings to defaults?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.solana_rpc.setText('https://api.mainnet-beta.solana.com')
            self.nano_node.setText('https://mynano.ninja/api')
            self.arweave_gateway.setText('https://arweave.net')
            self.timeout_spin.setValue(30)
            self.retry_spin.setValue(3)
            self.session_timeout.setValue(30)
            self.password_for_tx.setChecked(True)
            self.show_pk.setChecked(False)
            self.enable_biometric.setChecked(True)
            self.auto_lock.setChecked(True)
            self.theme_combo.setCurrentText("Light")
            self.font_size.setValue(11)
            self.show_usd.setChecked(True)
            self.refresh_interval.setValue(30)
            self.enable_logging.setChecked(True)
            self.log_level.setCurrentText("INFO")
            self.dev_mode.setChecked(False)
