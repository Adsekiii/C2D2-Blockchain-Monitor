from web3 import AsyncWeb3
from web3.providers import WebSocketProvider
from config import ConnConfig

class BlockchainAccess:
    def __init__(self):
        self.config = ConnConfig()
        self._w3_context = AsyncWeb3(WebSocketProvider(self.config.get_wss_url))
        self.w3 = None

    async def __aenter__(self):
        self.w3 = await self._w3_context.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._w3_context.__aexit__(exc_type, exc_val, exc_tb)

    async def connect(self):
        if self.w3 is not None:
            return await self.w3.is_connected()
        return False

    async def get_latest_block(self):
        return await self.w3.eth.get_block('latest')

    async def get_transaction(self, tx_hash):
        return await self.w3.eth.get_transaction(tx_hash)

    async def get_transaction_receipt(self, tx_hash):
        return await self.w3.eth.get_transaction_receipt(tx_hash)