import time
import logging
import aiohttp

from async_url_helpers import get_json_from_url

# data older than this is completely ignored
_OLDEST_ALLOWED_DATA_SECONDS = 300  # 5 minutes


async def get_gas_price():

    oracles = (
        ("https://owlracle.info/eth/gas",
            lambda j: j["speeds"][2]['gasPrice']),
        ("https://ethgas.watch/api/gas",
            lambda j: j["fast"]["gwei"]),
        ("https://data-api.defipulse.com/api/v1/egs/api/ethgasAPI.json?api-key=53be2a60f8bc0bb818ad161f034286d709a9c4ccb1362054b0543df78e27",
            lambda j: float(j["fast"]) / 10.0),
    )

    prices = []

    for url, parser_fn in oracles:
        try:
            prices.append(parser_fn(await get_json_from_url(url)))
        except:
            logging.exception(f"fail to fetch gas price from {url}")

    if len(prices) == 0:
        raise RuntimeError("no gas oracles responding")

    # average all the prices
    return sum(prices) / len(prices)


class GasPriceAPI():
    def __init__(self):
        self._gas_price = None
        self._time_last_updated = 0

    async def update(self):
        self._gas_price = await get_gas_price()
        self._time_last_updated = time.time()

    @property
    def gas_price(self):
        if time.time() - self._time_last_updated > _OLDEST_ALLOWED_DATA_SECONDS:
            return None
        else:
            return self._gas_price


async def load_once_and_print():
    api = GasPriceAPI()
    await api.update()
    print(f"gas_price: {api.gas_price}")

if __name__ == "__main__":
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(load_once_and_print())

