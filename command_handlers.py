
import logging
import time
import random
import datetime  # !help !ath
import re
import os
import asyncio

import configuration as config
import util

import ping_wrapper  # !ping command
from web3 import Web3  # !mine command
import etherscan  # !holders command

from formatting_helpers import (prettify_decimals, 
                                percent_change_to_emoji,
                                seconds_to_n_time_ago,
                                seconds_to_time,
                                to_readable_thousands,
                                string_to_float)


async def cmd_help(command_str, discord_message, apis):
    return ("trading commands: `price`  `price <exchange>`  `volume`  `ratio`  `rank`  `btc`  `eth`  `marketcap`\n"
            + "price commands: {}\n".format("  ".join("`{}`".format(c[1][0]) for c in random.Random(datetime.date.today().strftime("%j")).sample(config.EXPENSIVE_STUFF, 5)))
            #+ "bot commands: `uptime ping` "
            + "token info: `supply`  `difficulty`  `hashrate`  `blocktime`  `holders`  `halvening`  `burned`\n"
            + "quick link commands: `whitepaper`  `website`  `ann`  `contract`  `stats`  `miners`  `merch`\n"
            + "tools: `convert`  `income`  `mine`")

async def cmd_compare_price_vs(apis, item_name="lambo", item_price=200000):
    if apis.exchanges.last_updated_time() == 0:
        return ":shrug:"

    token_price_usd = apis.exchanges.price_eth(config.TOKEN_SYMBOL) * apis.exchanges.eth_price_usd()

    if token_price_usd == 0:
        return ":shrug:"

    return "1 {} = **{}** {} (${})".format(item_name, 
                                           prettify_decimals(item_price / token_price_usd),
                                           config.TOKEN_SYMBOL,
                                           to_readable_thousands(item_price))

def show_price_from_source(apis, source='aggregate'):
    if (apis.exchanges.last_updated_time(exchange_name=source) == 0):
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(apis.exchanges.short_url(exchange_name=source))
    
    token_price = apis.exchanges.price_eth(config.TOKEN_SYMBOL, exchange_name=source) * apis.exchanges.eth_price_usd()
    eth_price_on_this_exchange = float(apis.exchanges.eth_price_usd(exchange_name=source))

    # Enclaves usually fails this way
    if token_price == 0:
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(apis.exchanges.short_url(exchange_name=source))

    percent_change_str = ""
    if apis.exchanges.change_24h(config.TOKEN_SYMBOL, exchange_name=source) == None:
        percent_change_str = ""
    elif apis.exchanges.change_24h(config.TOKEN_SYMBOL, exchange_name=source) == 0:
        percent_change_str = "**0**% "
    else:
        percent_change_str = "**{:+.2f}**% {} ".format(100.0 * apis.exchanges.change_24h(config.TOKEN_SYMBOL, exchange_name=source),
                                                       percent_change_to_emoji(apis.exchanges.change_24h(config.TOKEN_SYMBOL, exchange_name=source)),)
    fmt_str = "{}{}: {}({:.5f} Ξ) {}{}[<{}>]"
    result = fmt_str.format('' if source == 'aggregate' else '**{}** '.format(source),
                            seconds_to_n_time_ago(time.time()-apis.exchanges.last_updated_time(exchange_name=source)),
                            '' if token_price == 0 else '**${:.3f}** '.format(token_price), 
                            apis.exchanges.price_eth(config.TOKEN_SYMBOL, exchange_name=source), 
                            percent_change_str,
                            '' if eth_price_on_this_exchange == 0 else '(ETH: **${:.0f}**) '.format(eth_price_on_this_exchange), 
                            apis.exchanges.short_url(exchange_name=source))
    return result

