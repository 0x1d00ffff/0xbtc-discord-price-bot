import logging
import asyncio
import aiohttp
import discord
import websockets
import concurrent

import backoff


""" from https://gist.github.com/Hornwitser/93aceb86533ed3538b6f """
async def keep_running(client, token):
    retry = backoff.ExponentialBackoff()

    while True:
        try:
            await client.login(token)

        except (discord.HTTPException, aiohttp.ClientError):
            logging.exception("Discord.py trying to login...")
            await asyncio.sleep(retry.delay())

        else:
            break

    while client.is_logged_in:
        if client.is_closed:
            client._closed.clear()
            client.http.recreate()

        try:
            await client.connect()

        # NOTE: aiohttp.errors does not exist anymore
        #except aiohttp.errors.ClientOSError:
            logging.error("Network down; discord.py trying to stay connected...")
            await asyncio.sleep(retry.delay())

        except TypeError as e:
            logging.error("Discord.py TypeError: '{}'".format(str(e)))
            if str(e) == "close_connection() got an unexpected keyword argument 'force'":
                logging.error("Discord.py trying to stay connected...")
            else:
                logging.exception("Unexpected error from discord, trying to stay connected...")

        except concurrent.futures._base.TimeoutError:
            # indicates something is acrually wrong, so discord will not auto
            # reconnect. The best solution here is to start over and recreate
            # the client object which happens in the caller.
            await asyncio.sleep(retry.delay())
            raise RuntimeError("got an error that is unrecoverable")


        except (discord.HTTPException, aiohttp.ClientError,
                discord.GatewayNotFound, discord.ConnectionClosed,
                websockets.InvalidHandshake,
                websockets.WebSocketProtocolError) as e:
            if isinstance(e, discord.ConnectionClosed) and e.code == 4004:
                raise # Do not reconnect on authentication failure
            logging.error("Discord.py trying to stay connected...")
            await asyncio.sleep(retry.delay())


#logging.basicConfig(level=logging.INFO)
#client = discord.Client()
#token = '<token>'
#asyncio.get_event_loop().run_until_complete(keep_running(client, token))

