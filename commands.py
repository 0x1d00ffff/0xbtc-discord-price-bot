import logging
import collections
import random
import datetime  # !help !ath
import time  # !uptime !price

# import socket  # unused

import configuration as config
import util

from web3 import Web3  # !mine command

import ping_wrapper  # !ping command

import command_handlers


CmdDef = collections.namedtuple('CmdDef', ['keywords', 'response'])

# commands that work in all channels (ignores the blacklist)
_GLOBAL_COMMANDS = [
    CmdDef(
        ['help', 'commands', 'bot'],
        command_handlers.cmd_help),
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
        ["miner", "miners", "software", "cosmic", "lttofu", "az", "azlehria", "nabiki", "gaiden", "soliditysha3miner", "amano", "ss3"],
        ("Azlehria: <https://github.com/azlehria/0xbitcoin-gpuminer/releases>\n"
         "COSMiC: <https://bitbucket.org/LieutenantTofu/cosmic-v3/downloads/>\n" 
         "MVIS-Tokenminer: <https://github.com/mining-visualizer/MVis-tokenminer/releases>\n"
         "SoliditySHA3Miner: <https://github.com/lwYeo/SoliditySHA3Miner/releases>")),
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
        ["soliditysha3miner", "amano", "ss3"],
        "SoliditySHA3Miner: <https://github.com/lwYeo/SoliditySHA3Miner/releases>"),
]
# commands that work in the #trading channel only
_TRADING_COMMANDS = [
    CmdDef(
        ['price', 'rice', 'pric', 'pricce', 'proce', 'rpice'],
        command_handlers.cmd_price),
    CmdDef(
        ['exchanges', 'wheretobuy'],
        command_handlers.cmd_price_all),
    CmdDef(
        ['vol', 'völ', 'vil'],
        command_handlers.cmd_volume),
    CmdDef(
        ['bettervolume'],
        lambda: ':star2:'*10 + '\n' + command_handlers.cmd_volume() + '\n' + ':star2:'*10),
    CmdDef(
        ['zj'],
        "If you have to ask big man, you can't afford it."),
    CmdDef(
        ['ratio'],
        command_handlers.cmd_ratio),
    CmdDef(
        ['rank'],
        command_handlers.cmd_rank),
    CmdDef(
        ['bitcoin price', 'btc price', 'bitcoin', 'btc'],
        command_handlers.cmd_bitcoinprice),
    CmdDef(
        ['ethereum price', 'eth price', 'ethereum', 'eth'],
        command_handlers.cmd_ethereumprice),
    CmdDef(
        ['convert', 'concert', 'conver', 'covert'],
        command_handlers.cmd_convert),
    CmdDef(
        ['hi', 'hey bot'],
        "Sup :sunglasses:"),
    CmdDef(
        ['uptime'],
        lambda: "Uptime: {}".format(seconds_to_time(time.time() - start_time))),
    CmdDef(
        ['marketcap', 'mcap'],
        command_handlers.cmd_marketcap),
    CmdDef(
        ['difficulty', 'diff', 'retarget', 'readjustment'],
        command_handlers.cmd_difficulty),
    CmdDef(
        ['block time', 'block rate', 'reward time', 'reward rate'],
        command_handlers.cmd_difficulty),
    CmdDef(
        ['hashrate'],
        command_handlers.cmd_difficulty),
    CmdDef(
        ['difficulty', 'diff', 'retarget', 'readjustment'],
        command_handlers.cmd_difficulty),
    CmdDef(
        ['minted', 'circulating', 'supply', 'tokens minted'],
        command_handlers.cmd_tokens_minted),
    CmdDef(
        ['era', 'halving', 'halvening'],
        command_handlers.cmd_era),
    CmdDef(
        ['burn', 'burned', 'address 0'],
        command_handlers.cmd_tokens_burned),
    CmdDef(
        ['holders', 'distribution', 'dist'],
        command_handlers.cmd_holders),
    CmdDef(
        ['income', 'profit', 'earnings', 'mining calculator', 'calculator'],
        command_handlers.cmd_income),
    CmdDef(
        ['mine'],
        command_handlers.cmd_mine),
    CmdDef(
        ['set address'],
        command_handlers.cmd_set_user_address),
    CmdDef(
        ['best share', 'top share', 'highest share', 'high score', 'top score'],
        command_handlers.cmd_bestshare),
    CmdDef(
        ['ath', 'all time high'],
        command_handlers.cmd_all_time_high),
    CmdDef(
        ['setath'],
        command_handlers.cmd_set_all_time_high),
    CmdDef(
        ['bot command'],
        command_handlers.cmd_bot_command),
    CmdDef(
        ['ping'],
        command_handlers.cmd_ping),
    CmdDef(
        ['pools'],
        command_handlers.cmd_pools),
]


async def handle_global_command(command_str, discord_message):
    for cmd_def in _GLOBAL_COMMANDS:
        if util.string_contains_any(command_str, cmd_def.keywords):
            try:
                return cmd_def.response(command_str, discord_message)
            except TypeError:
                return cmd_def.response
    return None

async def handle_trading_command(command_str, discord_message):
    msg = None

    for cmd_def in _TRADING_COMMANDS:
        if util.string_contains_any(command_str, cmd_def.keywords):
            try:
                return cmd_def.response(command_str, discord_message)
            except TypeError:
                return cmd_def.response

    # TODO: move this into _TRADING_COMMANDS somehow
    for price, names in config.EXPENSIVE_STUFF:
        if util.string_contains_any(command_str, names, exhaustive_search=True):
            correct_name = names[0]
            msg = cmd_compare_price_vs(correct_name, price)
            break

    return msg
