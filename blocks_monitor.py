import os
from web3 import AsyncWeb3
from web3.providers import WebSocketProvider
from config import ConnConfig

async def monitor_blocks():
    config = ConnConfig()
    try:
        async with AsyncWeb3(WebSocketProvider(config.get_wss_url)) as async_w3:
            if await async_w3.is_connected():
                print("Podłączono pod Sepolia!")
                
                for i in range(0,10):
                    print("=========================================================")
                    print(f"Fetching block nr {i+1}:")
                    latest_block = await raport_latest_block(async_w3)
                    latest_tx_details, latest_tx_receipt_details = await raport_transaction_data(latest_block, async_w3)


            else:
                print("No can do")
    except Exception as e:
        print(f"Critical Error: {e}")


async def raport_latest_block(async_w3):
    latest_block = await async_w3.eth.get_block('latest')
    print(f"Block number: {latest_block['number']}")
    print(f"Transactions: {len(latest_block['transactions'])}")
    print(f"Block Hash: {latest_block['hash'].hex()}")
    return latest_block

async def raport_transaction_data(block, async_w3):
    transactions = block['transactions']

    if len(transactions) > 0:
        latest_tx_hash = transactions[-1]
        tx_details = await async_w3.eth.get_transaction(latest_tx_hash)
        tx_receipt_details = await async_w3.eth.get_transaction_receipt(latest_tx_hash)

        print(f"=====Szczegóły ostatniej transakcji dla bloku {block['number']}=====")
        print(f"TX Hash: {tx_details['hash'].hex()}")
        print(f"Sender: {tx_details['from']}")
        print(f"Receiver: {tx_details['to']}")

        eth_amount = async_w3.from_wei(tx_details['value'], 'ether')
        print(f"Amount: {eth_amount}ETH")

        gas_used = tx_receipt_details['gasUsed']
        print(f"Gas used: {gas_used}")

        gas_price = tx_details['gasPrice']
        print(f"Gas price: {gas_price} Wei")
        
        total_cost_wei = gas_used  * gas_used
        total_cost_eth = async_w3.from_wei(total_cost_wei, 'ether')
        print(f"Fee: {total_cost_eth}ETH")
        return tx_details, tx_receipt_details
    else:
        print("This block does not have any transactions registered")