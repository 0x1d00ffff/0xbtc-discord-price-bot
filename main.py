# -*- coding: UTF-8 -*-

# https://github.com/Rapptz/discord.py/blob/async/examples/reply.py

import time
import socket
import websocket
import asyncio
import logging
import urllib

import discord
from secret_info import TOKEN
from livecoinwatch import get_coin_price

_VERSION = "0.0.1"

# todo: encapsulate these
bitcoin_price = 0
price_in_usd, price_in_eth, eth_price = 0, 0, 0
last_updated = 0

client = None


def seconds_to_readable_time(seconds):
    if seconds < 60:
        return 'now'

    minutes = seconds / 60;
    if minutes < 60:
        return "{:.0f}m ago".format(minutes)

    return "{:.0f}h ago".format(minutes / 60)

def cmd_lambo():
    LAMBO_PRICE_USD = 200000
    if last_updated == 0:
        return ":shrug:"

    return "1 lambo = {:,.0f} 0xBTC".format(LAMBO_PRICE_USD / price_in_usd)


def cmd_price():
    if last_updated == 0:
        return "sorry.. livecoinwatch won't tell me :sob: [<https://bit.ly/2w6Q0P0>]"

    fmt_str = "latest: **${:.3f}** ({:.5f} Ξ) (ETH: **${:.0f}**) [<https://bit.ly/2w6Q0P0>] ({})"
    result = fmt_str.format(price_in_usd, price_in_eth, eth_price, seconds_to_readable_time(time.time()-last_updated))
    return result


def cmd_bitcoinprice():
    if last_updated == 0:
        return "sorry.. livecoinwatch won't tell me :sob: [<https://bit.ly/2w6Q0P0>]"

    fmt_str = "latest: **${:.0f}** ({})"
    result = fmt_str.format(bitcoin_price, seconds_to_readable_time(time.time()-last_updated))
    return result


def cmd_ratio():
    if last_updated == 0:
        return ":shrug:"

    return "1 BTC : {:,.0f} 0xBTC".format(bitcoin_price / price_in_usd)


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
            last_updated = time.time()
        except Exception as e:
            logging.exception('failed to update prices')
            #await update_status(client, "???")

        # wait until at least one successful update to show status
        if last_updated != 0:
            fmt_str = "${:.2f}  |  {:.5f} Ξ ({})"
            await update_status(client, fmt_str.format(price_in_usd, 
                                                       price_in_eth,
                                                       seconds_to_readable_time(time.time()-last_updated)))

        await asyncio.sleep(60) # task runs every 60 seconds


def main():
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

        if message.content.startswith('!help'):
            logging.info('got !help')
            msg = "available commands: `price ratio bitcoinprice lambo`"
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
    client.run(TOKEN)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format= '[%(asctime)s.%(msecs)03d] %(levelname)s - %(message)s',
        datefmt='%H:%M:%S')
    logging.info('0xbtc-price-bot start v{}'.format(_VERSION))
    while True:
        try:
            client = discord.Client()
            main()
        except SystemExit:
            pass
        except KeyboardInterrupt:
            pass
        except Exception as e:
            logging.error('bot ded: {}'.format(e))
            time.sleep(5)  # wait a little time to prevent cpu spins
