import importlib.util
import sys
import types
from pathlib import Path
from types import SimpleNamespace

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

funding_spec = importlib.util.spec_from_file_location(
    "services.funding_manager_service",
    SERVICES_DIR / "funding_manager_service.py",
)
funding_module = importlib.util.module_from_spec(funding_spec)
sys.modules["services.funding_manager_service"] = funding_module
funding_spec.loader.exec_module(funding_module)

arweave_spec = importlib.util.spec_from_file_location(
    "services.arweave_purchase_service",
    SERVICES_DIR / "arweave_purchase_service.py",
)
arweave_purchase_service_module = importlib.util.module_from_spec(arweave_spec)
sys.modules["services.arweave_purchase_service"] = arweave_purchase_service_module
arweave_spec.loader.exec_module(arweave_purchase_service_module)

ArweavePurchaseService = arweave_purchase_service_module.ArweavePurchaseService
FundingConfig = funding_module.FundingConfig


@pytest.fixture
def everpay_config(monkeypatch):
    config = FundingConfig(
        arweave_native_provider="everpay",
        everpay_api_url="https://api.everpay.io",
        everpay_input_token="ethereum-usdc-0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
        everpay_ar_token="arweave,ethereum-ar-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA,0x4fadc7a98f2dc96510e42dd1a74141eeae0c1543",
        everpay_address="0xSigner",
    )
    monkeypatch.setattr(
        arweave_purchase_service_module,
        "get_funding_manager_service",
        lambda: SimpleNamespace(config=config),
    )
    return config


class TestArweavePurchaseService:
    @pytest.mark.asyncio
    async def test_get_native_provider_quote_returns_everpay_estimate(
        self,
        everpay_config,
        monkeypatch,
    ):
        service = ArweavePurchaseService()

        async def fake_get_token_info(identifier):
            if "usdc" in identifier.lower():
                return {"tag": "ethereum-usdc-0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"}
            return {"tag": "arweave,ethereum-ar-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA,0x4fadc7a98f2dc96510e42dd1a74141eeae0c1543"}

        async def fake_fetch_market_quote(_payment_amount):
            return {"usd_price": 8.5, "ar_amount": 0.25}

        monkeypatch.setattr(service, "_get_token_info", fake_get_token_info)
        monkeypatch.setattr(service, "_fetch_market_quote", fake_fetch_market_quote)
        monkeypatch.setattr(service, "_get_everpay_private_key", lambda: None)

        quote = await service.get_native_provider_quote(2.125, payment_currency="USDC")

        assert quote is not None
        assert quote["provider"]["id"] == "everpay"
        assert quote["provider"]["name"] == "everPay"
        assert quote["amount_winston"] == str(int(0.25 * service.AR_DECIMALS))
        assert quote["unit_price"] == 8.5
        assert quote["executable"] is False
        assert "local everPay wallet" in quote["status_message"]

    @pytest.mark.asyncio
    async def test_get_quote_builds_everpay_route_description(
        self,
        everpay_config,
        monkeypatch,
    ):
        service = ArweavePurchaseService()

        async def fake_provider_quote(payment_amount, payment_currency="USDC"):
            assert payment_amount == 1.0
            assert payment_currency == "USDC"
            return {
                "provider": {"name": "everPay", "id": "everpay"},
                "amount_winston": "250000000000",
                "unit_price": 8.5,
                "raw": {"market_quote": {"usd_price": 8.5, "ar_amount": 0.25}},
                "executable": True,
                "status_message": "everPay direct estimate ready.",
            }

        monkeypatch.setattr(service, "get_native_provider_quote", fake_provider_quote)

        quote = await service.get_quote(1.0)

        assert quote is not None
        assert quote.input_amount == 1_000_000
        assert quote.output_amount == 250000000000
        assert quote.executable is True
        assert quote.status_message == "everPay direct estimate ready."
        assert quote.route_description == "everPay Direct (AR/USD: $8.500000)"

    @pytest.mark.asyncio
    async def test_execute_native_purchase_requires_signer_address(
        self,
        everpay_config,
        monkeypatch,
    ):
        service = ArweavePurchaseService()
        monkeypatch.setattr(service, "_get_everpay_signer_address", lambda: None)

        result = await service.execute_native_purchase(
            user_pubkey="payer-reference",
            payment_amount=1.0,
            arweave_address="arweave-address",
            payment_currency="USDC",
        )

        assert result is None
        assert service.last_error == "everPay signer address is not configured"

    @pytest.mark.asyncio
    async def test_execute_native_purchase_submits_swap_and_withdraw(
        self,
        everpay_config,
        monkeypatch,
    ):
        service = ArweavePurchaseService()
        submitted_payloads = []

        async def fake_get_token_info(identifier):
            if "usdc" in identifier.lower():
                return {"tag": "ethereum-usdc-0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"}
            return {"tag": "arweave,ethereum-ar-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA,0x4fadc7a98f2dc96510e42dd1a74141eeae0c1543"}

        async def fake_get_token_balance(address, token_identifier):
            assert address == "0xSigner"
            if "usdc" in token_identifier.lower():
                return 2_000_000
            return 0

        async def fake_submit_everpay_tx(payload):
            submitted_payloads.append(payload)
            if payload["action"] == "swap":
                return {"reference": "0xswitch", "payload": payload, "response": {}}
            return {"reference": "0xwithdraw", "payload": payload, "response": {}}

        async def fake_await_balance_increase(address, token_identifier, starting_balance, attempts=6, delay=2.0):
            assert address == "0xSigner"
            assert starting_balance == 0
            assert "ar" in token_identifier.lower()
            return 125000000000

        async def fake_poll_transaction_record(everhash, attempts=5, delay=2.0):
            assert everhash == "0xwithdraw"
            return {"targetChainTxHash": "arweave-native-tx"}

        monkeypatch.setattr(service, "_get_everpay_signer_address", lambda: "0xSigner")
        monkeypatch.setattr(service, "_get_token_info", fake_get_token_info)
        monkeypatch.setattr(service, "_get_token_balance", fake_get_token_balance)
        monkeypatch.setattr(service, "_submit_everpay_tx", fake_submit_everpay_tx)
        monkeypatch.setattr(service, "_await_balance_increase", fake_await_balance_increase)
        monkeypatch.setattr(service, "_poll_transaction_record", fake_poll_transaction_record)

        result = await service.execute_native_purchase(
            user_pubkey="payer-reference",
            payment_amount=1.0,
            arweave_address="arweave-address",
            payment_currency="USDC",
        )

        assert result is not None
        assert result["success"] is True
        assert result["provider"] == "everPay"
        assert result["transaction_id"] == "0xswitch"
        assert result["withdraw_transaction_id"] == "0xwithdraw"
        assert result["arweave_tx_id"] == "arweave-native-tx"
        assert result["native_delivery"] is True
        assert result["withdraw_amount_winston"] == "125000000000"
        assert submitted_payloads[0]["action"] == "swap"
        assert submitted_payloads[0]["amount"] == "1000000"
        assert submitted_payloads[0]["swapTo"].startswith("arweave")
        assert submitted_payloads[1] == {
            "action": "withdraw",
            "from": "0xSigner",
            "token": "arweave,ethereum-ar-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA,0x4fadc7a98f2dc96510e42dd1a74141eeae0c1543",
            "amount": "125000000000",
            "target": "arweave-address",
            "nonce": submitted_payloads[1]["nonce"],
        }
