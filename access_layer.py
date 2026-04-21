import asyncio
import json
import logging

import websockets
from web3 import Web3

from config import ConnConfig, AppConfig


class BlockchainAccess:
    def __init__(self, conn_config: ConnConfig, app_config: AppConfig):
        self.conn = conn_config
        self.app = app_config
        self.logger = logging.getLogger("ConsoleReporter")
        self._w3 = Web3(Web3.HTTPProvider(self.conn.get_https_url))

    # -------------------------
    # HTTP
    # -------------------------

    def is_connected(self) -> bool:
        return self._w3.is_connected()

    def get_latest_block_number(self) -> int:
        return self._w3.eth.block_number

    def get_block(self, block_num: int, full_transactions: bool = True):
        return self._w3.eth.get_block(block_num, full_transactions)

    def get_transaction_receipt(self, tx_hash):
        return self._w3.eth.get_transaction_receipt(tx_hash)

    def from_wei(self, value: int, unit: str):
        return self._w3.from_wei(value, unit)

    # -------------------------
    # WebSocket
    # -------------------------

    async def subscribe_new_heads(self, callback) -> None:
        last_processed = None

        while True:
            try:
                self.logger.info(f"Connecting to WebSocket: {self.conn.wss_url[:40]}...")

                async with websockets.connect(
                    self.conn.get_wss_url, ping_interval=20
                ) as ws:

                    await ws.send(json.dumps({
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "eth_subscribe",
                        "params": ["newHeads"],
                    }))

                    ack = json.loads(await ws.recv())
                    sub_id = ack.get("result", "unknown")
                    self.logger.info(
                        f"Subscription active (id={sub_id}). "
                        f"Waiting for new blocks..."
                    )

                    async for raw_msg in ws:
                        try:
                            msg = json.loads(raw_msg)

                            if msg.get("method") != "eth_subscription":
                                continue

                            new_number = int(
                                msg["params"]["result"]["number"], 16
                            )

                            if last_processed is None:
                                last_processed = new_number - 1

                            if new_number <= last_processed:
                                continue

                            for block_num in range(
                                last_processed + 1, new_number + 1
                            ):
                                await callback(block_num)

                            last_processed = new_number

                        except Exception as exc:
                            self.logger.warning(
                                f"Error handling WS message: {exc}"
                            )

            except websockets.exceptions.ConnectionClosed as exc:
                self.logger.warning(
                    f"WebSocket connection closed ({exc}). "
                    f"Retrying in {self.app.reconnect_delay}s..."
                )
            except OSError as exc:
                self.logger.warning(
                    f"WebSocket network error ({exc}). "
                    f"Retrying in {self.app.reconnect_delay}s..."
                )

            await asyncio.sleep(self.app.reconnect_delay)