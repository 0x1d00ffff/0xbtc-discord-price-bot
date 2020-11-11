"""
API for Balancer distributed exchange (balancer.exchange)
Price info is pulled from the smart contract

NOTE: Balancer is in the first stage of 3 main stages of development. Things will change
      in v2 and 3, so this is a minimal implementation to support v1. Known changes
      include Smart Order Router which will be used in the future to pick the best route
      and price through all the balancer pools. This change would potentially allow
      this module to use any pool automatically and simplify its interface.
"""
import logging
from web3 import Web3
import time
from collections import defaultdict

from .base_exchange import Daily24hChangeTrackedAPI, NoLiquidityException

from .balancer_abi import bpool_abi
from .erc20_abi import erc20_abi
from secret_info import ETHEREUM_NODE_URL
from constants import SECONDS_PER_ETH_BLOCK
from token_class import Token
from weighted_average import WeightedAverage


exchanges = (
    (("0xBTC", "WETH"),
        "0xDBCd8b30eC1C4b136e740C147112f39D41a10166"),
    (("DUST", "DAI", "0xBTC", "BAL", "MATIC"),
        "0x6af162b6c48Fc99722c7A656ABA9520f43338c72"),
    (("DUST", "KIWI", "UNI", "LINK", "0xBTC", "BAL", "WETH", "GRT"),
        "0x63A63f2cAd45fee80b242436BA71e0f462A4178E"),
    (("DUST", "0xBTC"),
        "0x2b36d183be387Ca2cF81B63EFddDb030F3a643eb"),
)


def get_exchange_addresses_for_token(token_symbol):
    result_list = []
    for token_symbols, exchange_address in exchanges:
        if token_symbol in token_symbols:
            result_list.append(exchange_address)
    return result_list


def is_token_in_exchange(token_address, exchange_address):
    for symbols, address in exchanges:
        if (exchange_address.lower() == address.lower() 
                and token_address.lower() in list(s.lower() for s in symbols)):
            return True
    return False


def is_pool_empty(web3, bpool_address):
    """Returns true if the pool contains liquidity."""
    for address, balance in get_reserves(web3, bpool_address):
        if balance == 0:
            return True
    return False


def get_pooled_balance_for_address(web3, bpool_address, holder_address):
    """Get the liquidity balance of a particular address in a balancer pool.
    Returns a list like: 
    [
        (token_address, token_balance),
        (token_address, token_balance)
    ] """
    bpool = web3.eth.contract(address=bpool_address, abi=bpool_abi)
    # liquidity_token_balance_of_user = (
    #     bpool.functions.balanceOf(holder_address).call()
    #     / 10**bpool.functions.decimals().call())
    liquidity_token_total_supply = bpool.functions.totalSupply().call()
    if liquidity_token_total_supply == 0:
        liquidity_token_balance_of_user = 0
        ownership_percentage_of_user = 0
    else:
        liquidity_token_balance_of_user = bpool.functions.balanceOf(holder_address).call()
        ownership_percentage_of_user = liquidity_token_balance_of_user / liquidity_token_total_supply
    # print('liquidity_token_balance_of_user: {}'.format(liquidity_token_balance_of_user))
    # print('ownership_percentage_of_user: {}'.format(ownership_percentage_of_user))
    reserves = get_reserves(web3, bpool_address)
    results = []
    for token in reserves:
        results.append((token[0], token[1] * ownership_percentage_of_user))
    return results


def get_reserves(web3, bpool_address):
    """Get the reserves of swappable assets, in units of tokens, of a particular 
    balancer pool.
    Returns a list like: 
    [
        (token_address, token_balance),
        (token_address, token_balance)
    ] """
    bpool = web3.eth.contract(address=bpool_address, abi=bpool_abi)
    tokens_in_pool = bpool.functions.getFinalTokens().call()
    # print('tokens in pool: {}'.format(tokens_in_pool))
    result = []

    for address in tokens_in_pool:
        # print('address: {}'.format(address))
        token = web3.eth.contract(address=address, abi=erc20_abi)
        decimals = token.functions.decimals().call()
        # print('--decimals: {}'.format(decimals))
        balance = bpool.functions.getBalance(address).call()
        # print('--balance: {}'.format(balance / 10**decimals))
        result.append((address, balance / 10**decimals))

    return result


