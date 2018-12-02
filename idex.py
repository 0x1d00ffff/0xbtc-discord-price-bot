"""
API for Mercatox (mercatox.com)
# TODO: add multiple exchange support.. currently assumes only one (forkdelta)
data = 
{'24volume': '411695.9617',
 'pairs': {'ADST_BTC': {'baseVolume': '4.8000',
                        'high24hr': '0.00001571',
                        'highestBid': '0.00001570',
                        'id': '115',
                        'isFrozen': '0',
                        'last': '0.00001571',
                        'low24hr': '0.00001571',
                        'lowestAsk': '0.00007998',
                        'percentChange': '0.00000000',
                        'quoteVolume': '0.0001'},
           'ETH_BTC': {'baseVolume': '1203.4878',
                       'high24hr': '0.08528997',
                       'highestBid': '0.07901667',
                       'id': '19',
                       'isFrozen': '0',
                       'last': '0.07901667',
                       'low24hr': '0.07700007',
                       'lowestAsk': '0.08080000',
                       'percentChange': '-6.49730000',
                       'quoteVolume': '99.5457'},
           'ETH_LTC': {'baseVolume': '69.8462',
                       'high24hr': '5.36530692',
                       'highestBid': '5.02000005',
                       'id': '27',
                       'isFrozen': '0',
                       'last': '5.17790647',
                       'low24hr': '5.02000005',
                       'lowestAsk': '5.29000000',
                       'percentChange': '-1.29100000',
                       'quoteVolume': '365.4700'},

                       ...


"""
import time
import logging
import socket
try:
    from urllib.request import urlopen, Request
except:
    from urllib import urlopen, Request

from urllib.error import URLError

import json

import pprint

from weighted_average import WeightedAverage


class IDEXAPI():
    def __init__(self, currency_symbol):
        self._SERVER_URL = "https://api.idex.market"
        self.currency_symbol = currency_symbol
        self.api_name = "IDEX"
        self.command_names = ['idex', 'idx']
        self.short_url = "https://bit.ly/2stRdvt"
        self.last_updated_time = 0

        self.price_eth = None
        self.price_usd = None
        self.price_btc = None
        self.volume_usd = None
        self.volume_eth = None
        self.volume_btc = None
        self.change_24h = None
        self.eth_price_usd = None
        self.btc_price_usd = None

    def _update(self, timeout=10.0):
        method = "/returnTicker"

        req = Request(
            self._SERVER_URL+method, 
            data=None, 
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
            }
        )

        response = urlopen(req, timeout=timeout)
        response = response.read().decode("utf-8") 
        try:
            data = json.loads(response)
        except json.decoder.JSONDecodeError:
            raise TimeoutError("api sent bad data ({})".format(repr(response)))

        #pprint.pprint(data)

        volume_usd = 0

        for pair_name in data:
            base_pair, currency = pair_name.split('_')
            # skip reverse-pairings
            if currency.lower() != self.currency_symbol.lower():
                continue

            pair_info = data[pair_name]

            #pprint.pprint(pair_info)

            if base_pair == "BTC":
                self.price_btc = float(pair_info['last'])
                self.volume_btc = float(pair_info['baseVolume'])
                # TODO: this should be tracked per-base pair
                self.change_24h = float(pair_info['percentChange']) / 100.0

            if base_pair == "ETH":
                self.price_eth = float(pair_info['last'])
                self.volume_eth = float(pair_info['baseVolume'])
                # TODO: this should be tracked per-base pair
                self.change_24h = float(pair_info['percentChange']) / 100.0


        if self.currency_symbol == "ETH":
            self.price_eth = 1
            self.eth_price_usd = self.price_usd

        if self.currency_symbol == "BTC":
            self.price_btc = 1
            self.btc_price_usd = self.price_usd

    def update(self, timeout=10.0):
        try:
            self._update(timeout=timeout)
        except (TimeoutError,
                ConnectionResetError,
                ConnectionRefusedError,
                socket.gaierror,
                socket.timeout,
                URLError) as e:
            logging.warning('api timeout {}: {}'.format(self.api_name, str(e)))
        else:
            self.last_updated_time = time.time()

    def print_all_values(self):
        print(self.api_name, self.currency_symbol, 'price_eth    ', repr(self.price_eth))
        print(self.api_name, self.currency_symbol, 'price_usd    ', repr(self.price_usd))
        print(self.api_name, self.currency_symbol, 'price_btc    ', repr(self.price_btc))
        print(self.api_name, self.currency_symbol, 'volume_usd   ', repr(self.volume_usd))
        print(self.api_name, self.currency_symbol, 'volume_eth   ', repr(self.volume_eth))
        print(self.api_name, self.currency_symbol, 'volume_btc   ', repr(self.volume_btc))
        print(self.api_name, self.currency_symbol, 'change_24h   ', repr(self.change_24h))
        print(self.api_name, self.currency_symbol, 'eth_price_usd', repr(self.eth_price_usd))
        print(self.api_name, self.currency_symbol, 'btc_price_usd', repr(self.btc_price_usd))

if __name__ == "__main__":

    # eth_api = IDEXAPI('ETH')
    # eth_api.update()
    # eth_api.print_all_values()

    btc_api = IDEXAPI('OMG')
    btc_api.update()
    btc_api.print_all_values()

    oxbtc_api = IDEXAPI('0xBTC')
    oxbtc_api.update()
    oxbtc_api.print_all_values()
