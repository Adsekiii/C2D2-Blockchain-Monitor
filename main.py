import asyncio
import sys

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


async def main() -> None:
    conn_cfg = ConnConfig()
    app_cfg = AppConfig()
    reporter = ConsoleReporter()

    access = BlockchainAccess(conn_cfg, app_cfg)
    reporter.report_connection_status(access.is_connected())

    if not access.is_connected():
        reporter.logger.error("Cannot connect to the network. Check your API key and URL.")
        sys.exit(1)

    logic = BlockchainLogic(
        access,
        reporter,
        app_cfg,
        filters=[
            GasPriceFilter(0.03),
        ],
    )

    last_block = await logic.fetch_latest_blocks()

    try:
        await logic.subscribe_new_heads()
    except KeyboardInterrupt:
        pass
    finally:
        reporter.print_final_summary()


if __name__ == "__main__":
    try:
        gui.main()
    except KeyboardInterrupt:
        print("\nStopped by user.")


if __name__ == "__main__":
    main()
