class ConsoleReporter:
    def __init__(self):
        self.total_blocks_processed = 0
        self.total_txs_processed = 0

    def report_connection_status(self, is_connected):
        if is_connected:
            print("Podłączono pod Sepolia!")
        else:
            print("No can do")

    def report_block(self, block_data, iteration):
        print("=========================================================")
        print(f"Fetching block nr {iteration}:")
        print(f"Block number: {block_data['number']}")
        print(f"Transactions: {block_data['transactions_count']}")
        print(f"Block Hash: {block_data['hash']}")
        self.total_blocks_processed += 1

    def report_transaction(self, tx_data, block_number):
        print(f"=====Szczegóły ostatniej transakcji dla bloku {block_number}=====")
        print(f"TX Hash: {tx_data['hash']}")
        print(f"Sender: {tx_data['sender']}")
        print(f"Receiver: {tx_data['receiver']}")
        print(f"Amount: {tx_data['amount_eth']} ETH")
        print(f"Gas used: {tx_data['gas_used']}")
        print(f"Gas price: {tx_data['gas_price_wei']} Wei")
        print(f"Fee: {tx_data['fee_eth']} ETH")
        self.total_txs_processed += 1

    def report_no_transactions(self):
        print("This block does not have any transactions registered")

    def print_final_summary(self):
        print("\n=== RAPORT KOŃCOWY ===")
        print(f"Przetworzono bloków: {self.total_blocks_processed}")
        print(f"Przetworzono transakcji: {self.total_txs_processed}")