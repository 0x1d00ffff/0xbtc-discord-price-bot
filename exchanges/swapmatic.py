"""
API for Uniswap distributed exchange (uniswap.exchange)
Price info is pulled from the smart contract

https://docs.uniswap.io/api/exchange
"""
import logging
from web3 import Web3
import time

from .base_exchange import Daily24hChangeTrackedAPI
from .uniswap_v1_abi import exchange_abi
from .erc20_abi import erc20_abi
from secret_info import ETHEREUM_NODE_URL
from secret_info import MATIC_NODE_URL
from .uniswap_v2 import get_price as uniswap_v2_get_price

SECONDS_PER_MATIC_BLOCK = 2.1


def wei_to_ether(amount_in_wei):
    return int(amount_in_wei) / 1000000000000000000.0

def ether_to_wei(amount_in_ether):
    return int(amount_in_ether * 1000000000000000000.0)

class SwapmaticAPI(Daily24hChangeTrackedAPI):
    def __init__(self, currency_symbol):
        super().__init__()
        if currency_symbol == "0xBTC":
            self.exchange_address = "0x7c27aDF852c87D2A5BdF46abFDFa9531B76ef9c1"
            self.currency_address = "0x71B821aa52a49F32EEd535fCA6Eb5aa130085978"
            self._decimals = 8
        elif currency_symbol == "XXX":
            self.exchange_address = "0x0000000000000000000000000000000000000000"
            self.currency_address = "0x0000000000000000000000000000000000000000"
            self._decimals = 0
        else:
            raise RuntimeError("Unknown currency_symbol {}, need to add address to uniswap.py".format(currency_symbol))

        self.currency_symbol = currency_symbol
        self.exchange_name = "SwapMatic"
        self.command_names = ["swapmatic", "matic"]
        self.short_url = "https://bit.ly/2RPc2xt"  # swapmatic pre-selected to 0xbtc

        self._time_volume_last_updated = 0

        self._w3 = Web3(Web3.HTTPProvider(MATIC_NODE_URL))
        self._exchange = self._w3.eth.contract(address=self.exchange_address, abi=exchange_abi)

    async def _update_24h_volume(self, matic_eth_price, timeout=10.0):
        token_purchase_topic = "0xcd60aa75dea3072fbc07ae6d7d856b5dc5f4eee88854f5b4abf7b680ef8bc50f"
        eth_purchase_topic = "0x7f4091b46c33e918a0f3aa42307641d17bb67029427a5369e54b353984238705"
        transfer_topic = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
        remove_liquidity_topic = "0x0fbf06c058b90cb038a618f8c2acbf6145f8b3570fd1fa56abb8f0f3f05b36e8"
        add_liquidity_topic = "0x06239653922ac7bea6aa2b19dc486b9361821d37712eb796adfd38d81de278ca"
        current_eth_block = self._w3.eth.blockNumber
        volume_base = 0
        for event in self._w3.eth.getLogs({
                'fromBlock': current_eth_block - (int(60*60*24 / SECONDS_PER_MATIC_BLOCK)),
                'toBlock': current_eth_block - 1,
                'address': self.exchange_address}):
            topic0 = self._w3.toHex(event['topics'][0])
            if topic0 == token_purchase_topic:
                address = self._w3.toChecksumAddress(event['topics'][1][-20:])
                base_amount = wei_to_ether(self._w3.toInt(event['topics'][2]))
                token_amount = self._w3.toInt(event['topics'][3]) / 10**self._decimals
                volume_base += base_amount
            elif topic0 == eth_purchase_topic:
                address = self._w3.toChecksumAddress(event['topics'][1][-20:])
                token_amount = self._w3.toInt(event['topics'][2]) / 10**self._decimals
                base_amount = wei_to_ether(self._w3.toInt(event['topics'][3]))
                volume_base += base_amount
            elif topic0 == transfer_topic:
                # skip liquidity deposits/withdrawals
                continue
            elif topic0 == remove_liquidity_topic:
                # skip liquidity deposits/withdrawals
                continue
                address = self._w3.toChecksumAddress(event['topics'][1][-20:])
                base_amount = wei_to_ether(self._w3.toInt(event['topics'][2]))
                token_amount = self._w3.toInt(event['topics'][3]) / 10**self._decimals
            elif topic0 == add_liquidity_topic:
                # skip liquidity deposits/withdrawals
                continue
                address = self._w3.toChecksumAddress(event['topics'][1][-20:])
                base_amount = wei_to_ether(self._w3.toInt(event['topics'][2]))
                token_amount = self._w3.toInt(event['topics'][3]) / 10**self._decimals
            else:
                logging.debug('unknown topic txhash {}'.format(self._w3.toHex(event['transactionHash'])))
                logging.debug('unknown topic topic0 {}'.format(topic0))

        self.volume_eth = volume_base * matic_eth_price
        self._time_volume_last_updated = time.time()

    async def _update(self, timeout=10.0):
        # First grab price of ETH and price of MATIC from uniswap v2 on the eth network
        _w3 = Web3(Web3.HTTPProvider(ETHEREUM_NODE_URL))
        eth_dai_price = uniswap_v2_get_price(_w3, "DAI", "WETH")
        matic_eth_price = uniswap_v2_get_price(_w3, "WETH", "MATIC")
        matic_dai_price = matic_eth_price * eth_dai_price

        # TODO: The amount of tokens 'purchased' to determine the price should
        # not be a fixed value (200). Ideally, load the amount of tokens
        # available in the contract and use a certain percentage.
        amount_tokens = 200

        matic_amount_buy = wei_to_ether(self._exchange.functions.getEthToTokenOutputPrice(amount_tokens * 10**self._decimals).call())
        matic_amount_sell = wei_to_ether(self._exchange.functions.getTokenToEthInputPrice(amount_tokens * 10**self._decimals).call())
        average_matic_amount = (matic_amount_buy + matic_amount_sell) / 2

        average_eth_amount = average_matic_amount * matic_eth_price
        self.price_eth = average_eth_amount / amount_tokens

        # TODO: maybe don't do this? DAI isn't always 1:1 pegged to USD
        if self.currency_symbol == "DAI":
            self.eth_price_usd = 1 / self.price_eth

        # update volume once every hour since it (potentially) loads eth api
        if time.time() - self._time_volume_last_updated > 60*60:
            await self._update_24h_volume(matic_eth_price)

    # get the eth and token balance of a particular address in a uniswap v1 pool
    def get_pooled_balance_for_address(self, owner_address):
        all_ownership_tokens = self._exchange.functions.totalSupply().call()
        ownership_tokens_in_address = self._exchange.functions.balanceOf(owner_address).call()
        ownership_percentage = ownership_tokens_in_address / all_ownership_tokens

        eth_balance, token_balance = self.get_reserves()

        return eth_balance * ownership_percentage, token_balance * ownership_percentage

    # get the reserves, in eth and tokens, of a particular uniswap v1 pool
    def get_reserves(self):
        eth_balance = wei_to_ether(self._w3.eth.getBalance(self.exchange_address))
        token_contract = self._w3.eth.contract(address=self.currency_address, abi=erc20_abi)
        token_balance = token_contract.functions.balanceOf(self.exchange_address).call() / 10**self._decimals

        return eth_balance, token_balance

if __name__ == "__main__":
    e = SwapmaticAPI('0xBTC')
    e.load_once_and_print_values()
    print('reserves:', e.get_reserves())
    # e = SwapmaticAPI('DAI')
    # e.load_once_and_print_values()
