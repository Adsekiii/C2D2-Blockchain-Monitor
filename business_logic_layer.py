from decimal import Decimal

class BlockchainLogic:
    def __init__(self, w3_instance, filters=None):
        self.w3 = w3_instance
        self.filters = filters or []
        
        self.stats = {
            "total_blocks": 0,
            "total_transactions": 0,
            "total_gas_used": 0,
            "total_eth_value": Decimal('0')
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
        
        return {
            "number": block['number'],
            "transactions_count": tx_count,
            "hash": block['hash'].hex()
        }

    def process_transaction_data(self, tx_details, tx_receipt):
        gas_used = tx_receipt['gasUsed']
        eth_amount = self.w3.from_wei(tx_details['value'], 'ether')
        
        self.stats["total_gas_used"] += gas_used
        self.stats["total_eth_value"] += Decimal(str(eth_amount))

        if not self.passes_filters(tx_details, tx_receipt):
            return None

        gas_price = tx_details['gasPrice']
        total_cost_wei = gas_used * gas_price
        total_cost_eth = self.w3.from_wei(total_cost_wei, 'ether')

        return {
            "hash": tx_details['hash'].hex(),
            "sender": tx_details['from'],
            "receiver": tx_details['to'],
            "amount_eth": eth_amount,
            "gas_used": gas_used,
            "gas_price_wei": gas_price,
            "fee_eth": total_cost_eth
        }

    def get_aggregated_stats(self):
        """Zwraca słownik z obliczonymi średnimi i sumami."""
        avg_gas = 0
        if self.stats["total_blocks"] > 0:
            avg_gas = self.stats["total_gas_used"] / self.stats["total_blocks"]

        return {
            "summary_blocks_processed": self.stats["total_blocks"],
            "summary_transactions_monitored": self.stats["total_transactions"],
            "average_gas_per_block": round(avg_gas, 2),
            "total_value_transferred_eth": round(self.stats["total_eth_value"], 6)
        }