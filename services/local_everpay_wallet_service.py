"""
Local everPay wallet management for Sapphire Exchange.

This app never sends private keys off device.
All everPay actions are signed client-side by the user's local wallet.
"""
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from security.key_storage import SecureKeyStorage
from security.password_manager import PasswordManager
from security.vault_encryption import VaultEncryption
from services.everpay_client import EverpayClient

try:
    from eth_account import Account
    from eth_account.messages import encode_defunct
except ImportError:
    Account = None
    encode_defunct = None


@dataclass
class LocalEverpayWallet:
    address: str
    key_id: str
    created_at: str
    storage_dir: str


class LocalEverpayWalletService:
    """Local encrypted wallet service for everPay signing."""

    STORAGE_DIR = Path("~/.sapphire_exchange/everpay_wallet").expanduser()
    STATE_FILE = "wallet_state.json"
    KEY_ID = "everpay-local-wallet"
    PBKDF2_ITERATIONS = 100000
    GCM_IV_SIZE = 12
    SALT_SIZE = 16
    EVERPAY_MESSAGE_FIELDS = (
        "tokenSymbol",
        "action",
        "from",
        "to",
        "amount",
        "fee",
        "feeRecipient",
        "nonce",
        "tokenID",
        "chainType",
        "chainID",
        "data",
        "version",
    )

    def __init__(self, storage_dir: Optional[Path] = None, base_url: str = "https://api.everpay.io"):
        self.storage_dir = Path(storage_dir or self.STORAGE_DIR).expanduser()
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.storage_dir / self.STATE_FILE
        self.password_manager = PasswordManager()
        self.base_url = base_url
        self._wallet: Optional[Any] = None
        self._wallet_state: Optional[Dict[str, Any]] = self._read_state()

    def _read_state(self) -> Optional[Dict[str, Any]]:
        if not self.state_file.exists():
            return None
        try:
            return json.loads(self.state_file.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _write_state(self, state: Dict[str, Any]):
        self.state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
        self._wallet_state = state

    def _build_legacy_storage(self, password: str, salt_hex: str) -> SecureKeyStorage:
        derived = self.password_manager.derive_key(password, salt=bytes.fromhex(salt_hex))
        vault = VaultEncryption(derived.key)
        return SecureKeyStorage(vault, storage_dir=str(self.storage_dir))

    def _normalize_private_key(self, private_key: Any) -> str:
        if isinstance(private_key, bytes):
            value = private_key.hex()
        else:
            value = str(private_key).strip()
        if value.startswith("0x"):
            return value
        return f"0x{value}"

    def _coerce_bytes(self, value: Any) -> bytes:
        if isinstance(value, bytes):
            return value
        if isinstance(value, list):
            return bytes(value)
        if isinstance(value, str):
            normalized = value[2:] if value.startswith("0x") else value
            return bytes.fromhex(normalized)
        raise ValueError("Encrypted wallet payload is invalid")

    def _derive_encryption_key(self, password: str, salt: bytes) -> bytes:
        is_valid, message = self.password_manager.validate_password(password)
        if not is_valid:
            raise ValueError(f"Invalid password: {message}")
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.PBKDF2_ITERATIONS,
        )
        return kdf.derive(password.encode("utf-8"))

    def has_local_wallet(self) -> bool:
        return bool(self._wallet_state and self._wallet_state.get("address"))

    def is_wallet_loaded(self) -> bool:
        return self._wallet is not None

    def get_wallet_address(self) -> Optional[str]:
        if self._wallet is not None:
            return self._wallet.address
        if self._wallet_state:
            return self._wallet_state.get("address")
        return None

    def get_wallet_status(self) -> Dict[str, Any]:
        return {
            "available": self.has_local_wallet(),
            "loaded": self.is_wallet_loaded(),
            "address": self.get_wallet_address(),
            "created_at": self._wallet_state.get("created_at") if self._wallet_state else None,
        }

    def create_local_evm_account(self) -> Dict[str, str]:
        if Account is None:
            raise ValueError("eth-account is required for local everPay wallet support")
        wallet = Account.create()
        private_key = self._normalize_private_key(bytes(wallet.key))
        return {
            "address": wallet.address,
            "private_key": private_key,
        }

    def encrypt_private_key(
        self,
        private_key: str,
        password: str,
        salt: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        normalized_private_key = self._normalize_private_key(private_key)
        salt_bytes = salt or os.urandom(self.SALT_SIZE)
        iv = os.urandom(self.GCM_IV_SIZE)
        key = self._derive_encryption_key(password, salt_bytes)
        ciphertext = AESGCM(key).encrypt(iv, normalized_private_key.encode("utf-8"), None)
        return {
            "salt": list(salt_bytes),
            "iv": list(iv),
            "ciphertext": list(ciphertext),
        }

    def decrypt_private_key(self, encrypted: Dict[str, Any], password: str) -> str:
        if not isinstance(encrypted, dict):
            raise ValueError("Encrypted wallet payload is invalid")
        try:
            salt = self._coerce_bytes(encrypted["salt"])
            iv = self._coerce_bytes(encrypted["iv"])
            ciphertext = self._coerce_bytes(encrypted["ciphertext"])
        except Exception as e:
            raise ValueError(f"Encrypted wallet payload is invalid: {e}")
        try:
            key = self._derive_encryption_key(password, salt)
            private_key = AESGCM(key).decrypt(iv, ciphertext, None).decode("utf-8")
            return self._normalize_private_key(private_key)
        except Exception as e:
            raise ValueError(f"Invalid password or wallet data: {e}")

    def load_local_evm_account(self, encrypted: Dict[str, Any], password: str):
        if Account is None:
            raise ValueError("eth-account is required for local everPay wallet support")
        private_key = self.decrypt_private_key(encrypted, password)
        return Account.from_key(private_key)

    def create_local_wallet(self, password: str) -> LocalEverpayWallet:
        account = self.create_local_evm_account()
        created_at = datetime.now(timezone.utc).isoformat()
        state = {
            "version": 2,
            "type": "sapphire-everpay-local-wallet",
            "address": account["address"],
            "key_id": self.KEY_ID,
            "created_at": created_at,
            "encrypted_key": self.encrypt_private_key(account["private_key"], password),
        }
        self._write_state(state)
        self._wallet = Account.from_key(account["private_key"])
        return LocalEverpayWallet(
            address=account["address"],
            key_id=self.KEY_ID,
            created_at=created_at,
            storage_dir=str(self.storage_dir),
        )

    def _load_legacy_wallet(self, state: Dict[str, Any], password: str):
        if Account is None:
            raise ValueError("eth-account is required for local everPay wallet support")
        storage = self._build_legacy_storage(password, state["salt"])
        if not storage.load_vault():
            raise ValueError("Failed to load local everPay wallet vault")
        private_key = storage.retrieve_key(state["key_id"])
        if not private_key:
            raise ValueError("Invalid password or wallet data")
        return Account.from_key(private_key)

    def load_local_wallet(self, password: str) -> LocalEverpayWallet:
        state = self._read_state()
        if not state:
            raise ValueError("No local everPay wallet found")
        if state.get("encrypted_key"):
            self._wallet = self.load_local_evm_account(state["encrypted_key"], password)
        else:
            self._wallet = self._load_legacy_wallet(state, password)
        self._wallet_state = state
        return LocalEverpayWallet(
            address=self._wallet.address,
            key_id=state.get("key_id") or self.KEY_ID,
            created_at=state.get("created_at") or datetime.now(timezone.utc).isoformat(),
            storage_dir=str(self.storage_dir),
        )

    def unload_local_wallet(self):
        self._wallet = None

    def export_local_wallet(self, password: str, export_path: str) -> str:
        state = self._read_state()
        if not state:
            raise ValueError("No local everPay wallet found")
        if state.get("encrypted_key"):
            self.decrypt_private_key(state["encrypted_key"], password)
            export_payload = dict(state)
        else:
            storage = self._build_legacy_storage(password, state["salt"])
            if not storage.load_vault():
                raise ValueError("Failed to load local everPay wallet vault")
            private_key = storage.retrieve_key(state["key_id"])
            if not private_key:
                raise ValueError("Invalid password or wallet data")
            export_payload = {
                "version": state.get("version", 1),
                "type": state.get("type", "sapphire-everpay-local-wallet"),
                "address": state["address"],
                "key_id": state["key_id"],
                "salt": state["salt"],
                "created_at": state.get("created_at"),
                "vault": json.loads(storage.vault_encryption.export_vault_json()),
            }
        export_file = Path(export_path)
        export_file.write_text(json.dumps(export_payload, indent=2), encoding="utf-8")
        return str(export_file)

    def import_local_wallet(self, import_path: str, password: str) -> LocalEverpayWallet:
        if Account is None:
            raise ValueError("eth-account is required for local everPay wallet support")
        payload = json.loads(Path(import_path).read_text(encoding="utf-8"))
        if payload.get("encrypted_key"):
            wallet = self.load_local_evm_account(payload["encrypted_key"], password)
            state = {
                "version": payload.get("version", 2),
                "type": payload.get("type", "sapphire-everpay-local-wallet"),
                "address": wallet.address,
                "key_id": payload.get("key_id") or self.KEY_ID,
                "created_at": payload.get("created_at") or datetime.now(timezone.utc).isoformat(),
                "encrypted_key": payload["encrypted_key"],
            }
        else:
            salt_hex = payload.get("salt")
            if not salt_hex:
                raise ValueError("Imported wallet is missing salt metadata")
            storage = self._build_legacy_storage(password, salt_hex)
            if not storage.vault_encryption.import_vault_json(json.dumps(payload.get("vault") or {})):
                raise ValueError("Failed to import wallet vault")
            private_key = storage.retrieve_key(payload.get("key_id") or self.KEY_ID)
            if not private_key:
                raise ValueError("Invalid password or wallet data")
            wallet = Account.from_key(private_key)
            if payload.get("address") and wallet.address.lower() != payload["address"].lower():
                raise ValueError("Imported wallet address does not match vault contents")
            if not storage.save_vault():
                raise ValueError("Failed to persist imported wallet")
            state = {
                "version": payload.get("version", 1),
                "type": payload.get("type", "sapphire-everpay-local-wallet"),
                "address": wallet.address,
                "key_id": payload.get("key_id") or self.KEY_ID,
                "salt": salt_hex,
                "created_at": payload.get("created_at") or datetime.now(timezone.utc).isoformat(),
            }
        self._write_state(state)
        self._wallet = wallet
        return LocalEverpayWallet(
            address=wallet.address,
            key_id=state["key_id"],
            created_at=state["created_at"],
            storage_dir=str(self.storage_dir),
        )

    def get_everpay_message_data(self, tx: Dict[str, Any]) -> str:
        if not isinstance(tx, dict):
            raise ValueError("everPay transaction payload is invalid")
        missing_fields = [field for field in self.EVERPAY_MESSAGE_FIELDS if field not in tx]
        if missing_fields:
            raise ValueError(f"everPay transaction is missing required fields: {', '.join(missing_fields)}")
        return "\n".join(f"{field}:{tx[field]}" for field in self.EVERPAY_MESSAGE_FIELDS)

    def sign_everpay_tx(self, tx: Dict[str, Any]) -> str:
        if self._wallet is None:
            raise ValueError("Local everPay wallet is locked")
        if encode_defunct is None:
            raise ValueError("eth-account is required for local everPay wallet support")
        message = self.get_everpay_message_data(tx)
        signed = self._wallet.sign_message(encode_defunct(text=message))
        return signed.signature.hex()

    async def submit_everpay_tx(self, tx: Dict[str, Any], base_url: Optional[str] = None) -> Dict[str, Any]:
        client = EverpayClient(base_url=base_url or self.base_url)
        try:
            signature = self.sign_everpay_tx(tx)
            return await client.post_tx(tx, signature)
        finally:
            await client.close()

    async def get_balances(self, base_url: Optional[str] = None) -> Dict[str, Any]:
        address = self.get_wallet_address()
        if not address:
            raise ValueError("No local everPay wallet found")
        client = EverpayClient(base_url=base_url or self.base_url)
        try:
            return await client.get_balances(address)
        finally:
            await client.close()


_local_everpay_wallet_service: Optional[LocalEverpayWalletService] = None


def get_local_everpay_wallet_service() -> LocalEverpayWalletService:
    global _local_everpay_wallet_service
    if _local_everpay_wallet_service is None:
        _local_everpay_wallet_service = LocalEverpayWalletService()
    return _local_everpay_wallet_service
