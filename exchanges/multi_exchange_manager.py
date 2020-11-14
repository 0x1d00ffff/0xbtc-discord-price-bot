""" Manage multiple apis at once - allows calculating better values by
incorporating multiple sources. """

import time
import logging
import asyncio

from configuration import UPDATE_RATE
from weighted_average import WeightedAverage

# data older than this is completely ignored
_OLDEST_ALLOWED_DATA_SECONDS = UPDATE_RATE * 3

class MultiExchangeManager():
    def __init__(self, api_obj_list):
        self.api_obj_list = api_obj_list

    async def update(self):
        for api_obj in self.api_obj_list:
            report_success = api_obj.update_failure_count >= 2
            try:
                if asyncio.iscoroutinefunction(api_obj.update):
                    await api_obj.update()
                else:
                    api_obj.update()
            except TimeoutError as e:
                fmt_str = "Timeout {}: {}. Silencing until exchange is up again."
                logging.debug(fmt_str.format(api_obj.exchange_name,
                                               str(e)))
                # ignore a single failure, but log 2 in a row
                if api_obj.update_failure_count == 2:
                    logging.warning(fmt_str.format(api_obj.exchange_name,
                                                   str(e)))
            except:
                logging.exception(f"Unhandled Exception updating {api_obj.exchange_name}")
            else:
                if report_success:
                    logging.info(f"Exchange {api_obj.exchange_name} is back up")

    @property
    def all_exchanges(self):
        return self.api_obj_list

    @property
    def alive_exchanges(self):
        time_now = time.time()
        for a in self.api_obj_list:
            # skip apis that have never been updated
            if a.last_updated_time == None or a.last_updated_time == 0:
                continue
            # skip apis that have too old/stale data
            if time_now - a.last_updated_time > _OLDEST_ALLOWED_DATA_SECONDS:
                continue
            yield a

    @property
    def alive_api_names(self):
        all_names = []
        for a in self.alive_exchanges:
            all_names.append(a.exchange_name)

        # convert to set to remove duplicates 
        return list(set(all_names))

    def short_url(self, exchange_name='aggregate'):
        default_url = "https://bit.ly/35nae4n"  # uniswap v2
        if exchange_name == "aggregate":
            return default_url

        for a in self.api_obj_list:
            if a.exchange_name == exchange_name:
                return a.short_url
        return default_url

    def price_eth(self, currency_symbol, exchange_name='aggregate'):
        result = WeightedAverage()
        for a in self.alive_exchanges:
            if a.currency_symbol != currency_symbol:
                continue
            if a.price_eth == None:
                continue
            if a.volume_eth == None:
                # use 0 eth as fallback so it does not affect weighted price
                volume = 0
            else:
                volume = a.volume_eth
            if exchange_name == 'aggregate' or a.exchange_name == exchange_name:
                result.add(a.price_eth, volume)
        return result.average()

    def price_usd(self, currency_symbol, exchange_name='aggregate'):
        result = WeightedAverage()
        for a in self.alive_exchanges:
            if a.currency_symbol != currency_symbol:
                continue
            if a.price_usd == None:
                continue
            if a.volume_usd == None:
                volume = 0
            else:
                volume = a.volume_usd
            if exchange_name == 'aggregate' or a.exchange_name == exchange_name:
                result.add(a.price_usd, volume)
        return result.average()

    def volume_usd(self, currency_symbol, exchange_name='aggregate'):
        result = 0
        for a in self.alive_exchanges:
            if a.currency_symbol != currency_symbol:
                continue
            if a.volume_usd == None:
                continue
            if exchange_name == 'aggregate' or a.exchange_name == exchange_name:
                result += a.volume_usd
        return result

    def volume_eth(self, currency_symbol, exchange_name='aggregate'):
        result = 0
        for a in self.alive_exchanges:
            if a.currency_symbol != currency_symbol:
                continue
            if a.volume_eth == None:
                continue
            if exchange_name == 'aggregate' or a.exchange_name == exchange_name:
                result += a.volume_eth
        return result

    def volume_btc(self, currency_symbol, exchange_name='aggregate'):
        result = 0
        for a in self.alive_exchanges:
            if a.currency_symbol != currency_symbol:
                continue
            if a.volume_btc == None:
                continue
            if exchange_name == 'aggregate' or a.exchange_name == exchange_name:
                result += a.volume_btc
        return result

    def change_24h(self, currency_symbol, exchange_name='aggregate'):
        result = WeightedAverage()
        for a in self.alive_exchanges:
            if a.currency_symbol != currency_symbol:
                continue
            if a.change_24h == None:
                continue
            if a.volume_eth == None:
                # use 0 eth as fallback so it does not affect average
                volume = 0
            else:
                volume = a.volume_eth
            if exchange_name == 'aggregate' or a.exchange_name == exchange_name:
                result.add(a.change_24h, volume)
        return result.average()

    def rank(self, currency_symbol, exchange_name='aggregate'):
        result = None
        for a in self.alive_exchanges:
            if a.currency_symbol != currency_symbol:
                continue
            if exchange_name == 'aggregate' or a.exchange_name == exchange_name:
                try:
                    result = a.rank
                except AttributeError:
                    pass
        return result

    def eth_price_usd(self, exchange_name='aggregate'):
        result = WeightedAverage()
        for a in self.alive_exchanges:
            if a.eth_price_usd == None:
                continue
            if exchange_name == 'aggregate' or a.exchange_name == exchange_name:
                if a.currency_symbol == 'ETH':
                    result.add(a.price_usd, a.volume_usd / a.price_usd)
                else:
                    result.add(a.eth_price_usd, a.volume_eth)
        return result.average()

    def btc_price_usd(self, exchange_name='aggregate'):
        result = WeightedAverage()
        for a in self.alive_exchanges:
            if a.btc_price_usd == None:
                continue
            if exchange_name == 'aggregate' or a.exchange_name == exchange_name:
                if a.currency_symbol == 'BTC':
                    result.add(a.price_usd, a.volume_usd / a.price_usd)
                else:
                    result.add(a.btc_price_usd, a.volume_btc)
        return result.average()

    def last_updated_time(self, exchange_name='aggregate'):
        result = 0
        for a in self.alive_exchanges:
            if exchange_name == 'aggregate' or a.exchange_name == exchange_name:
                # use the lowest last_updated time
                #if result == 0 or a.last_updated_time < result:
                # use the highest last_updated time as a hack for how
                if result == 0 or a.last_updated_time > result:
                    result = a.last_updated_time
        return result

    def previous_hours_prices(self, currency_symbol, exchange_name='aggregate'):
        result = 0
        for a in self.alive_exchanges:
            if a.currency_symbol != currency_symbol:
                continue
            if exchange_name == 'aggregate' or a.exchange_name == exchange_name:
                # if aggregate, return the first exchange we find with previous prices
                try:
                    return a.previous_hours_prices
                except AttributeError:
                    # skip exchanges without previous price history
                    pass
        return None