async def cmd_price(command_str, discord_message, apis):
    msg = ""
    # search through all exchanges, if the command contains a string in one of
    # exchanges command_names list, show only that exchange
    for exchange in apis.exchanges.all_exchanges:
        if util.string_contains_any(command_str,
                                    exchange.command_names,
                                    exhaustive_search=True,
                                    require_cmd_char=False):
            # skip CMC since it only tracks ETH and BTC price
            # skip LCW since its more of an aggregator
            if (exchange.exchange_name == "Coin Market Cap"
                or exchange.exchange_name == "Live Coin Watch"):
                continue
            return show_price_from_source(apis, source=exchange.exchange_name)
    if util.string_contains_any(command_str, [
            'all',
            'al',
            'prices'], exhaustive_search=True, require_cmd_char=False):
        return await cmd_price_all(command_str, discord_message, apis)
    else:
        return show_price_from_source(apis)

def exchange_has_low_volume(apis, exchange):
    volume_usd = 0
    try:
        volume_usd += apis.exchanges.btc_price_usd() * exchange.volume_btc
    except TypeError:
        pass
    try:
        volume_usd += apis.exchanges.eth_price_usd() * exchange.volume_eth
    except TypeError:
        pass
    return volume_usd < 100

async def cmd_price_all(command_str, discord_message, apis):
    msg = ""
    for exchange in sorted(apis.exchanges.alive_exchanges, key=lambda a: a.exchange_name):
        # skip CMC, LCW and apis not directly tracking the main currency
        if (exchange.currency_symbol != config.TOKEN_SYMBOL 
            or exchange.exchange_name == "Coin Market Cap" 
            or exchange.exchange_name == "Live Coin Watch"):
            continue
        # TODO: skip exchanges with <$100 volume in last 24h?
        # if exchange_has_low_volume(apis, exchange):
        #     continue
        single_line = show_price_from_source(apis, source=exchange.exchange_name)
        # TODO: remove this when 'alive_exchanges' excludes apis correctly
        if single_line.startswith('not sure yet'):
            logging.warning("bugcheck: removed line 'not sure yet' from priceall ({})".format(exchange.exchange_name))
            continue
        msg += single_line + '\n'
    if msg == "":
        return ":shrug:"
    return msg

async def cmd_bitcoinprice(command_str, discord_message, apis):
    if apis.exchanges.last_updated_time() == 0:
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(apis.exchanges.short_url())

    if apis.exchanges.btc_price_usd() == 0:
        return ":shrug:"

    fmt_str = "Bitcoin price {}: **${:.0f}**"
    result = fmt_str.format(seconds_to_n_time_ago(time.time()-apis.exchanges.last_updated_time()),
                            apis.exchanges.btc_price_usd())
    return result

async def cmd_ethereumprice(command_str, discord_message, apis):
    if apis.exchanges.last_updated_time() == 0:
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(apis.exchanges.short_url())

    if apis.exchanges.eth_price_usd() == 0:
        return ":shrug:"

    fmt_str = "Ethereum price {}: **${:.0f}**"
    result = fmt_str.format(seconds_to_n_time_ago(time.time()-apis.exchanges.last_updated_time()), 
                            apis.exchanges.eth_price_usd())
    return result

async def cmd_marketcap(command_str, discord_message, apis):
    if apis.exchanges.last_updated_time() == 0:
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(apis.exchanges.short_url())

    token_price = apis.exchanges.price_eth(config.TOKEN_SYMBOL) * apis.exchanges.eth_price_usd()
    marketcap = apis.token.tokens_minted * token_price

    if marketcap == 0:
        return ":shrug:"

    fmt_str = "Marketcap: **${}** (Price: ${} Circulating Supply: {})"
    result = fmt_str.format(prettify_decimals(marketcap),
                            prettify_decimals(token_price),
                            prettify_decimals(apis.token.tokens_minted))
    return result

async def cmd_difficulty(command_str, discord_message, apis):
    if apis.token.difficulty == None:
        return ":shrug:"

    if apis.token.seconds_until_readjustment == float('inf'):
        retarget_str = ''
    else:
        retarget_str = " ({} until next retarget)".format(seconds_to_time(apis.token.seconds_until_readjustment))

    fmt_str = "Current difficulty: **{}** {}"
    result = fmt_str.format(to_readable_thousands(apis.token.difficulty, unit_type='long'),
                            retarget_str)
    return result

