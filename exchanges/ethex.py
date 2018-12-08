"""
API for Ethex (ethex.market)

https://api.ethex.market:5055/ticker24

data = 
{
  "ETH_BAT": {
    "last": null,
    "lowestAsk": "0.00131868",
    "highestBid": "0.001014",
    "volume": "0",
    "high24hr": null,
    "low24hr": null
  },
  "ETH_DAI": {
    "last": null,
    "lowestAsk": "0.00494096",
    "highestBid": "0.004627456",
    "volume": "0",
    "high24hr": null,
    "low24hr": null
  },
                       ...
"""
from .base_exchange import BaseExchangeAPI


class EthexAPI(BaseExchangeAPI):
    def __init__(self, currency_symbol):
        super().__init__()
        self._SERVER_URL = "https://api.ethex.market:5055"
        self.currency_symbol = currency_symbol
        self.exchange_name = "Ethex"
        self.command_names = ["ethex", "ethx"]
        self.short_url = "https://bit.ly/2SrmIl6"
        self.last_updated_time = 0
        self.update_failure_count = 0

    async def _update(self, timeout=10.0):
        method = "/ticker24"
        data = await self._get_json_from_url(self._SERVER_URL+method)

        for pair_name in data:
            base_pair, currency = pair_name.split('_')
            # skip reverse-pairings
            if currency != self.currency_symbol:
                continue

            try:
                if base_pair == "BTC":
                    self.price_btc = float(data[pair_name]['last'])
                    self.volume_btc = float(data[pair_name]['volume'])
                if base_pair == "ETH":
                    self.price_eth = float(data[pair_name]['last'])
                    self.volume_eth = float(data[pair_name]['volume'])
            except TypeError as e:
                raise TimeoutError("Could not convert data to float") from e

        if self.currency_symbol == "ETH":
            self.price_eth = 1
            self.eth_price_usd = self.price_usd
        if self.currency_symbol == "BTC":
            self.price_btc = 1
            self.btc_price_usd = self.price_usd

if __name__ == "__main__":

    btc_api = EthexAPI('DAI')
    btc_api.load_once_and_print_values()

    oxbtc_api = EthexAPI('0xBTC')
    oxbtc_api.load_once_and_print_values()
