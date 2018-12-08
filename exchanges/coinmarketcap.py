"""
API for CoinMarketCap (coinmarketcap.com)
# TODO: add multiple coin support.. currently only 0xBTC
data = 
{
    "data": {
        "id": 1027, 
        "name": "Ethereum", 
        "symbol": "ETH", 
        "website_slug": "ethereum", 
        "rank": 2, 
        "circulating_supply": 102638687.0, 
        "total_supply": 102638687.0, 
        "max_supply": null, 
        "quotes": {
            "USD": {
                "price": 207.52442295, 
                "volume_24h": 1419432665.53611, 
                "market_cap": 21300034253.0, 
                "percent_change_1h": 0.12, 
                "percent_change_24h": -1.36, 
                "percent_change_7d": -1.48
            }
        }, 
        "last_updated": 1539832604
    }, 
    "metadata": {
        "timestamp": 1539831963, 
        "error": null
    }
}

https://api.coinmarketcap.com/v2/ticker/1027/

"""
from .base_exchange import BaseExchangeAPI


class CoinMarketCapAPI(BaseExchangeAPI):
    def __init__(self, currency_symbol):
        super().__init__()
        self._SERVER_URL = "https://api.coinmarketcap.com/v2"
        self.currency_symbol = currency_symbol
        self.exchange_name = "Coin Market Cap"
        self.command_names = ['cmc', 'coinmarketcap']
        self.short_url = "https://bit.ly/1hJ8ztr"
        self.last_updated_time = 0
        self.update_failure_count = 0

        if currency_symbol == "ETH":
            self.currency_id = 1027
        elif currency_symbol == "BTC":
            self.currency_id = 1
        elif self.currency_symbol == '0xBTC':
            self.currency_id = 2837
        else:
            raise RuntimeError("unsupported currency, need to add currency_id to coinmarketcap.py")

    async def _update(self, timeout=10.0):
        method = "/ticker/{}".format(self.currency_id)

        data = await self._get_json_from_url(self._SERVER_URL+method)

        # CMC-only attributes; TODO: use market_cap in !market or something
        self.rank = int(data['data']['rank'])
        self.market_cap = float(data['data']['quotes']['USD']['market_cap'])

        self.price_usd = float(data['data']['quotes']['USD']['price'])

        # hack: only pull volume data for ETH and BTC, since they are usually
        # used as reference currencies only. The volume is ignored for other
        # currencies, since volume in this bot is defined as a per-exchange
        # volume, not an aggregate like CMC's api.
        if self.currency_symbol == "ETH" or self.currency_symbol == "BTC":
            self.volume_usd = float(data['data']['quotes']['USD']['volume_24h'])
            self.change_24h = float(data['data']['quotes']['USD']['percent_change_24h']) / 100.0

        if self.currency_symbol == "ETH":
            self.price_eth = 1
            self.eth_price_usd = self.price_usd
        
        if self.currency_symbol == "BTC":
            self.price_btc = 1
            self.btc_price_usd = self.price_usd

if __name__ == "__main__":
    eth_api = CoinMarketCapAPI('ETH')
    eth_api.load_once_and_print_values()