def get_price(web3, bpool_address, tokenin_address, tokenout_address):
    """Get price at a balancer pool located at address bpool_address.
    Price is given as the number of tokenin required to buy a single tokenout."""
    if is_pool_empty(web3, bpool_address):
        return 0

    if not is_token_in_exchange(Token.from_address(tokenin_address).symbol, bpool_address):
        return 0

    if not is_token_in_exchange(Token.from_address(tokenout_address).symbol, bpool_address):
        return 0

    bpool = web3.eth.contract(address=bpool_address, abi=bpool_abi)
    tokenin = web3.eth.contract(address=tokenin_address, abi=erc20_abi)
    tokenin_decimals = tokenin.functions.decimals().call()
    tokenout = web3.eth.contract(address=tokenout_address, abi=erc20_abi)
    tokenout_decimals = tokenout.functions.decimals().call()

    # Get spot price - it represents the ratio of one asset to another in terms of wei
    # on both sides. It's the number of wei you'll receive of one asset per wei of the
    # other asset. It is represented as an 18-decimal number so we divide that out.
    # mathematically: spot_price = num_wei_output_token / one_wei_input_token
    spot_price = (
        10**-18
        * bpool.functions.getSpotPrice(
            tokenin_address,
            tokenout_address).call())
    # since spot price is in terms of wei, we multiply out the two tokens decimals
    # to get price in 'normal' units
    spot_price_converted = spot_price * (10**(tokenout_decimals-tokenin_decimals))
    # print(f"{spot_price_converted} units of {tokenin_address} buys 1 unit of {tokenout_address}")

    return spot_price_converted


def get_volume(web3, bpool_address, num_hours=24):
    """Get total volume in a balancer pool for all tokens in the pool.
    Returns a dictionaty like: 
    {
        "token_address": token_volume,
        "token_address": token_volume
    } """
    bpool = web3.eth.contract(address=bpool_address, abi=bpool_abi)
    swap_topic = "0x908fb5ee8f16c6bc9bc3690973819f32a4d4b10188134543c88706e0e1d43378"
    token_volumes = defaultdict(int)

    current_eth_block = web3.eth.blockNumber

    for event in web3.eth.getLogs({
            'fromBlock': current_eth_block - (int(60*60*num_hours / SECONDS_PER_ETH_BLOCK)),
            'toBlock': current_eth_block - 1,
            'address': bpool_address}):
        topic0 = web3.toHex(event['topics'][0])
        if topic0 == swap_topic:
            #print('swap in tx', web3.toHex(event['transactionHash']))
            receipt = web3.eth.getTransactionReceipt(event['transactionHash'])
            parsed_logs = bpool.events.LOG_SWAP().processReceipt(receipt)

            correct_log = None
            for log in parsed_logs:
                if log.address.lower() == bpool.address.lower():
                    correct_log = log
            if correct_log is None:
                logging.warning('bad swap transaction {}'.format(web3.toHex(event['transactionHash'])))
                continue

            tokenAmountIn = correct_log.args.tokenAmountIn
            tokenAmountOut = correct_log.args.tokenAmountOut
            tokenIn = correct_log.args.tokenIn
            tokenOut = correct_log.args.tokenOut

            #print(f"swap {tokenAmountIn} of {tokenIn} for {tokenAmountOut} of {tokenOut}")

            token_volumes[tokenIn] += tokenAmountIn
            token_volumes[tokenOut] += tokenAmountOut
            continue
        else:
            # we only care about swaps, so ignore all else
            continue
            # logging.debug('unknown topic txhash {}'.format(web3.toHex(event['transactionHash'])))
            # logging.debug('unknown topic topic0 {}'.format(topic0))

    for token_address in token_volumes.keys():
        token = web3.eth.contract(address=token_address, abi=erc20_abi)
        token_volumes[token_address] /= 10**token.functions.decimals().call()
    return token_volumes


