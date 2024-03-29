
import logging
import time
import random
import datetime  # !help !ath
import re
import os
import asyncio
import discord

import configuration as config
import util
from text_graph import make_graph

import ping_wrapper  # !ping command
from web3 import Web3  # !mine command
#import etherscan  # !holders command, TODO: re-enable after fixing holders chart

from formatting_helpers import (prettify_decimals, 
                                percent_change_to_emoji,
                                seconds_to_n_time_ago,
                                seconds_to_time,
                                to_readable_thousands,
                                string_to_float,
                                unix_timestamp_to_readable_date,
                                unix_timestamp_to_readable_date_time)

from memory_usage import rss_resource
from version import __version__ as app_version


_MINIMUM_USD_LIQUIDITY_TO_DISPLAY = 50  # controls which exchanges are shown individually in !liquidity


class RebootRequest(Exception):
    pass


async def cmd_help(command_str, discord_message, apis):
    return ("trading commands: `price`  `price <exchange>`  `volume`  `ratio`  `rank`  `btc`  `eth`  `marketcap`\n"
            + "price commands: {}\n".format("  ".join("`{}`".format(c[1][0]) for c in random.Random(datetime.date.today().strftime("%j")).sample(config.EXPENSIVE_STUFF, 5)))
            #+ "bot commands: `uptime ping` "
            + "token info: `supply`  `difficulty`  `hashrate`  `blocktime`  `holders`  `halvening`  `burned` `balance`\n"
            + "quick link commands: `whitepaper`  `website`  `ann`  `contract`  `stats`  `miners`  `merch`\n"
            + "tools: `convert`  `income`  `cost`  `yield`  `mine`")


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


async def cmd_graph(command_str, discord_message, apis):
    # Uniswap v2  **0.00067Ξ**   $0.20   34.5Ξ volume
    # ```
    # 0.00070 |
    #         |                 ***
    #         |                *   ****
    #  +31.4% |        *** ** *
    #         |  ******   *  *
    #         |**
    # 0.00040 |-----------|-----------|
    #       -24h        -12h         now
    # ```

    # TODO: allowing !graph btc or !graph eth would be cool

    # allow !graph <exchange name>
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

            eth_token_price = apis.exchanges.price_eth(config.TOKEN_SYMBOL, exchange_name=exchange.exchange_name)
            if eth_token_price == 0:
                token_price = apis.exchanges.price_usd(config.TOKEN_SYMBOL, exchange_name=exchange.exchange_name)
                eth_token_price = token_price / apis.exchanges.eth_price_usd()
            else:
                token_price = eth_token_price * apis.exchanges.eth_price_usd()

            prices = apis.exchanges.previous_hours_prices(config.TOKEN_SYMBOL, exchange_name=exchange.exchange_name)
            if prices is None:
                return "No price history for {} :sob:".format(exchange.exchange_name)
            elif len(prices) < 4:
                return "Still collecting data for {}, try again in {} hours or so.".format(exchange.exchange_name, 5-len(prices))
            else:
                if len(prices) < 24:
                    graph_incomplete_msg = f"* only showing {len(prices)}h of data; graph complete in {24-len(prices)}h"
                else:
                    graph_incomplete_msg = ""

                graph_text = make_graph(prices, labels=['-24h', '-12h', 'now'])

                message = "{}  **{}Ξ**   ${}   {}Ξ volume\n```{}```{}".format(
                    exchange.exchange_name,
                    prettify_decimals(eth_token_price),
                    prettify_decimals(token_price),
                    prettify_decimals(apis.exchanges.volume_eth(config.TOKEN_SYMBOL, exchange_name=exchange.exchange_name)),
                    graph_text,
                    graph_incomplete_msg,
                )
                return message

    return "Graph what? try `!graph uniswap`"


