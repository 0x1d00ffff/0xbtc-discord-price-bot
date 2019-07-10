from .base_exchange import BaseExchangeAPI

class MerkleXAPI(BaseExchangeAPI):
    def __init__(self, currency_symbol):
        super().__init__()

        self._SERVER_URL = "https://api.merklex.io"
        self.currency_symbol = currency_symbol
        self.exchange_name = "merkleX"
        self.command_names = ['merkleX', 
                              'merklex', 
                              'merkelx', 
                              'mx']
        self.short_url = "http://bit.ly/2G21Axc"

    async def _update(self, timeout=10.0):
        method = "/markets/%s-DAI/stats" % self.currency_symbol
        data = await self._get_json_from_url(self._SERVER_URL+method)

        try:
            self.price_usd = float(data['last_trade']['price'])
            self.volume_usd = float(data['volume']['quote_volume_24h'])
        except TypeError as e:
            raise TimeoutError("Could not convert data to float") from e

if __name__ == "__main__":
    api = MerkleXAPI('0xBTC')
    api.load_once_and_print_values()

