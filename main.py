# -*- coding: UTF-8 -*-
"""
0xBitcoin Discord Price Bot

TODO: move commands out of main.py, this file is getting long
"""

import sys
assert sys.version_info >= (3,6), "requires python > 3.6+"

import time
import datetime
import socket
import websocket  # for websocket.enableTrace(False)
import websockets  # for websockets.exceptions.ConnectionClosed
import asyncio
import logging
import collections
import random
import re

from web3 import Web3
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
import ping_wrapper

from persistent_storage import Storage
import configuration as config

_PROGRAM_NAME = "0xbtc-discord-price-bot"
_VERSION = "0.2.1"

CmdDef = collections.namedtuple('CmdDef', ['keywords', 'response'])
# commands that work in all channels (ignores the blacklist)
_GLOBAL_COMMANDS = [
    CmdDef(
        ['help', 'commands', 'bot'],
        "available commands: `price volume ratio convert bitcoinprice lambo whitehouse millionaire billionaire`\nquick link commands: `whitepaper website ann contract stats merch mvis cosmic az ss3`"),
    CmdDef(
        ['white paper'],
        "0xBitcoin Whitepaper: <https://github.com/0xbitcoin/white-paper>"),
    CmdDef(
        ["site", "web site"],
        "0xBitcoin Website: <https://0xbitcoin.org/>"),
    CmdDef(
        ["ann", "bitcoin talk"],
        "[ANN] 0xBitcoin [0xBTC]: <https://bitcointalk.org/index.php?topic=3039182.0>"),
    CmdDef(
        ["contract", "address"],
        "0xBitcoin Contract: 0xB6eD7644C69416d67B522e20bC294A9a9B405B31 [<https://bit.ly/2y1WlMB>]"),
    CmdDef(
        ["stats", "statistics"],
        "0xBitcoin Stats: <https://0x1d00ffff.github.io/0xBTC-Stats/> (GitHub: <https://github.com/0x1d00ffff/0xBTC-Stats>)"),
    CmdDef(
        ["miner", "miners", "software"],
        "Try !mvis !cosmic !az !ss3"),
    CmdDef(
        ["lava"],
        "Lava Wallet: <https://lavawallet.io/> (Development:<https://github.com/lavawallet> and <http://forum.0xbtc.io/c/development/lava-network>)"),
    CmdDef(
        ["merch", "merchandise", "tshirt", "0xbtcat", "beeherder"],
        "0xBTC Merch: <https://www.teepublic.com/user/0xbtcat>"),
    CmdDef(
        ["mvis", "mining visualizer", "mvis tokenminer"],
        "MVIS-Tokenminer: <https://github.com/mining-visualizer/MVis-tokenminer/releases>"),
    CmdDef(
        ["cosmic", "lttofu"],
        "COSMiC: <https://bitbucket.org/LieutenantTofu/cosmic-v3/downloads/>"),
    CmdDef(
        ["az", "azlehria", "nabiki", "gaiden"],
        "Azlehria: <https://github.com/azlehria/0xbitcoin-gpuminer/releases>"),
    CmdDef(
        ["soliditysha3miner", "armano", "ss3"],
        "SoliditySHA3Miner: <https://github.com/lwYeo/SoliditySHA3Miner/releases>"),
]


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
                possible_command = config.COMMAND_CHARACTER+possible_command
            if possible_command in input_string:
                return True
    else:
        for possible_command in possible_commands:
            if require_cmd_char:
                possible_command = config.COMMAND_CHARACTER+possible_command
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

def round_to_n_decimals(x, n=1):
    from math import log10, floor
    assert n >= 1
    return round(x, -int(floor(log10(abs(x))))+n-1)

def prettify_decimals(number):
    if number == 0:
        return "0"
    if number < 1e-12:
        rounded = round_to_n_decimals(number, 3)
        return "{:.2e}".format(rounded)
    if number < 1.0:
        rounded = round_to_n_decimals(number, 3)
        return "{:.14f}".format(rounded).rstrip("0")
    if number < 10.0:
        rounded = round_to_n_decimals(number, 4)
        return "{:.3f}".format(rounded)
    if number < 10000.0:
        return "{:.2f}".format(number)
    if number < 1e9:
        return "{:,.0f}".format(number)
    if number < 1e15:
        return to_readable_thousands(number, unit_type='long')

    return "{:.2e}".format(number).replace("+", "")

def to_readable_thousands(value, unit_type='short', decimals=1):
    if unit_type == "long":
        units = ['', ' thousand', ' million', ' billion', ' trillion', ' quadrillion', ' sextillion', ' septillion', ' octillion', ' nonillion']
    if unit_type == "short":
        units = ['', 'k', 'm', 'b', 't', 'p', 's']
    if unit_type == "hashrate":
        units = ['H/s', ' Kh/s', ' Mh/s', ' Gh/s', ' Th/s', ' Ph/s', ' Eh/s', ' Zh/s', ' Yh/s']
    if unit_type == "short_hashrate":
        units = ['H', ' Kh', ' Mh', ' Gh', ' Th', ' Ph', ' Eh', ' Zh', ' Yh']

    for unit in units:
        if value < 1000:
            return "{:.1f}{}".format(value, unit)
        value /= 1000

    fmt_str = "{:." + decimals + "f}{}"
    return fmt_str.format(value*1000, units[-1])