def show_price_from_source(apis, source='aggregate'):
    if (apis.exchanges.last_updated_time(exchange_name=source) == 0):
        logging.debug("cannot show api '{}'; it has not been updated yet".format(source))
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(apis.exchanges.short_url(exchange_name=source))

    eth_token_price = apis.exchanges.price_eth(config.TOKEN_SYMBOL, exchange_name=source)

    if eth_token_price == 0:
        token_price_usd = apis.exchanges.price_usd(config.TOKEN_SYMBOL, exchange_name=source)
        eth_token_price = token_price_usd / apis.exchanges.eth_price_usd()
    else:
        token_price_usd = eth_token_price * apis.exchanges.eth_price_usd()

    eth_price_on_this_exchange = float(apis.exchanges.eth_price_usd(exchange_name=source))

    # Enclaves usually fails this way
    if token_price_usd == 0:
        logging.debug("cannot show api '{}'; eth_token_price:{}; eth_price_usd:{}".format(
            source, eth_token_price, apis.exchanges.eth_price_usd()))
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(apis.exchanges.short_url(exchange_name=source))

    percent_change_str = ""
    if apis.exchanges.change_24h(config.TOKEN_SYMBOL, exchange_name=source) is None:
        percent_change_str = ""
    elif apis.exchanges.change_24h(config.TOKEN_SYMBOL, exchange_name=source) == 0:
        percent_change_str = "**0**% "
    else:
        percent_change_str = "**{:+.2f}**% {} ".format(100.0 * apis.exchanges.change_24h(config.TOKEN_SYMBOL, exchange_name=source),
                                                       percent_change_to_emoji(apis.exchanges.change_24h(config.TOKEN_SYMBOL, exchange_name=source)),)
    fmt_str = "{}{}: {}({:.5f} Ξ) {}{}[<{}>]"
    result = fmt_str.format('' if source == 'aggregate' else '**{}** '.format(source),
                            seconds_to_n_time_ago(time.time() - apis.exchanges.last_updated_time(exchange_name=source)),
                            '' if token_price_usd == 0 else '**${:.3f}** '.format(token_price_usd),
                            eth_token_price,
                            percent_change_str,
                            '' if eth_price_on_this_exchange == 0 else '(ETH: **${:.0f}**) '.format(eth_price_on_this_exchange),
                            apis.exchanges.short_url(exchange_name=source))
    return result


def show_liquidity_from_source(apis, source='aggregate'):
    generic_err_str = "not sure yet... waiting on my APIs :sob: [<{}>]".format(apis.exchanges.short_url(exchange_name=source))
    last_updated_time = apis.exchanges.last_updated_time(exchange_name=source)
    if (last_updated_time == 0):
        logging.debug("cannot show api '{}'; it has not been updated yet".format(source))
        return generic_err_str

    # liquidity types - entries are like (symbol, liq amount, symbol price)
    #       where symbol       = string label to show for this liquidity type - probably a ticker symbol like DAI
    #             liq amount   = liquidity amount available in units of 'symbol'
    #             symbol price = price of the 'symbol' which is used to convert 'liq amount' to units of usd
    liquidity_types = [
        (
            config.TOKEN_SYMBOL,
            apis.exchanges.liquidity_tokens(config.TOKEN_SYMBOL, exchange_name=source),
            apis.exchanges.price_converted_to_usd(config.TOKEN_SYMBOL, exchange_name=source)
        ),
        (
            "Ξ",
            apis.exchanges.liquidity_eth(config.TOKEN_SYMBOL, exchange_name=source),
            apis.exchanges.eth_price_usd()
        ),
        (
            "₿",
            apis.exchanges.liquidity_btc(config.TOKEN_SYMBOL, exchange_name=source),
            apis.exchanges.btc_price_usd()
        ),
        (
            "DAI",
            apis.exchanges.liquidity_dai(config.TOKEN_SYMBOL, exchange_name=source),
            1
        ),
        (
            "USD",
            apis.exchanges.liquidity_usd(config.TOKEN_SYMBOL, exchange_name=source),
            1
        ),
    ]

    total_liq_usd = 0
    individual_liquidity_strings = []

    for liq_symbol, liq_amount, liq_price in liquidity_types:
        if liq_amount is None or liq_amount == 0:
            continue
        else:
            total_liq_usd += liq_amount * liq_price
            individual_liquidity_strings.append(
                "{} {}".format(
                    prettify_decimals(liq_amount),
                    liq_symbol,
            ))

    if total_liq_usd < _MINIMUM_USD_LIQUIDITY_TO_DISPLAY:
        # hide exchanges with less than threshold liquidity from this list
        # this return value causes caller to hide the output alltogether, since the 
        # caller is looking for this exact error message. this should be refactored
        # to raise an exception or something, but currently no commands ever raise
        # exceptions (intentionally)
        return generic_err_str
    else:
        source_name = "Total" if source == "aggregate" else source
        return "{}: $**{:,.0f}** ({})".format(
            source_name,
            total_liq_usd,
            " + ".join(individual_liquidity_strings))


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
    if util.string_contains_any(command_str,
                                ['all', 'al', 'prices'],
                                exhaustive_search=True,
                                require_cmd_char=False):
        return await cmd_price_all(command_str, discord_message, apis)
    elif util.string_contains_any(command_str,
                                  ['0xbtc'],
                                  exhaustive_search=True,
                                  require_cmd_char=False):
        return show_price_from_source(apis)
        # in this call to string_contains_any, we ignore commands containing '0x'. That
        # way this does not match !0xbitcoin
    elif util.string_contains_any(command_str,
                                  ['btc', 'bitcoin'],
                                  exhaustive_search=True,
                                  require_cmd_char=False,
                                  ignore_matches_containing='0x'):
        return await cmd_bitcoinprice(command_str, discord_message, apis)
    elif util.string_contains_any(command_str,
                                  ['eth', 'ethereum'],
                                  exhaustive_search=True,
                                  require_cmd_char=False):
        return await cmd_ethereumprice(command_str, discord_message, apis)
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


