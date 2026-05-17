import asyncio
from decimal import Decimal

from access_layer import BlockchainAccess
from config import AppConfig


class BlockchainLogic:
    def __init__(self, access: BlockchainAccess, reporter, app_config: AppConfig, filters=None):
        self.access = access
        self.reporter = reporter
        self.app = app_config
        self.filters = filters or []

        self.stats = {
            "total_blocks": 0,
            "total_transactions": 0,
            "total_gas_used": 0,
            "total_eth_value": Decimal("0"),
            "total_fees_eth": Decimal("0"),
            "filtered_transactions": 0,
            "block_timestamps": [],
            "unique_senders": set(),
            "unique_receivers": set(),
        }

    # -------------------------
    # Filtering
    # -------------------------

    def passes_filters(self, tx_details, tx_receipt) -> bool:
        return all(
            f.apply(tx_details, tx_receipt, self.access)
            for f in self.filters
        )

    # -------------------------
    # Data processing
    # -------------------------

    def process_block_data(self, block) -> dict:
        tx_count = len(block["transactions"])
        self.stats["total_blocks"] += 1
        self.stats["total_transactions"] += tx_count

        if "timestamp" in block:
            self.stats["block_timestamps"].append(block["timestamp"])
            self.stats["block_timestamps"].sort()

        return {
            "number": block["number"],
            "transactions_count": tx_count,
            "hash": block["hash"].hex()
            if isinstance(block["hash"], bytes)
            else block["hash"],
        }

    def process_transaction_data(self, tx_details, tx_receipt) -> dict | None:
        
        if not self.passes_filters(tx_details, tx_receipt):
            self.stats["filtered_transactions"] += 1
            return None

        gas_used = tx_receipt["gasUsed"]
        eth_amount = self.access.from_wei(tx_details["value"], "ether")
        gas_price = tx_details["gasPrice"]
        total_cost_wei = gas_used * gas_price
        total_cost_eth = self.access.from_wei(total_cost_wei, "ether")

        self.stats["total_gas_used"] += gas_used
        self.stats["total_eth_value"] += Decimal(str(eth_amount))
        self.stats["total_fees_eth"] += Decimal(str(total_cost_eth))

        if tx_details.get("from"):
            self.stats["unique_senders"].add(tx_details["from"])
        if tx_details.get("to"):
            self.stats["unique_receivers"].add(tx_details["to"])


        return {
            "hash": tx_details["hash"].hex()
            if isinstance(tx_details["hash"], bytes)
            else tx_details["hash"],
            "sender": tx_details["from"],
            "receiver": tx_details["to"],
            "amount_eth": eth_amount,
            "gas_used": gas_used,
            "gas_price_wei": gas_price,
            "fee_eth": total_cost_eth,
        }

    # -------------------------
    # Aggregated stats
    # -------------------------

    def get_aggregated_stats(self) -> dict:
        avg_gas = 0
        if self.stats["total_blocks"] > 0:
            avg_gas = self.stats["total_gas_used"] / self.stats["total_blocks"]

        return {
            "summary_blocks_processed": self.stats["total_blocks"],
            "summary_transactions_monitored": self.stats["total_transactions"],
            "average_gas_per_block": round(avg_gas, 2),
            "total_value_transferred_eth": round(self.stats["total_eth_value"], 6),
        }

    def get_live_analytics(self) -> dict:
        blocks = self.stats["total_blocks"]
        txs = self.stats["total_transactions"]

        avg_block_time = 0.0
        timestamps = self.stats["block_timestamps"]
        if len(timestamps) > 1:
            diffs = [
                timestamps[i] - timestamps[i - 1]
                for i in range(1, len(timestamps))
            ]
            avg_block_time = sum(diffs) / len(diffs)

        avg_fee = float(self.stats["total_fees_eth"]) / txs if txs > 0 else 0.0
        avg_eth = float(self.stats["total_eth_value"]) / txs if txs > 0 else 0.0
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
            "total_fees_pool": f"{float(self.stats['total_fees_eth']):.5f} ETH",
        }

    # -------------------------
    # Block handling (internal)
    # -------------------------

    async def _process_block_with_tx(self, block_num: int, iteration=None, fetch_tx: bool = True) -> None:
        """
        Fetches a single block via HTTP, processes it, and (optionally)
        processes the last transaction. Emits data through the reporter.
        """
        block = self.access.get_block(block_num, full_transactions=True)
        block_data = self.process_block_data(block)
        self.reporter.report_block(block_data, iteration if iteration is not None else block_num)

        if fetch_tx:
            if block["transactions"]:
                last_tx = block["transactions"][-1]
                receipt = self.access.get_transaction_receipt(last_tx["hash"])
                tx_data = self.process_transaction_data(last_tx, receipt)
                if tx_data:
                    self.reporter.report_transaction(tx_data, block_data["number"])
                else:
                    self.reporter.report_filtered_transaction()
            else:
                self.reporter.report_no_transactions()

    # -------------------------
    # Fetch historical blocks (MVP: >= 100 blocks)
    # -------------------------

    async def fetch_latest_blocks(self, count: int = None) -> int:
        """
        Fetches `count` of the most recent blocks via HTTP (MVP default: 100).
        Detailed TX data is fetched for the last 10 blocks in the range.
        Includes rate-limit-friendly delays between HTTP requests.
        """
        count = count or self.app.blocks_to_fetch
        latest_number = self.access.get_latest_block_number()
        start_block = max(0, latest_number - count + 1)
        tx_subset_start = start_block

        self.reporter.logger.info(
            f"Fetching blocks {start_block} – {latest_number} "
            f"({latest_number - start_block + 1} blocks)..."
        )

        for block_num in range(start_block, latest_number + 1):
            iteration = block_num - start_block + 1
            fetch_tx = block_num >= tx_subset_start
            try:
                await self._process_block_with_tx(block_num, iteration, fetch_tx)
                # Rate-limit protection: small delay between HTTP requests
                await asyncio.sleep(self.app.request_delay)
            except Exception as exc:
                self.reporter.logger.warning(
                    f"Error processing block {block_num}: {exc}"
                )

        return latest_number

    # -------------------------
    # WebSocket subscription
    # -------------------------

    async def subscribe_new_heads(self) -> None:
        """Delegates to access layer's WSS subscription, processing each new block."""
        await self.access.subscribe_new_heads(self._process_block_with_tx)