class BalancerAPI(Daily24hChangeTrackedAPI):
    def __init__(self, currency_symbol):
        super().__init__()
        self._exchange_addresses = get_exchange_addresses_for_token(currency_symbol)
        if len(self._exchange_addresses) == 0:
            raise RuntimeError("Unknown currency_symbol {}, need to add address to balancer.py".format(currency_symbol))

        self._currency_address = Token().from_symbol(currency_symbol).address
        self._decimals = Token().from_symbol(currency_symbol).decimals

        self.currency_symbol = currency_symbol
        self.exchange_name = "Balancer"
        self.command_names = ["balancer"]
        self.short_url = "https://bit.ly/3mp1qCS"  # balancer configured to eth->0xbtc

        self._time_volume_last_updated = 0
        self._w3 = Web3(Web3.HTTPProvider(ETHEREUM_NODE_URL))

    async def _update_volume(self):
        volume_eth = 0
        volume_dai = 0
        volume_tokens = 0
        for exchange_address in self._exchange_addresses:
            pool_volume = get_volume(self._w3, exchange_address, num_hours=24)
            for token_address in pool_volume.keys():
                if token_address.lower() == Token("WETH").address.lower():
                    volume_eth += pool_volume[token_address]
                if token_address.lower() == Token("DAI").address.lower():
                    volume_dai += pool_volume[token_address]
                elif token_address.lower() == self._currency_address.lower():
                    volume_tokens += pool_volume[token_address]
        self.volume_eth = volume_eth
        self.volume_usd = volume_dai
        self.volume_tokens = volume_tokens

    async def _update(self, timeout=10.0):
        if all(is_pool_empty(self._w3, e) for e in self._exchange_addresses):
            raise NoLiquidityException("Pool has no liquidity")

        self.liquidity_eth = 0
        self.liquidity_dai = 0
        self.liquidity_tokens = 0

        price_eth_avg = WeightedAverage()
        price_dai_avg = WeightedAverage()

        for exchange_address in self._exchange_addresses:
            liquidity_eth = 0
            liquidity_dai = 0
            liquidity_tokens = 0

            pool_liquidity = get_reserves(self._w3, exchange_address)
            for token_address, token_amount in pool_liquidity:
                if token_address.lower() == Token("WETH").address.lower():
                    liquidity_eth = token_amount
                if token_address.lower() == Token("DAI").address.lower():
                    liquidity_dai = token_amount
                elif token_address.lower() == self._currency_address.lower():
                    liquidity_tokens = token_amount

            price_eth = get_price(
                self._w3,
                exchange_address,
                Token("WETH").address,
                self._currency_address)
            price_eth_avg.add(price_eth, liquidity_eth)

            price_dai = get_price(
                self._w3,
                exchange_address,
                Token("DAI").address,
                self._currency_address)
            price_dai_avg.add(price_dai, liquidity_dai)

            self.liquidity_dai += liquidity_dai
            self.liquidity_eth += liquidity_eth
            self.liquidity_tokens += liquidity_tokens

        self.price_eth = price_eth_avg.average()
        self.price_usd = price_dai_avg.average()

        # update volume once every hour since it (potentially) loads eth api
        if time.time() - self._time_volume_last_updated > 60 * 60:
            await self._update_volume()
            self._time_volume_last_updated = time.time()


