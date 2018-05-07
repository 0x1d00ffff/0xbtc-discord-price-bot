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
from multi_api_manager import MultiApiManager

_VERSION = "0.0.5"
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


def seconds_to_readable_time(seconds):
    if seconds < 60:
        return 'now'

    minutes = seconds / 60;
    if minutes < 60:
        return "{:.0f}m ago".format(minutes)

    return "{:.0f}h ago".format(minutes / 60)

def cmd_whitehouse():
    WHITEHOUSE_PRICE_USD = 398.8*1000*1000
    if apis.last_updated_time() == 0:
        return ":shrug:"

    return "1 whitehouse = {:,.0f} 0xBTC".format(WHITEHOUSE_PRICE_USD / (apis.price_eth('0xBTC') * apis.eth_price_usd()))


def cmd_lambo():
    LAMBO_PRICE_USD = 200000
    if apis.last_updated_time() == 0:
        return ":shrug:"

    return "1 lambo = {:,.0f} 0xBTC".format(LAMBO_PRICE_USD / (apis.price_eth('0xBTC') * apis.eth_price_usd()))


def cmd_price(source='all'):
    if apis.last_updated_time(api_name=source) == 0:
        return "not sure yet... waiting on my APIs :sob: [<https://bit.ly/2rnYA7b>]"
    
    percent_change_str = ""

    if apis.change_24h('0xBTC', api_name=source) == None:
        percent_change_str = ""
    else:
        # TODO: enable percentage once enclaves is stable
        # percent_change_str = "**{:+.2f}**%24h {} ".format(100.0 * apis.change_24h('0xBTC'),
        #                                                   percent_change_to_emoji(apis.change_24h('0xBTC')),)
        pass

    fmt_str = "{}{}: **${:.3f}** ({:.5f} Ξ) {}(ETH: **${:.0f}**) [<https://bit.ly/2rnYA7b>]"
    result = fmt_str.format('' if source == 'all' else '**{}** '.format(source),
                            seconds_to_readable_time(time.time()-apis.last_updated_time(api_name=source)),
                            apis.price_eth('0xBTC', api_name=source) * apis.eth_price_usd(), 
                            apis.price_eth('0xBTC', api_name=source), 
                            percent_change_str,
                            apis.eth_price_usd(api_name=source))
    return result


def cmd_bitcoinprice():
    if apis.last_updated_time() == 0:
        return "not sure yet... waiting on my APIs :sob: [<https://bit.ly/2w6Q0P0>]"

    fmt_str = "{}: **${:.0f}**"
    result = fmt_str.format(seconds_to_readable_time(time.time()-apis.last_updated_time()), apis.btc_price_usd())
    return result


def cmd_ratio():
    if apis.last_updated_time() == 0:
        return "not sure yet... waiting on my APIs :sob: [<https://bit.ly/2w6Q0P0>]"

    return "1 BTC : {:,.0f} 0xBTC".format(apis.btc_price_usd() / (apis.price_eth('0xBTC') * apis.eth_price_usd()))


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
            last_updated = time.time()
        except Exception as e:
            logging.exception('failed to update prices')
            #await update_status(client, "???")

        # wait until at least one successful update to show status
        if apis.last_updated_time() != 0:
            fmt_str = "${:.2f}  |  {:.5f} Ξ ({})"
            await update_status(client, fmt_str.format(apis.price_eth('0xBTC') * apis.eth_price_usd(),
                                                       apis.price_eth('0xBTC'),
                                                       seconds_to_readable_time(time.time()-last_updated)))

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
                    'enclaves']):
                msg = cmd_price(source="Enclaves DEX")
            elif any(s in message.content.lower() for s in [
                    'lcw', 
                    'livecoinwatch', 
                    'live coin watch']):
                msg = cmd_price(source="Live Coin Watch")
            else:
                msg = cmd_price()
            
            await client.send_message(message.channel, msg)

        if message.content.startswith('!ratio'):
            logging.info('got !ratio')
            msg = cmd_ratio()
            await client.send_message(message.channel, msg)

        if message.content.startswith('!bitcoinprice'):
            logging.info('got !bitcoinprice')
            msg = cmd_bitcoinprice()
            await client.send_message(message.channel, msg)

        if message.content.startswith('!lambo'):
            logging.info('got !lambo')
            msg = cmd_lambo()
            await client.send_message(message.channel, msg)

        if message.content.startswith('!whitehouse'):
            logging.info('got !whitehouse')
            msg = cmd_whitehouse()
            await client.send_message(message.channel, msg)

        if message.content.startswith('!help'):
            logging.info('got !help')
            msg = "available commands: `price ratio bitcoinprice lambo whitehouse`"
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
