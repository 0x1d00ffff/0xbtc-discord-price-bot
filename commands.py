import logging
import collections
import random
import datetime  # !help !ath
import time  # !uptime !price

# import socket  # unused

from web3 import Web3  # !mine command

import ping_wrapper  # !ping command


CmdDef = collections.namedtuple('CmdDef', ['keywords', 'response'])

# commands that work in all channels (ignores the blacklist)
_GLOBAL_COMMANDS = [
    CmdDef(
        ['help', 'commands', 'bot'],
        cmd_help),
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
        cmd_price),
    CmdDef(
        ['exchanges', 'wheretobuy'],
        cmd_price_all),
    CmdDef(
        ['vol', 'völ', 'vil'],
        cmd_volume),
    CmdDef(
        ['bettervolume'],
        lambda: ':star2:'*10 + '\n' + cmd_volume() + '\n' + ':star2:'*10),
    CmdDef(
        ['zj'],
        "If you have to ask big man, you can't afford it."),
    CmdDef(
        ['ratio'],
        cmd_ratio),
    CmdDef(
        ['rank'],
        cmd_rank),
    CmdDef(
        ['bitcoin price', 'btc price', 'bitcoin', 'btc'],
        cmd_bitcoinprice),
    CmdDef(
        ['ethereum price', 'eth price', 'ethereum', 'eth'],
        cmd_ethereumprice),
    CmdDef(
        ['convert', 'concert', 'conver', 'covert'],
        cmd_convert),
    CmdDef(
        ['hi', 'hey bot'],
        "Sup :sunglasses:"),
    CmdDef(
        ['uptime'],
        lambda: "Uptime: {}".format(seconds_to_time(time.time() - start_time))),
    CmdDef(
        ['marketcap', 'mcap'],
        cmd_marketcap),
    CmdDef(
        ['difficulty', 'diff', 'retarget', 'readjustment'],
        cmd_difficulty),
    CmdDef(
        ['block time', 'block rate', 'reward time', 'reward rate'],
        cmd_difficulty),
    CmdDef(
        ['hashrate'],
        cmd_difficulty),
    CmdDef(
        ['difficulty', 'diff', 'retarget', 'readjustment'],
        cmd_difficulty),
    CmdDef(
        ['minted', 'circulating', 'supply', 'tokens minted'],
        cmd_tokens_minted),
    CmdDef(
        ['era', 'halving', 'halvening'],
        cmd_era),
    CmdDef(
        ['burn', 'burned', 'address 0'],
        cmd_tokens_burned),
    CmdDef(
        ['holders', 'distribution', 'dist'],
        cmd_holders),
    CmdDef(
        ['income', 'profit', 'earnings', 'mining calculator', 'calculator'],
        cmd_income),
    CmdDef(
        ['mine'],
        cmd_mine),
    CmdDef(
        ['set address'],
        cmd_set_user_address),
    CmdDef(
        ['best share', 'top share', 'highest share', 'high score', 'top score'],
        cmd_bestshare),
    CmdDef(
        ['ath', 'all time high'],
        cmd_all_time_high),
    CmdDef(
        ['setath'],
        cmd_set_all_time_high),
    CmdDef(
        ['bot command'],
        cmd_bot_command),
    CmdDef(
        ['ping'],
        cmd_ping),
    CmdDef(
        ['pools'],
        cmd_pools),
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

# These commands will work in any channel (TODO: move to a fn)
async def handle_global_command(command_str, author_id, raw_message):
    for cmd_def in _GLOBAL_COMMANDS:
        if string_contains_any(command_str, cmd_def.keywords):
            try:
                return cmd_def.response()
            except TypeError:
                return cmd_def.response
    return None

async def handle_trading_command(command_str, author_id, raw_message):
    msg = None

    for cmd_def in _TRADING_COMMANDS:
        if string_contains_any(command_str, cmd_def.keywords):
            try:
                return cmd_def.response()
            except TypeError:
                return cmd_def.response

    # TODO: move this into _TRADING_COMMANDS somehow
    for price, names in config.EXPENSIVE_STUFF:
        if string_contains_any(command_str, names, exhaustive_search=True):
            correct_name = names[0]
            msg = cmd_compare_price_vs(correct_name, price)
            break

    return msg


