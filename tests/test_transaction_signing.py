"""
Unit tests for transaction signing and broadcasting system.
Tests transaction builders, signers, broadcasters, and manager.
"""
import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from blockchain.transaction_builder import (
    TransactionBuilder,
    TransactionBuilderFactory,
    TransactionData,
    TransactionType,
    TransactionPriority,
    FeeEstimate,
    SolanaTransactionBuilder,
    NanoTransactionBuilder,
    ArweaveTransactionBuilder,
)
from blockchain.offline_signer import (
    OfflineSigner,
    OfflineSignerFactory,
    SignatureType,
    SignedTransaction,
    SolanaOfflineSigner,
    NanoOfflineSigner,
    ArweaveOfflineSigner,
)
from blockchain.broadcaster import (
    Broadcaster,
    BroadcasterFactory,
    BroadcastResult,
    BroadcastStatus,
)
from blockchain.transaction_tracker import (
    TransactionTracker,
    TransactionRecord,
    TransactionStatus,
)
from blockchain.transaction_manager import (
    TransactionManager,
    TransactionManagerFactory,
    TransactionWorkflow,
    TransactionPhase,
)


class TestTransactionBuilder:
    """Test transaction builder components."""
    
    def test_factory_create_solana(self):
        """Test creating Solana transaction builder."""
        builder = TransactionBuilderFactory.create("solana")
        assert isinstance(builder, SolanaTransactionBuilder)
        assert builder.chain == "solana"
        assert builder.asset == "usdc"
    
    def test_factory_create_nano(self):
        """Test creating Nano transaction builder."""
        builder = TransactionBuilderFactory.create("nano")
        assert isinstance(builder, NanoTransactionBuilder)
        assert builder.chain == "nano"
    
    def test_factory_create_arweave(self):
        """Test creating Arweave transaction builder."""
        builder = TransactionBuilderFactory.create("arweave")
        assert isinstance(builder, ArweaveTransactionBuilder)
        assert builder.chain == "arweave"
    
    def test_factory_unsupported_chain(self):
        """Test factory with unsupported chain."""
        with pytest.raises(ValueError, match="Unsupported chain"):
            TransactionBuilderFactory.create("invalid_chain")
    
    def test_get_supported_chains(self):
        """Test getting supported chains."""
        chains = TransactionBuilderFactory.get_supported_chains()
        assert "solana" in chains
        assert "nano" in chains
        assert "arweave" in chains
    
    @pytest.mark.asyncio
    async def test_solana_builder_build(self):
        """Test Solana transaction building."""
        builder = SolanaTransactionBuilder()
        
        tx_data = TransactionData(
            asset="usdc",
            chain="solana",
            transaction_type=TransactionType.TRANSFER,
            sender_address="DZnkkTmCiFWfYTfT41X3Rd1kJkMwS47sSikHtR9sApS",
            recipient_address="GrgttBWvji8rnucPAFqNzaESEqkqq82jMMhSgcJ1CZS",
            amount=100.0,
            fee=0.000005,
            priority=TransactionPriority.MEDIUM,
        )
        
        tx = await builder.build(tx_data)
        
        assert tx is not None
        assert tx["type"] == "solana_transfer"
        assert tx["sender"] == tx_data.sender_address
        assert tx["recipient"] == tx_data.recipient_address
        assert tx["amount"] == int(100.0 * 1e6)
    
    @pytest.mark.asyncio
    async def test_solana_builder_validate(self):
        """Test Solana transaction validation."""
        builder = SolanaTransactionBuilder()
        
        tx_data = TransactionData(
            asset="usdc",
            chain="solana",
            transaction_type=TransactionType.TRANSFER,
            sender_address="DZnkkTmCiFWfYTfT41X3Rd1kJkMwS47sSikHtR9sApS",
            recipient_address="GrgttBWvji8rnucPAFqNzaESEqkqq82jMMhSgcJ1CZS",
            amount=100.0,
        )
        
        await builder.build(tx_data)
        is_valid, message = await builder.validate()
        
        assert is_valid is True
    
    @pytest.mark.asyncio
    async def test_solana_estimate_fee(self):
        """Test Solana fee estimation."""
        builder = SolanaTransactionBuilder()
        
        tx_data = TransactionData(
            asset="usdc",
            chain="solana",
            transaction_type=TransactionType.TRANSFER,
            sender_address="DZnkkTmCiFWfYTfT41X3Rd1kJkMwS47sSikHtR9sApS",
            recipient_address="GrgttBWvji8rnucPAFqNzaESEqkqq82jMMhSgcJ1CZS",
            amount=100.0,
            priority=TransactionPriority.HIGH,
        )
        
        fee_estimate = await builder.estimate_fee(tx_data)
        
        assert fee_estimate.base_fee > 0
        assert fee_estimate.estimated_total > fee_estimate.base_fee
    
    @pytest.mark.asyncio
    async def test_nano_builder_build(self):
        """Test Nano transaction building."""
        builder = NanoTransactionBuilder()
        
        tx_data = TransactionData(
            asset="nano",
            chain="nano",
            transaction_type=TransactionType.TRANSFER,
            sender_address="nano_1abc123def456",
            recipient_address="nano_1xyz789abc456",
            amount=1.5,
        )
        
        tx = await builder.build(tx_data)
        
        assert tx is not None
        assert tx["type"] == "nano_state_block"
        assert tx["account"] == tx_data.sender_address
        assert tx["destination"] == tx_data.recipient_address
    
    @pytest.mark.asyncio
    async def test_arweave_builder_build(self):
        """Test Arweave transaction building."""
        builder = ArweaveTransactionBuilder()
        
        tx_data = TransactionData(
            asset="ar",
            chain="arweave",
            transaction_type=TransactionType.TRANSFER,
            sender_address="addr_sender_abc123",
            recipient_address="addr_recipient_xyz789",
            amount=0.5,
        )
        
        tx = await builder.build(tx_data)
        
        assert tx is not None
        assert tx["type"] == "arweave_transfer"
        assert tx["from"] == tx_data.sender_address
        assert tx["to"] == tx_data.recipient_address