async def cmd_liquidity(command_str, discord_message, apis):
    response_lines = []
    # iterate over all exchange names + one extra (named 'aggregate') to show totals
    for exchange in sorted(apis.exchanges.alive_exchanges, key=lambda a: a.exchange_name):
        # skip CMC, LCW and apis not directly tracking the main currency
        if (exchange.currency_symbol != config.TOKEN_SYMBOL
            or exchange.exchange_name == "Coin Market Cap"
            or exchange.exchange_name == "Live Coin Watch"):
            continue
        # TODO: skip exchanges with <$100 volume in last 24h?
        # if exchange_has_low_volume(apis, exchange):
        #     continue
        response_lines.append(show_liquidity_from_source(apis, source=exchange.exchange_name))

    response_lines.append("")  # adds a blank line before the 'total' line
    response_lines.append(show_liquidity_from_source(apis, source='aggregate'))

    response_str = ""
    for line in response_lines:
        # TODO: remove this when 'alive_exchanges' excludes apis correctly
        if line.startswith('not sure yet'):
            logging.warning("bugcheck: removed line 'not sure yet' from liquidity ({})".format(line))
        else:
            response_str += line + '\n'

    if response_str == "":
        return ":shrug:"
    return response_str


async def cmd_bitcoinprice(command_str, discord_message, apis):
    if apis.exchanges.last_updated_time() == 0:
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(apis.exchanges.short_url())

    if apis.exchanges.btc_price_usd() == 0:
        return ":shrug:"

    fmt_str = "Bitcoin price {}: **${:.0f}**"
    result = fmt_str.format(seconds_to_n_time_ago(time.time() - apis.exchanges.last_updated_time()),
                            apis.exchanges.btc_price_usd())
    return result


