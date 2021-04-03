# -*- coding: UTF-8 -*-
"""
0xBitcoin Discord Price Bot

TODO: move commands out of main.py, this file is getting long
"""

import sys
import os
import time
import websockets  # for websockets.exceptions.ConnectionClosed  # TODO: verify we need this
import asyncio
import logging
import discord
from discord.ext import tasks  # background_update is a task now
from secret_info import TOKEN

import exchanges

from mineable_token_info import MineableTokenInfo
import etherscan

import formatting_helpers
import commands

from util import preprocess_message

from persistent_storage import Storage
import configuration as config

import all_self_tests
from mock_discord_classes import MockClient, MockMessage, MockAuthor


_PROGRAM_NAME = "0xbtc-discord-price-bot"
_VERSION = "0.4.11"


old_status_string = None
async def update_status(client, status_string):
    global old_status_string
    if status_string != old_status_string:
        await client.change_presence(activity=discord.Activity(
            type=discord.ActivityType.playing,
            name=status_string))


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

    if apis.storage.all_time_high_image_filename.get() is None:
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
    price_eth = apis.exchanges.price_eth(config.TOKEN_SYMBOL)
    price_usd = apis.exchanges.price_eth(config.TOKEN_SYMBOL) * apis.exchanges.eth_price_usd()
    if (price_eth > 100 * apis.storage.all_time_high_eth_price.get()
            or price_usd > 100 * apis.storage.all_time_high_usd_price.get()):
        # check for prices so high they are likely bugs
        logging.warning(f"Prevented ATH announcement due to price too high ({price_eth} eth {price_usd} usd)")
        return
    try:
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


@tasks.loop(seconds=config.UPDATE_RATE)
async def background_update():
    # TODO: time this. even better: time each exchange
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

    # removed holders chart updates until etherscan.py works again
    #
    # if (time.time() - apis.storage.last_holders_update_timestamp.get()) / 3600.0 > config.TOKEN_HOLDER_UPDATE_RATE_HOURS:
    #     try:
    #         etherscan.update_saved_holders_chart(config.TOKEN_NAME,
    #                                              config.TOKEN_ETH_ADDRESS,
    #                                              apis.token.tokens_minted)
    #         apis.storage.last_holders_update_timestamp.set(time.time())
    #     except TimeoutError:
    #         logging.warning('Failed to update token holders chart')
    #     except:
    #         logging.exception('Failed to update token holders chart')
    #     else:
    #         logging.info('Updated token holders chart')

    try:
        await check_update_all_time_high(apis)
    except:
        logging.exception('Failed to check all time high')

    try:
        price_eth = apis.exchanges.price_eth(config.TOKEN_SYMBOL)
        price_usd = apis.exchanges.price_eth(config.TOKEN_SYMBOL) * apis.exchanges.eth_price_usd()
        # usd price is hidden if it is 0 (an error)
        usd_str = "" if price_usd == 0 else "${:.2f}  |  ".format(price_usd)

        # show hashrate if available, otherwise show 'time since last update'
        if apis.token.estimated_hashrate_since_readjustment is not None and apis.token.estimated_hashrate_since_readjustment > 0:
            end_of_status = formatting_helpers.to_readable_thousands(apis.token.estimated_hashrate_since_readjustment, unit_type='short_hashrate')
        else:
            end_of_status = formatting_helpers.seconds_to_n_time_ago(
                time.time() - apis.exchanges.last_updated_time())

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


@background_update.before_loop
async def before_background_update():
    # prevent background_update loops from starting until bot is ready
    await apis.client.wait_until_ready()


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
        await channel.send(message)
    except discord.errors.Forbidden:
        logging.debug('no permission in channel: {} [{}]'.format(channel.name, channel.id))


async def process_message(message):
    response = None
    # we do not want the bot to reply to itself
    if message.author == client.user:
        return
    # we do not want the bot to reply to other bots
    if message.author.bot:
        return

    message_contents = preprocess_message(message.content)
    if not isinstance(message_contents, str):
        logging.error("bugcheck: message_contents not a str? '{}'".format(repr(message_contents)))
    if message_contents == "":
        return

    response = await commands.handle_global_command(message_contents, message, apis)
    if response:
        await send_discord_msg_to_channel(message.channel, response)
        return

    # trading commands are ignored in blacklisted channels
    if message.channel.id not in config.BLACKLISTED_CHANNEL_IDS:
        response = await commands.handle_trading_command(message_contents, message, apis)
        if response:
            await send_discord_msg_to_channel(message.channel, response)
            return

    # If command starts with config.COMMAND_CHARACTER and we have not returned yet, it was unrecognized.
    if message_contents.startswith(config.COMMAND_CHARACTER):
        logging.info('UNKNOWN cmd {}'.format(repr(message_contents)))


def show_startup_info(client):
    logging.info('Logged in to {} servers as {} id:{}'.format(len(client.guilds),
                                                              client.user.name,
                                                              client.user.id))


