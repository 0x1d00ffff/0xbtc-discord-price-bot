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
import collections

import discord
from secret_info import TOKEN
from reconnecting_bot import keep_running
from enclavesdex import EnclavesAPI
from livecoinwatch import LiveCoinWatchAPI
from forkdelta import ForkDeltaAPI
from mercatox import MercatoxAPI
from idex import IDEXAPI
from hotbit import HotbitAPI
from multi_api_manager import MultiApiManager

_PROGRAM_NAME = "0xbtc-price-bot"
_VERSION = "0.1.0"
_UPDATE_RATE = 120  # how often to update all APIs (in seconds)
_CURRENCY = '0xBTC'
_COMMAND_CHARACTER = '!'  # what character should prepend all commands

_CLI_MODE = False  # if true, do not connect to discotd, instead start a CLI to test commands

_BLACKLISTED_CHANNEL_IDS = [
    # 0xbitcoin server
    '454156227446964226',  # announcements
    '417834372864147456',  # articles
    '413927301932253185',  # useful-links
    '412477591778492429',  # 0xbitcoin
    #'412483801265078273',  # trading (allowed)
    '429103257026297866',  # marketing
    '419929514316136473',  # miner-dev
    '414664710210846722',  # development
    '412483768541249536',  # support
    '438693168393748500',  # mining
    '435893447958986752',  # pools
    '439217061475123200',  # memes
    '421306695940046852',  # off-topic
    '418282243186753537',  # alts-trading

]

_EXPENSIVE_STUFF = [
    (400000,
     ['lambo']),
    (200000,
     ['used lambo']),
    (500000,
     ['private island', 'privare island', 'pirvate island']),
    (398.8*1000*1000,
     ['whitehouse']),
    (1.225*1000*1000*1000,
     ['buckinghampalace']),
    (101500, 
     ['tesla', 'telsa']),
    (1700,
     ['used ford taurus', 'used taurus', 'old ford taurus', 'old taurus']),
    (17600,
     ['like new ford taurus', 'like new taurus']),
    (28400,
     ['new ford taurus', 'ford taurus', 'new taurus', 'taurus']),
    (12,
     ['avocado toast',
      'avocado on toast', 
      'avacado toast', 
      'avacado on toast', 
      'avocato toast', 
      'avocato on toast',
      'avo toast']),
    (1,
     ['oneaire']),
    (10,
     ['tennaire', 'tenaire']),
    (100,
     ['hundredaire', 'hundradiere']),
    (1e3,
     ['thousandaire']),
    (1e6,
     ['millionaire']),
    (1e9,
     ['billionaire']),
    (1e12,
     ['trillionaire']),
    (650,
     ['magnum domperignon', 'domperignon', 'champagne', 'donperignon']),
    (200,
     ['microsoft windows license', 'microsoft windows', 'windows']),
]


CmdDef = collections.namedtuple('CmdDef', ['keywords', 'response'])
# commands that work in all channels (ignores the blacklist)
_GLOBAL_COMMANDS = [
    CmdDef(
        ['help'],
        "available commands: `price volume ratio convert bitcoinprice lambo privateisland whitehouse millionaire billionaire`\nquick link commands: `whitepaper website ann contract stats merch mvis cosmic az`"),
    CmdDef(
        ['white paper'],
        "0xBitcoin Whitepaper: <https://github.com/0xbitcoin/white-paper>"),
    CmdDef(
        ["site", "web site"],
        "0xBitcoin Website: <https://0xbitcoin.org/>"),
    CmdDef(
        ["lava wallet"],
        "Lava Wallet: <https://lavawallet.io/> (GitHub:<https://github.com/lavawallet>)"),
    CmdDef(
        ["contract", "address"],
        "0xBitcoin Contract: 0xb6ed7644c69416d67b522e20bc294a9a9b405b31 [<https://bit.ly/2y1WlMB>]"),
    CmdDef(
        ["stats", "statistics"],
        "0xBitcoin Stats: <https://0x1d00ffff.github.io/0xBTC-Stats/> (GitHub: <https://github.com/0x1d00ffff/0xBTC-Stats>)"),
    CmdDef(
        ["ann", "bitcoin talk"],
        "[ANN] 0xBitcoin [0xBTC]: <https://bitcointalk.org/index.php?topic=3039182.0>"),
    CmdDef(
        ["merch", "merchandise", "tshirt", "0xbtcat"],
        "0xBTC Merch: <https://www.teepublic.com/user/0xbtcat>"),
    CmdDef(
        ["mvis", "mining visualizer", "mvis tokenminer"],
        "MVIS-Tokenminer: <https://github.com/mining-visualizer/MVis-tokenminer/releases>"),
    CmdDef(
        ["cosmic"],
        "COSMiC: <https://bitbucket.org/LieutenantTofu/cosmic-v3/downloads/>"),
    CmdDef(
        ["az", "nabiki", "gaiden"],
        "Azlehria: <https://github.com/azlehria/0xbitcoin-gpuminer/releases>"),
]


