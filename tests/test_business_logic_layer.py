"""
Unit tests for BusinessLogicLayer.

Coverage targets (per project spec: 70-80% of Business Logic Layer):
  - process_block_data
  - process_transaction_data  (pass / filtered / no-to address)
  - passes_filters
  - get_aggregated_stats
  - get_live_analytics
  - fetch_latest_blocks       (mocked HTTP calls)
  - _process_block_with_tx    (mocked, tx / no-tx / filtered variants)
"""

import asyncio
from decimal import Decimal
from unittest.mock import MagicMock, AsyncMock, patch, call

import pytest

from business_logic_layer import BlockchainLogic
from config import AppConfig


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers / Fixtures
# ─────────────────────────────────────────────────────────────────────────────

def make_access(from_wei_side_effect=None):
    """Return a mock BlockchainAccess with sensible defaults."""
    access = MagicMock()
    # Default from_wei: just return the value divided by 1e18 (ETH conversion)
    if from_wei_side_effect:
        access.from_wei.side_effect = from_wei_side_effect
    else:
        access.from_wei.side_effect = lambda value, unit: value / 10**18
    return access


def make_reporter():
    return MagicMock()


def make_app_config(**kwargs):
    defaults = dict(blocks_to_fetch=100, reconnect_delay=5, request_delay=0)
    defaults.update(kwargs)
    return AppConfig(**defaults)


def make_block(number=1000, tx_hashes=None, timestamp=1_700_000_000):
    """Return a dict resembling a web3 block."""
    if tx_hashes is None:
        tx_hashes = [b"\xaa" * 32]
    return {
        "number": number,
        "hash": b"\xbb" * 32,
        "transactions": tx_hashes,
        "timestamp": timestamp,
    }


def make_tx_details(value=10**18, gas_price=10**9, from_addr="0xSender", to_addr="0xReceiver"):
    return {
        "hash": b"\xcc" * 32,
        "from": from_addr,
        "to": to_addr,
        "value": value,
        "gasPrice": gas_price,
        "input": "0x",
    }


def make_tx_receipt(gas_used=21_000, status=1):
    return {"gasUsed": gas_used, "status": status}


# ─────────────────────────────────────────────────────────────────────────────
#  process_block_data
# ─────────────────────────────────────────────────────────────────────────────

class TestProcessBlockData:
    def setup_method(self):
        self.logic = BlockchainLogic(make_access(), make_reporter(), make_app_config())

    def test_returns_correct_fields(self):
        block = make_block(number=42, tx_hashes=["a", "b", "c"])
        result = self.logic.process_block_data(block)
        assert result["number"] == 42
        assert result["transactions_count"] == 3

    def test_hash_bytes_converted_to_hex(self):
        block = make_block()
        result = self.logic.process_block_data(block)
        assert isinstance(result["hash"], str)
        assert result["hash"] == (b"\xbb" * 32).hex()

    def test_hash_string_passed_through(self):
        block = make_block()
        block["hash"] = "0xdeadbeef"
        result = self.logic.process_block_data(block)
        assert result["hash"] == "0xdeadbeef"

    def test_increments_total_blocks(self):
        self.logic.process_block_data(make_block(tx_hashes=[]))
        self.logic.process_block_data(make_block(tx_hashes=[]))
        assert self.logic.stats["total_blocks"] == 2

    def test_increments_total_transactions(self):
        self.logic.process_block_data(make_block(tx_hashes=["x", "y"]))
        self.logic.process_block_data(make_block(tx_hashes=["z"]))
        assert self.logic.stats["total_transactions"] == 3

    def test_empty_block_has_zero_tx(self):
        block = make_block(tx_hashes=[])
        result = self.logic.process_block_data(block)
        assert result["transactions_count"] == 0

    def test_timestamp_stored_and_sorted(self):
        self.logic.process_block_data(make_block(timestamp=200))
        self.logic.process_block_data(make_block(timestamp=100))
        assert self.logic.stats["block_timestamps"] == [100, 200]

    def test_no_timestamp_key_does_not_crash(self):
        block = {"number": 1, "hash": "0x1", "transactions": []}
        # Should not raise
        self.logic.process_block_data(block)
        assert self.logic.stats["block_timestamps"] == []


# ─────────────────────────────────────────────────────────────────────────────
#  process_transaction_data
# ─────────────────────────────────────────────────────────────────────────────

