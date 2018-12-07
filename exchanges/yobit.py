# API For Yobit exchange
#
# Thanks SEDO devs https://github.com/CryptoProjectDev/sedo-information-discord-bot/

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

from .base_exchange import BaseExchangeAPI


class YobitAPI(BaseExchangeAPI):
    def __init__(self, currency_symbol):
        super().__init__()
        self._SERVER_URL = "https://yobit.io/api/3/ticker"
        self.exchange_name = "Yobit"
        self.command_names = ["yobit"]

        self.currency_symbol = currency_symbol
        if currency_symbol == "SEDO":
            self.short_url = "https://bit.ly/2R0FHSf"
            self._currency_name_on_exchange = "sedo"
        else:
            raise RuntimeError("Unknown currency {}; need to edit yobit.py".format(currency_symbol))

    def _update(self, timeout=10.0):
        method = "/{0}_btc-{0}_eth-eth_usd-btc_usd".format(self._currency_name_on_exchange)

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
            raise TimeoutError("bad reply from server ({})".format(repr(response)))

        volume_usd = 0

        self.price_btc = float(data['{}_btc'.format(self._currency_name_on_exchange)]['last'])
        self.volume_btc = float(data['{}_btc'.format(self._currency_name_on_exchange)]['vol'])
        self.price_eth = float(data['{}_eth'.format(self._currency_name_on_exchange)]['last'])
        self.volume_eth = float(data['{}_eth'.format(self._currency_name_on_exchange)]['vol'])
        self.eth_price_usd = float(data['eth_usd']['last'])
        self.btc_price_usd = float(data['btc_usd']['last'])

if __name__ == "__main__":

    sedo_api = YobitAPI('SEDO')
    sedo_api.load_once_and_print_values()