def main():
    import warnings
    # Filter out 'MismatchedABI' warnings since web3 throws a warning anytime it sees
    # an event it does not recognise.. not sure why this is a case. It is very loud.
    warnings.filterwarnings("ignore", category=UserWarning)
    web3 = Web3(Web3.HTTPProvider(ETHEREUM_NODE_URL))


    price_dai = get_price(
        web3,
        "0x63A63f2cAd45fee80b242436BA71e0f462A4178E",
        Token("WETH").address,
        "0xB6eD7644C69416d67B522e20bC294A9a9B405B31")
    print('exchange price existing token:', price_dai)
    price_dai = get_price(
        web3,
        "0x63A63f2cAd45fee80b242436BA71e0f462A4178E",
        Token("DAI").address,
        "0xB6eD7644C69416d67B522e20bC294A9a9B405B31")
    print('exchange price missing token:', price_dai)

    print()
    print('volume: {}'.format(get_volume(web3, "0xDBCd8b30eC1C4b136e740C147112f39D41a10166")))
    print()
    print('{} 0xBTC buys 1 WETH'.format(get_price(
        web3,
        "0xDBCd8b30eC1C4b136e740C147112f39D41a10166",
        "0xB6eD7644C69416d67B522e20bC294A9a9B405B31",
        "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",)))
    print()
    print('{} WETH buys 1 0xBTC'.format(get_price(
        web3,
        "0xDBCd8b30eC1C4b136e740C147112f39D41a10166",
        "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "0xB6eD7644C69416d67B522e20bC294A9a9B405B31",)))
    print()

    print('0xbtc and ETH reserves: {}'.format(get_reserves(web3, "0xDBCd8b30eC1C4b136e740C147112f39D41a10166")))
    print()
    print('balance_of_user: {}'.format(get_pooled_balance_for_address(web3, "0xDBCd8b30eC1C4b136e740C147112f39D41a10166", "0xA7165A762099Cc7044d67CD98a3C8699c03e28A7")))


    # print('$1 in USDC will swap for {} 0xBTC tokens'.format(get_swap_amount(web3, 1, "USDC", "0xBTC")))
    # print('$1 in DAI will swap for {} 0xBTC tokens'.format(get_swap_amount(web3, 1, "DAI", "0xBTC")))
    # print('1 0xBTC token will swap for {} DAI'.format(get_swap_amount(web3, 1, "0xBTC", "DAI")))
    # print('100 0xBTC tokens will swap for {} DAI'.format(get_swap_amount(web3, 100, "0xBTC", "DAI")))
    # print('1 ETH will swap for {} DAI'.format(get_swap_amount(web3, 1, "WETH", "DAI")))
    # print('230 DAI will swap for {} ETH'.format(get_swap_amount(web3, 230, "DAI", "WETH")))
    # print('0xbtc and ETH balances:', get_reserves(web3, "0xBTC", "WETH"))
    # # print('0xbtc and ETH price:', e.get_price("0xBTC", "WETH"), "0xBTC per ETH")
    # # print('0xbtc and ETH price:', e.get_price("WETH", "0xBTC"), "ETH per 0xBTC")
    # print()
    # print('eth usdc reserves ', get_reserves(web3, "WETH", "USDC"))
    # print('1 in ETH will swap for {} USDC '.format(get_swap_amount(web3, 1, "WETH", "USDC")))
    # print('1 in ETH will swap for {} USDT '.format(get_swap_amount(web3, 1, "WETH", "USDT")))
    # print('1 in ETH will swap for {} DAI '.format(get_swap_amount(web3, 1, "WETH", "DAI")))
    # print()

    # get some data from 0xBTC pool via Uniswapv2API
    e = BalancerAPI('0xBTC')
    e.load_once_and_print_values()
    print()
    print('0xbtc-weth liquidity in eth', e.liquidity_eth)
    print('0xbtc-weth volume in tokens', e.liquidity_tokens)

    # e = Uniswapv2API('DAI')
    # e.load_once_and_print_values()


if __name__ == "__main__":
    main()
