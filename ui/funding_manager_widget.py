"""
Funding Manager Widget for Sapphire Exchange.
Provides a step-by-step wizard for funding wallet with USDC, purchasing Arweave, and accessing Nano funds.
"""

import io
import qrcode
from PIL import Image
from datetime import datetime
from decimal import Decimal, InvalidOperation

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QDialog,
    QProgressBar, QGroupBox, QLineEdit, QMessageBox, QScrollArea,
    QFrame, QListWidget, QListWidgetItem, QApplication, QTableWidget,
    QTableWidgetItem, QHeaderView
)
from PyQt5.QtCore import Qt, pyqtSignal, QUrl, QTimer
from PyQt5.QtGui import QFont, QColor, QDesktopServices, QPixmap

from services.application_service import app_service
from services.nano_cloudflare_service import get_nano_cloudflare_service
from services.funding_manager_service import get_funding_manager_service
from services.transaction_tracker import get_transaction_tracker
from utils.async_worker import AsyncWorker
from utils.validation_utils import Validator


class RequestNanoDialog(QDialog):
    """Dialog for requesting Nano via Cloudflare Worker."""
    
    def __init__(self, nano_address: str, parent=None):
        super().__init__(parent)
        self.nano_address = nano_address
        self.setWindowTitle("Request Nano")
        self.setModal(True)
        self.setMinimumWidth(400)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the request Nano dialog UI."""
        layout = QVBoxLayout(self)
        
        title = QLabel("Request Nano via Cloudflare Worker")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title)
        
        info = QLabel(
            "Enter the amount of Nano you want to request.\n"
            "The amount will be sent to your Nano address.\n\n"
            "Maximum: 1 Nano per request"
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #666;")
        layout.addWidget(info)
        
        form_layout = QVBoxLayout()
        
        amount_label = QLabel("Amount (Nano):")
        amount_label.setStyleSheet("font-weight: bold;")
        form_layout.addWidget(amount_label)
        
        self.amount_edit = QLineEdit()
        self.amount_edit.setPlaceholderText("0.001")
        self.amount_edit.setText("0.001")
        form_layout.addWidget(self.amount_edit)
        
        hint = QLabel("Enter decimal amount (e.g., 0.001, 0.01, 0.1)")
        hint.setStyleSheet("font-size: 10px; color: #999;")
        form_layout.addWidget(hint)
        
        layout.addLayout(form_layout)
        
        address_layout = QVBoxLayout()
        
        address_label = QLabel("Destination Address:")
        address_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        address_layout.addWidget(address_label)
        
        address_display = QLineEdit()
        address_display.setText(self.nano_address)
        address_display.setReadOnly(True)
        address_display.setFont(QFont("Courier", 9))
        address_layout.addWidget(address_display)
        
        layout.addLayout(address_layout)
        
        button_layout = QHBoxLayout()
        
        self.request_btn = QPushButton("🚀 Send Request")
        self.request_btn.setStyleSheet("""
            QPushButton {
                background-color: #8b5cf6;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7c3aed;
            }
            QPushButton:pressed {
                background-color: #6d28d9;
            }
        """)
        self.request_btn.clicked.connect(self.request_nano)
        button_layout.addWidget(self.request_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("margin-top: 10px; padding: 10px; border-radius: 4px;")
        layout.addWidget(self.status_label)
    
    def request_nano(self):
        """Request Nano via Cloudflare Worker with validation."""
        amount_text = self.amount_edit.text().strip()
        
        if not amount_text:
            QMessageBox.warning(self, "Invalid Input", "Please enter an amount.")
            return
        
        try:
            amount_decimal = Decimal(amount_text)
        except InvalidOperation:
            QMessageBox.warning(self, "Invalid Amount", "Please enter a valid amount.")
            return
        
        if amount_decimal <= 0:
            QMessageBox.warning(self, "Invalid Amount", "Amount must be positive")
            return
        
        if amount_decimal.as_tuple().exponent < -30:
            QMessageBox.warning(self, "Invalid Amount", "Amount has too many decimal places")
            return
        
        amount_float = float(amount_decimal)
        
        funding_service = get_funding_manager_service()
        if not funding_service.config.enable_cloudflare_nano:
            QMessageBox.warning(self, "Unavailable", "Nano requests are disabled in configuration.")
            return
        
        is_config_valid, config_errors = funding_service.validate_config()
        if not is_config_valid:
            QMessageBox.warning(self, "Configuration Error", "\n".join(config_errors))
            return
        
        if not Validator.validate_nano_address(self.nano_address):
            QMessageBox.warning(self, "Invalid Address", "Invalid Nano address configured.")
            return
        
        is_valid, error = funding_service.validate_nano_amount(amount_float)
        if not is_valid:
            QMessageBox.warning(self, "Invalid Amount", error)
            return
        
        self.request_btn.setEnabled(False)
        self.status_label.setText("⏳ Sending request to Cloudflare Worker...")
        self.status_label.setStyleSheet("background-color: #fef3c7; padding: 10px; border-radius: 4px; color: #92400e;")
        QApplication.processEvents()
        
        self._last_amount_text = str(amount_decimal)
        amount_raw = str(int((amount_decimal * Decimal("1e30")).to_integral_value()))
        
        worker = AsyncWorker(self._execute_request(amount_raw))
        worker.finished.connect(self._on_request_complete)
        worker.error.connect(self._on_request_error)
        worker.start()
        self._worker = worker
    
    async def _execute_request(self, amount_raw: str):
        """Execute Nano request."""
        try:
            service = await get_nano_cloudflare_service()
            result = await service.request_nano(self.nano_address, amount_raw)
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _track_nano_request(self, tx_hash: str, amount: str):
        user = app_service.get_current_user()
        if not user:
            return
        
        tracker = await get_transaction_tracker()
        tx = tracker.create_transaction(
            user_id=user.id,
            currency="NANO",
            tx_type="receive",
            amount=amount,
            from_address="cloudflare_worker",
            to_address=self.nano_address,
            tx_hash=tx_hash,
            metadata={"source": "cloudflare_worker"}
        )
        await tracker.track_pending_transaction(tx)
    
    def _on_request_complete(self, result):
        """Handle request completion with logging."""
        self.request_btn.setEnabled(True)
        funding_service = get_funding_manager_service()
        
        if result and result.get("success"):
            tx_hash = result.get("hash", "")
            display_hash = tx_hash[:16] + "..." if len(tx_hash) > 16 else tx_hash
            retry_count = result.get("retry_count", 0)
            
            # Log successful transaction
            funding_service.log_transaction("nano_request", {
                "address": self.nano_address,
                "tx_hash": tx_hash,
                "retry_count": retry_count,
                "status": "success"
            }, True)
            
            if tx_hash:
                track_worker = AsyncWorker(self._track_nano_request(tx_hash, self._last_amount_text))
                track_worker.start()
                self._track_worker = track_worker
            
            retry_msg = f" (after {retry_count} retries)" if retry_count > 0 else ""
            self.status_label.setText(
                f"✓ Nano request successful{retry_msg}!\n\n"
                f"Transaction: {display_hash}\n\n"
                f"Nano will appear in your wallet shortly."
            )
            self.status_label.setStyleSheet("background-color: #dcfce7; padding: 10px; border-radius: 4px; color: #166534;")
            
            QMessageBox.information(self, "Success", 
                f"Nano request sent successfully!\n\n"
                f"Transaction ID: {tx_hash}\n\n"
                f"Check your wallet for incoming Nano.")
            
            self.accept()
        else:
            error = result.get("error", "Unknown error") if result else "Unknown error"
            retry_count = result.get("retry_count", 0) if result else 0
            
            # Log failed transaction
            funding_service.log_transaction("nano_request", {
                "address": self.nano_address,
                "error": error,
                "retry_count": retry_count,
                "status": "failed"
            }, False)
            
            self.status_label.setText(f"✗ Request failed: {error}")
            self.status_label.setStyleSheet("background-color: #fee2e2; padding: 10px; border-radius: 4px; color: #991b1b;")
            
            QMessageBox.warning(self, "Request Failed", f"Error: {error}")
    
    def _on_request_error(self, error):
        """Handle request error with logging."""
        self.request_btn.setEnabled(True)
        funding_service = get_funding_manager_service()
        
        # Log error
        funding_service.log_transaction("nano_request", {
            "address": self.nano_address,
            "error": str(error),
            "status": "error"
        }, False)
        
        self.status_label.setText(f"✗ Error: {str(error)}")
        self.status_label.setStyleSheet("background-color: #fee2e2; padding: 10px; border-radius: 4px; color: #991b1b;")
        
        QMessageBox.critical(self, "Error", f"Request failed: {str(error)}")


class FundingWizardDialog(QDialog):
    """Multi-step funding wizard dialog."""
    
    funding_complete = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Wallet Funding Wizard")
        self.setModal(True)
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        
        self.current_step = 0
        self.tracker = None
        self.setup_ui()
        self.init_tracker()
    
    def setup_ui(self):
        """Setup the wizard UI."""
        layout = QVBoxLayout(self)
        
        header_layout = QHBoxLayout()
        title = QLabel("Wallet Funding Setup Wizard")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        header_layout.addWidget(title)
        
        self.step_indicator = QLabel("Step 1 of 3")
        self.step_indicator.setFont(QFont("Arial", 10))
        self.step_indicator.setStyleSheet("color: #666;")
        header_layout.addStretch()
        header_layout.addWidget(self.step_indicator)
        
        layout.addLayout(header_layout)
        
        layout.addWidget(self._create_separator())
        
        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidget(self.content_area)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)
        
        layout.addWidget(self._create_separator())
        
        button_layout = QHBoxLayout()
        
        self.prev_btn = QPushButton("← Previous")
        self.prev_btn.clicked.connect(self.previous_step)
        self.prev_btn.setEnabled(False)
        button_layout.addWidget(self.prev_btn)
        
        button_layout.addStretch()
        
        self.next_btn = QPushButton("Next →")
        self.next_btn.clicked.connect(self.next_step)
        button_layout.addWidget(self.next_btn)
        
        self.complete_btn = QPushButton("Complete")
        self.complete_btn.clicked.connect(self.accept)
        self.complete_btn.setVisible(False)
        button_layout.addWidget(self.complete_btn)
        
        layout.addLayout(button_layout)
        
        self.show_step(0)
    
    def _create_separator(self):
        """Create a horizontal separator."""
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        return sep
    
    def show_step(self, step_num):
        """Show the specified step."""
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        
        if step_num == 0:
            self._show_step_1_usdc()
        elif step_num == 1:
            self._show_step_2_arweave()
        elif step_num == 2:
            self._show_step_3_nano()
        
        self.current_step = step_num
        self.step_indicator.setText(f"Step {step_num + 1} of 3")
        
        self.prev_btn.setEnabled(step_num > 0)
        self.next_btn.setVisible(step_num < 2)
        self.complete_btn.setVisible(step_num == 2)
    
    def _show_step_1_usdc(self):
        """Step 1: Fund wallet with USDC."""
        title = QLabel("Step 1: Fund Your Solana Wallet with USDC")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        self.content_layout.addWidget(title)
        
        info_text = QLabel(
            "To use Arweave purchasing, you need USDC (stablecoin) in your Solana wallet.\n\n"
            "USDC is a widely accepted stablecoin on the Solana blockchain.\n\n"
            "Choose one of the following methods to fund your wallet:"
        )
        info_text.setWordWrap(True)
        self.content_layout.addWidget(info_text)
        
        methods_group = QGroupBox("Funding Methods")
        methods_layout = QVBoxLayout(methods_group)
        
        methods = [
            {
                "title": "1. Centralized Exchange (Recommended)",
                "description": "Transfer USDC from Coinbase, Kraken, FTX, or other exchanges",
                "steps": [
                    "Create account on supported exchange",
                    "Complete KYC verification",
                    "Purchase or deposit USDC",
                    "Withdraw USDC to your Solana wallet address",
                    "Usually arrives within 5-30 minutes"
                ]
            },
            {
                "title": "2. On-Ramp Services",
                "description": "Direct bank transfer to USDC",
                "steps": [
                    "Use services like Moonpay, Ramp, or Wyre",
                    "Connect your bank account",
                    "Deposit funds directly to USDC",
                    "Funds appear instantly in wallet"
                ]
            },
            {
                "title": "3. Swap from Existing Crypto",
                "description": "If you already have SOL or other tokens",
                "steps": [
                    "Visit Jupiter or Raydium DEX",
                    "Swap your tokens for USDC",
                    "Received USDC instantly"
                ]
            }
        ]
        
        for method in methods:
            method_label = QLabel(f"<b>{method['title']}</b>")
            method_label.setWordWrap(True)
            methods_layout.addWidget(method_label)
            
            desc_label = QLabel(f"<i>{method['description']}</i>")
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("color: #666;")
            methods_layout.addWidget(desc_label)
            
            steps_text = "\n".join(f"  • {step}" for step in method['steps'])
            steps_label = QLabel(steps_text)
            steps_label.setWordWrap(True)
            steps_label.setStyleSheet("margin-left: 20px; margin-bottom: 15px; font-size: 10px;")
            methods_layout.addWidget(steps_label)
        
        self.content_layout.addWidget(methods_group)
        
        your_address_group = QGroupBox("Your Solana Address")
        address_layout = QVBoxLayout(your_address_group)
        
        user = app_service.get_current_user()
        
        # Get Solana address from various possible attributes
        solana_address = None
        if user:
            # Try different attribute names (usdc_address is the Solana wallet address for USDC)
            for attr in ['usdc_address', 'solana_pubkey', 'solana_address', 'solana_wallet']:
                if hasattr(user, attr):
                    addr = getattr(user, attr, None)
                    if addr:
                        solana_address = addr
                        break
        
        if solana_address:
            # QR Code section
            qr_layout = QHBoxLayout()
            
            # QR Code
            qr_label = QLabel()
            qr_label.setAlignment(Qt.AlignCenter)
            qr_label.setMinimumSize(220, 220)
            qr_label.setMaximumSize(220, 220)
            
            qr_generated = False
            try:
                qr = qrcode.QRCode(version=1, box_size=10, border=2)
                qr.add_data(solana_address)
                qr.make(fit=True)
                
                qr_img = qr.make_image(fill_color="black", back_color="white")
                
                # Convert to QPixmap
                buffer = io.BytesIO()
                qr_img.save(buffer, format='PNG')
                buffer.seek(0)
                
                pixmap = QPixmap()
                success = pixmap.loadFromData(buffer.getvalue(), 'PNG')
                
                if success and not pixmap.isNull():
                    scaled_pixmap = pixmap.scaledToWidth(200, Qt.SmoothTransformation)
                    qr_label.setPixmap(scaled_pixmap)
                    qr_label.setStyleSheet("""
                        QLabel {
                            padding: 10px;
                            background: white;
                            border: 1px solid #ddd;
                            border-radius: 4px;
                        }
                    """)
                    qr_generated = True
                else:
                    raise Exception("Failed to load pixmap from PNG data")
            except Exception as e:
                print(f"QR Code generation error: {e}")
                qr_label.setText(f"QR Code Error:\n{str(e)[:50]}")
                qr_label.setStyleSheet("""
                    QLabel {
                        color: red;
                        padding: 10px;
                        border: 1px solid #ffcccc;
                        border-radius: 4px;
                        background: #ffeeee;
                    }
                """)
            
            qr_layout.addWidget(qr_label)
            
            # Address text and copy button
            address_text_layout = QVBoxLayout()
            
            address_title = QLabel("Scan or Copy:")
            address_title.setFont(QFont("Arial", 10, QFont.Bold))
            address_text_layout.addWidget(address_title)
            
            address_label = QLabel("Solana Address:")
            address_label.setStyleSheet("font-size: 10px; color: #666;")
            address_text_layout.addWidget(address_label)
            
            address_edit = QLineEdit()
            address_edit.setText(solana_address)
            address_edit.setReadOnly(True)
            address_edit.setFont(QFont("Courier", 8))
            address_text_layout.addWidget(address_edit)
            
            copy_btn = QPushButton("📋 Copy Address")
            copy_btn.clicked.connect(lambda: self._copy_to_clipboard(solana_address))
            copy_btn.setStyleSheet("""
                QPushButton {
                    background-color: #10b981;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #059669;
                }
            """)
            address_text_layout.addWidget(copy_btn)
            
            status_label = QLabel()
            if qr_generated:
                status_label.setText("✓ QR code generated successfully")
                status_label.setStyleSheet("color: #10b981; font-size: 10px;")
            else:
                status_label.setText("⚠ QR code display failed (use copy button)")
                status_label.setStyleSheet("color: #ff9800; font-size: 10px;")
            address_text_layout.addWidget(status_label)
            
            address_text_layout.addStretch()
            
            qr_layout.addLayout(address_text_layout, 1)
            
            address_layout.addLayout(qr_layout)
        else:
            no_addr = QLabel(
                "⚠️ Solana wallet not configured.\n\n"
                "Please complete account setup first.\n\n"
                "Your wallet address will appear here once configured."
            )
            no_addr.setWordWrap(True)
            no_addr.setStyleSheet("""
                QLabel {
                    color: #ff6b6b;
                    padding: 15px;
                    border: 1px solid #ffcccc;
                    border-radius: 4px;
                    background: #ffeeee;
                }
            """)
            address_layout.addWidget(no_addr)
        
        self.content_layout.addWidget(your_address_group)
        
        # Add pending USDC transactions
        self._add_pending_transactions_display("USDC")
        
        self.content_layout.addStretch()
    
    def _show_step_2_arweave(self):
        """Step 2: Purchase Arweave."""
        title = QLabel("Step 2: Purchase Arweave Coins")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        self.content_layout.addWidget(title)
        
        info_text = QLabel(
            "Once you have USDC in your Solana wallet, you can purchase Arweave (AR) tokens.\n\n"
            "This widget provides an easy way to swap USDC to AR using Jupiter DEX."
        )
        info_text.setWordWrap(True)
        self.content_layout.addWidget(info_text)
        
        purchase_group = QGroupBox("Purchase Details")
        purchase_layout = QVBoxLayout(purchase_group)
        
        details = [
            ("What is Arweave (AR)?", 
             "AR is the native token of Arweave, a decentralized storage network."),
            ("Why Arweave?",
             "Arweave enables permanent data storage. Perfect for auction records and item storage."),
            ("How much do I need?",
             "Start with 10-50 USDC. The swap will show you exact AR amounts."),
            ("Are there fees?",
             "Yes, Jupiter charges ~0.35% fee. Gas fees are minimal (~0.001 SOL)."),
        ]
        
        for q, a in details:
            q_label = QLabel(f"<b>{q}</b>")
            q_label.setWordWrap(True)
            purchase_layout.addWidget(q_label)
            
            a_label = QLabel(a)
            a_label.setWordWrap(True)
            a_label.setStyleSheet("margin-left: 20px; margin-bottom: 10px; color: #666;")
            purchase_layout.addWidget(a_label)
        
        self.content_layout.addWidget(purchase_group)
        
        purchase_info = QGroupBox("Ready to Purchase?")
        purchase_info_layout = QVBoxLayout(purchase_info)
        
        ready_text = QLabel(
            "In the next step, you can:\n"
            "  1. Select amount of USDC to spend\n"
            "  2. See live AR price estimate\n"
            "  3. Review swap details\n"
            "  4. Confirm and execute swap"
        )
        ready_text.setWordWrap(True)
        purchase_info_layout.addWidget(ready_text)
        
        launch_purchase_btn = QPushButton("Launch Purchase Dialog")
        launch_purchase_btn.clicked.connect(self.launch_arweave_purchase)
        purchase_info_layout.addWidget(launch_purchase_btn)
        
        self.content_layout.addWidget(purchase_info)
        
        # Add pending Arweave transactions
        self._add_pending_transactions_display("ARWEAVE")
        
        self.content_layout.addStretch()
    
    def _show_step_3_nano(self):
        """Step 3: Access Cloudflare for Nano funds."""
        title = QLabel("Step 3: Acquire Nano via Cloudflare Worker")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        self.content_layout.addWidget(title)
        
        info_text = QLabel(
            "Nano is a feeless, high-speed cryptocurrency.\n\n"
            "You can request Nano directly via our Cloudflare Worker, or access faucets manually."
        )
        info_text.setWordWrap(True)
        self.content_layout.addWidget(info_text)
        
        nano_group = QGroupBox("About Nano")
        nano_layout = QVBoxLayout(nano_group)
        
        nano_info = [
            ("What is Nano?",
             "Nano is a cryptocurrency with zero fees and instant confirmation. Perfect for fast transactions."),
            ("Why Nano?",
             "Nano offers instant, feeless transactions - ideal for p2p payments and trading."),
            ("How do I get it?",
             "Request via our Cloudflare Worker (instant, if configured) or use faucets below."),
        ]
        
        for q, a in nano_info:
            q_label = QLabel(f"<b>{q}</b>")
            q_label.setWordWrap(True)
            nano_layout.addWidget(q_label)
            
            a_label = QLabel(a)
            a_label.setWordWrap(True)
            a_label.setStyleSheet("margin-left: 20px; margin-bottom: 10px; color: #666;")
            nano_layout.addWidget(a_label)
        
        self.content_layout.addWidget(nano_group)
        
        user = app_service.get_current_user()
        
        nano_address_group = QGroupBox("Your Nano Address")
        nano_addr_layout = QVBoxLayout(nano_address_group)
        
        if user and hasattr(user, 'nano_address') and user.nano_address:
            qr_layout = QHBoxLayout()
            
            qr_label = QLabel()
            qr_label.setAlignment(Qt.AlignCenter)
            
            try:
                qr = qrcode.QRCode(version=1, box_size=8, border=2)
                qr.add_data(user.nano_address)
                qr.make(fit=True)
                
                qr_img = qr.make_image(fill_color="black", back_color="white")
                
                buffer = io.BytesIO()
                qr_img.save(buffer, format='PNG')
                buffer.seek(0)
                
                pixmap = QPixmap()
                pixmap.loadFromData(buffer.getvalue())
                qr_label.setPixmap(pixmap.scaled(180, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                qr_label.setStyleSheet("padding: 10px; background: white; border: 1px solid #ddd; border-radius: 4px;")
            except Exception as e:
                qr_label.setText(f"QR Error: {str(e)}")
                qr_label.setStyleSheet("color: red;")
            
            qr_layout.addWidget(qr_label)
            
            nano_text_layout = QVBoxLayout()
            
            nano_title = QLabel("Scan or Copy:")
            nano_title.setFont(QFont("Arial", 10, QFont.Bold))
            nano_text_layout.addWidget(nano_title)
            
            nano_label = QLabel("Nano Address:")
            nano_label.setStyleSheet("font-size: 10px; color: #666;")
            nano_text_layout.addWidget(nano_label)
            
            nano_addr_edit = QLineEdit()
            nano_addr_edit.setText(user.nano_address)
            nano_addr_edit.setReadOnly(True)
            nano_addr_edit.setFont(QFont("Courier", 8))
            nano_text_layout.addWidget(nano_addr_edit)
            
            copy_nano_btn = QPushButton("📋 Copy Address")
            copy_nano_btn.clicked.connect(lambda: self._copy_to_clipboard(user.nano_address))
            copy_nano_btn.setStyleSheet("""
                QPushButton {
                    background-color: #10b981;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #059669;
                }
            """)
            nano_text_layout.addWidget(copy_nano_btn)
            
            request_nano_btn = QPushButton("🔗 Request Nano")
            request_nano_btn.clicked.connect(self.request_nano_via_cloudflare)
            request_nano_btn.setStyleSheet("""
                QPushButton {
                    background-color: #8b5cf6;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #7c3aed;
                }
            """)
            nano_text_layout.addWidget(request_nano_btn)
            
            nano_text_layout.addStretch()
            
            qr_layout.addLayout(nano_text_layout, 1)
            
            nano_addr_layout.addLayout(qr_layout)
        else:
            no_nano = QLabel("⚠️ Nano address not configured.")
            no_nano.setStyleSheet("color: #ff6b6b;")
            nano_addr_layout.addWidget(no_nano)
        
        self.content_layout.addWidget(nano_address_group)
        
        faucet_group = QGroupBox("Alternative: Use Faucets")
        faucet_layout = QVBoxLayout(faucet_group)
        
        faucet_label = QLabel("If Cloudflare Worker is unavailable, use these faucets:")
        faucet_label.setStyleSheet("color: #666; font-size: 10px; margin-bottom: 10px;")
        faucet_layout.addWidget(faucet_label)
        
        faucet_links = [
            ("Nano Official Faucet", "https://faucet.nano.org/"),
            ("Nano Node - mynano.ninja", "https://mynano.ninja/"),
            ("NanoQuakz Faucet", "https://nanoquakz.com/"),
            ("Nano Community", "https://nano.org/"),
        ]
        
        for link_name, url in faucet_links:
            link_btn = QPushButton(f"🔗 {link_name}")
            link_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3b82f6;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 6px;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: #2563eb;
                }
            """)
            link_btn.clicked.connect(lambda checked, u=url: self._open_url(u))
            faucet_layout.addWidget(link_btn)
        
        self.content_layout.addWidget(faucet_group)
        
        self.content_layout.addSpacing(20)
        
        complete_info = QLabel(
            "<b>✓ Complete Wallet Setup!</b>\n\n"
            "You now have:\n"
            "  • USDC funded in Solana wallet\n"
            "  • Arweave tokens purchased\n"
            "  • Nano acquired and ready\n\n"
            "Your wallet is fully configured for trading and transactions!"
        )
        complete_info.setWordWrap(True)
        complete_info.setStyleSheet("background-color: #f0f9ff; padding: 15px; border-radius: 6px; border-left: 4px solid #3b82f6;")
        self.content_layout.addWidget(complete_info)
        
        # Add pending Nano transactions
        self._add_pending_transactions_display("NANO")
        
        self.content_layout.addStretch()
    
    def _add_pending_transactions_display(self, currency: str):
        """Add a compact pending transactions display for a specific currency."""
        try:
            user = app_service.get_current_user()
            if not user:
                return
            
            # Get pending transactions for this currency (may be empty)
            pending = []
            if self.tracker:
                pending = self.tracker.get_pending_transactions(
                    user_id=user.id,
                    currency=currency
                )
            
            # Always create group box, even if no transactions
            if pending:
                pending_group = QGroupBox(f"📊 Pending {currency} Transactions ({len(pending)})")
            else:
                pending_group = QGroupBox(f"📊 {currency} Transaction Status")
            
            pending_layout = QVBoxLayout(pending_group)
            pending_layout.setContentsMargins(10, 10, 10, 10)
            pending_layout.setSpacing(6)
            
            if pending:
                # Create compact list of transactions
                for tx in pending[:3]:  # Show max 3 transactions
                    target = self.tracker.confirmation_targets.get(currency, 6)
                    
                    # Format transaction item
                    tx_type = "Send" if tx.type == "send" else "Receive"
                    status_icon = "⏳" if tx.status == "pending" else "✓" if tx.status == "confirmed" else "✗"
                    
                    tx_label = QLabel(
                        f"{status_icon} {tx_type}: {tx.amount} {currency} "
                        f"({tx.confirmations}/{target} confirms)"
                    )
                    tx_label.setFont(QFont("Arial", 9))
                    
                    # Color based on status
                    if tx.status == "pending":
                        tx_label.setStyleSheet("color: #ff9800;")
                    elif tx.status == "confirmed":
                        tx_label.setStyleSheet("color: #4caf50;")
                    elif tx.status == "failed":
                        tx_label.setStyleSheet("color: #f44336;")
                    
                    pending_layout.addWidget(tx_label)
                
                # Show "more" if exceeded
                if len(pending) > 3:
                    more_label = QLabel(f"... and {len(pending) - 3} more pending transaction(s)")
                    more_label.setFont(QFont("Arial", 8))
                    more_label.setStyleSheet("color: #999; font-style: italic;")
                    pending_layout.addWidget(more_label)
            else:
                # No pending transactions
                no_pending_label = QLabel("✓ No pending transactions")
                no_pending_label.setFont(QFont("Arial", 9))
                no_pending_label.setStyleSheet("color: #4caf50; font-weight: bold;")
                pending_layout.addWidget(no_pending_label)
                
                status_label = QLabel("Ready to proceed with next step")
                status_label.setFont(QFont("Arial", 8))
                status_label.setStyleSheet("color: #999; font-style: italic; margin-top: 4px;")
                pending_layout.addWidget(status_label)
            
            pending_group.setStyleSheet("""
                QGroupBox {
                    border: 1px solid #e2e8f0;
                    border-radius: 4px;
                    margin-top: 8px;
                    padding-top: 10px;
                    font-weight: bold;
                    font-size: 10px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 3px 0 3px;
                }
            """)
            
            self.content_layout.addWidget(pending_group)
        
        except Exception as e:
            print(f"Error displaying pending transactions: {e}")
    
    def init_tracker(self):
        """Initialize transaction tracker."""
        worker = AsyncWorker(self._init_tracker_async())
        worker.start()
        self._tracker_worker = worker
    
    async def _init_tracker_async(self):
        """Initialize tracker asynchronously."""
        try:
            self.tracker = await get_transaction_tracker()
        except Exception as e:
            print(f"Error initializing tracker: {e}")
    
    def request_nano_via_cloudflare(self):
        """Show dialog to request Nano via Cloudflare Worker."""
        user = app_service.get_current_user()
        if not user or not hasattr(user, 'nano_address') or not user.nano_address:
            QMessageBox.warning(self, "Error", "Nano address not configured.")
            return
        
        dialog = RequestNanoDialog(user.nano_address, self)
        dialog.exec_()
    
    def next_step(self):
        """Go to next step."""
        if self.current_step < 2:
            self.show_step(self.current_step + 1)
    
    def previous_step(self):
        """Go to previous step."""
        if self.current_step > 0:
            self.show_step(self.current_step - 1)
    
    def launch_arweave_purchase(self):
        """Launch the Arweave purchase dialog."""
        from ui.wallet_widget import ArweavePurchaseDialog
        
        dialog = ArweavePurchaseDialog(self)
        dialog.exec_()
    
    def _copy_to_clipboard(self, text):
        """Copy text to clipboard."""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        QMessageBox.information(self, "Copied", "Address copied to clipboard!")
    
    def _open_url(self, url):
        """Open URL in default browser."""
        QDesktopServices.openUrl(QUrl(url))


