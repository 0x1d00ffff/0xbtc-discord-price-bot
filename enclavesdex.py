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
import time
import logging
import socket
import websocket
import json
import pprint

try:
    from urllib.request import urlopen
except:
    from urllib import urlopen


def wei_to_ether(amount_in_wei):
    return int(amount_in_wei) / 1000000000000000000.0

class EnclavesAPI():
    def __init__(self, currency_symbol="0xBTC"):
        self._WEBSOCKET_URL = "ws://app.enclaves.io:80/socket.io/?EIO=3&transport=websocket";

        if currency_symbol == "0xBTC":
            self._CONTRACT_ADDRESS = '0xb6ed7644c69416d67b522e20bc294a9a9b405b31'
        else:
            raise RuntimeError("Unknown currency_symbol {}".format(currency_symbol))

        self.last_updated_time = 0

        self.currency_symbol = currency_symbol
        self.api_name = "Enclaves DEX"

        self.price_eth = None
        self.price_usd = None
        self.volume_eth = None
        self.volume_usd = None
        self.change_24h = None
        self.eth_price_usd = None
        self.btc_price_usd = None


    def _update(self, timeout=10.0):
        #print('connecting to', self._WEBSOCKET_URL)

        ws = websocket.create_connection(self._WEBSOCKET_URL, timeout=timeout)
        #print('connected')
        # TMP forks read session id etc first so we do the same
        #print('rcv')
        result = ws.recv()
        #print('result:')
        #pprint.pprint(result)
        #print('rcv')
        result = ws.recv()
        #print('result:')
        #pprint.pprint(result)
        #request miner data
        ws.send('42["getTokens"]')
        result = ws.recv()
        #print('result:')
        #pprint.pprint(result)
        all_data = json.loads(result[2:])
        #pprint.pprint(all_data)
        tokens = all_data[1]['tokens']
        for token in tokens:
            if token['addr'] == self._CONTRACT_ADDRESS:
                self.price_eth = float(token['priceEnclaves'])
                self.volume_eth = wei_to_ether(token['volumeEther'])
                self.change_24h = float(token['change'])


    def update(self, timeout=10.0):
        try:
            self._update(timeout=timeout)
        except websocket._exceptions.WebSocketTimeoutException:
            logging.warning('api timeout {}'.format(self.api_name))
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
    e = EnclavesAPI('0xBTC')

    e.update()
    e.print_all_values()