class TestProcessTransactionData:
    def setup_method(self):
        self.access = make_access()
        self.reporter = make_reporter()
        self.logic = BlockchainLogic(self.access, self.reporter, make_app_config())

    def test_returns_correct_fields_when_no_filter(self):
        tx = make_tx_details(value=2 * 10**18, gas_price=10**9)
        receipt = make_tx_receipt(gas_used=21_000)
        result = self.logic.process_transaction_data(tx, receipt)
        assert result is not None
        assert result["sender"] == "0xSender"
        assert result["receiver"] == "0xReceiver"
        assert result["gas_used"] == 21_000
        assert result["gas_price_wei"] == 10**9

    def test_hash_bytes_converted_to_hex(self):
        tx = make_tx_details()
        result = self.logic.process_transaction_data(tx, make_tx_receipt())
        assert result["hash"] == (b"\xcc" * 32).hex()

    def test_hash_string_passed_through(self):
        tx = make_tx_details()
        tx["hash"] = "0xabcdef"
        result = self.logic.process_transaction_data(tx, make_tx_receipt())
        assert result["hash"] == "0xabcdef"

    def test_accumulates_gas_used(self):
        self.logic.process_transaction_data(make_tx_details(), make_tx_receipt(gas_used=21_000))
        self.logic.process_transaction_data(make_tx_details(), make_tx_receipt(gas_used=50_000))
        assert self.logic.stats["total_gas_used"] == 71_000

    def test_accumulates_eth_value(self):
        # from_wei returns value / 1e18, so 1e18 wei → 1.0 ETH
        self.logic.process_transaction_data(make_tx_details(value=10**18), make_tx_receipt())
        self.logic.process_transaction_data(make_tx_details(value=2 * 10**18), make_tx_receipt())
        assert self.logic.stats["total_eth_value"] == Decimal("3.0")

    def test_tracks_unique_senders_and_receivers(self):
        self.logic.process_transaction_data(
            make_tx_details(from_addr="0xA", to_addr="0xB"), make_tx_receipt()
        )
        self.logic.process_transaction_data(
            make_tx_details(from_addr="0xA", to_addr="0xC"), make_tx_receipt()
        )
        assert len(self.logic.stats["unique_senders"]) == 1
        assert len(self.logic.stats["unique_receivers"]) == 2

    def test_no_to_address_does_not_crash(self):
        tx = make_tx_details(to_addr=None)
        result = self.logic.process_transaction_data(tx, make_tx_receipt())
        assert result is not None
        assert result["receiver"] is None

    def test_filtered_transaction_returns_none(self):
        mock_filter = MagicMock()
        mock_filter.apply.return_value = False
        self.logic.filters = [mock_filter]
        result = self.logic.process_transaction_data(make_tx_details(), make_tx_receipt())
        assert result is None

    def test_filtered_transaction_increments_counter(self):
        mock_filter = MagicMock()
        mock_filter.apply.return_value = False
        self.logic.filters = [mock_filter]
        self.logic.process_transaction_data(make_tx_details(), make_tx_receipt())
        assert self.logic.stats["filtered_transactions"] == 1

    def test_passing_filter_does_not_increment_filtered_counter(self):
        mock_filter = MagicMock()
        mock_filter.apply.return_value = True
        self.logic.filters = [mock_filter]
        self.logic.process_transaction_data(make_tx_details(), make_tx_receipt())
        assert self.logic.stats["filtered_transactions"] == 0


# ─────────────────────────────────────────────────────────────────────────────
#  passes_filters
# ─────────────────────────────────────────────────────────────────────────────

class TestPassesFilters:
    def setup_method(self):
        self.access = make_access()
        self.logic = BlockchainLogic(self.access, make_reporter(), make_app_config())

    def _make_filter(self, result: bool):
        f = MagicMock()
        f.apply.return_value = result
        return f

    def test_no_filters_returns_true(self):
        assert self.logic.passes_filters(make_tx_details(), make_tx_receipt()) is True

    def test_all_passing_filters_returns_true(self):
        self.logic.filters = [self._make_filter(True), self._make_filter(True)]
        assert self.logic.passes_filters(make_tx_details(), make_tx_receipt()) is True

    def test_one_failing_filter_returns_false(self):
        self.logic.filters = [self._make_filter(True), self._make_filter(False)]
        assert self.logic.passes_filters(make_tx_details(), make_tx_receipt()) is False

    def test_all_failing_filters_returns_false(self):
        self.logic.filters = [self._make_filter(False), self._make_filter(False)]
        assert self.logic.passes_filters(make_tx_details(), make_tx_receipt()) is False

    def test_filter_receives_correct_arguments(self):
        mock_filter = self._make_filter(True)
        self.logic.filters = [mock_filter]
        tx = make_tx_details()
        receipt = make_tx_receipt()
        self.logic.passes_filters(tx, receipt)
        mock_filter.apply.assert_called_once_with(tx, receipt, self.access)


