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
from livecoinwatch import get_coin_price
from enclavesdex import EnclavesAPI

_VERSION = "0.0.2"
_UPDATE_RATE = 120

# todo: encapsulate these
bitcoin_price = 0
price_in_usd, price_in_eth, eth_price = 0, 0, 0
last_updated = 0
enclaves = EnclavesAPI()

client = None


def percent_change_to_emoji(percent_change):
    values = [
        # [0.3, ":arrow_up:"],
        # [0.1, ":arrow_upper_right:"],
        # [-0.1, ":arrow_right:"],
        # [-0.3, ":arrow_lower_right:"],
        # [-1, ":arrow_down:"],
        [0.3, ":chart_with_upwards_trend:"],
        [0.1, ":chart_with_upwards_trend:"],
        [-0.1, ""],
        [-0.3, ":chart_with_downwards_trend:"],
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
    if last_updated == 0:
        return ":shrug:"

    return "1 whitehouse = {:,.0f} 0xBTC".format(WHITEHOUSE_PRICE_USD / (enclaves.oxbtc_price_eth * eth_price))


def cmd_lambo():
    LAMBO_PRICE_USD = 200000
    if last_updated == 0:
        return ":shrug:"

    return "1 lambo = {:,.0f} 0xBTC".format(LAMBO_PRICE_USD / (enclaves.oxbtc_price_eth * eth_price))


def cmd_price():
    if last_updated == 0:
        return "not sure yet... waiting on my APIs :sob: [<https://bit.ly/2rnYA7b>]"

    fmt_str = "{}: **${:.3f}** ({:.5f} Ξ) **{:+.2f}**%24h {} (ETH: **${:.0f}**) [<https://bit.ly/2rnYA7b>]"
    result = fmt_str.format(seconds_to_readable_time(time.time()-last_updated),
                            enclaves.oxbtc_price_eth * eth_price, 
                            enclaves.oxbtc_price_eth, 
                            enclaves.oxbtc_24h_change,
                            percent_change_to_emoji(enclaves.oxbtc_24h_change),
                            eth_price)
    return result


def cmd_bitcoinprice():
    if last_updated == 0:
        return "not sure yet... waiting on my APIs :sob: [<https://bit.ly/2w6Q0P0>]"

    fmt_str = "{}: **${:.0f}**"
    result = fmt_str.format(seconds_to_readable_time(time.time()-last_updated), bitcoin_price)
    return result


def cmd_ratio():
    if last_updated == 0:
        return "not sure yet... waiting on my APIs :sob: [<https://bit.ly/2w6Q0P0>]"

    return "1 BTC : {:,.0f} 0xBTC".format(bitcoin_price / (enclaves.oxbtc_price_eth * eth_price))


async def update_status(client, stat_str):
    logging.info('changing status to {}'.format(repr(stat_str)))
    await client.change_presence(game=discord.Game(name=stat_str),
                                 status=discord.Status('online'),
                                 afk=False)


async def update_price_task():
    global price_in_usd, price_in_eth, eth_price, bitcoin_price, last_updated
    await client.wait_until_ready()
    while not client.is_closed:
        try:
            price_in_usd, price_in_eth, eth_price = get_coin_price('0xBTC')
            bitcoin_price, _, _ = get_coin_price('BTC')
            enclaves.update()
            last_updated = time.time()
        except Exception as e:
            logging.exception('failed to update prices')
            #await update_status(client, "???")

        # wait until at least one successful update to show status
        if last_updated != 0:
            fmt_str = "${:.2f}  |  {:.5f} Ξ ({})"
            await update_status(client, fmt_str.format(enclaves.oxbtc_price_eth * eth_price,
                                                       enclaves.oxbtc_price_eth,
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
            logging.info('got !price')
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
    while True:
        try:
            loop.run_until_complete(client.start(TOKEN))
            # client.run(TOKEN)
        except SystemExit:
            raise
        except KeyboardInterrupt:
            raise
        except:
            logging.exception('bot ded:')
            time.sleep(5)  # wait a little time to prevent cpu spins
