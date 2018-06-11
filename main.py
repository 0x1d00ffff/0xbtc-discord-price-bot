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
from reconnecting_bot import keep_running
from enclavesdex import EnclavesAPI
from livecoinwatch import LiveCoinWatchAPI
from forkdelta import ForkDeltaAPI
from mercatox import MercatoxAPI
from idex import IDEXAPI
from hotbit import HotbitAPI
from multi_api_manager import MultiApiManager

_VERSION = "0.0.26"
_UPDATE_RATE = 120

# todo: encapsulate these
#bitcoin_price = 0
#price_in_usd, price_in_eth, apis.eth_price_usd() = 0, 0, 0
last_updated = 0
command_count = 0
#enclaves = EnclavesAPI()

client = None

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
     ['usedlambo', 'used_lambo']),
    (500000,
     ['privateisland', 'private island', 'privareisland', 'pirvateisland']),
    (398.8*1000*1000,
     ['whitehouse']),
    (101500, 
     ['tesla', 'telsa']),
    (1700,
     ['usedfordtaurus', 'usedtaurus', 'oldfordtaurus', 'oldtaurus']),
    (17600,
     ['likenewfordtaurus', 'likenewtaurus']),
    (28400,
     ['newfordtaurus', 'fordtaurus']),
    (12,
     ['avocadotoast', 'avocadoontoast']),
    (100,
     ['hundredaire']),
    (1e3,
     ['thousandaire']),
    (1e6,
     ['millionaire']),
    (1e9,
     ['billionaire']),
    (650,
     ['magnumdomperignon', 'domperignon', 'expensivechampagne', 'fancychampagne']),
    (200,
     ['microsoft windows license', 'microsoft windows', 'microsoftwindows', 'microsoftwindowslicense', 'windows']),
]


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

    token_price_usd = apis.price_eth('0xBTC') * apis.eth_price_usd()

    if token_price_usd == 0:
        return ":shrug:"

    return "1 {} = **{}** 0xBTC (${})".format(item_name, 
                                              prettify_decimals(item_price / token_price_usd), 
                                              to_readable_thousands(item_price))


