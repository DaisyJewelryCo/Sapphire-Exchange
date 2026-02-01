"""
Backup and recovery dialogs.
Integrates with Plan 4 (Wallet Backup & Recovery).
"""
from typing import Optional
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit,
    QLineEdit, QProgressBar, QMessageBox, QGroupBox, QCheckBox,
    QListWidget, QListWidgetItem, QFormLayout, QComboBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont


class MnemonicDisplayDialog(QDialog):
    """Dialog for displaying mnemonic with security warnings."""
    
    mnemonic_confirmed = pyqtSignal(str)
    
    def __init__(self, mnemonic: str, wallet_name: str = "", parent=None):
        super().__init__(parent)
        self.mnemonic = mnemonic
        self.wallet_name = wallet_name
        self.confirmed = False
        self.setWindowTitle("Backup Your Mnemonic")
        self.setModal(True)
        self.setMinimumWidth(600)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the UI."""
        layout = QVBoxLayout(self)
        
        warning = QLabel(
            "⚠️ IMPORTANT SECURITY WARNING ⚠️\n\n"
            "This is your wallet's backup phrase. Store it somewhere safe.\n"
            "Anyone with this phrase can access your funds.\n"
            "Never share it with anyone, not even support staff.\n"
            "This phrase will only be shown once."
        )
        warning.setStyleSheet(
            "background: #fff3cd; color: #856404; padding: 15px; "
            "border-radius: 4px; border: 1px solid #ffc107;"
        )
        layout.addWidget(warning)
        
        self.mnemonic_display = QTextEdit()
        self.mnemonic_display.setPlainText(self.mnemonic)
        self.mnemonic_display.setReadOnly(True)
        self.mnemonic_display.setFont(QFont("Courier", 11))
        self.mnemonic_display.setMinimumHeight(120)
        layout.addWidget(self.mnemonic_display)
        
        button_layout = QHBoxLayout()
        
        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.clicked.connect(self.copy_to_clipboard)
        button_layout.addWidget(copy_btn)
        
        save_btn = QPushButton("Save to File")
        save_btn.clicked.connect(self.save_to_file)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
        
        self.understood_check = QCheckBox(
            "I understand that anyone with this phrase can access my funds"
        )
        layout.addWidget(self.understood_check)
        
        self.safe_check = QCheckBox(
            "I have safely stored this phrase and will not lose it"
        )
        layout.addWidget(self.safe_check)
        
        confirm_layout = QHBoxLayout()
        
        self.confirm_btn = QPushButton("I've Saved It Safely")
        self.confirm_btn.setEnabled(False)
        self.confirm_btn.clicked.connect(self.confirm)
        confirm_layout.addWidget(self.confirm_btn)
        
        close_btn = QPushButton("Close Without Confirming")
        close_btn.clicked.connect(self.reject)
        confirm_layout.addWidget(close_btn)
        
        layout.addLayout(confirm_layout)
        
        self.understood_check.stateChanged.connect(self.update_button_state)
        self.safe_check.stateChanged.connect(self.update_button_state)
    
    def update_button_state(self):
        """Update confirm button state based on checkboxes."""
        self.confirm_btn.setEnabled(
            self.understood_check.isChecked() and self.safe_check.isChecked()
        )
    
    def copy_to_clipboard(self):
        """Copy mnemonic to clipboard."""
        from PyQt5.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(self.mnemonic)
        QMessageBox.information(self, "Copied", "Mnemonic copied to clipboard")
    
    def save_to_file(self):
        """Save mnemonic to file."""
        from PyQt5.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Mnemonic",
            f"{self.wallet_name}_mnemonic.txt",
            "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write(f"Wallet: {self.wallet_name}\n")
                    f.write(f"Mnemonic: {self.mnemonic}\n")
                    f.write("\nStore this file securely. Do not store on cloud or email.\n")
                
                QMessageBox.information(self, "Saved", f"Mnemonic saved to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save: {str(e)}")
    
    def confirm(self):
        """Confirm backup."""
        self.confirmed = True
        self.mnemonic_confirmed.emit(self.mnemonic)
        self.accept()


class BackupWizardDialog(QDialog):
    """Wizard for creating complete wallet backups."""
    
    backup_complete = pyqtSignal(dict)
    
    def __init__(self, wallet_info: dict = None, parent=None):
        super().__init__(parent)
        self.wallet_info = wallet_info or {}
        self.backup_data = {}
        self.setWindowTitle("Backup Wizard")
        self.setModal(True)
        self.setMinimumWidth(600)
        self.current_step = 0
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the UI."""
        layout = QVBoxLayout(self)
        
        self.step_label = QLabel("Step 1: Backup Type Selection")
        self.step_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(self.step_label)
        
        self.content_layout = QVBoxLayout()
        layout.addLayout(self.content_layout)
        
        button_layout = QHBoxLayout()
        
        self.prev_btn = QPushButton("< Previous")
        self.prev_btn.clicked.connect(self.previous_step)
        button_layout.addWidget(self.prev_btn)
        
        self.next_btn = QPushButton("Next >")
        self.next_btn.clicked.connect(self.next_step)
        button_layout.addWidget(self.next_btn)
        
        layout.addLayout(button_layout)
        
        self.show_step(0)
    
    def clear_content(self):
        """Clear content layout."""
        while self.content_layout.count():
            self.content_layout.takeAt(0).widget().deleteLater()
    
    def show_step(self, step: int):
        """Show specific step."""
        self.clear_content()
        self.current_step = step
        
        if step == 0:
            self.step_label.setText("Step 1: Select Backup Methods")
            self.show_backup_selection()
        elif step == 1:
            self.step_label.setText("Step 2: Mnemonic Backup")
            self.show_mnemonic_backup()
        elif step == 2:
            self.step_label.setText("Step 3: Physical Backup")
            self.show_physical_backup()
        elif step == 3:
            self.step_label.setText("Step 4: Summary")
            self.show_summary()
        
        self.prev_btn.setEnabled(step > 0)
        self.next_btn.setText("Finish" if step == 3 else "Next >")
    
    def show_backup_selection(self):
        """Show backup method selection."""
        group = QGroupBox("Select Backup Methods")
        layout = QVBoxLayout(group)
        
        self.mnemonic_check = QCheckBox("Mnemonic Backup (BIP39 phrase)")
        self.mnemonic_check.setChecked(True)
        layout.addWidget(self.mnemonic_check)
        
        self.physical_check = QCheckBox("Physical Backup (Printable template)")
        self.physical_check.setChecked(True)
        layout.addWidget(self.physical_check)
        
        self.encrypted_check = QCheckBox("Encrypted Backup (Password protected)")
        self.encrypted_check.setChecked(False)
        layout.addWidget(self.encrypted_check)
        
        self.content_layout.addWidget(group)
    
    def show_mnemonic_backup(self):
        """Show mnemonic backup."""
        label = QLabel("Your Mnemonic Phrase")
        label.setFont(QFont("Arial", 10, QFont.Bold))
        self.content_layout.addWidget(label)
        
        mnemonic_text = QTextEdit()
        mnemonic_text.setPlainText(self.wallet_info.get('mnemonic', ''))
        mnemonic_text.setReadOnly(True)
        self.content_layout.addWidget(mnemonic_text)
    
    def show_physical_backup(self):
        """Show physical backup."""
        label = QLabel(
            "Print this page and store it in a safe location.\n"
            "Never store digital copies on computers or cloud services."
        )
        label.setStyleSheet("color: #ff4136; font-weight: bold;")
        self.content_layout.addWidget(label)
        
        print_btn = QPushButton("Generate Printable Template")
        print_btn.clicked.connect(self.generate_physical_backup)
        self.content_layout.addWidget(print_btn)
    
    def show_summary(self):
        """Show backup summary."""
        summary_label = QLabel("Backup Summary")
        summary_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.content_layout.addWidget(summary_label)
        
        summary_text = QTextEdit()
        summary = "Backups completed:\n\n"
        
        if self.mnemonic_check.isChecked():
            summary += "✓ Mnemonic backup\n"
        if self.physical_check.isChecked():
            summary += "✓ Physical backup\n"
        if self.encrypted_check.isChecked():
            summary += "✓ Encrypted backup\n"
        
        summary += "\nStore your backups in separate secure locations."
        summary_text.setPlainText(summary)
        summary_text.setReadOnly(True)
        self.content_layout.addWidget(summary_text)
    
    def generate_physical_backup(self):
        """Generate physical backup."""
        QMessageBox.information(
            self,
            "Physical Backup",
            "Physical backup template would be generated here.\n"
            "In full implementation, this would create an HTML/PDF template."
        )
    
    def next_step(self):
        """Go to next step."""
        if self.current_step < 3:
            self.show_step(self.current_step + 1)
        else:
            self.backup_complete.emit(self.backup_data)
            self.accept()
    
    def previous_step(self):
        """Go to previous step."""
        if self.current_step > 0:
            self.show_step(self.current_step - 1)