async def cmd_blocktime(command_str, discord_message, apis):
    if apis.token.seconds_per_reward == None:
        return ":shrug:"

    fmt_str = "Current average block time: **{}** (average taken over the last {})"
    result = fmt_str.format('unknown' if apis.token.seconds_per_reward == float('inf') else seconds_to_time(apis.token.seconds_per_reward),
                            seconds_to_time(apis.token.seconds_since_readjustment, granularity=1))
    return result

async def cmd_hashrate(command_str, discord_message, apis):
    if apis.token.estimated_hashrate == None:
        return ":shrug:"

    fmt_str = "Estimated hashrate: **{}** (average over the last {})"
    result = fmt_str.format(to_readable_thousands(apis.token.estimated_hashrate, unit_type="hashrate", decimals=2),
                            seconds_to_time(apis.token.seconds_since_readjustment, granularity=2))
    return result

async def cmd_tokens_minted(command_str, discord_message, apis):
    if apis.token.tokens_minted == None:
        return ":shrug:"

    fmt_str = "Tokens in circulation: **{}** / {} {}"
    result = fmt_str.format(prettify_decimals(apis.token.tokens_minted), 
                            prettify_decimals(apis.token.total_supply),
                            apis.token.SYMBOL)
    return result

async def cmd_era(command_str, discord_message, apis):
    try:
        apis.token.era
    except AttributeError:
        return ":shrug:"

    if apis.token.era == None:
        return ":shrug:"

    if apis.token.era == 39:
        return "In era 39 / 39"

    fmt_str = "Current era: **{}** / 39.  In {} the reward will drop to **{}** {}"
    result = fmt_str.format(apis.token.era,
                            seconds_to_time(apis.token.seconds_remaining_in_era),
                            apis.token.reward / 2,
                            apis.token.SYMBOL)
    return result

async def cmd_tokens_burned(command_str, discord_message, apis):
    if apis.token.addr_0_balance == None:
        return ":shrug:"

    fmt_str = "**{}** {} burned [<https://bit.ly/2AulG0C>]"
    result = fmt_str.format(apis.token.addr_0_balance, apis.token.SYMBOL)
    return result

async def cmd_holders(command_str, discord_message, apis):
    if apis.token.addr_0_balance == None:
        return ":shrug:"

    await apis.client.send_file(discord_message.channel,
                                etherscan.saved_holders_chart_filename)

    # # Async
    # await bot.send_file(channel, "filepath.png", content="...", filename="...")

    # # Rewrite
    # file = discord.File("filepath.png", filename="...")
    # await channel.send("content", file=file)

    return 'OK-noresponse'

async def cmd_income(command_str, discord_message, apis):
    if apis.token.difficulty is None:
        return "not sure yet... waiting on my APIs :sob:"

    try:
        command, hashrate = command_str.split(maxsplit=1)
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

    match = re.match("([<\d.,]+)", hashrate)
    if not match:
        return "Bad hashrate; try `!income 5`, `!income 300mh`, or `!income 2.8gh`"
    hashrate = string_to_float(match.group(1)) * selected_multiplier

    tokens_per_day = 0.8 * 86400 * apis.token.reward * hashrate / ((2**22) * apis.token.difficulty)
    seconds_per_block = 1.2 * ((2**22) * apis.token.difficulty) / hashrate

    if tokens_per_day > 1:
        tokens_over_time_str = "**{}** tokens/day".format(prettify_decimals(tokens_per_day))
    else:
        tokens_over_time_str = "**{}** tokens/week".format(prettify_decimals(tokens_per_day*7))

    fmt_str = "Income for {}: {}; **{}** per block solo"
    return fmt_str.format(to_readable_thousands(hashrate, unit_type='hashrate'),
                          tokens_over_time_str,
                          seconds_to_time(seconds_per_block))