def cmd_price(source='aggregate'):
    if apis.last_updated_time(api_name=source) == 0:
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(apis.short_url(api_name=source))
    
    token_price = apis.price_eth('0xBTC', api_name=source) * apis.eth_price_usd()
    eth_price = float(apis.eth_price_usd(api_name=source))

    percent_change_str = ""

    if apis.change_24h('0xBTC', api_name=source) == None:
        percent_change_str = ""
    else:
        # TODO: enable percentage once enclaves is stable
        percent_change_str = "**{:+.2f}**% {} ".format(100.0 * apis.change_24h('0xBTC', api_name=source),
                                                       percent_change_to_emoji(apis.change_24h('0xBTC', api_name=source)),)
        pass

    fmt_str = "{}{}: {}({:.5f} Ξ) {}{}[<{}>]"
    result = fmt_str.format('' if source == 'aggregate' else '**{}** '.format(source),
                            seconds_to_readable_time(time.time()-apis.last_updated_time(api_name=source)),
                            '' if token_price == 0 else '**${:.3f}** '.format(token_price), 
                            apis.price_eth('0xBTC', api_name=source), 
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

    for source in ['Enclaves DEX', 'Fork Delta', 'Mercatox', 'IDEX', 'Hotbit']:
        volume_eth = apis.volume_eth('0xBTC', api_name=source)
        volume_btc = apis.volume_btc('0xBTC', api_name=source)
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

    token_price_usd = apis.price_eth('0xBTC') * apis.eth_price_usd()

    if token_price_usd == 0:
        return ":shrug:"

    return "1 BTC : {:,.0f} 0xBTC".format(apis.btc_price_usd() / token_price_usd)

def cmd_convert(message):
    if apis.last_updated_time() == 0:
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(apis.short_url())

    try:
        # example: '!convert 1 usd to 0xbtc'
        _, amount, src, _, dest = message.split(' ')
        src = src.lower()
        dest = dest.lower()
        amount = float(amount)
    except:
        return "Bad formatting? try this : `!convert 1 eth to 0xbtc`"

    token_price_usd = apis.price_eth('0xBTC') * apis.eth_price_usd()


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
            price_usd = apis.price_eth('0xBTC') * apis.eth_price_usd()
            usd_str = "" if price_usd == 0 else "${:.2f}  |  ".format(price_usd)

            # wait until at least one successful update to show status
            if apis.last_updated_time() != 0:
                fmt_str = "{}{:.5f} Ξ ({})"
                await update_status(client, fmt_str.format(usd_str,
                                                           apis.price_eth('0xBTC'),
                                                           seconds_to_readable_time(time.time()-apis.last_updated_time())))
        except:
            logging.exception('failed to change status')

        await asyncio.sleep(_UPDATE_RATE)

    # this throws an exception which causes the program to restart
    # in normal operation, we should never reach this
    raise RuntimeError('update_price_task loop stopped - something is wrong')

def handle_command(command_str):
    global command_count
    msg = None
    if command_str.startswith('!price') or command_str.startswith('!rice'):
        #logging.info('got !price ({})'.format(command_str))
        if any(s in command_str for s in [
                'enclaves',
                'encalves']):
            msg = cmd_price(source="Enclaves DEX")
        elif any(s in command_str for s in [
                'fd', 
                'forkdelta',
                'fork delta']):
            msg = cmd_price(source="Fork Delta")
        elif any(s in command_str for s in [
                'merc', 
                'mercatox', 
                'meractox', 
                'mecratox']):
            msg = cmd_price(source="Mercatox")
        elif any(s in command_str for s in [
                'idex']):
            msg = cmd_price(source="IDEX")
        elif any(s in command_str for s in [
                'hotbit',
                'hot bit']):
            msg = cmd_price(source="Hotbit")
        elif any(s in command_str for s in [
                'btc',
                'bitcoin']):
            msg = cmd_bitcoinprice()
        elif any(s in command_str for s in [
                'eth',
                'ethereum']):
            msg = cmd_ethereumprice()
        elif any(s in command_str for s in [
                'all']):
            msg = '\n'.join([cmd_price(source="Enclaves DEX"),
                             cmd_price(source="Fork Delta"),
                             cmd_price(source="Mercatox"),
                             cmd_price(source="IDEX"),
                             cmd_price(source="Hotbit"),])
        else:
            msg = cmd_price()

    if command_str.startswith('!vol'):
        #logging.info('got !volume')
        msg = cmd_volume()

    if command_str.startswith('!ratio'):
        #logging.info('got !ratio')
        msg = cmd_ratio()

    if command_str.startswith('!bitcoinprice') or command_str.startswith('!btcprice'):
        #logging.info('got !bitcoinprice ({})'.format(command_str))
        msg = cmd_bitcoinprice()


    if command_str.startswith('!ethereumprice') or command_str.startswith('!ethprice'):
        #logging.info('got !ethereumprice ({})'.format(command_str))
        msg = cmd_ethereumprice()

    if command_str.startswith('!convert'):
        #logging.info('got !convert ({})'.format(command_str))
        msg = cmd_convert(command_str)

    for price, names in _EXPENSIVE_STUFF:
        if not any('!' + name in command_str for name in names):
            continue

        correct_name = names[0]
        #logging.info('got !{} ({})'.format(correct_name, command_str))
        msg = cmd_compare_price_vs(correct_name, price)

    if command_str.startswith('!help'):
        msg =  "available commands: `price volume ratio convert bitcoinprice lambo privateisland whitehouse millionaire billionaire`\n"
        msg += "quick link commands: `whitepaper website ann contract stats mvis cosmic az`"

    if command_str.startswith('!zj'):
        msg = "If you have to ask big man, you can't afford it."

        

    #if command_str.startswith('!hello'):
    #    msg = 'Hello {0.author.mention}'.format(message)
    #    await client.send_message(message.channel, msg)

    # log anything starting with ! with debug messages
    if command_str.startswith('!'):
        if msg != None:
            command_count += 1
            logging.info('cmd: {} total, matched {}'.format(command_count, repr(command_str)))
        else:
            logging.info('cmd: {} total, UNKNOWN {}'.format(command_count, repr(command_str)))

    return msg


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

        command_str = message.content.lower().strip()

        # allow unicode ! (replace with ascii version)
        if command_str.startswith('！'):
            command_str = '!' + command_str[1:]

        # allow '! command' since some platforms autocorrect to add a space
        if command_str.startswith('! '):
            command_str = '!' + command_str[2:]



        # These commands will work in any channel (TODO: move to a fn)
        if command_str.startswith('!whitepaper'):
            response = "0xBitcoin Whitepaper: https://github.com/0xbitcoin/white-paper"

        if command_str.startswith('!website'):
            response = "0xBitcoin Website: https://0xbitcoin.org/"

        if command_str.startswith('!contract'):
            response = "0xBitcoin Contract: 0xb6ed7644c69416d67b522e20bc294a9a9b405b31 [<https://bit.ly/2y1WlMB>]"

        if command_str == '!ann':
            response = "\"[ANN] 0xBitcoin [0xBTC]\": https://bitcointalk.org/index.php?topic=3039182.0"

        if command_str.startswith('!mvis'):
            response = "MVIS-Tokenminer: <https://github.com/mining-visualizer/MVis-tokenminer/releases>"

        if command_str.startswith('!cosmic'):
            response = "COSMiC: <https://bitbucket.org/LieutenantTofu/cosmic-v3/downloads/>"

        if command_str.startswith('!az'):
            response = "Azlehria: <https://github.com/azlehria/0xbitcoin-gpuminer/releases>"
        


        # if not in a blacklisted channel, allow complex commands
        if message.channel.id not in _BLACKLISTED_CHANNEL_IDS:
            response = handle_command(command_str)


        if response == None:
            return

        try:
            await client.send_message(message.channel, response)
        except discord.errors.Forbidden:
            logging.debug('no permission in this channel ({} in {})'.format(message.channel.name, message.server.name))



    @client.event
    async def on_ready():
        logging.info('Logged in as {} ({})'.format(client.user.name,
                                                   client.user.id))

    client.loop.create_task(update_price_task())

def setup_logging():
    path = '.'
    filename = 'debug.log'


    # set up logging to file

    filehandler = logging.FileHandler("{0}/{1}.log".format(path, filename),
                                      mode='a',
                                      encoding='utf-8')
    filehandler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s, %(name)-12s, %(levelname)-8s, %(message)s',
                                  datefmt='%m-%d-%y %H:%M:%S')
    filehandler.setFormatter(formatter)
    #logging.getLogger('').addHandler(filehandler)

    # define a Handler which writes INFO messages or higher to the sys.stderr
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    # set a format which is simpler for console use
    formatter = logging.Formatter('%(asctime)s [%(levelname)-5.5s] %(message)s',
                                  datefmt='%H:%M:%S')
    # tell the handler to use this format
    console.setFormatter(formatter)
    # add the handler to the root logger
    #logging.getLogger('').addHandler(console)


    logging.basicConfig(handlers=[filehandler, console],
        level=logging.DEBUG)

    # make websocket be quiet (no traces to log)
    websocket.enableTrace(False)
    logging.getLogger('websockets').setLevel(logging.WARNING)
    # make discord be quiet
    logging.getLogger('discord').setLevel(logging.WARNING)

if __name__ == "__main__":
    setup_logging()

    logging.info('0xbtc-price-bot start v{}'.format(_VERSION))
    loop = asyncio.get_event_loop()
    client = discord.Client()
    configure_client()
    apis = MultiApiManager(
    [
        EnclavesAPI('0xBTC'), 
        LiveCoinWatchAPI('ETH'),
        ForkDeltaAPI('0xBTC'),
        MercatoxAPI('0xBTC'),
        IDEXAPI('0xBTC'),
        HotbitAPI('0xBTC'),
    ])
    while True:
        try:
            asyncio.get_event_loop().run_until_complete(keep_running(client, TOKEN))
            # loop.run_until_complete(client.start(TOKEN))
            # client.run(TOKEN)
        except SystemExit:
            raise
        except KeyboardInterrupt:
            raise
        except:
            logging.exception('bot ded:')
            time.sleep(10)  # wait a little time to prevent cpu spins