if __name__ == "__main__":
    from .coinmarketcap import CoinMarketCapAPI
    from .enclavesdex import EnclavesAPI
    from .livecoinwatch import LiveCoinWatchAPI
    from .forkdelta import ForkDeltaAPI
    from .mercatox import MercatoxAPI

    apis = [
        EnclavesAPI('0xBTC'), 
        ForkDeltaAPI('0xBTC'),
        MercatoxAPI('0xBTC'),
        CoinMarketCapAPI('BTC'),
        CoinMarketCapAPI('ETH')
    ]

    m = MultiExchangeManager(apis)
    m.update()

    print("m.eth_price_usd()", m.eth_price_usd())
    print("m.btc_price_usd()", m.btc_price_usd())

    print("m.price_eth('0xBTC')", m.price_eth('0xBTC'))
    print("m.price_usd('0xBTC')", m.price_usd('0xBTC'))
    print("m.volume_usd('0xBTC')", m.volume_usd('0xBTC'))
    print("m.volume_eth('0xBTC')", m.volume_eth('0xBTC'))
    print("m.volume_btc('0xBTC')", m.volume_btc('0xBTC'))
    print("m.change_24h('0xBTC')", m.change_24h('0xBTC'))

    print("m.change_24h('0xBTC', exchange_name='Mercatox')",      m.change_24h('0xBTC', exchange_name='Mercatox'))