def setup_logging(path, verbose=False):
    class DiscordLogFilter(logging.Filter):
        """Filter to hide uninformative/annoying discord errors"""
        def filter(self, record):
            ignored_messages = (
                "PyNaCl is not installed, voice will NOT be supported",
            )
            return not record.getMessage() in ignored_messages

    # set up logging to file
    filehandler = logging.FileHandler(path,
                                      mode='a',
                                      encoding='utf-8')
    filehandler.addFilter(DiscordLogFilter())
    filehandler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s, %(name)-12s, %(levelname)-8s, %(message)s',
                                  datefmt='%d-%m-%y %H:%M:%S')
    filehandler.setFormatter(formatter)

    # define a Handler which writes INFO messages or higher to the sys.stderr
    console = logging.StreamHandler()
    console.addFilter(DiscordLogFilter())
    if verbose:
        console.setLevel(logging.DEBUG)
    else:
        console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)-15s %(name)-7.7s %(levelname)-5.5s %(message)s',
                                  datefmt='%m/%d %H:%M:%S')
    console.setFormatter(formatter)

    logging.basicConfig(handlers=[filehandler, console],
                        level=logging.DEBUG)

    # make libraries be quiet
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('websockets').setLevel(logging.WARNING)
    logging.getLogger('web3').setLevel(logging.INFO)
    logging.getLogger("urllib3").setLevel(logging.INFO)
    logging.getLogger("matplotlib").setLevel(logging.INFO)
    logging.getLogger('discord').setLevel(logging.WARNING)

    logging.info('Logging debug info to {}'.format(path))


async def manual_api_update():
    logging.info('Updating APIs')
    try:
        await apis.exchanges.update()
        apis.token.update()
    except Exception as e:
        logging.exception('failed to update prices / contract info')


async def manual_command(cmd, apis, ignore_response=False):
    cmd = preprocess_message(cmd)
    try:
        global_response = await commands.handle_global_command(cmd, MockMessage(), apis)
        trading_response = await commands.handle_trading_command(cmd, MockMessage(), apis)

        if ignore_response:
            return

        if global_response is not None and trading_response is not None:
            logging.warning("Command '{}' has both a global and trading response; only the global response will be shown".format(cmd))

        if global_response is not None:
            for line in global_response.split('\n'):
                logging.info('>' + line)
            return
        if trading_response is not None:
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


def blocking_api_update():
    asyncio.get_event_loop().run_until_complete(manual_api_update())


def raw_message_test():
    asyncio.get_event_loop().run_until_complete(manual_command("asdfasdf", apis, ignore_response=True))


def invalid_command_test():
    asyncio.get_event_loop().run_until_complete(manual_command("!asdfasdf", apis, ignore_response=True))


def string_command_test():
    asyncio.get_event_loop().run_until_complete(manual_command("!hug", apis, ignore_response=True))


def price_command_test():
    asyncio.get_event_loop().run_until_complete(manual_command("!priceall", apis, ignore_response=True))


def worst_case_command_test():
    asyncio.get_event_loop().run_until_complete(manual_command("!mine abc", apis, ignore_response=True))


def run_function_and_time_it(function_name, iterations):
    import timeit
    timer = timeit.Timer("{}()".format(function_name),
                         "gc.enable(); from main import {}".format(function_name))
    speed = min(timer.repeat(repeat=3, number=iterations))
    time_per_run = speed / iterations
    messages_per_sec = 1 / (speed / iterations)
    fmt_str = "{:>23}:{:>12} seconds per call{:>12} runs per sec"
    logging.info(fmt_str.format(function_name,
                                formatting_helpers.prettify_decimals(time_per_run),
                                formatting_helpers.prettify_decimals(messages_per_sec)))


