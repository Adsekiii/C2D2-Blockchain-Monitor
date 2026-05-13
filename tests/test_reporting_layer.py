import csv
import logging
from pathlib import Path

import pytest

from reporting_layer import ConsoleReporter


@pytest.fixture
def reporter(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return ConsoleReporter()


def test_reporter_initialization_creates_directories_and_csv(reporter):
    logs_dir = Path("logs")
    csv_dir = Path("logs/csv")

    assert logs_dir.exists()
    assert csv_dir.exists()

    csv_file = Path(reporter.csv_filename)
    assert csv_file.exists()

    with open(csv_file, encoding="utf-8") as file:
        reader = csv.reader(file)
        header = next(reader)

    assert header == [
        "Block_number",
        "TX_hash",
        "Sender",
        "Receiver",
        "ETH_amount",
        "Gas_used",
        "Gas_price",
        "ETH_fee"
    ]


def test_report_connection_status_success(reporter, caplog):
    with caplog.at_level(logging.INFO):
        reporter.report_connection_status(True)

    assert "Connected to Sepolia!" in caplog.text


def test_report_connection_status_failure(reporter, caplog):
    with caplog.at_level(logging.INFO):
        reporter.report_connection_status(False)

    assert "Error occured while connecting to Sepolia..." in caplog.text


def test_report_block_updates_counter(reporter, caplog):
    block_data = {
        "number": 123,
        "transactions_count": 5,
        "hash": "0xabc"
    }

    with caplog.at_level(logging.INFO):
        reporter.report_block(block_data, 1)

    assert reporter.total_blocks_processed == 1
    assert "Block number: 123" in caplog.text
    assert "Transactions: 5" in caplog.text
    assert "Block Hash: 0xabc" in caplog.text


def test_report_transaction_updates_totals_and_csv(reporter, caplog):
    tx_data = {
        "hash": "0xtx",
        "sender": "0xsender",
        "receiver": "0xreceiver",
        "amount_eth": 1.5,
        "gas_used": 21000,
        "gas_price_wei": 1000000000,
        "fee_eth": 0.0021
    }

    with caplog.at_level(logging.INFO):
        reporter.report_transaction(tx_data, 123)

    assert reporter.total_txs_processed == 1
    assert reporter.total_amount_eth == 1.5
    assert reporter.total_gas_used == 21000
    assert reporter.total_gas_price_wei == 1000000000
    assert reporter.total_fee_eth == 0.0021

    assert "TX Hash: 0xtx" in caplog.text
    assert "Sender: 0xsender" in caplog.text

    with open(reporter.csv_filename, encoding="utf-8") as file:
        rows = list(csv.reader(file))

    assert rows[1] == [
        "123",
        "0xtx",
        "0xsender",
        "0xreceiver",
        "1.5",
        "21000",
        "1000000000",
        "0.0021"
    ]


def test_report_no_transactions(reporter, caplog):
    with caplog.at_level(logging.INFO):
        reporter.report_no_transactions()

    assert "This block does not have any transactions registered" in caplog.text


def test_print_final_summary(reporter, caplog):
    reporter.total_blocks_processed = 10
    reporter.total_txs_processed = 50
    reporter.total_amount_eth = 5.5
    reporter.total_gas_used = 100000
    reporter.total_gas_price_wei = 999999
    reporter.total_fee_eth = 0.1

    with caplog.at_level(logging.INFO):
        reporter.print_final_summary()

    assert "Blocks processed: 10" in caplog.text
    assert "Transactions processed: 50" in caplog.text
    assert "Total ETH amount: 5.5" in caplog.text
    assert "Total Gas used: 100000" in caplog.text
    assert "Total Gas price: 999999" in caplog.text
    assert "Total ETH fee: 0.1" in caplog.text