def seconds_to_n_time_ago(seconds):
    if seconds < 60:
        return 'now'

    minutes = seconds / 60
    if minutes < 60:
        return "{:.0f}m ago".format(minutes)

    return "{:.0f}h ago".format(minutes / 60)

def seconds_to_time(seconds, granularity=2):
    result = []
    intervals = (
        ('centuries', 60*60*24*7*4.34524*12*10*10),
        ('decades',   60*60*24*7*4.34524*12*10),
        ('years',     60*60*24*7*4.34524*12),
        ('months',    60*60*24*7*4.34524),
        ('weeks',     60*60*24*7),
        ('days',      60*60*24),
        ('hours',     60*60),
        ('minutes',   60),
        ('seconds',   1),
    )

    if seconds == 0:
        return '0 seconds'

    for name, multiplier in intervals:
        value = seconds // multiplier
        if value > 0:
            seconds -= value * multiplier
            if value == 1:
                name = name.rstrip('s')
            result.append("{:.0f} {}".format(value, name))
    return ', '.join(result[:granularity])

def cmd_compare_price_vs(item_name="lambo", item_price=200000):
    if apis.last_updated_time() == 0:
        return ":shrug:"

    token_price_usd = apis.price_eth(config.CURRENCY) * apis.eth_price_usd()

    if token_price_usd == 0:
        return ":shrug:"

    return "1 {} = **{}** 0xBTC (${})".format(item_name, 
                                              prettify_decimals(item_price / token_price_usd), 
                                              to_readable_thousands(item_price))

def cmd_price(source='aggregate'):
    if (apis.last_updated_time(api_name=source) == 0):
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(apis.short_url(api_name=source))
    
    token_price = apis.price_eth(config.CURRENCY, api_name=source) * apis.eth_price_usd()
    eth_price_on_this_exchange = float(apis.eth_price_usd(api_name=source))

    # Enclaves usually fails this way
    if token_price == 0 and eth_price_on_this_exchange == 0:
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(apis.short_url(api_name=source))

    percent_change_str = ""
    if apis.change_24h(config.CURRENCY, api_name=source) == None:
        percent_change_str = ""
    elif apis.change_24h(config.CURRENCY, api_name=source) == 0:
        percent_change_str = "**0**% "
    else:
        percent_change_str = "**{:+.2f}**% {} ".format(100.0 * apis.change_24h(config.CURRENCY, api_name=source),
                                                       percent_change_to_emoji(apis.change_24h(config.CURRENCY, api_name=source)),)
    fmt_str = "{}{}: {}({:.5f} Ξ) {}{}[<{}>]"
    result = fmt_str.format('' if source == 'aggregate' else '**{}** '.format(source),
                            seconds_to_n_time_ago(time.time()-apis.last_updated_time(api_name=source)),
                            '' if token_price == 0 else '**${:.3f}** '.format(token_price), 
                            apis.price_eth(config.CURRENCY, api_name=source), 
                            percent_change_str,
                            '' if eth_price_on_this_exchange == 0 else '(ETH: **${:.0f}**) '.format(eth_price_on_this_exchange), 
                            apis.short_url(api_name=source))
    return result

def cmd_priceall():
    msg = ""
    for api in sorted(apis.alive_apis, key=lambda a: a.api_name):
        # this skips CMC and apis not directly tracking 0xbtc
        if api.currency_symbol != config.CURRENCY or api.api_name == "Coin Market Cap":
            continue
        single_line = cmd_price(source=api.api_name)
        # TODO: remove this when 'alive_apis' excludes apis correctly
        if single_line.startswith('not sure yet'):
            continue
        msg += single_line + '\n'
    if msg == "":
        return ":shrug:"
    return msg

def cmd_bitcoinprice():
    if apis.last_updated_time() == 0:
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(apis.short_url())

    if apis.btc_price_usd() == 0:
        return ":shrug:"

    fmt_str = "{}: **${:.0f}**"
    result = fmt_str.format(seconds_to_n_time_ago(time.time()-apis.last_updated_time()),
                            apis.btc_price_usd())
    return result

def cmd_ethereumprice():
    if apis.last_updated_time() == 0:
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(apis.short_url())

    if apis.eth_price_usd() == 0:
        return ":shrug:"

    fmt_str = "{}: **${:.0f}**"
    result = fmt_str.format(seconds_to_n_time_ago(time.time()-apis.last_updated_time()), 
                            apis.eth_price_usd())
    return result