# ─────────────────────────────────────────────────────────────────────────────
#  get_aggregated_stats
# ─────────────────────────────────────────────────────────────────────────────

class TestGetAggregatedStats:
    def setup_method(self):
        self.logic = BlockchainLogic(make_access(), make_reporter(), make_app_config())

    def test_zero_blocks_returns_zeroes(self):
        stats = self.logic.get_aggregated_stats()
        assert stats["summary_blocks_processed"] == 0
        assert stats["summary_transactions_monitored"] == 0
        assert stats["average_gas_per_block"] == 0
        assert stats["total_value_transferred_eth"] == 0

    def test_average_gas_calculated_correctly(self):
        self.logic.stats["total_blocks"] = 4
        self.logic.stats["total_gas_used"] = 200
        stats = self.logic.get_aggregated_stats()
        assert stats["average_gas_per_block"] == 50.0

    def test_total_value_rounded_to_6_places(self):
        self.logic.stats["total_blocks"] = 1
        self.logic.stats["total_eth_value"] = Decimal("1.1234567890")
        stats = self.logic.get_aggregated_stats()
        assert stats["total_value_transferred_eth"] == round(Decimal("1.1234567890"), 6)

    def test_reflects_processed_counts(self):
        self.logic.stats["total_blocks"] = 10
        self.logic.stats["total_transactions"] = 250
        stats = self.logic.get_aggregated_stats()
        assert stats["summary_blocks_processed"] == 10
        assert stats["summary_transactions_monitored"] == 250


# ─────────────────────────────────────────────────────────────────────────────
#  get_live_analytics
# ─────────────────────────────────────────────────────────────────────────────

class TestGetLiveAnalytics:
    def setup_method(self):
        self.logic = BlockchainLogic(make_access(), make_reporter(), make_app_config())

    def test_returns_all_expected_keys(self):
        analytics = self.logic.get_live_analytics()
        expected_keys = {
            "avg_block_time", "avg_fee_tx", "avg_eth_tx",
            "avg_tx_per_block", "avg_gas_per_block",
            "unique_senders", "unique_receivers", "total_fees_pool",
        }
        assert expected_keys == set(analytics.keys())

    def test_zeros_when_no_data(self):
        analytics = self.logic.get_live_analytics()
        assert analytics["avg_block_time"] == "0.00 s"
        assert analytics["unique_senders"] == "0"
        assert analytics["unique_receivers"] == "0"

    def test_avg_block_time_calculated_correctly(self):
        self.logic.stats["block_timestamps"] = [1000, 1012, 1024]  # 12s intervals
        analytics = self.logic.get_live_analytics()
        assert analytics["avg_block_time"] == "12.00 s"

    def test_unique_address_counts(self):
        self.logic.stats["unique_senders"] = {"0xA", "0xB", "0xC"}
        self.logic.stats["unique_receivers"] = {"0xX"}
        analytics = self.logic.get_live_analytics()
        assert analytics["unique_senders"] == "3"
        assert analytics["unique_receivers"] == "1"

    def test_avg_fee_and_eth_per_tx(self):
        self.logic.stats["total_blocks"] = 1
        self.logic.stats["total_transactions"] = 2
        self.logic.stats["total_fees_eth"] = Decimal("0.002")
        self.logic.stats["total_eth_value"] = Decimal("4.0")
        analytics = self.logic.get_live_analytics()
        assert analytics["avg_fee_tx"] == "0.001000000 ETH"
        assert analytics["avg_eth_tx"] == "2.000000000 ETH"

    def test_single_timestamp_block_time_is_zero(self):
        self.logic.stats["block_timestamps"] = [999]
        analytics = self.logic.get_live_analytics()
        assert analytics["avg_block_time"] == "0.00 s"


# ─────────────────────────────────────────────────────────────────────────────
#  _process_block_with_tx  (async)
# ─────────────────────────────────────────────────────────────────────────────

