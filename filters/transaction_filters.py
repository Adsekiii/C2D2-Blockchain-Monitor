from abc import ABC, abstractmethod

class TransactionFilter(ABC):
    @abstractmethod
    def apply(self, tx_details, tx_receipt, w3) -> bool:
        pass

class HighValueFilter(TransactionFilter):
    def __init__(self, min_eth: float):
        self.min_eth = min_eth

    def apply(self, tx_details, tx_receipt, w3) -> bool:
        value_eth = w3.from_wei(tx_details['value'], 'ether')
        return value_eth >= self.min_eth


class HighFeeFilter(TransactionFilter):
    def __init__(self, min_fee_eth: float):
        self.min_fee_eth = min_fee_eth

    def apply(self, tx_details, tx_receipt, w3) -> bool:
        gas_used = tx_receipt['gasUsed']
        gas_price = tx_details['gasPrice']
        fee_eth = w3.from_wei(gas_used * gas_price, 'ether')
        return fee_eth >= self.min_fee_eth


class AddressFilter(TransactionFilter):
    def __init__(self, address: str):
        self.address = address.lower()

    def apply(self, tx_details, tx_receipt, w3) -> bool:
        sender = tx_details['from'].lower()
        receiver = tx_details['to'].lower() if tx_details['to'] else None

        return sender == self.address or receiver == self.address

class ContractInteractionFilter(TransactionFilter):
    def __init__(self, only_contracts: bool = True):
        self.only_contracts = only_contracts

    def apply(self, tx_details, tx_receipt, w3) -> bool:
        is_contract = tx_details['to'] is None
        return is_contract if self.only_contracts else not is_contract
    
class WhaleTransactionFilter(TransactionFilter):
    def __init__(self, min_eth: float = 10):
        self.min_eth = min_eth

    def apply(self, tx_details, tx_receipt, w3) -> bool:
        value_eth = w3.from_wei(tx_details['value'], 'ether')
        return value_eth >= self.min_eth    
    
class GasPriceFilter(TransactionFilter):
    def __init__(self, min_gwei: int):
        self.min_gwei = min_gwei

    def apply(self, tx_details, tx_receipt, w3) -> bool:
        gas_price_wei = tx_details['gasPrice']
        gas_price_gwei = w3.from_wei(gas_price_wei, 'gwei')
        return gas_price_gwei >= self.min_gwei
    
class FailedTransactionFilter(TransactionFilter):
    def __init__(self, only_failed: bool = True):
        self.only_failed = only_failed

    def apply(self, tx_details, tx_receipt, w3) -> bool:
        status = tx_receipt['status']  # 1 = success, 0 = fail
        is_failed = status == 0
        return is_failed if self.only_failed else not is_failed
    
class FrequentSenderFilter(TransactionFilter):
    def __init__(self, threshold: int = 3):
        self.threshold = threshold
        self.counter = {}

    def apply(self, tx_details, tx_receipt, w3) -> bool:
        sender = tx_details['from'].lower()
        self.counter[sender] = self.counter.get(sender, 0) + 1
        return self.counter[sender] >= self.threshold
    
class TokenTransferFilter(TransactionFilter):
    def apply(self, tx_details, tx_receipt, w3) -> bool:
        # ERC20 transfer = dane w input (nie pusty)
        return tx_details['input'] != '0x'