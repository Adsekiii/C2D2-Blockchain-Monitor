import asyncio
import sys

from access_layer import BlockchainAccess
from business_logic_layer import BlockchainLogic
from config import ConnConfig, AppConfig
from filters import (
    GasPriceFilter, HighValueFilter, HighFeeFilter,
    FailedTransactionFilter, TokenTransferFilter,
    AddressFilter, ContractInteractionFilter,
    WhaleTransactionFilter, FrequentSenderFilter,
)
from reporting_layer import ConsoleReporter
import gui


def main():
    try:
        gui.main()
    except KeyboardInterrupt:
        print("\nStopped by user.")


if __name__ == "__main__":
    main()