class TestProcessBlockWithTx:
    def setup_method(self):
        self.access = make_access()
        self.reporter = make_reporter()
        self.logic = BlockchainLogic(self.access, self.reporter, make_app_config())

    def _run(self, coro):
        return asyncio.run(coro)

    def test_calls_report_block(self):
        self.access.get_block.return_value = make_block(number=5, tx_hashes=[])
        self._run(self.logic._process_block_with_tx(5, iteration=1, fetch_tx=False))
        self.reporter.report_block.assert_called_once()
        args = self.reporter.report_block.call_args[0]
        assert args[0]["number"] == 5
        assert args[1] == 1

    def test_no_tx_reported_when_fetch_tx_false(self):
        self.access.get_block.return_value = make_block(tx_hashes=["x"])
        self._run(self.logic._process_block_with_tx(5, fetch_tx=False))
        self.reporter.report_transaction.assert_not_called()
        self.reporter.report_no_transactions.assert_not_called()

    def test_report_no_transactions_when_block_empty(self):
        self.access.get_block.return_value = make_block(tx_hashes=[])
        self._run(self.logic._process_block_with_tx(5, fetch_tx=True))
        self.reporter.report_no_transactions.assert_called_once()

    def test_report_transaction_when_tx_passes_filter(self):
        tx = make_tx_details()
        receipt = make_tx_receipt()
        self.access.get_block.return_value = make_block(tx_hashes=[tx])
        self.access.get_transaction_receipt.return_value = receipt
        # Patch process_transaction_data to return a fake tx_data dict
        self.logic.process_transaction_data = MagicMock(return_value={
            "hash": "0xfake", "sender": "0xA", "receiver": "0xB",
            "amount_eth": 1.0, "gas_used": 21000,
            "gas_price_wei": 10**9, "fee_eth": 0.001,
        })
        self._run(self.logic._process_block_with_tx(5, fetch_tx=True))
        self.reporter.report_transaction.assert_called_once()

    def test_report_filtered_transaction_when_tx_filtered(self):
        tx = make_tx_details()
        receipt = make_tx_receipt()
        self.access.get_block.return_value = make_block(tx_hashes=[tx])
        self.access.get_transaction_receipt.return_value = receipt
        self.logic.process_transaction_data = MagicMock(return_value=None)
        self._run(self.logic._process_block_with_tx(5, fetch_tx=True))
        self.reporter.report_filtered_transaction.assert_called_once()

    def test_uses_block_num_as_iteration_when_none(self):
        self.access.get_block.return_value = make_block(number=999, tx_hashes=[])
        self._run(self.logic._process_block_with_tx(999, iteration=None, fetch_tx=False))
        args = self.reporter.report_block.call_args[0]
        assert args[1] == 999


# ─────────────────────────────────────────────────────────────────────────────
#  fetch_latest_blocks  (async)
# ─────────────────────────────────────────────────────────────────────────────

class TestFetchLatestBlocks:
    def setup_method(self):
        self.access = make_access()
        self.reporter = make_reporter()
        self.reporter.logger = MagicMock()
        self.logic = BlockchainLogic(self.access, self.reporter, make_app_config(blocks_to_fetch=5))

    def _run(self, coro):
        return asyncio.run(coro)

    def _make_block_for_num(self, num):
        return make_block(number=num, tx_hashes=[], timestamp=1_700_000_000 + num)

    def test_fetches_correct_number_of_blocks(self):
        latest = 1004
        self.access.get_latest_block_number.return_value = latest
        self.access.get_block.side_effect = lambda num, full_transactions: self._make_block_for_num(num)

        self._run(self.logic.fetch_latest_blocks(count=5))

        # Should fetch blocks 1000..1004
        assert self.access.get_block.call_count == 5

    def test_returns_latest_block_number(self):
        self.access.get_latest_block_number.return_value = 2000
        self.access.get_block.side_effect = lambda num, full_transactions: self._make_block_for_num(num)

        result = self._run(self.logic.fetch_latest_blocks(count=3))
        assert result == 2000

    def test_uses_app_config_count_when_none_passed(self):
        self.access.get_latest_block_number.return_value = 104
        self.access.get_block.side_effect = lambda num, full_transactions: self._make_block_for_num(num)

        self._run(self.logic.fetch_latest_blocks())  # count=None → uses blocks_to_fetch=5
        assert self.access.get_block.call_count == 5

    def test_continues_on_block_error(self):
        self.access.get_latest_block_number.return_value = 1002

        def side_effect(num, full_transactions):
            if num == 1001:
                raise ConnectionError("timeout")
            return self._make_block_for_num(num)

        self.access.get_block.side_effect = side_effect
        # Should not raise; error logged and loop continues
        self._run(self.logic.fetch_latest_blocks(count=3))
        self.reporter.logger.warning.assert_called()

    def test_tx_detail_fetched_for_all_blocks(self):
        latest = 1019  # 20 blocks: 1000..1019
        self.access.get_latest_block_number.return_value = latest
        self.access.get_block.side_effect = lambda num, full_transactions: make_block(
            number=num, tx_hashes=[make_tx_details()], timestamp=num
        )
        receipt = make_tx_receipt()
        self.access.get_transaction_receipt.return_value = receipt
        self.logic.process_transaction_data = MagicMock(return_value=None)

        self._run(self.logic.fetch_latest_blocks(count=20))

        # get_transaction_receipt should  be called for blocks all blocks 1000-1019 (20 blocks)
        assert self.access.get_transaction_receipt.call_count == 20
