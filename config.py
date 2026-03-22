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