def cmd_marketcap():
    if apis.last_updated_time() == 0:
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(apis.short_url())

    token_price = apis.price_eth(config.CURRENCY) * apis.eth_price_usd()
    marketcap = token.tokens_minted * token_price

    if marketcap == 0:
        return ":shrug:"

    fmt_str = "Marketcap: **${}** (Price: ${} Circulating Supply: {})"
    result = fmt_str.format(prettify_decimals(marketcap),
                            prettify_decimals(token_price),
                            prettify_decimals(token.tokens_minted))
    return result

def cmd_difficulty():
    if token.difficulty == None:
        return ":shrug:"

    fmt_str = "Current difficulty: **{}** ({} until next retarget)"
    result = fmt_str.format(to_readable_thousands(token.difficulty, unit_type='long'),
                            seconds_to_time(token.seconds_until_readjustment))
    return result

def cmd_blocktime():
    if token.seconds_per_reward == None:
        return ":shrug:"

    fmt_str = "Current average block time: **{}** (average taken over the last {})"
    result = fmt_str.format(seconds_to_time(token.seconds_per_reward),
                            seconds_to_time(token.seconds_since_readjustment, granularity=1))
    return result

def cmd_hashrate():
    if token.estimated_hashrate == None:
        return ":shrug:"

    fmt_str = "Estimated hashrate: **{}**"
    result = fmt_str.format(to_readable_thousands(token.estimated_hashrate, unit_type="hashrate", decimals=2))
    return result

def cmd_tokens_minted():
    if token.tokens_minted == None:
        return ":shrug:"

    fmt_str = "Tokens in circulation: **{}** / {} {}"
    result = fmt_str.format(prettify_decimals(token.tokens_minted), 
                            prettify_decimals(token.total_supply),
                            token.SYMBOL)
    return result

def cmd_era():
    if token.era == None:
        return ":shrug:"

    if token.era == 39:
        return "In era 39 / 39"

    fmt_str = "Current era: **{}** / 39.  In {} the reward will drop to **{}** {}"
    result = fmt_str.format(token.era,
                            seconds_to_time(token.seconds_remaining_in_era),
                            token.reward / 2,
                            token.SYMBOL)
    return result

def cmd_tokens_burned():
    if token.addr_0_balance == None:
        return ":shrug:"

    fmt_str = "**{}** {} burned [<https://bit.ly/2AulG0C>]"
    result = fmt_str.format(token.addr_0_balance, token.SYMBOL)
    return result

async def cmd_holders(message, author_id, raw_message):
    if token.addr_0_balance == None:
        return ":shrug:"

    await client.send_file(raw_message.channel,
                           etherscan.saved_holders_chart_filename)

    # # Async
    # await bot.send_file(channel, "filepath.png", content="...", filename="...")

    # # Rewrite
    # file = discord.File("filepath.png", filename="...")
    # await channel.send("content", file=file)

    return 'OK-noresponse'

def cmd_income(message, author_id, raw_message):
    if token.difficulty is None:
        return "Sorry, I'm having problems with my APIs..."

    try:
        command, hashrate = message.split(maxsplit=1)
    except:
        return "Bad hashrate; try `!income 5`, `!income 300mh`, or `!income 2.8gh`"

    multipliers = (
        ('k', 1e3),
        ('m', 1e6),
        ('g', 1e9),
        ('t', 1e12),
        ('p', 1e15),
        ('e', 1e18),
        ('z', 1e21),
        ('y', 1e24))
    selected_multiplier = 1e9
    for char, mult in multipliers:
        if char in hashrate:
            selected_multiplier = mult

    match = re.match("([<\d.]+)", hashrate)
    if not match:
        return "Bad hashrate; try `!income 5`, `!income 300mh`, or `!income 2.8gh`"
    hashrate = float(match.group(1)) * selected_multiplier

    tokens_per_day = 0.8 * 86400 * token.reward * hashrate / ((2**22) * token.difficulty)
    seconds_per_block = 1.2 * ((2**22) * token.difficulty) / hashrate

    if tokens_per_day > 1:
        tokens_over_time_str = "**{}** tokens/day".format(prettify_decimals(tokens_per_day))
    else:
        tokens_over_time_str = "**{}** tokens/week".format(prettify_decimals(tokens_per_day*7))

    fmt_str = "Income for {}: {}; **{}** per block solo"
    return fmt_str.format(to_readable_thousands(hashrate, unit_type='hashrate'),
                          tokens_over_time_str,
                          seconds_to_time(seconds_per_block))

