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


def cmd_price():
    result = "sorry.. livecoinwatch won't tell me :sob: [<https://bit.ly/2w6Q0P0>]"

    try:
        price_in_usd, price_in_eth, eth_price = get_coin_price('0xBTC')
    except TimeoutError:
        pass
    except ConnectionResetError:
        pass
    except socket.gaierror:
        pass
    except socket.timeout:
        pass
    except urllib.error.URLError:
        pass
    #except websocket._exceptions.WebSocketAddressException:
    #    pass
    #except websocket._exceptions.WebSocketConnectionClosedException:
    #    pass
    except ConnectionRefusedError:
        pass
    except KeyError:
        pass
    else:
        fmt_str = "latest: **${:.3f}** ({:.5f} Ξ) (ETH: **${:.0f}**) [<https://bit.ly/2w6Q0P0>]"
        result = fmt_str.format(price_in_usd, price_in_eth, eth_price)

    return result


async def update_status(client, stat_str):
    logging.info('changing status to {}'.format(stat_str))
    await client.change_presence(game=discord.Game(name=stat_str),
                                 status=discord.Status('online'),
                                 afk=False)


# def update_status(stat_str, url="https://bit.ly/2w6Q0P0"):
#     logging.info('changing status to', stat_str)
#     yield from client.change_presence(
#         game=discord.Game(name=stat_str))


async def price_in_status_task():
    await client.wait_until_ready()
    while not client.is_closed:
        try:
            price_in_usd, price_in_eth, eth_price = get_coin_price('0xBTC')
        except:
            await update_status(client, "???")
        else:
            await update_status(client, "${:.3f}  |  {:.5f} Ξ".format(price_in_usd, price_in_eth))

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

    client.loop.create_task(price_in_status_task())
    client.run(TOKEN)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format= '[%(asctime)s.%(msecs)03d] %(levelname)s - %(message)s',
        datefmt='%H:%M:%S')
    while True:
        try:
            client = discord.Client()
            main()
        except SystemExit:
            pass
        except KeyboardInterrupt:
            pass
        except Exception as e:
            logging.error('bot ded: {}', str(e))
            time.sleep(5)  # wait a little time to prevent cpu spins