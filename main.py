# -*- coding: UTF-8 -*-
"""
0xBitcoin Discord Price Bot

TODO: move commands out of main.py, this file is getting long
"""

import sys
import os
# TODO: after upgrading discord.py to rewrite, change to >=3.6
assert sys.version_info != (3,6), "requires python 3.6"

import time
import websocket  # for websocket.enableTrace(False)
import websockets  # for websockets.exceptions.ConnectionClosed
import asyncio
import logging
import discord
from secret_info import TOKEN
from reconnecting_bot import keep_running

# from coinmarketcap import CoinMarketCapAPI
# from enclavesdex import EnclavesAPI
# from forkdelta import ForkDeltaAPI
# from mercatox import MercatoxAPI
# from idex import IDEXAPI
# from ethex import EthexAPI
# from coinexchange import CoinExchangeAPI
# from multi_exchange_manager import MultiExchangeManager
import exchanges

from mineable_token_info import MineableTokenInfo
import etherscan

import formatting_helpers
import commands

from persistent_storage import Storage
import configuration as config

from mock_discord_classes import MockClient, MockMessage, MockAuthor


_PROGRAM_NAME = "0xbtc-discord-price-bot"
_VERSION = "0.3.3"


old_status_string = None
async def update_status(client, status_string):
    global old_status_string
    if status_string != old_status_string:
        await client.change_presence(game=discord.Game(name=status_string),
                                     status=discord.Status('online'),
                                     afk=False)

async def send_message_to_user_by_id(apis, user_id, message):
    user = discord.utils.get(apis.client.get_all_members(), id=user_id)

    if not isinstance(message, str):
        logging.error("tried to respond with something other than a string - cancelling; message='{}' type={}".format(message, type(message)))
        return

    if user is not None:
        await apis.client.send_message(user, message)
    else:
        raise RuntimeError("send_message_to_user_by_id could not find user id {}".format(user_id))

async def send_message_to_channel_by_id(apis, channel_id, message):
    channel = apis.client.get_channel(channel_id)

    if channel is not None:
        await apis.client.send_message(channel, message)
    else:
        raise RuntimeError("send_message_to_channel_by_id could not find channel id {}".format(channel_id))

async def send_file_to_channel_by_id(apis, channel_id, filepath):
    channel = apis.client.get_channel(channel_id)

    if channel is not None:
        await apis.client.send_file(channel,
                                    filepath)
    else:
        raise RuntimeError("send_file_to_channel_by_id could not find channel id {}".format(channel_id))

async def show_all_time_high_image(apis):
    try:
        apis.storage.all_time_high_image_filename.get()
    except KeyError:
        return

    if apis.storage.all_time_high_image_filename.get() == None:
        return

    logging.info("Showing ath image. Filename is '{}'".format(apis.storage.all_time_high_image_filename.get()))
    try:
        await send_file_to_channel_by_id(apis, 
                                         config.ANNOUNCEMENT_CHANNEL_ID, 
                                         os.path.join(config.DATA_FOLDER,
                                                      apis.storage.all_time_high_image_filename.get()))
    except Exception as e:
        logging.warning('Failed to send image to channel: {}'.format(str(e)))
    else:
        # wait some time to make sure image is uploaded
        await asyncio.sleep(5.0)
        # once the image is sent, clear the filename in storage
        apis.storage.all_time_high_image_filename.set(None)

async def send_all_time_high_announcement(apis, message):
    await show_all_time_high_image(apis)

    await send_message_to_channel_by_id(apis, config.ANNOUNCEMENT_CHANNEL_ID, message)
    logging.info('Sending announcement: {}'.format(message))

async def check_update_all_time_high(apis):
    try:
        price_eth = apis.exchanges.price_eth(config.TOKEN_SYMBOL)
        price_usd = apis.exchanges.price_eth(config.TOKEN_SYMBOL) * apis.exchanges.eth_price_usd()
        if (price_usd > apis.storage.all_time_high_usd_price.get()
            and formatting_helpers.prettify_decimals(price_usd)
                != formatting_helpers.prettify_decimals(apis.storage.all_time_high_usd_price.get())):
            msg = 'New USD all-time-high **${}**'.format(formatting_helpers.prettify_decimals(price_usd))
            await send_all_time_high_announcement(apis, msg)
            apis.storage.all_time_high_usd_price.set(price_usd)
            apis.storage.all_time_high_usd_timestamp.set(time.time())
        if (price_eth > apis.storage.all_time_high_eth_price.get()
            and formatting_helpers.prettify_decimals(price_eth)
                != formatting_helpers.prettify_decimals(apis.storage.all_time_high_eth_price.get())):
            msg = 'New Ethereum all-time-high **{}Ξ**'.format(formatting_helpers.prettify_decimals(price_eth))
            await send_all_time_high_announcement(apis, msg)
            apis.storage.all_time_high_eth_price.set(price_eth)
            apis.storage.all_time_high_eth_timestamp.set(time.time())
    except:
        logging.exception('Failed to save ATH data')

