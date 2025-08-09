"""
Seed Phrase Dialog for Sapphire Exchange.
Beautiful dialog for displaying and managing seed phrases.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGridLayout, QWidget, QTextEdit, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont


class SeedPhraseDialog(QDialog):
    """Beautiful dialog for displaying seed phrase."""
    
    def __init__(self, seed_phrase, parent=None):
        super().__init__(parent)
        self.seed_phrase = seed_phrase
        self.setup_ui()
    
    def setup_ui(self):
        """Create the beautiful seed phrase dialog UI."""
        try:
            self.setWindowTitle("Your New Seed Phrase")
            self.setModal(True)
            
            # Set initial size and constraints
            self.setMinimumSize(550, 450)
            self.setMaximumSize(750, 650)
            self.resize(650, 550)
            
            # Ensure we have a valid seed phrase
            if not self.seed_phrase or not self.seed_phrase.strip():
                raise ValueError("Invalid seed phrase provided")
            
            # Main layout with proper spacing
            main_layout = QVBoxLayout(self)
            main_layout.setContentsMargins(15, 15, 15, 15)
            main_layout.setSpacing(12)
            
            self._create_ui_elements(main_layout)
            
        except Exception as e:
            print(f"Error setting up seed phrase dialog: {e}")
            # Fallback to simple dialog
            self._create_simple_fallback_ui()
    
    def _create_ui_elements(self, main_layout):
        """Create all UI elements for the dialog."""
        # Header section
        header_frame = QFrame()
        header_frame.setFixedHeight(80)
        header_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #2b7bba, stop:1 #1a5a8f);
                border-radius: 8px;
            }
        """)
        
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 10, 15, 10)
        header_layout.setSpacing(5)
        
        # Title
        title = QLabel("🔐 Your New Seed Phrase")
        title.setFont(QFont('Arial', 16, QFont.Bold))
        title.setStyleSheet("color: white; background: transparent;")
        title.setAlignment(Qt.AlignCenter)
        
        # Subtitle
        subtitle = QLabel("This is your unique recovery phrase")
        subtitle.setFont(QFont('Arial', 11))
        subtitle.setStyleSheet("color: #e8f4fd; background: transparent;")
        subtitle.setAlignment(Qt.AlignCenter)
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        
        # Warning section
        warning_frame = QFrame()
        warning_frame.setStyleSheet("""
            QFrame {
                background-color: #fff3cd;
                border: 1px solid #ffeaa7;
                border-radius: 6px;
            }
        """)
        
        warning_layout = QVBoxLayout(warning_frame)
        warning_layout.setContentsMargins(12, 10, 12, 10)
        warning_layout.setSpacing(5)
        
        warning_title = QLabel("⚠️ IMPORTANT SECURITY NOTICE")
        warning_title.setFont(QFont('Arial', 11, QFont.Bold))
        warning_title.setStyleSheet("color: #856404; background: transparent;")
        
        warning_text = QLabel(
            "• Write down these words in the exact order shown\n"
            "• Store them in a safe, offline location\n"
            "• Never share your seed phrase with anyone\n"
            "• This is the ONLY way to recover your account"
        )
        warning_text.setFont(QFont('Arial', 9))
        warning_text.setStyleSheet("color: #856404; background: transparent;")
        warning_text.setWordWrap(True)
        
        warning_layout.addWidget(warning_title)
        warning_layout.addWidget(warning_text)
        
        # Seed phrase display
        seed_frame = QFrame()
        seed_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 2px solid #e9ecef;
                border-radius: 8px;
            }
        """)
        
        seed_layout = QVBoxLayout(seed_frame)
        seed_layout.setContentsMargins(15, 12, 15, 12)
        seed_layout.setSpacing(8)
        
        seed_title = QLabel("Your Seed Phrase:")
        seed_title.setFont(QFont('Arial', 11, QFont.Bold))
        seed_title.setStyleSheet("color: #495057; background: transparent;")
        
        # Create a container widget for the words grid
        words_container = QWidget()
        words_container.setStyleSheet("background: transparent;")
        words_grid = QGridLayout(words_container)
        words_grid.setSpacing(8)
        words_grid.setContentsMargins(5, 5, 5, 5)
        
        # Split seed phrase into words
        words = self.seed_phrase.split()
        
        # Calculate grid dimensions (prefer 3 columns)
        cols = 3
        rows = (len(words) + cols - 1) // cols
        
        for i, word in enumerate(words):
            word_frame = QFrame()
            word_frame.setFixedHeight(35)
            word_frame.setMinimumWidth(80)
            word_frame.setStyleSheet("""
                QFrame {
                    background-color: white;
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                }
            """)
            
            word_layout = QHBoxLayout(word_frame)
            word_layout.setContentsMargins(8, 5, 8, 5)
            word_layout.setSpacing(5)
            
            # Word number
            number_label = QLabel(f"{i+1}.")
            number_label.setFont(QFont('Arial', 9, QFont.Bold))
            number_label.setStyleSheet("color: #6c757d; background: transparent;")
            number_label.setFixedWidth(18)
            
            # Word text
            word_label = QLabel(word)
            word_label.setFont(QFont('Courier New', 10, QFont.Bold))
            word_label.setStyleSheet("color: #212529; background: transparent;")
            
            word_layout.addWidget(number_label)
            word_layout.addWidget(word_label)
            word_layout.addStretch()
            
            # Add to grid
            row = i // cols
            col = i % cols
            words_grid.addWidget(word_frame, row, col)
        
        # Ensure grid columns have equal stretch
        for col in range(cols):
            words_grid.setColumnStretch(col, 1)
        
        seed_layout.addWidget(seed_title)
        seed_layout.addWidget(words_container)
        
        # Copy button section
        copy_layout = QHBoxLayout()
        copy_layout.setContentsMargins(0, 5, 0, 5)
        
        self.copy_button = QPushButton("📋 Copy to Clipboard")
        self.copy_button.setFixedHeight(32)
        self.copy_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:pressed {
                background-color: #545b62;
            }
        """)
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        
        copy_layout.addStretch()
        copy_layout.addWidget(self.copy_button)
        copy_layout.addStretch()
        
        # Confirm button section
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 10, 0, 0)
        
        self.confirm_button = QPushButton("I've Saved My Seed Phrase")
        self.confirm_button.setFixedHeight(40)
        self.confirm_button.setMinimumWidth(200)
        self.confirm_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)
        self.confirm_button.clicked.connect(self.accept)
        
        button_layout.addStretch()
        button_layout.addWidget(self.confirm_button)
        button_layout.addStretch()
        
        # Add all sections to main layout
        main_layout.addWidget(header_frame)
        main_layout.addWidget(warning_frame)
        main_layout.addWidget(seed_frame, 1)  # Give seed frame most space
        main_layout.addLayout(copy_layout)
        main_layout.addLayout(button_layout)
        
        # Ensure dialog shows properly
        self.adjustSize()
        
        # Center on parent if available
        if self.parent():
            self.center_on_parent()
    
    def _create_simple_fallback_ui(self):
        """Create a simple fallback UI if the main UI fails to load."""
        try:
            # Clear any existing layout
            if self.layout():
                QWidget().setLayout(self.layout())
            
            # Create simple layout
            layout = QVBoxLayout(self)
            layout.setContentsMargins(20, 20, 20, 20)
            layout.setSpacing(15)
            
            # Title
            title = QLabel("Your New Seed Phrase")
            title.setFont(QFont('Arial', 16, QFont.Bold))
            title.setAlignment(Qt.AlignCenter)
            title.setStyleSheet("color: #2b7bba; margin-bottom: 10px;")
            
            # Warning
            warning = QLabel("⚠️ IMPORTANT: Write down these words and store them safely!")
            warning.setFont(QFont('Arial', 12, QFont.Bold))
            warning.setAlignment(Qt.AlignCenter)
            warning.setStyleSheet("color: #d63384; margin-bottom: 15px;")
            warning.setWordWrap(True)
            
            # Seed phrase display (simple text)
            seed_display = QTextEdit()
            seed_display.setPlainText(self.seed_phrase)
            seed_display.setReadOnly(True)
            seed_display.setFont(QFont('Courier New', 12))
            seed_display.setMaximumHeight(100)
            seed_display.setStyleSheet("""
                QTextEdit {
                    background-color: #f8f9fa;
                    border: 2px solid #dee2e6;
                    border-radius: 4px;
                    padding: 10px;
                }
            """)
            
            # Copy button
            self.copy_button = QPushButton("Copy to Clipboard")
            self.copy_button.clicked.connect(self.copy_to_clipboard)
            self.copy_button.setStyleSheet("""
                QPushButton {
                    background-color: #6c757d;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #5a6268;
                }
            """)
            
            # Confirm button
            self.confirm_button = QPushButton("I've Saved My Seed Phrase")
            self.confirm_button.clicked.connect(self.accept)
            self.confirm_button.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    border: none;
                    padding: 12px 24px;
                    border-radius: 6px;
                    font-weight: bold;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #218838;
                }
            """)
            
            # Add widgets to layout
            layout.addWidget(title)
            layout.addWidget(warning)
            layout.addWidget(seed_display)
            layout.addWidget(self.copy_button, 0, Qt.AlignCenter)
            layout.addStretch()
            layout.addWidget(self.confirm_button, 0, Qt.AlignCenter)
            
            # Adjust size for fallback
            self.resize(500, 400)
            
        except Exception as e:
            print(f"Even fallback UI failed: {e}")
            # Last resort - just show the seed phrase in a message box
            QMessageBox.information(self, "Seed Phrase", f"Your seed phrase:\n\n{self.seed_phrase}")
            self.accept()
    
    def center_on_parent(self):
        """Center the dialog on its parent window."""
        try:
            parent = self.parent()
            if parent:
                # Get parent geometry
                parent_rect = parent.geometry()
                
                # Calculate center position
                x = parent_rect.x() + (parent_rect.width() - self.width()) // 2
                y = parent_rect.y() + (parent_rect.height() - self.height()) // 2
                
                # Move dialog to center
                self.move(x, y)
        except Exception as e:
            print(f"Failed to center dialog: {e}")
    
    def showEvent(self, event):
        """Override showEvent to ensure proper centering."""
        super().showEvent(event)
        # Re-center after the dialog is fully shown and sized
        if self.parent():
            QTimer.singleShot(10, self.center_on_parent)
    
    def copy_to_clipboard(self):
        """Copy seed phrase to clipboard."""
        try:
            from PyQt5.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(self.seed_phrase)
            
            # Temporarily change button text to show feedback
            original_text = self.copy_button.text()
            self.copy_button.setText("✅ Copied!")
            self.copy_button.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                    font-size: 12px;
                }
            """)
            
            # Reset button after 2 seconds
            QTimer.singleShot(2000, lambda: self.reset_copy_button(original_text))
            
        except Exception as e:
            QMessageBox.warning(self, "Copy Failed", f"Failed to copy to clipboard: {str(e)}")
    
    def reset_copy_button(self, original_text):
        """Reset copy button to original state."""
        self.copy_button.setText(original_text)
        self.copy_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:pressed {
                background-color: #545b62;
            }
        """)