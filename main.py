# -*- coding: UTF-8 -*-

# https://github.com/Rapptz/discord.py/blob/async/examples/reply.py

import socket
import websocket

import discord
from secret_info import TOKEN
from livecoinwatch import get_coin_price

def cmd_price():
    try:
        price_in_usd, price_in_eth, eth_price = get_coin_price('0xBTC')
    except TimeoutError:
        pass
    except ConnectionResetError:
        pass
    except socket.gaierror:
        pass
    #except websocket._exceptions.WebSocketAddressException:
    #    pass
    #except websocket._exceptions.WebSocketConnectionClosedException:
    #    pass
    except ConnectionRefusedError:
        pass
    except KeyError:
        pass

    return "latest: **${:.3f}** ({:.5f} Ξ) (ETH: **${:.0f}**) [<https://bit.ly/2w6Q0P0>]".format(price_in_usd, price_in_eth, eth_price)


def main():
    client = discord.Client()

    @client.event
    async def on_message(message):
        # we do not want the bot to reply to itself
        if message.author == client.user:
            return
        # we do not want the bot to reply to other bots
        if message.author.bot:
            return

        if message.content.startswith('!price'):
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
        print('Logged in as')
        print(client.user.name)
        print(client.user.id)
        print('------')

    client.run(TOKEN)


if __name__ == "__main__":
    main()