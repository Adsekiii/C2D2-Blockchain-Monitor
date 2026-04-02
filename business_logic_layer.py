class BlockchainLogic:
    def __init__(self, w3_instance):
        self.w3 = w3_instance

    def process_block_data(self, block):
        return {
            "number": block['number'],
            "transactions_count": len(block['transactions']),
            "hash": block['hash'].hex()
        }

    def process_transaction_data(self, tx_details, tx_receipt):
        eth_amount = self.w3.from_wei(tx_details['value'], 'ether')
        gas_used = tx_receipt['gasUsed']
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