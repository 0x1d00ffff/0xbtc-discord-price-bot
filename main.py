# -*- coding: UTF-8 -*-
"""
0xBitcoin Discord Price Bot

TODO: move commands out of main.py, this file is getting long
"""

import sys
# TODO: after upgrading discord.py to rewrite, change to >=3.6
assert sys.version_info != (3,6), "requires python 3.6"

import time
import websocket  # for websocket.enableTrace(False)
import websockets  # for websockets.exceptions.ConnectionClosed
import asyncio
import logging
import re
import discord
from secret_info import TOKEN
from reconnecting_bot import keep_running

from coinmarketcap import CoinMarketCapAPI
from enclavesdex import EnclavesAPI
from forkdelta import ForkDeltaAPI
from mercatox import MercatoxAPI
from idex import IDEXAPI
from ethex import EthexAPI
from multi_api_manager import MultiApiManager

from mineable_token_info import MineableTokenInfo
import etherscan

import formatting_helpers
import commands

from persistent_storage import Storage
import configuration as config

_PROGRAM_NAME = "0xbtc-discord-price-bot"
_VERSION = "0.2.3"


old_status_string = None
async def update_status(client, status_string):
    global old_status_string
    if status_string != old_status_string:
        await client.change_presence(game=discord.Game(name=status_string),
                                     status=discord.Status('online'),
                                     afk=False)

async def background_update():
    await client.wait_until_ready()
    while not client.is_closed:
        try:
            exchanges.update()
        except RuntimeError as e:
            logging.warning('Failed to update exchange APIs: {}'.format(str(e)))
        except:
            logging.exception('Failed to update exchange APIs')

        try:
            token.update()
        except RuntimeError as e:
            logging.warning('Failed to update contract info: {}'.format(str(e)))
        except:
            logging.exception('Failed to update contract info')

        if (time.time() - storage.last_holders_update_timestamp.get()) / 3600.0 > config.TOKEN_HOLDER_UPDATE_RATE_HOURS:
            try:
                etherscan.update_saved_holders_chart(config.TOKEN_ETH_ADDRESS,
                                                     token.tokens_minted)
                storage.last_holders_update_timestamp.set(time.time())
            except TimeoutError:
                logging.warning('Failed to update token holders chart')
            except:
                logging.exception('Failed to update token holders chart')
            else:
                logging.info('Updated token holders chart')

        try:
            price_eth = exchanges.price_eth(config.CURRENCY)
            price_usd = exchanges.price_eth(config.CURRENCY) * exchanges.eth_price_usd()
            if price_usd > storage.all_time_high_usd_price.get():
                logging.info('New usd ATH! ${}'.format(price_usd))
                storage.all_time_high_usd_price.set(price_usd)
                storage.all_time_high_usd_timestamp.set(time.time())
            if price_eth > storage.all_time_high_eth_price.get():
                logging.info('New eth ATH! {}Ξ'.format(price_eth))
                storage.all_time_high_eth_price.set(price_eth)
                storage.all_time_high_eth_timestamp.set(time.time())
        except:
            logging.exception('Failed to save ATH data')

        try:
            price_eth = exchanges.price_eth(config.CURRENCY)
            price_usd = exchanges.price_eth(config.CURRENCY) * exchanges.eth_price_usd()
            # usd price is hidden if it is 0 (an error)
            usd_str = "" if price_usd == 0 else "${:.2f}  |  ".format(price_usd)

            # show hashrate if available, otherwise show 'time since last update'
            if token.estimated_hashrate is not None and token.estimated_hashrate > 0:
                end_of_status = to_readable_thousands(token.estimated_hashrate, unit_type='short_hashrate')
            else:
                end_of_status = formatting_helpers.seconds_to_n_time_ago(time.time()-exchanges.last_updated_time())

            # wait until at least one successful update to show status
            if exchanges.last_updated_time() != 0:
                fmt_str = "{}{} Ξ ({})"
                await update_status(client, fmt_str.format(usd_str,
                                                           prettify_decimals(price_eth),
                                                           end_of_status))
        except (websockets.exceptions.ConnectionClosed,
                RuntimeError) as e:
            logging.warning('Falied to change status: {}'.format(str(e)))
        except:
            logging.exception('Failed to change status')

        await asyncio.sleep(config.UPDATE_RATE)

    # this throws an exception which causes the program to restart
    # in normal operation we should never reach this
    raise RuntimeError('background_update loop stopped - something is wrong')

