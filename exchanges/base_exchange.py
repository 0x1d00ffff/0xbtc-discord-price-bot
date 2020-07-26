"""
Base exchange class
"""
import time
import socket
import websocket
from urllib.error import URLError
import datetime

import aiohttp
import asyncio

import json

from requests import Session
import logging


class BaseExchangeAPI():
    def __init__(self):
        self._SERVER_URL = ""
        self.currency_symbol = ""
        self.exchange_name = ""
        self.command_names = []
        self.short_url = ""
        self.last_updated_time = 0
        self.update_failure_count = 0

        self.price_eth = None
        self.price_usd = None
        self.price_btc = None
        self.volume_usd = None
        self.volume_eth = None
        self.volume_btc = None
        self.change_24h = None
        self.eth_price_usd = None
        self.btc_price_usd = None

    # TODO: make this function, use it in enclaves
    async def _get_json_from_websocket(self, url, commands):
        pass

    async def _get_json_via_get_request(self, url, parameters, headers):
        session = Session()
        session.headers.update(headers)

        try:
            response = session.get(url, params=parameters)
        except (ConnectionError, Timeout, TooManyRedirects) as e:
            raise TimeoutError("api is down - got timeout")
        finally:
            # close session to avoid ResourceWarning: unclosed <ssl.SSLSocket...
            session.close()

        try:
            data = json.loads(response.text)
        except json.decoder.JSONDecodeError:
            response = response[:2000]
            if ("be right back" in response
                or "404 Not Found" in response and "nginx" in response
                or "Request unsuccessful. Incapsula incident ID" in response):
                raise TimeoutError("api is down - got error page")
            else:
                raise TimeoutError("api sent bad data ({})".format(repr(response)))
        else:
            return data


    async def _get_json_from_url(self, url):
        async def fetch(session, url):
            async with session.get(url) as response:
                return await response.text()
        
        headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
        }
        async with aiohttp.ClientSession(headers=headers) as session:
            response = await fetch(session, url)

        try:
            data = json.loads(response)
        except json.decoder.JSONDecodeError:
            response = response[:2000]
            if ("be right back" in response
                or "404 Not Found" in response and "nginx" in response
                or "Request unsuccessful. Incapsula incident ID" in response):
                raise TimeoutError("api is down - got error page")
            else:
                raise TimeoutError("api sent bad data ({})".format(repr(response)))
        else:
            return data

    async def update(self, timeout=10.0):
        try:
            await self._update(timeout=timeout)
        except (websocket._exceptions.WebSocketTimeoutException,
                websocket._exceptions.WebSocketBadStatusException,
                websocket._exceptions.WebSocketAddressException,
                TimeoutError,
                ConnectionResetError,
                ConnectionRefusedError,
                socket.gaierror,
                socket.timeout,
                URLError) as e:
            self.update_failure_count += 1
            raise TimeoutError(str(e)) from e
        except Exception:
            self.update_failure_count += 1
            raise
        else:
            self.last_updated_time = time.time()
            self.update_failure_count = 0

    def print_all_values(self):
        print(self.exchange_name, self.currency_symbol, 'price_eth    ', self.price_eth)
        print(self.exchange_name, self.currency_symbol, 'price_btc    ', self.price_btc)
        print(self.exchange_name, self.currency_symbol, 'price_usd    ', self.price_usd)
        print(self.exchange_name, self.currency_symbol, 'volume_usd   ', self.volume_usd)
        print(self.exchange_name, self.currency_symbol, 'volume_eth   ', self.volume_eth)
        print(self.exchange_name, self.currency_symbol, 'volume_btc   ', self.volume_btc)
        print(self.exchange_name, self.currency_symbol, 'change_24h   ', self.change_24h)
        print(self.exchange_name, self.currency_symbol, 'eth_price_usd', self.eth_price_usd)
        print(self.exchange_name, self.currency_symbol, 'btc_price_usd', self.btc_price_usd)

    def load_once_and_print_values(self):
        async def load_once():
            await self.update()
        loop = asyncio.get_event_loop()
        loop.run_until_complete(load_once())
        self.print_all_values()


# Instance of BaseExchangeAPI which generates the change_24h property automatically
class Daily24hChangeTrackedAPI(BaseExchangeAPI):
    def __init__(self):
        super().__init__()
        # a list of price for each hour of the last 24 hours. last entry in the list is
        # the last hour's price, 2nd to last entry is price 2 hours ago, and so on. the
        # first entries in the list are removed to limit list size to 24, which keeps
        # the price from 24 hours ago in previous_hours_prices[0]
        self.previous_hours_prices = []
        # keep track of the current hour so it is easy to keep track of when it changes
        self.current_hour = None
        pass

    async def update(self, timeout=10.0):
        await super().update()
        await self.calculate_24h_change()

    async def calculate_24h_change(self):
        # pick a price to use. usd price change takes priority, followed by eth, then btc
        if self.price_usd is not None and self.price_usd != 0:
            price = self.price_usd
        elif self.price_eth is not None and self.price_eth != 0:
            price = self.price_eth
        elif self.price_btc is not None and self.price_btc != 0:
            price = self.price_btc
        else:
            logging.error('Fail to calculate change; had price update with no price? exchange_name: {}'.format(self.exchange_name))
            return

        current_hour = datetime.datetime.now().hour
        if self.current_hour != current_hour:
            self.previous_hours_prices.append(price)
            # trim the list so it keeps at most 24 entries
            self.previous_hours_prices = self.previous_hours_prices[-24:]
            self.current_hour = current_hour

        price_change_absolute = price - self.previous_hours_prices[0]
        price_change_percentage = price_change_absolute / self.previous_hours_prices[0]
        self.change_24h = price_change_percentage