class TestOfflineSigner:
    """Test offline signer components."""
    
    def test_signer_factory_solana(self):
        """Test creating Solana signer."""
        signer = OfflineSignerFactory.create("solana")
        assert isinstance(signer, SolanaOfflineSigner)
        assert signer.chain == "solana"
    
    def test_signer_factory_nano(self):
        """Test creating Nano signer."""
        signer = OfflineSignerFactory.create("nano")
        assert isinstance(signer, NanoOfflineSigner)
    
    def test_signer_factory_arweave(self):
        """Test creating Arweave signer."""
        signer = OfflineSignerFactory.create("arweave")
        assert isinstance(signer, ArweaveOfflineSigner)
    
    @pytest.mark.asyncio
    async def test_solana_signer_sign(self):
        """Test Solana transaction signing."""
        signer = SolanaOfflineSigner()
        
        test_private_key = bytes.fromhex("0" * 64)
        test_transaction = {
            "id": "test_tx_1",
            "sender": "DZnkkTmCiFWfYTfT41X3Rd1kJkMwS47sSikHtR9sApS",
            "amount": 1000000,
        }
        
        signed_tx = await signer.sign_transaction(test_transaction, test_private_key)
        
        assert signed_tx.is_valid is True
        assert len(signed_tx.signature) > 0
        assert signed_tx.signature_type == SignatureType.ED25519
    
    @pytest.mark.asyncio
    async def test_solana_signer_invalid_key_length(self):
        """Test Solana signer with invalid key length."""
        signer = SolanaOfflineSigner()
        
        invalid_key = bytes.fromhex("00ff")
        test_transaction = {"id": "test_tx_1"}
        
        signed_tx = await signer.sign_transaction(test_transaction, invalid_key)
        
        assert signed_tx.is_valid is False
        assert "Invalid private key length" in signed_tx.error
    
    @pytest.mark.asyncio
    async def test_nano_signer_sign(self):
        """Test Nano transaction signing."""
        signer = NanoOfflineSigner()
        
        test_private_key = bytes.fromhex("0" * 64)
        test_transaction = {
            "id": "test_block_1",
            "account": "nano_1abc123",
            "destination": "nano_1xyz789",
            "amount": 1000000000000000000000000000000,
        }
        
        signed_tx = await signer.sign_transaction(test_transaction, test_private_key)
        
        assert signed_tx.is_valid is True
        assert len(signed_tx.signature) > 0
        assert signed_tx.signature_type == SignatureType.ED25519
    
    @pytest.mark.asyncio
    async def test_arweave_signer_invalid_key(self):
        """Test Arweave signer with invalid key."""
        signer = ArweaveOfflineSigner()
        
        invalid_pem = b"invalid_key_data"
        test_transaction = {"id": "test_tx_1"}
        
        signed_tx = await signer.sign_transaction(test_transaction, invalid_pem)
        
        assert signed_tx.is_valid is False
        assert "Signing failed" in signed_tx.error