async def background_update():
    await client.wait_until_ready()
    while not client.is_closed:
        try:
            await apis.exchanges.update()
        except RuntimeError as e:
            logging.warning('Failed to update exchange APIs: {}'.format(str(e)))
        except:
            logging.exception('Failed to update exchange APIs')

        try:
            apis.token.update()
        except RuntimeError as e:
            logging.warning('Failed to update contract info: {}'.format(str(e)))
        except:
            logging.exception('Failed to update contract info')

        if (time.time() - apis.storage.last_holders_update_timestamp.get()) / 3600.0 > config.TOKEN_HOLDER_UPDATE_RATE_HOURS:
            try:
                etherscan.update_saved_holders_chart(config.TOKEN_NAME,
                                                     config.TOKEN_ETH_ADDRESS,
                                                     apis.token.tokens_minted)
                apis.storage.last_holders_update_timestamp.set(time.time())
            except TimeoutError:
                logging.warning('Failed to update token holders chart')
            except:
                logging.exception('Failed to update token holders chart')
            else:
                logging.info('Updated token holders chart')

        await check_update_all_time_high(apis)

        try:
            price_eth = apis.exchanges.price_eth(config.TOKEN_SYMBOL)
            price_usd = apis.exchanges.price_eth(config.TOKEN_SYMBOL) * apis.exchanges.eth_price_usd()
            # usd price is hidden if it is 0 (an error)
            usd_str = "" if price_usd == 0 else "${:.2f}  |  ".format(price_usd)

            # show hashrate if available, otherwise show 'time since last update'
            if apis.token.estimated_hashrate is not None and apis.token.estimated_hashrate > 0:
                end_of_status = formatting_helpers.to_readable_thousands(apis.token.estimated_hashrate, unit_type='short_hashrate')
            else:
                end_of_status = formatting_helpers.seconds_to_n_time_ago(time.time()-apis.exchanges.last_updated_time())

            # wait until at least one successful update to show status
            if apis.exchanges.last_updated_time() != 0:
                fmt_str = "{}{} Ξ ({})"
                await update_status(client, fmt_str.format(usd_str,
                                                           formatting_helpers.prettify_decimals(price_eth),
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

async def send_discord_msg_to_channel(channel, message):
    # don't send messages that are only 'OK-noresponse' (this indicates
    # command ran, but no output is expected
    if message == "OK-noresponse":
        return

    if not isinstance(message, str):
        logging.error("tried to respond with something other than a string - cancelling; message='{}' type={}".format(message, type(message)))
        return

    if message.strip() == "":
        logging.error("tried to respond with empty string - cancelling; message={}".format(repr(message)))
        return

    try:
        await client.send_message(channel, message)
    except discord.errors.Forbidden:
        logging.debug('no permission in channel: {} [{}]'.format(channel.name, channel.id))

def preprocess(message):
    message = message.lower().strip()

    # allow '! command' since some platforms autocorrect to add a space
    if message.startswith(config.COMMAND_CHARACTER + ' '):
        message = config.COMMAND_CHARACTER + message[2:]

    # allow '!!command', its a common typo
    if message.startswith(config.COMMAND_CHARACTER+config.COMMAND_CHARACTER):
        message = config.COMMAND_CHARACTER + message[2:]

    # allow unicode ! (replace with ascii version)
    if config.COMMAND_CHARACTER == '!':
        if message.startswith('！'):
            message = '!' + message[1:]

    return message

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

        command_str = preprocess(message.content)

        if message.channel.id in config.BLACKLISTED_CHANNEL_IDS:
            # check only global commands in a blacklisted channel
            response = await commands.handle_global_command(command_str, message, apis)
            if response:
                await send_discord_msg_to_channel(message.channel, response)
                return
        else:
            # check all commands in a normal channel
            response = await commands.handle_global_command(command_str, message, apis)
            if response:
                await send_discord_msg_to_channel(message.channel, response)
                return
            response = await commands.handle_trading_command(command_str, message, apis)
            if response:
                await send_discord_msg_to_channel(message.channel, response)
                return

        # If command starts with config.COMMAND_CHARACTER and we have not returned yet, it was unrecognized.
        if command_str.startswith(config.COMMAND_CHARACTER):
            logging.info('UNKNOWN cmd {}'.format(repr(command_str)))

    @client.event
    async def on_ready():
        show_startup_info(client, show_channels)

def show_startup_info(client, show_channels):
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
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('websockets').setLevel(logging.WARNING)
    logging.getLogger('web3').setLevel(logging.INFO)
    logging.getLogger("urllib3").setLevel(logging.INFO)
    logging.getLogger("matplotlib").setLevel(logging.INFO)
    logging.getLogger('discord').setLevel(logging.WARNING)

    logging.info('Logging debug info to {}'.format(path))

async def manual_api_update():
    logging.info('updating apis...')
    try:
        await apis.exchanges.update()
        apis.token.update()
    except Exception as e:
        logging.exception('failed to update prices / contract info')


async def manual_command(cmd, apis):
    cmd = preprocess(cmd)
    try:
        global_response = await commands.handle_global_command(cmd, MockMessage(), apis)
        trading_response = await commands.handle_trading_command(cmd, MockMessage(), apis)

        if global_response != None and trading_response != None:
            logging.warning("Command '{}' has both a global and trading response; only the global response will be shown".format(cmd))
        
        if global_response != None:
            for line in global_response.split('\n'):
                logging.info('>' + line)
            return
        if trading_response != None:
            for line in trading_response.split('\n'):
                logging.info('>' + line)
            return
    except (KeyboardInterrupt, SystemExit):
        raise
    except:
        logging.exception('Got exception from command handler')

async def command_test():
    global apis

    # todo: start background_update instead?
    await manual_api_update()

    while True:
        cmd = input('command: ')
        if cmd == "quit" or cmd == "exit":
            return
        if cmd == "update" or cmd == "api":
            await manual_api_update()
            continue
        if cmd == "runall":
            for cmd_def in config.GLOBAL_COMMANDS + config.TRADING_COMMANDS:
                cmd = config.COMMAND_CHARACTER + cmd_def.keywords[0]
                if cmd == "!convert":
                    cmd += " 1 eth to usd"
                if cmd == "!income":
                    cmd += " 100mh"
                if cmd == "!mine":
                    cmd += " 123"
                if cmd == "!set address":
                    cmd += " 0x0000000000000000000000000000000000000000"
                if cmd == "!setath":
                    cmd += " 0.001 2001-02-03 4.05 2006-07-08"
                if cmd == "!setbestshare":
                    cmd += " Username0 0 0x00 0"
                logging.info("")
                logging.info("--- Running command '{}' ---".format(cmd))
                await manual_command(cmd, apis)
            continue

        await manual_command(cmd, apis)

# todo: encapsulate these
client = None
apis = None

class APIWrapper():
    def __init__(self, client, storage, exchanges, token, start_time):
        self.client = client
        self.storage = storage
        self.exchanges = exchanges
        self.token = token

        self.start_time = start_time

def main():
    import argparse
    import os

    global client, apis
    
    parser = argparse.ArgumentParser(description='{} v{}'.format(_PROGRAM_NAME, _VERSION),
                                     epilog='<3 0x1d00ffff')
    # TODO: make show_channels a keyboard shortcut and remove this param
    parser.add_argument('--show_channels', action='store_true', default=False,
                        help='Show all visible channels/permissions during init')
    parser.add_argument('--command_test', action='store_true', default=False,
                        help=("If set, don't connect to Discord - instead "
                              "run a CLI interface to allow command tests."))
    parser.add_argument('--self_test', action='store_true', default=False,
                        help=("Run unittests"))
    parser.add_argument('--version', action='version', 
                        version='%(prog)s v{}'.format(_VERSION))
    args = parser.parse_args()

    start_time = time.time()

    if args.self_test or args.command_test:
        config.DATA_FOLDER = './test_data/databases/'

    if not os.path.exists(config.DATA_FOLDER):
        os.makedirs(config.DATA_FOLDER)
    setup_logging(os.path.join(config.DATA_FOLDER, 'debug.log'))

    exchange_manager = exchanges.MultiExchangeManager(
    [
        exchanges.CoinMarketCapAPI(config.TOKEN_SYMBOL),
        exchanges.CoinMarketCapAPI('ETH'),
        exchanges.CoinMarketCapAPI('BTC'),
        exchanges.EnclavesAPI(config.TOKEN_SYMBOL),
        exchanges.ForkDeltaAPI(config.TOKEN_SYMBOL),
        exchanges.IDEXAPI(config.TOKEN_SYMBOL),
        exchanges.MercatoxAPI(config.TOKEN_SYMBOL),
        #exchanges.HotbitAPI(config.TOKEN_SYMBOL),
        exchanges.EthexAPI(config.TOKEN_SYMBOL),
        exchanges.CoinExchangeAPI(config.TOKEN_SYMBOL),
        exchanges.UniswapAPI(config.TOKEN_SYMBOL),
    ])
    token = MineableTokenInfo(config.TOKEN_ETH_ADDRESS)
    storage = Storage(config.DATA_FOLDER)

    if args.self_test:
        import all_self_tests
        client = MockClient()
        apis = APIWrapper(client, storage, exchange_manager, token, start_time)
        all_self_tests.run_all()
    elif args.command_test:
        client = MockClient()
        apis = APIWrapper(client, storage, exchange_manager, token, start_time)
        asyncio.get_event_loop().run_until_complete(command_test())
    else:
        logging.info('Starting {} version {}'.format(_PROGRAM_NAME, _VERSION))
        logging.debug('discord.py version {}'.format(discord.__version__))
        client = discord.Client()
        apis = APIWrapper(client, storage, exchange_manager, token, start_time)
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
