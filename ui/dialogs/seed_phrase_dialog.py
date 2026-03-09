"""
Seed Phrase Dialog for Sapphire Exchange.
Beautiful dialog for displaying and managing seed phrases.
"""

import json
import os
from datetime import datetime

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QWidget, QTextEdit, QMessageBox, QFileDialog,
    QInputDialog, QLineEdit
)

from blockchain.unified_wallet_generator import UnifiedWalletGenerator
from security.account_backup_manager import AccountBackupManager


class SeedPhraseDialog(QDialog):
    """Beautiful dialog for displaying seed phrase."""

    def __init__(self, seed_phrase, parent=None):
        super().__init__(parent)
        self.seed_phrase = seed_phrase
        self.mnemonic_saved = False
        self.key_backup_saved = False
        self.saved_mnemonic_password = None
        self.wallet_generator = UnifiedWalletGenerator()
        self.setup_ui()

    def setup_ui(self):
        """Create the beautiful seed phrase dialog UI."""
        try:
            self.setWindowTitle("Your New Seed Phrase")
            self.setModal(True)
            self.setMinimumSize(620, 520)
            self.setMaximumSize(820, 760)
            self.resize(700, 620)

            if not self.seed_phrase or not self.seed_phrase.strip():
                raise ValueError("Invalid seed phrase provided")

            main_layout = QVBoxLayout(self)
            main_layout.setContentsMargins(15, 15, 15, 15)
            main_layout.setSpacing(12)

            self._create_ui_elements(main_layout)

        except Exception as e:
            print(f"Error setting up seed phrase dialog: {e}")
            self._create_simple_fallback_ui()

    def _create_ui_elements(self, main_layout):
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

        title = QLabel("🔐 Your New Seed Phrase")
        title.setFont(QFont('Arial', 16, QFont.Bold))
        title.setStyleSheet("color: white; background: transparent;")
        title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel("Complete both steps to continue to login")
        subtitle.setFont(QFont('Arial', 11))
        subtitle.setStyleSheet("color: #e8f4fd; background: transparent;")
        subtitle.setAlignment(Qt.AlignCenter)

        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)

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

        seed_text = QTextEdit()
        seed_text.setPlainText(self.seed_phrase)
        seed_text.setReadOnly(True)
        seed_text.setFont(QFont('Courier New', 12, QFont.Bold))
        seed_text.setFixedHeight(80)
        seed_text.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 10px;
                color: #212529;
                selection-background-color: #007bff;
                selection-color: white;
            }
        """)

        seed_layout.addWidget(seed_title)
        seed_layout.addWidget(seed_text)

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

        warning_title = QLabel("⚠ IMPORTANT SECURITY NOTICE")
        warning_title.setFont(QFont('Arial', 11, QFont.Bold))
        warning_title.setStyleSheet("color: #856404; background: transparent;")

        warning_text = QLabel(
            "• Save an encrypted mnemonic file with your own password\n"
            "• Save an encrypted key backup file (password is your mnemonic)\n"
            "• Both steps are required before you can continue\n"
            "• Never share your seed phrase or backup files"
        )
        warning_text.setFont(QFont('Arial', 9))
        warning_text.setStyleSheet("color: #856404; background: transparent;")
        warning_text.setWordWrap(True)

        warning_layout.addWidget(warning_title)
        warning_layout.addWidget(warning_text)

        steps_frame = QFrame()
        steps_frame.setStyleSheet("""
            QFrame {
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
            }
        """)
        steps_layout = QVBoxLayout(steps_frame)
        steps_layout.setContentsMargins(12, 12, 12, 12)
        steps_layout.setSpacing(10)

        step1_layout = QHBoxLayout()
        self.step1_status = QLabel("○ Step 1: Save encrypted mnemonic")
        self.step1_status.setFont(QFont('Arial', 10, QFont.Bold))
        self.step1_status.setStyleSheet("color: #dc3545;")

        self.save_mnemonic_button = QPushButton("Save Encrypted Mnemonic")
        self.save_mnemonic_button.setFixedHeight(34)
        self.save_mnemonic_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 8px 14px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        self.save_mnemonic_button.clicked.connect(self.save_encrypted_mnemonic)

        step1_layout.addWidget(self.step1_status, 1)
        step1_layout.addWidget(self.save_mnemonic_button)

        step2_layout = QHBoxLayout()
        self.step2_status = QLabel("○ Step 2: Save key backup")
        self.step2_status.setFont(QFont('Arial', 10, QFont.Bold))
        self.step2_status.setStyleSheet("color: #dc3545;")

        self.save_key_backup_button = QPushButton("Save Key Backup")
        self.save_key_backup_button.setFixedHeight(34)
        self.save_key_backup_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 8px 14px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        self.save_key_backup_button.clicked.connect(self.save_key_backup)

        step2_layout.addWidget(self.step2_status, 1)
        step2_layout.addWidget(self.save_key_backup_button)

        steps_layout.addLayout(step1_layout)
        steps_layout.addLayout(step2_layout)

        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 10, 0, 0)

        self.confirm_button = QPushButton("Continue to Login")
        self.confirm_button.setFixedHeight(40)
        self.confirm_button.setMinimumWidth(220)
        self.confirm_button.setEnabled(False)
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
            QPushButton:disabled {
                background-color: #adb5bd;
                color: #f8f9fa;
            }
        """)
        self.confirm_button.clicked.connect(self.accept)

        button_layout.addStretch()
        button_layout.addWidget(self.confirm_button)
        button_layout.addStretch()

        main_layout.addWidget(header_frame)
        main_layout.addWidget(seed_frame)
        main_layout.addWidget(warning_frame)
        main_layout.addWidget(steps_frame)
        main_layout.addLayout(button_layout)

        self.adjustSize()

        if self.parent():
            self.center_on_parent()

    def _create_simple_fallback_ui(self):
        try:
            if self.layout():
                QWidget().setLayout(self.layout())

            layout = QVBoxLayout(self)
            layout.setContentsMargins(20, 20, 20, 20)
            layout.setSpacing(15)

            title = QLabel("Your New Seed Phrase")
            title.setFont(QFont('Arial', 16, QFont.Bold))
            title.setAlignment(Qt.AlignCenter)
            title.setStyleSheet("color: #2b7bba; margin-bottom: 10px;")

            warning = QLabel("⚠️ IMPORTANT: Save both required backup files before continuing")
            warning.setFont(QFont('Arial', 12, QFont.Bold))
            warning.setAlignment(Qt.AlignCenter)
            warning.setStyleSheet("color: #d63384; margin-bottom: 15px;")
            warning.setWordWrap(True)

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

            self.save_mnemonic_button = QPushButton("Save Encrypted Mnemonic")
            self.save_mnemonic_button.clicked.connect(self.save_encrypted_mnemonic)

            self.save_key_backup_button = QPushButton("Save Key Backup")
            self.save_key_backup_button.clicked.connect(self.save_key_backup)

            self.confirm_button = QPushButton("Continue to Login")
            self.confirm_button.setEnabled(False)
            self.confirm_button.clicked.connect(self.accept)

            layout.addWidget(title)
            layout.addWidget(warning)
            layout.addWidget(seed_display)
            layout.addWidget(self.save_mnemonic_button, 0, Qt.AlignCenter)
            layout.addWidget(self.save_key_backup_button, 0, Qt.AlignCenter)
            layout.addStretch()
            layout.addWidget(self.confirm_button, 0, Qt.AlignCenter)

            self.resize(500, 420)

        except Exception as e:
            print(f"Even fallback UI failed: {e}")
            QMessageBox.information(self, "Seed Phrase", f"Your seed phrase:\n\n{self.seed_phrase}")
            self.accept()

    def center_on_parent(self):
        try:
            parent = self.parent()
            if parent:
                parent_rect = parent.geometry()
                x = parent_rect.x() + (parent_rect.width() - self.width()) // 2
                y = parent_rect.y() + (parent_rect.height() - self.height()) // 2
                self.move(x, y)
        except Exception as e:
            print(f"Failed to center dialog: {e}")

    def showEvent(self, event):
        super().showEvent(event)
        if self.parent():
            QTimer.singleShot(10, self.center_on_parent)

    def update_step_states(self):
        if hasattr(self, 'step1_status'):
            if self.mnemonic_saved:
                self.step1_status.setText("✓ Step 1: Save encrypted mnemonic")
                self.step1_status.setStyleSheet("color: #28a745;")
            else:
                self.step1_status.setText("○ Step 1: Save encrypted mnemonic")
                self.step1_status.setStyleSheet("color: #dc3545;")

        if hasattr(self, 'step2_status'):
            if self.key_backup_saved:
                self.step2_status.setText("✓ Step 2: Save key backup")
                self.step2_status.setStyleSheet("color: #28a745;")
            else:
                self.step2_status.setText("○ Step 2: Save key backup")
                self.step2_status.setStyleSheet("color: #dc3545;")

        if hasattr(self, 'confirm_button'):
            self.confirm_button.setEnabled(self.mnemonic_saved and self.key_backup_saved)

    def _prompt_password(self, title, prompt):
        password, ok = QInputDialog.getText(self, title, prompt, QLineEdit.Password)
        if not ok:
            return None
        password = password.strip()
        if not password:
            QMessageBox.warning(self, "Password Required", "Password cannot be empty.")
            return None

        confirm, ok_confirm = QInputDialog.getText(self, title, "Confirm password:", QLineEdit.Password)
        if not ok_confirm:
            return None
        if password != confirm:
            QMessageBox.warning(self, "Mismatch", "Passwords do not match.")
            return None

        return password

    def save_encrypted_mnemonic(self):
        try:
            password = self._prompt_password(
                "Set Mnemonic Encryption Password",
                "Enter password to encrypt your mnemonic file:"
            )
            if not password:
                return

            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Encrypted Mnemonic",
                "sapphire_mnemonic_backup.mnemonic.enc",
                "Encrypted Files (*.enc);;All Files (*)"
            )
            if not file_path:
                return

            salt = os.urandom(16)
            nonce = os.urandom(12)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = kdf.derive(password.encode('utf-8'))

            cipher = AESGCM(key)
            ciphertext = cipher.encrypt(nonce, self.seed_phrase.encode('utf-8'), None)

            payload = {
                'version': '1.0',
                'type': 'sapphire_mnemonic_backup',
                'kdf': {
                    'name': 'PBKDF2-HMAC-SHA256',
                    'iterations': 100000,
                    'salt': salt.hex(),
                },
                'cipher': {
                    'name': 'AES-256-GCM',
                    'nonce': nonce.hex(),
                    'ciphertext': ciphertext.hex(),
                },
                'created_at': datetime.utcnow().isoformat(),
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=2)

            self.saved_mnemonic_password = password
            self.mnemonic_saved = True
            self.update_step_states()
            QMessageBox.information(self, "Saved", f"Encrypted mnemonic saved:\n{file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save encrypted mnemonic: {str(e)}")

    def save_key_backup(self):
        try:
            wallet = self.wallet_generator.create_from_mnemonic(
                "account_setup_backup",
                self.seed_phrase,
                passphrase="",
                assets=['nano', 'solana', 'arweave']
            )

            wallet_data = {}
            if wallet.nano_wallet:
                wallet_data['nano'] = wallet.nano_wallet.to_dict()
            if wallet.solana_wallet:
                wallet_data['solana'] = wallet.solana_wallet.to_dict()
            if wallet.arweave_wallet:
                wallet_data['arweave'] = wallet.arweave_wallet.to_dict()

            if not wallet_data:
                QMessageBox.warning(self, "Failed", "Unable to generate wallet keys from mnemonic.")
                return

            nano_address = ''
            solana_address = ''
            arweave_address = ''
            if isinstance(wallet_data.get('nano'), dict):
                nano_address = wallet_data['nano'].get('address', '')
            if isinstance(wallet_data.get('solana'), dict):
                solana_address = wallet_data['solana'].get('address', '')
            if isinstance(wallet_data.get('arweave'), dict):
                arweave_address = wallet_data['arweave'].get('address', '')

            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Key Backup",
                "sapphire_key_backup.account.enc",
                "Encrypted Account Backup (*.account.enc);;All Files (*)"
            )
            if not file_path:
                return

            private_keys = {}
            if isinstance(wallet_data.get('nano'), dict):
                private_keys['nano_private_key'] = wallet_data['nano'].get('private_key')
                private_keys['nano_seed'] = wallet_data['nano'].get('seed')
            if isinstance(wallet_data.get('solana'), dict):
                private_keys['solana_private_key'] = wallet_data['solana'].get('private_key')
                private_keys['solana_seed'] = wallet_data['solana'].get('seed')
            if isinstance(wallet_data.get('arweave'), dict):
                private_keys['arweave_jwk'] = wallet_data['arweave'].get('jwk')

            backup_payload = {
                'type': 'sapphire_key_backup',
                'version': '1.0',
                'nano_address': nano_address,
                'solana_address': solana_address,
                'arweave_address': arweave_address,
                'wallets': wallet_data,
                'private_keys': private_keys,
                'created_at': datetime.utcnow().isoformat(),
            }

            plaintext = json.dumps(backup_payload).encode('utf-8')
            backup_key = AccountBackupManager.derive_key_from_mnemonic(self.seed_phrase)
            backup_cipher = AESGCM(backup_key)
            iv = os.urandom(12)
            ciphertext_and_tag = backup_cipher.encrypt(iv, plaintext, None)
            ciphertext = ciphertext_and_tag[:-16]
            tag = ciphertext_and_tag[-16:]

            encrypted_blob = {
                'nano_address': nano_address,
                'solana_address': solana_address,
                'arweave_address': arweave_address,
                'ciphertext': ciphertext.hex(),
                'iv': iv.hex(),
                'tag': tag.hex(),
                'password_hint': 'Use your mnemonic phrase to decrypt this backup.',
                'created_at': datetime.utcnow().isoformat(),
                'type': 'sapphire_key_backup_enc',
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(encrypted_blob, f, indent=2)

            self.key_backup_saved = True
            self.update_step_states()
            QMessageBox.information(
                self,
                "Saved",
                f"Encrypted key backup saved:\n{file_path}\n\nPassword for this backup is your mnemonic phrase."
            )

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save key backup: {str(e)}")