def speed_test():
    global apis
    iterations = 2000
    fmt_str = "--- Starting speed test: {} calls per message type ---"
    logging.info(fmt_str.format(iterations))

    # simple non-command message processing speed
    run_function_and_time_it('blocking_api_update', 1)
    # simple non-command message processing speed
    run_function_and_time_it('raw_message_test', iterations)
    # simple non-command message processing speed
    run_function_and_time_it('invalid_command_test', iterations)
    # simple non-command message processing speed
    run_function_and_time_it('string_command_test', iterations)
    # simple non-command message processing speed
    run_function_and_time_it('price_command_test', iterations)
    # simple non-command message processing speed
    run_function_and_time_it('worst_case_command_test', iterations // 10)

    return


# todo: encapsulate these
apis = None
client = None


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

    # TODO: make client NOT global.
    global client, apis

    parser = argparse.ArgumentParser(description='{} v{}'.format(_PROGRAM_NAME, _VERSION),
                                     epilog='<3 0x1d00ffff')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--command_test', action='store_true', default=False,
                       help=("If set, don't connect to Discord - instead "
                             "run a CLI interface to allow command tests."))
    group.add_argument('--self_test', action='store_true', default=False,
                       help=("Run unittests"))
    group.add_argument('--speed_test', action='store_true', default=False,
                       help=("Run command processing speed test"))
    group.add_argument('--fuzz_test', action='store_true', default=False,
                       help=("Run command processing fuzz test"))
    group.add_argument('--version', action='version',
                       version='%(prog)s v{}'.format(_VERSION))
    parser.add_argument('--verbose', action='store_true',
                        help=("Enable detailed debug messages"))
    args = parser.parse_args()

    start_time = time.time()

    if args.self_test or args.command_test or args.speed_test or args.fuzz_test:
        logging.basicConfig(level=logging.INFO)
        config.DATA_FOLDER = './test_data/databases/'

    if not os.path.exists(config.DATA_FOLDER):
        os.makedirs(config.DATA_FOLDER)
    setup_logging(os.path.join(config.DATA_FOLDER, 'debug.log'), verbose=args.verbose)

    token = MineableTokenInfo(config.TOKEN_ETH_ADDRESS)
    storage = Storage(config.DATA_FOLDER)
    exchange_manager = exchanges.MultiExchangeManager([
        exchanges.CoinMarketCapAPI(config.TOKEN_SYMBOL),
        # exchanges.CoinMarketCapAPI('ETH'),
        # exchanges.CoinMarketCapAPI('BTC'),
        exchanges.LiveCoinWatchAPI('ETH'),
        exchanges.LiveCoinWatchAPI('BTC'),
        # 5/4/20 removed IDEX. They seem to only partially (?) support 0xBTC. They are also a CEX masquerading as a DEX, which is unethical.
        # exchanges.IDEXAPI(config.TOKEN_SYMBOL),
        exchanges.MercatoxAPI(config.TOKEN_SYMBOL),
        # 9/10/20 remove uniswap v1. All liquidity (except $200) has moved to v2
        # exchanges.Uniswapv1API(config.TOKEN_SYMBOL),
        exchanges.Uniswapv2API(config.TOKEN_SYMBOL),
        # 3/13/20 removed 0xChange. Will re-enable in the future.
        # exchanges.ZxchangeAPI(config.TOKEN_SYMBOL),
        # 2/12/20 removed coinexchange. homepage says closed.
        # exchanges.CoinExchangeAPI(config.TOKEN_SYMBOL),
        # 2/12/20 removed enclaves. blocks all usa traffic.
        # exchanges.EnclavesAPI(config.TOKEN_SYMBOL),
        # 2/12/20 removed ethex, they might be out of business. homepage says check later.
        # exchanges.EthexAPI(config.TOKEN_SYMBOL),
        # 2/12/20 removed forkdelta, need new api. 7/26/20: reenabled forkdelta
        exchanges.ForkDeltaAPI(config.TOKEN_SYMBOL, storage),
        # 9/06/20 added balancer
        exchanges.BalancerAPI(config.TOKEN_SYMBOL),
        # exchanges.HotbitAPI(config.TOKEN_SYMBOL),
        # 2/12/20 removed merklex. seems to have rebranded to nitrade.
        # exchanges.MerkleXAPI(config.TOKEN_SYMBOL),
        # 9/22/20 added swapmatic
        exchanges.SwapmaticAPI(config.TOKEN_SYMBOL),
        # 4/03/21 added quickswap
        exchanges.QuickSwapAPI(config.TOKEN_SYMBOL),
    ])

    if args.self_test:
        client = MockClient()
        apis = APIWrapper(client, storage, exchange_manager, token, start_time)
        all_self_tests.run_all()
    elif args.command_test:
        client = MockClient()
        apis = APIWrapper(client, storage, exchange_manager, token, start_time)
        try:
            asyncio.get_event_loop().run_until_complete(command_test())
        except (SystemExit, KeyboardInterrupt):
            return
    elif args.speed_test:
        client = MockClient()
        apis = APIWrapper(client, storage, exchange_manager, token, start_time)
        speed_test()
    elif args.fuzz_test:
        client = MockClient()
        apis = APIWrapper(client, storage, exchange_manager, token, start_time)
        try:
            all_self_tests.run_command_fuzzer()
        except (SystemExit, KeyboardInterrupt):
            return
    else:
        logging.info('{} v{}, discord.py v{}'.format(_PROGRAM_NAME, _VERSION, discord.__version__))

        while True:
            client = discord.Client()

            @client.event
            async def on_message(message):
                await process_message(message)

            @client.event
            async def on_ready():
                show_startup_info(client)

            apis = APIWrapper(client, storage, exchange_manager, token, start_time)

            try:
                background_update.cancel()  # stops the task only if it is running
                background_update.start()
                client.run(TOKEN)
            except (SystemExit, KeyboardInterrupt):
                # what we expect to get when exiting with Ctrl+C
                break
            except RuntimeError as e:
                if str(e) == "Event loop is closed":
                    # this error is sometimes thrown when exiting the bot with Ctrl+C
                    break
                else:
                    logging.exception('Unexpected error from Discord... retrying')
                    time.sleep(10)  # wait a little time to prevent cpu spins
            except Exception:
                logging.exception('Unexpected error from Discord... retrying')
                time.sleep(10)  # wait a little time to prevent cpu spins

        logging.info("Exiting...bye!")

if __name__ == "__main__":
    main()