class TestBroadcaster:
    """Test broadcaster components."""
    
    def test_broadcaster_factory_solana(self):
        """Test creating Solana broadcaster."""
        broadcaster = BroadcasterFactory.create("solana")
        assert broadcaster.chain == "solana"
    
    def test_broadcaster_factory_nano(self):
        """Test creating Nano broadcaster."""
        broadcaster = BroadcasterFactory.create("nano")
        assert broadcaster.chain == "nano"
    
    def test_broadcaster_factory_arweave(self):
        """Test creating Arweave broadcaster."""
        broadcaster = BroadcasterFactory.create("arweave")
        assert broadcaster.chain == "arweave"
    
    @pytest.mark.asyncio
    async def test_broadcast_result_to_dict(self):
        """Test BroadcastResult serialization."""
        result = BroadcastResult(
            transaction_id="tx_123",
            broadcast_hash="hash_456",
            status=BroadcastStatus.SUBMITTED,
            confirmations=0,
        )
        
        data = result.to_dict()
        
        assert data["transaction_id"] == "tx_123"
        assert data["status"] == "submitted"


class TestTransactionTracker:
    """Test transaction tracker."""
    
    @pytest.mark.asyncio
    async def test_tracker_track_transaction(self, tmp_path):
        """Test tracking a transaction."""
        tracker = TransactionTracker(str(tmp_path / "test.db"))
        
        record = TransactionRecord(
            tx_id="tx_test_123",
            chain="solana",
            asset="usdc",
            from_address="addr_from",
            to_address="addr_to",
            amount=100.0,
            status=TransactionStatus.SUBMITTED,
            signature="sig_abc123",
            broadcast_hash="hash_xyz789",
        )
        
        success = await tracker.track(record)
        assert success is True
    
    @pytest.mark.asyncio
    async def test_tracker_get_transaction(self, tmp_path):
        """Test retrieving tracked transaction."""
        tracker = TransactionTracker(str(tmp_path / "test.db"))
        
        record = TransactionRecord(
            tx_id="tx_test_456",
            chain="nano",
            asset="nano",
            from_address="nano_1abc",
            to_address="nano_1xyz",
            amount=50.0,
            status=TransactionStatus.PENDING,
            signature="sig_123",
        )
        
        await tracker.track(record)
        retrieved = await tracker.get_transaction("tx_test_456")
        
        assert retrieved is not None
        assert retrieved.tx_id == "tx_test_456"
        assert retrieved.amount == 50.0
    
    @pytest.mark.asyncio
    async def test_tracker_update_status(self, tmp_path):
        """Test updating transaction status."""
        tracker = TransactionTracker(str(tmp_path / "test.db"))
        
        record = TransactionRecord(
            tx_id="tx_test_789",
            chain="arweave",
            asset="ar",
            from_address="addr_from",
            to_address="addr_to",
            amount=1.0,
            status=TransactionStatus.SUBMITTED,
            signature="sig_789",
        )
        
        await tracker.track(record)
        success = await tracker.update_status(
            "tx_test_789",
            TransactionStatus.CONFIRMED,
            confirmations=1,
        )
        
        assert success is True
        updated = await tracker.get_transaction("tx_test_789")
        assert updated.status == TransactionStatus.CONFIRMED
        assert updated.confirmations == 1
    
    @pytest.mark.asyncio
    async def test_tracker_list_pending(self, tmp_path):
        """Test listing pending transactions."""
        tracker = TransactionTracker(str(tmp_path / "test.db"))
        
        record1 = TransactionRecord(
            tx_id="tx_pending_1",
            chain="solana",
            asset="usdc",
            from_address="addr1",
            to_address="addr2",
            amount=10.0,
            status=TransactionStatus.PENDING,
            signature="sig1",
        )
        
        record2 = TransactionRecord(
            tx_id="tx_confirmed_1",
            chain="solana",
            asset="usdc",
            from_address="addr1",
            to_address="addr2",
            amount=20.0,
            status=TransactionStatus.CONFIRMED,
            signature="sig2",
        )
        
        await tracker.track(record1)
        await tracker.track(record2)
        
        pending = await tracker.list_pending("solana")
        
        assert len(pending) >= 1
        assert any(tx.tx_id == "tx_pending_1" for tx in pending)