def cmd_mine(message, author_id, raw_message):
    if token.mining_target is None:
        return "Sorry, I'm having problems with my APIs..."

    try:
        address = storage.user_addresses.get(author_id)
    except KeyError:
        return "Looks like you don't have a public address set; run `!setaddress 0xAAA...` first"

    try:
        command, nonce = message.split(maxsplit=1)
    except:
        return "Bad nonce; try `mine 0xABBA`, `!mine 27`, or `!mine message`"

    nonce, digest = token.get_digest_for_nonce_str(nonce, address)
    resulting_difficulty = token.MAX_TARGET / Web3.toInt(digest)
    percent_of_the_way_to_full_target = token.mining_target / Web3.toInt(digest)

    fmt_str = "Nonce `0x{}...` -> Digest `0x{}...`\nDiff: {} ({}% of the way to a full solution)"
    result = fmt_str.format(nonce[:5].hex(),
                            digest[:5].hex(),
                            prettify_decimals(resulting_difficulty), 
                            prettify_decimals(percent_of_the_way_to_full_target * 100.0))

    if resulting_difficulty > storage.top_miner_difficulty.get():
        fmt_str = "\nNew best share! Previous was `0x{}...` (Difficulty: {}) by {}"
        result += fmt_str.format(storage.top_miner_digest.get()[:5].hex(),
                                 prettify_decimals(storage.top_miner_difficulty.get()),
                                 storage.top_miner_name.get())

        storage.top_miner_difficulty.set(resulting_difficulty)
        storage.top_miner_name.set(raw_message.author.name)
        storage.top_miner_id.set(author_id)
        storage.top_miner_digest.set(digest)

    # in case someone solves a block... never going to happen but why not?
    if Web3.toInt(digest) <= token.mining_target:
        result += "\n~~~~~"
        result += "\n:money_mouth: You seem to have solved a block!? Try your luck here [<https://etherscan.io/address/0xb6ed7644c69416d67b522e20bc294a9a9b405b31#writeContract>]"
        result += "\nMake sure you log into metamask using the public address you have set here, and type these values into the mint() function:"
        result += "\n  nonce=`{}`".format(Web3.toHex(nonce))
        result += "\n  challenge_digest=`{}`".format(Web3.toHex(digest))
        result += "\n~~~~~"

    return result

def cmd_bestshare():
    fmt_str = "Best share digest: `0x{}...` (Difficulty: {}) by {}"
    result = fmt_str.format(storage.top_miner_digest.get()[:16].hex(),
                            prettify_decimals(storage.top_miner_difficulty.get()),
                            storage.top_miner_name.get())
    return result

def cmd_all_time_high():
    import platform
    time_eth = datetime.datetime.fromtimestamp(storage.all_time_high_eth_timestamp.get())
    time_usd = datetime.datetime.fromtimestamp(storage.all_time_high_usd_timestamp.get())

    if platform.system() == "Linux":
        time_eth = time_eth.strftime("%a %B %-e %Y")
        time_usd = time_usd.strftime("%a %B %-e %Y")
    else:
        time_eth = time_eth.strftime("%a %B %#e %Y")
        time_usd = time_usd.strftime("%a %B %#e %Y")

    if time_eth == time_usd:
        fmt_str = "All time high: **{}Ξ** **${}** ({})"
        result = fmt_str.format(prettify_decimals(storage.all_time_high_eth_price.get()),
                                prettify_decimals(storage.all_time_high_usd_price.get()),
                                time_usd)
    else:
        fmt_str = "All time high: \n**{}Ξ** ({})  **${}** ({})"
        result = fmt_str.format(prettify_decimals(storage.all_time_high_eth_price.get()),
                                time_eth,
                                prettify_decimals(storage.all_time_high_usd_price.get()),
                                time_usd)
    return result

def cmd_set_all_time_high(message, author_id, raw_message):
    if author_id not in config.PRIVILEGED_USER_IDS:
        fmt_str = 'User not allowed to run cmd_set_all_time_high: {} ({})'
        logging.info(fmt_str.format(author_id, raw_message.author.name))
        return

    try:
        command, price_eth, time_eth, price_usd, time_usd = message.split()
        price_eth = float(price_eth)
        time_eth = datetime.datetime.strptime(time_eth, '%Y-%m-%d').timestamp()
        price_usd = float(price_usd.replace('$', ' '))
        time_usd = datetime.datetime.strptime(time_usd, '%Y-%m-%d').timestamp()

        assert 0 <= price_eth <= 1e20
        assert 0 <= price_usd <= 1e20
    except:
        return "Error parsing; try `!setath <price_eth> YYYY-MM-DD <price_usd> YYYY-MM-DD`"

    storage.all_time_high_eth_price.set(price_eth)
    storage.all_time_high_eth_timestamp.set(time_eth)
    storage.all_time_high_usd_price.set(price_usd)
    storage.all_time_high_usd_timestamp.set(time_usd)

    result = "New ATH set!\n" + cmd_all_time_high()
    return result

