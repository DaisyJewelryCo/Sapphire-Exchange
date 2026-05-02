import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SERVICES_DIR = ROOT / "services"
SECURITY_DIR = ROOT / "security"

services_package = sys.modules.get("services")
if services_package is None:
    services_package = types.ModuleType("services")
    services_package.__path__ = [str(SERVICES_DIR)]
    sys.modules["services"] = services_package

security_package = sys.modules.get("security")
if security_package is None:
    security_package = types.ModuleType("security")
    security_package.__path__ = [str(SECURITY_DIR)]
    sys.modules["security"] = security_package

for module_name, file_name in [
    ("security.vault_encryption", "vault_encryption.py"),
    ("security.password_manager", "password_manager.py"),
    ("security.key_storage", "key_storage.py"),
    ("services.everpay_client", "everpay_client.py"),
    ("services.local_everpay_wallet_service", "local_everpay_wallet_service.py"),
]:
    spec = importlib.util.spec_from_file_location(module_name, (SECURITY_DIR if module_name.startswith("security.") else SERVICES_DIR) / file_name)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

wallet_module = sys.modules["services.local_everpay_wallet_service"]
LocalEverpayWalletService = wallet_module.LocalEverpayWalletService


@pytest.mark.skipif(wallet_module.Account is None, reason="eth-account is not installed")
def test_create_load_export_and_import_local_wallet(tmp_path):
    service = LocalEverpayWalletService(storage_dir=tmp_path / "wallet")

    created_wallet = service.create_local_wallet("strong-password-123")
    assert created_wallet.address.startswith("0x")
    assert service.has_local_wallet() is True
    assert service.is_wallet_loaded() is True

    exported_path = tmp_path / "wallet-export.json"
    export_result = service.export_local_wallet("strong-password-123", str(exported_path))
    assert export_result == str(exported_path)
    assert exported_path.exists()

    exported_payload = json.loads(exported_path.read_text(encoding="utf-8"))
    assert exported_payload["address"] == created_wallet.address
    assert exported_payload["type"] == "sapphire-everpay-local-wallet"
    assert "encrypted_key" in exported_payload

    service.unload_local_wallet()
    loaded_wallet = service.load_local_wallet("strong-password-123")
    assert loaded_wallet.address == created_wallet.address

    imported_service = LocalEverpayWalletService(storage_dir=tmp_path / "imported-wallet")
    imported_wallet = imported_service.import_local_wallet(str(exported_path), "strong-password-123")
    assert imported_wallet.address == created_wallet.address
    assert imported_service.get_wallet_status()["available"] is True


@pytest.mark.skipif(wallet_module.Account is None, reason="eth-account is not installed")
def test_encrypt_and_load_local_evm_account(tmp_path):
    service = LocalEverpayWalletService(storage_dir=tmp_path / "wallet")

    account = service.create_local_evm_account()
    encrypted = service.encrypt_private_key(account["private_key"], "strong-password-123")
    loaded_wallet = service.load_local_evm_account(encrypted, "strong-password-123")

    assert loaded_wallet.address == account["address"]
    assert service.decrypt_private_key(encrypted, "strong-password-123") == account["private_key"]


@pytest.mark.skipif(wallet_module.Account is None, reason="eth-account is not installed")
def test_sign_everpay_tx_requires_loaded_wallet(tmp_path):
    service = LocalEverpayWalletService(storage_dir=tmp_path / "wallet")
    service.create_local_wallet("strong-password-123")
    service.unload_local_wallet()

    with pytest.raises(ValueError, match="locked"):
        service.sign_everpay_tx(
            {
                "tokenSymbol": "USDC",
                "action": "transfer",
                "from": "0x1",
                "to": "everpay",
                "amount": "1",
                "fee": "0",
                "feeRecipient": "0x2",
                "nonce": "1",
                "tokenID": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
                "chainType": "ethereum",
                "chainID": "1",
                "data": "",
                "version": "v1",
            }
        )


@pytest.mark.skipif(wallet_module.Account is None, reason="eth-account is not installed")
def test_get_everpay_message_data_uses_protocol_field_order(tmp_path):
    service = LocalEverpayWalletService(storage_dir=tmp_path / "wallet")

    message = service.get_everpay_message_data(
        {
            "tokenSymbol": "USDC",
            "action": "transfer",
            "from": "0xabc",
            "to": "everpay",
            "amount": "1000000",
            "fee": "0",
            "feeRecipient": "0xdef",
            "nonce": "123",
            "tokenID": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
            "chainType": "ethereum",
            "chainID": "1",
            "data": "{\"swapTo\":\"arweave-token\"}",
            "version": "v1",
            "swapTo": "arweave-token",
        }
    )

    assert message == (
        "tokenSymbol:USDC\n"
        "action:transfer\n"
        "from:0xabc\n"
        "to:everpay\n"
        "amount:1000000\n"
        "fee:0\n"
        "feeRecipient:0xdef\n"
        "nonce:123\n"
        "tokenID:0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48\n"
        "chainType:ethereum\n"
        "chainID:1\n"
        "data:{\"swapTo\":\"arweave-token\"}\n"
        "version:v1"
    )
