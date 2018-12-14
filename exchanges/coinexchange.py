"""
API for CoinExchange (coinexchange.io)

TODO: can't track eth or btc directly because it loads currency vs both eth and
      btc.. and there are no eth/eth pairs

GET https://www.coinexchange.io/api/v1/getmarkets

{
    "success": "1",
    "request": "/api/v1/public/getmarkets",
    "message": "",
    "result": [
    {

        "MarketID": "1",
        "MarketAssetName": "Megacoin",
        "MarketAssetCode": "MEC",
        "MarketAssetID": "3",
        "MarketAssetType": "currency",
        "BaseCurrency": "Bitcoin",
        "BaseCurrencyCode": "BTC",
        "BaseCurrencyID": "1",
        "Active": true

    },
    {

        "MarketID": "3",
        "MarketAssetName": "Litecoin",
        "MarketAssetCode": "LTC",
        "MarketAssetID": "2",
        "MarketAssetType": "currency",
        "BaseCurrency": "Bitcoin",
        "BaseCurrencyCode": "BTC",
        "BaseCurrencyID": "1",
        "Active": true

    }
    ]
}


GET https://www.coinexchange.io/api/v1/getmarketsummaries

{
    "success": "1",
    "request": "/api/v1/public/getmarketsummaries",
    "message": "",
    "result": [
    {
        "MarketID": "1",
        "LastPrice": "0.00902321",
        "Change": "2.01",
        "HighPrice": "0.00961681",
        "LowPrice": "0.00853751",
        "Volume": "3043.78746852",
        "BTCVolume": "3043.78746852",
        "TradeCount": "1332",
        "BidPrice": "0.00902321",
        "AskPrice": "0.00928729",
        "BuyOrderCount": "7796",
        "SellOrderCount": "7671"
    },
    {
        "MarketID": "3",
        "LastPrice": "0.05000000",
        "Change": "0.00",
        "HighPrice": "0.00000000",
        "LowPrice": "0.00000000",
        "Volume": "0.00000000",
        "BTCVolume": "0.00000000",
        "TradeCount": "0",
        "BidPrice": "0.00000000",
        "AskPrice": "0.02000000",
        "BuyOrderCount": "0",
        "SellOrderCount": "1"
    }
    ]
}
"""
from .base_exchange import BaseExchangeAPI
from weighted_average import WeightedAverage


class CoinExchangeAPI(BaseExchangeAPI):
    def __init__(self, currency_symbol):
        super().__init__()
        self._SERVER_URL = "https://www.coinexchange.io/api/v1"
        self.currency_symbol = currency_symbol
        self.exchange_name = "Coin Exchange"
        self.command_names = ['coin exchange']
        self.short_url = "https://bit.ly/2zPcVgZ"
        self.last_updated_time = 0
        self.update_failure_count = 0
        self.market_id_vs_eth = None
        self.market_id_vs_btc = None
        self.market_id_eth_btc = None

    async def _get_market_id(self, asset_code, currency_code):
        """Get market ID for the given asset code ("0xBTC", "LTC", etc) and 
        currency code ("BTC", "ETH", etc)"""
        data = await self._get_json_from_url(self._SERVER_URL+"/getmarkets")

        for element in data["result"]:
            if (element["MarketAssetCode"] == asset_code
                and element["BaseCurrencyCode"] == currency_code):
                return element["MarketID"]

        return None

    async def _fetch_market_data(self, market_id):
        method = "/getmarketsummary?market_id={}".format(market_id)
        data = await self._get_json_from_url(self._SERVER_URL+method)
        return (float(data["result"]["LastPrice"]), 
                float(data["result"]["Volume"]), 
                float(data["result"]["Change"]) / 100.0)

    async def _update(self, timeout=10.0):
        if self.market_id_vs_eth is None:
            self.market_id_vs_eth = await self._get_market_id(self.currency_symbol, "ETH")
        if self.market_id_vs_btc is None:
            self.market_id_vs_btc = await self._get_market_id(self.currency_symbol, "BTC")
        if self.market_id_eth_btc is None:
            self.market_id_eth_btc = await self._get_market_id("ETH", "BTC")

        if self.market_id_vs_eth is None or self.market_id_vs_btc is None:
            raise RuntimeError("Failed to get market ids for asset code '{}'".format(self.currency_symbol))

        # grab market data for the desired currency vs ETH and BTC
        self.price_eth, self.volume_eth, change_eth = await self._fetch_market_data(self.market_id_vs_eth)
        self.price_btc, self.volume_btc, change_btc = await self._fetch_market_data(self.market_id_vs_btc)

        # grab market data for ETH/BTC so we can interpret relative data
        eth_price_in_btc, _, _ = await self._fetch_market_data(self.market_id_eth_btc)

        if self.volume_btc == 0:
            ratio_of_eth_vs_btc_volume = 100000
        else:
            ratio_of_eth_vs_btc_volume = self.volume_eth / (self.volume_btc / eth_price_in_btc)

        average = WeightedAverage()
        average.add(change_eth, ratio_of_eth_vs_btc_volume)
        average.add(change_btc, 1)
        self.change_24h = average.average()

if __name__ == "__main__":
    eth_api = CoinExchangeAPI('0xBTC')
    eth_api.load_once_and_print_values()
