import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv(dotenv_path=".secret")


@dataclass
class ConnConfig:
    https_url: str = "https://eth-sepolia.g.alchemy.com/v2/"
    wss_url: str = "wss://eth-sepolia.g.alchemy.com/v2/"
    api_key: str = os.getenv("ALCHEMY_KEY")

    @property
    def get_https_url(self) -> str:
        return f"{self.https_url}{self.api_key}"

    @property
    def get_wss_url(self) -> str:
        return f"{self.wss_url}{self.api_key}"


@dataclass
class AppConfig:
    # MVP requirement: monitor at least 100 of the latest blocks
    blocks_to_fetch: int = 100
    # Seconds to wait before WebSocket reconnect attempt
    reconnect_delay: int = 5
    # Delay between consecutive HTTP requests (rate-limit protection)
    request_delay: float = 0.1