def check_and_set_top_share(apis, resulting_difficulty, author_name, author_id, digest):
    result = ""
    if resulting_difficulty > apis.storage.top_miner_difficulty.get():
        fmt_str = "\nNew best share! Previous was `0x{}...` (Difficulty: {}) by {}"
        result += fmt_str.format(apis.storage.top_miner_digest.get()[:5].hex(),
                                 prettify_decimals(apis.storage.top_miner_difficulty.get()),
                                 apis.storage.top_miner_name.get())

        apis.storage.top_miner_difficulty.set(resulting_difficulty)
        apis.storage.top_miner_name.set(author_name)
        apis.storage.top_miner_id.set(author_id)
        apis.storage.top_miner_digest.set(digest)
    # in case someone solves a block... never going to happen but why not?
    if Web3.toInt(digest) <= apis.token.mining_target:
        result += "\n~~~~~"
        result += "\n:money_mouth: You seem to have solved a block!? Try your luck here [<https://etherscan.io/address/0xb6ed7644c69416d67b522e20bc294a9a9b405b31#writeContract>]"
        result += "\nMake sure you log into metamask using the public address you have set here, and type these values into the mint() function:"
        result += "\n  nonce=`{}`".format(Web3.toHex(nonce))
        result += "\n  challenge_digest=`{}`".format(Web3.toHex(digest))
        result += "\n~~~~~"
    return result

def parse_mining_results(apis, nonce, digest, save_high_score=False, author_name=None, author_id=None):
    resulting_difficulty = apis.token.MAX_TARGET / Web3.toInt(digest)
    percent_of_the_way_to_full_target = apis.token.mining_target / Web3.toInt(digest)
    fmt_str = "Nonce `0x{}...` -> Digest `0x{}...`\nDiff: {} ({}% of the way to a full solution)"
    result = fmt_str.format(nonce[:5].hex(),
                            digest[:5].hex(),
                            prettify_decimals(resulting_difficulty), 
                            prettify_decimals(percent_of_the_way_to_full_target * 100.0))
    if save_high_score:
        result += check_and_set_top_share(apis,
                                          resulting_difficulty, 
                                          author_name,
                                          author_id,
                                          digest)
    return result

async def cmd_mine(command_str, discord_message, apis):
    if apis.token.mining_target is None:
        return "not sure yet... waiting on my APIs :sob:"

    if 'test' in command_str:
        return await cmd_mine_test(command_str, discord_message, apis)

    try:
        address = apis.storage.user_addresses.get(discord_message.author.id)
    except KeyError:
        return "Looks like you don't have a public address set; run `!setaddress 0xAAA...` first.\nProtip: You can PM me this if you like. Run `!setaddress dontcare` if you don't care."

    try:
        command, nonce = command_str.split(maxsplit=1)
    except:
        return "Bad nonce; try `mine 0xABBA`, `!mine 27`, or `!mine message`"

    try:
        nonce, digest = apis.token.get_digest_for_nonce_str(nonce, address)
    except RuntimeError as e:
        return str(e)

    return parse_mining_results(apis,
                                nonce,
                                digest,
                                save_high_score=True,
                                author_name=discord_message.author.name,
                                author_id=discord_message.author.id)

async def cmd_mine_test(command_str, discord_message, apis):
    """ wrapper around get_digest_for_nonce to make testing easier. Example:

        !mine test 
        0x3b0ec88154c8aecbc7876f50d8915ef7cd6112a604cad4f86f549d5b9eed369a 
        0x540d752A388B4fC1c9Deeb1Cd3716A2B7875D8A6 
        0x03000000000000000440a2682657259316000000e87905d96943030a90de3e74 
    """

    try:
        challenge_number, address, nonce = command_str.split()[-3:]
    except:
        return "Bad command; try `mine test <challenge_number> <address> <nonce>`"

    try:
        address = Web3.toChecksumAddress(address)
    except:
        return "Error parsing address"

    try:
        nonce, digest = apis.token.get_digest_for_nonce_str(nonce, 
                                                            address, 
                                                            challenge_number)
    except RuntimeError as e:
        return str(e)
    
    return parse_mining_results(apis, nonce, digest)

