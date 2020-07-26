"""
API for ForkDelta

TODO: replace with real API instead of relying on livecoinwatch

data = 
{'data': [
    {
        '__v': 0,
        '_id': '5ae231e61bf2276634e771d5',
        'active': True,
        'base': '0xBTC',
        'exchange': 'ForkDelta',
        'last': 0.594567000066063,
        'lastq': 660.6300000000001,
        'outlier': False,
        'quote': 'ETH',
      # last price in the quote currency
        'rate': 0.0009000000001,
        'url': 'https://forkdelta.github.io/#!/trade/0xBTC-ETH',
      # value in USD
        'usd': 0.594567000066063,
      # price of the quote currency (ETH, BTC, etc) in USD
        'usdq': 660.6300000000001,
      # 24h volume in USD
        'volume': 20153.666549554204,
      # volume of this exchange as % of total volume for this coin
        'volumep': 100,
        'volumepq': 0.0007236425477855652
    },{
      # info for exchange #2, etc
    }],


"""
import logging
from web3 import Web3
import time
from .base_exchange import BaseExchangeAPI
from .etherdelta_v2_abi import exchange_abi
from secret_info import ETHEREUM_NODE_URL
from constants import SECONDS_PER_ETH_BLOCK
from persistent_storage import Storage

ETHERDELTA_V2_ADDRESS = "0x8d12A197cB00D4747a1fe03395095ce2A5CC6819"
# etherdelta does a weird thing where it treats eth as a token at 0x0. this is a copy
ETH_AS_TOKEN_ADDRESS = "0x0000000000000000000000000000000000000000"
ETHEREUM_DECIMALS = 18


class ForkDeltaAPI(BaseExchangeAPI):
    def __init__(self, currency_symbol, persistent_storage):
        super().__init__()
        self.exchange_name = "Fork Delta"
        self.command_names = ["fd", "fork delta"]
        self.short_url = "https://bit.ly/2rqTGWB"
        self.currency_symbol = currency_symbol
        self._persistent_storage = persistent_storage

        # TODO: switch to using a global token address lookup module
        if self.currency_symbol == "0xBTC":
            self._token_address = "0xB6eD7644C69416d67B522e20bC294A9a9B405B31"
            self._token_decimals = 8
        else:
            raise RuntimeError("Unknown currency_symbol {}, need to add address to forkdelta.py. Note that if you are running two forkdelta modules at once, you will need to upgrade ForkDeltaAPI to use different persistent_storage modules.".format(self.currency_symbol))

        self._w3 = Web3(Web3.HTTPProvider(ETHEREUM_NODE_URL))
        self._exchange = self._w3.eth.contract(address=ETHERDELTA_V2_ADDRESS, abi=exchange_abi)

    async def get_history_n_days(self, num_days=1, timeout=10.0):
        volume_tokens = 0
        volume_eth = 0
        last_price = None
        trade_topic = "0x6effdda786735d5033bfad5f53e5131abcced9e52be6c507b62d639685fbed6d"
        withdraw_topic = "0xf341246adaac6f497bc2a656f546ab9e182111d630394f0c57c710a59a2cb567"
        deposit_topic = "0xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7"
        cancel_topic = "0x1e0b760c386003e9cb9bcf4fcf3997886042859d9b6ed6320e804597fcdb28b0"
        current_eth_block = self._w3.eth.blockNumber

        for event in self._w3.eth.getLogs({
                'fromBlock': current_eth_block - (int(60*60*24*num_days / SECONDS_PER_ETH_BLOCK)),
                'toBlock': current_eth_block - 1,
                'address': self._exchange.address}):
            topic0 = self._w3.toHex(event['topics'][0])

            if topic0 == trade_topic:
                #print('trade in tx', self._w3.toHex(event['transactionHash']))
                receipt = self._w3.eth.getTransactionReceipt(event['transactionHash'])
                parsed_logs = self._exchange.events.Trade().processReceipt(receipt)
                correct_log = None
                for log in parsed_logs:
                    if log.address.lower() == self._exchange.address.lower():
                        correct_log = log
                if correct_log is None:
                    logging.warning('bad trade transaction {}'.format(self._w3.toHex(event['transactionHash'])))
                    continue

                tokenGet = correct_log.args.tokenGet
                amountGet = correct_log.args.amountGet
                tokenGive = correct_log.args.tokenGive
                amountGive = correct_log.args.amountGive
                get = correct_log.args.get
                give = correct_log.args.give  # this is msg.sender from contract perspective
                block_number = correct_log.blockNumber

                if tokenGive.lower() == self._token_address.lower():
                    token_amount = amountGive / 10**self._token_decimals
                    eth_amount = amountGet / 10**ETHEREUM_DECIMALS
                elif tokenGet.lower() == self._token_address.lower():
                    token_amount = amountGet / 10**self._token_decimals
                    eth_amount = amountGive / 10**ETHEREUM_DECIMALS
                else:
                    # trade doesn't include token we are interested in, so skip
                    continue

                volume_tokens += token_amount
                volume_eth += eth_amount
                last_price = eth_amount / token_amount
                #print('{} tokens and {} eth - last_price {}'.format(token_amount, eth_amount, last_price))

            elif topic0 == withdraw_topic:
                #print('withdraw in tx', self._w3.toHex(event['transactionHash']))
                continue
            elif topic0 == deposit_topic:
                #print('deposit in tx', self._w3.toHex(event['transactionHash']))
                continue
            elif topic0 == cancel_topic:
                #print('cancel in tx', self._w3.toHex(event['transactionHash']))
                continue
            else:
                logging.debug('unknown topic txhash {}'.format(self._w3.toHex(event['transactionHash'])))
                logging.debug('unknown topic topic0 {}'.format(topic0))

        return volume_tokens, volume_eth, last_price

    async def _update(self, timeout=10.0):
        volume_tokens, volume_eth, last_price = await self.get_history_n_days(num_days=1, timeout=timeout)

        self.volume_tokens = volume_tokens
        self.volume_eth = volume_eth

        # Forkdelta is difficult to handle; there is no price available from the contract.
        # Instead you must remember the price of the last trade. Of course there are 
        # better and more complicated ways to consider price (order book for example) but
        # this tracker does not aim to be complicated.
        if last_price is None:
            last_price = self._persistent_storage.last_forkdelta_price.get()
        else:
            self._persistent_storage.last_forkdelta_price.set(last_price)

        self.price_eth = last_price


if __name__ == "__main__":
    storage = Storage('./test_data/databases/')
    oxbtc_api = ForkDeltaAPI("0xBTC", storage)
    oxbtc_api.load_once_and_print_values()

    # dai_api = ForkDeltaAPI("OMG")
    # dai_api.load_once_and_print_values()
