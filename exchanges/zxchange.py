"""
API for 0xchange
Support only for WETH pairs

{'base': '0XBTC',
 'close_price': '0.001',
 'id': 48,
 'last_price': '0.001',
 'last_price_change': '0.11111111111111116',
 'last_price_usd': None,
 'open_price': '0.0009',
 'pair': '0XBTC-WETH',
 'price_max_24': '0.001',
 'price_min_24': '0.0009',
 'quote': 'WETH',
 'quote_volume_24': '0.001',
 'resolution': 'D',
 'total_orders': 2,
 'updated_at': '1570595563573',
 'utc_date': '2019-10-9',
 'utc_timestamp': '1570579200',
 'volume_24': '6'}


"""
from .base_exchange import BaseExchangeAPI
from async_url_helpers import get_json_from_url


class ZxchangeAPI(BaseExchangeAPI):
    def __init__(self, currency_symbol):
        super().__init__()
        self._SERVER_URL = "https://dex-backend.verisafe.io/v3/"
        self.exchange_name = "0xChange"
        self.command_names = ['0xchange', 'zxchange', 'change']
        self.short_url = "http://bit.ly/35mgKIz"

        if currency_symbol.lower() == "0xbtc":
            self.currency_symbol = "0xBTC"
            self._symbol_on_exchange = "0XBTC"
        else:
            raise RuntimeError("Unexpected currency_symbol {}".format(currency_symbol))

    async def _update(self, timeout=10.0):
        method = "markets/stats/"+self._symbol_on_exchange+"-WETH"
        data = await get_json_from_url(self._SERVER_URL+method)
        try:
            self.price_eth = float(data['last_price'])
            self.volume_eth = float(data['quote_volume_24'])
            self.change_24h = float(data['last_price_change'])
        except TypeError as e:
            raise TimeoutError("Could not convert data to float") from e

        return

        # later on, DAI might be supported via this api
        method = "markets/stats/"+self._symbol_on_exchange+"-DAI"
        data = await get_json_from_url(self._SERVER_URL+method)
        try:
            self.price_usd = float(data['last_price'])
            self.volume_usd = float(data['quote_volume_24'])
        #     self.change_24h = float(data['last_price_change']) * 100.0
        except TypeError as e:
            raise TimeoutError("Could not convert data to float") from e


if __name__ == "__main__":
    api = ZxchangeAPI('0xBTC')
    api.load_once_and_print_values()
