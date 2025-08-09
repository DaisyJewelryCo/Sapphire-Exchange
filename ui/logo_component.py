"""
Logo Component for Sapphire Exchange.
Reusable logo component that can be used across all screens.
"""

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont


class LogoComponent(QWidget):
    """Reusable logo component for Sapphire Exchange."""
    
    # Signal emitted when logo is clicked (for navigation to home)
    logo_clicked = pyqtSignal()
    
    def __init__(self, size="normal", clickable=True, compact=False, parent=None):
        """
        Initialize the logo component.
        
        Args:
            size: "small", "normal", or "large"
            clickable: Whether the logo should be clickable
            compact: Whether to use compact layout (no stretch)
            parent: Parent widget
        """
        super().__init__(parent)
        self.size = size
        self.clickable = clickable
        self.compact = compact
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the logo UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Size configurations
        size_config = {
            "small": {
                "icon_size": "16px",
                "text_size": 16,
                "font_weight": QFont.Bold
            },
            "normal": {
                "icon_size": "20px", 
                "text_size": 20,
                "font_weight": QFont.Bold
            },
            "large": {
                "icon_size": "28px",
                "text_size": 28,
                "font_weight": QFont.Bold
            }
        }
        
        config = size_config.get(self.size, size_config["normal"])
        
        if self.clickable:
            # Create clickable logo button
            self.logo_button = QPushButton()
            self.logo_button.clicked.connect(self.logo_clicked.emit)
            
            # Create logo content
            logo_layout = QHBoxLayout(self.logo_button)
            logo_layout.setContentsMargins(8, 4, 8, 4)
            logo_layout.setSpacing(8)
            
            # Gavel icon (using emoji as fallback)
            self.icon_label = QLabel("⚖️")
            self.icon_label.setStyleSheet(f"""
                QLabel {{
                    font-size: {config['icon_size']};
                    color: #000000;
                    background-color: transparent;
                    border: none;
                    padding: 0;
                }}
            """)
            logo_layout.addWidget(self.icon_label)
            
            # SapphireX text
            self.text_label = QLabel("SapphireX")
            self.text_label.setFont(QFont('Inter', config['text_size'], config['font_weight']))
            self.text_label.setStyleSheet("""
                QLabel {
                    color: #000000;
                    background-color: transparent;
                    border: none;
                    padding: 0;
                }
            """)
            logo_layout.addWidget(self.text_label)
            
            # Style the button
            self.logo_button.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    padding: 4px 8px;
                    border-radius: 6px;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: #f1f5f9;
                }
                QPushButton:pressed {
                    background-color: #e2e8f0;
                }
            """)
            
            layout.addWidget(self.logo_button)
        else:
            # Create non-clickable logo
            # Gavel icon
            self.icon_label = QLabel("⚖️")
            self.icon_label.setStyleSheet(f"""
                QLabel {{
                    font-size: {config['icon_size']};
                    color: #000000;
                    background-color: transparent;
                    border: none;
                    padding: 0;
                }}
            """)
            layout.addWidget(self.icon_label)
            
            # SapphireX text
            self.text_label = QLabel("SapphireX")
            self.text_label.setFont(QFont('Inter', config['text_size'], config['font_weight']))
            self.text_label.setStyleSheet("""
                QLabel {
                    color: #000000;
                    background-color: transparent;
                    border: none;
                    padding: 0;
                }
            """)
            layout.addWidget(self.text_label)
        
        # Add stretch only if not in compact mode
        if not self.compact:
            layout.addStretch()
        
        # Set size policy to prevent unnecessary expansion
        from PyQt5.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
    
    def sizeHint(self):
        """Return the preferred size for the logo component."""
        from PyQt5.QtCore import QSize
        # Calculate size based on content
        if self.size == "small":
            return QSize(120, 32)
        elif self.size == "normal":
            return QSize(140, 36)
        elif self.size == "large":
            return QSize(160, 40)
        return QSize(140, 36)
    
    def set_color(self, color="#000000"):
        """Set the logo color."""
        if hasattr(self, 'text_label'):
            self.text_label.setStyleSheet(f"""
                QLabel {{
                    color: {color};
                    background-color: transparent;
                    border: none;
                    padding: 0;
                }}
            """)


class HeaderWithLogo(QWidget):
    """Header component with logo for screens that need a header."""
    
    # Signal emitted when logo is clicked
    logo_clicked = pyqtSignal()
    
    def __init__(self, title="", show_title=True, parent=None):
        """
        Initialize header with logo.
        
        Args:
            title: Optional title to show next to logo
            show_title: Whether to show the title
            parent: Parent widget
        """
        super().__init__(parent)
        self.title = title
        self.show_title = show_title
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the header UI."""
        self.setFixedHeight(60)
        self.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border-bottom: 1px solid #e2e8f0;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(16)
        
        # Logo
        self.logo = LogoComponent(size="normal", clickable=True)
        self.logo.logo_clicked.connect(self.logo_clicked.emit)
        layout.addWidget(self.logo)
        
        # Optional title
        if self.show_title and self.title:
            # Separator
            separator = QLabel("|")
            separator.setStyleSheet("color: #e2e8f0; font-size: 20px;")
            layout.addWidget(separator)
            
            # Title
            title_label = QLabel(self.title)
            title_label.setFont(QFont('Inter', 18, QFont.Medium))
            title_label.setStyleSheet("color: #64748b;")
            layout.addWidget(title_label)
        
        # Add stretch to push everything to the left
        layout.addStretch()
    
    def set_title(self, title):
        """Update the header title."""
        self.title = title
        # Refresh the UI if needed
        if hasattr(self, 'title_label'):
            self.title_label.setText(title)