async def send_discord_msg(channel, message):
    # don't send messages that are only 'OK-noresponse' (this indicates
    # command ran, but no output is expected
    if message == "OK-noresponse":
        return

    try:
        await client.send_message(channel, message)
    except discord.errors.Forbidden:
        logging.debug('no permission in channel: {} [{}]'.format(channel.name, channel.id))

def configure_discord_client(show_channels=False):
    client.loop.create_task(background_update())

    @client.event
    async def on_message(message):
        response = None

        # we do not want the bot to reply to itself
        if message.author == client.user:
            return
        # we do not want the bot to reply to other bots
        if message.author.bot:
            return

        message_contents = message.content.lower().strip()

        # allow '! command' since some platforms autocorrect to add a space
        if message_contents.startswith(config.COMMAND_CHARACTER + ' '):
            message_contents = config.COMMAND_CHARACTER + message_contents[2:]

        # allow '!!command', its a common typo
        if message_contents.startswith(config.COMMAND_CHARACTER+config.COMMAND_CHARACTER):
            message_contents = config.COMMAND_CHARACTER + message_contents[2:]

        # allow unicode ! (replace with ascii version)
        if config.COMMAND_CHARACTER == '!':
            if message_contents.startswith('！'):
                message_contents = '!' + message_contents[1:]

        if message.channel.id in config.BLACKLISTED_CHANNEL_IDS:
            # check only global commands in a blacklisted channel
            response = await commands.handle_global_command(message_contents, message)
            if response:
                await send_discord_msg(message.channel, response)
                return
        else:
            # check all commands in a normal channel
            response = await commands.handle_global_command(message_contents, message)
            if response:
                await send_discord_msg(message.channel, response)
                return
            response = await commands.handle_trading_command(message_contents, message)
            if response:
                await send_discord_msg(message.channel, response)
                return

        # If command starts with config.COMMAND_CHARACTER and we have not returned yet, it was unrecognized.
        if message_contents.startswith(config.COMMAND_CHARACTER):
            logging.info('UNKNOWN cmd {}'.format(repr(message_contents)))

    @client.event
    async def on_ready():
        show_startup_info(client, show_channels)

def show_startup_info(client, show_channels):
    logging.info('Starting {} version {}'.format(_PROGRAM_NAME, _VERSION))
    logging.debug('discord.py version {}'.format(discord.__version__))
    logging.info('Logged in to {} servers as {} id:{}'.format(len(client.servers),
                                                              client.user.name,
                                                              client.user.id))
    if show_channels:
        for server in client.servers:
            logging.info('  - {} - {} Members - id:{} '.format(server.name, 
                                                               server.member_count,
                                                               server.id))
            member = server.get_member(client.user.id)
            for channel in server.channels:
                allowed = '[No send permission]' if not channel.permissions_for(member).send_messages else ''
                logging.info('     - {} id:{} {}'.format(channel.name, 
                                                           channel.id,
                                                           allowed))

def setup_logging(path):
    class DiscordLogFilter(logging.Filter):
        """Filter to hide uninformative/annoying discord errors"""
        def filter(self, record):
            ignored_messages = (
                "PyNaCl is not installed, voice will NOT be supported",
                #"We have stopped responding to the gateway.",
                )
            return not record.getMessage() in ignored_messages

    # set up logging to file
    filehandler = logging.FileHandler(path,
                                      mode='a',
                                      encoding='utf-8')
    filehandler.addFilter(DiscordLogFilter())
    filehandler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s, %(name)-12s, %(levelname)-8s, %(message)s',
                                  datefmt='%m-%d-%y %H:%M:%S')
    filehandler.setFormatter(formatter)

    # define a Handler which writes INFO messages or higher to the sys.stderr
    console = logging.StreamHandler()
    console.addFilter(DiscordLogFilter())
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)-15s %(name)-7.7s %(levelname)-5.5s %(message)s',
                                  datefmt='%d/%m %H:%M:%S')
    console.setFormatter(formatter)

    logging.basicConfig(handlers=[filehandler, console],
        level=logging.DEBUG)

    # make libraries be quiet
    websocket.enableTrace(False)
    logging.getLogger('websockets').setLevel(logging.WARNING)
    logging.getLogger('web3').setLevel(logging.INFO)
    logging.getLogger("urllib3").setLevel(logging.INFO)
    logging.getLogger("matplotlib").setLevel(logging.INFO)
    logging.getLogger('discord').setLevel(logging.WARNING)

    logging.info('Logging debug info to {}'.format(path))