# todo: encapsulate these
last_updated = 0
command_count = 0
client = None



# look through an input_string, return True if it looks like a match for command
# if exhaustive_search is true, look in the middle of string for commands - otherwise only check beginning
# if permute_whitespace is true, replace spaces with dashes etc and also match those
# if require_cmd_char is true, search only for `!command` - otherwise allow `command`
def string_contains_command(input_string, command, exhaustive_search=False, permute_whitespace=True, require_cmd_char=True):
    possible_commands = [command]
    if permute_whitespace:
        possible_commands.append(command.replace(' ', '-'))
        possible_commands.append(command.replace(' ', '_'))
        possible_commands.append(command.replace(' ', ''))

    if exhaustive_search:
        for possible_command in possible_commands:
            if require_cmd_char:
                possible_command = _COMMAND_CHARACTER+possible_command
            if possible_command in input_string:
                return True
    else:
        for possible_command in possible_commands:
            if require_cmd_char:
                possible_command = _COMMAND_CHARACTER+possible_command
            if input_string.startswith(possible_command):
                return True

    return False

# similar to string_contains_command but accepts a list of multiple command synonyms
def string_contains_any(input_string, command_list, exhaustive_search=False, permute_whitespace=True, require_cmd_char=True):
    for command in command_list:
        if string_contains_command(input_string, command, exhaustive_search, permute_whitespace, require_cmd_char):
            return True

    return False

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
    if number < 0.000000000001:
        return "{:.2E}".format(number)
    if number < 0.00000001:
        return "{:.12f}".format(number)
    if number < 0.00001:
        return "{:.8f}".format(number)
    elif number < 0.001:
        return "{:.5f}".format(number)
    elif number < 1.0:
        return "{:.3f}".format(number)
    elif number < 1000.0:
        return "{:.2f}".format(number)
    elif number < 10000.0:
        return "{:,.1f}".format(number)

    return "{:,.0f}".format(number)

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

    token_price_usd = apis.price_eth(_CURRENCY) * apis.eth_price_usd()

    if token_price_usd == 0:
        return ":shrug:"

    return "1 {} = **{}** 0xBTC (${})".format(item_name, 
                                              prettify_decimals(item_price / token_price_usd), 
                                              to_readable_thousands(item_price))


