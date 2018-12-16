"""
Base exchange class
"""
import time
import socket
import websocket
from urllib.error import URLError

import aiohttp
import asyncio

import json


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