def cmd_help():
    return ("trading commands: `price`  `price <exchange>`  `volume`  `ratio`  `rank`  `btc`  `eth`  `marketcap`\n"
            + "price commands: {}\n".format("  ".join("`{}`".format(c[1][0]) for c in random.Random(datetime.date.today().strftime("%j")).sample(config.EXPENSIVE_STUFF, 5)))
            #+ "bot commands: `uptime ping` "
            + "token info: `supply`  `difficulty`  `hashrate`  `blocktime`  `holders`  `halvening`  `burned`\n"
            + "quick link commands: `whitepaper`  `website`  `ann`  `contract`  `stats`  `miners`  `merch`\n"
            + "tools: `convert`  `income`  `mine`")

def cmd_compare_price_vs(item_name="lambo", item_price=200000):
    if exchanges.last_updated_time() == 0:
        return ":shrug:"

    token_price_usd = exchanges.price_eth(config.CURRENCY) * exchanges.eth_price_usd()

    if token_price_usd == 0:
        return ":shrug:"

    return "1 {} = **{}** 0xBTC (${})".format(item_name, 
                                              prettify_decimals(item_price / token_price_usd), 
                                              to_readable_thousands(item_price))

def show_price_from_source(source='aggregate'):
    if (exchanges.last_updated_time(api_name=source) == 0):
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(exchanges.short_url(api_name=source))
    
    token_price = exchanges.price_eth(config.CURRENCY, api_name=source) * exchanges.eth_price_usd()
    eth_price_on_this_exchange = float(exchanges.eth_price_usd(api_name=source))

    # Enclaves usually fails this way
    if token_price == 0:
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(exchanges.short_url(api_name=source))

    percent_change_str = ""
    if exchanges.change_24h(config.CURRENCY, api_name=source) == None:
        percent_change_str = ""
    elif exchanges.change_24h(config.CURRENCY, api_name=source) == 0:
        percent_change_str = "**0**% "
    else:
        percent_change_str = "**{:+.2f}**% {} ".format(100.0 * exchanges.change_24h(config.CURRENCY, api_name=source),
                                                       percent_change_to_emoji(exchanges.change_24h(config.CURRENCY, api_name=source)),)
    fmt_str = "{}{}: {}({:.5f} Ξ) {}{}[<{}>]"
    result = fmt_str.format('' if source == 'aggregate' else '**{}** '.format(source),
                            seconds_to_n_time_ago(time.time()-exchanges.last_updated_time(api_name=source)),
                            '' if token_price == 0 else '**${:.3f}** '.format(token_price), 
                            exchanges.price_eth(config.CURRENCY, api_name=source), 
                            percent_change_str,
                            '' if eth_price_on_this_exchange == 0 else '(ETH: **${:.0f}**) '.format(eth_price_on_this_exchange), 
                            exchanges.short_url(api_name=source))
    return result

def cmd_price(command_str):
    if string_contains_any(command_str, [
            'enclaves',
            'encalves'], exhaustive_search=True, require_cmd_char=False):
        msg = show_price_from_source(source="Enclaves DEX")
    elif string_contains_any(command_str, [
            'fd',
            'fork delta'], exhaustive_search=True, require_cmd_char=False):
        msg = show_price_from_source(source="Fork Delta")
    elif string_contains_any(command_str, [
            'merc', 
            'mercatox', 
            'meractox', 
            'mecratox'], exhaustive_search=True, require_cmd_char=False):
        msg = show_price_from_source(source="Mercatox")
    elif string_contains_any(command_str, [
            'idex'], exhaustive_search=True, require_cmd_char=False):
        msg = show_price_from_source(source="IDEX")
    #elif string_contains_any(command_str, [
    #        'hotbit',
    #        'hot bit'], exhaustive_search=True, require_cmd_char=False):
    #    msg = show_price_from_source(source="Hotbit")
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
        msg  = cmd_price_all()
    else:
        msg = show_price_from_source()

def cmd_price_all():
    msg = ""
    for api in sorted(exchanges.alive_apis, key=lambda a: a.api_name):
        # this skips CMC and apis not directly tracking 0xbtc
        if api.currency_symbol != config.CURRENCY or api.api_name == "Coin Market Cap":
            continue
        single_line = show_price_from_source(source=api.api_name)
        # TODO: remove this when 'alive_apis' excludes apis correctly
        if single_line.startswith('not sure yet'):
            continue
        msg += single_line + '\n'
    if msg == "":
        return ":shrug:"
    return msg

def cmd_bitcoinprice():
    if exchanges.last_updated_time() == 0:
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(exchanges.short_url())

    if exchanges.btc_price_usd() == 0:
        return ":shrug:"

    fmt_str = "{}: **${:.0f}**"
    result = fmt_str.format(seconds_to_n_time_ago(time.time()-exchanges.last_updated_time()),
                            exchanges.btc_price_usd())
    return result