async def cmd_bestshare(command_str, discord_message, apis):
    fmt_str = "Best share digest: `0x{}...` (Difficulty: {}) by {}"
    result = fmt_str.format(apis.storage.top_miner_digest.get()[:16].hex(),
                            prettify_decimals(apis.storage.top_miner_difficulty.get()),
                            apis.storage.top_miner_name.get())
    return result

async def cmd_all_time_high(command_str, discord_message, apis):
    import platform
    time_eth = datetime.datetime.fromtimestamp(apis.storage.all_time_high_eth_timestamp.get())
    time_usd = datetime.datetime.fromtimestamp(apis.storage.all_time_high_usd_timestamp.get())

    if platform.system() == "Linux":
        time_eth = time_eth.strftime("%a %B %-e %Y")
        time_usd = time_usd.strftime("%a %B %-e %Y")
    else:
        time_eth = time_eth.strftime("%a %B %#e %Y")
        time_usd = time_usd.strftime("%a %B %#e %Y")

    if time_eth == time_usd:
        fmt_str = "All time high: **{}Ξ** **${}** ({})"
        result = fmt_str.format(prettify_decimals(apis.storage.all_time_high_eth_price.get()),
                                prettify_decimals(apis.storage.all_time_high_usd_price.get()),
                                time_usd)
    else:
        fmt_str = "All time high: \n**{}Ξ** ({})  **${}** ({})"
        result = fmt_str.format(prettify_decimals(apis.storage.all_time_high_eth_price.get()),
                                time_eth,
                                prettify_decimals(apis.storage.all_time_high_usd_price.get()),
                                time_usd)
    return result

async def cmd_set_all_time_high(command_str, discord_message, apis):
    # !setath 0.007719 2018-06-06 4.68 2018-06-06
    if discord_message.author.id not in config.PRIVILEGED_USER_IDS:
        fmt_str = 'User not allowed to run cmd_set_all_time_high: {} ({})'
        logging.info(fmt_str.format(discord_message.author.id, discord_message.author.name))
        return

    try:
        command, price_eth, time_eth, price_usd, time_usd = command_str.split()
        price_eth = float(price_eth)
        time_eth = datetime.datetime.strptime(time_eth, '%Y-%m-%d').timestamp()
        price_usd = float(price_usd.replace('$', ' '))
        time_usd = datetime.datetime.strptime(time_usd, '%Y-%m-%d').timestamp()

        assert 0 <= price_eth <= 1e20
        assert 0 <= price_usd <= 1e20
    except:
        return "Error parsing; try `!setath <price_eth> YYYY-MM-DD <price_usd> YYYY-MM-DD`"

    apis.storage.all_time_high_eth_price.set(price_eth)
    apis.storage.all_time_high_eth_timestamp.set(time_eth)
    apis.storage.all_time_high_usd_price.set(price_usd)
    apis.storage.all_time_high_usd_timestamp.set(time_usd)

    return "New ATH set!\n---\n{}".format(await cmd_all_time_high(command_str, discord_message, apis))

async def cmd_set_all_time_high_image_filename(command_str, discord_message, apis):
    if discord_message.author.id not in config.PRIVILEGED_USER_IDS:
        fmt_str = 'User not allowed to run cmd_set_all_time_high_image_filename: {} ({})'
        logging.info(fmt_str.format(discord_message.author.id, discord_message.author.name))
        return

    try:
        command, image_filename = command_str.split()
    except:
        return "Error parsing; try `!set ath filename image.img`"

    # to clear the filename, run the command with filename of 'none'
    if image_filename == "none":
        apis.storage.all_time_high_image_filename.set(None)
        return "All-time-high image filename cleared"

    if not os.path.isfile(os.path.join(config.DATA_FOLDER,
                                       image_filename)):
        return "Error; could not find image"

    try:
        apis.storage.all_time_high_image_filename.set(image_filename)
    except:
        return "Error setting image filename. Try again later."
    else:
        await apis.client.send_file(discord_message.channel,
                                    os.path.join(config.DATA_FOLDER,
                                                 apis.storage.all_time_high_image_filename.get()))
        await asyncio.sleep(5.0)
        return "New all-time-high filename set! `{}`".format(image_filename)

