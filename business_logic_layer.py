from decimal import Decimal

class BlockchainLogic:
    def __init__(self, w3_instance, filters=None):
        self.w3 = w3_instance
        self.filters = filters or []
        
        self.stats = {
            "total_blocks": 0,
            "total_transactions": 0,
            "total_gas_used": 0,
            "total_eth_value": Decimal('0'),
            "total_fees_eth": Decimal('0'),
            "filtered_transactions": 0,
            "block_timestamps": [],
            "unique_senders": set(),
            "unique_receivers": set()
        }

    def passes_filters(self, tx_details, tx_receipt):
        return all(
            f.apply(tx_details, tx_receipt, self.w3)
            for f in self.filters
        )

    def process_block_data(self, block):
        tx_count = len(block['transactions'])
        self.stats["total_blocks"] += 1
        self.stats["total_transactions"] += tx_count
        
        if 'timestamp' in block:
            self.stats["block_timestamps"].append(block['timestamp'])
            self.stats["block_timestamps"].sort()
        
        return {
            "number": block['number'],
            "transactions_count": tx_count,
            "hash": block['hash'].hex() if isinstance(block['hash'], bytes) else block['hash']
        }

    def process_transaction_data(self, tx_details, tx_receipt):
        gas_used = tx_receipt['gasUsed']
        eth_amount = self.w3.from_wei(tx_details['value'], 'ether')
        
        self.stats["total_gas_used"] += gas_used
        self.stats["total_eth_value"] += Decimal(str(eth_amount))

        # Statystyki unikalnych adresów
        if tx_details.get('from'):
            self.stats["unique_senders"].add(tx_details['from'])
        if tx_details.get('to'):
            self.stats["unique_receivers"].add(tx_details['to'])

        gas_price = tx_details['gasPrice']
        total_cost_wei = gas_used * gas_price
        total_cost_eth = self.w3.from_wei(total_cost_wei, 'ether')
        self.stats["total_fees_eth"] += Decimal(str(total_cost_eth))

        if not self.passes_filters(tx_details, tx_receipt):
            self.stats["filtered_transactions"] += 1
            return None

        return {
            "hash": tx_details['hash'].hex() if isinstance(tx_details['hash'], bytes) else tx_details['hash'],
            "sender": tx_details['from'],
            "receiver": tx_details['to'],
            "amount_eth": eth_amount,
            "gas_used": gas_used,
            "gas_price_wei": gas_price,
            "fee_eth": total_cost_eth
        }

    def increment_filtered_counter(self):
        self.stats["filtered_transactions"] += 1

    def get_live_analytics(self):
        """Generuje zaawansowane, zagregowane dane dla nowej zakładki GUI."""
        blocks = self.stats["total_blocks"]
        txs = self.stats["total_transactions"]
        
        avg_block_time = 0.0
        timestamps = self.stats["block_timestamps"]
        if len(timestamps) > 1:
            diffs = [timestamps[i] - timestamps[i-1] for i in range(1, len(timestamps))]
            avg_block_time = sum(diffs) / len(diffs)

        avg_fee = 0.0
        if txs > 0:
            avg_fee = float(self.stats["total_fees_eth"]) / txs
        avg_eth = 0.0

        if txs > 0:
            avg_eth = float(self.stats["total_eth_value"]) / txs

        avg_tx_per_block = txs / blocks if blocks > 0 else 0

        avg_gas_per_block = self.stats["total_gas_used"] / blocks if blocks > 0 else 0

        return {
            "avg_block_time": f"{avg_block_time:.2f} s",
            "avg_fee_tx": f"{avg_fee:.9f} ETH",
            "avg_eth_tx": f"{avg_eth:.9f} ETH",
            "avg_tx_per_block": f"{avg_tx_per_block:.1f}",
            "avg_gas_per_block": f"{avg_gas_per_block:,.0f}",
            "unique_senders": str(len(self.stats["unique_senders"])),
            "unique_receivers": str(len(self.stats["unique_receivers"])),
            "total_fees_pool": f"{float(self.stats['total_fees_eth']):.5f} ETH"
        }

    def get_aggregated_stats(self):
        """Zwraca słownik końcowy po zakończeniu monitorowania."""
        avg_gas = 0
        if self.stats["total_blocks"] > 0:
            avg_gas = self.stats["total_gas_used"] / self.stats["total_blocks"]

        return {
            "summary_blocks_processed": self.stats["total_blocks"],
            "summary_transactions_monitored": self.stats["total_transactions"],
            "average_gas_per_block": round(avg_gas, 2),
            "total_value_transferred_eth": round(self.stats["total_eth_value"], 6)
        }