async def cmd_set_user_address(message, author_id, raw_message):
    try:
        address = message.split()[-1]
    except:
        return "Something went wrong setting your public address... try `!setaddress 0xAAA...`"

    if address == "dontcare":
        address = "0x0000000000000000000000000000000000000000"

    if not Web3.isAddress(address):
        return "Something went wrong setting your public address... try `!setaddress 0xAAA...`. You can use `!setaddress dontcare` if you don't care."

    address = Web3.toChecksumAddress(address)
    storage.user_addresses.set(author_id, address)

    await client.add_reaction(raw_message,"\U0001F44D")  # :thumbsup:
    return "OK-noresponse"

def cmd_bot_command(message, author_id, raw_message):
    if author_id not in config.PRIVILEGED_USER_IDS:
        fmt_str = 'User not allowed to run cmd_bot_command: {} ({})'
        logging.info(fmt_str.format(author_id, raw_message.author.name))
        return

    try:
        message_parts = message.split()

        if message_parts[1] == 'poweroff':
            if message_parts[-1] == 'really':
                raise SystemExit('Exit requested by user {}'.format(raw_message.author.name))
            else:
                return "Really? If you're sure run `!botcommand poweroff really`"
    except SystemExit:
        raise
    except:
        return "Error parsing command"

    return "OK-noresponse"

def cmd_ping(message, author_id, raw_message):
    delta = datetime.datetime.utcnow() - raw_message.timestamp
    response = "Discord: {:.1f} ms\n".format(delta.total_seconds() * 1000.0)

    ping_times = ping_wrapper.ping_list(['api.infura.io', 'etherscan.io'])
    for url, latency in ping_times:
        if latency == None:
            response += "{}: down\n".format(url)
        else:
            response += "{}: {.1f} ms\n".format(url, latency)

    return response

def cmd_pools():
    all_pools = (
        ("Token Mining Pool", "http://TokenMiningPool.com", "0xeabe"),
        ("mike.rs pool", "http://mike.rs", "0x5021"),
        ("tosti.ro", "http://tosti.ro/", "0x540d"),
        # TODO: uncomment when extremehash finds a block
        #("ExtremeHash.io", "http://0xbtc.extremehash.io/", "0xbbdf"),
        )
    response = ""
    for name, url, address in all_pools:
        response += "{} <{}>\n".format(name, url)

    return response

def cmd_volume():
    if apis.last_updated_time() == 0:
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(apis.short_url())

    total_eth_volume = 0
    total_btc_volume = 0
    response = ""


    for api in sorted(apis.alive_apis, key=lambda a: a.api_name):
        # this skips CMC and apis not directly tracking 0xbtc
        if api.currency_symbol != config.CURRENCY or api.api_name == "Coin Market Cap":
            continue

        volume_eth = apis.volume_eth(config.CURRENCY, api_name=api.api_name)
        volume_btc = apis.volume_btc(config.CURRENCY, api_name=api.api_name)
        if volume_eth == 0 and volume_btc == 0:
            continue

        total_eth_volume += volume_eth
        total_btc_volume += volume_btc
        if apis.eth_price_usd() == 0:
            response += "{}: **{}Ξ** ".format(api.api_name, prettify_decimals(volume_eth))
        else:
            response += "{}: $**{}**({}Ξ) ".format(api.api_name, prettify_decimals(volume_eth * apis.eth_price_usd()), prettify_decimals(volume_eth))
        if volume_btc != 0:
            if apis.btc_price_usd() == 0:
                response += "+ **{}₿** ".format(prettify_decimals(volume_btc))
            else:
                response += "+ $**{}**({}₿) ".format(prettify_decimals(volume_btc * apis.btc_price_usd()), prettify_decimals(volume_btc))

    response += "\n"

    if apis.eth_price_usd() == 0 or apis.btc_price_usd() == 0:
        response += "Total: {}Ξ + {}₿".format(prettify_decimals(total_eth_volume), prettify_decimals(total_btc_volume))
    else:
        response += "Total: $**{}**({}Ξ+{}₿)".format(prettify_decimals((total_eth_volume * apis.eth_price_usd()) + (total_btc_volume * apis.btc_price_usd())), prettify_decimals(total_eth_volume), prettify_decimals(total_btc_volume))

    return response

def cmd_ratio():
    if apis.last_updated_time() == 0:
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(apis.short_url())

    token_price_usd = apis.price_eth(config.CURRENCY) * apis.eth_price_usd()
    if token_price_usd == 0:
        return ":shrug:"

    return "1 BTC : {:,.0f} 0xBTC".format(apis.btc_price_usd() / token_price_usd)

def cmd_rank():
    api_name = "Coin Market Cap"
    api_url = apis.short_url(api_name=api_name)

    if apis.last_updated_time() == 0:
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(api_url)

    rank = apis.rank(currency_symbol=config.CURRENCY,
                     api_name=api_name)
    if rank is None:
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(api_url)

    return "Rank: **{}** on {} [<{}>]".format(rank, api_name, api_url)