async def cmd_set_bestshare(command_str, discord_message, apis):
    if discord_message.author.id not in config.PRIVILEGED_USER_IDS:
        fmt_str = 'User not allowed to run cmd_set_best_share: {} ({})'
        logging.info(fmt_str.format(discord_message.author.id, discord_message.author.name))
        return

    try:
        command, name, user_id, digest, difficulty = command_str.split()
        int(user_id)
        digest = Web3.toBytes(hexstr=digest)
        difficulty = float(difficulty)
        assert 0 <= difficulty <= 1e50
    except:
        return "Error parsing; try `!set top score <name> <id> <digest_as_hex> <difficulty>`"

    try:
        apis.storage.top_miner_difficulty.set(difficulty)
        apis.storage.top_miner_name.set(name)
        apis.storage.top_miner_id.set(user_id)
        apis.storage.top_miner_digest.set(digest)
    except:
        return "Something went wrong... Couldn't set storage"

    fmt_str = "New best share set!\nName:{}\nUser ID:{}\nDigest:{}\nDifficulty:{}\n---\n{}"
    return fmt_str.format(name,
                          user_id,
                          digest.hex(),
                          difficulty,
                          await cmd_bestshare(command_str, discord_message, apis))

async def cmd_set_user_address(command_str, discord_message, apis):
    try:
        address = command_str.split()[-1]
    except:
        return "Something went wrong setting your public address... try `!setaddress 0xAAA...` (Protip: You can PM me this if you like.  Run `!setaddress dontcare` if you don't care.)"

    if address == "dontcare":
        address = "0x0000000000000000000000000000000000000000"

    try:
        address = Web3.toChecksumAddress(address)
    except:
        return "Something went wrong setting your public address... try `!setaddress 0xAAA...`. You can use `!setaddress dontcare` if you don't care."

    if not Web3.isAddress(address):
        return "Something went wrong setting your public address... try `!setaddress 0xAAA...`. You can use `!setaddress dontcare` if you don't care."

    apis.storage.user_addresses.set(discord_message.author.id, address)

    await apis.client.add_reaction(discord_message,"\U0001F44D")  # :thumbsup:
    return "OK-noresponse"

async def cmd_mod_command(command_str, discord_message, apis):
    if discord_message.author.id not in config.PRIVILEGED_USER_IDS:
        fmt_str = 'User not allowed to run cmd_mod_command: {} ({})'
        logging.info(fmt_str.format(discord_message.author.id, discord_message.author.name))
        return "OK-noresponse"

    try:
        message_parts = command_str.split()

        if 'poweroff' in message_parts:
            if 'really' in message_parts:
                raise SystemExit('Exit requested by user {}'.format(discord_message.author.name))
            else:
                return "Really? If you're sure run `!modcommand poweroff really`"

    except SystemExit:
        raise
    except:
        # TODO: remove this
        logging.exception('exception running mod command')
        return "Error parsing command"
    else:
        return "modcommand (poweroff)"

async def cmd_ping(command_str, discord_message, apis):
    #logging.info('command_str is ')
    #import pdb; pdb.set_trace()
    delta = datetime.datetime.utcnow() - discord_message.timestamp
    response = "Discord: {:.1f} ms\n".format(delta.total_seconds() * 1000.0)

    ping_times = ping_wrapper.ping_list(['api.infura.io', 'etherscan.io'])
    for url, latency in ping_times:
        if latency == None:
            response += "{}: down\n".format(url)
        else:
            response += "{}: {:.1f} ms\n".format(url, latency)

    return response

async def cmd_pools(command_str, discord_message, apis):
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

async def cmd_uptime(command_str, discord_message, apis):
    return "Uptime: {}".format(seconds_to_time(time.time() - apis.start_time))

