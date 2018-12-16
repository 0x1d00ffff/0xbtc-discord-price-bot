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

from .base_exchange import BaseExchangeAPI


def wei_to_ether(amount_in_wei):
    return int(amount_in_wei) / 1000000000000000000.0

class EnclavesAPI(BaseExchangeAPI):
    def __init__(self, currency_symbol):
        super().__init__()
        self._WEBSOCKET_URL = "ws://app.enclaves.io:80/socket.io/?EIO=3&transport=websocket";

        if currency_symbol == "0xBTC":
            self._CONTRACT_ADDRESS = '0xb6ed7644c69416d67b522e20bc294a9a9b405b31'
        elif currency_symbol == "XXX":
            self._CONTRACT_ADDRESS = '0x0000000000000000000000000000000000000000'
        else:
            raise RuntimeError("Unknown currency_symbol {}, need to add address to enclavesdex.py".format(currency_symbol))

        self.currency_symbol = currency_symbol
        self.exchange_name = "Enclaves DEX"
        self.command_names = ['enclaves', 'encalves']
        self.short_url = "https://bit.ly/2rnYA7b"

    async def _update(self, timeout=10.0):
        ws = websocket.create_connection(self._WEBSOCKET_URL, timeout=timeout)
        # real implementations read session id etc first so we do the same
        result = ws.recv()
        result = ws.recv()
        # request actual data
        ws.send('42["getTokens"]')
        result = ws.recv()

        try:
            all_data = json.loads(result[2:])
        except json.decoder.JSONDecodeError:
            if "be right back" in response:
                raise TimeoutError("api is down - got 404 page")
            else:
            	raise TimeoutError("api sent bad data ({})".format(repr(response)))

        data_was_updated = False
        tokens = all_data[1]['tokens']
        for token in tokens:
            if token['addr'] == self._CONTRACT_ADDRESS:
                self.price_eth = float(token['priceEnclaves'])
                self.volume_eth = wei_to_ether(token['volumeEther'])
                self.change_24h = float(token['change'])
                data_was_updated = True

        if self.price_eth == self.volume_eth == self.change_24h == 0.0:
            raise TimeoutError('All values from enclaves read 0')

        if not data_was_updated:
            raise RuntimeError('Response from Enclaves did not include indicated currency ({}).'.format(self.currency_symbol))

if __name__ == "__main__":
    e = EnclavesAPI('0xBTC')
    e.load_once_and_print_values()
