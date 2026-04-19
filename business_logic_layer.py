import asyncio

from access_layer import BlockchainAccess
from config import AppConfig


class BlockchainLogic:
    def __init__(self, access: BlockchainAccess, reporter, app_config: AppConfig):
        self.access = access
        self.reporter = reporter
        self.app = app_config

    # -------------------------
    # Data processing
    # -------------------------

    def process_block_data(self, block) -> dict:
        return {
            "number": block["number"],
            "transactions_count": len(block["transactions"]),
            "hash": block["hash"].hex(),
        }

    def process_transaction_data(self, tx_details, tx_receipt) -> dict:
        eth_amount = self.access.from_wei(tx_details["value"], "ether")
        gas_used = tx_receipt["gasUsed"]
        gas_price = tx_details["gasPrice"]

        total_cost_wei = gas_used * gas_price
        total_cost_eth = self.access.from_wei(total_cost_wei, "ether")

        return {
            "hash": tx_details["hash"].hex(),
            "sender": tx_details["from"],
            "receiver": tx_details["to"],
            "amount_eth": eth_amount,
            "gas_used": gas_used,
            "gas_price_wei": gas_price,
            "fee_eth": total_cost_eth,
        }

    # -------------------------
    # Block handling
    # -------------------------

    async def _process_block_with_tx(self, block_num: int, iteration=None, fetch_tx=True) -> None:
        block = self.access.get_block(block_num, full_transactions=True)
        block_data = self.process_block_data(block)
        self.reporter.report_block(block_data, iteration or block_num)

        if fetch_tx:
            if block["transactions"]:
                last_tx = block["transactions"][-1]
                receipt = self.access.get_transaction_receipt(last_tx["hash"])
                tx_data = self.process_transaction_data(last_tx, receipt)
                self.reporter.report_transaction(tx_data, block_data["number"])
            else:
                self.reporter.report_no_transactions()

    # -------------------------
    # Fetch historical blocks
    # -------------------------

    async def fetch_latest_blocks(self, count: int = None) -> int:
        count = count or self.app.blocks_to_fetch
        latest_number = self.access.get_latest_block_number()
        start_block = max(0, latest_number - count + 1)
        tx_subset_start = latest_number - 9

        self.reporter.logger.info(
            f"Fetching blocks {start_block} – {latest_number} "
            f"({latest_number - start_block + 1} blocks)..."
        )

        for block_num in range(start_block, latest_number + 1):
            iteration = block_num - start_block + 1
            fetch_tx = block_num >= tx_subset_start
            try:
                await self._process_block_with_tx(block_num, iteration, fetch_tx)
                await asyncio.sleep(0.1)
            except Exception as exc:
                self.reporter.logger.warning(
                    f"Error processing block {block_num}: {exc}"
                )

        return latest_number

    # -------------------------
    # WebSocket subscription
    # -------------------------

    async def subscribe_new_heads(self) -> None:
        await self.access.subscribe_new_heads(self._process_block_with_tx)