"""
API for Uniswap distributed exchange (uniswap.exchange)
Price info is pulled from the smart contract

https://docs.uniswap.io/api/exchange
"""
import logging
from web3 import Web3
import time

from .base_exchange import BaseExchangeAPI
from .uniswap_abi import exchange_abi
from configuration import ETHEREUM_NODE_URL
from constants import SECONDS_PER_ETH_BLOCK


def wei_to_ether(amount_in_wei):
    return int(amount_in_wei) / 1000000000000000000.0

def ether_to_wei(amount_in_ether):
    return int(amount_in_ether * 1000000000000000000.0)

class UniswapAPI(BaseExchangeAPI):
    def __init__(self, currency_symbol):
        super().__init__()
        if currency_symbol == "0xBTC":
            self.uniswap_exchange_address = "0x701564Aa6E26816147D4fa211a0779F1B774Bb9B"
            self._decimals = 8
        elif currency_symbol == "XXX":
            self.uniswap_exchange_address = "0x0000000000000000000000000000000000000000"
            self._decimals = 0
        else:
            raise RuntimeError("Unknown currency_symbol {}, need to add address to uniswap.py".format(currency_symbol))

        self.currency_symbol = currency_symbol
        self.exchange_name = "Uniswap"
        self.command_names = ["uniswap"]
        #self.short_url = "https://bit.ly/2PnLAre"  # main uniswap interface
        #self.short_url = "http://0xbitcoin.trade"  # 0xbtc version of the ui
        self.short_url = "https://bit.ly/35nae4n"  # main uniswap pre-selected to 0xbtc

        self._time_volume_last_updated = 0

        self._w3 = Web3(Web3.HTTPProvider(ETHEREUM_NODE_URL))
        self._exchange = self._w3.eth.contract(address=self.uniswap_exchange_address, abi=exchange_abi)

    async def _update_24h_volume(self, timeout=10.0):
        token_purchase_topic = "0xcd60aa75dea3072fbc07ae6d7d856b5dc5f4eee88854f5b4abf7b680ef8bc50f"
        eth_purchase_topic = "0x7f4091b46c33e918a0f3aa42307641d17bb67029427a5369e54b353984238705"
        transfer_topic = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
        remove_liquidity_topic = "0x0fbf06c058b90cb038a618f8c2acbf6145f8b3570fd1fa56abb8f0f3f05b36e8"
        add_liquidity_topic = "0x06239653922ac7bea6aa2b19dc486b9361821d37712eb796adfd38d81de278ca"
        current_eth_block = self._w3.eth.blockNumber
        self.volume_eth = 0
        for event in self._w3.eth.getLogs({
                'fromBlock': current_eth_block - (int(60*60*24 / SECONDS_PER_ETH_BLOCK)),
                'toBlock': current_eth_block - 1,
                'address': self.uniswap_exchange_address}):
            topic0 = self._w3.toHex(event['topics'][0])
            if topic0 == token_purchase_topic:
                address = self._w3.toChecksumAddress(event['topics'][1][-20:])
                eth_amount = wei_to_ether(self._w3.toInt(event['topics'][2]))
                token_amount = self._w3.toInt(event['topics'][3]) / 10**self._decimals
                self.volume_eth += eth_amount
            elif topic0 == eth_purchase_topic:
                address = self._w3.toChecksumAddress(event['topics'][1][-20:])
                token_amount = self._w3.toInt(event['topics'][2]) / 10**self._decimals
                eth_amount = wei_to_ether(self._w3.toInt(event['topics'][3]))
                self.volume_eth += eth_amount
            elif topic0 == transfer_topic:
                # skip liquidity deposits/withdrawals
                continue
            elif topic0 == remove_liquidity_topic:
                # skip liquidity deposits/withdrawals
                continue
                address = self._w3.toChecksumAddress(event['topics'][1][-20:])
                eth_amount = wei_to_ether(self._w3.toInt(event['topics'][2]))
                token_amount = self._w3.toInt(event['topics'][3]) / 10**self._decimals
            elif topic0 == add_liquidity_topic:
                # skip liquidity deposits/withdrawals
                continue
                address = self._w3.toChecksumAddress(event['topics'][1][-20:])
                eth_amount = wei_to_ether(self._w3.toInt(event['topics'][2]))
                token_amount = self._w3.toInt(event['topics'][3]) / 10**self._decimals
            else:
                logging.debug('unknown topic txhash', self._w3.toHex(event['transactionHash']))
                logging.debug('unknown topic topic0', topic0)
        self._time_volume_last_updated = time.time()

    async def _update(self, timeout=10.0):
        # TODO: The amount of tokens 'purchased' to determine the price should
        # not be a fixed value (200). Ideally, load the amount of tokens
        # available in the contract and use a certain percentage.
        amount_tokens = 200

        eth_amount_buy = wei_to_ether(self._exchange.functions.getEthToTokenOutputPrice(amount_tokens * 10**self._decimals).call())
        eth_amount_sell = wei_to_ether(self._exchange.functions.getTokenToEthInputPrice(amount_tokens * 10**self._decimals).call())
        average_eth_amount = (eth_amount_buy + eth_amount_sell) / 2

        self.price_eth = average_eth_amount / amount_tokens

        # update volume once every hour since it (potentially) loads eth api
        if time.time() - self._time_volume_last_updated > 60*60:
            await self._update_24h_volume()

if __name__ == "__main__":
    e = UniswapAPI('0xBTC')
    e.load_once_and_print_values()
