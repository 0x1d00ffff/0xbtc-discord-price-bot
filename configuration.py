# 0xbtc-discord-price-bot configuration file
#

TOKEN_SYMBOL = '0xBTC'
TOKEN_NAME = '0xBitcoin'
TOKEN_ETH_ADDRESS = "0xB6eD7644C69416d67B522e20bC294A9a9B405B31"

UPDATE_RATE = 240  # how often to update all APIs (in seconds)
#UPDATE_RATE = 20  # testing rate

TOKEN_HOLDER_UPDATE_RATE_HOURS = 6  # how often to update the token holder chart (in hours)
COMMAND_CHARACTER = '!'  # what character should prepend all commands

DATA_FOLDER = './databases/'  # folder to store persistent data (all-time high prices, etc)

# Channel ID to send announcements (for now, all-time-high prices)
ANNOUNCEMENT_CHANNEL_ID = 412483801265078273  # 0xbitcoin - trading
#ANNOUNCEMENT_CHANNEL_ID = 828027316848164884  # testing channel


# Channels listed here will be ignored by the bot for all but 'global' commands
BLACKLISTED_CHANNEL_IDS = [
    # 0xbitcoin server
    454156227446964226,  # announcements
    417834372864147456,  # articles
    413927301932253185,  # useful-links
    412477591778492429,  # 0xbitcoin
    #412483801265078273,  # trading (allowed)
    429103257026297866,  # marketing
    419929514316136473,  # miner-dev
    414664710210846722,  # development
    412483768541249536,  # support
    438693168393748500,  # mining
    435893447958986752,  # pools
    439217061475123200,  # memes
    421306695940046852,  # off-topic
    418282243186753537,  # alts-trading
]

# List of users who should be allowed to run privileged commands (like !setath)
PRIVILEGED_USER_IDS = [
    '0',                   # testing user ID
    400860916876574731,  # 0x1d00ffff
]

# List of object prices. This is used by two classes of bot commands:
#  - Trading commands ie `!lambo` -> "1 lambo = 1,194,557 0xBTC ($400.0k)"
#  - Source data for convert ie `!convert 800 0xbtc to tesla`
EXPENSIVE_STUFF = [
    (400000,
     ['Lamborghini Aventador', 'lambo']),
    (200000,
     ['used lambo']),
    (500000,
     ['private island', 'privare island', 'pirvate island', 'island']),
    (398.8*1000*1000,
     ['White House', 'whitehouse']),
    (1.225*1000*1000*1000,
     ['Buckingham Palace']),
    (3.9*1000*1000*1000,
     ['Air Force One']),
    (1700,
     ['Used Ford Taurus', 'used taurus', 'old ford taurus', 'old taurus', 'used ford torus', 'used tarus', 'uft']),
    (17600,
     ['Like-new Ford Taurus', 'like new ford taurus', 'like new taurus']),
    (28400,
     ['New Ford Taurus', 'ford taurus', 'new taurus', 'taurus']),
    (12,
     ['Avocado Toast',
      'avocado on toast', 
      'avacado toast', 
      'avacado on toast', 
      'avocato toast', 
      'avocato on toast',
      'avovado toast',
      'avacodo toast',
      'avo toast']),
    (24,
     ['Avocado Sandwich (2 Avocado Toasts)', 'avocado sandwich']),
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
     ['Magnum Domperignon', 'domperignon', 'champagne', 'donperignon']),
    (200,
     ['Microsoft Windows license', 'microsoft', 'windows']),
    (74990, 
     ['Tesla Model S', 'tesla', 'telsa', 'testla', 'model s']),
    (79990, 
     ['Tesla Model X', 'model x']),
    (37990, 
     ['Tesla Model 3', 'model 3']),
    (49990, 
     ['Tesla Model Y', 'model y']),
    (250000, 
     ['Tesla Roadster', 'roadster']),
    (39900, 
     ['Tesla Cybertruck', 'cybertruck']),
    # falcon 9 (reused booster) lowered to 50M around may 2018
    # https://spacenews.com/spacex-targeting-24-hour-turnaround-in-2019-full-reusability-still-in-the-works/
    (50000000,  # 50 million
     ['SpaceX Falcon 9', 'falcon9']),
    (150e9,  # 150 billion 
     ['International Space Station', 'iss']),
    (115500,
     ['BMW 545e', 'bmw545e']),
]


