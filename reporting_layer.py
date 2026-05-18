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
        self._start_time = datetime.now()

        os.makedirs("logs", exist_ok=True)
        os.makedirs("logs/csv", exist_ok=True)

        timestamp = datetime.now().strftime("%d-%m-%Y-%H-%M-%S")
        log_filename = f"logs/{timestamp}.log"
        self.csv_filename = f"logs/csv/{timestamp}.csv"
        self.txt_filename = f"logs/{timestamp}_summary.txt"

        # Unique logger name prevents handler duplication across multiple instances
        self.logger = logging.getLogger(f"ConsoleReporter_{timestamp}")
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
                "ETH_fee",
            ])

    def report_connection_status(self, is_connected: bool) -> None:
        if is_connected:
            self.logger.info("Connected to Sepolia!")
        else:
            self.logger.info("Error occured while connecting to Sepolia...")

    def report_block(self, block_data: dict, iteration) -> None:
        self.logger.info("=========================================================")
        self.logger.info(f"Fetching block nr {iteration}:")
        self.logger.info(f"Block number: {block_data['number']}")
        self.logger.info(f"Transactions: {block_data['transactions_count']}")
        self.logger.info(f"Block Hash: {block_data['hash']}")
        self.total_blocks_processed += 1

    def report_transaction(self, tx_data: dict, block_number: int) -> None:
        self.logger.info(f"=====Details of last transaction for block {block_number}=====")
        self.logger.info(f"TX Hash: {tx_data['hash']}")
        self.logger.info(f"Sender: {tx_data['sender']}")
        self.logger.info(f"Receiver: {tx_data['receiver']}")
        self.logger.info(f"Amount: {tx_data['amount_eth']} ETH")
        self.logger.info(f"Gas used: {tx_data['gas_used']}")
        self.logger.info(f"Gas price: {tx_data['gas_price_wei']} Wei")
        self.logger.info(f"Fee: {tx_data['fee_eth']} ETH")
        self.total_txs_processed += 1
        self.total_amount_eth += tx_data["amount_eth"]
        self.total_gas_used += tx_data["gas_used"]
        self.total_gas_price_wei += tx_data["gas_price_wei"]
        self.total_fee_eth += tx_data["fee_eth"]

        with open(self.csv_filename, mode="a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([
                block_number,
                tx_data["hash"],
                tx_data["sender"],
                tx_data["receiver"],
                tx_data["amount_eth"],
                tx_data["gas_used"],
                tx_data["gas_price_wei"],
                tx_data["fee_eth"],
            ])

    def report_no_transactions(self) -> None:
        self.logger.info("This block does not have any transactions registered")

    def report_filtered_transaction(self) -> None:
        self.logger.info("Transaction filtered out")

    def print_final_summary(self) -> None:
        """
        Logs the summary to console/log file AND writes a human-readable
        .txt summary report as required by the project specification.
        """
        end_time = datetime.now()
        duration = end_time - self._start_time
        avg_gas = (
            round(self.total_gas_used / self.total_blocks_processed, 2)
            if self.total_blocks_processed > 0
            else 0
        )

        lines = [
            "=" * 57,
            "           SEPOLIA BLOCKCHAIN MONITOR – SUMMARY REPORT",
            "=" * 57,
            f"  Session start  : {self._start_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"  Session end    : {end_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"  Duration       : {str(duration).split('.')[0]}",
            "-" * 57,
            f"  Blocks processed       : {self.total_blocks_processed}",
            f"  Transactions processed : {self.total_txs_processed}",
            f"  Total ETH transferred  : {self.total_amount_eth} ETH",
            f"  Total gas used         : {self.total_gas_used}",
            f"  Average gas / block    : {avg_gas}",
            f"  Total gas price sum    : {self.total_gas_price_wei} Wei",
            f"  Total fees paid        : {self.total_fee_eth} ETH",
            "-" * 57,
            f"  CSV log  : {self.csv_filename}",
            f"  Full log : {self.csv_filename.replace('/csv/', '/').replace('.csv', '.log')}",
            "=" * 57,
        ]

        summary_text = "\n".join(lines)

        # 1. Console + log file output
        for line in lines:
            self.logger.info(line)

        # 2. Standalone .txt summary report (project requirement)
        try:
            with open(self.txt_filename, mode="w", encoding="utf-8") as f:
                f.write(summary_text + "\n")
            self.logger.info(f"Summary saved to: {self.txt_filename}")
        except OSError as exc:
            self.logger.warning(f"Could not write summary file: {exc}")
