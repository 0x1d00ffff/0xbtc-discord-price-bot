"""
API for LiveCoinWatch (livecoinwatch.com)
# TODO: add multiple exchange support.. currently assumes only one (forkdelta)
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
import time
import logging
import socket
try:
    from urllib.request import urlopen
except:
    from urllib import urlopen

import json

import pprint

from weighted_average import WeightedAverage


class LiveCoinWatchAPI():
    def __init__(self, currency_symbol="0xBTC"):
        self._SERVER_URL = "https://www.livecoinwatch.com/api"
        self.currency_symbol = currency_symbol
        self.api_name = "Live Coin Watch"
        self.short_url = "https://bit.ly/2w6Q0P0"
        self.last_updated_time = 0

        self.price_eth = None
        self.price_usd = None
        self.volume_usd = None
        self.volume_eth = None
        self.change_24h = None
        self.eth_price_usd = None
        self.btc_price_usd = None

    def _update(self, timeout=10.0):
        method = "/coin/{}".format(self.currency_symbol)

        response = urlopen(self._SERVER_URL+method, timeout=timeout)
        response = response.read().decode("utf-8") 
        try:
            data = json.loads(response)
        except json.decoder.JSONDecodeError:
            if "be right back" in response:
                raise TimeoutError("api is down - got 404 page")
            else:
            	raise TimeoutError("api sent bad data ({})".format(repr(response)))
            

        volume_usd = 0



        volume_usd = 0
        wavg_price_eth = WeightedAverage()
        wavg_price_usd = WeightedAverage()

        for exchange_data in data['data']:
            # skip reverse-pairings
            if exchange_data['base'] != self.currency_symbol:
                continue

            # last_price_in_usd = data['data'][0]['usd']
            # last_price_in_eth = data['data'][0]['rate']
            # last_eth_price = data['data'][0]['lastq']
            base_pair = exchange_data['quote']

            relative_volume = float(exchange_data['volumep'])

            if base_pair == "ETH":
                # TODO: average price of base pairs (or something), they might all be the same
                self.eth_price_usd = exchange_data['lastq']

                wavg_price_eth.add(exchange_data['rate'], relative_volume)
            elif (base_pair in ["AUD", "CAD", "CNY", "DAI", "EUR", "EURO", "GBP", "JPY", "KRW", "RUB", "USDT", "USD"]):
                # allow all fiat pairings to count towards volume
                pass
            elif (base_pair in ["BTC"]):
                # TODO: average price of base pairs (or something), they might all be the same
                self.btc_price_usd = exchange_data['lastq']
                # allow BTC pairings to count towards volume
                pass
            else:
                #pprint.pprint(exchange_data)
                logging.debug('Unknown base_pair {}'.format(base_pair))
                # if base pair is unknown, don't use for calcualted volume/price
                continue

            wavg_price_usd.add(exchange_data['usd'], relative_volume)
            volume_usd += exchange_data['volume']



        self.price_usd = wavg_price_usd.average()

        if self.currency_symbol == "ETH":
            self.price_eth = 1
            self.eth_price_usd = self.price_usd
        else:
            self.price_eth = wavg_price_eth.average()

        self.volume_usd = volume_usd
        self.volume_eth = self.volume_usd / self.eth_price_usd

        if self.currency_symbol == "BTC":
            self.btc_price_usd = self.price_usd

    def update(self, timeout=10.0):
        try:
            self._update(timeout=timeout)
        except (TimeoutError,
                ConnectionResetError,
                ConnectionRefusedError,
                socket.timeout,
                socket.gaierror) as e:
            logging.warning('api timeout {}: {}'.format(self.api_name, str(e)))
        else:
            self.last_updated_time = time.time()

    def print_all_values(self):
        print(self.api_name, self.currency_symbol, 'price_eth    ', self.price_eth)
        print(self.api_name, self.currency_symbol, 'price_usd    ', self.price_usd)
        print(self.api_name, self.currency_symbol, 'volume_usd   ', self.volume_usd)
        print(self.api_name, self.currency_symbol, 'volume_eth   ', self.volume_eth)
        print(self.api_name, self.currency_symbol, 'change_24h   ', self.change_24h)
        print(self.api_name, self.currency_symbol, 'eth_price_usd', self.eth_price_usd)
        print(self.api_name, self.currency_symbol, 'btc_price_usd', self.btc_price_usd)

if __name__ == "__main__":
    oxbtc_api = LiveCoinWatchAPI('0xBTC')
    oxbtc_api.update()
    oxbtc_api.print_all_values()

    btc_api = LiveCoinWatchAPI('ETH')
    btc_api.update()
    btc_api.print_all_values()

    btc_api = LiveCoinWatchAPI('BTC')
    btc_api.update()
    btc_api.print_all_values()