async def cmd_ethereumprice(command_str, discord_message, apis):
    if apis.exchanges.last_updated_time() == 0:
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(apis.exchanges.short_url())

    if apis.exchanges.eth_price_usd() == 0:
        return ":shrug:"

    fmt_str = "Ethereum price {}: **${:.0f}**"
    result = fmt_str.format(seconds_to_n_time_ago(time.time() - apis.exchanges.last_updated_time()), 
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


async def cmd_challenge(command_str, discord_message, apis):
    if apis.token.challenge_number is None:
        return ":shrug:"

    return "Current challenge: `{}`".format(apis.token.challenge_number)


async def cmd_difficulty(command_str, discord_message, apis):
    if apis.token.difficulty is None:
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
    if apis.token.seconds_per_reward is None:
        return ":shrug:"

    fmt_str = "Current average block time: **{}** (average taken over the last {})"
    result = fmt_str.format('unknown' if apis.token.seconds_per_reward == float('inf') else seconds_to_time(apis.token.seconds_per_reward),
                            seconds_to_time(apis.token.seconds_since_readjustment, granularity=1))
    return result


async def cmd_hashrate(command_str, discord_message, apis):
    if apis.token.estimated_hashrate_since_readjustment is None:
        result = ":shrug:"
    # check if the 24h hashrate estimate was not calculated
    #
    # unfortunately infura v3 removed the functions necessary to calculate it, and
    # we store 'None' in that case. If they ever being back support it should be
    # populated again and just work
    elif apis.token.estimated_hashrate_24h is None:
        fmt_str = "Estimated hashrate: **{}** over the last {}."
        result = fmt_str.format(to_readable_thousands(apis.token.estimated_hashrate_since_readjustment, unit_type="hashrate", decimals=2),
                                seconds_to_time(apis.token.seconds_since_readjustment, granularity=2))
    else:
        fmt_str = "Estimated hashrate: **{}** over the last {}, and **{}** over the last 24 hours."
        result = fmt_str.format(to_readable_thousands(apis.token.estimated_hashrate_since_readjustment, unit_type="hashrate", decimals=2),
                                seconds_to_time(apis.token.seconds_since_readjustment, granularity=2),
                                to_readable_thousands(apis.token.estimated_hashrate_24h, unit_type="hashrate", decimals=2))
    return result


async def cmd_balance_of(command_str, discord_message, apis):
    if apis.token.estimated_hashrate_since_readjustment is None:
        return ":shrug:"

    try:
        address = command_str.split()[-1:][0]
        address = Web3.toChecksumAddress(address)
    except:
        return "Bad address, try `!balance of 0x0000000000000000000000000000000000000000`"

    try:
        fmt_str = "0xBitcoin balance: **{}** 0xBTC."
        result = fmt_str.format(prettify_decimals(apis.token.balance_of(address)))
    except:
        logging.exception('exception in token.balance_of')
        return ":shrug:"
    else:
        return result


async def cmd_tokens_minted(command_str, discord_message, apis):
    if apis.token.tokens_minted is None:
        return ":shrug:"

    fmt_str = "Tokens in circulation: **{}** / {} {}"
    result = fmt_str.format(prettify_decimals(apis.token.tokens_minted),
                            prettify_decimals(apis.token.total_supply),
                            apis.token.symbol)
    return result


async def cmd_era(command_str, discord_message, apis):
    try:
        apis.token.era
    except AttributeError:
        return ":shrug:"

    if apis.token.era is None:
        return ":shrug:"

    if apis.token.era == 39:
        return "In era 39 / 39"

    fmt_str = "Current era: **{}** / 39.  In {} the reward will drop to **{}** {}"
    result = fmt_str.format(apis.token.era,
                            seconds_to_time(apis.token.seconds_remaining_in_era),
                            apis.token.reward / 2,
                            apis.token.symbol)
    return result


async def cmd_tokens_burned(command_str, discord_message, apis):
    if apis.token.lost_token_balance is None:
        return ":shrug:"

    fmt_str = "**{}** {} burned [<https://bit.ly/2AulG0C>, <https://bit.ly/3csDklj>]"
    result = fmt_str.format(apis.token.lost_token_balance, apis.token.symbol)
    return result


async def cmd_holders(command_str, discord_message, apis):
    # TODO: fix holders chart and remove this stub
    return ":shrug: etherscan's API is not working"

    # if apis.token.addr_0_balance is None:
    #     return ":shrug:"

    # await apis.client.send_file(discord_message.channel,
    #                             etherscan.saved_holders_chart_filename)

    # return 'OK-noresponse'


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

    # TODO: throws DeprecationWarning: invalid escape sequence \d
    match = re.match("([<\d.,]+)", hashrate)
    if not match:
        return "Bad hashrate; try `!income 5`, `!income 300mh`, or `!income 2.8gh`"
    try:
        hashrate = string_to_float(match.group(1)) * selected_multiplier
    except ValueError:
        return "Bad hashrate; try `!income 5`, `!income 300mh`, or `!income 2.8gh`"

    if hashrate == 0:
        return "Bad hashrate; try `!income 5`, `!income 300mh`, or `!income 2.8gh`"

    tokens_per_day = 0.8 * 86400 * apis.token.reward * hashrate / ((2**22) * apis.token.difficulty)
    seconds_per_block = 1.2 * ((2**22) * apis.token.difficulty) / hashrate

    if tokens_per_day > 1:
        tokens_over_time_str = "**{}** tokens/day".format(prettify_decimals(tokens_per_day))
    else:
        tokens_over_time_str = "**{}** tokens/week".format(prettify_decimals(tokens_per_day * 7))

    fmt_str = "Income for {}: {}; **{}** per block solo"
    return fmt_str.format(to_readable_thousands(hashrate, unit_type='hashrate'),
                          tokens_over_time_str,
                          seconds_to_time(seconds_per_block))


async def cmd_cost(command_str, discord_message, apis):
    response = ""
    verbose_response = ""
    if apis.gas_price_api.gas_price == None:
        return "not sure yet... waiting on my APIs :sob:"

    # gas cost

    # about 92042 gas per mint (and 10% cost 94,854 and a diff adjust cost even more)
    # 0.009513791719658944 eth for 103.3 gewi
    # 0.010306009645882052 eth for 112 gwei
    # -> 0.00009205830231906971 eth per gwei

    gas_cost_per_mint_usd = apis.exchanges.eth_price_usd() * 0.00009205830231906971 * apis.gas_price_api.gas_price
    gas_cost_per_token_usd = gas_cost_per_mint_usd / apis.token.reward
    response += "Token cost: **${:.2f}** gas @ {:.1f} gwei".format(
        gas_cost_per_token_usd,
        apis.gas_price_api.gas_price)

    verbose_response += "Eth price: ${:.2f}, Gas price: {:.1f} gwei\n".format(
        apis.exchanges.eth_price_usd(),
        apis.gas_price_api.gas_price)

    verbose_response += " -> ${:.2f} / {} eth per mint in gas\n".format(
        gas_cost_per_mint_usd,
        prettify_decimals(gas_cost_per_mint_usd / apis.exchanges.eth_price_usd()))

    # electricity cost

    usd_cost_per_kwh = 0.10

    # stats for blackminer f2
    # https://shop.fpga.guide/products/blackminer-f2-by-hashaltcoin?variant=35115212931235
    example_miner_hashrate = 27.4e9  # 27.4 gh/s
    example_miner_power = 885  # 885 W

    mints_per_day = 86400 * example_miner_hashrate / ((2**22) * apis.token.difficulty)
    kwh_used_per_day = 24 * example_miner_power / 1000.0

    kwh_used_per_mint = kwh_used_per_day / mints_per_day
    usd_cost_per_mint = kwh_used_per_mint * usd_cost_per_kwh
    usd_cost_per_token = usd_cost_per_mint / apis.token.reward

    response += " + **${:.2f}** electricity ({} diff, Blackminer F2, {}¢/kwh)".format(
        usd_cost_per_token,
        prettify_decimals(apis.token.difficulty),
        int(100 * usd_cost_per_kwh))

    response += " = **${:.2f}** total".format(
        gas_cost_per_token_usd + usd_cost_per_token)

    verbose_response += "Example hashrate: {}, Power: {}W, Bill: {}¢/kwh\n".format(
        to_readable_thousands(example_miner_hashrate, unit_type='hashrate'),
        example_miner_power,
        int(100 * usd_cost_per_kwh))

    verbose_response += " -> Solutions per day: {}, Power per day: {}kwh\n".format(
        prettify_decimals(mints_per_day),
        prettify_decimals(kwh_used_per_day))

    verbose_response += " -> ${:.2f} / {} eth per mint in electricity\n".format(
        usd_cost_per_mint,
        prettify_decimals(usd_cost_per_mint / apis.exchanges.eth_price_usd()))

    if any(x in command_str for x in ["explain", "verbose", "all", "detail"]):
        response = verbose_response + response

    return response


async def cmd_yield(command_str, discord_message, apis):
    response = ""
    if apis.gas_price_api.gas_price == None:
        return "not sure yet... waiting on my APIs :sob:"

    msg = ""
    for exchange in sorted(apis.exchanges.alive_exchanges, key=lambda a: a.exchange_name):
        # skip CMC, LCW and apis not directly tracking the main currency
        if (exchange.currency_symbol != config.TOKEN_SYMBOL
            or exchange.exchange_name == "Coin Market Cap"
            or exchange.exchange_name == "Live Coin Watch"):
            continue

        number_of_hours_covered_by_volume = apis.exchanges.number_of_hours_covered_by_volume(config.TOKEN_SYMBOL, exchange.exchange_name)
        if number_of_hours_covered_by_volume is None:
            continue

        if not exchange.show_yield:
            continue

        token_price_usd = apis.exchanges.price_eth(config.TOKEN_SYMBOL) * apis.exchanges.eth_price_usd()
        msg += "**${:.1f}** in yield in the last {} on {}\n".format(
            sum(exchange.hourly_volume_tokens) * token_price_usd * 0.01,  # assumes 1% pools
            seconds_to_time(number_of_hours_covered_by_volume * 3600, granularity=1),
            exchange.exchange_name
        )

    if msg == "":
        return ":shrug:"
    return msg


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
    resulting_difficulty = apis.token.max_target / Web3.toInt(digest)
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
    time_eth = unix_timestamp_to_readable_date(apis.storage.all_time_high_eth_timestamp.get())
    time_usd = unix_timestamp_to_readable_date(apis.storage.all_time_high_usd_timestamp.get())

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


async def helper_show_all_time_high_image_in_channel(apis, channel):
    filename = apis.storage.all_time_high_image_filename.get()
    if filename is None:
        logging.info(f"Not showing all time high image; filename is '{filename}'")
        return
    logging.info(f"Showing ath image; filename is '{filename}'")
    with open(os.path.join(config.DATA_FOLDER,
                           filename),
              "rb") as handle:
        filename_to_show = filename
        file_to_send = discord.File(handle, filename=filename_to_show)
        await channel.send(file=file_to_send)


async def cmd_set_all_time_high_image_filename(command_str, discord_message, apis):
    if discord_message.author.id not in config.PRIVILEGED_USER_IDS:
        fmt_str = 'User not allowed to run cmd_set_all_time_high_image_filename: {} ({})'
        logging.info(fmt_str.format(discord_message.author.id, discord_message.author.name))
        return

    try:
        current_filename = apis.storage.all_time_high_image_filename.get()
    except KeyError:
        current_filename = "<unset>"

    try:
        command, image_filename = command_str.split()
    except ValueError:
        response = "Error parsing; try `!set ath filename image.img` or  `!set ath filename none`"

        response += f"\nCurrent filename: {current_filename}"
        return response

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
        await helper_show_all_time_high_image_in_channel(apis, discord_message.channel)
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

    await discord_message.add_reaction("\U0001F44D")  # :thumbsup:
    return "OK-noresponse"


async def cmd_mod_command(command_str, discord_message, apis):
    if discord_message.author.id not in config.PRIVILEGED_USER_IDS:
        fmt_str = 'User not allowed to run cmd_mod_command: {} ({})'
        logging.info(fmt_str.format(discord_message.author.id, discord_message.author.name))
        return "OK-noresponse"

    try:
        message_parts = command_str.split()

        if 'poweroff' in message_parts and 'really' in message_parts:
            await discord_message.add_reaction("\U0001F44D")  # :thumbsup:
            raise SystemExit('Exit requested by user {}'.format(discord_message.author.name))
        elif 'poweroff' in message_parts:
            return "Really? If you're sure run `!modcommand poweroff really`"
        elif 'reboot' in message_parts and 'really' in message_parts:
            await discord_message.add_reaction("\U0001F44D")  # :thumbsup:
            raise RebootRequest('Reboot requested by user {}'.format(discord_message.author.name))
        elif 'reboot' in message_parts:
            return "Really? If you're sure run `!modcommand reboot really`"

    except (SystemExit, RebootRequest):
        raise
    except:
        # TODO: remove this
        logging.exception('exception running mod command')
        return "Error parsing command"
    else:
        return "modcommand poweroff|reboot"


async def get_ping_times(command_str, discord_message, apis):
    discord_time_delta = datetime.datetime.utcnow() - discord_message.created_at
    discord_latency_ms = discord_time_delta.total_seconds() * 1000.0

    ping_times = [('Discord API', discord_latency_ms)]
    ping_times += ping_wrapper.ping_list([
        # 'mainnet.infura.io',
        'etherscan.io',
        'ethgas.watch',
        'data-api.defipulse.com',
        # 'rpc-mainnet.matic.network'
    ], count=2)

    return ping_times


async def cmd_status(command_str, discord_message, apis):
    # TODO: this function should build a list of label, status tuples then
    # format them all at the end
    response = "```diff\n"
    # TODO: sort exchange list alphabetically
    for exchange in apis.exchanges.all_exchanges:
        full_exchange_name = "{} [{}]:".format(exchange.exchange_name,
                                               exchange.currency_symbol)
        if exchange.update_failure_count > 0:
            if exchange.last_updated_time == 0:
                time_str = "not yet updated"
            else:
                time_str = "last updated {} ago".format(seconds_to_time(time.time() - exchange.last_updated_time),
                                                        granularity=1)
            response += "- {:<24} {}\n".format(full_exchange_name,
                                               time_str)
        else:
            response += "+ {:<24} OK (took {})\n".format(
                full_exchange_name, seconds_to_time(exchange.last_update_duration,
                                                    granularity=1,
                                                    show_subsecond_values=True))

    ping_times = await get_ping_times(command_str, discord_message, apis)
    for url, latency in ping_times:
        url = url + ':'
        if latency is None:
            response += "- {:<24} down\n".format(url)
        else:
            response += "+ {:<24} {:.1f} ms\n".format(url, latency)
    try:
        response += "+ {:<24} {:.2f} MB\n".format("Memory:", rss_resource())
    except ModuleNotFoundError:
        pass

    response += "+ {:<24} {}\n".format(
        "Uptime:",
        seconds_to_time(time.time() - apis.start_time), granularity=2)

    response += "+ {:<24} {}\n".format("Version:", app_version)

    return response + "```"


async def cmd_pools(command_str, discord_message, apis):
    all_pools = (
        ("Token Mining Pool", "http://TokenMiningPool.com", "0xeabe"),
        ("mike.rs pool", "http://mike.rs", "0x5021"),
        # ("tosti.ro", "http://0xbtc.tosti.ro", "0x540d"),
        ("mvis.ca", "https://mvis.ca/", "0x7d3e"),
        # TODO: uncomment when extremehash finds a block
        # ("ExtremeHash.io", "http://0xbtc.extremehash.io/", "0xbbdf"),
    )
    response = ""
    for name, url, address in all_pools:
        response += "{} <{}>\n".format(name, url)

    return response


async def cmd_uptime(command_str, discord_message, apis):
    return "Uptime: {}".format(seconds_to_time(time.time() - apis.start_time))


async def cmd_washing_machine(command_str, discord_message, apis):
    token_price_usd = apis.exchanges.price_eth(config.TOKEN_SYMBOL) * apis.exchanges.eth_price_usd()

    return "jaykslol's washing machine cost **${}** (750 0xBTC)".format(
        prettify_decimals(token_price_usd * 750.0))


async def cmd_volume(command_str, discord_message, apis):
    if apis.exchanges.last_updated_time() == 0:
        return "not sure yet... waiting on my APIs :sob: [<{}>]".format(apis.exchanges.short_url())

    total_eth_volume = 0
    total_btc_volume = 0
    total_usd_volume = 0
    response = ""

    for api in sorted(apis.exchanges.alive_exchanges, key=lambda a: a.exchange_name):
        # skip CMC and apis not directly tracking main currency
        if api.currency_symbol != config.TOKEN_SYMBOL or api.exchange_name == "Coin Market Cap":
            continue

        volume_eth = apis.exchanges.volume_eth(config.TOKEN_SYMBOL, exchange_name=api.exchange_name)
        volume_btc = apis.exchanges.volume_btc(config.TOKEN_SYMBOL, exchange_name=api.exchange_name)
        volume_usd = apis.exchanges.volume_usd(config.TOKEN_SYMBOL, exchange_name=api.exchange_name)

        if volume_eth == 0 and volume_btc == 0 and volume_usd == 0:
            continue

        total_eth_volume += volume_eth
        total_btc_volume += volume_btc
        total_usd_volume += volume_usd

        response += "{}: ".format(api.exchange_name)

        if volume_eth != 0:
            if apis.exchanges.eth_price_usd() == 0:
                response += "**{}Ξ** ".format(prettify_decimals(volume_eth))
            else:
                response += "$**{}**({}Ξ) ".format(prettify_decimals(volume_eth * apis.exchanges.eth_price_usd()), prettify_decimals(volume_eth))

        if volume_btc != 0:
            if volume_eth != 0:
                response += "+ "

            if apis.exchanges.btc_price_usd() == 0:
                response += "**{}₿** ".format(prettify_decimals(volume_btc))
            else:
                response += "$**{}**({}₿) ".format(prettify_decimals(volume_btc * apis.exchanges.btc_price_usd()), prettify_decimals(volume_btc))

        if volume_usd != 0:
            if volume_eth != 0 or volume_btc != 0:
                response += "+ "
            response += "$**{}** ".format(prettify_decimals(volume_usd))

        number_of_hours_covered_by_volume = apis.exchanges.number_of_hours_covered_by_volume(config.TOKEN_SYMBOL, api.exchange_name)
        if number_of_hours_covered_by_volume != None and number_of_hours_covered_by_volume < 24:
            response += "*only showing last {} hours of volume ".format(number_of_hours_covered_by_volume)

        response += "\n"

    response += "\n"

    if apis.exchanges.eth_price_usd() == 0 or apis.exchanges.btc_price_usd() == 0:
        response += "Total: {}Ξ + {}₿ + ${}".format(prettify_decimals(total_eth_volume), prettify_decimals(total_btc_volume), prettify_decimals(total_usd_volume))
    else:
        response += "Total: $**{}**({}Ξ+{}₿+${})".format(prettify_decimals(total_usd_volume + (total_eth_volume * apis.exchanges.eth_price_usd()) + (total_btc_volume * apis.exchanges.btc_price_usd())), prettify_decimals(total_eth_volume), prettify_decimals(total_btc_volume), prettify_decimals(total_usd_volume))

    if "better" in command_str:
        # !bettervolume
        return ':star2:' * 10 + '\n' + response + '\n' + ':star2:' * 10
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


def convert(amount, src, dest, apis):
    """
    Convert from source currency to dest currency. _amount_ indicates total
    amount of source currency. Example:
    >>> convert(100, 'cents', 'usd')
    1
    """
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
            if util.string_contains_any(src, names, exhaustive_search=True, require_cmd_char=False, ignore_case=True):
                src = names[0]  # replace name with the non-typo'd version
                usd_value = amount * price
                break

    if usd_value is None:
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
            if util.string_contains_any(dest, names, exhaustive_search=True, require_cmd_char=False, ignore_case=True):
                dest = names[0]  # replaces provided name with the non-typo'd version
                result = usd_value / price
                break

    if result is None:
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
