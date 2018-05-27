# -*- coding: UTF-8 -*-

# https://github.com/Rapptz/discord.py/blob/async/examples/reply.py
"""

livecoinwatch bitly: https://bit.ly/2w6Q0P0
enclaves bitly: https://bit.ly/2rnYA7b
"""

import time
import socket
import websocket
import asyncio
import logging
import urllib

import discord
from secret_info import TOKEN
from reconnecting_bot import keep_running
from enclavesdex import EnclavesAPI
from livecoinwatch import LiveCoinWatchAPI
from mercatox import MercatoxAPI
from multi_api_manager import MultiApiManager

_VERSION = "0.0.12"
_UPDATE_RATE = 120

# todo: encapsulate these
#bitcoin_price = 0
#price_in_usd, price_in_eth, apis.eth_price_usd() = 0, 0, 0
last_updated = 0
#enclaves = EnclavesAPI()

client = None


def percent_change_to_emoji(percent_change):
    values = [
        # [0.3, ":arrow_up:"],
        # [0.1, ":arrow_upper_right:"],
        # [-0.1, ":arrow_right:"],
        # [-0.3, ":arrow_lower_right:"],
        # [-1, ":arrow_down:"],
        [0.3, ":chart_with_upwards_trend:"],
        [0.1, ""],
        [-0.1, ""],
        [-0.3, ""],
        [-1, ":chart_with_downwards_trend:"],
    ]
    for v in values:
        if percent_change > v[0]:
            return v[1]
    # return the last option as fallback
    return values[-1:][0][1]


def prettify_decimals(number):
    if number < 0.00001:
        return "{:.8f}".format(number)
    elif number < 0.001:
        return "{:.5f}".format(number)
    elif number < 1.0:
        return "{:.3f}".format(number)
    elif number < 1000.0:
        return "{:.2f}".format(number)
    elif number < 100000.0:
        return "{:.1f}".format(number)

    return "{:.0f}".format(number)

def to_readable_thousands(value):
    units = ['', 'k', 'm', 'b'];

    for unit in units:
        if value < 1000:
            return "{:.1f}{}".format(value, unit)
        value /= 1000

    return "{:.1f}{}".format(value, 't')

def seconds_to_readable_time(seconds):
    if seconds < 60:
        return 'now'

    minutes = seconds / 60;
    if minutes < 60:
        return "{:.0f}m ago".format(minutes)

    return "{:.0f}h ago".format(minutes / 60)

def cmd_compare_price_vs(item_name="lambo", item_price=200000):
    if apis.last_updated_time() == 0:
        return ":shrug:"

    token_price_usd = apis.price_eth('0xBTC') * apis.eth_price_usd()

    if token_price_usd == 0:
        return ":shrug:"

    return "1 {} = **{:,.0f}** 0xBTC (${})".format(item_name, item_price / token_price_usd, to_readable_thousands(item_price))


def cmd_price(source='aggregate'):
    if apis.last_updated_time(api_name=source) == 0:
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(apis.short_url(api_name=source))
    
    token_price = apis.price_eth('0xBTC', api_name=source) * apis.eth_price_usd()
    eth_price = float(apis.eth_price_usd(api_name=source))

    percent_change_str = ""

    if apis.change_24h('0xBTC', api_name=source) == None:
        percent_change_str = ""
    else:
        # TODO: enable percentage once enclaves is stable
        percent_change_str = "**{:+.2f}**% {} ".format(100.0 * apis.change_24h('0xBTC', api_name=source),
                                                       percent_change_to_emoji(apis.change_24h('0xBTC', api_name=source)),)
        pass

    fmt_str = "{}{}: {}({:.5f} Ξ) {}{}[<{}>]"
    result = fmt_str.format('' if source == 'aggregate' else '**{}** '.format(source),
                            seconds_to_readable_time(time.time()-apis.last_updated_time(api_name=source)),
                            '' if token_price == 0 else '**${:.3f}** '.format(token_price), 
                            apis.price_eth('0xBTC', api_name=source), 
                            percent_change_str,
                            '' if eth_price == 0 else '(ETH: **${:.0f}**) '.format(eth_price), 
                            apis.short_url(api_name=source))
    return result


def cmd_bitcoinprice():
    if apis.last_updated_time() == 0:
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(apis.short_url())

    if apis.btc_price_usd() == 0:
        return ":shrug:"

    fmt_str = "{}: **${:.0f}**"
    result = fmt_str.format(seconds_to_readable_time(time.time()-apis.last_updated_time()), apis.btc_price_usd())
    return result


def cmd_ratio():
    if apis.last_updated_time() == 0:
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(apis.short_url())

    token_price_usd = apis.price_eth('0xBTC') * apis.eth_price_usd()

    if token_price_usd == 0:
        return ":shrug:"

    return "1 BTC : {:,.0f} 0xBTC".format(apis.btc_price_usd() / token_price_usd)

def cmd_convert(message):
    if apis.last_updated_time() == 0:
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(apis.short_url())

    try:
        _, amount, src, _, dest = message.split(' ')
        src = src.lower()
        dest = dest.lower()
        amount = float(amount)
    except:
        return "Bad formatting? try this : `!convert 1 eth to 0xbtc`"

    token_price_usd = apis.price_eth('0xBTC') * apis.eth_price_usd()


    if src == '0xbtc':
        usd_value = token_price_usd * amount
    elif src == 'eth':
        usd_value = apis.eth_price_usd() * amount
    elif src == 'btc':
        usd_value = apis.btc_price_usd() * amount
    elif src == 'mbtc':
        usd_value = apis.btc_price_usd() * amount / 1000.0
    elif src == 'usd':
        usd_value = amount
    else:
        return "Bad source currency ({}). 0xbtc, eth, mbtc, btc, and usd are supported.".format(src)

    if dest == '0xbtc':
        result = usd_value / token_price_usd
    elif dest == 'eth':
        result = usd_value / apis.eth_price_usd()
    elif dest == 'btc':
        result = usd_value / apis.btc_price_usd()
    elif dest == 'mbtc':
        result = usd_value * 1000.0 / apis.btc_price_usd()
    elif dest == 'usd':
        result = usd_value
    else:
        return "Bad destination currency ({}). 0xbtc, eth, mbtc, btc, and usd are supported.".format(src)

    amount = prettify_decimals(amount)
    result = prettify_decimals(result)

    return "{} {} = **{}** {}".format(amount, src, result, dest)