import command_handlers
from util import CmdDef

# commands that work in all channels (ignores the blacklist)
GLOBAL_COMMANDS = [
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
    CmdDef(
        ["miner", "miners", "software", "cosmic", "lttofu", "az", "azlehria", "nabiki", "gaiden", "soliditysha3miner", "amano", "ss3"],
        ("Azlehria: <https://github.com/azlehria/0xbitcoin-gpuminer/releases>\n"
         "COSMiC: <https://bitbucket.org/LieutenantTofu/cosmic-v3/downloads/>\n" 
         "MVIS-Tokenminer: <https://github.com/mining-visualizer/MVis-tokenminer/releases>\n"
         "SoliditySHA3Miner: <https://github.com/lwYeo/SoliditySHA3Miner/releases>")),
    CmdDef(
        ["pools"],
        command_handlers.cmd_pools),
]

# commands that do not work in blacklisted channels
TRADING_COMMANDS = [
    CmdDef(
        ['0xbtc', '0xbitcoin', 'price', 'rice', 'pric', 'pricce', 'proce', 'rpice'],
        command_handlers.cmd_price),
    CmdDef(
        ['exchanges', 'wheretobuy'],
        command_handlers.cmd_price_all),
    CmdDef(
        ['liq', 'liquidity'],
        command_handlers.cmd_liquidity),
    CmdDef(
        ['vol', 'völ', 'vil', 'bettervolume'],
        command_handlers.cmd_volume),
    CmdDef(
        ['graph', 'chart'],
        command_handlers.cmd_graph),
    CmdDef(
        ['zj'],
        "If you have to ask big man, you can't afford it."),
    CmdDef(
        ['ratio'],
        command_handlers.cmd_ratio),
    CmdDef(
        ['rank', 'cmc rank'],
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
        ['hug'],
        "*SQUEEEEEEEEEEEEE* There, there. It's alright now. Botty is gonna make it all better."),
    CmdDef(
        ['marketcap', 'mcap'],
        command_handlers.cmd_marketcap),
    CmdDef(
        ['challenge'],
        command_handlers.cmd_challenge),
    CmdDef(
        ['difficulty', 'diff', 'retarget', 'readjustment'],
        command_handlers.cmd_difficulty),
    CmdDef(
        ['block time', 'block rate', 'reward time', 'reward rate'],
        command_handlers.cmd_blocktime),
    CmdDef(
        ['hashrate'],
        command_handlers.cmd_hashrate),
    CmdDef(
        ['balance'],
        command_handlers.cmd_balance_of),
    CmdDef(
        ['minted', 'circulating', 'supply', 'tokens minted'],
        command_handlers.cmd_tokens_minted),
    CmdDef(
        ['era', 'halving', 'halvening'],
        command_handlers.cmd_era),
    CmdDef(
        ['burn', 'burned', 'address 0', 'thevoid'],
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
        ['best share', 'top share', 'highest share', 'high score', 'top score', 'record'],
        command_handlers.cmd_bestshare),
    CmdDef(
        ['ath', 'all time high'],
        command_handlers.cmd_all_time_high),
    CmdDef(
        ['setathfilename', 'setathimage'],
        command_handlers.cmd_set_all_time_high_image_filename),
    CmdDef(
        ['setath'],
        command_handlers.cmd_set_all_time_high),
    CmdDef(
        ['setbestshare'],
        command_handlers.cmd_set_bestshare),
    CmdDef(
        ['mod command'],
        command_handlers.cmd_mod_command),
    CmdDef(
        ['uptime'],
        command_handlers.cmd_uptime),
    CmdDef(
        ['wash', 'washing machine'],
        command_handlers.cmd_washing_machine),
    CmdDef(
        ['ping', 'status'],
        command_handlers.cmd_status),
    CmdDef(
        ['hi', 'hey bot'],
        "Sup :sunglasses:"),
    CmdDef(
        ['party'],
        ":partying_face:"),
]

