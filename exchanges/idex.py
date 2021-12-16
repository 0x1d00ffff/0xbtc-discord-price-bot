"""
API for IDEX (idex.market)
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
from .base_exchange import BaseExchangeAPI
from async_url_helpers import get_json_from_url


class IDEXAPI(BaseExchangeAPI):
    def __init__(self, currency_symbol):
        super().__init__()
        self._SERVER_URL = "https://api.idex.market"
        self.currency_symbol = currency_symbol
        self.exchange_name = "IDEX"
        self.command_names = ['idex', 'idx']
        self.short_url = "https://bit.ly/2stRdvt"

    async def _update(self, timeout=10.0):
        method = "/returnTicker"
        data = await get_json_from_url(self._SERVER_URL+method)

        for pair_name in data:
            base_pair, currency = pair_name.split('_')
            # skip reverse-pairings
            if currency.lower() != self.currency_symbol.lower():
                continue

            pair_info = data[pair_name]

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

if __name__ == "__main__":
    omg_api = IDEXAPI('OMG')
    omg_api.load_once_and_print_values()
    oxbtc_api = IDEXAPI('0xBTC')
    oxbtc_api.load_once_and_print_values()