async def cmd_volume(command_str, discord_message, apis):
    if apis.exchanges.last_updated_time() == 0:
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(apis.exchanges.short_url())

    total_eth_volume = 0
    total_btc_volume = 0
    response = ""

    for api in sorted(apis.exchanges.alive_exchanges, key=lambda a: a.exchange_name):
        # skip CMC and apis not directly tracking main currency
        if api.currency_symbol != config.TOKEN_SYMBOL or api.exchange_name == "Coin Market Cap":
            continue

        volume_eth = apis.exchanges.volume_eth(config.TOKEN_SYMBOL, exchange_name=api.exchange_name)
        volume_btc = apis.exchanges.volume_btc(config.TOKEN_SYMBOL, exchange_name=api.exchange_name)
        if volume_eth == 0 and volume_btc == 0:
            continue

        total_eth_volume += volume_eth
        total_btc_volume += volume_btc
        if apis.exchanges.eth_price_usd() == 0:
            response += "{}: **{}Ξ** ".format(api.exchange_name, prettify_decimals(volume_eth))
        else:
            response += "{}: $**{}**({}Ξ) ".format(api.exchange_name, prettify_decimals(volume_eth * apis.exchanges.eth_price_usd()), prettify_decimals(volume_eth))
        if volume_btc != 0:
            if apis.exchanges.btc_price_usd() == 0:
                response += "+ **{}₿** ".format(prettify_decimals(volume_btc))
            else:
                response += "+ $**{}**({}₿) ".format(prettify_decimals(volume_btc * apis.exchanges.btc_price_usd()), prettify_decimals(volume_btc))

    response += "\n"

    if apis.exchanges.eth_price_usd() == 0 or apis.exchanges.btc_price_usd() == 0:
        response += "Total: {}Ξ + {}₿".format(prettify_decimals(total_eth_volume), prettify_decimals(total_btc_volume))
    else:
        response += "Total: $**{}**({}Ξ+{}₿)".format(prettify_decimals((total_eth_volume * apis.exchanges.eth_price_usd()) + (total_btc_volume * apis.exchanges.btc_price_usd())), prettify_decimals(total_eth_volume), prettify_decimals(total_btc_volume))

    if "better" in command_str:
        # !bettervolume
        return ':star2:'*10 + '\n' + response + '\n' + ':star2:'*10
    else:
        return response

async def cmd_ratio(command_str, discord_message, apis):
    if apis.exchanges.last_updated_time() == 0:
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(apis.exchanges.short_url())

    token_price_usd = apis.exchanges.price_eth(config.TOKEN_SYMBOL) * apis.exchanges.eth_price_usd()
    if token_price_usd == 0:
        return ":shrug:"

    return "1 BTC : {:,.0f} {}".format(apis.exchanges.btc_price_usd() / token_price_usd, config.TOKEN_SYMBOL)

async def cmd_rank(command_str, discord_message, apis):
    api_name = "Coin Market Cap"
    api_url = apis.exchanges.short_url(exchange_name=api_name)

    if apis.exchanges.last_updated_time() == 0:
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(api_url)

    rank = apis.exchanges.rank(currency_symbol=config.TOKEN_SYMBOL,
                     exchange_name=api_name)
    if rank is None:
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(api_url)

    return "Rank: **{}** on {} [<{}>]".format(rank, api_name, api_url)