class TestTransactionManager:
    """Test unified transaction manager."""
    
    def test_manager_factory_create(self):
        """Test creating transaction manager."""
        manager = TransactionManagerFactory.create("solana")
        assert isinstance(manager, TransactionManager)
        assert manager.chain == "solana"
    
    def test_manager_factory_unsupported_chain(self):
        """Test factory with unsupported chain."""
        with pytest.raises(ValueError):
            TransactionManagerFactory.create("invalid")
    
    @pytest.mark.asyncio
    async def test_manager_prepare_transaction(self):
        """Test preparing a transaction."""
        manager = TransactionManagerFactory.create("solana")
        
        tx_data = TransactionData(
            asset="usdc",
            chain="solana",
            transaction_type=TransactionType.TRANSFER,
            sender_address="DZnkkTmCiFWfYTfT41X3Rd1kJkMwS47sSikHtR9sApS",
            recipient_address="GrgttBWvji8rnucPAFqNzaESEqkqq82jMMhSgcJ1CZS",
            amount=50.0,
        )
        
        success, workflow = await manager.prepare(tx_data)
        
        assert success is True
        assert workflow.phase == TransactionPhase.PREPARED
        assert workflow.built_transaction is not None
    
    @pytest.mark.asyncio
    async def test_manager_sign_transaction(self):
        """Test signing a prepared transaction."""
        manager = TransactionManagerFactory.create("solana")
        
        tx_data = TransactionData(
            asset="usdc",
            chain="solana",
            transaction_type=TransactionType.TRANSFER,
            sender_address="DZnkkTmCiFWfYTfT41X3Rd1kJkMwS47sSikHtR9sApS",
            recipient_address="GrgttBWvji8rnucPAFqNzaESEqkqq82jMMhSgcJ1CZS",
            amount=50.0,
        )
        
        success, workflow = await manager.prepare(tx_data)
        assert success is True
        
        test_private_key = bytes.fromhex("0" * 64)
        success, workflow = await manager.sign(workflow, test_private_key)
        
        assert success is True
        assert workflow.phase == TransactionPhase.SIGNED
        assert workflow.signed_transaction is not None
    
    @pytest.mark.asyncio
    async def test_manager_estimate_fee(self):
        """Test fee estimation."""
        manager = TransactionManagerFactory.create("nano")
        
        tx_data = TransactionData(
            asset="nano",
            chain="nano",
            transaction_type=TransactionType.TRANSFER,
            sender_address="nano_1abc",
            recipient_address="nano_1xyz",
            amount=1.0,
        )
        
        fee_estimate = await manager.estimate_fee(tx_data)
        
        assert fee_estimate is not None
        assert "estimated_total" in fee_estimate
        assert fee_estimate["estimated_total"] == 0.0


class TestTransactionDataValidation:
    """Test transaction data validation."""
    
    def test_transaction_data_creation(self):
        """Test creating transaction data."""
        tx_data = TransactionData(
            asset="usdc",
            chain="solana",
            transaction_type=TransactionType.TRANSFER,
            sender_address="addr_from",
            recipient_address="addr_to",
            amount=100.0,
        )
        
        assert tx_data.asset == "usdc"
        assert tx_data.amount == 100.0
        assert tx_data.priority == TransactionPriority.MEDIUM
    
    def test_transaction_data_to_dict(self):
        """Test converting transaction data to dictionary."""
        tx_data = TransactionData(
            asset="nano",
            chain="nano",
            transaction_type=TransactionType.TRANSFER,
            sender_address="nano_1abc",
            recipient_address="nano_1xyz",
            amount=50.0,
            priority=TransactionPriority.HIGH,
        )
        
        data_dict = tx_data.to_dict()
        
        assert data_dict["asset"] == "nano"
        assert data_dict["transaction_type"] == "transfer"
        assert data_dict["priority"] == "high"


class TestIntegration:
    """Integration tests for full transaction workflows."""
    
    @pytest.mark.asyncio
    async def test_solana_workflow_build_and_sign(self):
        """Test complete Solana workflow: build and sign."""
        manager = TransactionManagerFactory.create("solana")
        
        tx_data = TransactionData(
            asset="usdc",
            chain="solana",
            transaction_type=TransactionType.TRANSFER,
            sender_address="DZnkkTmCiFWfYTfT41X3Rd1kJkMwS47sSikHtR9sApS",
            recipient_address="GrgttBWvji8rnucPAFqNzaESEqkqq82jMMhSgcJ1CZS",
            amount=75.0,
            priority=TransactionPriority.HIGH,
        )
        
        success, workflow = await manager.prepare(tx_data)
        assert success is True
        
        private_key = bytes.fromhex("0" * 64)
        success, workflow = await manager.sign(workflow, private_key)
        assert success is True
        assert workflow.signed_transaction is not None
    
    @pytest.mark.asyncio
    async def test_nano_workflow_build_and_sign(self):
        """Test complete Nano workflow: build and sign."""
        manager = TransactionManagerFactory.create("nano")
        
        tx_data = TransactionData(
            asset="nano",
            chain="nano",
            transaction_type=TransactionType.TRANSFER,
            sender_address="nano_1abc123456789",
            recipient_address="nano_1xyz987654321",
            amount=10.5,
        )
        
        success, workflow = await manager.prepare(tx_data)
        assert success is True
        assert workflow.built_transaction["account"] == "nano_1abc123456789"
        
        private_key = bytes.fromhex("0" * 64)
        success, workflow = await manager.sign(workflow, private_key)
        assert success is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
