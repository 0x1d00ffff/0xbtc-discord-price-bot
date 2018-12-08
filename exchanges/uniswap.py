"""
API for Enclaves distributed exchange (enclaves.io)

example token entry:
    {'addr': '0xb6ed7644c69416d67b522e20bc294a9a9b405b31',
     'amountEther': '22230538924500000',
     'amountToken': '3293413174',
     'change': '-0.13460428979858716137',
     'priceEnclaves': '0.000675',
     'volumeEnclavesEther': '17921353316879564600',
     'volumeEther': '21737691009396312760'},
"""
import websocket
import json
from web3 import Web3

from .base_exchange import BaseExchangeAPI
from .uniswap_abi import exchange_abi

from configuration import ETHEREUM_NODE_URL


def wei_to_ether(amount_in_wei):
    return int(amount_in_wei) / 1000000000000000000.0

def ether_to_wei(amount_in_ether):
    return int(amount_in_ether * 1000000000000000000.0)

class UniswapAPI(BaseExchangeAPI):
    def __init__(self, currency_symbol):
        super().__init__()
        if currency_symbol == "0xBTC":
            uniswap_exchange_address = "0x701564Aa6E26816147D4fa211a0779F1B774Bb9B"
            self._decimals = 8
        elif currency_symbol == "XXX":
            uniswap_exchange_address = "0x0000000000000000000000000000000000000000"
            self._decimals = 0
        else:
            raise RuntimeError("Unknown currency_symbol {}, need to add address to uniswap.py".format(currency_symbol))

        self.currency_symbol = currency_symbol
        self.exchange_name = "Uniswap"
        self.command_names = ["uniswap"]
        self.short_url = "https://bit.ly/2PnLAre"

        self._w3 = Web3(Web3.HTTPProvider(ETHEREUM_NODE_URL))
        self._exchange = self._w3.eth.contract(address=uniswap_exchange_address, abi=exchange_abi)

    async def _update(self, timeout=10.0):
        # TODO: The amount of tokens 'purchased' to determine the price should
        # not be a fixed value (100). Ideally, load the amount of tokens
        # available in the contract and use a certain percentage.
        amount_tokens = 100

        eth_amount_buy = wei_to_ether(self._exchange.functions.getEthToTokenOutputPrice(amount_tokens * 10**self._decimals).call())
        eth_amount_sell = wei_to_ether(self._exchange.functions.getTokenToEthInputPrice(amount_tokens * 10**self._decimals).call())
        average_eth_amount = (eth_amount_buy + eth_amount_sell) / 2

        self.price_eth = average_eth_amount / amount_tokens

if __name__ == "__main__":
    e = UniswapAPI('0xBTC')
    e.load_once_and_print_values()