def manual_api_update():
    logging.info('updating apis...')
    try:
        exchanges.update()
        token.update()
    except Exception as e:
        logging.exception('failed to update prices / contract info')

def command_test():
    global client

    class MockClient():
        def __init__(self):
            self.is_closed = False
        def wait_until_ready(self):
            pass
        def change_presence(self, game=None, status=None, afk=None):
            args = {'game':game, 'status':status, 'afk':afk}
            logging.debug('Call to change_presence: {}'.format(args))
    class MockAuthor():
        name = "Test Name"
        id = '0'
    class MockMessage():
        author = MockAuthor()
        timestamp = time.time()

    client = MockClient()

    # todo: start background_update instead?
    manual_api_update()

    while True:
        cmd = input('command: ')
        if cmd == "quit" or cmd == "exit":
            return
        if cmd == "update" or cmd == "api":
            manual_api_update()
            continue
        try:
            mock_message = MockMessage()
            tasks = (
                commands.handle_global_command(cmd, mock_message),
                commands.handle_trading_command(cmd, mock_message)
            )

            responses = asyncio.get_event_loop().run_until_complete(asyncio.gather(*tasks))
            logging.info('Global response:')
            if responses[0] != None:
                for line in responses[0].split('\n'):
                    logging.info('>' + line)
            logging.info('Trading response:')
            if responses[1] != None:
                for line in responses[1].split('\n'):
                    logging.info('>' + line)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            logging.exception('Got exception from command handler')

# todo: encapsulate these
client = None
storage = None
exchanges = None
token = None
start_time = None

def main():
    import argparse
    import os

    global client, storage, exchanges, token, start_time
    
    parser = argparse.ArgumentParser(description='0xBitcoin Server Price Bot v{}'.format(_VERSION),
                                     epilog='<3 0x1d00ffff')
    parser.add_argument('--show_channels', action='store_true', default=False,
                        help='Show all visible channels/permissions during init')
    parser.add_argument('--command_test', action='store_true', default=False,
                        help=("If set, don't connect to Discord - instead "
                              "run a CLI interface to allow command tests."))
    parser.add_argument('--self_test', action='store_true', default=False,
                        help=("Run unittests"))
    parser.add_argument('--log_location',
                        default=os.path.join(config.DATA_FOLDER, 'debug.log'),
                        help=("Set the location of the debug log file. By "
                              "default it will go to the DATA_FOLDER set in "
                              "configuration.py"))
    parser.add_argument('--version', action='version', 
                        version='%(prog)s v{}'.format(_VERSION))
    args = parser.parse_args()

    start_time = time.time()

    if args.self_test:
        import all_self_tests
        all_self_tests.run_all()
        return

    if not os.path.exists(os.path.split(args.log_location)[0]):
        os.makedirs(os.path.split(args.log_location)[0])
    setup_logging(args.log_location)

    exchanges = MultiApiManager(
    [
        CoinMarketCapAPI(config.CURRENCY),
        CoinMarketCapAPI('ETH'),
        CoinMarketCapAPI('BTC'),
        EnclavesAPI(config.CURRENCY),
        ForkDeltaAPI(config.CURRENCY),
        IDEXAPI(config.CURRENCY),
        MercatoxAPI(config.CURRENCY),
        EthexAPI(config.CURRENCY),
        #HotbitAPI(config.CURRENCY),
    ])
    token = MineableTokenInfo(config.TOKEN_ETH_ADDRESS)
    storage = Storage(config.DATA_FOLDER)

    if args.command_test:
        storage = Storage('./test_data/databases/')
        command_test()
        return

    client = discord.Client()
    configure_discord_client(args.show_channels)

    while True:
        try:
            asyncio.get_event_loop().run_until_complete(keep_running(client, TOKEN))
        except SystemExit:
            raise
        except KeyboardInterrupt:
            raise
        except:
            logging.exception('Unexpected error from Discord... retrying')
            time.sleep(10)  # wait a little time to prevent cpu spins

if __name__ == "__main__":
    main()