def cmd_price(source='aggregate'):
    if apis.last_updated_time(api_name=source) == 0:
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(apis.short_url(api_name=source))
    
    token_price = apis.price_eth(_CURRENCY, api_name=source) * apis.eth_price_usd()
    eth_price = float(apis.eth_price_usd(api_name=source))

    percent_change_str = ""

    if apis.change_24h(_CURRENCY, api_name=source) == None:
        percent_change_str = ""
    else:
        # TODO: enable percentage once enclaves is stable
        percent_change_str = "**{:+.2f}**% {} ".format(100.0 * apis.change_24h(_CURRENCY, api_name=source),
                                                       percent_change_to_emoji(apis.change_24h(_CURRENCY, api_name=source)),)
        pass

    fmt_str = "{}{}: {}({:.5f} Ξ) {}{}[<{}>]"
    result = fmt_str.format('' if source == 'aggregate' else '**{}** '.format(source),
                            seconds_to_readable_time(time.time()-apis.last_updated_time(api_name=source)),
                            '' if token_price == 0 else '**${:.3f}** '.format(token_price), 
                            apis.price_eth(_CURRENCY, api_name=source), 
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


def cmd_ethereumprice():
    if apis.last_updated_time() == 0:
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(apis.short_url())

    if apis.eth_price_usd() == 0:
        return ":shrug:"

    fmt_str = "{}: **${:.0f}**"
    result = fmt_str.format(seconds_to_readable_time(time.time()-apis.last_updated_time()), apis.eth_price_usd())
    return result


def cmd_volume():
    if apis.last_updated_time() == 0:
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(apis.short_url())

    total_eth_volume = 0
    total_btc_volume = 0
    response = ""

    #for source in ['Enclaves DEX', 'Fork Delta', 'Mercatox', 'IDEX', 'Hotbit']:
    for source in ['Enclaves DEX', 'Fork Delta', 'Mercatox', 'IDEX']:
        volume_eth = apis.volume_eth(_CURRENCY, api_name=source)
        volume_btc = apis.volume_btc(_CURRENCY, api_name=source)
        total_eth_volume += volume_eth
        total_btc_volume += volume_btc
        response += "{}: $**{}**({}Ξ) ".format(source, prettify_decimals(volume_eth * apis.eth_price_usd()), prettify_decimals(volume_eth))
        if volume_btc != 0:
            response += "+ $**{}**({}₿) ".format(prettify_decimals(volume_btc * apis.btc_price_usd()), prettify_decimals(volume_btc))

    response += "\n"
    response += "Total: $**{}**({}Ξ+{}₿)".format(prettify_decimals((total_eth_volume * apis.eth_price_usd()) + (total_btc_volume * apis.btc_price_usd())), prettify_decimals(total_eth_volume), prettify_decimals(total_btc_volume))

    return response


def cmd_ratio():
    if apis.last_updated_time() == 0:
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(apis.short_url())

    token_price_usd = apis.price_eth(_CURRENCY) * apis.eth_price_usd()

    if token_price_usd == 0:
        return ":shrug:"

    return "1 BTC : {:,.0f} 0xBTC".format(apis.btc_price_usd() / token_price_usd)

"""Convert from source currency to dest currency. _amount_ indicates total
amount of source currency. Example:
>>> convert(100, 'cents', 'usd')
1
"""
def convert(amount, src, dest):
    src = src.lower()
    dest = dest.lower()
    amount = float(amount)

    token_price_usd = apis.price_eth(_CURRENCY) * apis.eth_price_usd()

    if src in ['0xbtc', '0xbitcoins', '0xbitcoin']:
        usd_value = token_price_usd * amount
    elif src in ['0xsatoshis', '0xsatoshi', 'satoastis', 'satoasti', 'crumbs', 'crumb']:
        usd_value = token_price_usd * amount / 10**8
    elif src in ['eth', 'ethereum']:
        usd_value = apis.eth_price_usd() * amount
    elif src == 'wei':
        usd_value = apis.eth_price_usd() * amount / 10**18
    elif src in ['btc', 'bitcoins', 'bitcoin']:
        usd_value = apis.btc_price_usd() * amount
    elif src in ['satoshis', 'satoshi']:
        usd_value = apis.btc_price_usd() * amount / 10**8
    elif src in ['mbtc', 'millibtc', 'millibitcoins', 'millibitcoin']:
        usd_value = apis.btc_price_usd() * amount / 1000.0
    elif src in ['usd', 'dollars', 'dollar', 'bucks', 'buck']:
        usd_value = amount
    elif src in ['cents', 'cent']:
        usd_value = amount / 100.0
    else:
        return "Bad currency ({}). 0xbtc, 0xsatoshis, eth, wei, btc, mbtc, satoshis, and usd are supported.".format(src)

    if dest in ['0xbtc', '0xbitcoins', '0xbitcoin']:
        result = usd_value / token_price_usd
    elif dest in ['0xsatoshis', '0xsatoshi', 'satoastis', 'satoasti', 'crumbs', 'crumb']:
        result = 10**8 * usd_value / token_price_usd
    elif dest in ['eth', 'ethereum']:
        result = usd_value / apis.eth_price_usd()
    elif dest == 'wei':
        result = 10**18 * usd_value / apis.eth_price_usd()
    elif dest in ['btc', 'bitcoins', 'bitcoin']:
        result = usd_value / apis.btc_price_usd()
    elif dest in ['satoshis', 'satoshi']:
        result = 10**8 * usd_value / apis.btc_price_usd()
    elif dest in ['mbtc', 'millibtc', 'millibitcoins', 'millibitcoin']:
        result = usd_value * 1000.0 / apis.btc_price_usd()
    elif dest in ['usd', 'dollars', 'dollar', 'bucks', 'buck']:
        result = usd_value
    elif dest in ['cents', 'cent']:
        result = usd_value * 100.0
    else:
        return "Bad currency ({}). 0xbtc, 0xsatoshis, eth, wei, btc, mbtc, satoshis, and usd are supported.".format(dest)

    amount = prettify_decimals(amount)
    result = prettify_decimals(result)

    return "{} {} = **{}** {}".format(amount, src, result, dest)


def cmd_convert(message):
    if apis.last_updated_time() == 0:
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(apis.short_url())

    split = message.split()
    
    # example input: '!convert 1 usd to 0xbtc'
    try:
        _, amount, src, _, dest = split
    except ValueError:
        pass
    except:
        return "Something went wrong :sob: try this: `!convert 1 eth to 0xbtc`"
    else:
        return convert(amount, src, dest)
    
    # example input: '!convert 1 usd 0xbtc'
    try:
        _, amount, src, dest = split
    except ValueError:
        pass
    except:
        return "Something went wrong :sob: try this: `!convert 1 eth to 0xbtc`"
    else:
        return convert(amount, src, dest)

    # ValueError exceptions lead here
    return "Something went wrong :sob: try this: `!convert 1 eth to 0xbtc`"


async def update_status(client, stat_str):
    logging.info('changing status to %s', repr(stat_str))
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

        try:
            # price in usd is conritional - only show it if eth price is not 0 (an error)
            price_usd = apis.price_eth(_CURRENCY) * apis.eth_price_usd()
            usd_str = "" if price_usd == 0 else "${:.2f}  |  ".format(price_usd)

            # wait until at least one successful update to show status
            if apis.last_updated_time() != 0:
                fmt_str = "{}{:.5f} Ξ ({})"
                await update_status(client, fmt_str.format(usd_str,
                                                           apis.price_eth(_CURRENCY),
                                                           seconds_to_readable_time(time.time()-apis.last_updated_time())))
        except:
            logging.exception('failed to change status')

        await asyncio.sleep(_UPDATE_RATE)

    # this throws an exception which causes the program to restart
    # in normal operation, we should never reach this
    raise RuntimeError('update_price_task loop stopped - something is wrong')

# These commands will work in any channel (TODO: move to a fn)
def handle_global_command(command_str):
    for cmd_def in _GLOBAL_COMMANDS:
        if string_contains_any(command_str, cmd_def.keywords):
            return cmd_def.response
    return None

def handle_trading_command(command_str):
    msg = None
    if string_contains_any(command_str, ['price', 'rice']):
        if string_contains_any(command_str, [
                'enclaves',
                'encalves'], exhaustive_search=True, require_cmd_char=False):
            msg = cmd_price(source="Enclaves DEX")
        elif string_contains_any(command_str, [
                'fd',
                'fork delta'], exhaustive_search=True, require_cmd_char=False):
            msg = cmd_price(source="Fork Delta")
        elif string_contains_any(command_str, [
                'merc', 
                'mercatox', 
                'meractox', 
                'mecratox'], exhaustive_search=True, require_cmd_char=False):
            msg = cmd_price(source="Mercatox")
        elif string_contains_any(command_str, [
                'idex'], exhaustive_search=True, require_cmd_char=False):
            msg = cmd_price(source="IDEX")
        #elif string_contains_any(command_str, [
        #        'hotbit',
        #        'hot bit'], exhaustive_search=True, require_cmd_char=False):
        #    msg = cmd_price(source="Hotbit")
        elif string_contains_any(command_str, [
                'btc',
                'bitcoin'], exhaustive_search=True, require_cmd_char=False):
            msg = cmd_bitcoinprice()
        elif string_contains_any(command_str, [
                'eth',
                'ethereum'], exhaustive_search=True, require_cmd_char=False):
            msg = cmd_ethereumprice()
        elif string_contains_any(command_str, [
                'all',
                'prices'], exhaustive_search=True, require_cmd_char=False):
            msg = ""
            for api in sorted(apis.alive_apis, key=lambda a: a.api_name):
                # this skips apis not directly tracking 0xbtc
                if api.currency_symbol != _CURRENCY:
                    continue
                single_line = cmd_price(source=api.api_name)
                # TODO: remove this when 'alive_apis' excludes apis correctly
                if single_line.startswith('not sure yet'):
                    continue
                msg += single_line + '\n'
        else:
            msg = cmd_price()

    if string_contains_any(command_str, ['vol', 'völ']):
        msg = cmd_volume()

    if string_contains_any(command_str, ['zj']):
        msg = "If you have to ask big man, you can't afford it."

    if string_contains_any(command_str, ['bettervolume']):
        msg = ':star2:'*10 + '\n' + cmd_volume() + '\n' + ':star2:'*10

    if string_contains_any(command_str, ['ratio']):
        msg = cmd_ratio()

    if string_contains_any(command_str, ['bitcoin price', 'btc price', 'btc']):
        msg = cmd_bitcoinprice()

    if string_contains_any(command_str, ['ethereum price', 'eth price', 'eth']):
        msg = cmd_ethereumprice()

    if string_contains_any(command_str, ['convert', 'concert', 'conver']):
        msg = cmd_convert(command_str)

    if string_contains_any(command_str, ['hug']):
        msg = "*SQUEEEEEEEEEEEEE* There, there. It's alright now. Botty is gonna make it all better."

    if string_contains_any(command_str, ['hi', 'hey bot']):
        msg = "Sup :sunglasses:"

    # TODO: enable when there is a source for this info
    #if string_contains_any(command_str, ['binance', 'binants', 'bine ants']):
    #    msg = "Listing fee for binance is 10-30 BTC"

    for price, names in _EXPENSIVE_STUFF:
        if string_contains_any(command_str, names, exhaustive_search=True):
            correct_name = names[0]
            msg = cmd_compare_price_vs(correct_name, price)
            break

    return msg

async def send_discord_msg(channel, message):
    try:
        await client.send_message(channel, message)
    except discord.errors.Forbidden:
        logging.debug('no permission: {} [{}]'.format(channel.name, channel.id))


def configure_client():

    client.loop.create_task(update_price_task())

    @client.event
    async def on_message(message):
        global command_count
        response = None

        # we do not want the bot to reply to itself
        if message.author == client.user:
            return
        # we do not want the bot to reply to other bots
        if message.author.bot:
            return

        command_str = message.content.lower().strip()

        # allow '! command' since some platforms autocorrect to add a space
        if command_str.startswith(_COMMAND_CHARACTER + ' '):
            command_str = _COMMAND_CHARACTER + command_str[2:]

        # allow '!!command', its a common typo
        if command_str.startswith(_COMMAND_CHARACTER+_COMMAND_CHARACTER):
            command_str = _COMMAND_CHARACTER + command_str[2:]

        # allow unicode ! (replace with ascii version)
        if _COMMAND_CHARACTER == '!':
            if command_str.startswith('！'):
                command_str = '!' + command_str[1:]

        # trading commands are ignored in blacklisted channels
        if message.channel.id not in _BLACKLISTED_CHANNEL_IDS:
            response = handle_trading_command(command_str)
            if response:
                await send_discord_msg(message.channel, response);
                return

        response = handle_global_command(command_str)
        if response:
            await send_discord_msg(message.channel, response);
            return


        # If command starts with _COMMAND_CHARACTER and we have not returned yet, it was unrecognized.
        if command_str.startswith(_COMMAND_CHARACTER):
            logging.info('UNKNOWN cmd {}'.format(repr(command_str)))


    @client.event
    async def on_ready():
        logging.info('Logged in as {} ({})'.format(client.user.name,
                                                   client.user.id))

        logging.info('In {} servers'.format(len(client.servers)))
        for server in client.servers:
            logging.info('  {} [id:{}] ({} Members), {}'.format(server.name, server.id, server.member_count, server.region))


def setup_logging():
    path = '.'
    filename = 'debug.log'

    # set up logging to file
    filehandler = logging.FileHandler("{0}/{1}".format(path, filename),
                                      mode='a',
                                      encoding='utf-8')
    filehandler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s, %(name)-12s, %(levelname)-8s, %(message)s',
                                  datefmt='%m-%d-%y %H:%M:%S')
    filehandler.setFormatter(formatter)

    # define a Handler which writes INFO messages or higher to the sys.stderr
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s [%(levelname)-5.5s] %(message)s',
                                  datefmt='%H:%M:%S')
    console.setFormatter(formatter)

    logging.basicConfig(handlers=[filehandler, console],
        level=logging.DEBUG)

    # make websocket be quiet (no traces to log)
    websocket.enableTrace(False)
    logging.getLogger('websockets').setLevel(logging.WARNING)
    # make discord be quiet
    logging.getLogger('discord').setLevel(logging.WARNING)

if __name__ == "__main__":
    setup_logging()

    logging.info('{} version {}'.format(_PROGRAM_NAME, _VERSION))
    logging.info('discord.py version {}'.format(discord.__version__))
    loop = asyncio.get_event_loop()
    client = discord.Client()
    configure_client()
    apis = MultiApiManager(
    [
        EnclavesAPI(_CURRENCY),
        LiveCoinWatchAPI('ETH'),
        ForkDeltaAPI(_CURRENCY),
        MercatoxAPI(_CURRENCY),
        IDEXAPI(_CURRENCY),
        #HotbitAPI(_CURRENCY),
    ])
    while True:
        try:
            asyncio.get_event_loop().run_until_complete(keep_running(client, TOKEN))
        except SystemExit:
            raise
        except KeyboardInterrupt:
            raise
        except:
            logging.exception('bot ded:')
            time.sleep(10)  # wait a little time to prevent cpu spins