"""Convert from source currency to dest currency. _amount_ indicates total
amount of source currency. Example:
>>> convert(100, 'cents', 'usd')
1
"""
def convert(amount, src, dest):
    src = src.lower()
    dest = dest.lower()
    amount = float(amount)

    usd_value, result = None, None

    token_price_usd = apis.price_eth(config.CURRENCY) * apis.eth_price_usd()

    if src in ['0xbtc', '0xbitcoins', '0xbitcoin']:
        usd_value = token_price_usd * amount
    elif src in ['m0xbtc', 'milli0xbtc', 'milli0xbitcoin', 'milli0xbitcoins']:
        usd_value = token_price_usd * amount / 1000.0
    elif src in ['0xsatoshis', '0xsatoshi', 'satoastis', 'satoasti', 'crumbs', 'crumb']:
        usd_value = token_price_usd * amount / 10**8
    elif src in ['eth', 'ethereum']:
        usd_value = apis.eth_price_usd() * amount
    elif src == 'wei':
        usd_value = apis.eth_price_usd() * amount / 10**18
    elif src in ['btc', 'bitcoins', 'bitcoin']:
        usd_value = apis.btc_price_usd() * amount
    elif src in ['mbtc', 'millibtc', 'millibitcoins', 'millibitcoin']:
        usd_value = apis.btc_price_usd() * amount / 1000.0
    elif src in ['satoshis', 'satoshi']:
        usd_value = apis.btc_price_usd() * amount / 10**8
    elif src in ['usd', 'dollars', 'dollar', 'ddollar', 'bucks', 'buck']:
        usd_value = amount
    elif src in ['cents', 'cent']:
        usd_value = amount / 100.0
    else:
        for price, names in config.EXPENSIVE_STUFF:
            if string_contains_any(src, names, exhaustive_search=True, require_cmd_char=False):
                src = names[0]  # replace name with the non-typo'd version
                usd_value = amount * price
                break

    if usd_value == None:
        return "Bad currency ({}). 0xbtc, 0xsatoshis, eth, wei, btc, mbtc, satoshis, and usd are supported.".format(src)

    if dest in ['0xbtc', '0xbitcoins', '0xbitcoin']:
        result = usd_value / token_price_usd
    elif dest in ['m0xbtc', 'milli0xbtc', 'milli0xbitcoin', 'milli0xbitcoins']:
        result = 1000.0 * usd_value / token_price_usd
    elif dest in ['0xsatoshis', '0xsatoshi', 'satoastis', 'satoasti', 'crumbs', 'crumb']:
        result = 10**8 * usd_value / token_price_usd
    elif dest in ['eth', 'ethereum']:
        result = usd_value / apis.eth_price_usd()
    elif dest == 'wei':
        result = 10**18 * usd_value / apis.eth_price_usd()
    elif dest in ['btc', 'bitcoins', 'bitcoin']:
        result = usd_value / apis.btc_price_usd()
    elif dest in ['mbtc', 'millibtc', 'millibitcoins', 'millibitcoin']:
        result = usd_value * 1000.0 / apis.btc_price_usd()
    elif dest in ['satoshis', 'satoshi']:
        result = 10**8 * usd_value / apis.btc_price_usd()
    elif dest in ['usd', 'dollars', 'dollar', 'ddollar', 'bucks', 'buck']:
        result = usd_value
    elif dest in ['cents', 'cent']:
        result = usd_value * 100.0
    else:
        for price, names in config.EXPENSIVE_STUFF:
            if string_contains_any(dest, names, exhaustive_search=True, require_cmd_char=False):
                dest = names[0]  # replaces provided name with the non-typo'd version
                result = usd_value / price
                break

    if result == None:
        return "Bad currency ({}). 0xbtc, 0xsatoshis, eth, wei, btc, mbtc, satoshis, and usd are supported.".format(dest)

    amount = prettify_decimals(amount)
    result = prettify_decimals(result)

    return "{} {} = **{}** {}".format(amount, src, result, dest)

