"""
API for CoinMarketCap (coinmarketcap.com)
# TODO: add multiple coin support.. currently only 0xBTC
data = 
{'data': {'0xBTC': {'circulating_supply': 5736550,
                    'cmc_rank': 1018,
                    'date_added': '2018-06-04T00:00:00.000Z',
                    'id': 2837,
                    'is_active': 1,
                    'is_fiat': 0,
                    'last_updated': '2020-06-03T08:28:09.000Z',
                    'max_supply': None,
                    'name': '0xBitcoin',
                    'num_market_pairs': 7,
                    'platform': {'id': 1027,
                                 'name': 'Ethereum',
                                 'slug': 'ethereum',
                                 'symbol': 'ETH',
                                 'token_address': '0xb6ed7644c69416d67b522e20bc294a9a9b405b31'},
                    'quote': {'USD': {'last_updated': '2020-06-03T08:28:09.000Z',
                                      'market_cap': 762341.7350225202,
                                      'percent_change_1h': -2.92041,
                                      'percent_change_24h': -7.08114,
                                      'percent_change_7d': -0.200939,
                                      'price': 0.132892023084,
                                      'volume_24h': 1100779.78357411}},
                    'slug': '0xbtc',
                    'symbol': '0xBTC',
                    'tags': ['mineable'],
                    'total_supply': 20999984}},
 'status': {'credit_count': 1,
            'elapsed': 6,
            'error_code': 0,
            'error_message': None,
            'notice': None,
            'timestamp': '2020-06-03T08:28:37.881Z'}}

https://api.coinmarketcap.com/v2/ticker/1027/

"""
from .base_exchange import BaseExchangeAPI
from secret_info import COINMARKETCAP_API_KEY


class CoinMarketCapAPI(BaseExchangeAPI):
    def __init__(self, currency_symbol):
        super().__init__()
        self._SERVER_URL = "https://pro-api.coinmarketcap.com/v1"
        self.currency_symbol = currency_symbol
        self.exchange_name = "Coin Market Cap"
        self.command_names = ['cmc', 'coinmarketcap']
        self.short_url = "https://bit.ly/1hJ8ztr"
        self.last_updated_time = 0
        self.update_failure_count = 0
        self._skip_counter = 0

    async def _update_cmc_data(self, timeout):
        parameters = {
            'symbol': self.currency_symbol
        }
        headers = {
            'Accepts': 'application/json',
            'X-CMC_PRO_API_KEY': COINMARKETCAP_API_KEY,
        }
        method = "/cryptocurrency/quotes/latest"
        data = await self._get_json_from_url(
            self._SERVER_URL + method,
            parameters=parameters,
            headers=headers)

        # CMC-only attributes; TODO: use market_cap in !market or something
        self.rank = int(data['data'][self.currency_symbol]['cmc_rank'])
        self.market_cap = float(data['data'][self.currency_symbol]['quote']['USD']['market_cap'])

        self.price_usd = float(data['data'][self.currency_symbol]['quote']['USD']['price'])

        # hack: only pull volume data for ETH and BTC, since they are usually
        # used as reference currencies only. The volume is ignored for other
        # currencies, since volume in this bot is defined as a per-exchange
        # volume, not an aggregate like CMC's api.
        #
        # this is done because otherwise, coinmarketcap would have its own volume
        # for the 0xBTC pair, and the rest of this program would treat it as an
        # exchange with N volume - but that volume is really just an aggregate
        # of the volumes of our other tracked exchanges
        if self.currency_symbol == "ETH" or self.currency_symbol == "BTC":
            self.volume_usd = float(data['data'][self.currency_symbol]['quote']['USD']['volume_24h'])
            self.change_24h = float(data['data'][self.currency_symbol]['quote']['USD']['percent_change_24h']) / 100.0

        if self.currency_symbol == "ETH":
            self.price_eth = 1
            self.eth_price_usd = self.price_usd

        if self.currency_symbol == "BTC":
            self.price_btc = 1
            self.btc_price_usd = self.price_usd

    async def _update(self, timeout=10.0):
        # HACK: since coinmarketcap has a much lower api limit than the other data
        # sources, add a check here to only update every 10th time this function is
        # called. combined with the 2m normal update rate, this should limit CMC to an
        # update only every 20m.
        if self._skip_counter <= 0:
            self._update_cmc_data(timeout)
            self._skip_counter = 10
        else:
            self._skip_counter -= 1
            return


if __name__ == "__main__":
    eth_api = CoinMarketCapAPI('ETH')
    eth_api.load_once_and_print_values()
    eth_api = CoinMarketCapAPI('0xBTC')
    eth_api.load_once_and_print_values()
