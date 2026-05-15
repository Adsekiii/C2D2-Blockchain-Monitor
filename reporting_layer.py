import csv
import os
import logging
from datetime import datetime


class ConsoleReporter:
    def __init__(self):
        self.total_blocks_processed = 0
        self.total_txs_processed = 0
        self.total_amount_eth = 0
        self.total_gas_used = 0
        self.total_gas_price_wei = 0
        self.total_fee_eth = 0

        os.makedirs("logs", exist_ok=True)
        os.makedirs("logs/csv", exist_ok=True)

        timestamp = datetime.now().strftime("%d-%m-%Y-%H-%M-%S")
        log_filename = f"logs/{timestamp}.log"
        self.csv_filename = f"logs/csv/{timestamp}.csv"

        self.logger = logging.getLogger(
            f"ConsoleReporter_{timestamp}"
        )

        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        console_formatter = logging.Formatter("%(message)s")

        file_handler = logging.FileHandler(log_filename, encoding="utf-8")
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        with open(self.csv_filename, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([
                "Block_number",
                "TX_hash",
                "Sender",
                "Receiver",
                "ETH_amount",
                "Gas_used",
                "Gas_price",
                "ETH_fee"
            ])

    def report_connection_status(self, is_connected):
        if is_connected:
            self.logger.info("Connected to Sepolia!")
        else:
            self.logger.info("Error occured while connecting to Sepolia...")


    def report_block(self, block_data, iteration):
        self.logger.info("=========================================================")
        self.logger.info(f"Fetching block nr {iteration}:")
        self.logger.info(f"Block number: {block_data['number']}")
        self.logger.info(f"Transactions: {block_data['transactions_count']}")
        self.logger.info(f"Block Hash: {block_data['hash']}")
        self.total_blocks_processed += 1


    def report_transaction(self, tx_data, block_number):
        self.logger.info(f"=====Details of last transaction for block {block_number}=====")
        self.logger.info(f"TX Hash: {tx_data['hash']}")
        self.logger.info(f"Sender: {tx_data['sender']}")
        self.logger.info(f"Receiver: {tx_data['receiver']}")
        self.logger.info(f"Amount: {tx_data['amount_eth']} ETH")
        self.logger.info(f"Gas used: {tx_data['gas_used']}")
        self.logger.info(f"Gas price: {tx_data['gas_price_wei']} Wei")
        self.logger.info(f"Fee: {tx_data['fee_eth']} ETH")
        self.total_txs_processed += 1
        self.total_amount_eth += tx_data['amount_eth']
        self.total_gas_used += tx_data['gas_used']
        self.total_gas_price_wei += tx_data['gas_price_wei']
        self.total_fee_eth += tx_data['fee_eth']

        with open(self.csv_filename, mode="a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([
                block_number,
                tx_data['hash'],
                tx_data['sender'],
                tx_data['receiver'],
                tx_data['amount_eth'],
                tx_data['gas_used'],
                tx_data['gas_price_wei'],
                tx_data['fee_eth']
            ])


    def report_no_transactions(self):
        self.logger.info("This block does not have any transactions registered")


    def print_final_summary(self):
        self.logger.info("\n=== SUMMARY REPORT ===")
        self.logger.info(f"Blocks processed: {self.total_blocks_processed}")
        self.logger.info(f"Transactions processed: {self.total_txs_processed}")
        self.logger.info(f"Total ETH amount: {self.total_amount_eth}")
        self.logger.info(f"Total Gas used: {self.total_gas_used}")
        self.logger.info(f"Total Gas price: {self.total_gas_price_wei}")
        self.logger.info(f"Total ETH fee: {self.total_fee_eth}")