def cmd_ethereumprice():
    if exchanges.last_updated_time() == 0:
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(exchanges.short_url())

    if exchanges.eth_price_usd() == 0:
        return ":shrug:"

    fmt_str = "{}: **${:.0f}**"
    result = fmt_str.format(seconds_to_n_time_ago(time.time()-exchanges.last_updated_time()), 
                            exchanges.eth_price_usd())
    return result

def cmd_marketcap():
    if exchanges.last_updated_time() == 0:
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(exchanges.short_url())

    token_price = exchanges.price_eth(config.CURRENCY) * exchanges.eth_price_usd()
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

    if token.seconds_until_readjustment == float('inf'):
        retarget_str = ''
    else:
        retarget_str = " ({} until next retarget)".format(seconds_to_time(token.seconds_until_readjustment))

    fmt_str = "Current difficulty: **{}** {}"
    result = fmt_str.format(to_readable_thousands(token.difficulty, unit_type='long'),
                            retarget_str)
    return result

def cmd_blocktime():
    if token.seconds_per_reward == None:
        return ":shrug:"

    fmt_str = "Current average block time: **{}** (average taken over the last {})"
    result = fmt_str.format('unknown' if token.seconds_per_reward == float('inf') else seconds_to_time(token.seconds_per_reward),
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

def check_and_set_top_share(resulting_difficulty, author_name, author_id, digest):
    result = ""
    if resulting_difficulty > storage.top_miner_difficulty.get():
        fmt_str = "\nNew best share! Previous was `0x{}...` (Difficulty: {}) by {}"
        result += fmt_str.format(storage.top_miner_digest.get()[:5].hex(),
                                 prettify_decimals(storage.top_miner_difficulty.get()),
                                 storage.top_miner_name.get())

        storage.top_miner_difficulty.set(resulting_difficulty)
        storage.top_miner_name.set(author_name)
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

def parse_mining_results(nonce, digest, save_high_score=False, author_name=None, author_id=None):
    resulting_difficulty = token.MAX_TARGET / Web3.toInt(digest)
    percent_of_the_way_to_full_target = token.mining_target / Web3.toInt(digest)
    fmt_str = "Nonce `0x{}...` -> Digest `0x{}...`\nDiff: {} ({}% of the way to a full solution)"
    result = fmt_str.format(nonce[:5].hex(),
                            digest[:5].hex(),
                            prettify_decimals(resulting_difficulty), 
                            prettify_decimals(percent_of_the_way_to_full_target * 100.0))
    if save_high_score:
        result += check_and_set_top_share(resulting_difficulty, 
                                          author_name,
                                          author_id,
                                          digest)
    return result

def cmd_mine(message, author_id, raw_message):
    if token.mining_target is None:
        return "Sorry, I'm having problems with my APIs..."

    if 'test' in message:
        return cmd_mine_test(message, author_id, raw_message)

    try:
        address = storage.user_addresses.get(author_id)
    except KeyError:
        return "Looks like you don't have a public address set; run `!setaddress 0xAAA...` first"

    try:
        command, nonce = message.split(maxsplit=1)
    except:
        return "Bad nonce; try `mine 0xABBA`, `!mine 27`, or `!mine message`"

    try:
        nonce, digest = token.get_digest_for_nonce_str(nonce, address)
    except RuntimeError as e:
        return str(e)

    return parse_mining_results(nonce,
                                digest,
                                save_high_score=True,
                                author_name=raw_message.author.name,
                                author_id=raw_message.author.id)

def cmd_mine_test(message, author_id, raw_message):
    """ wrapper around get_digest_for_nonce to make testing easier. Example:

        !mine test 
        0x3b0ec88154c8aecbc7876f50d8915ef7cd6112a604cad4f86f549d5b9eed369a 
        0x540d752A388B4fC1c9Deeb1Cd3716A2B7875D8A6 
        0x03000000000000000440a2682657259316000000e87905d96943030a90de3e74 
    """

    try:
        challenge_number, address, nonce = message.split()[-3:]
    except:
        return "Bad command; try `mine test <challenge_number> <address> <nonce>`"

    try:
        nonce, digest = token.get_digest_for_nonce_str(nonce, address, challenge_number)
    except RuntimeError as e:
        return str(e)
    
    return parse_mining_results(nonce, digest)

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
            response += "{}: {:.1f} ms\n".format(url, latency)

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
    if exchanges.last_updated_time() == 0:
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(exchanges.short_url())

    total_eth_volume = 0
    total_btc_volume = 0
    response = ""


    for api in sorted(exchanges.alive_apis, key=lambda a: a.api_name):
        # this skips CMC and apis not directly tracking 0xbtc
        if api.currency_symbol != config.CURRENCY or api.api_name == "Coin Market Cap":
            continue

        volume_eth = exchanges.volume_eth(config.CURRENCY, api_name=api.api_name)
        volume_btc = exchanges.volume_btc(config.CURRENCY, api_name=api.api_name)
        if volume_eth == 0 and volume_btc == 0:
            continue

        total_eth_volume += volume_eth
        total_btc_volume += volume_btc
        if exchanges.eth_price_usd() == 0:
            response += "{}: **{}Ξ** ".format(api.api_name, prettify_decimals(volume_eth))
        else:
            response += "{}: $**{}**({}Ξ) ".format(api.api_name, prettify_decimals(volume_eth * exchanges.eth_price_usd()), prettify_decimals(volume_eth))
        if volume_btc != 0:
            if exchanges.btc_price_usd() == 0:
                response += "+ **{}₿** ".format(prettify_decimals(volume_btc))
            else:
                response += "+ $**{}**({}₿) ".format(prettify_decimals(volume_btc * exchanges.btc_price_usd()), prettify_decimals(volume_btc))

    response += "\n"

    if exchanges.eth_price_usd() == 0 or exchanges.btc_price_usd() == 0:
        response += "Total: {}Ξ + {}₿".format(prettify_decimals(total_eth_volume), prettify_decimals(total_btc_volume))
    else:
        response += "Total: $**{}**({}Ξ+{}₿)".format(prettify_decimals((total_eth_volume * exchanges.eth_price_usd()) + (total_btc_volume * exchanges.btc_price_usd())), prettify_decimals(total_eth_volume), prettify_decimals(total_btc_volume))

    return response

def cmd_ratio():
    if exchanges.last_updated_time() == 0:
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(exchanges.short_url())

    token_price_usd = exchanges.price_eth(config.CURRENCY) * exchanges.eth_price_usd()
    if token_price_usd == 0:
        return ":shrug:"

    return "1 BTC : {:,.0f} 0xBTC".format(exchanges.btc_price_usd() / token_price_usd)

def cmd_rank():
    api_name = "Coin Market Cap"
    api_url = exchanges.short_url(api_name=api_name)

    if exchanges.last_updated_time() == 0:
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(api_url)

    rank = exchanges.rank(currency_symbol=config.CURRENCY,
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

    token_price_usd = exchanges.price_eth(config.CURRENCY) * exchanges.eth_price_usd()

    if src in ['0xbtc', '0xbitcoins', '0xbitcoin']:
        usd_value = token_price_usd * amount
    elif src in ['m0xbtc', 'milli0xbtc', 'milli0xbitcoin', 'milli0xbitcoins']:
        usd_value = token_price_usd * amount / 1000.0
    elif src in ['0xsatoshis', '0xsatoshi', 'satoastis', 'satoasti', 'crumbs', 'crumb']:
        usd_value = token_price_usd * amount / 10**8
    elif src in ['eth', 'ethereum', 'ether']:
        usd_value = exchanges.eth_price_usd() * amount
    elif src == 'wei':
        usd_value = exchanges.eth_price_usd() * amount / 10**18
    elif src in ['btc', 'bitcoins', 'bitcoin']:
        usd_value = exchanges.btc_price_usd() * amount
    elif src in ['mbtc', 'millibtc', 'millibitcoins', 'millibitcoin']:
        usd_value = exchanges.btc_price_usd() * amount / 1000.0
    elif src in ['satoshis', 'satoshi']:
        usd_value = exchanges.btc_price_usd() * amount / 10**8
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
    elif dest in ['eth', 'ethereum', 'ether']:
        result = usd_value / exchanges.eth_price_usd()
    elif dest == 'wei':
        result = 10**18 * usd_value / exchanges.eth_price_usd()
    elif dest in ['btc', 'bitcoins', 'bitcoin']:
        result = usd_value / exchanges.btc_price_usd()
    elif dest in ['mbtc', 'millibtc', 'millibitcoins', 'millibitcoin']:
        result = usd_value * 1000.0 / exchanges.btc_price_usd()
    elif dest in ['satoshis', 'satoshi']:
        result = 10**8 * usd_value / exchanges.btc_price_usd()
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
    if exchanges.last_updated_time() == 0 or exchanges.eth_price_usd() == 0 or exchanges.btc_price_usd() == 0:
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(exchanges.short_url())

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
