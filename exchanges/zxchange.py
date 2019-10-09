"""
API for 0xchange
Support only for WETH pairs
"""
from .base_exchange import BaseExchangeAPI


class ZxchangeAPI(BaseExchangeAPI):
    def __init__(self, currency_symbol):
        super().__init__()
        self._SERVER_URL = "https://veridex.herokuapp.com/v2/"
        self.currency_symbol = currency_symbol
        self.exchange_name = "0xChange"
        self.command_names = ['0x', 
                              '0xchange', 
                              '0xbtc', 
                              'change']
        self.short_url = "http://bit.ly/35mgKIz"

    async def _update(self, timeout=10.0):
        method = "markets/stats/"+self.currency_symbol+"-WETH"
        data = await self._get_json_from_url(self._SERVER_URL+method)
        try:
            self.price_eth = float(data['last_price'])
            self.volume_eth = float(data['quote_volume_24'])
            self.change_24h = float(data['last_price_change']) * 100.0

        except TypeError as e:
                raise TimeoutError("Could not convert data to float") from e

if __name__ == "__main__":
    api = ZxchangeAPI('0XBTC')
    api.load_once_and_print_values()