def cmd_convert(message):
    # example input: '!convert 1 usd to 0xbtc'
    if apis.last_updated_time() == 0 or apis.eth_price_usd() == 0 or apis.btc_price_usd() == 0:
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(apis.short_url())

    split = message.split()
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
            apis.update()
        except RuntimeError as e:
            logging.warning('Failed to update exchange APIs: {}'.format(e.msg))
        except:
            logging.exception('Failed to update exchange APIs')

        try:
            token.update()
        except RuntimeError as e:
            logging.warning('Failed to update contract info: {}'.format(e.msg))
        except:
            logging.exception('Failed to update contract info')

        if (time.time() - storage.last_holders_update_timestamp.get()) / 3600.0 > config.TOKEN_HOLDER_UPDATE_RATE_HOURS:
            try:
                etherscan.update_saved_holders_chart(config.TOKEN_ETH_ADDRESS,
                                                     token.tokens_minted)
                storage.last_holders_update_timestamp.set(time.time())
            except:
                logging.exception('Failed to update token holders chart')
            else:
                logging.info('Updated token holders chart')

        try:
            price_eth = apis.price_eth(config.CURRENCY)
            price_usd = apis.price_eth(config.CURRENCY) * apis.eth_price_usd()
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
            price_eth = apis.price_eth(config.CURRENCY)
            price_usd = apis.price_eth(config.CURRENCY) * apis.eth_price_usd()
            # usd price is hidden if it is 0 (an error)
            usd_str = "" if price_usd == 0 else "${:.2f}  |  ".format(price_usd)

            # show hashrate if available, otherwise show 'time since last update'
            if token.estimated_hashrate is not None and token.estimated_hashrate > 0:
                end_of_status = to_readable_thousands(token.estimated_hashrate, unit_type='short_hashrate')
            else:
                end_of_status = seconds_to_n_time_ago(time.time()-apis.last_updated_time())

            # wait until at least one successful update to show status
            if apis.last_updated_time() != 0:
                fmt_str = "{}{} Ξ ({})"
                await update_status(client, fmt_str.format(usd_str,
                                                           prettify_decimals(price_eth),
                                                           end_of_status))
        except (websockets.exceptions.ConnectionClosed,
                RuntimeError) as e:
            logging.warning('Falied to change status: {}'.format(e.msg))
        except:
            logging.exception('Failed to change status')

        await asyncio.sleep(config.UPDATE_RATE)

    # this throws an exception which causes the program to restart
    # in normal operation we should never reach this
    raise RuntimeError('background_update loop stopped - something is wrong')

# These commands will work in any channel (TODO: move to a fn)
async def handle_global_command(command_str, author_id, raw_message):
    for cmd_def in _GLOBAL_COMMANDS:
        if string_contains_any(command_str, cmd_def.keywords):
            return cmd_def.response
    return None

async def handle_trading_command(command_str, author_id, raw_message):
    msg = None

    if string_contains_any(command_str, ['exchanges', 'wheretobuy']):
        msg = cmd_priceall()

    if string_contains_any(command_str, ['price', 'rice', 'pric', 'pricce', 'proce', 'rpice']):
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
                'al',
                'prices'], exhaustive_search=True, require_cmd_char=False):
            msg  = cmd_priceall()
        else:
            msg = cmd_price()

    if string_contains_any(command_str, ['vol', 'völ', 'vil']):
        msg = cmd_volume()

    if string_contains_any(command_str, ['zj']):
        msg = "If you have to ask big man, you can't afford it."

    if string_contains_any(command_str, ['bettervolume']):
        msg = ':star2:'*10 + '\n' + cmd_volume() + '\n' + ':star2:'*10

    if string_contains_any(command_str, ['ratio']):
        msg = cmd_ratio()

    if string_contains_any(command_str, ['rank']):
        msg = cmd_rank()

    if string_contains_any(command_str, ['bitcoin price', 'btc price', 'bitcoin', 'btc']):
        msg = cmd_bitcoinprice()

    if string_contains_any(command_str, ['ethereum price', 'eth price', 'ethereum', 'eth']):
        msg = cmd_ethereumprice()

    if string_contains_any(command_str, ['convert', 'concert', 'conver', 'covert']):
        msg = cmd_convert(command_str)

    if string_contains_any(command_str, ['hug']):
        msg = "*SQUEEEEEEEEEEEEE* There, there. It's alright now. Botty is gonna make it all better."

    if string_contains_any(command_str, ['hi', 'hey bot']):
        msg = "Sup :sunglasses:"

    if string_contains_any(command_str, ['uptime']):
        msg = "Uptime: {}".format(seconds_to_time(time.time() - start_time))

    if string_contains_any(command_str, ['marketcap', 'mcap']):
        msg = cmd_marketcap()

    if string_contains_any(command_str, ['difficulty', 'diff', 'retarget', 'readjustment']):
        msg = cmd_difficulty()

    if string_contains_any(command_str, ['block time', 'block rate', 'reward time', 'reward rate']):
        msg = cmd_blocktime()

    if string_contains_any(command_str, ['hashrate']):
        msg = cmd_hashrate()

    if string_contains_any(command_str, ['minted', 'circulating', 'supply', 'tokens minted']):
        msg = cmd_tokens_minted()

    if string_contains_any(command_str, ['era', 'halving', 'halvening']):
        msg = cmd_era()

    if string_contains_any(command_str, ['burn', 'burned', 'address 0']):
        msg = cmd_tokens_burned()

    if string_contains_any(command_str, ['holders', 'distribution', 'dist']):
        msg = await cmd_holders(command_str, author_id, raw_message)

    if string_contains_any(command_str, ['income', 'profit', 'earnings', 'mining calculator', 'calculator']):
        msg = cmd_income(command_str, author_id, raw_message)

    if string_contains_any(command_str, ['mine']):
        msg = cmd_mine(command_str, author_id, raw_message)

    if string_contains_any(command_str, ['set address']):
        msg = await cmd_set_user_address(command_str, author_id, raw_message)

    if string_contains_any(command_str, ['best share', 'top share', 'highest share', 'high score', 'top score']):
        msg = cmd_bestshare()

    if string_contains_any(command_str, ['ath', 'all time high']):
        msg = cmd_all_time_high()

    if string_contains_any(command_str, ['setath']):
        msg = cmd_set_all_time_high(command_str, author_id, raw_message)

    if string_contains_any(command_str, ['bot command']):
        msg = cmd_bot_command(command_str, author_id, raw_message)

    if string_contains_any(command_str, ['ping']):
        msg = cmd_ping(command_str, author_id, raw_message)

    if string_contains_any(command_str, ['pools']):
        msg = cmd_pools()

    if string_contains_any(command_str, ['help all']):
        # TODO: generate this automatically
        msg = ("trading commands: `price`  `price <exchange>`  `volume`  `ratio`  `convert`  `rank`  `btc`  `eth`  `marketcap`\n"
               #+ "bot commands: `uptime` "
               + "token info: `supply`  `difficulty`  `hashrate`  `blocktime`  `holders`  `halvening`  `burned`  `mine`\n"
               + "price commands: {}\n".format("  ".join("`{}`".format(c[1][0]) for c in random.Random(datetime.date.today().strftime("%j")).sample(config.EXPENSIVE_STUFF, 10)))
               + "quick link commands: `whitepaper`  `website`  `ann`  `contract`  `stats`  `miners`  `merch`\n"
               + "tools: `convert`  `income`  `mine`\n")

    for price, names in config.EXPENSIVE_STUFF:
        if string_contains_any(command_str, names, exhaustive_search=True):
            correct_name = names[0]
            msg = cmd_compare_price_vs(correct_name, price)
            break

    return msg