"""Convert from source currency to dest currency. _amount_ indicates total
amount of source currency. Example:
>>> convert(100, 'cents', 'usd')
1
"""
def convert(amount, src, dest, apis):
    src = src.lower()
    dest = dest.lower()
    amount = string_to_float(amount)

    usd_value, result = None, None

    token_price_usd = apis.exchanges.price_eth(config.TOKEN_SYMBOL) * apis.exchanges.eth_price_usd()

    if config.TOKEN_SYMBOL != "0xBTC":
        logging.warning("unknown currency {}; !convert command assumes 0xBTC".format(config.TOKEN_SYMBOL))

    if src in ['0xbtc', '0xbitcoins', '0xbitcoin']:
        usd_value = token_price_usd * amount
    elif src in ['m0xbtc', 'milli0xbtc', 'milli0xbitcoin', 'milli0xbitcoins']:
        usd_value = token_price_usd * amount / 1000.0
    elif src in ['0xsatoshis', '0xsatoshi', 'satoastis', 'satoasti', 'crumbs', 'crumb']:
        usd_value = token_price_usd * amount / 10**8
    elif src in ['eth', 'ethereum', 'ether']:
        usd_value = apis.exchanges.eth_price_usd() * amount
    elif src == 'wei':
        usd_value = apis.exchanges.eth_price_usd() * amount / 10**18
    elif src in ['btc', 'bitcoins', 'bitcoin']:
        usd_value = apis.exchanges.btc_price_usd() * amount
    elif src in ['mbtc', 'millibtc', 'millibitcoins', 'millibitcoin']:
        usd_value = apis.exchanges.btc_price_usd() * amount / 1000.0
    elif src in ['satoshis', 'satoshi']:
        usd_value = apis.exchanges.btc_price_usd() * amount / 10**8
    elif src in ['usd', 'dollars', 'dollar', 'ddollar', 'bucks', 'buck']:
        usd_value = amount
    elif src in ['cents', 'cent']:
        usd_value = amount / 100.0
    else:
        for price, names in config.EXPENSIVE_STUFF:
            if util.string_contains_any(src, names, exhaustive_search=True, require_cmd_char=False):
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
        result = usd_value / apis.exchanges.eth_price_usd()
    elif dest == 'wei':
        result = 10**18 * usd_value / apis.exchanges.eth_price_usd()
    elif dest in ['btc', 'bitcoins', 'bitcoin']:
        result = usd_value / apis.exchanges.btc_price_usd()
    elif dest in ['mbtc', 'millibtc', 'millibitcoins', 'millibitcoin']:
        result = usd_value * 1000.0 / apis.exchanges.btc_price_usd()
    elif dest in ['satoshis', 'satoshi']:
        result = 10**8 * usd_value / apis.exchanges.btc_price_usd()
    elif dest in ['usd', 'dollars', 'dollar', 'ddollar', 'bucks', 'buck']:
        result = usd_value
    elif dest in ['cents', 'cent']:
        result = usd_value * 100.0
    else:
        for price, names in config.EXPENSIVE_STUFF:
            if util.string_contains_any(dest, names, exhaustive_search=True, require_cmd_char=False):
                dest = names[0]  # replaces provided name with the non-typo'd version
                result = usd_value / price
                break

    if result == None:
        return "Bad currency ({}). 0xbtc, 0xsatoshis, eth, wei, btc, mbtc, satoshis, and usd are supported.".format(dest)

    amount = prettify_decimals(amount)
    result = prettify_decimals(result)

    return "{} {} = **{}** {}".format(amount, src, result, dest)

async def cmd_convert(command_str, discord_message, apis):
    # example input: '!convert 1 usd to 0xbtc'
    if apis.exchanges.last_updated_time() == 0 or apis.exchanges.eth_price_usd() == 0 or apis.exchanges.btc_price_usd() == 0:
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(apis.exchanges.short_url())

    split = command_str.split()
    try:
        _, amount, src, _, dest = split
        return convert(amount, src, dest, apis)
    except ValueError:
        pass
    except:
        return "Something went wrong :sob: try this: `!convert 1 eth to {}`".format(config.TOKEN_SYMBOL)

    # example input: '!convert 1 usd 0xbtc'
    try:
        _, amount, src, dest = split
        return convert(amount, src, dest, apis)
    except:
        return "Something went wrong :sob: try this: `!convert 1 eth to {}`".format(config.TOKEN_SYMBOL)

    # ValueError exceptions lead here
    return "Something went wrong :sob: try this: `!convert 1 eth to {}`".format(config.TOKEN_SYMBOL)
