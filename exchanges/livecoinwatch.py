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
  # value of pase pair in USD
    'usdb': 0.594567000066063,
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
from .base_exchange import BaseExchangeAPI
from weighted_average import WeightedAverage


class LiveCoinWatchAPI(BaseExchangeAPI):
    def __init__(self, currency_symbol, allowed_apis='all'):
        super().__init__()
        self._SERVER_URL = "https://http-api.livecoinwatch.com"
        self.currency_symbol = currency_symbol
        self.allowed_apis = allowed_apis
        self.exchange_name = "Live Coin Watch"
        self.command_names = ['live coin watch']
        self.short_url = "https://bit.ly/2w6Q0P0"

    async def _update(self, timeout=10.0):
        method = "/markets?currency=USD&coin={}".format(self.currency_symbol)

        data = await self._get_json_from_url(self._SERVER_URL+method)

        # import pprint
        # print(self._SERVER_URL+method)
        # pprint.pprint(data)

        volume_usd = 0
        volume_usd_eth = 0
        volume_usd_btc = 0

        wavg_eth_price_usd = WeightedAverage()
        wavg_btc_price_usd = WeightedAverage()

        wavg_price_eth = WeightedAverage()
        wavg_price_btc = WeightedAverage()
        wavg_price_usd = WeightedAverage()

        for exchange_data in data['data']:
            # skip reverse-pairings
            if exchange_data['base'] != self.currency_symbol:
                continue

            # last_price_in_usd = data['data'][0]['usd']
            # last_price_in_eth = data['data'][0]['rate']
            # last_eth_price = data['data'][0]['lastq']
            base_pair = exchange_data['quote']
            relative_volume = float(exchange_data['volume'])

            # NOTE: this entire if statement is ONLY to collect price of eth and btc
            if base_pair == "ETH":
                # average price of base pairs, they are NOT all the same
                wavg_eth_price_usd.add(exchange_data['usdq'], relative_volume)
            elif (base_pair in ["AUD", "CAD", "CNY", "DAI", "EUR", "EURO", "GBP", "JPY", "KRW", "RUB", "USDT", "USD"]):
                # allow all fiat pairings to count towards volume
                pass
            elif (base_pair in ["BTC"]):
                # average price of base pairs, they are NOT all the same
                wavg_btc_price_usd.add(exchange_data['usdq'], relative_volume)
                # allow BTC pairings to count towards volume
                pass
            else:
                # if base pair is unknown, don't use for calcualted volume/price
                continue

            # only let allowed_apis to count toward price
            if self.allowed_apis == 'all' or exchange_data['exchange'] in self.allowed_apis:
                wavg_price_usd.add(exchange_data['usdb'], relative_volume)
                volume_usd += exchange_data['volume']
                
                if base_pair == "ETH":
                    wavg_price_eth.add(exchange_data['rate'], relative_volume)
                    volume_usd_eth += exchange_data['volume']
                
                if base_pair == "BTC":
                    wavg_price_btc.add(exchange_data['rate'], relative_volume)
                    volume_usd_btc += exchange_data['volume']

        self.price_usd = wavg_price_usd.average()

        self.eth_price_usd = wavg_eth_price_usd.average()
        if self.eth_price_usd == 0:
            self.eth_price_usd = None
        self.btc_price_usd = wavg_btc_price_usd.average()
        if self.btc_price_usd == 0:
            self.btc_price_usd = None

        if self.currency_symbol == "ETH":
            self.price_eth = 1
            self.eth_price_usd = self.price_usd
        else:
            self.price_eth = wavg_price_eth.average()

        self.volume_usd = volume_usd

        if self.eth_price_usd != None and self.eth_price_usd != 0:
            # TODO: volume_eth should really represent quantity of volume in eth,
            # not quantity of all volume converted to price of eth. This
            # calculation includes btc in eth volume.
            self.volume_eth = volume_usd_eth / self.eth_price_usd

        if self.btc_price_usd != None and self.btc_price_usd != 0:
            # TODO: volume_eth should really represent quantity of volume in eth,
            # not quantity of all volume converted to price of eth. This
            # calculation includes btc in eth volume.
            self.volume_btc = volume_usd_btc / self.btc_price_usd

        if self.currency_symbol == "BTC":
            self.price_btc = 1
            self.btc_price_usd = self.price_usd
        else:
            self.price_btc = wavg_price_btc.average()

if __name__ == "__main__":

    api = LiveCoinWatchAPI('ETH')
    api.load_once_and_print_values()

    api = LiveCoinWatchAPI('BTC')
    api.load_once_and_print_values()

    api = LiveCoinWatchAPI('0xBTC')
    api.load_once_and_print_values()