class FundingManagerWidget(QWidget):
    """Widget managing wallet funding process."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tracker = None
        self.setup_ui()
        self.setup_auto_refresh()
        # Initialize tracker immediately (non-blocking)
        self._init_tracker_immediate()
    
    def setup_auto_refresh(self):
        """Setup auto-refresh of pending transactions."""
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_pending_transactions)
        self.refresh_timer.start(3000)
    
    def _init_tracker_immediate(self):
        """Initialize tracker asynchronously without blocking UI."""
        worker = AsyncWorker(self._init_tracker())
        worker.finished.connect(self.refresh_pending_transactions)
        worker.error.connect(lambda e: print(f"Error initializing tracker: {e}"))
        worker.start()
        self._init_worker = worker
    
    def setup_ui(self):
        """Setup the widget UI."""
        layout = QVBoxLayout(self)
        
        container = QGroupBox("Wallet Funding Manager")
        container.setStyleSheet("""
            QGroupBox {
                border: 2px solid #3b82f6;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
            }
        """)
        
        container_layout = QVBoxLayout(container)
        
        header = QLabel("Quick Funding Setup")
        header.setFont(QFont("Arial", 12, QFont.Bold))
        container_layout.addWidget(header)
        
        desc = QLabel(
            "Get your wallet ready for trading in 3 simple steps:\n"
            "1️⃣  Fund your Solana wallet with USDC\n"
            "2️⃣  Purchase Arweave (AR) tokens\n"
            "3️⃣  Access Nano funds via Cloudflare"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666; margin-bottom: 15px;")
        container_layout.addWidget(desc)
        
        self.progress_label = QLabel("Not started")
        self.progress_label.setStyleSheet("color: #666; font-size: 11px;")
        container_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(3)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #e2e8f0;
                border-radius: 4px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #3b82f6;
                border-radius: 3px;
            }
        """)
        container_layout.addWidget(self.progress_bar)
        
        # Pending Transactions Section
        pending_group = QGroupBox("📊 Pending Transactions")
        pending_layout = QVBoxLayout(pending_group)
        
        self.pending_table = QTableWidget()
        self.pending_table.setColumnCount(7)
        self.pending_table.setHorizontalHeaderLabels([
            "Coin", "Type", "Amount", "Status", "Confirmations", "Time", "Action"
        ])
        
        header = self.pending_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        
        self.pending_table.setMaximumHeight(150)
        self.pending_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.pending_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #e2e8f0;
                border-radius: 4px;
                gridline-color: #f0f0f0;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QHeaderView::section {
                background-color: #f8fafc;
                padding: 5px;
                border: none;
                border-right: 1px solid #e2e8f0;
                font-weight: bold;
            }
        """)
        pending_layout.addWidget(self.pending_table)
        
        self.pending_info_label = QLabel("Loading transaction status...")
        self.pending_info_label.setStyleSheet("color: #1976d2; font-size: 10px; font-weight: bold;")
        pending_layout.addWidget(self.pending_info_label)
        
        container_layout.addWidget(pending_group)
        
        button_layout = QHBoxLayout()
        
        self.launch_btn = QPushButton("🚀 Launch Funding Wizard")
        self.launch_btn.setFont(QFont("Arial", 11, QFont.Bold))
        self.launch_btn.setMinimumHeight(40)
        self.launch_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
            }
        """)
        self.launch_btn.clicked.connect(self.show_wizard)
        button_layout.addWidget(self.launch_btn)
        
        button_layout.addStretch()
        
        container_layout.addLayout(button_layout)
        
        layout.addWidget(container)
        layout.addStretch()
    
    def show_wizard(self):
        """Show the funding wizard dialog."""
        wizard = FundingWizardDialog(self)
        wizard.exec_()
        self.update_progress()
        self.refresh_pending_transactions()
    
    def refresh_pending_transactions(self):
        """Refresh pending transactions display."""
        try:
            user = app_service.get_current_user()
            if not user:
                self.pending_info_label.setText("No user logged in")
                return
                
            if not self.tracker:
                # Initialize tracker asynchronously
                worker = AsyncWorker(self._init_tracker())
                worker.finished.connect(lambda _: self._display_pending_transactions())
                worker.error.connect(lambda e: self.pending_info_label.setText(f"Error: {str(e)[:50]}"))
                worker.start()
                self._init_worker = worker
                return
            
            self._display_pending_transactions()
        except Exception as e:
            print(f"Error refreshing pending transactions: {e}")
            self.pending_info_label.setText(f"Error: {str(e)[:50]}")
    
    async def _init_tracker(self):
        """Initialize tracker asynchronously."""
        try:
            self.tracker = await get_transaction_tracker()
            return True
        except Exception as e:
            print(f"Error initializing tracker: {e}")
            return False
    
    def _display_pending_transactions(self):
        """Display pending transactions in table."""
        try:
            if not self.tracker:
                return
            
            user = app_service.get_current_user()
            if not user:
                return
            
            # Get pending and failed transactions
            pending = self.tracker.get_pending_transactions(user_id=user.id)
            history = self.tracker.get_transaction_history(user_id=user.id, limit=20, days=30)
            failed = [tx for tx in history if tx.status == "failed"]
            
            tx_lookup = {}
            for tx in pending + failed:
                tx_lookup[tx.id] = tx
            
            display_txs = list(tx_lookup.values())
            
            # Clear table
            self.pending_table.setRowCount(0)
            
            if not display_txs:
                self.pending_info_label.setText("✓ No pending transactions - wallet ready for transactions")
                self.pending_info_label.setStyleSheet("color: #1976d2; font-size: 10px; font-weight: bold;")
                return
            
            # Add rows for each transaction
            for tx in display_txs:
                row = self.pending_table.rowCount()
                self.pending_table.insertRow(row)
                
                # Coin
                coin_item = QTableWidgetItem(tx.currency)
                coin_item.setFont(QFont("Arial", 9, QFont.Bold))
                self.pending_table.setItem(row, 0, coin_item)
                
                # Type
                tx_type = "Send" if tx.type == "send" else "Receive"
                type_item = QTableWidgetItem(tx_type)
                self.pending_table.setItem(row, 1, type_item)
                
                # Amount
                amount_item = QTableWidgetItem(f"{tx.amount} {tx.currency}")
                self.pending_table.setItem(row, 2, amount_item)
                
                # Status
                status_item = QTableWidgetItem(tx.status.upper())
                if tx.status == "pending":
                    status_item.setForeground(QColor("#ff9800"))
                elif tx.status == "confirmed":
                    status_item.setForeground(QColor("#4caf50"))
                    status_item.setText("✓ CONFIRMED")
                elif tx.status == "failed":
                    status_item.setForeground(QColor("#f44336"))
                    if tx.error_message:
                        status_item.setToolTip(tx.error_message)
                self.pending_table.setItem(row, 3, status_item)
                
                # Confirmations
                target = self.tracker.confirmation_targets.get(tx.currency, 6)
                conf_item = QTableWidgetItem(f"{tx.confirmations}/{target}")
                self.pending_table.setItem(row, 4, conf_item)
                
                # Time (created_at)
                try:
                    dt = datetime.fromisoformat(tx.created_at)
                    time_str = dt.strftime("%H:%M:%S")
                except:
                    time_str = "N/A"
                
                time_item = QTableWidgetItem(time_str)
                time_item.setStyleSheet("color: #999; font-size: 9px;")
                self.pending_table.setItem(row, 5, time_item)
                
                # Action
                action_item = QTableWidgetItem("-")
                self.pending_table.setItem(row, 6, action_item)
                if tx.status == "failed":
                    max_retries = self.tracker.max_retries.get(tx.currency, 3)
                    retry_btn = QPushButton("Retry")
                    retry_btn.setEnabled(tx.retry_count < max_retries)
                    retry_btn.clicked.connect(lambda checked, tx_id=tx.id: self._retry_failed_transaction(tx_id))
                    self.pending_table.setCellWidget(row, 6, retry_btn)
            
            failed_count = len([tx for tx in display_txs if tx.status == "failed"])
            if failed_count:
                self.pending_info_label.setText(f"{failed_count} failed transaction(s) detected. Retry available.")
                self.pending_info_label.setStyleSheet("color: #d32f2f; font-size: 10px; font-weight: bold;")
            else:
                self.pending_info_label.setText(f"Monitoring {len(display_txs)} pending transaction(s)...")
                self.pending_info_label.setStyleSheet("color: #1976d2; font-size: 10px; font-weight: bold;")
        
        except Exception as e:
            self.pending_info_label.setText(f"Error: {str(e)[:50]}")
    
    def _retry_failed_transaction(self, tx_id: str):
        try:
            worker = AsyncWorker(self._retry_failed_transaction_async(tx_id))
            worker.finished.connect(lambda success: self._handle_retry_result(success))
            worker.error.connect(lambda e: QMessageBox.warning(self, "Retry Failed", str(e)))
            worker.start()
            self._retry_worker = worker
        except Exception as e:
            QMessageBox.warning(self, "Retry Failed", str(e))
    
    async def _retry_failed_transaction_async(self, tx_id: str):
        if not self.tracker:
            self.tracker = await get_transaction_tracker()
        return await self.tracker.retry_transaction(tx_id)
    
    def _handle_retry_result(self, success: bool):
        if success:
            QMessageBox.information(self, "Retry Started", "Transaction retry started and will be monitored.")
        else:
            QMessageBox.warning(self, "Retry Unavailable", "Transaction could not be retried.")
        self.refresh_pending_transactions()
    
    def update_progress(self):
        """Update progress display."""
        user = app_service.get_current_user()
        if not user:
            self.progress_label.setText("Not started")
            self.progress_bar.setValue(0)
            return
        
        steps_completed = 0
        status_text = ""
        
        if hasattr(user, 'usdc_address') and user.usdc_address:
            steps_completed += 1
            status_text += "✓ Solana wallet configured"
        else:
            status_text += "○ Solana wallet not configured"
        
        status_text += " | "
        
        if hasattr(user, 'arweave_address') and user.arweave_address:
            steps_completed += 1
            status_text += "✓ Arweave wallet configured"
        else:
            status_text += "○ Arweave wallet not configured"
        
        status_text += " | "
        
        if hasattr(user, 'nano_address') and user.nano_address:
            steps_completed += 1
            status_text += "✓ Nano wallet configured"
        else:
            status_text += "○ Nano wallet not configured"
        
        self.progress_label.setText(status_text)
        self.progress_bar.setValue(steps_completed)
    
    def showEvent(self, event):
        """Initialize when widget is shown."""
        super().showEvent(event)
        # Initialize tracker if not already done
        if not self.tracker:
            worker = AsyncWorker(self._init_tracker())
            worker.finished.connect(self.refresh_pending_transactions)
            worker.start()
            self._init_worker = worker
    
    def hideEvent(self, event):
        """Cleanup when widget is hidden."""
        super().hideEvent(event)
        if hasattr(self, 'refresh_timer'):
            self.refresh_timer.stop()
    
    def closeEvent(self, event):
        """Cleanup on close."""
        if hasattr(self, 'refresh_timer'):
            self.refresh_timer.stop()
        super().closeEvent(event)
