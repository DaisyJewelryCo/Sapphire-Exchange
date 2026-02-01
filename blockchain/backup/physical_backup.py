"""
Physical backup generation for offline wallet recovery.
Generates QR codes, paper templates, and instructions for backup storage.
"""
from typing import Optional, Dict, Any, Tuple
from pathlib import Path
from datetime import datetime
import json
import base64

try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False


class PhysicalBackupGenerator:
    """Generate physical backup materials."""
    
    def __init__(self):
        """Initialize physical backup generator."""
        pass
    
    async def generate_qr_code(self, mnemonic: str,
                              output_path: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Generate QR code for mnemonic.
        
        Args:
            mnemonic: BIP39 mnemonic phrase
            output_path: Optional path to save QR code image
        
        Returns:
            Tuple of (success, base64_image_or_path)
        """
        if not HAS_QRCODE:
            return False, "qrcode library not installed"
        
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4,
            )
            
            qr.add_data(mnemonic)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            if output_path:
                img.save(output_path)
                return True, output_path
            else:
                import io
                buffer = io.BytesIO()
                img.save(buffer, format="PNG")
                image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                return True, image_base64
        
        except Exception as e:
            return False, f"QR code generation failed: {str(e)}"
    
    async def generate_paper_template(self, mnemonic: str,
                                     wallet_name: str = "Sapphire Wallet",
                                     output_path: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Generate paper backup template with mnemonic and instructions.
        
        Args:
            mnemonic: BIP39 mnemonic phrase
            wallet_name: Wallet name for template
            output_path: Optional path to save template
        
        Returns:
            Tuple of (success, html_content_or_path)
        """
        try:
            words = mnemonic.split()
            words_html = ""
            
            for i, word in enumerate(words, 1):
                col_class = "col-left" if i % 2 == 1 else "col-right"
                words_html += f'''
                <div class="word-item {col_class}">
                    <span class="word-num">{i}.</span>
                    <span class="word-text">{word}</span>
                </div>
                '''
            
            html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{wallet_name} - Seed Phrase Backup</title>
    <style>
        body {{
            font-family: monospace;
            max-width: 800px;
            margin: 40px auto;
            padding: 20px;
            background: white;
            color: #000;
        }}
        
        .header {{
            text-align: center;
            border-bottom: 3px solid #000;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        
        .header h1 {{
            margin: 0;
            font-size: 24px;
        }}
        
        .header p {{
            margin: 5px 0;
            font-size: 14px;
        }}
        
        .warning {{
            background: #fff3cd;
            border: 2px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
        }}
        
        .warning strong {{
            color: #856404;
        }}
        
        .words-container {{
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            margin: 30px 0;
            page-break-inside: avoid;
        }}
        
        .words-column {{
            flex: 1;
            min-width: 300px;
        }}
        
        .word-item {{
            display: flex;
            margin-bottom: 10px;
            font-size: 14px;
        }}
        
        .word-num {{
            min-width: 30px;
            font-weight: bold;
            margin-right: 10px;
        }}
        
        .word-text {{
            border-bottom: 1px dotted #000;
            flex: 1;
            padding-bottom: 2px;
        }}
        
        .instructions {{
            margin-top: 30px;
            padding: 20px;
            border: 1px solid #ccc;
            background: #f9f9f9;
        }}
        
        .instructions h3 {{
            margin-top: 0;
        }}
        
        .instructions ol {{
            margin: 10px 0;
            padding-left: 20px;
        }}
        
        .instructions li {{
            margin-bottom: 8px;
            font-size: 12px;
        }}
        
        .footer {{
            margin-top: 40px;
            text-align: center;
            font-size: 11px;
            color: #666;
            border-top: 1px solid #ccc;
            padding-top: 20px;
        }}
        
        @media print {{
            body {{
                margin: 0;
                padding: 10px;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{wallet_name}</h1>
        <p>Seed Phrase Backup</p>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="warning">
        <strong>⚠️ SECURITY WARNING:</strong> This document contains your wallet's secret seed phrase. 
        Anyone with access to this phrase can steal your funds. 
        Store this in a safe, dry place. Do not share digitally or take screenshots.
    </div>
    
    <div class="words-container">
        <div class="words-column">
            {words_html[:len(words_html)//2]}
        </div>
        <div class="words-column">
            {words_html[len(words_html)//2:]}
        </div>
    </div>
    
    <div class="instructions">
        <h3>How to Store This Backup</h3>
        <ol>
            <li>Print this document or write down the seed phrase</li>
            <li>Store in a fireproof, waterproof safe or safety deposit box</li>
            <li>Keep in a cool, dry location away from moisture</li>
            <li>Do not store on digital devices or cloud services</li>
            <li>Consider storing in multiple locations for redundancy</li>
            <li>Never share your seed phrase with anyone</li>
            <li>Verify seed phrase integrity regularly</li>
        </ol>
        
        <h3>Recovery Instructions</h3>
        <ol>
            <li>Download Sapphire Exchange or compatible wallet</li>
            <li>Select "Recover Wallet" from the menu</li>
            <li>Enter your seed phrase word by word</li>
            <li>Set a new master password</li>
            <li>Your wallet will be recovered with the same addresses</li>
        </ol>
        
        <h3>Additional Security Tips</h3>
        <ol>
            <li>Consider metal backup for extreme durability</li>
            <li>Use Shamir Secret Sharing for distributed storage</li>
            <li>Store passphrase separately from seed phrase</li>
            <li>Test recovery procedure in non-production environment first</li>
        </ol>
    </div>
    
    <div class="footer">
        <p>Sapphire Exchange - Non-Custodial Wallet</p>
        <p>Keep this document secure. It is the only way to recover your wallet.</p>
    </div>
</body>
</html>
'''
            
            if output_path:
                Path(output_path).write_text(html_content, encoding='utf-8')
                return True, output_path
            else:
                return True, html_content
        
        except Exception as e:
            return False, f"Template generation failed: {str(e)}"
    
    async def generate_backup_instructions(self) -> str:
        """
        Generate comprehensive backup storage instructions.
        
        Returns:
            Instructions text
        """
        instructions = """
SEED PHRASE BACKUP INSTRUCTIONS
================================

WHAT IS A SEED PHRASE?
A seed phrase is a 12 or 24-word recovery code that grants access to all your wallets
and funds. Anyone with this phrase can steal your cryptocurrency.

STORAGE METHODS
===============

1. PAPER WALLET (Recommended for most users)
   - Print the backup template or handwrite the 24 words
   - Store in a safe, dry location
   - Use waterproof, fireproof storage
   - Consider laminating for protection

2. METAL BACKUP (Maximum durability)
   - Engrave seed phrase on stainless steel plate
   - Resistant to fire, water, and corrosion
   - Lasts indefinitely
   - Cannot be digitally hacked

3. DISTRIBUTED STORAGE (Advanced)
   - Use Shamir Secret Sharing (3-of-5 recommended)
   - Split phrase into 5 shares
   - Need 3 shares to recover
   - Store each share in different locations
   - Minimize single point of failure

4. HARDWARE WALLET STORAGE
   - Store recovery phrase with hardware wallet device
   - Never expose to network during storage
   - Keep device in safe location

SECURITY BEST PRACTICES
========================

DO:
✓ Store in fireproof, waterproof safe
✓ Keep in safety deposit box
✓ Use metal backup for durability
✓ Store in multiple secure locations
✓ Keep separate from passphrase
✓ Test recovery in test environment first
✓ Document storage locations

DON'T:
✗ Store on computer or phone
✗ Upload to cloud storage
✗ Share digitally or verbally
✗ Take screenshots or photos
✗ Discuss publicly
✗ Store in unencrypted form
✗ Expose to moisture or heat

RECOVERY PROCESS
=================

1. Download Sapphire Exchange or compatible wallet
2. Select "Recover Wallet" option
3. Choose 12 or 24-word recovery
4. Enter seed phrase word by word
5. Create new master password
6. Verify recovered addresses match original
7. Check balances to confirm successful recovery

VERIFICATION CHECKLIST
======================

□ Seed phrase consists of valid English words
□ Word count is 12 or 24
□ Sequence matches stored backup exactly
□ No words are misspelled
□ Passphrase (if used) is stored separately
□ Backup location is documented
□ Multiple copies stored if needed
□ Recovery tested in test environment
□ Master password is strong and unique

EMERGENCY RECOVERY
===================

If you lose access to your wallet:
1. Retrieve seed phrase from backup
2. Use any compatible wallet software
3. Follow recovery process above
4. Your funds will be restored

Remember: Your seed phrase is the ultimate backup.
Guard it as carefully as you would your actual cash.
"""
        return instructions
    
    async def generate_wallet_metadata(self, wallet_name: str,
                                      mnemonic_word_count: int,
                                      has_passphrase: bool) -> Dict[str, Any]:
        """
        Generate metadata for backup verification.
        
        Args:
            wallet_name: Wallet name
            mnemonic_word_count: Word count (12, 24)
            has_passphrase: Whether passphrase is used
        
        Returns:
            Metadata dictionary
        """
        return {
            "wallet_name": wallet_name,
            "mnemonic_word_count": mnemonic_word_count,
            "has_passphrase": has_passphrase,
            "backup_date": datetime.utcnow().isoformat(),
            "version": "1.0",
            "supported_chains": ["solana", "nano", "arweave"],
        }
    
    @staticmethod
    def get_backup_checklist() -> Dict[str, list]:
        """
        Get comprehensive backup checklist.
        
        Returns:
            Dictionary with backup checklist items
        """
        return {
            "before_backup": [
                "Choose secure storage location",
                "Gather backup materials (paper/metal)",
                "Ensure no one is watching",
                "Disable screen recording",
                "Have backup template or instructions ready",
            ],
            "during_backup": [
                "Record seed phrase carefully",
                "Verify each word spelling",
                "Cross-check word order",
                "Store backup securely",
                "Do NOT take photos or screenshots",
                "Do NOT type into computer",
            ],
            "after_backup": [
                "Test recovery in test environment",
                "Verify recovered addresses match",
                "Document backup location",
                "Inform trusted contact of location",
                "Set reminder to verify backup annually",
                "Update location if moved",
            ],
        }
