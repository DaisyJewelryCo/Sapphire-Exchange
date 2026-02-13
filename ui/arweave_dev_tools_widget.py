"""
Arweave Development Tools Widget for previewing Arweave posts before posting.
Provides a dev tools sidebar for inspecting and testing Arweave post generation.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextBrowser, QTabWidget, QListWidget, QListWidgetItem, 
    QScrollArea, QFrame, QComboBox, QSplitter, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor

from utils.arweave_auction_viewer import ArweaveAuctionViewer


class ArweaveDevToolsWidget(QWidget):
    """Widget for viewing and managing Arweave post previews in dev tools."""
    
    post_ready_to_send = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.posts = []
        self.current_post_index = -1
        self.arweave_post_service = None
        self.viewer = None
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the dev tools UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        header = QLabel("Arweave Post Preview (Dev Tools)")
        header.setFont(QFont("Arial", 12, QFont.Bold))
        header.setStyleSheet("color: #1e293b;")
        layout.addWidget(header)
        
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("border: 1px solid #e2e8f0;")
        layout.addWidget(separator)
        
        main_splitter = QSplitter(Qt.Horizontal)
        
        left_panel = self._create_left_panel()
        right_panel = self._create_right_panel()
        
        main_splitter.addWidget(left_panel)
        main_splitter.addWidget(right_panel)
        main_splitter.setSizes([200, 400])
        
        layout.addWidget(main_splitter)
        
        self.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
            }
            QTextBrowser {
                background-color: #f8f9fa;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                font-family: monospace;
                font-size: 10px;
            }
            QListWidget {
                background-color: #f8f9fa;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
            }
            QListWidget::item:selected {
                background-color: #3b82f6;
                color: white;
            }
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 500;
                font-size: 11px;
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
    
    def _create_left_panel(self):
        """Create the left panel with post list."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(6)
        
        label = QLabel("Generated Posts")
        label.setFont(QFont("Arial", 10, QFont.Bold))
        label.setStyleSheet("color: #1e293b;")
        layout.addWidget(label)
        
        self.posts_list = QListWidget()
        self.posts_list.itemSelectionChanged.connect(self.on_post_selected)
        layout.addWidget(self.posts_list)
        
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        
        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.clicked.connect(self.clear_posts)
        self.clear_btn.setEnabled(False)
        button_layout.addWidget(self.clear_btn)
        
        layout.addLayout(button_layout)
        
        return panel
    
    def _create_right_panel(self):
        """Create the right panel with post details."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(6)
        
        view_label = QLabel("View:")
        view_label.setFont(QFont("Arial", 9))
        controls_layout.addWidget(view_label)
        
        self.view_combo = QComboBox()
        self.view_combo.addItems([
            "Preview",
            "Structure",
            "JSON",
            "Metadata Only"
        ])
        self.view_combo.currentIndexChanged.connect(self.update_display)
        controls_layout.addWidget(self.view_combo)
        
        controls_layout.addStretch()
        
        self.export_btn = QPushButton("Save to File")
        self.export_btn.clicked.connect(self.save_post_to_file)
        self.export_btn.setEnabled(False)
        controls_layout.addWidget(self.export_btn)
        
        self.post_btn = QPushButton("Post to Arweave")
        self.post_btn.clicked.connect(self.on_post_to_arweave)
        self.post_btn.setEnabled(False)
        self.post_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
            }
            QPushButton:hover {
                background-color: #059669;
            }
            QPushButton:pressed {
                background-color: #047857;
            }
            QPushButton:disabled {
                background-color: #9ca3af;
            }
        """)
        controls_layout.addWidget(self.post_btn)
        
        layout.addLayout(controls_layout)
        
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("border: 1px solid #e2e8f0;")
        layout.addWidget(separator)
        
        self.content_browser = QTextBrowser()
        self.content_browser.setMinimumHeight(300)
        layout.addWidget(self.content_browser)
        
        info_label = QLabel("")
        info_label.setFont(QFont("Arial", 9))
        info_label.setStyleSheet("color: #64748b;")
        info_label.setWordWrap(True)
        self.info_label = info_label
        layout.addWidget(info_label)
        
        return panel
    
    def set_arweave_service(self, service):
        """Set the Arweave post service reference."""
        self.arweave_post_service = service
        if service:
            self.viewer = ArweaveAuctionViewer(service)
    
    def load_pending_inventory_posts(self, user_id: str):
        """Load pending inventory posts from the Arweave service."""
        if not self.arweave_post_service:
            return
        
        pending = self.arweave_post_service.get_pending_inventory(user_id)
        if pending:
            self.update_or_add_pending_post(pending)
    
    def update_or_add_pending_post(self, post_data: dict):
        """Update existing pending inventory post or add if new."""
        title = f"[PENDING] Inventory - {post_data.get('item_count', 0)} items"
        
        if post_data.get('type') == 'inventory':
            pending_index = None
            for i, p in enumerate(self.posts):
                if p.get('type') == 'inventory' and p.get('posted_by') == post_data.get('posted_by'):
                    pending_index = i
                    break
            
            if pending_index is not None:
                self.posts[pending_index] = post_data
                item = self.posts_list.item(pending_index)
                if item:
                    item.setText(title)
                if self.current_post_index == pending_index:
                    self.update_display()
                return
        
        self.add_post_preview(post_data, title)
    
    def add_post_preview(self, post_data: dict, title: str = None):
        """Add a new post preview to the list."""
        if post_data not in self.posts:
            self.posts.append(post_data)
            
            if title is None:
                auction = post_data.get('auction', {})
                title = auction.get('title', 'Untitled Auction')
            
            item = QListWidgetItem(title)
            item.setData(Qt.UserRole, len(self.posts) - 1)
            self.posts_list.addItem(item)
            
            self.clear_btn.setEnabled(True)
            
            self.posts_list.setCurrentRow(len(self.posts) - 1)
    
    def on_post_selected(self):
        """Handle post selection from list."""
        current_item = self.posts_list.currentItem()
        if current_item:
            index = current_item.data(Qt.UserRole)
            self.current_post_index = index
            self.update_display()
            self.export_btn.setEnabled(True)
            self.post_btn.setEnabled(True)
    
    def update_display(self):
        """Update the display based on selected post and view mode."""
        if self.current_post_index < 0 or self.current_post_index >= len(self.posts):
            self.content_browser.setText("No post selected")
            self.info_label.setText("")
            return
        
        if not self.viewer:
            self.content_browser.setText("Arweave service not initialized")
            return
        
        post_data = self.posts[self.current_post_index]
        view_mode = self.view_combo.currentText()
        
        try:
            if view_mode == "Preview":
                content = self.viewer.preview_auction_post(post_data, verbose=True)
            elif view_mode == "Structure":
                content = self.viewer.preview_post_structure(post_data)
            elif view_mode == "JSON":
                content = self.viewer.preview_auction_post_json(post_data, pretty=True)
            elif view_mode == "Metadata Only":
                content = self._get_metadata_only(post_data)
            else:
                content = self.viewer.preview_auction_post(post_data, verbose=False)
            
            self.content_browser.setText(content)
            
            size_bytes = len(str(post_data).encode('utf-8'))
            estimated_ar = (size_bytes / 1000) * 0.001
            self.info_label.setText(
                f"Post Size: {size_bytes:,} bytes | Estimated AR: ~{estimated_ar:.6f} AR | "
                f"Posts in preview: {len(self.posts)}"
            )
        except Exception as e:
            self.content_browser.setText(f"Error: {str(e)}")
            self.info_label.setText(f"Error rendering preview: {str(e)}")
    
    def _get_metadata_only(self, post_data: dict) -> str:
        """Get metadata-only view of post."""
        lines = [
            "=" * 80,
            "ARWEAVE POST METADATA",
            "=" * 80,
            ""
        ]
        
        lines.append(f"Version: {post_data.get('version', 'N/A')}")
        lines.append(f"Sequence: {post_data.get('sequence', 'N/A')}")
        lines.append(f"Posted By: {post_data.get('posted_by', 'N/A')[:16]}...")
        lines.append(f"Created At: {post_data.get('created_at', 'N/A')}")
        lines.append("")
        
        post_type = post_data.get('type', 'auction')
        if post_type == 'inventory':
            lines.append(f"INVENTORY POST ({post_data.get('item_count', 0)} items)")
        else:
            auction = post_data.get('auction', {})
            lines.append("TOP SECTION AUCTION:")
            lines.append(f"  Item ID: {auction.get('item_id', 'N/A')[:16]}...")
            lines.append(f"  Title: {auction.get('title', 'N/A')}")
            lines.append(f"  Seller: {auction.get('seller_id', 'N/A')[:16]}...")
            lines.append(f"  SHA ID: {auction.get('sha_id', 'N/A')[:16]}...")
            lines.append("")
            
            expiring = post_data.get('expiring_auctions', [])
            lines.append(f"BOTTOM SECTION: {len(expiring)} Expiring Auctions")
        
        lines.append("")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def save_post_to_file(self):
        """Save the current post to a file."""
        if self.current_post_index < 0 or not self.viewer:
            QMessageBox.warning(self, "No Post", "No post selected to save")
            return
        
        post_data = self.posts[self.current_post_index]
        post_type = post_data.get('type', 'auction')
        
        if post_type == 'inventory':
            title = f"inventory_{post_data.get('item_count', 0)}_items"
        else:
            auction = post_data.get('auction', {})
            title = auction.get('title', 'untitled').replace(' ', '_').lower()
        
        filename = f"/tmp/arweave_post_{title}_{self.current_post_index}.txt"
        
        try:
            self.viewer.save_post_to_file(post_data, filename)
            QMessageBox.information(self, "Saved", f"Post saved to:\n{filename}")
        except Exception as e:
            QMessageBox.critical(self, "Save Failed", f"Failed to save post:\n{str(e)}")
    
    def on_post_to_arweave(self):
        """Emit signal to post to Arweave."""
        if self.current_post_index < 0:
            QMessageBox.warning(self, "No Post", "No post selected")
            return
        
        post_data = self.posts[self.current_post_index]
        
        reply = QMessageBox.question(
            self,
            "Post to Arweave",
            f"Post this auction to Arweave?\n\n"
            f"This will incur AR network fees and cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.post_ready_to_send.emit(post_data)
    
    def clear_posts(self):
        """Clear all previewed posts."""
        reply = QMessageBox.question(
            self,
            "Clear Posts",
            "Clear all post previews?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.posts.clear()
            self.posts_list.clear()
            self.current_post_index = -1
            self.content_browser.setText("")
            self.info_label.setText("")
            self.clear_btn.setEnabled(False)
            self.export_btn.setEnabled(False)
            self.post_btn.setEnabled(False)