async def update_status(client, stat_str):
    logging.info('changing status to {}'.format(repr(stat_str)))
    await client.change_presence(game=discord.Game(name=stat_str),
                                 status=discord.Status('online'),
                                 afk=False)


async def update_price_task():
    global last_updated
    await client.wait_until_ready()
    while not client.is_closed:
        try:
            apis.update()
            #last_updated = time.time()
        except Exception as e:
            logging.exception('failed to update prices')
            #await update_status(client, "???")

        # price in usd is conritional - only show it if eth price is not 0 (an error)
        price_usd = apis.price_eth('0xBTC') * apis.eth_price_usd()
        usd_str = "" if price_usd == 0 else "${:.2f}  |  ".format(price_usd)

        # wait until at least one successful update to show status
        if apis.last_updated_time() != 0:
            fmt_str = "{}{:.5f} Ξ ({})"
            await update_status(client, fmt_str.format(usd_str,
                                                       apis.price_eth('0xBTC'),
                                                       seconds_to_readable_time(time.time()-apis.last_updated_time())))

        await asyncio.sleep(_UPDATE_RATE)


def configure_client():
    #client = discord.Client()

    @client.event
    async def on_message(message):
        # we do not want the bot to reply to itself
        if message.author == client.user:
            return
        # we do not want the bot to reply to other bots
        if message.author.bot:
            return

        if message.content.startswith('!price'):
            logging.info('got !price ({})'.format(message.content))
            if any(s in message.content.lower() for s in [
                    'enclaves',
                    'encalves']):
                msg = cmd_price(source="Enclaves DEX")
            elif any(s in message.content.lower() for s in [
                    'lcw', 
                    'livecoinwatch', 
                    'live coin watch']):
                msg = cmd_price(source="Live Coin Watch")
            elif any(s in message.content.lower() for s in [
                    'merc', 
                    'mercatox', 
                    'meractox', 
                    'mecratox']):
                msg = cmd_price(source="Mercatox")
            elif any(s in message.content.lower() for s in [
                    'all']):
                msg = '\n'.join([cmd_price(source="Enclaves DEX"),
                                 cmd_price(source="Live Coin Watch"),
                                 cmd_price(source="Mercatox")])
            else:
                msg = cmd_price()
            
            await client.send_message(message.channel, msg)

        if message.content.lower().startswith('!ratio'):
            logging.info('got !ratio')
            msg = cmd_ratio()
            await client.send_message(message.channel, msg)

        if message.content.lower().startswith('!bitcoinprice'):
            logging.info('got !bitcoinprice')
            msg = cmd_bitcoinprice()
            await client.send_message(message.channel, msg)

        if message.content.lower().startswith('!convert'):
            logging.info('got !convert ({})'.format(message.content))
            msg = cmd_convert(message.content)
            await client.send_message(message.channel, msg)

        expensive_stuff = [
            ('lambo',           400000),
            ('used_lambo',      200000),
            ('privateisland',   500000),
            ('whitehouse',      398.8*1000*1000),
            ('tesla',           101500),
            ('usedfordtaurus',  1700),
            ('thousandaire',    1e3),
            ('millionaire',     1e6),
            ('billionaire',     1e9),
        ]
        for name, price in expensive_stuff:
            if message.content.lower().startswith('!' + name):
                logging.info('got !{}'.format(name))
                msg = cmd_compare_price_vs(name, price)
                await client.send_message(message.channel, msg)

        if message.content.lower().startswith('!help'):
            logging.info('got !help')
            msg = "available commands: `price ratio convert bitcoinprice lambo privateisland whitehouse millionaire billionaire`"
            await client.send_message(message.channel, msg)

        #if message.content.startswith('!volume'):
        #    msg = cmd_price()
        #    await client.send_message(message.channel, msg)

        #if message.content.startswith('!hello'):
        #    msg = 'Hello {0.author.mention}'.format(message)
        #    await client.send_message(message.channel, msg)

    @client.event
    async def on_ready():
        logging.info('Logged in as {} ({})'.format(client.user.name,
                                                   client.user.id))

    client.loop.create_task(update_price_task())


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format= '[%(asctime)s.%(msecs)03d] %(levelname)s - %(message)s',
        datefmt='%H:%M:%S')
    logging.info('0xbtc-price-bot start v{}'.format(_VERSION))
    loop = asyncio.get_event_loop()
    client = discord.Client()
    configure_client()
    apis = MultiApiManager(
    [
        EnclavesAPI('0xBTC'), 
        LiveCoinWatchAPI('0xBTC'),
        LiveCoinWatchAPI('ETH'),
        MercatoxAPI('0xBTC'),
    ])
    while True:
        try:
            asyncio.get_event_loop().run_until_complete(keep_running(client, TOKEN))
            # loop.run_until_complete(client.start(TOKEN))
            # client.run(TOKEN)
        except SystemExit:
            raise
        except KeyboardInterrupt:
            raise
        except:
            logging.exception('bot ded:')
            time.sleep(10)  # wait a little time to prevent cpu spins