class RecoveryWizardDialog(QDialog):
    """Wizard for recovering wallets."""
    
    recovery_complete = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Wallet Recovery")
        self.setModal(True)
        self.setMinimumWidth(600)
        self.recovered_mnemonic = None
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the UI."""
        layout = QVBoxLayout(self)
        
        title = QLabel("Recover Your Wallet")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title)
        
        form_layout = QFormLayout()
        
        self.method_combo = QComboBox()
        self.method_combo.addItems(["Mnemonic Phrase", "Encrypted Backup", "Recovery Shares"])
        form_layout.addRow("Recovery Method:", self.method_combo)
        
        self.recovery_input = QTextEdit()
        self.recovery_input.setPlaceholderText("Enter your recovery information here")
        self.recovery_input.setMinimumHeight(150)
        form_layout.addRow("Recovery Data:", self.recovery_input)
        
        layout.addLayout(form_layout)
        
        self.progress = QProgressBar()
        layout.addWidget(self.progress)
        
        button_layout = QHBoxLayout()
        
        recover_btn = QPushButton("Recover Wallet")
        recover_btn.clicked.connect(self.recover)
        button_layout.addWidget(recover_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def recover(self):
        """Recover wallet."""
        recovery_data = self.recovery_input.toPlainText().strip()
        
        if not recovery_data:
            QMessageBox.warning(self, "Missing Data", "Please enter recovery data")
            return
        
        try:
            from mnemonic import Mnemonic
            mnemo = Mnemonic("english")
            
            if not mnemo.check(recovery_data):
                QMessageBox.critical(self, "Invalid Data", "Recovery data is invalid")
                return
            
            self.progress.setValue(100)
            self.recovered_mnemonic = recovery_data
            self.recovery_complete.emit(recovery_data)
            
            QMessageBox.information(
                self,
                "Recovery Complete",
                "Wallet recovered successfully.\n"
                "Your addresses will now be synchronized."
            )
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Recovery failed: {str(e)}")