async def send_discord_msg(channel, message):
    # don't send messages that are only 'OK-noresponse' (this indicates
    # command ran, but no output is expected
    if message == "OK-noresponse":
        return

    try:
        await client.send_message(channel, message)
    except discord.errors.Forbidden:
        logging.debug('no permission in channel: {} [{}]'.format(channel.name, channel.id))

def configure_discord_client():
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

        # trading commands are ignored in blacklisted channels
        if message.channel.id not in config.BLACKLISTED_CHANNEL_IDS:
            response = await handle_trading_command(message_contents, message.author.id, message)
            if response:
                await send_discord_msg(message.channel, response)
                return

        response = await handle_global_command(message_contents, message.author.id, message)
        if response:
            await send_discord_msg(message.channel, response)
            return

        # If command starts with config.COMMAND_CHARACTER and we have not returned yet, it was unrecognized.
        if message_contents.startswith(config.COMMAND_CHARACTER):
            logging.info('UNKNOWN cmd {}'.format(repr(message_contents)))

    @client.event
    async def on_ready():
        show_startup_info(client)

def show_startup_info(client):
    logging.info('Starting {} version {}'.format(_PROGRAM_NAME, _VERSION))
    logging.debug('discord.py version {}'.format(discord.__version__))
    logging.info('Logged in to {} servers as {} id:{}'.format(len(client.servers),
                                                              client.user.name,
                                                              client.user.id))
    if settings['show_channels']:
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
    logging.getLogger('discord').setLevel(logging.WARNING)

    logging.info('Logging debug info to {}'.format(path))

def manual_api_update():
    logging.info('updating apis...')
    try:
        apis.update()
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
                handle_global_command(cmd, mock_message.author.id, mock_message), 
                handle_trading_command(cmd, mock_message.author.id, mock_message)
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
apis = None
token = None
start_time = None
settings = {}

def main():
    import argparse
    import os

    global client, storage, apis, token, start_time, settings
    
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
                        help=("Set the location of the debug log file"))
    parser.add_argument('--version', action='version', 
                        version='%(prog)s v{}'.format(_VERSION))
    args = parser.parse_args()

    start_time = time.time()

    if args.self_test:
        import all_self_tests
        all_self_tests.run_all()
        return

    settings['show_channels'] = args.show_channels

    if not os.path.exists(os.path.split(args.log_location)[0]):
        os.makedirs(os.path.split(args.log_location)[0])
    setup_logging(args.log_location)

    apis = MultiApiManager(
    [
        CoinMarketCapAPI(config.CURRENCY),
        CoinMarketCapAPI('ETH'),
        CoinMarketCapAPI('BTC'),
        EnclavesAPI(config.CURRENCY),
        ForkDeltaAPI(config.CURRENCY),
        IDEXAPI(config.CURRENCY),
        MercatoxAPI(config.CURRENCY),
        EthexAPI(config.CURRENCY),
    ])
    token = MineableTokenInfo(config.TOKEN_ETH_ADDRESS)
    storage = Storage(config.DATA_FOLDER)

    if args.command_test:
        storage = Storage('./test_data/databases/')
        command_test()
        return

    client = discord.Client()
    configure_discord_client()

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
