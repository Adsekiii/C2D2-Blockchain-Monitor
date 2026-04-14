import asyncio
from access_layer import BlockchainAccess
from business_logic_layer import BlockchainLogic
from filters import HighValueFilter, HighFeeFilter, GasPriceFilter, FailedTransactionFilter, TokenTransferFilter, AddressFilter, ContractInteractionFilter, WhaleTransactionFilter, FrequentSenderFilter
from reporting_layer import ConsoleReporter

async def monitor_blocks():

    latest_block = 0

    async with BlockchainAccess() as access:
        logic = BlockchainLogic(
            access.w3,
            filters=[
                HighValueFilter(0.005),
                GasPriceFilter(0.3),
                FailedTransactionFilter(False)
            ]
        )
        reporter = ConsoleReporter()

        is_connected = await access.connect()
        reporter.report_connection_status(is_connected)

        if not is_connected:
            return

        try:
            for i in range(1, 11):
                raw_block = await access.get_latest_block()
                while raw_block['number'] == latest_block:
                    raw_block = await access.get_latest_block()
                latest_block = raw_block['number']
                processed_block = logic.process_block_data(raw_block)
                reporter.report_block(processed_block, i)

                if processed_block['transactions_count'] > 0:
                    latest_tx_hash = raw_block['transactions'][-1]
                    
                    raw_tx = await access.get_transaction(latest_tx_hash)
                    raw_receipt = await access.get_transaction_receipt(latest_tx_hash)
                    
                    processed_tx = logic.process_transaction_data(raw_tx, raw_receipt)

                    if processed_tx:
                        reporter.report_transaction(processed_tx, processed_block['number'])
                    else:
                        print("odfiltrowane")
                else:
                    reporter.report_no_transactions()
                    
                await asyncio.sleep(2)

        except Exception as e:
            print(f"Critical Error: {e}")
        finally:
            reporter.print_final_summary()


def main():
    try:
        asyncio.run(monitor_blocks())
    except KeyboardInterrupt:
        print("\nUżytkownik wstrzymał działanie")

if __name__ == "__main__":
    main()